import sqlite3
import sys
from pathlib import Path

import pytest

import set_category
from set_category import update_category

REAL_DB = Path(set_category.__file__).resolve().parent / "web_content.db"


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


def make_db_file(path, *, with_table=True, with_category=True):
    """在磁盘上建一个临时库，用于测试 main() 的各类错误路径。"""
    conn = sqlite3.connect(path)
    if with_table:
        extra = ", category TEXT, category_source TEXT" if with_category else ""
        conn.execute(
            "CREATE TABLE content_summary ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, original_url TEXT"
            f"{extra})"
        )
        conn.execute(
            "INSERT INTO content_summary (title, original_url) "
            "VALUES ('t1', 'https://e.com/1')"
        )
    conn.commit()
    conn.close()


def fetch_row(path, row_id=1):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(
            "SELECT category, category_source FROM content_summary WHERE id=?",
            (row_id,),
        ).fetchone()
    finally:
        conn.close()


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


def test_rejects_url_and_row_id_together():
    conn = make_db()
    with pytest.raises(ValueError, match="必须且只能"):
        update_category(conn, "工具", url="https://e.com/1", row_id=1)


def test_rejects_neither_url_nor_row_id():
    conn = make_db()
    with pytest.raises(ValueError, match="必须且只能"):
        update_category(conn, "工具")


def test_invalid_category_leaves_db_untouched():
    conn = make_db()
    before = conn.execute(
        "SELECT id, category, category_source FROM content_summary ORDER BY id"
    ).fetchall()
    with pytest.raises(ValueError):
        update_category(conn, "随笔", row_id=1)
    after = conn.execute(
        "SELECT id, category, category_source FROM content_summary ORDER BY id"
    ).fetchall()
    assert after == before


def test_main_success_updates_db(tmp_path, monkeypatch, capsys):
    db = tmp_path / "web_content.db"
    make_db_file(db)
    monkeypatch.setattr(set_category, "DB_PATH", db)
    monkeypatch.setattr(
        sys, "argv", ["set_category.py", "--url", "https://e.com/1", "工具"]
    )

    assert set_category.main() == 0
    assert fetch_row(db) == ("工具", "manual")
    out = capsys.readouterr().out
    assert "id=1" in out and "t1" in out and "工具" in out


def test_main_missing_db_returns_1_without_creating_file(
    tmp_path, monkeypatch, capsys
):
    db = tmp_path / "missing.db"
    monkeypatch.setattr(set_category, "DB_PATH", db)
    monkeypatch.setattr(
        sys, "argv", ["set_category.py", "--id", "1", "工具"]
    )

    assert set_category.main() == 1
    assert not db.exists()
    assert "数据库不存在" in capsys.readouterr().err


def test_main_missing_table_returns_1(tmp_path, monkeypatch, capsys):
    db = tmp_path / "web_content.db"
    make_db_file(db, with_table=False)
    monkeypatch.setattr(set_category, "DB_PATH", db)
    monkeypatch.setattr(
        sys, "argv", ["set_category.py", "--id", "1", "工具"]
    )

    assert set_category.main() == 1
    err = capsys.readouterr().err
    assert "数据库操作失败" in err
    assert "Traceback" not in err


def test_main_missing_category_column_returns_1(tmp_path, monkeypatch, capsys):
    db = tmp_path / "web_content.db"
    make_db_file(db, with_category=False)
    monkeypatch.setattr(set_category, "DB_PATH", db)
    monkeypatch.setattr(
        sys, "argv", ["set_category.py", "--id", "1", "工具"]
    )

    assert set_category.main() == 1
    err = capsys.readouterr().err
    assert "数据库操作失败" in err
    assert "Traceback" not in err


def test_real_db_schema_has_category_columns():
    if not REAL_DB.is_file():
        pytest.skip("真实数据库不存在，跳过 schema 检查")
    conn = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    try:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(content_summary)").fetchall()
        }
    finally:
        conn.close()
    if "category" not in cols:
        pytest.skip("迁移尚未执行：category 列不存在")
    assert {"category", "category_source"} <= cols
