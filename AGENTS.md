# Repository Guidelines

This project is a hybrid application combining a React + Vite frontend with Python backend scripts for content scraping, extraction, and database management.

## Project Structure

```
deepthink/
├── src/                    # React frontend source
│   ├── components/         # React components (ContentCard, TagFilter, WaterfallGrid)
│   ├── utils/             # Utility functions (categories.js, formatDate.js, searchUtils.js)
│   ├── assets/            # Generated static-data.json/.js + reports/links data
│   ├── App.jsx            # Main application component
│   └── main.jsx           # Application entry point
├── python_scripts/        # Python backend scripts
│   ├── web_content_system/  # Modular scraping system
│   │   ├── scrapers/        # Website-specific scrapers
│   │   ├── processors/      # Content processors
│   │   ├── llm_clients/     # LLM API integrations
│   │   └── database/        # Database utilities
│   ├── category_classifier.py  # LLM 七分类
│   ├── migrate_category.py     # 一次性分类迁移（已完成）
│   ├── set_category.py         # 人工修正单条分类
│   ├── fetch_from_params.py    # 周更入口：按 grab_params.json 抓取
│   ├── crawler_subpages.py     # 周更入口：按脚本内 ROOT_URLS 抓取
│   ├── grab_params.json        # 待抓 URL 清单（{"url","tags","done"}）
│   ├── main.py             # Legacy interactive CLI
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
| `npm ci` | Install exact dependencies from the committed lockfile |
| `npm install` | Install dependencies (updates the lockfile; commit the result) |
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run gen:static-js` | Generate static-data.json + static-data.js from the DB |
| `npm run check:data` | Verify the DB and generated files are consistent (CI) |

### Backend Scripts

```bash
# Python dependencies
pip install -r python_scripts/requirements.txt

# Restore the ignored plaintext DB from the tracked encrypted copy (needs SQLITE_KEY).
# The scripts read SQLITE_KEY from the environment only (they do not load .env):
set -a; . ./.env; set +a   # or: export SQLITE_KEY=...
./scripts/decrypt-db.sh

# Re-encrypt after changing the DB, then commit python_scripts/web_content.db.enc
./scripts/encrypt-db.sh

# Weekly update entry points
cd python_scripts && python3 fetch_from_params.py   # reads grab_params.json
cd python_scripts && python3 crawler_subpages.py    # fixed ROOT_URLS; no params file

# Legacy interactive CLI. It does not write `category`, so rows it inserts make
# `npm run gen:static-js` fail validation; its manual input only writes
# `manual_content`, which is not site data.
cd python_scripts && python3 main.py
```

## Coding Style

- **Frontend**: React 18 with functional components and hooks; ES6+ JavaScript
- **Styling**: TailwindCSS utility classes; keep component-scoped styles in `App.css`
- **Backend**: Python with modular structure under `web_content_system/`
- **Formatting**: Run `npm run build` before commits to verify no build errors

## Testing

- Backend tests located in `python_scripts/test_*.py`
- Run Python tests: `cd python_scripts && python3 -m pytest test_*.py`
- Run data pipeline tests: `npm run test:data`

## Git Workflow

### Commit Convention

Use conventional commit prefixes:

- `feat:` — New features
- `fix:` — Bug fixes  
- `chore:` — Maintenance, dependency updates
- `docs:` — Documentation changes
- `refactor:` — Code refactoring

Example: `feat: add a new article to the database`

### Pull Requests

1. Commit from the `main` branch
2. Use clear commit messages following the convention above
3. Ensure `npm run build` succeeds before pushing
4. The CI/CD workflow (`.github/workflows/deploy.yml`) also runs on pull requests (`test:data`, `check:data`, `build`); production deployment is based on `main` push.

## Configuration

Copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` — LLM API keys
- `OLLAMA_API_URL` — Local Ollama endpoint (defaults to `http://localhost:11434`)
- `SQLITE_KEY` — Required for `./scripts/encrypt-db.sh` / `./scripts/decrypt-db.sh`; the same value is stored as the CI `SQLITE_KEY` secret. Keep `.env` at mode 600.

## Database

- SQLite database: `python_scripts/web_content.db` — the local plaintext working copy; **not tracked** (ignored by `*.db`)
- Encrypted copy: `python_scripts/web_content.db.enc` — **tracked; the only data copy in the repository**. Re-generate and commit it after every DB change via `./scripts/encrypt-db.sh`
- CI restores the plaintext from `.enc` with the `SQLITE_KEY` secret before `test:data` / `check:data`; build/deploy uses the committed generated files
- Fresh clone: run `./scripts/decrypt-db.sh` before `npm run gen:static-js` / `npm run check:data`
- Generated artifacts: `src/assets/static-data.json` + `src/assets/static-data.js` (via `npm run gen:static-js`; do not edit by hand)
- `content_summary` columns: `id`, `title`, `created_time`, `summary`, `original_url`, `tags`, `uid`, `content`, `category`, `category_source`
- `manual_content` is a legacy table written by the old `WebContentExtractor`; it is not part of the site data
