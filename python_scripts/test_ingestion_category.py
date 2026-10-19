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

# Pre-category schema: no `category` / `category_source` columns yet.
OLD_SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT UNIQUE, tags TEXT, uid TEXT UNIQUE, content TEXT
);
"""

# Even older table: no uid / content either (crawler upgrader must ALTER first,
# then create the uid index — CREATE INDEX before the ALTER used to fail).
LEGACY_SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT UNIQUE, tags TEXT
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


def test_crawler_duplicate_url_does_not_classify():
    conn = make_db()
    url = "https://e.com/dup"
    with patch.object(crawler_subpages, "classify_one", return_value="工具"):
        first = crawler_subpages.insert_row(conn, url, "标题", "摘要", "AI", "正文")
    assert first is not None

    with patch.object(
        crawler_subpages,
        "classify_one",
        side_effect=AssertionError("should not classify"),
    ):
        second = crawler_subpages.insert_row(conn, url, "标题", "摘要", "AI", "正文")

    assert second is None
    count = conn.execute(
        "SELECT COUNT(*) FROM content_summary WHERE original_url=?", (url,)
    ).fetchone()[0]
    assert count == 1


def test_crawler_fallback_when_classifier_returns_none(capsys):
    conn = make_db()
    with patch.object(crawler_subpages, "classify_one", return_value=None):
        row_id = crawler_subpages.insert_row(
            conn, "https://e.com/6", "标题", "摘要", "AI", "正文"
        )
    assert row_id is not None
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/6'"
    ).fetchone()
    assert row == ("文章", "default")
    assert "分类失败" in capsys.readouterr().out


def test_fetch_ensure_schema_adds_category_columns():
    conn = sqlite3.connect(":memory:")
    conn.executescript(OLD_SCHEMA)

    fetch_from_params.ensure_schema(conn)

    cols = {row[1]: row[4] for row in conn.execute("PRAGMA table_info(content_summary)")}
    assert "category" in cols
    assert "category_source" in cols
    assert cols["category_source"] == "'default'"


def test_crawler_ensure_schema_adds_category_columns(tmp_path):
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_SCHEMA)
    conn.commit()
    conn.close()

    conn = crawler_subpages.ensure_schema(db_path)

    cols = {row[1]: row[4] for row in conn.execute("PRAGMA table_info(content_summary)")}
    assert "category" in cols
    assert "category_source" in cols
    assert cols["category_source"] == "'default'"
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(content_summary)")}
    assert {"idx_uid", "idx_tags"} <= indexes


def test_crawler_ensure_schema_upgrades_table_without_uid(tmp_path):
    """M2: indexes are created after the ALTERs, so a pre-uid DB upgrades."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(LEGACY_SCHEMA)
    conn.commit()
    conn.close()

    conn = crawler_subpages.ensure_schema(db_path)

    cols = {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    assert {"uid", "content", "category", "category_source"} <= cols
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(content_summary)")}
    assert {"idx_uid", "idx_tags"} <= indexes
