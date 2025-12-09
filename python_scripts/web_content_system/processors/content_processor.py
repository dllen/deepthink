"""
Content processor for summary and weibo generation.
"""

from typing import List, Optional

from ..llm_clients import (
    BaseLLMClient,
    OpenAIClient,
    DeepSeekClient,
    LocalModelClient,
    FallbackSummarizer
)
from ..config import APIConfig


class ContentProcessor:
    """Processes content to generate summaries and weibo posts."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize content processor.
        
        Args:
            config: API configuration
        """
        self.config = config or APIConfig()
        self.llm_clients: List[BaseLLMClient] = []
        self._setup_clients()
    
    def _setup_clients(self):
        """Setup LLM clients in priority order."""
        # Add DeepSeek client if API key is available
        if self.config.deepseek_api_key:
            self.llm_clients.append(DeepSeekClient(self.config))

        # Add OpenAI client if API key is available
        if self.config.openai_api_key:
            self.llm_clients.append(OpenAIClient(self.config))
        
        # Add local model client
        self.llm_clients.append(LocalModelClient(self.config))
        
        # Add fallback summarizer (always available)
        self.llm_clients.append(FallbackSummarizer())
    
    def generate_summary(self, content: str, title: str) -> str:
        """
        Generate summary using available LLM clients.
        
        Tries clients in order until one succeeds.
        
        Args:
            content: Full content text
            title: Content title
            
        Returns:
            Generated summary
        """
        for client in self.llm_clients:
            summary = client.generate_summary(content, title)
            if summary:
                return summary
        
        # This should never happen since FallbackSummarizer always returns a result
        return "摘要生成失败"
    
    def generate_weibo_content(self, title: str, summary: str, url: str) -> str:
        """
        Generate weibo post content.
        
        Args:
            title: Content title
            summary: Content summary
            url: Original URL
            
        Returns:
            Formatted weibo content
        """
        # Truncate title and summary to fit weibo constraints
        title_part = title[:20] if len(title) > 20 else title
        summary_part = summary[:80] if len(summary) > 80 else summary
        
        weibo_content = f"【{title_part}】{summary_part} 更多内容: {url}"
        
        # Ensure total length is appropriate for weibo (140 character limit)
        if len(weibo_content) > 140:
            weibo_content = f"【{title_part}】{summary_part[:60]}... 详情: {url}"
        
        return weibo_content
    
    def validate_content(self, content: str, min_length: int = 50) -> bool:
        """
        Validate that content is sufficient for processing.
        
        Args:
            content: Content to validate
            min_length: Minimum acceptable length
            
        Returns:
            True if content is valid
        """
        if not content:
            return False
        
        content = content.strip()
        return len(content) >= min_length
