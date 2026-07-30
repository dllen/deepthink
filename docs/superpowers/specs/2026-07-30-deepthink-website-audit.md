# DeepThink Website Optimization Audit

**Date:** 2026-07-30
**Scope:** Audit only — no code changes in this document. Each finding requires
explicit user approval before an implementation plan is generated.
**Repo:** `dllen/deepthink` (main)

---

## Context

A full-codebase optimization audit of the `deepthink` project — a React + Vite
frontend that renders articles & analysis reports from an encrypted SQLite DB,
plus a Python scraping pipeline that populates the DB.

The audit followed the brainstorming skill (full deep-dive, option 3 per user
choice). This document records all findings so the user can pick which areas
to act on. **None of the items below have been implemented yet.**

### Project snapshot

- `src/` — ~854 LoC across 6 components + `App.jsx` + `sqliteReader.js`
- 62 rows live in `python_scripts/web_content.db` (just-crawled)
- Frontend reads from `src/assets/static-data.js` (last regenerated Jul 30 17:20,
  contains a stale 32-row dataset, not the new 62-row one)
- 4 scripts (`generate-data.js`, `encrypt-db.sh`, `crawler.py`,
  `crawler_subpages.py`, `fetch_and_add.py`)
- Stack: React 18 · Vite 4 · TailwindCSS 3 · Fuse.js 7 · sql.js 1.8

### Severity legend

- 🟥 **High** — visible user impact, dead code, or breaks functionality
- 🟧 **Medium** — clear improvement, low risk
- 🟨 **Low / cosmetic** — polish or future-proofing

---

## Findings

### A. Data pipeline disconnect — 🟥  (highest priority)

