#!/usr/bin/env python3
"""
crawler_subpages.py — fetch each root page + a bounded set of its sub-URLs and
append them all to python_scripts/web_content.db.

Unlike crawler.py (which wipes the DB on every run), this script:
    * NEVER deletes or modifies existing rows.
    * Inserts the 4 root pages (idempotent via UNIQUE uid).
    * For each root, discovers same-domain internal links from the rendered
      HTML, filters out nav / utility / static-asset URLs, and caps the list.
    * Fetches each sub-URL, summarizes it, and inserts the row.
    * Re-running is safe — INSERT OR IGNORE on the uid unique index.

Defaults:
    * MAX_SUBPAGES_PER_ROOT = 15      (≈ 60 sub-rows max + 4 roots)
    * MIN_CONTENT_LEN        = 50     (skip essentially-empty pages)
    * Polite pause of 0.5 s between requests.

Usage:
    cd python_scripts
    python crawler_subpages.py
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "web_content.db"
ENV_PATH = SCRIPT_DIR.parent / ".env"

ROOT_URLS: list[dict] = [
    {
        "url": "https://chuan.us/",
        "tags": "chuan.us",
    },
    {
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

MAX_SUBPAGES_PER_ROOT = 15
MIN_CONTENT_LEN = 50
REQUEST_TIMEOUT = 25
POLITE_PAUSE = 0.5  # seconds between HTTP calls

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
}

# Filter — drop these URL path fragments anywhere they appear
SKIP_PATH_FRAGMENTS = (
    "/login", "/logout", "/signin", "/signup", "/sign-in", "/sign-up",
    "/register", "/admin", "/wp-admin", "/wp-json",
    "/api/", "/cdn-cgi/", "/feed", "/rss", "/atom",
    "/sitemap", "/robots.txt", "/static/", "/assets/",
    "/tag/", "/tags/", "/category/", "/author/",
    "/page/", "/p=", "?p=", "/search?", "/search/",
    "/privacy", "/terms", "/about-us", "/contact",
    "/wp-content/uploads/", "/wp-includes/",
    "/?",
)

# Skip MediaWiki edit / history / talk / redlink queries
SKIP_QUERY_PARAMS = (
    "action=edit", "action=history", "action=raw", "action=info",
    "action=delete", "action=protect", "action=purge",
    "action=submit", "action=render",
    "redlink=1", "oldid=", "diff=",
)

# Static asset extensions — never fetch these
STATIC_EXT = re.compile(
    r"\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico|tiff|pdf|zip|tar|gz|7z|rar|"
    r"mp3|mp4|m4a|wav|ogg|avi|mkv|mov|wmv|flv|webm|"
    r"css|js|map|woff2?|ttf|otf|eot|json|xml|rss|atom)$",
    re.I,
)

# ---------------------------------------------------------------------------
# Tiny .env loader (so we don't depend on python-dotenv)
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
# Database (append-only — never wipes)
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS content_summary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    created_time TEXT    NOT NULL,
    summary      TEXT    NOT NULL,
    original_url TEXT    NOT NULL,
    tags         TEXT,
    uid          TEXT
);
CREATE TABLE IF NOT EXISTS manual_content (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    created_time TEXT    NOT NULL,
    summary      TEXT,
    tags         TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_uid  ON content_summary (uid);
CREATE INDEX        IF NOT EXISTS idx_tags ON content_summary (tags);
"""


def ensure_schema(path: Path) -> sqlite3.Connection:
    """Connect and make sure the schema exists. Never deletes rows."""
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
) -> int | None:
    """Insert a row; ON CONFLICT(uid) DO NOTHING. Returns rowid or None."""
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO content_summary "
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
    return cur.lastrowid if cur.rowcount > 0 else None


# ---------------------------------------------------------------------------
# Fetch & extract
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


def fetch_page(url: str) -> tuple[str, str, BeautifulSoup] | None:
    """Fetch a URL and return (title, plain_text, soup) — or None on failure."""
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"   ! HTTP error ({type(exc).__name__}): {exc}")
        return None

    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = extract_title(soup, resp.url or url)
    content = extract_main_text(soup)
    content = re.sub(r"\s+", " ", content).strip()
    return title, content, soup


