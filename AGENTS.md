# Repository Guidelines

This project is a hybrid application combining a React + Vite frontend with Python backend scripts for content scraping, extraction, and database management.

## Project Structure

```
deepthink/
├── src/                    # React frontend source
│   ├── components/         # React components (ContentCard, TagFilter, WaterfallGrid)
│   ├── utils/             # Utility functions (sqliteReader.js)
│   ├── assets/            # Static assets
│   ├── App.jsx            # Main application component
│   └── main.jsx           # Application entry point
├── python_scripts/        # Python backend scripts
│   ├── web_content_system/  # Modular scraping system
│   │   ├── scrapers/        # Website-specific scrapers
│   │   ├── processors/      # Content processors
│   │   ├── llm_clients/     # LLM API integrations
│   │   └── database/        # Database utilities
│   ├── main.py             # Main scraping script
│   ├── clean_db.py         # Database cleanup utility
│   └── web_content_extractor.py
├── public/                 # Static files (HTML pages, data)
├── dist/                   # Built frontend output
├── scripts/                # Build and utility scripts
└── static/                 # Static data files
```

## Build Commands

### Frontend (Node.js >= 20.0.0)

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies |
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run gen:static-js` | Generate static JS from JSON data |

### Backend Scripts

```bash
# Python dependencies
pip install -r python_scripts/requirements.txt

# Encrypt database
./scripts/encrypt-db.sh

# Run content extractor
cd python_scripts && python main.py
```

## Coding Style

- **Frontend**: React 18 with functional components and hooks; ES6+ JavaScript
- **Styling**: TailwindCSS utility classes; keep component-scoped styles in `App.css`
- **Backend**: Python with modular structure under `web_content_system/`
- **Formatting**: Run `npm run build` before commits to verify no build errors

## Testing

- Backend tests located in `python_scripts/test_*.py`
- Run Python tests: `cd python_scripts && python -m pytest test_*.py`
- No frontend unit tests currently configured

## Git Workflow

### Commit Convention

Use conventional commit prefixes:

- `feat:` — New features
- `fix:` — Bug fixes  
- `chore:` — Maintenance, dependency updates
- `docs:` — Documentation changes
- `refactor:` — Code refactoring

Example: `feat: add new article to static data`

### Pull Requests

1. Commit from the `main` branch
2. Use clear commit messages following the convention above
3. Ensure `npm run build` succeeds before pushing
4. The CI/CD workflow (`.github/workflows/deploy.yml`) auto-deploys to GitHub Pages on `main` push

## Configuration

Copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` — LLM API keys
- `OLLAMA_API_URL` — Local Ollama endpoint (defaults to `http://localhost:11434`)
- `SQLITE_KEY` — Database encryption key

## Database

- SQLite database: `python_scripts/web_content.db`
- Encrypted copy: `python_scripts/web_content.db.enc`
- Expected schema: `id`, `title`, `created_time`, `summary`, `original_url`, `tags`
