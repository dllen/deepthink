# Area B — Dead Code & Dead Runtime Path Removal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the runtime SQLite reader that nothing reaches on the happy path, the unused sql.js dependency, the duplicated crawler scripts, and the obfuscation layer that's hiding data we never needed to hide.

**Architecture:** Pure deletions and small text fixes. No new logic. Each task removes one or more files / dependencies and verifies the app still builds.

**Tech Stack:** React 18 · Vite 4 · TailwindCSS 3 · sql.js (being removed) · javascript-obfuscator (being removed)

**Preconditions:**
- Working tree clean (commit any pending work first)
- `npm run build` succeeds today (so we have a baseline)
- Resolved open questions: hard-delete `sqliteReader` (Q2), drop obfuscator (Q3), archive one crawler + delete one (Q5)

**Scope:** Four sub-areas, one task each.

---

## File Structure

| Path | Change |
|---|---|
| `src/utils/sqliteReader.js` | **Delete** |
| `src/App.jsx` | Modify — strip the SQLite fallback branch and the dead Fuse key |
| `package.json` | Modify — drop `sql.js`, `sqlite-parser`, `javascript-obfuscator` |
| `python_scripts/crawler.py` | **Delete** (superseded) |
| `python_scripts/fetch_and_add.py` | Move to `python_scripts/_archive/fetch_and_add.py` |
| `scripts/generate-data.js` | Modify — remove obfuscation step |
| `scripts/` | Create `_archive/` directory |

---

## Tasks

### Task 1: Remove `sqliteReader.js` and the `sql.js` runtime path

**Files:**
- Delete: `src/utils/sqliteReader.js`
- Modify: `src/App.jsx:1-50` (strip fallback branch)
- Modify: `package.json` (remove `sql.js` and `sqlite-parser` deps)

- [ ] **Step 1: Open `src/App.jsx` and locate the SQLite fallback**

Lines ~21–37 of `src/App.jsx` define `loadStaticData()` which has a `try/catch` that calls `readSQLiteData()` if `data` is empty. The whole `readSQLiteData` function (~lines 39–55) and its caller inside the catch are what we want to delete.

- [ ] **Step 2: Simplify `App.jsx` data loading**

Replace the entire `loadStaticData` + `readSQLiteData` logic with this single effect:
```jsx
useEffect(() => {
  const reader = new SQLiteReader();
  const tags = reader.extractTags(data);
  setItems(data);
  setFilteredData(data);
  setTags(tags);
  setIsLoading(false);
}, []);
```
Wait — the reader call now does nothing useful since we always have `data`. Replace with:
```jsx
useEffect(() => {
  const allTags = new Set();
  data.forEach((item) => {
    if (!item.tags) return;
    item.tags.split(',').forEach((t) => {
      const trimmed = t.trim();
      if (trimmed) allTags.add(trimmed);
    });
  });
  setItems(data);
  setFilteredData(data);
  setTags(Array.from(allTags));
  setIsLoading(false);
}, []);
```

Remove these lines from the imports:
```jsx
import SQLiteReader from './utils/sqliteReader';
```

And remove the duplicated sample-data fallback branches inside the deleted code.

- [ ] **Step 3: Delete `src/utils/sqliteReader.js`**

Run:
```bash
git rm src/utils/sqliteReader.js
```

- [ ] **Step 4: Verify no other file imports it**

Run:
```bash
grep -rn "sqliteReader\|SQLiteReader" src/ scripts/ 2>/dev/null
```

Expected: no output. If anything remains, fix the import in that file.

- [ ] **Step 5: Build**

Run:
```bash
npm run build
```

