"""
Requests-based web scraper using BeautifulSoup.
"""

import re
from typing import Tuple, Optional
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..config import BrowserConfig


class RequestsScraper(BaseScraper):
    """Web scraper using requests and BeautifulSoup."""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize requests scraper.
        
        Args:
            config: Browser configuration (for user agent)
        """
        self.config = config or BrowserConfig()
    
    def scrape(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape content from URL using requests.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (title, content) or (None, None) on failure
        """
        try:
            headers = {
                'User-Agent': self.config.user_agent
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else "无标题"
            
            # Extract content
            content = self._extract_content(soup)
            
            return self.clean_title(title), self.clean_content(content)
            
        except Exception as e:
            print(f"⚠️  Requests抓取失败: {e}")
            return "抓取失败", "无法获取页面内容"
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract content from BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            Extracted content text
        """
        # Strategy 1: Look for article tag
        article_content = soup.find('article')
        if article_content:
            return article_content.get_text()
        
        # Strategy 2: Look for main content area
        main_content = (
            soup.find('main') or
            soup.find('div', class_=re.compile(r'article|content|main|post|entry')) or
            soup.find('section', class_=re.compile(r'article|content|main|post|entry'))
        )
        if main_content:
            return main_content.get_text()
        
        # Strategy 3: Get all paragraphs
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
        
        return content if content else soup.get_text()
