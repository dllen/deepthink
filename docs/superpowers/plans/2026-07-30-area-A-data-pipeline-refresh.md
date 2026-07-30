# Area A — Data Pipeline Refresh

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deployed site actually display the latest `web_content.db` content, and ensure future DB updates automatically flow to the production bundle.

**Architecture:** Add a CI step that invokes `npm run gen:static-js` (which already exists) before `vite build` so the bundled `static-data.{json,js}` is always regenerated from the committed DB. Locally, run the same command and commit the refreshed files once now (the site is currently stale).

**Tech Stack:** Node.js ≥20 · npm · sql.js (already in devDeps) · GitHub Actions

**Preconditions:**
- `python_scripts/web_content.db` has the desired fresh content (currently 62 rows)
- `npm install` has been run (so `sql.js` and `javascript-obfuscator` are present locally)
- `SQLITE_KEY` is available as a GitHub Actions secret

---

## File Structure

| Path | Change |
|---|---|
| `.github/workflows/deploy.yml` | Modify — insert "Generate static data" step before "Build" |
| `src/assets/static-data.json` | Regenerate from current DB (committed in this PR) |
| `src/assets/static-data.js` | Regenerate from current DB (committed in this PR) |

No new files. No new code.

---

## Tasks

### Task 1: Verify local regeneration works

**Files:** None (read-only check)

- [ ] **Step 1: Run the generation script**

Run from repo root:
```bash
npm run gen:static-js
```

Expected: completes without error, prints `✅ Found 62 records in content_summary` (or equivalent success message) and writes `src/assets/static-data.{json,js}`.

- [ ] **Step 2: Confirm the new data is in the JSON**

Run:
```bash
python3 -c "import json; d=json.load(open('src/assets/static-data.json')); print('rows:', len(d)); print('first:', d[0]['title'])"
```

Expected: prints `rows: 62` (matches current DB row count) and `first: chuan.us` (or whatever the first row's title is — the order is `created_time DESC`).

- [ ] **Step 3: Confirm git diff shows changed assets**

Run:
```bash
git status --short src/assets/
```

Expected: `M src/assets/static-data.json` and `M src/assets/static-data.js`.

### Task 2: Commit the refreshed static data

**Files:**
- Modify: `src/assets/static-data.json`
- Modify: `src/assets/static-data.js`

- [ ] **Step 1: Commit**

Run:
```bash
git add src/assets/static-data.json src/assets/static-data.js
git commit -m "chore(data): refresh static-data from web_content.db (62 rows)"
```

Expected: one new commit. The deployed site, once this PR is merged and CI runs, will pick up these files via the existing build step.

### Task 3: Add CI step to regenerate before build

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: Locate the "Build project" step**

Open `.github/workflows/deploy.yml`. The current "Build project" step is:
```yaml
- name: Build project
  run: npm run build
```

- [ ] **Step 2: Insert generation step before build**

Add the following step immediately BEFORE the `- name: Build project` line:
```yaml
- name: Generate static data from web_content.db
  run: npm run gen:static-js
  env:
    SQLITE_KEY: ${{ secrets.SQLITE_KEY }}
```

The resulting block should look like:
```yaml
- name: Generate static data from web_content.db
  run: npm run gen:static-js
  env:
    SQLITE_KEY: ${{ secrets.SQLITE_KEY }}

- name: Build project
  run: npm run build
```

- [ ] **Step 3: Verify the YAML still parses**

Run:
```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))" && echo OK
```

If `pyyaml` is not installed, use any YAML validator. Expected: prints `OK`.

- [ ] **Step 4: Commit**

Run:
```bash
git add .github/workflows/deploy.yml
git commit -m "ci: regenerate static-data from DB before build"
```

Expected: one new commit. The next deploy after merge will run `gen:static-js` in CI before building.

### Task 4 (optional): Manual refresh workflow

**Files:**
- Modify: `.github/workflows/deploy.yml`

Only do this task if the user wants a `workflow_dispatch` trigger to force a fresh DB-driven regeneration without depending on a `main` push.

- [ ] **Step 1: Verify user wants it**

Skip this task unless explicitly requested. A push to `main` already regenerates static-data automatically after Task 3 lands.

---

## Self-Review

- **Spec coverage:** Audit § A1–A3 → Tasks 1, 2, 3 implement all three (local regen, commit, CI step). Manual refresh workflow (§ A3) is conditional.
- **Placeholder scan:** No "TBD"/"TODO"/"add appropriate handling". Code blocks are complete.
- **Type consistency:** No new types, methods, or props introduced. `npm run gen:static-js` is the existing entrypoint.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-A-data-pipeline-refresh.md`. Ready for execution. Recommended: **Subagent-Driven** for review between each task. Inline execution is fine for this small plan too.
