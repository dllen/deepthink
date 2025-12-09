"""
Configuration management for the web content extraction system.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class APIConfig:
    """Configuration for LLM API providers."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"

    # DeepSeek Configuration
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    
    # Local Model Configuration (Ollama)
    ollama_api_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llama2"
    
    # API Settings
    max_tokens: int = 300
    temperature: float = 0.5
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> "APIConfig":
        """Create configuration from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", cls.openai_base_url),
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", cls.deepseek_base_url),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", cls.deepseek_model),
            ollama_api_url=os.getenv("OLLAMA_API_URL", cls.ollama_api_url),
            ollama_model=os.getenv("OLLAMA_MODEL", cls.ollama_model),
        )


@dataclass
class DatabaseConfig:
    """Configuration for database operations."""
    
    db_path: str = "web_content.db"
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables."""
        return cls(
            db_path=os.getenv("DB_PATH", cls.db_path)
        )


@dataclass
class BrowserConfig:
    """Configuration for browser scraping."""
    
    headless: bool = True
    window_size: str = "1920,1080"
    timeout: int = 10
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """Create configuration from environment variables."""
        return cls(
            headless=os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
            window_size=os.getenv("BROWSER_WINDOW_SIZE", cls.window_size),
            timeout=int(os.getenv("BROWSER_TIMEOUT", str(cls.timeout))),
        )


@dataclass
class Config:
    """Main configuration class combining all settings."""
    
    api: APIConfig
    database: DatabaseConfig
    browser: BrowserConfig
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            api=APIConfig.from_env(),
            database=DatabaseConfig.from_env(),
            browser=BrowserConfig.from_env(),
        )
    
    @classmethod
    def default(cls) -> "Config":
        """Create default configuration."""
        return cls(
            api=APIConfig(),
            database=DatabaseConfig(),
            browser=BrowserConfig(),
        )
