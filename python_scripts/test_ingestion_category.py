import sqlite3
from unittest.mock import patch

import fetch_from_params
import crawler_subpages

SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT UNIQUE, tags TEXT, uid TEXT UNIQUE, content TEXT,
    category TEXT, category_source TEXT
);
"""


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    return conn


def test_save_to_db_writes_llm_category():
    conn = make_db()
    with patch.object(fetch_from_params, "classify_one", return_value="工具"):
        inserted = fetch_from_params.save_to_db(
            conn, "https://e.com/1", "标题", "摘要", "AI", "正文"
        )
    assert inserted is True
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/1'"
    ).fetchone()
    assert row == ("工具", "llm")


def test_save_to_db_falls_back_to_default():
    conn = make_db()
    with patch.object(fetch_from_params, "classify_one", return_value=None):
        fetch_from_params.save_to_db(
            conn, "https://e.com/2", "标题", "摘要", "AI", "正文"
        )
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/2'"
    ).fetchone()
    assert row == ("文章", "default")


def test_crawler_insert_row_writes_llm_category():
    conn = make_db()
    with patch.object(crawler_subpages, "classify_one", return_value="言论"):
        crawler_subpages.insert_row(
            conn, "https://e.com/3", "标题", "摘要", "AI", "正文"
        )
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/3'"
    ).fetchone()
    assert row == ("言论", "llm")
