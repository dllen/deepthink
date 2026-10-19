#!/usr/bin/env python3
"""
crawler_subpages.py — fetch each root page + a bounded set of its sub-URLs and
append them all to python_scripts/web_content.db.

Unlike crawler.py (which wipes the DB on every run), this script:
    * NEVER deletes or modifies existing rows.
    * Inserts each root page (idempotent via UNIQUE uid); roots marked
      `skip_root` are listing pages and are not inserted at all.
    * For each root, discovers same-domain internal links from the rendered
      HTML, filters out nav / utility / static-asset URLs, and caps the list.
    * Fetches each sub-URL, summarizes it, and inserts the row.
    * Re-running is safe — INSERT OR IGNORE on the uid unique index.

Noise guards (added after the 2026-10 cleanup):
    * MediaWiki special/login/utility pages are skipped by URL.
    * Site-chrome titles (所有页面 / 特殊页面 / 登录 / Issues 列表 …) are skipped.
    * A row whose exact title is already in the DB is skipped, which stops the
      same article from being stored twice under two URL forms (e.g. wiki
      /index.php/<title> vs /<title>, or a weekly issue mirrored on two hosts).
    * The vibecodinghub weekly mirror root is gone — the GitHub blob view is the
      canonical weekly source, so future runs cannot duplicate it.

Defaults:
    * MAX_SUBPAGES_PER_ROOT = 30      (≈ 120 sub-rows max + 4 roots)
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
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from category_classifier import DEFAULT_CATEGORY, classify_one

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
    {
        # GitHub Issues 列表：读者自荐（开源自荐、文章自荐、工具推荐等）。
        # ponytail: 默认只看 OPEN 状态；closed 历史要全量可再手添带 q=is:issue+state:closed 的变体。
        # 标题在 bdi.js-issue-title；正文在 .markdown-body（首页 <h1> 顺带会拼上 #issueId，但 bdi 干净）。
        # 只跟进纯 issues/<id> 链接，过滤分页/筛选 chip。
        # skip_root: 列表页本身不是内容，不插入（2026-10 清理前会存成「Issues · …」噪声行）。
        "url": "https://github.com/ruanyf/weekly/issues",
        "tags": "github-issues,ruanyifeng,weekly",
        # GitHub SPA 渲染的 issue 页，bdi.js-issue-title 不一定存在；直接用 <title> 后剥掉 " · Issue #NNN · ... · GitHub" 后缀。
        "title_selector": "title",
        "title_strip": r"\s*·\s*Issue\s*#\d+.*$",
        "content_selectors": ["[data-testid=\"issue-body\"]", ".markdown-body"],
        "link_pattern": r"/ruanyf/weekly/issues/\d+$",
        "skip_root": True,
    },
    {
        # GitHub blob 视图：<title  > 是 "repo/path at master · repo · GitHub"，没有用。
        # 真正标题在 .markdown-body 里的第一个 <h1  >；正文也在 .markdown-body。
        # 只跟进 issue markdown 页面，避开市场页/导航。master/main 两个分支都容许。
        # 周刊的唯一抓取源（vibecodinghub 镜像根已移除；2026-10 清理时镜像重复全部删除）。
        "url": "https://github.com/ruanyf/weekly",
        "tags": "github,ruanyifeng,weekly",
        "title_selector": ".markdown-body h1",
        "content_selectors": [".markdown-body", "article"],
        "link_pattern": r"/ruanyf/weekly/blob/(?:master|main)/docs/issue-\d+\.md$",
        "skip_root": True,
    },
    # ------------------------------------------------------------------
    # 热搜 / 聚合类信息源头（多平台热榜）。
    # 注意：这些多为 JS 渲染的 SPA 热榜页，纯 requests 可能只拿到空壳 HTML
    # （正文 < MIN_CONTENT_LEN 会被跳过）；且热榜链接指向站外平台，
    # is_same_site 过滤后不会跟进子页。若抓到空壳，需换 browser_scraper
    # 或逐站补 title_selector/content_selectors。
    # ------------------------------------------------------------------
    {
        # NewsNow 多平台聚合：知乎/微博/B站/虎扑/V2EX 一站看全。
        "url": "https://newsnow.busiyi.world/",
        "tags": "聚合,热搜,newsnow",
    },
    {
        # SoPilot：专盯 X 爆款帖子与舆论风向。
        "url": "https://sopilot.net/zh/hot-tweets",
        "tags": "聚合,X,热搜,sopilot",
    },
    {
        # 今日热榜：含 GitHub Trending / Product Hunt / Hacker News。
        "url": "https://tophub.today/c/tech",
        "tags": "聚合,热搜,技术,tophub",
    },
    {
        # 英为财情：全球行情（A股/港股/美股/外汇/大宗商品）。
        "url": "https://www.investing.com/",
        "tags": "财经,行情,投资,investing",
    },
    {
        # 萝卜投研（通联数据）：AI 驱动的智能投研平台（研报/知识图谱/财务模型）。
        # 官网是 robo.datayes.com —— luobo.cn 是「保卫萝卜」手游，勿混。
        "url": "https://robo.datayes.com/",
        "tags": "投研,AI,研报,robo",
    },
    {
        # REBANG：50+ 平台热搜聚合，极简无广告。
        "url": "https://rebang.open2hub.com/",
        "tags": "聚合,热搜,rebang",
    },
]

MAX_SUBPAGES_PER_ROOT = 30
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
    # 2026-10 cleanup: special/login pages carry a return URL or a Special: target
    "returnto=", "title=special:", "title=special%3a", "pagesetting",
)

# MediaWiki special pages — decoded path/query contains "特殊:" (Special:)
SPECIAL_PATH = re.compile(r"(?:special:|特殊:)", re.I)

# Site chrome titles — navigation / login / listing pages, never article content
TITLE_NOISE_PATTERNS = (
    "所有页面", "特殊页面", "需要登录", "用户登录", "登录 -", "登录－",
)
TITLE_NOISE_EXACT = {"个人维基", "首页 - 个人维基", "科技爱好者周刊"}
TITLE_NOISE_REGEX = re.compile(r"^(?:Issues|Pull requests|Actions|Projects)\s*·", re.I)

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
    uid          TEXT,
    content      TEXT,
    category     TEXT,
    category_source TEXT DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS manual_content (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    created_time TEXT    NOT NULL,
    summary      TEXT,
    tags         TEXT
);
"""

