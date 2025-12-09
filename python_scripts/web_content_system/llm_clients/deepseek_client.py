"""
DeepSeek API client for summary generation.
"""

from typing import Optional
from openai import OpenAI

from .base_client import BaseLLMClient
from ..config import APIConfig


class DeepSeekClient(BaseLLMClient):
    """LLM client using DeepSeek API."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize DeepSeek client.
        
        Args:
            config: API configuration
        """
        self.config = config or APIConfig()
        self.client = None
        
        if self.config.deepseek_api_key:
            self.client = OpenAI(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url
            )
    
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        """
        Generate summary using DeepSeek API.
        
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
                model=self.config.deepseek_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=False
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            print(f"⚠️  DeepSeek API调用失败: {e}")
            return None