# ---------------------------------------------------------------------------
# Link discovery & filtering
# ---------------------------------------------------------------------------
def _normalize_host(host: str) -> str:
    """Treat www. and the bare host as the same site."""
    return (host or "").lower().lstrip(".").removeprefix("www.")


def is_same_site(url_a: str, url_b: str) -> bool:
    return _normalize_host(urlparse(url_a).netloc) == _normalize_host(urlparse(url_b).netloc)


def is_skippable_link(href: str) -> bool:
    if not href:
        return True
    href = href.strip()
    if not href:
        return True
    low = href.lower()
    if low.startswith(("#", "mailto:", "javascript:", "tel:", "data:", "ftp:")):
        return True
    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return True
    if STATIC_EXT.search(parsed.path or ""):
        return True
    path_low = (parsed.path or "/").lower()
    for frag in SKIP_PATH_FRAGMENTS:
        if frag in path_low or frag in low:
            return True
    query_low = (parsed.query or "").lower()
    for q in SKIP_QUERY_PARAMS:
        if q in query_low:
            return True
    return False


def discover_suburls(
    root_url: str,
    soup: BeautifulSoup,
    cap: int = MAX_SUBPAGES_PER_ROOT,
) -> list[str]:
    """Pull all internal links from `soup`, normalize and dedupe, exclude root."""
    root_norm = root_url.rstrip("/")
    candidates: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if is_skippable_link(href):
            continue
        absolute = urljoin(root_url, href).split("#", 1)[0]
        if not absolute:
            continue
        if absolute.rstrip("/") == root_norm:
            continue
        if not is_same_site(absolute, root_url):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        candidates.append(absolute)
        if len(candidates) >= cap:
            break
    return candidates


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
        "请用 100–200 个汉字为下面这篇网页写一段中文摘要，"
        "要求客观、抓重点，不要编造内容；如果正文几乎为空，也请如实说明。\n\n"
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
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as exc:  # noqa: BLE001
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
def insert_one(
    conn: sqlite3.Connection,
    url: str,
    tags: str,
    *,
    label: str,
) -> bool:
    """Fetch one URL, summarize, insert. Returns True if newly inserted."""
    print(f"\n→ {label} {url}")
    page = fetch_page(url)
    if page is None:
        return False
    title, content, _ = page
    print(f"   title  : {title[:90]}")
    print(f"   chars  : {len(content)}")

    if len(content) < MIN_CONTENT_LEN:
        print(f"   skip   : only {len(content)} chars (below min {MIN_CONTENT_LEN})")
        return False

    summary = make_summary(title, content)
    row_id = insert_row(conn, url, title, summary, tags)
    if row_id is None:
        print("   skip   : already in db (uid collision)")
        return False
    print(f"   ✓ saved id={row_id}")
    return True


def main() -> int:
    load_env(ENV_PATH)

    print("=" * 60)
    print("Crawler (subpages) — append-only")
    print("=" * 60)
    print(f"DB: {DB_PATH}  (will append, never wipe)")

    conn = ensure_schema(DB_PATH)
    print("✓ schema verified\n")

    grand_inserted = 0
    grand_skipped = 0
    grand_failed = 0

    try:
        for root in ROOT_URLS:
            root_url = root["url"]
            root_tags = root.get("tags", "")

            print(f"\n══════ ROOT  {root_url}  ══════")

            # 1) Insert the root page itself
            inserted = insert_one(conn, root_url, root_tags, label="ROOT  ")
            grand_inserted += int(bool(inserted))
            grand_skipped += int(not inserted)

            # 2) Discover same-domain sub-URLs from the root page
            page = fetch_page(root_url)
            if page is None:
                grand_failed += 1
                continue
            _title, _content, root_soup = page

            suburls = discover_suburls(root_url, root_soup)
            print(f"\n   discovered {len(suburls)} candidate sub-URL(s)")
            sub_tags = root_tags + ",subpage"
            for i, sub_url in enumerate(suburls, 1):
                time.sleep(POLITE_PAUSE)
                ok = insert_one(conn, sub_url, sub_tags, label=f"SUB   [{i:>2}/{len(suburls)}]")
                if ok:
                    grand_inserted += 1
                else:
                    grand_skipped += 1
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print(
        f"Done — inserted {grand_inserted}, "
        f"skipped {grand_skipped} (already in db), "
        f"failed {grand_failed} (network/empty)"
    )
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(1)
