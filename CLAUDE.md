# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"观念棱镜" (DeepThink) — a fully static content-waterfall site. A React + Vite + Tailwind frontend renders articles scraped and summarized by a separate Python backend. **There is no runtime server**: content is baked into the JS bundle at build time.

Two independent halves:
1. **Frontend** (`src/`, `index.html`) — imports `src/assets/static-data.js` (a generated `export default [...]` module) and renders a filterable waterfall.
2. **Python scraper** (`python_scripts/`) — scrapes URLs, summarizes via LLM, writes a local SQLite DB whose **encrypted copy** is committed to git.

## Commands

Frontend (Node ≥ 20):
- `npm ci` — install the exact dependency tree from the committed `package-lock.json`
- `npm install` — install deps (updates the lockfile; commit it if it changes)
- `npm run dev` — Vite dev server
- `npm run build` — production build to `dist/`
- `npm run lint` — ESLint (flat config, covers `src/` + `scripts/`)
- `npm run gen:static-js` — 从 `python_scripts/web_content.db` 单向生成 `static-data.json` + `static-data.js`（先校验；失败不写入。行数比上一版下降 >10% 会被拒绝，确认无误时用 `npm run gen:static-js -- --allow-shrink`）
- `npm run check:data` — 校验 DB、`static-data.json`、`static-data.js` 三者一致（CI 在 build 前强制执行；提交前务必跑）
- `npm run test:data` — 数据规则与生成器的 Node 单元测试

Backend (Python):
- `pip install -r python_scripts/requirements.txt`
- `cd python_scripts && python3 main.py` — legacy 交互路径（scrape / manual input / view / batch）。它不写 `category`，其写入的行会让 `npm run gen:static-js` 校验失败；manual input 只写 `manual_content`，不进入站点数据。周更入口请用 `python3 fetch_from_params.py` / `python3 crawler_subpages.py`
- `cd python_scripts && python3 -m pytest test_*.py` — run backend tests
- `./scripts/encrypt-db.sh` — encrypt the DB (requires `SQLITE_KEY` in env), then commit `web_content.db.enc`
- `./scripts/decrypt-db.sh` — restore the ignored plaintext DB from `.enc` (requires `SQLITE_KEY`); needed after a fresh clone

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
- 仓库只跟踪加密副本 `python_scripts/web_content.db.enc`；明文 `python_scripts/web_content.db` 被 `*.db` 忽略。fresh clone 后先运行 `./scripts/decrypt-db.sh` 才能本地 `gen:static-js` / `check:data`。
- `category` 是 DB 的列（七类之一），抓取入库时由 `category_classifier.py` 自动分类，可用 `set_category.py` 人工修正。
- 更新内容：改 DB → `npm run gen:static-js` → `./scripts/encrypt-db.sh` 重新加密并提交 `.enc`（不提交明文）→ 推送到 `main` 自动部署。
- `npm run check:data` 校验 DB 与生成物一致，CI 在 build 前执行（先解密 `.enc`）。
- 数据只取自 `content_summary`（导出 `id/title/created_time/summary/original_url/tags/category`）；读取上一版 `static-data.js` 仅用于缩水校验。按 `created_time DESC, id DESC` 排序，一次性重写两个生成物；不做增量合并，也不产生快照。
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

- **`package-lock.json` is committed** (resolved from the public npm registry, no internal URLs). CI runs `npm ci`. If you regenerate it, use `npm install --package-lock-only --registry=https://registry.npmjs.org` and confirm `grep -c "corp.kuaishou" package-lock.json` is `0`.
- **Only the encrypted DB is tracked** — `web_content.db` is ignored by `*.db`; `web_content.db.enc` is the sole data copy in git. CI decrypts it with the `SQLITE_KEY` secret before `check:data`; build/deploy uses the committed generated files. The `.env` holding `SQLITE_KEY` is not committed, and losing the key makes `.enc` unrecoverable. A missing secret only degrades on PRs (fork PRs skip `check:data`; `test:data` does not need the DB) — on a non-PR run it is a hard `::error::` failure before deploy.
- **Historical commits still contain the old plaintext DB** — an accepted risk; Git history is not being rewritten. Don't re-add the plaintext DB to tracking.
- **Generated data files must be committed**: CI does not run `gen:static-js`; it deploys the committed `static-data.json` / `static-data.js`, and `check:data` fails if they diverge from the DB.
- **Never hand-edit `static-data.json` / `static-data.js`** — the DB is the single source of truth. Change the DB, then run `npm run gen:static-js`. Fix a category with `python_scripts/set_category.py`.
- **抓取入库有噪声过滤**（2026-10-19 清理后）— `crawler_subpages.py` 会跳过 MediaWiki 特殊/登录页（含百分号编码与 `returnto=`）、站点导航/列表标题，以及 DB 中已存在完全同标题的重复（同一文章两种 URL 的镜像）。vibecodinghub 周刊镜像根已移除，周刊只从 GitHub blob 视图抓；GitHub 列表/仓库根本身标记 `skip_root` 不入库。规则有单测 `python_scripts/test_crawler_filters.py`；清理记录见 `docs/superpowers/audits/2026-10-19-cleanup/summary.md`。
- **Deploy only from `main`** — production is `https://deepthink.global`; the Pages project alias `dllen.github.io/deepthink/` is unsupported (absolute paths, default `base`). Push to `main` or a manual `workflow_dispatch` **started on `main`** deploys to `gh-pages`; pull requests run `test:data` / `check:data` / `build` but never deploy. Production deploys use `concurrency: group: pages-deploy-${{ github.ref }}`: runs on `refs/heads/main` share one group where a new run cancels an in-progress old one, while each PR gets its own group and cannot cancel a production deploy. The job has a 10-minute timeout.
- **Post-deploy smoke gate** — after deploy, CI retries **the index check** 6 times (10s apart, no sleep after the last failed attempt): index 200 + `text/html`, and the `assets/index-*.js` name matches this build. Then `assets/index-*.js`, `assets/index-*.css`, and `/logo.svg` are each checked once (200 + javascript / `text/css` / `image/svg+xml`). All curl calls use `-m 15`; failures report the last status/content-type/expected/actual. A 200 status alone is not enough: Cloudflare can return a 200 fallback page.
- **Rollback** — `git revert <bad-commit> && git push` and let CI redeploy. Don't hand-edit `gh-pages`; last resort is `git push --force-with-lease origin <deploy-sha>:gh-pages`.
