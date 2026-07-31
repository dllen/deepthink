#!/usr/bin/env python3
"""
Backfill the `content` column of content_summary.

Unlike fetch_from_params.py (which sources URLs from grab_params.json) and
crawler_subpages.py (which sources URLs from ROOT_URLS), this script reads
URLs directly from the DB and re-fetches each one, storing the full
extracted body in the `content` column. The summary / title / tags are
preserved.

Default: only rows where `content IS NULL OR content = ''` are processed.
Pass --all to also refresh rows that already have content (e.g. if the
stored body is now stale).

Run:

    cd python_scripts
    python backfill_content.py           # only NULL / empty content
    python backfill_content.py --all      # every row
    python backfill_content.py --limit 5  # first 5 only (smoke test)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "web_content.db"
ENV_PATH = SCRIPT_DIR.parent / ".env"

MAX_CONTENT_LEN = 100_000
REQUEST_TIMEOUT = 25
POLITE_PAUSE = 0.5  # seconds between HTTP calls

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9,en;q=0.8",
}


CONTENT_SELECTORS = [
    "#mw-content-text",       # MediaWiki
    "article",
    "main",
    "#content",
    "#app",
    ".entry-content",
    ".post-content",
    ".article-content",
    ".article-body",
    "#main-content",
]


def load_env(path: Path) -> None:
    if not path.exists():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if not k or k in os.environ:
            continue
        os.environ[k] = v.strip().strip('"').strip("'")


def extract_main_text(soup: BeautifulSoup) -> str:
    for selector in CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 60:
                return text
    paras = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 30
    ]
    if paras:
        return " ".join(paras)
    return soup.get_text(" ", strip=True)


def extract_title(soup: BeautifulSoup, url: str) -> str:
    if soup.title and soup.title.string:
        t = soup.title.string.strip()
        if t:
            return t
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(strip=True)
        if t:
            return t
    return urlparse(url).netloc or url


def fetch_page(url: str):
    """Fetch URL and return (title, content) or (None, None) on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        print(f"   ! HTTP error ({type(exc).__name__}): {exc}")
        return None, None

    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = extract_title(soup, resp.url or url)
    content = extract_main_text(soup)
    content = re.sub(r"\s+", " ", content).strip()
    return title, content


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-fetch and store full content for content_summary rows."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every row, including those that already have content.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N rows (useful for smoke tests). 0 = no limit.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Disable the polite 0.5s pause between requests.",
    )
    args = parser.parse_args()

    load_env(ENV_PATH)

    if not DB_PATH.exists():
        print(f"✗ {DB_PATH} not found")
        return 1

    print("=" * 60)
    print("Backfill content for web_content.db")
    print(f"  Mode: {'all' if args.all else 'NULL/empty only'}")
    print(f"  Limit: {args.limit or 'none'}")
    print(f"  Polite pause: {'off' if args.no_pause else '0.5s'}")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if args.all:
        cur.execute("SELECT id, original_url FROM content_summary ORDER BY id")
    else:
        cur.execute(
            "SELECT id, original_url FROM content_summary "
            "WHERE content IS NULL OR content = '' "
            "ORDER BY id"
        )
    targets = cur.fetchall()
    if args.limit:
        targets = targets[: args.limit]
    print(f"Target rows: {len(targets)}")

    if not targets:
        print("Nothing to do.")
        conn.close()
        return 0

    updated = 0
    failed = 0
    for i, (row_id, url) in enumerate(targets, start=1):
        if not args.no_pause and i > 1:
            time.sleep(POLITE_PAUSE)
        print(f"\n[{i}/{len(targets)}] id={row_id} {url}")
        title, content = fetch_page(url)
        if not content:
            print("   ! no content fetched, skipping")
            failed += 1
            continue

        body = content
        if len(body) > MAX_CONTENT_LEN:
            body = body[:MAX_CONTENT_LEN] + "\n\n[…truncated at MAX_CONTENT_LEN]"
        cur.execute(
            "UPDATE content_summary SET content = ? WHERE id = ?",
            (body, row_id),
        )
        conn.commit()
        print(f"   ✓ updated body {len(body)} chars")
        updated += 1

    conn.close()
    print("\n" + "=" * 60)
    print(f"Done. updated={updated} failed={failed} target={len(targets)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
