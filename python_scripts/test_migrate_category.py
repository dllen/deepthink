import hashlib
import json
import sqlite3
import sys
from types import SimpleNamespace

import pytest

import migrate_category
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


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_columns(path):
    conn = sqlite3.connect(path)
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    finally:
        conn.close()


def row_count(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0]
    finally:
        conn.close()


def migrated_db(tmp_path):
    """建库并跑一次 skip-llm 迁移，返回 (db, site)；此时「新文」仍为 NULL。"""
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)
    run_migration(db, site, skip_llm=True)
    return db, site


class StubClient:
    """最小 OpenAI 兼容客户端：create() 总是返回同一段 content。"""

    def __init__(self, content):
        self.content = content
        self.calls = 0
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls += 1
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


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
    assert report["allow_fallback"] is False
    assert report["site_legacy_unmatched"] == 0
    conn.close()


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)

    first = run_migration(db, site, skip_llm=True)
    second = run_migration(db, site, skip_llm=True)
    assert first["inserted_manual"] == 1
    assert second["added_columns"] == []
    assert second["uid_backfilled"] == 0
    assert second["updated_from_site"] == 0
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


def test_rollback_on_failure(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)
    before = row_count(db)

    def boom(*args, **kwargs):
        raise RuntimeError("classify exploded")

    monkeypatch.setattr(migrate_category, "classify_missing", boom)

    with pytest.raises(RuntimeError):
        migrate_category.run_migration(db, site, skip_llm=False)

    assert table_columns(db).isdisjoint({"category", "category_source"})
    assert row_count(db) == before == 2


def test_dry_run_leaves_db_untouched(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)
    backups = tmp_path / "backups"
    monkeypatch.setattr(migrate_category, "BACKUP_DIR", backups)
    before = sha256(db)

    monkeypatch.setattr(sys, "argv", [
        "migrate_category.py", "--dry-run", "--skip-llm",
        "--db", str(db), "--site-js", str(site),
    ])
    assert migrate_category.main() == 0

    assert sha256(db) == before
    report_files = list(backups.glob("migration-report-*.json"))
    assert len(report_files) == 1
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["allow_fallback"] is False


def test_classify_missing_success_with_stub_client(tmp_path):
    db, _ = migrated_db(tmp_path)
    client = StubClient('[{"index": 0, "category": "科技动态"}]')

    conn = sqlite3.connect(db)
    classified, failed = migrate_category.classify_missing(conn, client=client)
    conn.commit()
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/new'"
    ).fetchone()
    conn.close()

    assert (classified, failed) == (1, 0)
    assert row == ("科技动态", "llm")
    assert client.calls == 1


def test_classify_missing_failure_keeps_null(tmp_path):
    db, _ = migrated_db(tmp_path)
    client = StubClient("这不是 JSON")

    conn = sqlite3.connect(db)
    classified, failed = migrate_category.classify_missing(conn, client=client)
    conn.commit()
    row = conn.execute(
        "SELECT category FROM content_summary WHERE original_url='https://e.com/new'"
    ).fetchone()
    conn.close()

    assert classified == 0
    assert failed > 0
    assert row[0] is None
    assert client.calls == 2  # 整批失败后重试了一次


def test_classify_missing_allow_fallback(tmp_path):
    db, _ = migrated_db(tmp_path)
    client = StubClient("这不是 JSON")

    conn = sqlite3.connect(db)
    classified, failed = migrate_category.classify_missing(
        conn, client=client, allow_fallback=True
    )
    conn.commit()
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/new'"
    ).fetchone()
    conn.close()

    assert classified == 0
    assert failed > 0
    assert row == (migrate_category.DEFAULT_CATEGORY, "default")
    assert row[0] == "文章"


def test_main_returns_2_on_classify_failure(tmp_path, monkeypatch, capsys):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)
    monkeypatch.setattr(migrate_category, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(
        migrate_category, "classify_batch",
        lambda items, client=None: [None] * len(items),
    )
    monkeypatch.setattr(sys, "argv", [
        "migrate_category.py", "--db", str(db), "--site-js", str(site),
    ])

    assert migrate_category.main() == 2

    captured = capsys.readouterr()
    assert "分类失败" in captured.err
    assert "NULL" in captured.err
    assert "--allow-fallback" in captured.err
    # 失败行没有被写成兜底分类
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT category FROM content_summary WHERE original_url='https://e.com/new'"
    ).fetchone()
    conn.close()
    assert row[0] is None


def test_main_returns_1_for_missing_files(tmp_path, monkeypatch, capsys):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    monkeypatch.setattr(migrate_category, "BACKUP_DIR", tmp_path / "backups")

    # DB 不存在
    monkeypatch.setattr(sys, "argv", [
        "migrate_category.py", "--db", str(db), "--site-js", str(site),
    ])
    assert migrate_category.main() == 1
    err = capsys.readouterr().err
    assert "--db" in err and str(db) in err

    # DB 存在但站点文件不存在
    make_db(db)
    monkeypatch.setattr(sys, "argv", [
        "migrate_category.py", "--db", str(db), "--site-js", str(site),
    ])
    assert migrate_category.main() == 1
    err = capsys.readouterr().err
    assert "--site-js" in err and str(site) in err


def test_does_not_overwrite_manual_category(tmp_path):
    db, site = migrated_db(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE content_summary SET category='工具', category_source='manual' "
        "WHERE original_url='https://e.com/legacy'"
    )
    conn.commit()
    conn.close()

    items = [{
        "id": 1, "title": "旧文", "created_time": "2026-07-30 20:14:39",
        "summary": "摘要", "original_url": "https://e.com/legacy",
        "tags": "AI", "category": "文章",
    }]
    site.write_text("export default " + json.dumps(items) + ";", encoding="utf-8")

    report = run_migration(db, site, skip_llm=True)
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT category, category_source FROM content_summary "
        "WHERE original_url='https://e.com/legacy'"
    ).fetchone()
    conn.close()

    assert report["updated_from_site"] == 0
    assert row == ("工具", "manual")
