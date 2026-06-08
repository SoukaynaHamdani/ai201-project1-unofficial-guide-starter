"""
Milestone 3 - Step 1: INGESTION

Pulls every source defined in sources.py, extracts clean text, and writes one
normalized record per "document unit" to data/processed/documents.jsonl.

A "document unit" is:
  - one Reddit post (with its comments appended)  -> kind "reddit"
  - one web page                                  -> kind "html"
  - one PDF page                                  -> kind "pdf"
  - one CSV row (one review)                      -> kind "csv"
  - one whole text file                           -> kind "txt"

Run:  python src/ingest.py
"""

import json
import os
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from sources import SOURCES, SUBREDDIT

# Many sites (and Reddit) 403 a non-browser User-Agent. A realistic browser UA
# gets past simple bot filters; it does NOT defeat Reddit's stricter blocking.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

OUT_DIR = os.path.join("data", "processed")
OUT_PATH = os.path.join(OUT_DIR, "documents.jsonl")

# Be polite to servers: pause between network requests.
REQUEST_DELAY = 2.0


def fetch_url(url, as_json=False):
    """GET a URL with retries. Returns response text or parsed json (or None)."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            if as_json:
                return resp.json()
            # Fix mojibake: requests often guesses latin-1; let charset detection win
            # so curly apostrophes/quotes decode correctly instead of becoming U+FFFD.
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text
        except Exception as e:  # noqa: BLE001  (student project: keep it simple)
            print(f"    ! attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


# --------------------------------------------------------------------------- #
# Per-kind extractors. Each yields dicts: {title, text, url}
# --------------------------------------------------------------------------- #

def ingest_reddit(src):
    """Search the subreddit, then pull each top post + its comments."""
    query = src["location"]
    limit = src.get("extra", {}).get("limit", 8)
    search_url = (
        f"https://www.reddit.com/r/{SUBREDDIT}/search.json"
        f"?q={requests.utils.quote(query)}&restrict_sr=1&sort=relevance&t=all&limit={limit}"
    )
    data = fetch_url(search_url, as_json=True)
    if not data:
        print("    ! Reddit search failed (often a 403/429). "
              "Fallback: save thread JSON manually into documents/ and switch this source to 'txt'.")
        return

    for child in data.get("data", {}).get("children", []):
        post = child["data"]
        permalink = "https://www.reddit.com" + post["permalink"]
        # Fetch the full thread (post + comments)
        thread = fetch_url(permalink + ".json", as_json=True)
        parts = [post.get("title", ""), post.get("selftext", "")]
        if thread and len(thread) > 1:
            for c in thread[1]["data"]["children"]:
                body = c.get("data", {}).get("body")
                if body:
                    parts.append(body)
        text = "\n\n".join(p for p in parts if p and p.strip())
        if text.strip():
            yield {"title": post.get("title", ""), "text": text, "url": permalink}


def ingest_html(src):
    """Download a page and strip it down to readable body text."""
    html = fetch_url(src["location"])
    if not html:
        return
    soup = BeautifulSoup(html, "lxml")
    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "noscript",
                     "aside", "button"]):
        tag.decompose()
    # Prefer the main content region if the page marks one (MediaWiki, <main>, <article>).
    # This drops site chrome (sidebars, menus) that isn't inside semantic nav tags.
    main = (soup.select_one("#mw-content-text")
            or soup.select_one("main")
            or soup.select_one("article")
            or soup.body
            or soup)
    text = main.get_text(separator="\n")
    # MediaWiki appends a footer starting with "Retrieved from"; cut it and anything after.
    cut = text.find("Retrieved from")
    if cut != -1:
        text = text[:cut]
    # Common nav/boilerplate lines that survive tag stripping
    BOILERPLATE = {"skip to main content", "skip to content", "menu", "search",
                   "toggle navigation", "back to top"}
    seen = set()
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.lower() in BOILERPLATE:
            continue
        if ln in seen:           # drop repeated lines (menus echoed in multiple spots)
            continue
        seen.add(ln)
        lines.append(ln)
    text = "\n".join(lines)
    title = soup.title.get_text(strip=True) if soup.title else src["name"]
    # A page that cleans down to almost nothing is usually JavaScript-rendered:
    # requests/BeautifulSoup only see the empty HTML shell. Skip + warn rather than
    # emit a useless fragment chunk.
    if len(text) < 200:
        print(f"    ! '{src['name']}' yielded only {len(text)} chars after cleaning "
              "(likely JS-rendered). Skipping. Save the text manually as a .txt instead.")
        return
    yield {"title": title, "text": text, "url": src["location"]}


def ingest_pdf(src):
    """Extract text page-by-page with pdfplumber. One record per page."""
    path = src["location"]
    if not os.path.exists(path):
        print(f"    ! PDF not found at {path}. Download it first (see sources.py note). Skipping.")
        return
    import pdfplumber  # imported lazily so the script runs even without the PDF
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                yield {"title": f"{src['name']} - p.{i}", "text": text, "url": path}


def ingest_csv(src):
    """One review per row -> one document."""
    df = pd.read_csv(src["location"])
    for _, row in df.iterrows():
        venue = row.get("venue", src["name"])
        rating = row.get("rating", "")
        review = row.get("review_text", "")
        date = row.get("date", "")
        text = f"Review of {venue} ({rating}/5 stars, {date}): {review}"
        yield {"title": f"{venue} review", "text": text, "url": src["location"]}


def ingest_txt(src):
    """Whole text file as one document."""
    with open(src["location"], "r", encoding="utf-8") as f:
        text = f.read()
    if text.strip():
        yield {"title": src["name"], "text": text, "url": src["location"]}


EXTRACTORS = {
    "reddit": ingest_reddit,
    "html": ingest_html,
    "pdf": ingest_pdf,
    "csv": ingest_csv,
    "txt": ingest_txt,
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    documents = []
    for src in SOURCES:
        if not src.get("enabled", True):  # skip sources explicitly disabled
            print(f"-- skipping {src['name']} (disabled)")
            continue
        print(f"-> {src['name']} ({src['kind']})")
        extractor = EXTRACTORS[src["kind"]]
        count = 0
        for unit in extractor(src):
            documents.append({
                "id": f"doc-{len(documents):04d}",
                "source_name": src["name"],
                "source_type": src["source_type"],  # official | community | mock
                "kind": src["kind"],
                "title": unit["title"],
                "url": unit["url"],
                "text": unit["text"],
            })
            count += 1
        print(f"   collected {count} document unit(s)")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"\nDONE. Wrote {len(documents)} documents to {OUT_PATH}")


if __name__ == "__main__":
    main()
