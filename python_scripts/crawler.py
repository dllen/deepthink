#!/usr/bin/env python3
"""
Crawler — wipes and rebuilds python_scripts/web_content.db from a fixed list of URLs.

Usage:
    cd python_scripts
    python crawler.py

Behavior:
    * Deletes python_scripts/web_content.db on every run (full wipe).
    * Recreates the `content_summary` table with the canonical schema
      (id, title, created_time, summary, original_url, tags, uid).
    * Fetches each URL in TARGETS with a browser-like User-Agent.
    * Extracts the most useful content the page exposes (MediaWiki main text,
      <article>, <main>, common CSS hooks, paragraphs as a last resort).
    * Generates a Chinese summary — DeepSeek first, otherwise a 300-char
      snippet of the body.
    * Inserts one row per URL with a stable MD5(uid) so re-runs are idempotent
      on a freshly wiped DB (and unique if you remove the wipe).

Dependencies (already in requirements.txt): requests, beautifulsoup4.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "web_content.db"
ENV_PATH = SCRIPT_DIR.parent / ".env"

TARGETS: list[dict] = [
    {
        "url": "https://chuan.us/",
        "tags": "chuan.us",
    },
    {
        # mywiki.cn — "百发百中穿心龙爪手" 首页
        "url": (
            "https://www.mywiki.cn/%E7%99%BE%E5%8F%91%E7%99%BE%E4%B8%AD"
            "%E7%A9%BF%E5%BF%83%E9%BE%99%E7%88%AA%E6%89%8B"
            "/index.php/%E9%A6%96%E9%A1%B5"
        ),
        "tags": "百科,百传中穿心龙爪手",
    },
    {
        "url": "https://xiaolai.co/search",
        "tags": "xiaolai,搜索",
    },
    {
        "url": "https://lixiaolai.com/",
        "tags": "lixiaolai",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh-Hans;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

REQUEST_TIMEOUT = 25  # seconds

# ---------------------------------------------------------------------------
# Tiny .env loader (avoids requiring python-dotenv at runtime)
# ---------------------------------------------------------------------------
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
        v = v.strip().strip('"').strip("'")
        os.environ[k] = v


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE content_summary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    created_time TEXT    NOT NULL,
    summary      TEXT    NOT NULL,
    original_url TEXT    NOT NULL,
    tags         TEXT,
    uid          TEXT
);
CREATE TABLE manual_content (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    created_time TEXT    NOT NULL,
    summary      TEXT,
    tags         TEXT
);
CREATE UNIQUE INDEX idx_uid  ON content_summary (uid);
CREATE INDEX        idx_tags ON content_summary (tags);
"""


def reset_db(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
        print(f"  removed existing db: {path.name}")
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def uid_for(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def insert_row(
    conn: sqlite3.Connection,
    url: str,
    title: str,
    summary: str,
    tags: str,
) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO content_summary "
        "(title, created_time, summary, original_url, tags, uid) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            title,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary,
            url,
            tags,
            uid_for(url),
        ),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------
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


def extract_main_text(soup: BeautifulSoup) -> str:
    for selector in CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(" ", strip=True)
            if len(text) > 60:
                return text

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 30
    ]
    if paragraphs:
        return " ".join(paragraphs)

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


def fetch_url(url: str) -> tuple[str, str]:
    print(f"\n→ {url}")
    resp = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()

    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = extract_title(soup, url)
    content = extract_main_text(soup)
    content = re.sub(r"\s+", " ", content).strip()

    print(f"   title  : {title[:90]}")
    print(f"   chars  : {len(content)}")
    return title, content


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------
def summarize_with_deepseek(title: str, content: str) -> str | None:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-your-"):
        return None

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    prompt = (
        "请用 100–200 个汉字为下面这篇网页写一段中文摘要，要求客观、抓重点，"
        "不要编造内容；如果正文几乎为空，也请如实说明。\n\n"
        f"标题：{title}\n\n正文：\n{content[:3500]}\n\n摘要："
    )

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.3,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — any failure falls back
        print(f"   ! DeepSeek failed ({type(exc).__name__}): {exc}")
        return None


def summarize_fallback(title: str, content: str) -> str:
    cleaned = re.sub(r"\s+", " ", content).strip()
    if not cleaned:
        return f"无法获取「{title}」的正文内容。"
    snippet = cleaned[:300]
    suffix = "…" if len(cleaned) > 300 else ""
    return f"{title}：{snippet}{suffix}"


def make_summary(title: str, content: str) -> str:
    summary = summarize_with_deepseek(title, content)
    if summary:
        print(f"   summary (DeepSeek): {summary[:120]}…")
        return summary
    fallback = summarize_fallback(title, content)
    print(f"   summary (fallback): {fallback[:120]}…")
    return fallback


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    load_env(ENV_PATH)

    print("=" * 60)
    print("Crawler — wipe & rebuild web_content.db")
    print("=" * 60)

    conn = reset_db(DB_PATH)
    print(f"✓ created fresh db at {DB_PATH}")

    saved, failed = 0, 0
    for i, item in enumerate(TARGETS, 1):
        url = item["url"]
        tags = item.get("tags", "")
        try:
            title, content = fetch_url(url)
        except Exception as exc:  # noqa: BLE001
            print(f"   !! fetch failed: {exc}")
            failed += 1
            continue

        if not content or len(content) < 5:
            print("   !! empty body, skipping insert")
            failed += 1
            continue

        summary = make_summary(title, content)
        row_id = insert_row(conn, url, title, summary, tags)
        saved += 1
        print(f"   ✓ saved row id={row_id}  ({i}/{len(TARGETS)})")

    conn.close()

    print("\n" + "=" * 60)
    print(f"Done — saved {saved}/{len(TARGETS)} rows  (failed: {failed})")
    if failed:
        print("       (rows were not inserted for failures)")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(1)
