#!env python

from picturesofultra.process import build_site_data
from picturesofultra.media import download_images
from picturesofultra.generate import build_site_content


def main():
    videos, kwds = build_site_data()
    images = download_images(videos)
    build_site_content(videos, kwds, images)

    return videos, kwds, images


if __name__ == "__main__":
    main()

