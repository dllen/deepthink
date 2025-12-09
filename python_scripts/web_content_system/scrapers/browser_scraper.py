"""
Browser-based web scraper using Selenium.
"""

from typing import Tuple, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper
from ..config import BrowserConfig


class BrowserScraper(BaseScraper):
    """Web scraper using Selenium WebDriver."""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize browser scraper.
        
        Args:
            config: Browser configuration
        """
        self.config = config or BrowserConfig()
        self.driver = None
        self._setup_browser()
    
    def _setup_browser(self):
        """Setup Chrome WebDriver with options."""
        chrome_options = Options()
        
        if self.config.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--window-size={self.config.window_size}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Hide webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception as e:
            print(f"⚠️  无法启动Chrome浏览器: {e}")
            print("请确保已安装Chrome浏览器和ChromeDriver")
            self.driver = None
    
    def scrape(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape content from URL using browser.
        
        Args:
            url: URL to scrape
            
        Returns:
            Tuple of (title, content) or (None, None) on failure
        """
        if not self.driver:
            return None, None
        
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.config.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page title
            title = self.driver.title
            
            # Extract content using multiple strategies
            content = self._extract_content()
            
            return self.clean_title(title), self.clean_content(content)
            
        except Exception as e:
            print(f"⚠️  浏览器抓取失败: {e}")
            return None, None
    
    def _extract_content(self) -> str:
        """
        Extract content from page using multiple strategies.
        
        Returns:
            Extracted content text
        """
        content = ""
        
        # Strategy 1: Look for article tags
        article_elements = self.driver.find_elements(By.TAG_NAME, "article")
        if article_elements:
            content = " ".join([elem.text for elem in article_elements])
            if len(content) > 100:
                return content
        
        # Strategy 2: Look for main content area
        main_elements = self.driver.find_elements(By.TAG_NAME, "main")
        if main_elements:
            content = main_elements[0].text
            if len(content) > 100:
                return content
        
        # Strategy 3: Look for content-related divs
        content_divs = self.driver.find_elements(
            By.CSS_SELECTOR,
            "div[class*='content'], div[class*='article'], "
            "div[class*='post'], div[class*='main']"
        )
        if content_divs:
            content = " ".join([elem.text for elem in content_divs])
            if len(content) > 100:
                return content
        
        # Strategy 4: Get all paragraphs
        p_elements = self.driver.find_elements(By.TAG_NAME, "p")
        content = " ".join([p.text for p in p_elements if len(p.text) > 20])
        if len(content) > 100:
            return content
        
        # Strategy 5: Fallback to body
        body_element = self.driver.find_element(By.TAG_NAME, "body")
        return body_element.text
    
    def close(self):
        """Close browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
