#!/usr/bin/env python3
"""一次性迁移：加 category 列、补 uid、导入手工内容、回填分类。

默认先备份、再在事务里执行；--dry-run 在临时副本上执行，不改真实 DB。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from category_classifier import CATEGORIES, DEFAULT_CATEGORY, classify_batch

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "web_content.db"
SITE_JS = BASE.parent / "src/assets/static-data.js"
BACKUP_DIR = BASE / "backups"
IMPORT_TIME = "2026-08-28 13:29:02"
BATCH_SIZE = 10


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_site_items(path: Path):
    raw = path.read_text(encoding="utf-8")
    body = re.sub(r"^export default\s*", "", raw.strip()).rstrip(";")
    return json.loads(body)


def ensure_columns(conn) -> list:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    added = []
    if "category" not in columns:
        conn.execute("ALTER TABLE content_summary ADD COLUMN category TEXT")
        added.append("category")
    if "category_source" not in columns:
        conn.execute(
            "ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default'"
        )
        added.append("category_source")
    return added


def backfill_uid(conn) -> int:
    rows = list(
        conn.execute(
            "SELECT id, original_url, title, created_time FROM content_summary "
            "WHERE uid IS NULL OR uid = ''"
        )
    )
    for row_id, url, title, created_time in rows:
        key = url or f"{title}|{created_time}"
        conn.execute("UPDATE content_summary SET uid=? WHERE id=?", (md5(key), row_id))
    return len(rows)


def apply_site_categories(conn, site_items) -> int:
    mapping = {}
    for item in site_items:
        url = item.get("original_url") or ""
        if url and item.get("category") in CATEGORIES:
            mapping.setdefault(url, item)
    updated = 0
    rows = list(conn.execute("SELECT id, original_url FROM content_summary"))
    for row_id, url in rows:
        item = mapping.get(url or "")
        if not item:
            continue
        source = "manual" if item.get("created_time") is None else "legacy-default"
        cur = conn.execute(
            "UPDATE content_summary SET category=?, category_source=? "
            "WHERE id=? AND (category IS NULL OR category='')",
            (item["category"], source, row_id),
        )
        updated += cur.rowcount
    return updated


def insert_manual_items(conn, site_items) -> int:
    existing_urls = {row[0] for row in conn.execute("SELECT original_url FROM content_summary")}
    existing_uids = {row[0] for row in conn.execute("SELECT uid FROM content_summary")}
    inserted = 0
    for item in site_items:
        if item.get("created_time"):  # 旧文（含已从 DB 删除的幽灵行）不补录
            continue
        url = item.get("original_url") or ""
        if not url or url in existing_urls:
            continue
        title = item.get("title") or ""
        uid = md5(url)
        if uid in existing_uids:
            uid = md5(f"{url}|{title}")
        if uid in existing_uids:
            continue
        conn.execute(
            "INSERT INTO content_summary "
            "(title, created_time, summary, original_url, tags, uid, content, category, category_source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                IMPORT_TIME,
                item.get("summary"),
                url,
                item.get("tags"),
                uid,
                None,
                item.get("category") if item.get("category") in CATEGORIES else DEFAULT_CATEGORY,
                "manual",
            ),
        )
        # 不把新 url 加进 existing_urls：同一 URL 的手工内容按 uid/title 区分
        existing_uids.add(uid)
        inserted += 1
    return inserted


def classify_missing(conn, client=None, batch_size: int = BATCH_SIZE):
    rows = list(
        conn.execute(
            "SELECT id, title, summary FROM content_summary "
            "WHERE category IS NULL OR category='' ORDER BY id"
        )
    )
    classified = failed = 0
    for start in range(0, len(rows), batch_size):
        chunk = rows[start : start + batch_size]
        items = [{"title": row[1], "summary": row[2] or ""} for row in chunk]
        categories = classify_batch(items, client=client)
        for (row_id, _, _), category in zip(chunk, categories):
            if category:
                conn.execute(
                    "UPDATE content_summary SET category=?, category_source='llm' WHERE id=?",
                    (category, row_id),
                )
                classified += 1
            else:
                conn.execute(
                    "UPDATE content_summary SET category=?, category_source='default' WHERE id=?",
                    (DEFAULT_CATEGORY, row_id),
                )
                failed += 1
    return classified, failed


def run_migration(db_path, site_js_path, *, skip_llm=False, client=None) -> dict:
    site_items = load_site_items(Path(site_js_path))
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        added = ensure_columns(conn)
        uid_backfilled = backfill_uid(conn)
        updated = apply_site_categories(conn, site_items)
        inserted = insert_manual_items(conn, site_items)
        classified = failed = 0
        if not skip_llm:
            classified, failed = classify_missing(conn, client=client)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    total = conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0]
    coverage = conn.execute(
        "SELECT COUNT(*) FROM content_summary WHERE category IS NOT NULL AND category != ''"
    ).fetchone()[0]
    distribution = dict(
        conn.execute(
            "SELECT COALESCE(category, '(空)'), COUNT(*) FROM content_summary GROUP BY category"
        )
    )
    sources = dict(
        conn.execute(
            "SELECT COALESCE(category_source, '(空)'), COUNT(*) FROM content_summary GROUP BY category_source"
        )
    )
    conn.close()
    return {
        "added_columns": added,
        "uid_backfilled": uid_backfilled,
        "updated_from_site": updated,
        "inserted_manual": inserted,
        "classified": classified,
        "classify_failed": failed,
        "total_rows": total,
        "category_coverage": coverage,
        "distribution": distribution,
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移 DB 到 category 真源模型")
    parser.add_argument("--dry-run", action="store_true", help="在临时副本上执行，不改真实 DB")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 分类")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--site-js", default=str(SITE_JS))
    args = parser.parse_args()

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.dry_run:
        tmp_dir = Path(tempfile.mkdtemp(prefix="deepthink-migrate-"))
        target = tmp_dir / "dryrun.db"
        shutil.copy2(args.db, target)
    else:
        backup = BACKUP_DIR / f"web_content-{stamp}.db"
        shutil.copy2(args.db, backup)
        target = Path(args.db)
        print(f"🗄  备份: {backup}")

    report = run_migration(
        target, Path(args.site_js), skip_llm=args.skip_llm
    )
    report["mode"] = "dry-run" if args.dry_run else "apply"
    report_path = BACKUP_DIR / f"migration-report-{stamp}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"📄 报告: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
