# Area D — UX & Accessibility Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the silent failure of the `ReportModal` zoom-in animation, correct `<html lang>` and add a meta description, wire `aria-pressed` / `aria-label`, tighten the iframe sandbox, and unify focus styling.

**Architecture:** Small accessibility / correctness fixes. Each task touches one file. No new architecture.

**Tech Stack:** React 18 · TailwindCSS 3 · `tailwindcss-animate` (Choice A — recommended)

**Preconditions:**
- Working tree clean
- Resolved open questions: install `tailwindcss-animate` plugin (Q1)

---

## File Structure

| Path | Change |
|---|---|
| `package.json` | Modify — add `tailwindcss-animate` devDep |
| `tailwind.config.js` | Modify — register plugin |
| `src/components/ReportModal.jsx` | Modify (already references the classes) |
| `index.html` | Modify — `lang="zh-CN"`, add description |
| `src/components/TagFilter.jsx` | Modify — `aria-pressed` |
| `src/components/SearchBar.jsx` | Modify — `aria-label` |
| `src/components/ReportModal.jsx` | Modify — tighten iframe sandbox |

---

## Tasks

### Task 1: Install `tailwindcss-animate` and register it (D1)

**Files:**
- Modify: `package.json` (via npm)
- Modify: `tailwind.config.js`

- [ ] **Step 1: Install the plugin**

Run:
```bash
npm install -D tailwindcss-animate
```

Expected: new line in `devDependencies`.

- [ ] **Step 2: Register the plugin**

Open `tailwind.config.js` and replace the `plugins: []` line:
```js
plugins: [require('tailwindcss-animate')],
```
(Note: the top of `tailwind.config.js` uses ES module `export default`. Convert to CommonJS only if `require` complains, or use:
```js
import animate from 'tailwindcss-animate';
// ...
plugins: [animate],
```
which keeps ESM consistent.)

- [ ] **Step 3: Verify the animated classes now exist in the build**

Run:
```bash
npm run build
```

Expected: builds. The `animate-in zoom-in-95 duration-200` classes on `ReportModal` will now produce a working animation.

- [ ] **Step 4: Commit**

Run:
```bash
git add package.json package-lock.json tailwind.config.js
git commit -m "feat(modal): wire tailwindcss-animate for report zoom-in"
```

### Task 2: Update `index.html` language and metadata (D2)

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Update `lang` and add description**

Replace the file contents with:
```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="观念棱镜 — 汇集深度思考与智慧洞见的瀑布流。" />
    <title>观念棱镜</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Build**

Run:
```bash
npm run build
```

Expected: builds. The served HTML now has `lang="zh-CN"` and a `meta[name=description]`.

- [ ] **Step 3: Commit**

Run:
```bash
git add index.html
git commit -m "a11y(html): set lang=zh-CN and add meta description"
```

### Task 3: Add `aria-pressed` to `TagFilter` (D3)

**Files:**
- Modify: `src/components/TagFilter.jsx`

- [ ] **Step 1: Update the tag button**

The current button:
```jsx
<button
  key={tag}
  onClick={() => onTagToggle(tag)}
  className={...}
>
```

Change to:
```jsx
<button
  key={tag}
  onClick={() => onTagToggle(tag)}
  aria-pressed={selectedTags.includes(tag)}
  className={...}
>
```

Also add `aria-pressed` to the "全部内容" button (its state is the inverse of any filter being active):
```jsx
<button
  onClick={onClearFilters}
  aria-pressed={selectedTags.length === 0}
  className={...}
>
```

- [ ] **Step 2: Build**

Run:
```bash
npm run build
```

Expected: builds.

- [ ] **Step 3: Commit**

Run:
```bash
git add src/components/TagFilter.jsx
git commit -m "a11y(tags): expose selected state with aria-pressed"
```

### Task 4: Add `aria-label` to `SearchBar` input (D4)

**Files:**
- Modify: `src/components/SearchBar.jsx`

- [ ] **Step 1: Update the input**

Change:
```jsx
<input
  type="text"
  value={searchQuery}
  onChange={(e) => onSearchChange(e.target.value)}
  placeholder="搜索标题、内容或摘要..."
  className="..."
/>
```

to:
```jsx
<input
  type="text"
  value={searchQuery}
  onChange={(e) => onSearchChange(e.target.value)}
  placeholder="搜索标题、内容或摘要..."
  aria-label="搜索内容"
  className="..."
/>
```

- [ ] **Step 2: Commit**

Run:
```bash
git add src/components/SearchBar.jsx
git commit -m "a11y(search): add aria-label to search input"
```

### Task 5: Tighten `ReportModal` iframe sandbox (D5)

**Files:**
- Modify: `src/components/ReportModal.jsx`

- [ ] **Step 1: Remove the ineffective attributes**

Change:
```jsx
<iframe
  src={report.path}
  title={report.title}
  className="..."
  sandbox="allow-scripts allow-same-origin"
/>
```

to:
```jsx
<iframe
  src={report.path}
  title={report.title}
  className="..."
  sandbox=""
/>
```

`allow-scripts + allow-same-origin` together let a co-origin script escape the sandbox via `document.write`. We control the report HTML and don't need scripts there.

- [ ] **Step 2: Verify report HTML opens**

The report at `/public/A股行业财政乘数矩阵看板.html` should still load correctly inside the modal (it's static HTML with no scripts in the current set).

- [ ] **Step 3: Commit**

Run:
```bash
git add src/components/ReportModal.jsx
git commit -m "security(modal): tighten iframe sandbox (no permissions)"
```

### Task 6: Standardize focus rings (D6)

**Files:**
- Modify: `src/components/ReportsPanel.jsx`
- Modify: `src/components/ReportModal.jsx`
- Modify: `src/components/TagFilter.jsx`

- [ ] **Step 1: Adopt a uniform focus pattern**

Where `className` on a clickable element ends without a focus ring, append (one of):

For primary buttons:
```jsx
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
```

For icon-only buttons:
```jsx
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
```

Specifically:
- `ReportsPanel.jsx` card div: leave as div — add `role="button"`, `tabIndex={0}`, and an `onKeyDown` handler (`if (e.key === 'Enter' || e.key === ' ') setActiveReport(report)`).
- `ReportModal.jsx` icon-only close button: add focus ring (currently `hover:bg-slate-200` only).
- `TagFilter.jsx` "全部内容" button: add focus ring.

(Icon-link "新窗口" anchor in modal already inherits browser default focus styling — leave it.)

- [ ] **Step 2: Build**

Run:
```bash
npm run build
```

- [ ] **Step 3: Smoke-test in dev**

Run:
```bash
npm run dev
```

Press `Tab` through the page; the focus outline should be visible on every interactive element.

- [ ] **Step 4: Commit**

Run:
```bash
git add -A
git commit -m "a11y(focus): standardize visible focus rings across interactive elements"
```

---

## Self-Review

- **Spec coverage:** Audit § D1 → Task 1; § D2 → Task 2; § D3 → Task 3; § D4 → Task 4; § D5 → Task 5; § D6 → Task 6. All covered.
- **Placeholder scan:** No placeholders.
- **Type consistency:** All ARIA attributes used are valid `aria-*` boolean / string attrs.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-D-ux-a11y-fixes.md`. Recommended: **Inline execution** with a quick visual smoke-test after Tasks 1 + 2.
