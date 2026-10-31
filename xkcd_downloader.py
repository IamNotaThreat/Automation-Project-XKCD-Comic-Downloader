#!/usr/bin/env python3
"""
xkcd_downloader.py
-------------------
Automate the Boring Stuff with Python -- Chapter 12 (Web Scraping) project:
"Project: Downloading All XKCD Comics"
Book reference: https://automatetheboringstuff.com/2e/chapter12/

WHAT THIS SCRIPT DOES
----------------------
Starting from the latest comic on https://xkcd.com, this script:
  1. Downloads the current page's HTML.
  2. Parses it with BeautifulSoup to find the comic image.
  3. Downloads and saves that image to a local folder.
  4. Follows the "Prev" link to the previous comic.
  5. Repeats until it reaches comic #1, or until it hits the comic
     count given by --limit (whichever comes first).

It is safe to stop and re-run: comics that were already downloaded
are skipped, so the script picks up roughly where it left off.

SAMPLE USAGE
------------
    python xkcd_downloader.py --limit 10
    python xkcd_downloader.py --limit 10 --output comics
    python xkcd_downloader.py                # no --limit = download every comic

SAMPLE OUTPUT (truncated)
--------------------------
    [1] Fetching page: https://xkcd.com
        Saved image -> xkcd/text_entry.png
    [2] Fetching page: https://xkcd.com/3148/
        Saved image -> xkcd/election_fraud.png
    [3] Fetching page: https://xkcd.com/3147/
        Already have xkcd/book_club.png, skipping download.
    ...
    Done. Downloaded 8 new comic(s), skipped 2 already on disk.
    Files saved in: /home/you/xkcd
"""

import argparse
import logging
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# The site we are scraping. Starting here always gives us the newest comic.
START_URL = "https://xkcd.com"

# Be a polite scraper: pause briefly between requests so we don't hammer
# xkcd's servers with a tight loop of requests.
REQUEST_DELAY_SECONDS = 1.0

# A real browser-like header avoids some servers blocking bare "python-requests"
# user agents. This is a courtesy, not a trick to bypass any access control.
HEADERS = {"User-Agent": "xkcd-downloader-student-project/1.0 (automate-the-boring-stuff exercise)"}


def setup_logging() -> None:
    """Configure simple, readable console logging for progress messages."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )


def fetch_page(url: str) -> BeautifulSoup:
    """
    Download one xkcd page and return it as a parsed BeautifulSoup object.

    Raises requests.exceptions.RequestException on network problems so the
    caller can decide how to handle a failed fetch (retry, skip, stop).
    """
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()  # raises an exception for 4xx/5xx responses
    return BeautifulSoup(response.text, "html.parser")


def get_comic_image_url(soup: BeautifulSoup, page_url: str) -> str | None:
    """
    Pull the comic image URL out of a parsed xkcd page.

    Returns None if no comic image is found (this happens on a handful of
    "special" xkcd pages, such as interactive comics, that don't use a
    plain <img> tag).
    """
    comic_elem = soup.select("#comic img")
    if not comic_elem:
        return None
    # The <img> src is often protocol-relative ("//imgs.xkcd.com/...") or
    # a relative path, so urljoin() resolves it against the page's URL.
    return urljoin(page_url, comic_elem[0].get("src"))


def get_prev_url(soup: BeautifulSoup, page_url: str) -> str | None:
    """
    Find the "Prev" link's target so we can walk backward through the
    archive one comic at a time. Returns None once we've reached comic #1,
    since xkcd's first comic has a disabled Prev link that points to "#".
    """
    prev_link = soup.select('a[rel="prev"]')
    if not prev_link:
        return None
    href = prev_link[0].get("href", "")
    if href in ("#", ""):
        return None
    return urljoin(page_url, href)


def download_image(image_url: str, output_dir: str) -> str:
    """
    Download a single image and save it under output_dir.
    Returns the local file path it was saved to (or already existed at).
    """
    filename = os.path.basename(image_url)
    local_path = os.path.join(output_dir, filename)

    # Skip re-downloading a comic we already have -- makes the script
    # safe to re-run after an interruption.
    if os.path.exists(local_path):
        logging.info("    Already have %s, skipping download.", local_path)
        return local_path

    image_response = requests.get(image_url, headers=HEADERS, timeout=10)
    image_response.raise_for_status()

    # Write in binary mode and in chunks, since comic images are
    # binary data (PNG/JPEG), not text.
    with open(local_path, "wb") as image_file:
        for chunk in image_response.iter_content(chunk_size=8192):
            image_file.write(chunk)

    logging.info("    Saved image -> %s", local_path)
    return local_path


def download_xkcd(limit: int | None, output_dir: str) -> tuple[int, int]:
    """
    Walk backward through xkcd starting at the latest comic, downloading
    each comic's image until either:
      - we've downloaded `limit` comics (if limit is not None), or
      - we reach comic #1 and there is no more "Prev" link.

    Returns (downloaded_count, skipped_count).
    """
    os.makedirs(output_dir, exist_ok=True)

    url = START_URL
    downloaded = 0
    skipped = 0
    comic_number = 0

    while url is not None:
        comic_number += 1
        logging.info("[%d] Fetching page: %s", comic_number, url)

        try:
            soup = fetch_page(url)
        except requests.exceptions.RequestException as error:
            # A single failed page shouldn't crash the whole run -- log it
            # and stop, since we can no longer find the next "Prev" link.
            logging.error("    Failed to fetch %s (%s). Stopping.", url, error)
            break

        image_url = get_comic_image_url(soup, url)
        if image_url is None:
            logging.info("    No comic image found on this page, skipping.")
        else:
            before = os.path.exists(os.path.join(output_dir, os.path.basename(image_url)))
            try:
                download_image(image_url, output_dir)
                if before:
                    skipped += 1
                else:
                    downloaded += 1
            except requests.exceptions.RequestException as error:
                logging.error("    Failed to download %s (%s).", image_url, error)

        if limit is not None and downloaded + skipped >= limit:
            logging.info("Reached requested limit of %d comic(s).", limit)
            break

        url = get_prev_url(soup, url)
        if url is not None:
            time.sleep(REQUEST_DELAY_SECONDS)  # be polite between requests

    return downloaded, skipped


def parse_args() -> argparse.Namespace:
    """Read command-line options: how many comics to grab and where to save them."""
    parser = argparse.ArgumentParser(
        description="Download xkcd comics, starting from the latest one."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of comics to download. Omit to download every comic.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="xkcd",
        help="Folder to save downloaded comic images into (default: ./xkcd).",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    logging.info("Starting xkcd download (limit=%s, output=%s)\n", args.limit, args.output)
    downloaded, skipped = download_xkcd(limit=args.limit, output_dir=args.output)

    logging.info(
        "\nDone. Downloaded %d new comic(s), skipped %d already on disk.",
        downloaded,
        skipped,
    )
    logging.info("Files saved in: %s", os.path.abspath(args.output))


if __name__ == "__main__":
    main()
