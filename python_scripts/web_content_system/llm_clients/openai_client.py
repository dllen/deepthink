"""
OpenAI API client for summary generation.
"""

from typing import Optional
from openai import OpenAI

from .base_client import BaseLLMClient
from ..config import APIConfig


class OpenAIClient(BaseLLMClient):
    """LLM client using OpenAI API."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize OpenAI client.
        
        Args:
            config: API configuration
        """
        self.config = config or APIConfig()
        self.client = None
        
        if self.config.openai_api_key:
            self.client = OpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url
            )
    
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        """
        Generate summary using OpenAI API.
        
        Args:
            content: Full content text
            title: Content title
            
        Returns:
            Generated summary or None on failure
        """
        if not self.client:
            return None
        
        try:
            prompt = self.create_prompt(content, title)
            
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            print(f"⚠️  OpenAI API调用失败: {e}")
            return None
