import json
import os
import re
import urllib.parse as urlparse
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pyyoutube
import requests
import vimeo

from . import *

IMG_FORMATS = ["jpg", "jpeg", "gif", "png"]
MIN_THUMB_WIDTH = 120


def youtube_get_video(urldata: Dict[str, str]) -> pyyoutube.VideoListResponse:
    with open(os.path.join(BASEDIR, "secrets", "youtube_api_key")) as f:
        yt_key = f.read()
    api = pyyoutube.Api(api_key=yt_key)
    return api.get_video_by_id(video_id=urldata["vid"])


def vimeo_get_video(urldata: Dict[str, str]) -> Dict[str, Any]:
    with open(os.path.join(BASEDIR, "secrets", "vimeo.json")) as f:
        vm_creds = json.load(f)
    v = vimeo.VimeoClient(**vm_creds)
    return v.get(f'https://api.vimeo.com/videos/{urldata["vid"]}').json()  # type: ignore[no-any-return]


def parse_stream_url(video_id: Union[int, str], ss: str) -> Optional[Dict[str, str]]:
    out = None
    try:
        url = urlparse.urlparse(ss)
        if "youtube" in url.netloc:
            out = {
                "type": "youtube",
                "vid": urlparse.parse_qs(url.query)["v"][0],
                "url": url.geturl()
            }
        elif "vimeo" in url.netloc and 'ondemand' not in url.path:
            out = {
                "type": "vimeo",
                "vid": url.path.split("/")[-1],
                "url": url.geturl()
            }
        elif "dailymotion" in url.netloc:
            out = {
                "type": "dailymotion",
                "vid": url.path.split("/")[-1],
                "url": url.geturl()
            }
    except Exception as err:
        raise RuntimeError(f"Invalid URL {ss} for video id={video_id}")

    return out


def download_image(url: str, basepath: str, filename: str) -> str:
    # Extract extension:
    ext = urlparse.urlparse(url).path.split("/")[-1].split(".")[-1]
    if ext not in IMG_FORMATS:
        raise RuntimeError(f'Unexpected img extension for url "{url}"')
    fname = f"{filename}.{ext}"
    r = requests.get(url, timeout=2)
    if r.status_code == 200:
        with open(os.path.join(basepath, fname), "wb") as f:
            f.write(r.content)
    else:
        raise RuntimeError(f'Unexpected response "{r.status_code}" from "{url}"')
    return fname


def images_get_from_links(
    video: Dict[str, Any], img_basepath: str
) -> Optional[Dict[str, str]]:
    # Get the image from main stream if supported, if not, get from trailer, if not, well fuck
    MIN_THUMB_WIDTH = 120
    v_images = None
    for key in ["link_stream", "link_trailer"]:
        if video[key] is np.NaN:
            continue
        urldata = parse_stream_url(video["id"], video[key])
        if urldata is None:
            continue
        if urldata["type"] == "youtube":
            vdata = youtube_get_video(urldata)
            if len(vdata.items) == 0:
                continue
            yt_vid = vdata.items[0].to_dict()["snippet"]
            if "thumbnails" in yt_vid and yt_vid["thumbnails"]:
                imgs = []
                for imgsize in ["default", "medium", "high", "standard", "maxres"]:
                    if imgsize not in yt_vid["thumbnails"]:
                        continue
                    if yt_vid["thumbnails"][imgsize] is None or not yt_vid[
                        "thumbnails"
                    ][imgsize].get("url", None):
                        continue
                    imgs.append(yt_vid["thumbnails"][imgsize]["url"])
                v_images = {"thumb": imgs[0], "main": imgs[-1]}
                break

        elif urldata["type"] == "vimeo":
            cdata = vimeo_get_video(urldata)
            pictures = cdata["pictures"]["sizes"]
            imgs = []
            for pic in pictures:
                if pic["width"] >= MIN_THUMB_WIDTH:
                    imgs.append(pic)
            imgs.sort(key=lambda x: x["width"])  # type: ignore[no-any-return]
            # Set URL w/o QS
            img_thumb = urlparse.urlparse(imgs[0]["link"])
            img_main = urlparse.urlparse(imgs[-1]["link"])
            v_images = {
                "thumb": f"{img_thumb.scheme}://{img_thumb.netloc}{img_thumb.path}",
                "main": f"{img_main.scheme}://{img_main.netloc}{img_main.path}",
            }
            break

    if v_images is not None:
        # Download the img files
        v_images["thumb"] = download_image(
            v_images["thumb"], img_basepath, f'{video["slug_fs"]}.thumb'
        )
        v_images["main"] = download_image(
            v_images["main"], img_basepath, f'{video["slug_fs"]}.main'
        )
        print(f'Downloaded images for video {video["slug_fs"]}[{video["id"]}]')
    else:
        print(
            f'Unable to download images for video {video["slug_fs"]}[{video["id"]}] using urls: {video["link_trailer"]}, {video["link_stream"]}'
        )

    return v_images


def download_images(videos: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    images = {}
    images_basepath = os.path.join(BASEDIR, "content", "images")
    for video in videos:
        # Support multiple file formats
        vslug = video["slug_fs"]
        v_images = {}

        # Check if imgs already exist for this video
        for img_format in IMG_FORMATS:
            if os.path.isfile(
                os.path.join(images_basepath, f"{vslug}.main.{img_format}")
            ):
                v_images["main"] = f"{vslug}.main.{img_format}"
            if os.path.isfile(
                os.path.join(images_basepath, f"{vslug}.thumb.{img_format}")
            ):
                v_images["thumb"] = f"{vslug}.thumb.{img_format}"

        # if there is only a thumb, set it as main also, is only main, set it as thumb also.
        if "main" in v_images and "thumb" not in v_images:
            v_images["thumb"] = v_images["main"]
        elif "thumb" in v_images and "main" not in v_images:
            v_images["main"] = v_images["thumb"]
        elif not v_images:
            retrieved = images_get_from_links(video, images_basepath)
            if retrieved is not None:
                v_images = retrieved

        if v_images:
            images[vslug] = v_images

    return images
