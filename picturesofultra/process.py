import datetime as dt
import os
import re
from typing import Any, Dict, List, Tuple, Union

import gspread
import numpy as np
import pandas as pd
import pycountry
import pyyoutube
from leven import levenshtein

from . import *

TAG_RE = re.compile(r"<[^>]+>")


def download_gspread() -> pd.DataFrame:
    gc = gspread.service_account(
        filename=os.path.join(BASEDIR, "secrets", "picturesofultra.key.json")
    )
    sh = gc.open("Ultra stuffs")
    return pd.DataFrame(sh.sheet1.get_all_records())


def validate_non_empty(df: pd.DataFrame, colname: str) -> None:
    errs = df[df[colname].isna()]
    if not errs.empty:
        print(f"Found empty/wrong values in column {colname}")
        print(errs)
        raise RuntimeError(f"Empty values in critical column {colname}")


def validate_unique(df: pd.DataFrame, colname: str) -> None:
    errs = df[df[colname].duplicated(keep=False)]
    if not errs.empty:
        print(f"Found duplicate values in unique column {colname}")
        print(errs)
        raise RuntimeError(f"Duplicate values in unique column {colname}")


def validate_is_yesno(df: pd.DataFrame, colname: str) -> None:
    errs = df[~df[colname].isin(["yes", "no"])]
    if not errs.empty:
        print(f"Found bad values in bool column {colname}")
        print(errs)
        raise RuntimeError(f"Bad values in bool column {colname}")


def remove_tags(text: str) -> str:
    if not text:
        return text
    return TAG_RE.sub("", text).strip()


def clean_gspread_data(orig_data: pd.DataFrame) -> pd.DataFrame:

    data = orig_data.copy()

    # minimal data clean and type casting
    data = data.applymap(lambda x: x.strip() if type(x) is str else x)
    data = data.replace("", np.nan)

    # Drop rows not for export
    validate_is_yesno(data, "export")
    data = data[data.export == "yes"]

    # Drop cols not for export
    data = data.drop(["saw", "export"], axis=1)

    # Col id
    validate_non_empty(data, "id")
    validate_unique(data, "id")

    # Col title
    validate_non_empty(data, "title")
    data["title"] = data.title.apply(remove_tags)
    validate_unique(data, "title")

    # Col release_year
    validate_non_empty(data, "release_year")
    if data.release_year.dtype is not np.dtype("int64"):
        raise RuntimeError(
            f"Invalid value(s) in release_year field. Column type is not int64"
        )

    # Col slug -> slug_fs + slug_web
    validate_non_empty(data, "slug")
    data["slug_fs"] = data.slug.apply(lambda x: x.lower())
    validate_unique(data, "slug_fs")

    def build_web_slug(idx: int, slug: str) -> str:
        if re.match(r"^[0-9a-z\_]+$", slug) is None:
            raise RuntimeError(f"Invalid slug in col id == {idx} ({slug})")
        return slug.replace("_", "-")

    data["slug_web"] = data.apply(
        lambda row: build_web_slug(row.id, row.slug_fs), axis=1
    )
    data.drop("slug", axis=1, inplace=True)

    # Col created
    validate_non_empty(data, "created")

    def parse_created(row: pd.Series) -> dt.datetime:
        try:
            return dt.datetime.strptime(row.created, "%Y/%m/%d")
        except Exception as err:
            raise RuntimeError(
                f"Failed to parse created for row.id == {row.id} ({row.created}) - {err}"
            )

    data["created"] = data.apply(parse_created, axis=1)

    # Col duration
    def parse_duration(row: pd.Series) -> Union[dt.timedelta, float]:
        if row.duration is np.NaN:
            return row.duration
        try:
            t = dt.datetime.strptime(row.duration, "%H:%M:%S")
            return dt.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        except Exception as err:
            raise RuntimeError(
                f"Failed to parse duration for row.id == {row.id} ({row.duration}) - {err}"
            )

    data["duration"] = data.apply(parse_duration, axis=1)

    # Col language
    def parse_lang(idx: int, lang: str) -> Union[str, float]:
        if lang is np.NaN:
            return lang
        if lang not in LANG_MAP:
            raise RuntimeError(f"Unknown language in col id == {idx} ({lang})")
        return LANG_MAP[lang]

    data["language"] = data.apply(lambda row: parse_lang(row.id, row.language), axis=1)

    # Col country
    def country_name(idx: int, code: str) -> Union[str, float]:
        if code is np.NaN:
            return code
        cty = pycountry.countries.get(alpha_2=code)
        if cty is not None:
            return cty.name
        raise RuntimeError(f"Unknown country code in col id == {idx} ({code})")

    data["country"] = data.apply(lambda row: country_name(row.id, row.country), axis=1)

    # Cols direction, production, events, sponsors, people
    # Split into items
    get_name = (
        lambda col, label: NAME_MAPS.get(col, {}).get(label, {}).get("name", label)
    )
    for colname in ["events", "people", "sponsors", "production", "direction"]:
        data[colname] = data[colname].str.split(",").apply(lambda items: [get_name(colname, item.strip()) for item in np.unique(items)] if type(items) is list else items)  # type: ignore[no-untyped-call]

    # Col description
    validate_non_empty(data, "description")
    data["description"] = data.description.apply(remove_tags)

    # TODO Warn if no video link in video

    # Col free access
    validate_non_empty(data, "free_access")
    data["free_access"] = data["free_access"].apply(lambda val: val == "yes")

    # Col favorite
    validate_non_empty(data, "favorite")
    data["favorite"] = data["favorite"].apply(lambda val: val == "yes")

    # Add category info
    def set_category(year: int) -> str:
        if year < 2000:
            return "x-1999"
        elif year < 2005:
            return "2000-2004"
        elif year < 2010:
            return "2005-2009"
        elif year < 2015:
            return "2010-2014"
        else:
            return str(year)

    data["category"] = data.release_year.apply(set_category)

    return data


