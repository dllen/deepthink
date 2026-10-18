import json
import sqlite3

from migrate_category import run_migration

SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT, tags TEXT, uid TEXT, content TEXT
);
CREATE UNIQUE INDEX idx_uid ON content_summary (uid);
"""


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid) "
        "VALUES ('旧文', '2026-07-30 20:14:39', '摘要', 'https://e.com/legacy', 'AI', NULL)"
    )
    conn.execute(
        "INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid) "
        "VALUES ('新文', '2026-08-28 13:22:58', '摘要', 'https://e.com/new', 'AI', 'x')"
    )
    conn.commit()
    conn.close()


def write_site_js(path):
    items = [
        {   # 命中 DB 的旧文
            "id": 1, "title": "旧文", "created_time": "2026-07-30 20:14:39",
            "summary": "摘要", "original_url": "https://e.com/legacy",
            "tags": "AI", "category": "工具",
        },
        {   # 只在站点里的手工内容
            "id": 172, "title": "手工", "created_time": None,
            "summary": "摘要", "original_url": "https://e.com/manual",
            "tags": "观点", "category": "言论",
        },
    ]
    path.write_text("export default " + json.dumps(items) + ";", encoding="utf-8")


def test_migration_adds_columns_and_rows(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)

    report = run_migration(db, site, skip_llm=True)
    conn = sqlite3.connect(db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    assert {"category", "category_source"} <= columns
    assert conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0] == 3
    legacy = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/legacy'"
    ).fetchone()
    assert legacy == ("工具", "legacy-default")
    manual = conn.execute(
        "SELECT category, category_source, created_time FROM content_summary "
        "WHERE original_url='https://e.com/manual'"
    ).fetchone()
    assert manual == ("言论", "manual", "2026-08-28 13:29:02")
    assert report["inserted_manual"] == 1
    assert report["updated_from_site"] == 1
    assert report["uid_backfilled"] == 1
    assert report["category_coverage"] == 2  # skip_llm 时“新文”仍为空
    assert report["total_rows"] == 3
    conn.close()


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)

    first = run_migration(db, site, skip_llm=True)
    second = run_migration(db, site, skip_llm=True)
    assert first["inserted_manual"] == 1
    assert second["inserted_manual"] == 0
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0] == 3
    conn.close()


def test_migration_dedupes_duplicate_url_by_title(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    items = [
        {
            "title": "同一期 A", "created_time": None, "summary": "s",
            "original_url": "https://e.com/issue", "tags": "t", "category": "文章",
        },
        {
            "title": "同一期 B", "created_time": None, "summary": "s",
            "original_url": "https://e.com/issue", "tags": "t", "category": "言论",
        },
    ]
    site.write_text("export default " + json.dumps(items) + ";", encoding="utf-8")

    report = run_migration(db, site, skip_llm=True)
    assert report["inserted_manual"] == 2
    conn = sqlite3.connect(db)
    uids = [row[0] for row in conn.execute(
        "SELECT uid FROM content_summary WHERE original_url='https://e.com/issue' ORDER BY id"
    )]
    assert len(uids) == 2 and len(set(uids)) == 2
    conn.close()
