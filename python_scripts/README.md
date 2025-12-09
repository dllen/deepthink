# Web Content Extraction System

A modular Python system for extracting web content, generating summaries using LLM APIs, and storing results in a database.

## Features

- 🕸️ **Web Scraping**: Supports both browser-based (Selenium) and HTTP-based (requests) scraping
- 🤖 **LLM Integration**: Multiple LLM API support with automatic fallback
  - OpenAI API (GPT models)
  - Local models (Ollama)
  - Simple extractive summarization (fallback)
- 💾 **Database Storage**: SQLite database for persistent storage
- 🐦 **Weibo Content**: Automatic generation of weibo-formatted posts
- ✍️ **Manual Input**: Support for manually entered content
- 🏷️ **Tagging System**: Tag-based organization and search

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser (for browser-based scraping)
- ChromeDriver (matching your Chrome version)

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

The system uses environment variables for configuration:

### OpenAI API (Optional)

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional, for compatible APIs
export OPENAI_MODEL="gpt-3.5-turbo"  # Optional, default model
```

### Local Model API (Optional)

```bash
export OLLAMA_API_URL="http://localhost:11434/api/generate"
export OLLAMA_MODEL="llama2"
```

### Database

```bash
export DB_PATH="web_content.db"  # Optional, default path
```

### Browser Settings

```bash
export BROWSER_HEADLESS="true"  # Run browser in headless mode
export BROWSER_TIMEOUT="10"  # Page load timeout in seconds
```

## Usage

### Command Line Interface

Run the interactive CLI:

```bash
python main.py
```

### Programmatic Usage

```python
from web_content_system import WebContentExtractor

# Create extractor instance
with WebContentExtractor() as extractor:
    # Scrape a URL
    extractor.scrape_and_process("https://example.com", tags="tech,news")
    
    # Manual input
    summary = extractor.manual_input(
        title="My Article",
        content="Article content here...",
        tags="personal"
    )
    
    # View recent records
    extractor.view_recent_records(limit=5)
```

## Architecture

The system is organized into modular components:

```
web_content_system/
├── config.py              # Configuration management
├── database/              # Database operations
│   └── db_manager.py
├── scrapers/              # Web scraping
│   ├── base_scraper.py
│   ├── browser_scraper.py
│   └── requests_scraper.py
├── llm_clients/           # LLM API integrations
│   ├── base_client.py
│   ├── openai_client.py
│   ├── local_model_client.py
│   └── fallback_summarizer.py
├── processors/            # Content processing
│   └── content_processor.py
└── extractor.py           # Main orchestrator
```

## Testing

Run the test suite:

```bash
python test_system.py
```

## Database Schema

### content_summary Table

- `id`: Primary key
- `title`: Content title
- `created_time`: Creation timestamp
- `summary`: Generated summary
- `original_url`: Source URL
- `tags`: Comma-separated tags

### manual_content Table

- `id`: Primary key
- `title`: Content title
- `content`: Full content text
- `created_time`: Creation timestamp
- `summary`: Generated summary
- `tags`: Comma-separated tags

## Extending the System

### Adding a New LLM Provider

1. Create a new client class in `llm_clients/`:

```python
from .base_client import BaseLLMClient

class MyLLMClient(BaseLLMClient):
    def generate_summary(self, content: str, title: str) -> Optional[str]:
        # Implementation here
        pass
```

2. Add it to `ContentProcessor` in `processors/content_processor.py`

### Adding a New Scraper

1. Create a new scraper class in `scrapers/`:

```python
from .base_scraper import BaseScraper

class MyScraper(BaseScraper):
    def scrape(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        # Implementation here
        pass
```

2. Use it in `WebContentExtractor`

## License

MIT License

## Author

Your Name
