# Area E — Build / Tooling Cleanup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clarify the intentional-vs-accidental status of tracked `.db` files, add ESLint config + lint script, reconsider the `vite manualChunks` setting, decide whether `static/` HTML files are intentional.

**Architecture:** Pure config / metadata changes. No application logic.

**Tech Stack:** ESLint 9 · React plugin · React-Hooks plugin · Vite 4

---

## File Structure

| Path | Change |
|---|---|
| `.gitignore` | Modify — add explanatory comment near `*.db` |
| `package.json` | Modify — add `lint` script + ESLint deps |
| `.eslintrc.cjs` | **Create** — flat-ish config with React rules |
| `vite.config.js` | Modify — drop aggressive manualChunks |
| `.gitignore` | Modify (optional) — decide static/ status |

---

## Tasks

### Task 1: Clarify `.gitignore` for tracked DB files (E1)

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add an explanatory comment**

Open `.gitignore` and locate the block:
```
# Database files
*.db
*.sqlite
*.sqlite3
```

Replace with:
```gitignore
# Database files (raw DB is intentionally tracked via `git add -f`,
# because the deploy workflow depends on python_scripts/web_content.db{,.enc}.
# See AGENTS.md / dev.md "Database Content Security" for context.)
*.db
*.sqlite
*.sqlite3
```

- [ ] **Step 2: Commit**

Run:
```bash
git add .gitignore
git commit -m "docs(gitignore): explain why .db files are tracked"
```

### Task 2: Add ESLint config + lint script (E2)

**Files:**
- Create: `eslint.config.js` (ESLint 9 flat config)
- Create: `package.json` `lint` script

- [ ] **Step 1: Install ESLint and plugins**

Run:
```bash
npm install -D eslint eslint-plugin-react eslint-plugin-react-hooks
```

- [ ] **Step 2: Write the flat config**

Create `eslint.config.js` at the repo root:
```js
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    plugins: { react, 'react-hooks': reactHooks },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { window: 'readonly', document: 'readonly' },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    settings: { react: { version: 'detect' } },
    rules: {
      'react/jsx-uses-react': 'off', // React 17+ JSX transform
      'react/react-in-jsx-scope': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**', 'src/assets/static-data.js', 'src/assets/static-reports.js'],
  },
];
```

If `@eslint/js` is not present, also run:
```bash
npm install -D @eslint/js
```

- [ ] **Step 3: Add the lint script**

In `package.json`:
```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "lint": "eslint src docs scripts",
  "gen:static-js": "node scripts/generate-data.js --from-json"
}
```

- [ ] **Step 4: Run lint on existing code**

Run:
```bash
npm run lint
```

Expected: at least some warnings on existing JS (that's normal for legacy code). Capture the count.

- [ ] **Step 5: Commit**

Run:
```bash
git add package.json package-lock.json eslint.config.js
git commit -m "chore(lint): add ESLint flat config + lint script"
```

### Task 3: Drop the `manualChunks` `react` chunk (E3)

**Files:**
- Modify: `vite.config.js`

- [ ] **Step 1: Locate the block**

Find:
```js
build: {
  outDir: 'dist',
  assetsDir: 'assets',
  rollupOptions: {
    output: {
      manualChunks: {
        'react': ['react', 'react-dom'],
      },
    },
  },
},
```

- [ ] **Step 2: Remove the manual chunk**

Replace with:
```js
build: {
  outDir: 'dist',
  assetsDir: 'assets',
},
```

For 854 LoC of code, the vendor chunk adds an extra request without meaningful cache benefits.

- [ ] **Step 3: Verify the build output**

Run:
```bash
npm run build
ls -la dist/assets/ | head -10
```

Expected: still produces chunks, but no separate `react` file.

- [ ] **Step 4: Commit**

Run:
```bash
git add vite.config.js
git commit -m "chore(vite): drop manualChunks react split (small codebase)"
```

### Task 4 (optional): Decide on `static/` HTML tracking (E5)

**Files:**
- Modify: `.gitignore`

Only do this task if the user wants `static/*.html` to NOT be tracked.

- [ ] **Step 1: Ask the user**

Verify the user's intent. The current state — `static/A股行业财政乘数矩阵看板.html` is tracked — is fine if it's intended as part of the deployed artifact. If it's meant to be a developer's scratch space:
```gitignore
# Per-user static analysis dashboards (not part of the deployed site)
static/*.html
!static/README.md
```
tracked explicitly via `!static/README.md`.

- [ ] **Step 2: Commit if changed**

Run:
```bash
git add .gitignore
git commit -m "chore(gitignore): clarify static/*.html tracking"
```

---

## Self-Review

- **Spec coverage:** Audit § E1 → Task 1; § E2 → Task 2; § E3 → Task 3; § E4 → done in Area B Task 4; § E5 → Task 4. (E6 testing slot is forward-looking — no implementation today.)
- **Placeholder scan:** No placeholders.
- **Type consistency:** ESLint config is self-contained.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-E-build-tooling.md`. Recommended: **Inline execution**. After Tasks 2 + 3 run, you may wish to address any new ESLint warnings in source files (separate small change; out of scope of this plan).
