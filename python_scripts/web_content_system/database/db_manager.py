import hashlib
import sqlite3
from datetime import datetime
from typing import List, Tuple


class DatabaseManager:
    """Manages all database operations for the web content extraction system."""
    
    def __init__(self, db_path: str = "web_content.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._setup_database()
    
    def _setup_database(self):
        """Create database connection and tables."""
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
    
    def _create_tables(self):
        """Create or migrate necessary database tables."""
        cursor = self.conn.cursor()
        
        # Ensure table exists with baseline columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_time TEXT NOT NULL,
                summary TEXT NOT NULL,
                original_url TEXT NOT NULL,
                tags TEXT
            )
        ''')
        
        # Migrate: add uid column if missing
        cursor.execute("PRAGMA table_info(content_summary)")
        columns = [row[1] for row in cursor.fetchall()]
        if "uid" not in columns:
            cursor.execute("ALTER TABLE content_summary ADD COLUMN uid TEXT")
        
        # Create unique index on uid
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_uid ON content_summary (uid)')
        
        # Create index on tags
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON content_summary (tags)')
        
        # Backfill uid for existing rows where missing
        cursor.execute("SELECT id, original_url FROM content_summary WHERE uid IS NULL OR uid = ''")
        rows = cursor.fetchall()
        for rid, orig_url in rows:
            if orig_url:
                uid = hashlib.md5(orig_url.encode('utf-8')).hexdigest()
                cursor.execute("UPDATE content_summary SET uid = ? WHERE id = ?", (uid, rid))
        
        # Deduplicate by uid keeping the latest id
        cursor.execute("""
            SELECT uid, MAX(id) AS keep_id
            FROM content_summary
            WHERE uid IS NOT NULL AND uid <> ''
            GROUP BY uid
        """)
        keep_map = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("""
            SELECT id, uid FROM content_summary
            WHERE uid IS NOT NULL AND uid <> ''
        """)
        to_delete = []
        for rid, uid in cursor.fetchall():
            if uid in keep_map and rid != keep_map[uid]:
                to_delete.append(rid)
        if to_delete:
            cursor.executemany("DELETE FROM content_summary WHERE id = ?", [(rid,) for rid in to_delete])
        
        # Create manual_content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manual_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_time TEXT NOT NULL,
                summary TEXT,
                tags TEXT
            )
        ''')
        
        self.conn.commit()
    
    def save_content_summary(
        self, 
        title: str, 
        summary: str, 
        url: str, 
        tags: str = ""
    ) -> int:
        """
        Save content summary to database with upsert on uid (md5 of URL).
        
        Args:
            title: Content title
            summary: Generated summary
            url: Original URL
            tags: Comma-separated tags
            
        Returns:
            ID of inserted record
        """
        cursor = self.conn.cursor()
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        uid = hashlib.md5((url or "").encode('utf-8')).hexdigest()
        
        cursor.execute('''
            INSERT INTO content_summary (uid, title, created_time, summary, original_url, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET
              title=excluded.title,
              created_time=excluded.created_time,
              summary=excluded.summary,
              original_url=excluded.original_url,
              tags=excluded.tags
        ''', (uid, title, created_time, summary, url, tags))
        
        self.conn.commit()
        
        # Return the id of the affected row
        cursor.execute("SELECT id FROM content_summary WHERE uid = ?", (uid,))
        row = cursor.fetchone()
        return row[0] if row else cursor.lastrowid
    
    def save_manual_content(
        self,
        title: str,
        content: str,
        summary: str,
        tags: str = ""
    ) -> int:
        """
        Save manually entered content to database.
        
        Args:
            title: Content title
            content: Full content text
            summary: Generated summary
            tags: Comma-separated tags
            
        Returns:
            ID of inserted record
        """
        cursor = self.conn.cursor()
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO manual_content (title, content, created_time, summary, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, created_time, summary, tags))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recent_summaries(self, limit: int = 10) -> List[Tuple]:
        """
        Get recent content summaries.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of tuples containing record data
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM content_summary ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()
    
    def get_recent_manual_content(self, limit: int = 10) -> List[Tuple]:
        """
        Get recent manual content entries.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of tuples containing record data
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM manual_content ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()
    
    def search_by_tags(self, tags: str) -> List[Tuple]:
        """
        Search content by tags.
        
        Args:
            tags: Tags to search for
            
        Returns:
            List of matching records
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM content_summary WHERE tags LIKE ? ORDER BY id DESC",
            (f"%{tags}%",)
        )
        return cursor.fetchall()
    
    def get_table_info(self, table_name: str) -> List[Tuple]:
        """
        Get table schema information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information
        """
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
