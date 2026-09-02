# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"观念棱镜" (DeepThink) — a fully static content-waterfall site. A React + Vite + Tailwind frontend renders articles scraped and summarized by a separate Python backend. **There is no runtime server**: content is baked into the JS bundle at build time.

Two independent halves:
1. **Frontend** (`src/`, `index.html`) — imports `src/assets/static-data.js` (a generated `export default [...]` module) and renders a filterable waterfall.
2. **Python scraper** (`python_scripts/`) — scrapes URLs, summarizes via LLM, writes a SQLite DB that is committed to git.

## Commands

Frontend (Node ≥ 20):
- `npm install` — install deps (no lockfile; see Gotchas)
- `npm run dev` — Vite dev server
- `npm run build` — production build to `dist/`
- `npm run lint` — ESLint (flat config, covers `src/` + `scripts/`)
- `npm run gen:static-js` — regenerate `static-data.js` from `python_scripts/web_content.db` (via sql.js)
- `npm run gen:static-js:from-json` — regenerate `static-data.js` from `static-data.json`, without the DB

Backend (Python):
- `pip install -r python_scripts/requirements.txt`
- `cd python_scripts && python main.py` — interactive CLI (scrape / manual input / view / batch)
- `cd python_scripts && python -m pytest test_*.py` — run backend tests
- `./scripts/encrypt-db.sh` — encrypt the DB (requires `SQLITE_KEY` in env)

## Architecture

### Data pipeline (the part that spans files)

```
python_scripts/web_content.db ──sql.js──▶ scripts/generate-data.js
   (SQLite, committed)                     │ reads content_summary
                                           │ (falls back to manual_content)
                                           ▼
                         src/assets/static-data.json  (canonical, committed)
                         src/assets/static-data.js    (generated `export default`)
                                           │
                                           ▼
                         src/App.jsx imports static-data.js
```

- `scripts/generate-data.js` reads the committed SQLite with sql.js, does an **incremental merge** keyed on `original_url` (fallback `title+created_time`), then writes timestamped snapshots + `static-data.json` + `static-data.js`.
- CI does **not** regenerate data — it deploys the committed `static-data.js`/`.json` directly (`deploy.yml`; in-CI regeneration was intentionally removed).

### Frontend

- `src/App.jsx` owns all state: `items`, category (single-select), tags (multi-select), search (Fuse.js). Filtering is entirely client-side in `filterData()`.
- `src/utils/categories.js` — the 7 mutually-exclusive categories (阮一峰《科技爱好者周刊》 structure): 科技动态 / 文章 / 工具 / 资源 / 图片 / 文摘 / 言论. Items lacking `category` render as `文章`.
- Components: `SearchBar`, `CategoryFilter`, `TagFilter`, `WaterfallGrid` → `ContentCard`, `ReportsPanel` → `ReportModal`.
- Reports are standalone static HTML pages under `public/`, listed in `src/assets/static-reports.js` — they are **not** part of the SQLite data.

### Python backend (`python_scripts/web_content_system/`)

Modular packages orchestrated by `extractor.py` / `main.py`:
- `scrapers/` — `BaseScraper` + `requests_scraper` and `browser_scraper` (Selenium)
- `llm_clients/` — OpenAI / DeepSeek / Ollama / extractive fallback summarizers
- `processors/` — content processing
- `database/db_manager.py` — SQLite access
- `config.py` — dataclass config from env (python-dotenv)

Two tables: `content_summary` (id, title, created_time, summary, original_url, tags) and `manual_content` (adds full `content`). `grab_params.json` drives batch scraping.

## Gotchas

- **No `package-lock.json`** (intentionally gitignored). CI runs `npm install --legacy-peer-deps`, not `npm ci` — the old lockfile pinned an internal npm registry unreachable from GH runners. Don't re-add it.
- **DB files are committed despite `*.db` in `.gitignore`** (`web_content.db` + `.web_content.db.enc`) — the deploy pipeline relies on them. The `.env` holding `SQLITE_KEY` is not committed.
- **`static-data-<timestamp>.json` snapshots are gitignored**; only `static-data.json` + `static-data.js` are tracked artifacts. Clean up snapshots rather than committing them.
- **`category` is not in the original DB schema** — it is assigned during extraction/backfill, so it appears in `static-data.js` but not in `content_summary`'s documented columns.
- Deploy is automatic on push to `main` → GitHub Pages (`gh-pages` branch).
