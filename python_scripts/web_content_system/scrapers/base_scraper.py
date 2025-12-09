"""
Base scraper interface.
"""

import re
from abc import ABC, abstractmethod
from typing import Tuple, Optional


class BaseScraper(ABC):
    """Abstract base class for web scrapers."""
    
    @abstractmethod
    def scrape(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape content from a URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (title, content) or (None, None) on failure
        """
        pass
    
    @staticmethod
    def clean_content(content: str) -> str:
        """
        Clean extracted content.
        
        Args:
            content: Raw content text
            
        Returns:
            Cleaned content
        """
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove leading/trailing whitespace
        content = content.strip()
        return content
    
    @staticmethod
    def clean_title(title: str) -> str:
        """
        Clean extracted title.
        
        Args:
            title: Raw title text
            
        Returns:
            Cleaned title
        """
        return title.strip() if title else "无标题"
