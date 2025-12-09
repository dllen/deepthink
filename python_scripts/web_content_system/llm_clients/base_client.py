"""
Base LLM client interface.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        """
        Generate summary from content.
        
        Args:
            content: Full content text
            title: Content title
            
        Returns:
            Generated summary or None on failure
        """
        pass
    
    @staticmethod
    def create_prompt(content: str, title: str, max_content_length: int = 3000) -> str:
        """
        Create standard prompt for summary generation.
        
        Args:
            content: Full content text
            title: Content title
            max_content_length: Maximum content length to include
            
        Returns:
            Formatted prompt
        """
        truncated_content = content[:max_content_length]
        
        return f"""请为以下文章生成一个简洁准确的摘要，字数在100-200字之间：

文章标题: {title}

文章内容: {truncated_content}

请生成摘要:"""
