import sqlite3

import pytest

from set_category import update_category


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE content_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, created_time TEXT, summary TEXT,
            original_url TEXT, tags TEXT, uid TEXT,
            content TEXT, category TEXT, category_source TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO content_summary (title, original_url, category, category_source) "
        "VALUES ('t1', 'https://e.com/1', NULL, NULL)"
    )
    conn.execute(
        "INSERT INTO content_summary (title, original_url, category, category_source) "
        "VALUES ('t2', 'https://e.com/2', '文章', 'legacy-default')"
    )
    conn.commit()
    return conn


def test_update_by_url_sets_manual():
    conn = make_db()
    row_id = update_category(conn, "工具", url="https://e.com/1")
    assert row_id == 1
    assert conn.execute(
        "SELECT category, category_source FROM content_summary WHERE id=1"
    ).fetchone() == ("工具", "manual")


def test_update_by_id():
    conn = make_db()
    update_category(conn, "言论", row_id=2)
    assert conn.execute(
        "SELECT category, category_source FROM content_summary WHERE id=2"
    ).fetchone() == ("言论", "manual")


def test_rejects_invalid_category():
    conn = make_db()
    with pytest.raises(ValueError):
        update_category(conn, "随笔", row_id=1)


def test_missing_row_raises():
    conn = make_db()
    with pytest.raises(LookupError):
        update_category(conn, "工具", url="https://e.com/nope")


def test_ambiguous_url_raises():
    conn = make_db()
    conn.execute(
        "INSERT INTO content_summary (title, original_url) VALUES ('dup', 'https://e.com/1')"
    )
    conn.commit()
    with pytest.raises(LookupError):
        update_category(conn, "工具", url="https://e.com/1")
