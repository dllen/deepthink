# Python Backend Audit — Script Convergence / Module Boundaries / Dependency Drift

**Date:** 2026-10-18
**Scope:** `python_scripts/**` (all Python), plus backend-facing contracts: `scripts/generate-data.js`, `requirements*.txt`, `.github/workflows/`, `AGENTS.md` / `CLAUDE.md` / `python_scripts/README.md`.
**Mode:** read-only. No code changes, no production scripts executed. Read-only SQLite queries and `/tmp` probes only.
**Related audits (deliberately not duplicated):** `data-pipeline.md` (DB→static-data freshness, `category` reproducibility, stray root DB), `security-privacy.md` (tracked plaintext DB, encryption, CI supply chain). This document covers the **code/module/dependency** layer and only cross-references those findings.

Severity legend: **High** = broken or dangerous in normal use · **Medium** = clear risk/maintenance drag, low fix risk · **Low** = hygiene/documentation.

---

## 1. Current state snapshot

Runtime observed: Python **3.11.15** (pyenv). Installed: `requests 2.34.2`, `beautifulsoup4 4.15.0`, `lxml 6.1.1`, `urllib3 2.7.0`, `python-dotenv 1.2.3`, `pytest 9.1.1`. **Not installed: `selenium`, `openai`.**

Python code inventory (LoC, `wc -l`):

| Group | Files | LoC |
|---|---|---|
| `web_content_system/` package | 17 | 1,289 |
| Standalone pipeline scripts | 5 | 1,529 |
| Legacy interactive extractors | 2 | 893 |
| Tests | 2 | 378 |
| `_archive/` | 1 | 254 |

Entry points and real usage:

| Script | Role today | Referenced by | Notes |
|---|---|---|---|
| `python_scripts/crawler_subpages.py` | **De-facto canonical crawler** (append-only, depth-1 + subpages) | `_archive/README.md`, old audit | Writes DB; 10 root sources configured, last 6 added 2026-09-02 and never harvested |
| `python_scripts/fetch_from_params.py` | `grab_params.json` driver → DB | docstring, AGENTS tree | 17 entries (15 `done`, 2 pending); also owns `--backfill` |
| `python_scripts/backfill_content.py` | Re-fetch and fill `content` column | docstring | DB-driven, preserves summary/title/tags |
| `python_scripts/clean_db.py` | Truncate / hard-delete DB | AGENTS.md | Destructive; `--hard` deletes file |
| `python_scripts/main.py` | Modular interactive CLI (crawl / manual / view / batch) | `AGENTS.md`, `CLAUDE.md`, `python_scripts/README.md` | Only consumer of the package; **cannot start in the current interpreter** (needs selenium + openai) |
| `python_scripts/web_content_extractor.py` | Legacy monolithic interactive CLI | none in code or docs except `AGENTS.md` tree listing | 424 LoC; superseded by `main.py` |
| `python_scripts/web_content_extractor_simple.py` | Forked variant of the above | none | 467 LoC; 280 lines identical to the other legacy file; has newer extraction heuristics never backported |
| `python_scripts/_archive/fetch_and_add.py` | Archived early fetcher | `_archive/README.md` | Intentionally archived; fine |

Live DB observed (read-only): `content_summary` = 192 rows, 190 with non-empty `content`, 2 rows with `NULL uid`, 0 duplicate `original_url`, `PRAGMA integrity_check` = ok. Columns: `id,title,created_time,summary,original_url,tags,uid,content`. `manual_content` = 0 rows. `web_content.db.enc` is stale (103 rows) — covered by security audit, not repeated here.

---

## 2. Findings

### F1 · The package cannot be imported without optional heavy dependencies — **High**

`web_content_system/__init__.py:11` eagerly imports `extractor.py`, which eagerly imports `scrapers/__init__.py` → `browser_scraper.py:6` → `selenium`. Therefore **every** submodule import fails when selenium is absent, including `config` and `database`:

```
$ cd python_scripts && python3 -c "from web_content_system.database import DatabaseManager"
ModuleNotFoundError: No module named 'selenium'
```

