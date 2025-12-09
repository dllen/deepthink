"""
Local model API client (e.g., Ollama).
"""

from typing import Optional
import requests

from .base_client import BaseLLMClient
from ..config import APIConfig


class LocalModelClient(BaseLLMClient):
    """LLM client using local model APIs like Ollama."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        Initialize local model client.
        
        Args:
            config: API configuration
        """
        self.config = config or APIConfig()
    
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        """
        Generate summary using local model API.
        
        Args:
            content: Full content text
            title: Content title
            
        Returns:
            Generated summary or None on failure
        """
        try:
            prompt = self.create_prompt(content, title)
            
            data = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(
                self.config.ollama_api_url,
                json=data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get("response", "").strip()
                return summary if summary else None
            else:
                print(f"⚠️  本地模型API返回错误: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️  本地模型API调用失败: {e}")
            return None
