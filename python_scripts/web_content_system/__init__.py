"""
Web Content Extraction System

A modular system for extracting web content, generating summaries using LLM APIs,
and storing the results in a database.
"""

__version__ = "2.0.0"
__author__ = "Your Name"

from .extractor import WebContentExtractor

__all__ = ["WebContentExtractor"]