MAX_CONTENT_LEN = 100_000  # cap per-row stored body to keep DB compact


def ensure_schema(path: Path) -> sqlite3.Connection:
    """Connect and make sure the schema exists. Never deletes rows.

    Adds the `content` / `category` / `category_source` columns to existing
    content_summary tables via ALTER TABLE on subsequent runs (SQLite has no
    IF NOT EXISTS for columns).
    """
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA_SQL)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(content_summary)")
    cols = [row[1] for row in cur.fetchall()]
    if "uid" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN uid TEXT")
    if "content" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN content TEXT")
    if "category" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN category TEXT")
    if "category_source" not in cols:
        cur.execute(
            "ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default'"
        )
    # Indexes must come after the ALTERs: an old DB may lack uid/category, and
    # CREATE INDEX on a missing column fails before the upgrade completes.
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uid ON content_summary (uid)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags ON content_summary (tags)")
    conn.commit()
    return conn


def uid_for(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def title_exists(conn: sqlite3.Connection, title: str) -> bool:
    """True when an exact title is already stored (guards URL-variant dupes)."""
    cur = conn.execute(
        "SELECT 1 FROM content_summary WHERE title = ? LIMIT 1", (title.strip(),)
    )
    return cur.fetchone() is not None


def insert_row(
    conn: sqlite3.Connection,
    url: str,
    title: str,
    summary: str,
    tags: str,
    content: str = "",
    update_content: bool = False,
) -> int | None:
    """Insert a row; ON CONFLICT(uid) DO NOTHING. Returns rowid or None.

    `content` is the full extracted page text — stored as a backup so the
    source body survives even if the URL goes offline. Capped at MAX_CONTENT_LEN.

    When `update_content=True` and the row already exists, only the `content`
    column is updated (title / summary / created_time / tags preserved).
    """
    cur = conn.cursor()
    body = (content or "").strip()
    if len(body) > MAX_CONTENT_LEN:
        body = body[:MAX_CONTENT_LEN] + "\n\n[…truncated at MAX_CONTENT_LEN]"
    uid = uid_for(url)

    if update_content:
        cur.execute("UPDATE content_summary SET content = ? WHERE uid = ?", (body, uid))
        if cur.rowcount > 0:
            conn.commit()
            cur.execute("SELECT id FROM content_summary WHERE uid = ?", (uid,))
            row = cur.fetchone()
            return row[0] if row else None
        # Row didn't exist yet — fall through to insert

    # Duplicate check BEFORE classification: re-running over an existing DB must
    # not spend a DeepSeek call (or an INSERT OR IGNORE) on a known URL.
    cur.execute("SELECT id FROM content_summary WHERE uid = ?", (uid,))
    if cur.fetchone():
        return None

    category = classify_one(title, summary)
    if not category:
        print("  ⚠️  分类失败，使用兜底「文章」（source=default）")
    cur.execute(
        "INSERT OR IGNORE INTO content_summary "
        "(title, created_time, summary, original_url, tags, uid, content, category, category_source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            title,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary,
            url,
            tags,
            uid,
            body,
            category or DEFAULT_CATEGORY,
            "llm" if category else "default",
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


def extract_main_text(
    soup: BeautifulSoup,
    *,
    selectors: list[str] | None = None,
) -> str:
    for selector in (selectors or CONTENT_SELECTORS):
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


def extract_title(
    soup: BeautifulSoup,
    url: str,
    *,
    selector: str | None = None,
) -> str:
    if selector:
        el = soup.select_one(selector)
        if el:
            t = el.get_text(strip=True)
            if t:
                return t
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


def _root_config_for(url: str) -> dict:
    """Return the first ROOT_URLS entry whose netloc matches `url`'s netloc.

    Used to inherit per-source extraction overrides (selectors, link_pattern)
    for sub-URLs that don't carry their own config.
    """
    host = _normalize_host(urlparse(url).netloc)
    for r in ROOT_URLS:
        rh = _normalize_host(urlparse(r["url"]).netloc)
        if rh == host:
            return r
    return {}


def fetch_page(url: str, *, root: dict | None = None) -> tuple[str, str, BeautifulSoup] | None:
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

    cfg = root if root is not None else _root_config_for(url)
    title = extract_title(soup, resp.url or url, selector=cfg.get("title_selector"))
    strip_pat = cfg.get("title_strip")
    if strip_pat:
        title = re.sub(strip_pat, "", title).strip()
    content = extract_main_text(soup, selectors=cfg.get("content_selectors"))
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
    # Compare decoded forms too: 特殊:/%E7%89%B9%E6%AE%8A: and %3A-encoded queries
    decoded = unquote(low)
    if SPECIAL_PATH.search(path_low) or SPECIAL_PATH.search(decoded):
        return True
    for frag in SKIP_PATH_FRAGMENTS:
        if frag in path_low or frag in low:
            return True
    query_low = (parsed.query or "").lower()
    for q in SKIP_QUERY_PARAMS:
        if q in query_low or q in decoded:
            return True
    return False


def is_noise_title(title: str) -> bool:
    """True for site-chrome titles: nav / login / listing pages.

    These are never article content even when the page body is long enough to
    pass MIN_CONTENT_LEN (that is how wiki 「所有页面」 and GitHub issue
    listings ended up in the site before the 2026-10 cleanup).
    """
    t = (title or "").strip()
    if not t:
        return True
    if t in TITLE_NOISE_EXACT:
        return True
    if TITLE_NOISE_REGEX.search(t):
        return True
    return any(p in t for p in TITLE_NOISE_PATTERNS)


def discover_suburls(
    root_url: str,
    soup: BeautifulSoup,
    cap: int = MAX_SUBPAGES_PER_ROOT,
    link_pattern: str | None = None,
) -> list[str]:
    """Pull all internal links from `soup`, normalize and dedupe, exclude root.

    `link_pattern`: optional regex string — when set, only links whose absolute
    URL matches `re.search(link_pattern, absolute)` are kept. Use `\\Z` or `$`
    to anchor to end of URL.
    """
    root_norm = root_url.rstrip("/")
    candidates: list[str] = []
    seen: set[str] = set()
    pat = re.compile(link_pattern) if link_pattern else None

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
        if pat and not pat.search(absolute):
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
    update_content: bool = False,
    root: dict | None = None,
) -> bool:
    """Fetch one URL, summarize, insert. Returns True if newly inserted or updated.

    `root`: optional ROOT_URLS entry — when set, its title_selector /
    content_selectors overrides are used for extraction.
    """
    print(f"\n→ {label} {url}")
    page = fetch_page(url, root=root)
    if page is None:
        return False
    title, content, _ = page
    print(f"   title  : {title[:90]}")
    print(f"   chars  : {len(content)}")

    if len(content) < MIN_CONTENT_LEN:
        print(f"   skip   : only {len(content)} chars (below min {MIN_CONTENT_LEN})")
        return False

    if is_noise_title(title):
        print("   skip   : site chrome title (nav / login / listing)")
        return False

    if title_exists(conn, title):
        print("   skip   : same title already in db (mirror / URL variant)")
        return False

    summary = make_summary(title, content)
    row_id = insert_row(conn, url, title, summary, tags, content=content, update_content=update_content)
    if row_id is None:
        print("   skip   : already in db (uid collision)")
        return False
    if update_content:
        print(f"   ✓ updated id={row_id}")
    else:
        print(f"   ✓ saved id={row_id}")
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Crawler — append-only subpage fetcher")
    parser.add_argument(
        "--update-content",
        action="store_true",
        help="When a URL is already in the DB, update only the `content` "
             "column instead of skipping. Useful for refreshing the backup "
             "body without re-running DeepSeek on the summary.",
    )
    args = parser.parse_args()

    load_env(ENV_PATH)

    print("=" * 60)
    print(f"Crawler (subpages) — append-only{' [update-content]' if args.update_content else ''}")
    print("=" * 60)
    print(f"DB: {DB_PATH}  (will append, never wipe)")

    conn = ensure_schema(DB_PATH)
    print("✓ schema verified\n")

    from category_classifier import make_client

    if make_client() is None:
        print("⚠️  未配置 DEEPSEEK_API_KEY 或缺少 openai SDK：新内容将使用「文章」兜底分类")

    grand_inserted = 0
    grand_skipped = 0
    grand_failed = 0

    try:
        for root in ROOT_URLS:
            root_url = root["url"]
            root_tags = root.get("tags", "")

            print(f"\n══════ ROOT  {root_url}  ══════")

            # 1) Insert the root page itself (listing roots set `skip_root`)
            if root.get("skip_root"):
                print("   (listing root — not inserted)")
            else:
                inserted = insert_one(conn, root_url, root_tags, label="ROOT  ", update_content=args.update_content, root=root)
                grand_inserted += int(bool(inserted))
                grand_skipped += int(not inserted)

            # 2) Discover same-domain sub-URLs from the root page
            page = fetch_page(root_url, root=root)
            if page is None:
                grand_failed += 1
                continue
            _title, _content, root_soup = page

            suburls = discover_suburls(
                root_url,
                root_soup,
                link_pattern=root.get("link_pattern"),
            )
            print(f"\n   discovered {len(suburls)} candidate sub-URL(s)")
            sub_tags = root_tags + ",subpage"
            for i, sub_url in enumerate(suburls, 1):
                time.sleep(POLITE_PAUSE)
                ok = insert_one(
                    conn,
                    sub_url,
                    sub_tags,
                    label=f"SUB   [{i:>2}/{len(suburls)}]",
                    update_content=args.update_content,
                    root=root,
                )
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
