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
- `npm run gen:static-js` — 从 `python_scripts/web_content.db` 单向生成 `static-data.json` + `static-data.js`（先校验；失败不写入）
- `npm run check:data` — 校验 DB、`static-data.json`、`static-data.js` 三者一致（CI 在 build 前执行）
- `npm run test:data` — 数据规则与生成器的 Node 单元测试

Backend (Python):
- `pip install -r python_scripts/requirements.txt`
- `cd python_scripts && python main.py` — interactive CLI (scrape / manual input / view / batch)
- `cd python_scripts && python -m pytest test_*.py` — run backend tests
- `./scripts/encrypt-db.sh` — encrypt the DB (requires `SQLITE_KEY` in env)

## Architecture

### 数据管线（唯一真源）

```
python_scripts/web_content.db ──scripts/generate-data.js──▶ src/assets/static-data.json
   (SQLite, 唯一真源)                     │                 src/assets/static-data.js
                                          │
                                          ▼
                                  src/App.jsx imports static-data.js
```

- DB 是唯一真源；两个数据文件都是生成物，**禁止手工编辑**。
- `category` 是 DB 的列（七类之一），抓取入库时由 `category_classifier.py` 自动分类，可用 `set_category.py` 人工修正。
- 更新内容：改 DB → `npm run gen:static-js` → 提交 → 推送自动部署。
- `npm run check:data` 校验 DB 与生成物一致，CI 在 build 前执行。
- 生成器只读 `content_summary`（导出 `id/title/created_time/summary/original_url/tags/category`），按 `created_time DESC, id DESC` 排序，一次性重写两个生成物；不做增量合并，也不产生快照。
- CI 不重新生成数据：`deploy.yml` 直接部署提交的 `static-data.js`/`.json`；`test:data` + `check:data` 在 build 前执行。

### Frontend

- `src/App.jsx` owns all state: `items`, category (single-select), tags (multi-select), search (Fuse.js). Filtering is entirely client-side in `filterData()`.
- `src/utils/categories.js` — the 7 mutually-exclusive categories (阮一峰《科技爱好者周刊》 structure): 科技动态 / 文章 / 工具 / 资源 / 图片 / 文摘 / 言论. Category filtering is strict equality; rows lacking `category` match no category filter, and only the badge/color helper `getCategoryStyle` falls back to 文章's colors (the badge itself is not rendered without a category).
- Components: `SearchBar`, `CategoryFilter`, `TagFilter`, `WaterfallGrid` → `ContentCard`, `ReportsPanel` → `ReportModal`.
- Reports are standalone static HTML pages under `public/`, listed in `src/assets/static-reports.js` — they are **not** part of the SQLite data.

### Python backend (`python_scripts/web_content_system/`)

Modular packages orchestrated by `extractor.py` / `main.py`:
- `scrapers/` — `BaseScraper` + `requests_scraper` and `browser_scraper` (Selenium)
- `llm_clients/` — OpenAI / DeepSeek / Ollama / extractive fallback summarizers
- `processors/` — content processing
- `database/db_manager.py` — SQLite access
- `config.py` — dataclass config from env (python-dotenv)

`content_summary` 是站点数据的唯一来源表：`id, title, created_time, summary, original_url, tags, uid, content, category, category_source`。生成器只导出其中的 `id, title, created_time, summary, original_url, tags, category`。`manual_content` 是旧版表（旧 `WebContentExtractor` 仍会写入），不进入站点数据。`grab_params.json` 驱动 `fetch_from_params.py` 批量抓取。

## Gotchas

- **No `package-lock.json`** (intentionally gitignored). CI runs `npm install --legacy-peer-deps`, not `npm ci` — the old lockfile pinned an internal npm registry unreachable from GH runners. Don't re-add it.
- **DB files are committed despite `*.db` in `.gitignore`** (`web_content.db` + `web_content.db.enc`) — CI's `check:data` reads the plaintext DB. The `.env` holding `SQLITE_KEY` is not committed.
- **Generated data files must be committed**: CI does not run `gen:static-js`; it deploys the committed `static-data.json` / `static-data.js`, and `check:data` fails if they diverge from the DB.
- **Never hand-edit `static-data.json` / `static-data.js`** — the DB is the single source of truth. Change the DB, then run `npm run gen:static-js`. Fix a category with `python_scripts/set_category.py`.
- Deploy is automatic on push to `main` → GitHub Pages (`gh-pages` branch).