Same for `openai` (`llm_clients/*_client.py`, `processor/content_processor.py:6`). Consequences: the DB layer, config layer and fallback summarizer are unreachable/testable standalone; pytest collection fails (F7); operators get a misleading "install deps" error instead of graceful degradation.

### F2 · Schema is declared in 5 places and has already forked — **High**

`content_summary` DDL is duplicated in:

- `web_content_system/database/db_manager.py:31-40` — **no `content` column** (adds only `uid`)
- `crawler_subpages.py:210-231` (`SCHEMA_SQL`) — has `uid` + `content`
- `fetch_from_params.py:56-88` (`ensure_schema`) — has `uid` + `content`
- `web_content_extractor.py:37-68` and `web_content_extractor_simple.py:32-64` — legacy DDL, no `uid`/`content`

Probe (in `/tmp`, importing `db_manager.py` directly): a fresh DB created by `DatabaseManager` has columns `id,title,created_time,summary,original_url,tags,uid` — **no `content`**. So a DB created by the modular path breaks the content-backup tools:

```
SELECT ... FROM content_summary WHERE content IS NULL OR content = ''   -- backfill_content.py:181
→ sqlite3.OperationalError: no such column: content
```

There is also no migration/version table; `db_manager._create_tables()` ad-hoc `ALTER`s on every connection and runs a **destructive dedupe** (see F3). The data audit's `category` finding is the same root cause one level up: **no single owner of the schema**.

### F3 · `DatabaseManager.__init__` can crash or silently delete rows — **High**

`db_manager.py:42-93` runs on *every* construction (including tests):

1. adds `uid`, creates `UNIQUE INDEX idx_uid`;
2. backfills `uid = md5(original_url)` for NULL rows;
3. deletes all but `MAX(id)` per `uid` without confirmation.

If a legacy script (or any external insert) ever wrote two rows for the same URL, the backfill **UPDATE violates the unique index and raises**, leaving the DB unusable for the modular path:

```
$ /tmp probe: legacy DB with 2 rows sharing one URL, then DatabaseManager('legacy.db')
sqlite3.IntegrityError: UNIQUE constraint failed: content_summary.uid
```

The legacy extractors (`web_content_extractor*.py:303-314`, `_archive/fetch_and_add.py:41-70`) write without `uid`, so this is reachable for any user of the old CLIs. Conversely, when the migration *does* run, step 3 silently deletes rows (keeping the newest id, discarding the original `created_time`). The live DB still has 2 `NULL uid` rows, which indicates the modular path has not run against it since those rows were written.

### F4 · Production pipeline bypasses the package entirely; four pipeline implementations coexist — **Medium**

Only `main.py` + tests import `web_content_system`. The scripts that actually populate the DB (`crawler_subpages.py`, `fetch_from_params.py`, `backfill_content.py`) re-implement the same four stages: load env → HTTP fetch → title/body extract → summarize → upsert. Near-duplicates measured with `difflib` on AST source segments:

| Helper | Locations | Similarity |
|---|---|---|
| `extract_main_text` | `crawler_subpages.py:324`, `backfill_content.py:88` | 0.93 |
| `load_env` | `crawler_subpages.py:188`, `backfill_content.py:70` | 0.96 |
| `extract_title` | `crawler_subpages.py:345`, `backfill_content.py:105`, `fetch_from_params.py:115-121` | 0.73 |
| `fetch_page` / `fetch_content` | `crawler_subpages.py:383`, `backfill_content.py:118`, `fetch_from_params.py:94` | 0.67 |
| env loader variant | `fetch_from_params.py:31` (`load_env_file`) | 0.35 vs `load_env` |

Also duplicated: md5 URL→uid in 5 places (`db_manager.py:117`, `db_manager.py:59`, `crawler_subpages.py:253`, `fetch_from_params.py:90`, `_archive/fetch_and_add.py:73`); schema DDL in 5 places (F2); `MAX_CONTENT_LEN`/`POLITE_PAUSE`/`CONTENT_SELECTORS`/`HEADERS` in 2–3 places each; **five different summarizer stacks** (package clients; crawler raw-HTTP DeepSeek; fetch OpenAI/Ollama; legacy DeepSeek/Qwen/OpenAI-compatible; legacy-simple OpenAI/Ollama/extractive). The legacy pair alone is 893 LoC with 280 identical lines and no caller.