def extract_keywords(
    data: pd.DataFrame, similarity_threshold: int = 3
) -> Dict[str, Dict[str, Any]]:
    def item_table(data: pd.DataFrame, colname: str) -> pd.DataFrame:
        items = pd.DataFrame(
            data[colname].dropna().explode().str.strip().value_counts()
        )
        items.columns = ["counts"]
        items["is_tag"] = items.counts.apply(lambda c: c >= TAG_MIN_COUNT)
        return items

    def find_similar(
        items: List[str], similarity_threshold: int = 3
    ) -> List[Tuple[str, str, float]]:
        itemnb = len(items)
        scores = [
            (items[i], items[j], levenshtein(items[i], items[j]))
            for i in range(itemnb)
            for j in range(i + 1, itemnb)
        ]
        # TODO if both are len < threshold + 2 : do something
        return sorted(
            [x for x in scores if x[2] <= similarity_threshold], key=lambda x: x[2]
        )

    out = {
        "events": item_table(data, "events"),
        "people": item_table(data, "people"),
        "sponsors": item_table(data, "sponsors"),
        "production": item_table(data, "production"),
        "direction": item_table(data, "direction"),
    }

    for k, items in out.items():
        similar = find_similar(items.index.to_list(), similarity_threshold)

        if len(similar):
            print(f'\n\nFound similar "{k}" keywords. You may want to review these:')
            for sim in similar:
                print(f"* {sim[2]}\t{sim[0]}\t{sim[1]}")

    out_final = {}
    for k, df in out.items():
        out_final[k] = df.to_dict("index")

    # Ensure we have no conflicting keywords
    # all_k = [name for vals in out_final.values() for name, info in vals.items() if info['is_tag']]

    return out_final


def build_site_data() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    data = download_gspread()
    data_df = clean_gspread_data(data)
    keywords = extract_keywords(data_df)
    videos = data_df.to_dict("records")
    return videos, keywords
