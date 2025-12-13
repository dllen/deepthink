"""
Main web content extractor orchestrator.
"""

from typing import Optional, List, Tuple

from .config import Config
from .database import DatabaseManager
from .scrapers import BrowserScraper, RequestsScraper
from .processors import ContentProcessor


class WebContentExtractor:
    """
    Main orchestrator for web content extraction system.
    
    Coordinates scrapers, processors, and database operations.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize web content extractor.
        
        Args:
            config: System configuration
        """
        self.config = config or Config.from_env()
        
        # Initialize components
        self.db = DatabaseManager(self.config.database.db_path)
        self.browser_scraper = BrowserScraper(self.config.browser)
        self.requests_scraper = RequestsScraper(self.config.browser)
        self.processor = ContentProcessor(self.config.api)
    
    def scrape_and_process(self, url: str, tags: str = "") -> bool:
        """
        Scrape URL, generate summary, and save to database.
        
        Args:
            url: URL to scrape
            tags: Comma-separated tags
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🔍 开始抓取: {url}")
        
        title, content = self.browser_scraper.scrape(url)
        
        if not content or not self.processor.validate_content(content):
            title, content = self.requests_scraper.scrape(url)
        
        if not self.processor.validate_content(content):
            print("❌ 无法抓取到有效内容")
            return False
        
        title = self.processor.generate_title(content)
        print(f"✅ 抓取成功 - 标题: {title[:50]}{'...' if len(title) > 50 else ''}")
        print(f"📊 内容长度: {len(content)} 字符")
        
        # Generate summary
        print("⏳ 正在生成摘要...")
        summary = self.processor.generate_summary(content, title)
        print(f"📋 摘要: {summary}")
        
        # Generate weibo content
        weibo_content = self.processor.generate_weibo_content(title, summary, url)
        print(f"🐦 微博: {weibo_content}")
        
        # Save to database
        self.db.save_content_summary(title, summary, url, tags)
        
        return True
    
    def manual_input(self, title: str, content: str, tags: str = "") -> str:
        """
        Process manually entered content.
        
        Args:
            title: Content title
            content: Full content text
            tags: Comma-separated tags
            
        Returns:
            Generated summary
        """
        title = self.processor.generate_title(content)
        print("⏳ 正在生成摘要...")
        summary = self.processor.generate_summary(content, title)
        
        # Save to database
        self.db.save_manual_content(title, content, summary, tags)
        
        return summary
    
    def view_recent_records(self, limit: int = 10):
        """
        Display recent content summaries.
        
        Args:
            limit: Maximum number of records to display
        """
        results = self.db.get_recent_summaries(limit)
        
        if not results:
            print("暂无抓取记录")
            return
        
        print(f"\n📊 最近{len(results)}条抓取记录:")
        print("=" * 80)
        
        for row in results:
            print(f"ID: {row[0]}")
            print(f"标题: {row[1][:50]}{'...' if len(row[1]) > 50 else ''}")
            print(f"时间: {row[2]}")
            print(f"摘要: {row[3][:100]}{'...' if len(row[3]) > 100 else ''}")
            print(f"URL: {row[4][:50]}{'...' if len(row[4]) > 50 else ''}")
            print(f"标签: {row[5] if row[5] else '无'}")
            print("-" * 80)
    
    def close(self):
        """Close all resources."""
        self.db.close()
        self.browser_scraper.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # Expose database connection for backward compatibility with tests
    @property
    def conn(self):
        """Get database connection."""
        return self.db.conn