This is the "three crawlers, one job" finding from the July audit only partially done: `crawler.py` was removed and `fetch_and_add.py` archived, but a second convergence axis (package vs scripts) was never resolved — the package is now effectively demo/test code while the production path is script-shaped.

### F5 · DB path policy is inconsistent — **Medium** (data-pipeline audit also flags the 0-byte root DB; code angle here)

| Component | Path |
|---|---|
| `web_content_system/config.py:56` | `"web_content.db"` (CWD-relative) |
| `fetch_from_params.py:26` | `"web_content.db"` (CWD-relative) |
| `main.py:27` | `"grab_params.json"` (CWD-relative) |
| `crawler_subpages.py:43`, `backfill_content.py:39`, `clean_db.py:6-8` | `<repo>/python_scripts/web_content.db` (script-relative) |
| `db_manager.py:10` default | `"web_content.db"` (CWD-relative) |

`DB_PATH` is documented in `python_scripts/README.md` but honored only by `config.py:62` and `clean_db.py:41`; the crawler/backfill ignore it. A run from the repo root (documented `python main.py` vs `cd python_scripts`) silently creates/uses a different DB — the untracked 0-byte `./web_content.db` at the repo root is that artifact. Fix is cheap and high-leverage: one resolver, `DB_PATH` override, default `<repo>/python_scripts/web_content.db`.

### F6 · Documented install/tests are currently unrunnable; test suite is unsafe — **High** (verification integrity)

`python_scripts/requirements.txt` declares selenium/openai but not pytest; the interpreter has neither selenium nor openai. `python_scripts/README.md` says "run `python test_system.py`", which fails:

- `test_system.py:62` calls `extractor.generate_summary_with_api(...)` — that method exists only on the **legacy** classes (`web_content_extractor*.py:161/178`), not on `WebContentExtractor`;
- `test_system.py:88` uses `sqlite3` but only imports it inside `if __name__ == "__main__"` (`:114`) → `NameError` under pytest;
- `test_system.py:42` calls `manual_input`, which **writes into the tracked production DB** (via `DatabaseManager` at `config.py:56`);
- `test_modular.py:52` creates `test_temp.db` in the CWD and deletes it afterwards; no fixtures/tmp dirs.

Actual `pytest` behaviour today (no DB touched):

```
$ cd python_scripts && python3 -m pytest test_modular.py test_system.py --collect-only -q
5 tests collected, 1 error
ERROR collecting test_system.py
  ModuleNotFoundError: No module named 'selenium'
```

No Python CI job exists (`.github/workflows/deploy.yml` is Node-only), so this has never been caught. See `.github/workflows/deploy.yml:1-43`.

### F7 · Dependency drift between two requirement files, no pins, no lock, no CI — **Medium**

| Dep | `requirements.txt` (root) | `python_scripts/requirements.txt` | Imported by | Installed locally |
|---|---|---|---|---|
| requests | `>=2.25.1` | `>=2.31.0` | 6+ files | 2.34.2 |
| beautifulsoup4 | `>=4.9.3` | `>=4.12.0` | 6+ files | 4.15.0 |
| selenium | `>=4.0.0` | `>=4.15.0` | `browser_scraper.py` | **missing** |
| openai | `>=1.0.0` | `>=1.3.0` | `llm_clients/*`, `fetch_from_params.py`, legacy | **missing** |
| python-dotenv | **absent** | `>=1.0.0` | `web_content_system/config.py:8` | 1.2.3 |
| lxml | `>=4.6.3` | absent | **nothing** (parsers are `html.parser`) | 6.1.1 |
| urllib3 | `>=1.26.5` | absent | **nothing directly** | 2.7.0 |
| pytest | absent | absent | `AGENTS.md` test command | 9.1.1 |
| dashscope | absent (commented) | absent (comment only) | `web_content_extractor.py:224` (Qwen path) | missing |

