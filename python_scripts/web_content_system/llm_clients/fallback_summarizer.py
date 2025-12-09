"""
Fallback summarizer using simple extractive methods.
"""

from typing import Optional

from .base_client import BaseLLMClient


class FallbackSummarizer(BaseLLMClient):
    """Simple extractive summarizer when APIs are unavailable."""
    
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        """
        Generate summary using simple extractive method.
        
        Args:
            content: Full content text
            title: Content title
            
        Returns:
            Generated summary
        """
        try:
            # Split content into paragraphs
            paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) > 20]
            
            if not paragraphs:
                # If no paragraphs, just truncate the content
                return self._truncate_content(content)
            
            # Extract first few paragraphs
            summary_parts = []
            total_chars = 0
            target_length = 150  # Target around 150 characters
            
            for para in paragraphs:
                if total_chars >= target_length:
                    break
                summary_parts.append(para)
                total_chars += len(para)
            
            summary = " ".join(summary_parts)
            
            # Ensure summary is not too long
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            return summary
            
        except Exception as e:
            print(f"⚠️  简单摘要生成失败: {e}")
            return self._truncate_content(content)
    
    @staticmethod
    def _truncate_content(content: str, max_length: int = 200) -> str:
        """
        Truncate content to maximum length.
        
        Args:
            content: Content to truncate
            max_length: Maximum length
            
        Returns:
            Truncated content
        """
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
