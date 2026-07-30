#!/usr/bin/env python3
"""
Fetch content from URLs and add to web_content.db
Run: cd python_scripts && python fetch_and_add.py
"""

import sqlite3
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

# Database path
DB_PATH = "web_content.db"

# URLs to fetch
URLS = [
    {
        "url": "https://chuan.us/",
        "tags": "chuan.us"
    },
    {
        "url": "https://www.mywiki.cn/%E7%99%BE%E5%8F%91%E7%99%BE%E4%B8%AD%E7%A9%BF%E5%BF%83%E9%BE%99%E7%88%AA%E6%89%8B/index.php/%E9%A6%96%E9%A1%B5",
        "tags": "百科,百传中穿心龙爪手"
    },
    {
        "url": "https://xiaolai.co/search",
        "tags": "xiaolai,搜索"
    }
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_db_connection():
    """Get database connection with schema setup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_time TEXT NOT NULL,
            summary TEXT NOT NULL,
            original_url TEXT NOT NULL,
            tags TEXT,
            uid TEXT
        )
    ''')
    
    # Ensure uid column exists
    cursor.execute("PRAGMA table_info(content_summary)")
    columns = [row[1] for row in cursor.fetchall()]
    if "uid" not in columns:
        cursor.execute("ALTER TABLE content_summary ADD COLUMN uid TEXT")
    
    # Ensure indexes exist
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_uid ON content_summary (uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON content_summary (tags)')
    
    conn.commit()
    return conn


def generate_uid(url):
    """Generate unique ID from URL."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()


def fetch_content(url):
    """Fetch and extract content from URL."""
    try:
        print(f"Fetching: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        
        # Detect encoding
        if resp.encoding is None:
            resp.encoding = resp.apparent_encoding or 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Remove scripts and styles
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Get title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Get main content
        content = ""
        article = soup.find('article')
        if article:
            content = article.get_text(separator=' ', strip=True)
        else:
            main = soup.find('main') or soup.find('div', class_=re.compile(r'content|main|article', re.I))
            if main:
                content = main.get_text(separator=' ', strip=True)
            else:
                # Get all paragraphs
                paragraphs = soup.find_all('p')
                content = ' '.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        
        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()
        
        print(f"  Title: {title[:80]}")
        print(f"  Content length: {len(content)} chars")
        
        return title, content
        
    except Exception as e:
        print(f"  Error: {e}")
        return None, None


def generate_summary(title, content):
    """Generate summary using available LLM API."""
    if not content:
        return "无法获取内容"
    
    # Try Ollama first (local)
    ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    
    prompt = f"""请为以下网页内容生成100-200字的中文摘要：

标题：{title}

内容：{content[:3000]}

摘要要求：
- 简洁准确
- 突出重点
- 100-200字

摘要："""
    
    # Try Ollama
    try:
        resp = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": "llama3",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=60
        )
        if resp.status_code == 200:
            result = resp.json()
            summary = result.get("message", {}).get("content", "").strip()
            if summary:
                print(f"  Summary (Ollama): {summary[:100]}...")
                return summary
    except Exception as e:
        print(f"  Ollama not available: {e}")
    
    # Try DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5
            )
            summary = response.choices[0].message.content.strip()
            if summary:
                print(f"  Summary (DeepSeek): {summary[:100]}...")
                return summary
        except Exception as e:
            print(f"  DeepSeek not available: {e}")
    
    # Fallback: simple extract
    summary = content[:200] + "..." if len(content) > 200 else content
    print(f"  Summary (fallback): {summary[:100]}...")
    return summary


def save_to_db(conn, url, title, summary, tags):
    """Save content to database."""
    cursor = conn.cursor()
    uid = generate_uid(url)
    created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if already exists
    cursor.execute("SELECT id FROM content_summary WHERE uid = ?", (uid,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"  Already exists, skipping (uid: {uid})")
        return False
    
    cursor.execute('''
        INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, created_time, summary, url, tags, uid))
    
    conn.commit()
    print(f"  Saved to DB: id={cursor.lastrowid}")
    return True


def main():
    print("=" * 50)
    print("Fetch URLs and add to web_content.db")
    print("=" * 50)
    
    conn = get_db_connection()
    
    success_count = 0
    for i, item in enumerate(URLS):
        url = item["url"]
        tags = item["tags"]
        
        print(f"\n[{i + 1}/{len(URLS)}] Processing: {url}")
        
        title, content = fetch_content(url)
        if not title and not content:
            print(f"  Failed to fetch content")
            continue
        
        summary = generate_summary(title, content)
        saved = save_to_db(conn, url, title, summary, tags)
        
        if saved:
            success_count += 1
    
    conn.close()
    
    print("\n" + "=" * 50)
    print(f"Done! Added {success_count}/{len(URLS)} items to database")
    print("=" * 50)


if __name__ == "__main__":
    main()