Also: no `pyproject.toml`, no `.python-version`, no lock; `README.md` claims "Python 3.8 or higher" while `crawler_subpages.py:419` uses `str.removeprefix` (3.9+) — so the minimum actually differs per script. `docs` and code disagree about which requirements file is authoritative; `AGENTS.md` points at `python_scripts/requirements.txt`, `CLAUDE.md` at both.

### F8 · Error handling and observability are print-based; no retries, no concurrency guard — **Medium**

- **Zero `logging` usage** (`grep -rn "import logging"` across `python_scripts` → no matches); every diagnostic is `print`, nothing is timestamped/leveled/collectable.
- Broad `except Exception` + `print(...)` in every I/O path; several **bare `except Exception: pass`** in `content_processor.py:129-130,142-143,153-154` (title generation) silently swallow API/parse failures.
- No retries/backoff anywhere (`grep retry|backoff` → no matches); a single timeout/5xx just skips the URL ("failed" is only a final count).
- No `busy_timeout` / WAL (`grep busy_timeout|journal_mode` → no matches). Two writers on the same file (e.g. crawler + fetch) can hit `database is locked`; the module path also opens SQLite without any timeout option.
- Timeout values are ad hoc across files: 15 s (`requests_scraper.py:41`), 20 s (`fetch_from_params.py:98`), 25 s (`crawler_subpages.py:141`, `backfill_content.py:43`), 30 s (`config.py:35`), 60 s (`crawler_subpages.py:520`, `fetch_from_params.py:189`).
- `crawler_subpages.py:625` + `:630` fetch every root page **twice** (once inside `insert_one`, once for link discovery) — wasteful and doubles rate-limit exposure.

### F9 · `grab_params.json` is mutated in place by two independent tools — **Low–Medium**

`main.py:66-67` and `fetch_from_params.py:368-369` both rewrite the same JSON with different semantics (`main.py` batch uses the modular extractor and its own `done` bookkeeping; `fetch_from_params.py` the production path). Neither write is atomic (no tmp+rename), so an interrupted run can corrupt the file. A single owner (or an atomic writer helper) is needed; otherwise "2 pending" can silently diverge between the two tools.

### F10 · User-visible workflow bugs in the modular path — **Medium**

- `extractor.py:48` scrapes `title`, then `:57` **overwrites it** with an LLM-generated ≤20-char title; genuine page titles are never stored by `main.py`.
- `extractor.py:75-94` `manual_input(title, ...)` ignores the caller's `title` and regenerates it from content (`:87`).
- `requests_scraper.py:58-60` returns `("抓取失败", "无法获取页面内容")` on HTTP error instead of `(None, None)`; the error string then flows through the same "title/content" contract (only saved by the length check).
- `main.py` option 5 (`process_batch_scraping`) duplicates `fetch_from_params.py` but writes `grab_params.json` without atomicity (F9) and ignores `tags`-preservation nuances.

### F11 · Documentation drifts from the code — **Low**

- `AGENTS.md`: documents the schema as `id,title,created_time,summary,original_url,tags` (missing `uid`, `content`, `category`); calls `main.py` "Main scraping script" although `crawler_subpages.py` is the canonical crawler; documents `python -m pytest test_*.py`, which currently cannot pass (F6).
- `python_scripts/README.md`: "Python 3.8+"; test command broken; architecture tree omits `deepseek_client.py`; schema section omits `uid`/`content`; claims browser scraping is primary (it is optional in practice).
- `CLAUDE.md`: says `category` "is assigned during extraction/backfill" — no current Python code assigns it (data audit owns that fact; cross-ref only).
- `_archive/README.md`: references `TARGETS` and a `--wipe` flag in `crawler_subpages.py`; the actual names are `ROOT_URLS` and `--update-content`, and there is no wipe mode (yet).
- `python_scripts/README.md` instructs `python test_system.py`, which writes the tracked DB (F6).

### F12 · `clean_db.py` is the only destructive tool and it is unguarded beyond flags — **Low**

