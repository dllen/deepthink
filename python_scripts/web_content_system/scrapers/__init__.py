"""
Web scraping package.
"""

from .base_scraper import BaseScraper
from .browser_scraper import BrowserScraper
from .requests_scraper import RequestsScraper

__all__ = ["BaseScraper", "BrowserScraper", "RequestsScraper"]
