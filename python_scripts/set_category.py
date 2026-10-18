#!/usr/bin/env python3
"""人工修正单条内容的七分类。"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from category_classifier import CATEGORIES

DB_PATH = Path(__file__).resolve().parent / "web_content.db"

_DB_ERROR_HINT = "（是否已运行 migrate_category.py？DB 是否被占用？）"


def update_category(conn, category, *, url=None, row_id=None):
    if (url is None) == (row_id is None):
        raise ValueError("必须且只能指定 url 或 row_id 之一")
    if category not in CATEGORIES:
        raise ValueError(f"非法分类: {category}，可选：{'、'.join(CATEGORIES)}")
    if row_id is not None:
        rows = list(conn.execute("SELECT id FROM content_summary WHERE id=?", (row_id,)))
    else:
        rows = list(
            conn.execute(
                "SELECT id FROM content_summary WHERE original_url=?", (url,)
            )
        )
    if not rows:
        raise LookupError(f"找不到对应行（url={url} id={row_id}）")
    if len(rows) > 1:
        ids = [row[0] for row in rows]
        raise LookupError(f"匹配到 {len(ids)} 行: {ids}，请用 --id 指定")
    target = rows[0][0]
    conn.execute(
        "UPDATE content_summary SET category=?, category_source='manual' WHERE id=?",
        (category, target),
    )
    conn.commit()
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="人工修正一条内容的分类",
        epilog="示例: python3 set_category.py --url https://example.com/post 工具",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="按 original_url 定位")
    group.add_argument("--id", type=int, help="按 id 定位")
    parser.add_argument("category", help=f"七类之一：{'、'.join(CATEGORIES)}")
    args = parser.parse_args()

    if not DB_PATH.is_file():
        print(f"❌ 数据库不存在: {DB_PATH}", file=sys.stderr)
        return 1

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        row_id = update_category(
            conn, args.category, url=args.url, row_id=args.id
        )
        row = conn.execute(
            "SELECT title FROM content_summary WHERE id=?", (row_id,)
        ).fetchone()
        title = row[0] if row else None
    except (ValueError, LookupError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"❌ 数据库操作失败: {exc}{_DB_ERROR_HINT}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()

    label = f"「{title}」" if title else ""
    print(f"✅ id={row_id}{label} → {args.category} (source=manual)")
    print("   记得运行: npm run gen:static-js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