`--hard` deletes the DB file and optionally `.enc` with a print only (no backup, no confirmation); `truncate_tables` wipes both tables and VACUUMs. Flags are explicit and `--dry-run` exists, so risk is acceptable, but it should not be able to target an unexpected path silently given the path-policy problem (F5).

---

## 3. Not re-reported (already fixed or owned elsewhere)

- `fetch_and_add.py` archived and `crawler.py` removed (old audit B2, commits `07b3386` / history) — done, no action.
- DB files intentionally tracked with `.gitignore` comments (old audit E1) — accepted by security audit; not repeated.
- Obfuscation removed from `generate-data.js` (old audit B4) — done.
- `category` reproducibility, DB/static-data freshness, ghost rows, 0-byte root DB — **owned by `data-pipeline.md`**; F2/F5/F11 reference but do not repeat.
- Plaintext DB, encryption staleness, CI supply chain, SSRF prompt-injection — **owned by `security-privacy.md`**.

---

## 4. Recommended order of work (proposals, not executed)

| # | Priority | Change | Why now | Acceptance criteria |
|---|---|---|---|---|
| 1 | **P0** | Make the package import-safe: lazy-import `selenium` inside `BrowserScraper._setup_browser`, lazy-import `openai` inside clients, don't instantiate `BrowserScraper` eagerly in `WebContentExtractor.__init__` | Unblocks tests, DB layer, fallback path; tiny diff | `python -c "from web_content_system.database import DatabaseManager"` succeeds with only requests/bs4/dotenv installed; `pytest --collect-only` has 0 errors |
| 2 | **P0** | One schema/migration module (single DDL + `uid` helper + idempotent, non-destructive migration). Decide `content`/`category` columns there once; replace 5 DDL copies; dedupe only via explicit flag/report, never implicit DELETE | Prevents fresh-DB drift and the legacy-duplicate crash | Fresh DB schema == live DB schema; legacy duplicate DB opens with a warning + documented repair; migration covered by a test |
| 3 | **P0** | Resolve `category` ownership with Architect/data-pipeline: add column + assignment step, or declare frontend-only and stop regenerating | Otherwise any data refresh erases classification (data audit R1) | `npm run gen:static-js` keeps `category` (or docs say it is not derived from DB) |
| 4 | **P1** | Convergence: one `pipeline` module (env → fetch → extract → summarize → upsert) imported by the 3 scripts; archive `web_content_extractor*.py` (893 LoC); one uid helper, one timeout table, one env loader | Removes the biggest maintenance drag; legacy files have no callers | `grep` shows one implementation of uid/DDL/env-load; scripts become thin CLIs; tests cover the shared module |
| 5 | **P1** | Single DB path resolver (`DB_PATH` override, default `python_scripts/web_content.db`) used by all 6 writers; remove stray root DB | Cheap; prevents split-brain DB writes | Running any CLI from repo root or `python_scripts/` touches the same file; no repo-root `*.db` recreated |
| 6 | **P1** | Dependency/CI: one pinned requirements (or `pyproject.toml` with `scraper`/`llm`/`dev` extras), pytest declared, CI job running `pytest` in a temp dir; fix test_system (delete missing-method test, temp DB, mock network) | Restores a verifiable "tests pass" claim; catches drift | Fresh venv install + `pytest` green in CI; no test touches tracked DB; Python version pinned for CI |
| 7 | **P2** | Observability/resilience: `logging`, retry with backoff+jitter on transient HTTP errors, `busy_timeout`+WAL, run summary counts, atomic `grab_params.json` write | Makes failures diagnosable; enables safe concurrency | A failed run leaves log lines with URL/status/attempt; two concurrent runs do not raise `database is locked`; JSON write is tmp+rename |
| 8 | **P2** | Docs sync: `AGENTS.md`/`CLAUDE.md`/`python_scripts/README.md`/`_archive/README.md` to match code; decide fate of `main.py` (single CLI) vs scripts | Onboarding accuracy | Docs commands verified from a fresh checkout |
| 9 | **P2** | Decide the browser-scraper question: keep Selenium (optional extra, new headless mode) or drop it (requests-only + selector strategies) | Selenium is absent locally and heavyweight; currently nothing in the production path needs it | `browser_scraper` either behind an extra with a smoke test, or deleted |

