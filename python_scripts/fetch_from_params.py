#!/usr/bin/env python3
"""
Fetch content from grab_params.json URL entries and add to web_content.db.

Reads `grab_params.json` in the same directory. For every entry with
`done: false`, fetches the page, generates a Chinese summary via DeepSeek
(or Ollama, or a simple extract fallback), and inserts it into
`content_summary` de-duplicated by `uid` (md5 of URL).

Saves back to `grab_params.json`, marking successful entries as `done: true`.

Run: cd python_scripts && python fetch_from_params.py
"""

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DB_PATH = "web_content.db"
PARAMS_PATH = "grab_params.json"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path) -> None:
    """Minimal .env loader (no python-dotenv dependency)."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

MIN_CONTENT_LEN = 80


def ensure_schema(conn):
    """Create content_summary table + uid dedup index if missing."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS content_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_time TEXT NOT NULL,
            summary TEXT NOT NULL,
            original_url TEXT NOT NULL,
            tags TEXT,
            uid TEXT
        )
        """
    )
    cur.execute("PRAGMA table_info(content_summary)")
    cols = [row[1] for row in cur.fetchall()]
    if "uid" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN uid TEXT")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_uid ON content_summary (uid)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags ON content_summary (tags)")
    conn.commit()


def uid_of(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def fetch_content(url: str):
    """Fetch URL and return (title, content) or (None, None) on failure."""
    print(f"  → Fetching: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ✗ HTTP error: {e}")
        return None, None

    # Use apparent_encoding which is more reliable than server's charset
    apparent = resp.apparent_encoding
    if apparent and apparent.lower() not in ("ascii",):
        resp.encoding = apparent
    elif resp.encoding is None:
        resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    article = soup.find("article")
    if article:
        content = article.get_text(separator=" ", strip=True)
    else:
        main = soup.find("main") or soup.find(
            "div", class_=re.compile(r"content|main|article", re.I)
        )
        if main:
            content = main.get_text(separator=" ", strip=True)
        else:
            paragraphs = soup.find_all("p")
            content = " ".join(
                p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20
            )

    content = re.sub(r"\s+", " ", content).strip()

    print(f"  → Title: {title[:80]}")
    print(f"  → Content length: {len(content)} chars")
    return title, content


def generate_summary(title: str, content: str) -> str:
    """Generate Chinese summary using DeepSeek → Ollama → extractive fallback."""
    if not content:
        return "无法获取内容"

    prompt = (
        "请为以下网页内容生成100-200字的中文摘要：\n\n"
        f"标题：{title}\n\n"
        f"内容：{content[:3000]}\n\n"
        "摘要要求：\n- 简洁准确\n- 突出重点\n- 100-200字\n\n摘要："
    )

    # 1. DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5,
            )
            summary = (response.choices[0].message.content or "").strip()
            if summary:
                print(f"  ✓ Summary (DeepSeek): {summary[:80]}...")
                return summary
        except Exception as e:
            print(f"  ⚠ DeepSeek failed: {e}")
    else:
        print("  · DEEPSEEK_API_KEY not set, skipping DeepSeek")

    # 2. Ollama
    ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    try:
        resp = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=60,
        )
        if resp.status_code == 200:
            result = resp.json()
            summary = (result.get("message", {}) or {}).get("content", "").strip()
            if summary:
                print(f"  ✓ Summary (Ollama): {summary[:80]}...")
                return summary
    except Exception as e:
        print(f"  · Ollama not available: {e}")

    # 3. Extractive fallback
    summary = content[:200] + ("..." if len(content) > 200 else "")
    print(f"  · Summary (fallback): {summary[:80]}...")
    return summary


def save_to_db(conn, url: str, title: str, summary: str, tags: str) -> bool:
    """Insert into content_summary, dedup by uid. Returns True if inserted."""
    cur = conn.cursor()
    uid = uid_of(url)
    cur.execute("SELECT id FROM content_summary WHERE uid = ?", (uid,))
    if cur.fetchone():
        print(f"  · Already in DB (uid: {uid}), skipping")
        return False

    created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, created_time, summary, url, tags, uid),
    )
    conn.commit()
    print(f"  ✓ Saved id={cur.lastrowid}")
    return True


def main():
    print("=" * 60)
    print("Fetch URLs from grab_params.json → web_content.db")
    print("=" * 60)
    load_env_file(ENV_PATH)
    if os.getenv("DEEPSEEK_API_KEY"):
        print(f"  · DEEPSEEK_API_KEY loaded (len={len(os.environ['DEEPSEEK_API_KEY'])})")
    else:
        print("  ⚠ DEEPSEEK_API_KEY not set in .env")

    if not os.path.exists(PARAMS_PATH):
        print(f"✗ {PARAMS_PATH} not found")
        return 1

    with open(PARAMS_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        print("✗ grab_params.json must be a list")
        return 1

    pending = [it for it in items if not it.get("done", False)]
    print(f"Total entries: {len(items)}, pending: {len(pending)}")

    if not pending:
        print("Nothing to do.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    inserted = 0
    for i, item in enumerate(pending, start=1):
        url = item.get("url")
        tags = item.get("tags", "")
        if not url:
            print(f"[{i}] ⊘ Skipping entry without url")
            continue
        print(f"\n[{i}/{len(pending)}] {url}")

        title, content = fetch_content(url)
        if not title and not content:
            print(f"  ✗ No content fetched, leaving done=false")
            continue

        # Check if URL is already in DB (regardless of content quality)
        existing_uid = conn.execute(
            "SELECT 1 FROM content_summary WHERE uid = ?", (uid_of(url),)
        ).fetchone()
        if existing_uid:
            print(f"  · Already in DB, marking as done")
            item["done"] = True
            continue

        if not content or len(content) < MIN_CONTENT_LEN:
            print(f"  ⚠ Content too short ({len(content or '')} chars), skipping save")
            continue

        summary = generate_summary(title, content)
        if save_to_db(conn, url, title, summary, tags):
            inserted += 1
            item["done"] = True

    conn.close()

    with open(PARAMS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"\nDone. Inserted {inserted} new rows; updated grab_params.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
