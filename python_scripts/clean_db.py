import os
import argparse
import sqlite3
from pathlib import Path

def get_default_db_path():
    base = Path(__file__).parent
    return str(base / "web_content.db")

def truncate_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='content_summary'")
    has_summary = cur.fetchone()[0] > 0
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='manual_content'")
    has_manual = cur.fetchone()[0] > 0
    before_summary = 0
    before_manual = 0
    if has_summary:
        cur.execute("SELECT COUNT(*) FROM content_summary")
        before_summary = cur.fetchone()[0]
    if has_manual:
        cur.execute("SELECT COUNT(*) FROM manual_content")
        before_manual = cur.fetchone()[0]
    if has_summary:
        cur.execute("DELETE FROM content_summary")
    if has_manual:
        cur.execute("DELETE FROM manual_content")
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    return before_summary, before_manual

def main():
    parser = argparse.ArgumentParser(prog="clean_db", description="清理 SQLite 数据库内容")
    parser.add_argument("--db", help="数据库路径，默认使用 python_scripts/web_content.db")
    parser.add_argument("--hard", action="store_true", help="硬清理：删除数据库文件")
    parser.add_argument("--also-enc", action="store_true", help="在硬清理时同时删除加密文件 web_content.db.enc")
    parser.add_argument("--dry-run", action="store_true", help="试运行：仅显示将删除的记录数量，不执行删除")
    args = parser.parse_args()

    db_path = args.db or os.getenv("DB_PATH") or get_default_db_path()
    enc_path = str(Path(db_path).with_suffix(".db.enc")) if db_path.endswith(".db") else str(Path(db_path).parent / "web_content.db.enc")

    if args.hard:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ 已删除数据库文件: {db_path}")
        else:
            print(f"ℹ️ 数据库文件不存在: {db_path}")
        if args.also_enc:
            if os.path.exists(enc_path):
                os.remove(enc_path)
                print(f"✅ 已删除加密文件: {enc_path}")
            else:
                print(f"ℹ️ 加密文件不存在: {enc_path}")
        return

    if not os.path.exists(db_path):
        print(f"❌ 未找到数据库文件: {db_path}")
        print("请先创建或解密数据库后再执行清理")
        return

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='content_summary'")
        has_summary = cur.fetchone()[0] > 0
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='manual_content'")
        has_manual = cur.fetchone()[0] > 0
        count_summary = 0
        count_manual = 0
        if has_summary:
            cur.execute("SELECT COUNT(*) FROM content_summary")
            count_summary = cur.fetchone()[0]
        if has_manual:
            cur.execute("SELECT COUNT(*) FROM manual_content")
            count_manual = cur.fetchone()[0]
        print(f"📊 待删除记录数: content_summary={count_summary}, manual_content={count_manual}")
        if args.dry_run:
            print("🔎 试运行模式：未执行删除")
            return
        before_summary, before_manual = truncate_tables(conn)
        print(f"✅ 已清理记录: content_summary={before_summary}, manual_content={before_manual}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