First three items are intentionally small and unblock the rest; #4 is the one that pays down the 893 LoC + 4-pipeline duplication.

---

## 5. Verification evidence (commands actually run)

All commands read-only; no crawler/fetch/backfill/clean/main was executed. `/tmp` probes used throwaway directories.

1. Inventory/LoC: `wc -l python_scripts/**/*.py`; `R.lg`-style AST scan for cross-file duplicate function bodies → 7 exact duplicates (all trivial dunders/base stubs), plus `difflib` similarity for near-duplicates (0.93/0.96/0.73/0.67 above).
2. Runtime probe: `python3 --version` → 3.11.15; `python3 -m pip list | grep -iE 'requests|beautifulsoup|selenium|openai|dotenv|lxml|pytest|urllib3'` → selenium/openai missing.
3. Import coupling: `python3 -c "from web_content_system.config import Config"` and `...database import DatabaseManager` → `ModuleNotFoundError: No module named 'selenium'` (traceback through `__init__`→`extractor`→`scrapers`→`browser_scraper`).
4. Test reality: `python3 -m pytest test_modular.py test_system.py --collect-only -q` → `5 tests collected, 1 error` (test_system import).
5. Schema fork (in `/tmp`, importing `db_manager.py` directly): fresh DB columns `['id','title','created_time','summary','original_url','tags','uid']`.
6. Crash probe (in `/tmp`): legacy table + 2 rows same URL + `DatabaseManager('legacy.db')` → `sqlite3.IntegrityError: UNIQUE constraint failed: content_summary.uid`.
7. Live DB read-only: `sqlite3("file:python_scripts/web_content.db?mode=ro", uri=True)` → tables/indexes/columns as in §1; 192 rows, 190 content, 2 NULL uid, 0 duplicate URLs, integrity ok.
8. Static side (cross-ref only): parsed `src/assets/static-data.js` → 143 rows, all 7 categories populated; `static-data.json` → 111 rows, 0 with `category`; DB schema has no `category`; `generate-data.js` SELECT (lines ~94-102) omits it.
9. Greps: no `logging` usage; no `retry|backoff|busy_timeout|journal_mode|WAL`; no TODO/FIXME markers.
10. Git timeline: `git log --oneline --date=iso -- python_scripts src/assets/static-data.js` → last Python change 2026-09-02 (adds 6 roots); DB mtime 2026-08-28 13:22; `static-data.js` mtime 2026-08-28 10:45.
11. `grab_params.json` status: 17 entries, 15 done, 2 pending.

---

## 6. Assumptions and limitations

- Read-only audit. No network calls, no crawler/fetch/backfill/clean/main execution, no repo DB writes. The `/tmp` probes create and discard their own files.
- "Current state" = working tree at commit `22544ca` plus uncommitted state observed on 2026-10-18 23:00 Asia/Shanghai. Data counts/freshness will drift; code findings will not.
- Package-vs-scripts direction (F4) is a product/architecture decision (see §7); this audit deliberately does not pick one, only documents the cost of the current split.
- Duplication metrics are text/AST similarity, not a semantic proof; they identify hotspots, not an exhaustive clone list.
- Security and data-freshness findings are referenced from the sibling audits, not re-validated here.

## 7. Open decisions needed before implementation

1. **Package-first or scripts-first?** Either make `web_content_system` the single pipeline (needs deps + browser optionality) or reduce it to a shared library and keep the scripts as the interface. Current state — both, with different schemas — is the expensive option.
2. **`category` ownership** (Python assignment step vs frontend derivation) — shared decision with the data audit.
3. **Browser scraping**: keep as optional extra or remove?
4. **Python runtime target** for CI (3.11 locally; docs say 3.8; code needs ≥3.9).
5. **Is `main.py` still a supported entry point**, or can the three scripts be the only supported interface?