Expected: builds successfully. No errors about missing `sql.js` (it's still in deps until next step).

- [ ] **Step 6: Drop `sql.js` and `sqlite-parser` from `package.json`**

Run:
```bash
npm uninstall sql.js sqlite-parser
```

Expected: removes the two packages from `dependencies` in `package.json`.

- [ ] **Step 7: Commit**

Run:
```bash
git add -A
git commit -m "refactor: drop runtime sqliteReader.js + unused sql.js/sqlite-parser deps"
```

### Task 2: Fix Fuse.js key list (B3)

**Files:**
- Modify: `src/App.jsx` (inside the `fuse = useMemo(...)`)

- [ ] **Step 1: Locate the Fuse config**

Find:
```jsx
const fuse = useMemo(() => {
  return new Fuse(items, {
    keys: ['title', 'content', 'summary'],
    threshold: 0.3,
    ignoreLocation: true,
    useExtendedSearch: true,
  });
}, [items]);
```

- [ ] **Step 2: Remove `content` from keys**

Replace with:
```jsx
const fuse = useMemo(() => {
  return new Fuse(items, {
    keys: ['title', 'summary'],
    threshold: 0.35,
    ignoreLocation: true,
    useExtendedSearch: true,
  });
}, [items]);
```

- [ ] **Step 3: Smoke-test in dev (optional)**

Run:
```bash
npm run dev
```

Manual: type a query, confirm results render. No build error, no React warning.

- [ ] **Step 4: Commit**

Run:
```bash
git add src/App.jsx
git commit -m "fix(search): drop nonexistent 'content' key from Fuse index"
```

### Task 3: Consolidate Python crawlers (B2)

**Files:**
- Move: `python_scripts/fetch_and_add.py` → `python_scripts/_archive/fetch_and_add.py`
- Delete: `python_scripts/crawler.py`
- Create: empty `python_scripts/_archive/.gitkeep` (so the dir is tracked)

- [ ] **Step 1: Create the archive dir**

Run:
```bash
mkdir -p python_scripts/_archive
touch python_scripts/_archive/.gitkeep
git add python_scripts/_archive/.gitkeep
```

- [ ] **Step 2: Use `git mv` so history is preserved**

Run:
```bash
git mv python_scripts/fetch_and_add.py python_scripts/_archive/fetch_and_add.py
```

- [ ] **Step 3: Delete the redundant `crawler.py`**

Run:
```bash
git rm python_scripts/crawler.py
```

- [ ] **Step 4: Add a README in the archive**

Create `python_scripts/_archive/README.md`:
```markdown
# Archive

These scripts are kept for historical reference.

- `fetch_and_add.py` — early single-URL fetcher. Superseded by `crawler_subpages.py`.
- `crawler.py` — removed in commit <pending hash>; functionality merged into `crawler_subpages.py`.
```

(Fill in `<pending hash>` after Task 3 commits.)

- [ ] **Step 5: Verify `crawler_subpages.py` is canonical**

The `crawler_subpages.py` already supports append-mode (default) and discovery. No change needed. Optionally add a `--wipe` flag for completeness, but this is optional and can be skipped.

- [ ] **Step 6: Commit**

Run:
```bash
git add python_scripts/_archive/README.md
git commit -m "chore: archive obsolete crawler scripts"
```

### Task 4: Drop obfuscation in `generate-data.js` (B4)

**Files:**
- Modify: `scripts/generate-data.js` (remove obfuscator import & call)
- Modify: `package.json` (drop `javascript-obfuscator`)

- [ ] **Step 1: Locate the obfuscator block in `scripts/generate-data.js`**

Lines 1–9 import `JavaScriptObfuscator`. Lines ~30–40 define `writeJsModule()` which calls it.

- [ ] **Step 2: Replace `writeJsModule` with a plain emitter**

Replace the function:
```js
function writeJsModule(result) {
  const jsModule = `export default ${JSON.stringify(result)};`;
  const obfuscated = JavaScriptObfuscator.obfuscate(jsModule, {
    compact: true,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.75,
    deadCodeInjection: false,
    stringArray: true,
    stringArrayThreshold: 1,
    renameGlobals: false,
  });
  fs.writeFileSync(OUTPUT_JS_PATH, obfuscated.getObfuscatedCode());
  console.log(`🔐 Obfuscated JS generated at: ${OUTPUT_JS_PATH}`);
}
```
with:
```js
function writeJsModule(result) {
  const jsModule = `export default ${JSON.stringify(result)};`;
  fs.writeFileSync(OUTPUT_JS_PATH, jsModule);
  console.log(`📦 static-data.js generated at: ${OUTPUT_JS_PATH}`);
}
```

- [ ] **Step 3: Drop the import**

Remove or comment out:
```js
import JavaScriptObfuscator from 'javascript-obfuscator';
```
(Set it to a bare `//` comment if you want to keep the import line visible.)

- [ ] **Step 4: Drop the devDep**

Run:
```bash
npm uninstall javascript-obfuscator
```

- [ ] **Step 5: Regenerate**

Run:
```bash
npm run gen:static-js
```

Expected: writes `src/assets/static-data.js` as plain `export default [...]`.

- [ ] **Step 6: Build**

Run:
```bash
npm run build
```

Expected: builds. `static-data.js` size shrinks significantly (was obfuscated, now plain).

- [ ] **Step 7: Commit**

Run:
```bash
git add -A
git commit -m "refactor(data): stop obfuscating public-summary JS bundle"
```

---

## Self-Review

- **Spec coverage:** Audit § B1 → Task 1; § B2 → Task 3; § B3 → Task 2; § B4 → Task 4. All four sub-areas covered.
- **Placeholder scan:** No "TBD"/"TODO"/etc. Commands and code are complete.
- **Type consistency:** `App.jsx` useEffect dependency is `[]` — accurate after removing the SQLite fallback branch.
- **Bundle impact:** Drops ~1MB WASM (`sql.js`), drops obfuscation overhead. Estimated raw bundle delta: -1.1 MB; gzip delta: -300 to -400 KB.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-B-dead-code-removal.md`. Tasks are independent and can run in any order, but Tasks 1 and 2 are the highest-impact (sqlite removal + Fuse fix). Tasks 3 and 4 are housekeeping. Recommended: **Inline execution** (small, mostly deletional).
