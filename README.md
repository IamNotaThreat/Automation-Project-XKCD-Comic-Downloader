# Cyber301 Automation Project — XKCD Comic Downloader

## Project Selected

This project is based on **"Project: Downloading All XKCD Comics"** from
Chapter 12 (Web Scraping) of *[Automate the Boring Stuff with
Python](https://automatetheboringstuff.com/2e/chapter12/)* by Al Sweigart.

The original book project scrapes [xkcd.com](https://xkcd.com) using
`requests` and `BeautifulSoup`, walking backward through the comic
archive one "Prev" link at a time and saving each comic image to disk.

## What the Script Does

`xkcd_downloader.py`:

1. Starts at the latest comic on xkcd.com.
2. Downloads the page's HTML and parses it with BeautifulSoup.
3. Finds the comic image on the page and downloads it to a local folder
   (`xkcd/` by default).
4. Follows the page's "Prev" link to move to the previous comic.
5. Repeats until it either reaches comic #1 or hits the `--limit` you
   specify (whichever comes first).

**Extensions beyond the book's original version:**

- A `--limit` command-line flag so you can grab a handful of comics for
  a quick demo instead of the entire archive (which is several thousand
  comics and would take a long time to download in full).
- A `--output` flag to choose where files are saved.
- Re-running the script skips any comic image already saved, so an
  interrupted run can simply be restarted.
- Network errors on a single page (timeout, 404, connection drop) are
  caught and logged instead of crashing the whole script.
- A short, polite delay between requests so the script doesn't hammer
  xkcd's servers with back-to-back requests.

## How to Run It

**Requirements:** Python 3.10+ (uses the `X | None` type hint syntax).

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/Cyber301-Automation-Project.git
cd Cyber301-Automation-Project

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run it — grab the 10 most recent comics
python xkcd_downloader.py --limit 10

# Or download the entire archive (no limit, saved to ./xkcd by default)
python xkcd_downloader.py

# Or choose a different output folder
python xkcd_downloader.py --limit 25 --output my_comics
```

### Sample Output

```
Starting xkcd download (limit=10, output=xkcd)

[1] Fetching page: https://xkcd.com
    Saved image -> xkcd/text_entry.png
[2] Fetching page: https://xkcd.com/3148/
    Saved image -> xkcd/election_fraud.png
[3] Fetching page: https://xkcd.com/3147/
    Saved image -> xkcd/book_club.png
...
Reached requested limit of 10 comic(s).

Done. Downloaded 10 new comic(s), skipped 0 already on disk.
Files saved in: /home/you/Cyber301-Automation-Project/xkcd
```

Re-running the same command afterward produces:

```
[1] Fetching page: https://xkcd.com
    Already have xkcd/text_entry.png, skipping download.
...
Done. Downloaded 0 new comic(s), skipped 10 already on disk.
```

## Challenges Encountered

- **Some comics don't have a plain image.** xkcd occasionally publishes
  interactive or special-format comics (built with JavaScript or an
  `<iframe>` instead of a single `<img>` tag). The script detects when no
  `#comic img` element exists and logs it as skipped rather than
  crashing.
- **Resolving image URLs correctly.** The image `src` attribute on the
  page is sometimes a protocol-relative URL (`//imgs.xkcd.com/...`), so
  `urljoin()` is used instead of simple string concatenation to build a
  valid, absolute URL every time.
- **Being a good citizen when scraping.** Looping through thousands of
  pages with no delay could look like abusive traffic to the site. A
  short `time.sleep()` between requests and a descriptive `User-Agent`
  header address this.
- **Making repeated runs safe.** Downloading the full archive can take a
  long time, so it needed to be safe to stop and restart without
  re-downloading everything from comic #1 — handled by checking whether
  the target file already exists before downloading it.

## Possible Future Improvements

- Save each comic's alt-text/title (the hover tooltip) alongside the
  image, since it's often part of the joke.
- Add a `--random` option to grab a single random comic for a quick demo.
- Add retry-with-backoff logic for transient network errors instead of
  stopping the whole run on the first failure.
- Write a small test suite using a mocked HTML page instead of hitting
  the live site, so the parsing logic can be verified without a network
  connection.