The new 62-row `web_content.db` (commit `e015e41`) **never reached the
browser**. The frontend reads `src/assets/static-data.js`, which still
contains the old dataset (id=32 "中国AI全明星深度对话AGI前沿", tags="AI",
mtime `Jul 30 17:20:09 2026` — pre-dating today's crawl).

The deploy workflow (`.github/workflows/deploy.yml`) runs only `npm run build`
— there's no step to invoke `npm run gen:static-js`.

**Proposed (area A):**
1. Add a CI step that runs `npm run gen:static-js` before `npm run build`,
   with `SQLITE_KEY` from the GitHub secret:
   ```yaml
   - name: Generate static data
     run: npm run gen:static-js
     env:
       SQLITE_KEY: ${{ secrets.SQLITE_KEY }}
   ```
2. After CI is wired, run `npm run gen:static-js` locally once to commit
   the refreshed `static-data.{json,js}` to `main`.
3. Consider a `workflow_dispatch` path so data refreshes don't require a
   rebuild of static assets.

---

### B. Dead code & dead runtime paths

#### B1. `src/utils/sqliteReader.js` (260 LoC) — 🟥

The whole runtime SQLite path is only reached as an error fallback when
`static-data.js` is missing. In normal operation it is unreachable. Also:
- Pulls `sql.js` (~1MB WASM) from `https://sql.js.org/dist/` at runtime
- The 8-row "fallback sample data" array is **duplicated** in two branches
  (`if (!file)` and the `catch` block)
- Bundles `sql.js` into the production build

**Proposed:**
- Delete `src/utils/sqliteReader.js`
- Remove `sql.js` and `sqlite-parser` from `dependencies` in `package.json`
- Remove the `readSQLiteData` error-path branch in `App.jsx` (lines ~21–37)
- **Bundle win:** ~1 MB raw (smaller after gzip), ~250 LoC source

#### B2. Three crawlers, one job — 🟧

The repository now contains:
- `python_scripts/fetch_and_add.py` (early single-URL fetcher)
- `python_scripts/crawler.py` (4-URL wipe-and-refill)
- `python_scripts/crawler_subpages.py` (append-only depth-1)

The first two are strictly subsets of what `crawler_subpages.py` can do.

**Proposed:**
- Make `crawler_subpages.py` the canonical tool
- Add a `--wipe` flag to `crawler_subpages.py` for the wipe-and-refill mode
  (so it can replace `crawler.py`)
- Move `fetch_and_add.py` to `python_scripts/_archive/` or delete
- Update `AGENTS.md` / `dev.md` to point at the new canonical entry point

#### B3. `App.jsx` Fuse indexes a key that doesn't exist — 🟨

```js
keys: ['title', 'content', 'summary']
```

`content` is `undefined` for every row in the loaded dataset (only `summary`
is populated). Fuse still has to look at it.

**Proposed:**
```js
keys: ['title', 'summary'], threshold: 0.35
```

#### B4. `scripts/generate-data.js` ships obfuscated JS for non-IP data — 🟧

`JavaScriptObfuscator` with `controlFlowFlattening: 0.75` is applied to
`static-data.js`. The data is **public article summaries** — nothing to
protect. The obfuscation adds ~3× file size and makes any production debug
session painful.

**Proposed:**
- Drop `JavaScriptObfuscator` and the `javascript-obfuscator` devDep
- Re-emit plain `export default [...]` for `static-data.js`

---

### C. Code quality / boundaries

#### C1. Duplicated `formatDate` helper — 🟧

Same date-formatting logic appears in three components with slightly
different output styles:
- `src/components/ContentCard.jsx`
- `src/components/ReportsPanel.jsx`
- `src/components/ReportModal.jsx`

**Proposed:** Extract to `src/utils/formatDate.js`:
```js
export const formatDate = (s, { withTime = false } = {}) =>
  new Date(s).toLocaleDateString('zh-CN', {
    year:   'numeric',
    month:  withTime ? '2-digit' : 'long',
    day:    withTime ? '2-digit' : 'numeric',
    hour:   withTime ? '2-digit' : undefined,
    minute: withTime ? '2-digit' : undefined,
  });
```
Adopt across the three components.

#### C2. `WaterfallGrid` visual order ≠ DOM order — 🟧

Uses CSS `columns-*` for the masonry layout. Reading/tab order runs column
by column, but visual order is left-to-right by row. Keyboard users get
non-intuitive focus jumps.

**Proposed (least-disruptive):** keep columns layout, add `tabIndex` and
`aria-posinset` so AT software can linearize. **Proposed (ideal):** switch
to a simple JS-masonry component or accept visual quirk until CSS grid
masonry lands in stable browsers.

Decision deferred — record as tech debt.

#### C3. `App.jsx` `filterData` not memoized — 🟨

`filterData` is rebuilt on every render. Wrap in `useCallback` keyed on
`[items, searchQuery, selectedTags]` for stability.

---

### D. UX / accessibility

#### D1. `ReportModal` animation classes don't exist — 🟥

```jsx
<div className="relative ... animate-in zoom-in-95 duration-200">
```

These classes come from the `tailwindcss-animate` plugin which is **not
installed** (only `tailwindcss@3.3.0` is in devDependencies). The modal
just snaps in with no animation — a visible UX bug.

**Choice A (recommended):** install plugin:
```bash
npm i -D tailwindcss-animate
```
```js
// tailwind.config.js
plugins: [require('tailwindcss-animate')]
```

**Choice B:** custom keyframe:
```css
@keyframes zoomIn { from { opacity:0; transform: scale(.95) } to { opacity:1; transform: scale(1) } }
.animate-in.zoom-in-95 { animation: zoomIn .2s ease-out }
```

Decision deferred — see Open Questions.

#### D2. `<html lang="en">` but the entire UI is Chinese — 🟧

```html
<html lang="zh-CN">
<meta name="description" content="观念棱镜 — 汇集深度思考与智慧洞见的瀑布流" />
```

#### D3. `TagFilter` buttons lack `aria-pressed` — 🟧

Add `aria-pressed={selectedTags.includes(tag)}` to the tag buttons so
screen readers announce the selected state.

#### D4. `SearchBar` input lacks an accessible label — 🟨

```jsx
<input aria-label="搜索内容" placeholder="搜索标题、内容或摘要..." ... />
```

#### D5. `ReportModal` iframe sandbox is ineffective — 🟧

```jsx
<iframe sandbox="allow-scripts allow-same-origin" />
```

Per MDN, `allow-scripts` + `allow-same-origin` together defeat the
sandbox (a script running under same-origin can remove the sandbox via
`document.write`). The reports are HTML we control, so the sandbox can
be tightened to deny by default:

**Proposed:**
```jsx
<iframe src={report.path} sandbox="" />
```

#### D6. Focus rings inconsistent across buttons — 🟨

Some buttons have `focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2`,
others have nothing. Standardize via a single class pattern, e.g.
`focus-visible:ring-2 focus-visible:ring-indigo-500`.

---

### E. Build / deploy / tooling

#### E1. `.db` files tracked despite `.gitignore` — 🟧

`.gitignore` lists `*.db` but `python_scripts/web_content.db{,.enc}` are
tracked. They were `git add -f`'d.

**Proposed:** keep tracked (intentional, the deploy workflow depends on
it). Add an explanatory comment to `.gitignore`:
```gitignore
# NOTE: python_scripts/web_content.db{,.enc} are intentionally tracked
# despite the *.db pattern below — the deploy workflow relies on them.
*.db
*.sqlite
*.sqlite3
```

#### E2. No lint/format scripts — 🟧

`package.json` has no `lint` script, no ESLint config in the repo.

**Proposed:**
```json
"scripts": { "lint": "eslint src --ext .js,.jsx" }
"devDependencies": { "eslint": "^9", "eslint-plugin-react": "^7", "eslint-plugin-react-hooks": "^5" }
```
Add `.eslintrc.cjs` with React + hooks rules.

#### E3. Vite `manualChunks` too narrow — 🟨

```js
manualChunks: { 'react': ['react', 'react-dom'] }
```
For an 854-LoC site this adds an extra request for marginal cache benefit.
Consider removing and letting Rollup auto-chunk. Audit with
`rollup-plugin-visualizer` once added.

#### E4. `dist/` correctly gitignored ✅

#### E5. `static/A股行业财政乘数矩阵看板.html` tracked — 🟨

`AGENTS.md` refers to `static/` as a "static page area" but the file is
committed rather than ignored. Either commit all report HTMLs intentionally
or gitignore them. Today's state: tracked.

#### E6. CI doesn't run any tests — 🟨 (forward-looking)

No tests today. When Vitest is added, wire it into `.github/workflows/deploy.yml`.

---

### F. Performance

#### F1. `static-data.json` shipped uncompressed — 🟨

GitHub Pages serves gzip/br only when file extensions are `.html`/`.css`/
`.js`, so JSON gets served uncompressed. Acceptable trade-off for 7 KB.

#### F2. `backdrop-blur-md` on sticky header — 🟨

GPU scroll cost. Acceptable for a small site.

#### F3. `WaterfallGrid` not virtualized — 🟨 (forward-looking)

At 62 rows, fine. At ~500+ rows consider `react-window` or `react-virtuoso`.

---

## Summary

Total findings: **~24** of which **6 are 🟥 high-impact**.
Roughly 1/3 are dead code / unused deps, 1/3 are quality / a11y, 1/3 are
build & data-pipeline hygiene.

### 🟥 High-impact list (in suggested order)

1. **A — Data pipeline** — refresh `static-data.*`, wire `gen:static-js`
   into CI; the deployed site is currently stale.
2. **B1 — Delete `sqliteReader.js` + drop `sql.js`/`sqlite-parser`** —
   1 MB bundle saving, 250 LoC deletion.
3. **D1 — `ReportModal` animation is dead** — fix or install plugin.

### Decomposition note

This audit identifies work in 6 distinct areas (A–F). They are independent
and can be implemented in separate PRs / sessions. The brainstorming skill
spec calls for "one project per spec → plan → implementation cycle". Treat
each finding-group (A, B, D1, …) as a candidate sub-project with its own
implementation plan.

---

## Open questions (need user input before planning)

1. **For D1 (animation):** Choice A (install `tailwindcss-animate`) or
   Choice B (custom CSS keyframe)? Choice A is more standard.
2. **For B1 (sqliteReader deletion):** should we keep any path for users
   to upload a custom `.db` from the browser (e.g., a dev-only flag)?
   Or is the static-data-only path the product direction?
3. **For B4 (drop obfuscator):** is there *any* IP concern in the data
   that would warrant keeping it?
4. **For C2 (masonry order):** keep current + add a11y hints, or schedule
   a real JS-masonry rewrite later?
5. **For B2 (consolidate crawlers):** confirm `crawler_subpages.py` is the
   intended canonical entry point, and decide whether `fetch_and_add.py`
   should be archived vs deleted.

---

## What this document is **not**

- Not an implementation plan (that's the next step, per the brainstorming
  skill, via the `writing-plans` skill)
- Not a refactor or rewrite proposal that has been agreed upon
- Not a performance benchmark (no measurements taken; estimates are
  ballpark only)

---

## Approval gate

Per the brainstorming skill, this design is **not yet approved**. The user
should select which (if any) areas they want acted on and resolve the
open questions above before an implementation plan is generated.
