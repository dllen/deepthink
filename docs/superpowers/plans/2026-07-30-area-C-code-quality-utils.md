# Area C — Code Quality & Utilities

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the duplicated `formatDate` logic, optionally clean up `filterData` memoization, and add a minor a11y hint to `WaterfallGrid`.

**Architecture:** Pure refactor — extract shared date helper to `src/utils/formatDate.js`, replace three component-local copies with imports, then add `aria-posinset` to the masonry so screen readers can linearize.

**Tech Stack:** React 18 · JavaScript (no TS), standard library

**Preconditions:** none beyond clean working tree

**Resolved open questions:**
- Q4 (C2 masonry): keep current CSS columns + add a11y hint, defer real rewrite

---

## File Structure

| Path | Change |
|---|---|
| `src/utils/formatDate.js` | **Create** — shared date helper |
| `src/components/ContentCard.jsx` | Modify — adopt shared helper |
| `src/components/ReportsPanel.jsx` | Modify — adopt shared helper |
| `src/components/ReportModal.jsx` | Modify — adopt shared helper |
| `src/App.jsx` | Modify — wrap `filterData` in `useCallback` |
| `src/components/WaterfallGrid.jsx` | Modify — add `aria-posinset` |

---

## Tasks

### Task 1: Create shared `formatDate` helper

**Files:**
- Create: `src/utils/formatDate.js`

- [ ] **Step 1: Write the helper**

Create `src/utils/formatDate.js`:
```js
/**
 * Format an ISO-ish date string for display.
 *
 * @param {string|Date} input
 * @param {{ withTime?: boolean, monthStyle?: 'long' | '2-digit' }} [opts]
 * @returns {string}
 */
export function formatDate(input, opts = {}) {
  const { withTime = false, monthStyle = 'long' } = opts;
  const d = input instanceof Date ? input : new Date(input);
  if (Number.isNaN(d.getTime())) return '';

  const month = monthStyle === '2-digit' ? '2-digit' : 'long';
  const day = monthStyle === 'long' ? 'numeric' : '2-digit';

  const fmt = {
    year: 'numeric',
    month,
    day,
  };
  if (withTime) {
    fmt.hour = '2-digit';
    fmt.minute = '2-digit';
  }

  return d.toLocaleDateString('zh-CN', fmt);
}
```

- [ ] **Step 2: Commit**

Run:
```bash
git add src/utils/formatDate.js
git commit -m "refactor: add shared formatDate helper"
```

### Task 2: Adopt helper in `ContentCard.jsx`

**Files:**
- Modify: `src/components/ContentCard.jsx:1-15`

- [ ] **Step 1: Replace local `formatDate`**

The current file has a `formatDate` at the top. Replace it with an import:
```jsx
import { formatDate } from '../utils/formatDate';
```

And update the call site:
```jsx
<span className="...">
  {formatDate(item.created_time, { monthStyle: '2-digit', withTime: true })}
</span>
```

(Was: `formatDate(item.created_time)` with local helper that included time.)

- [ ] **Step 2: Verify visually in dev (optional)**

Run:
```bash
npm run dev
```

Open the page. Card timestamps should still show `YYYY-MM-DD HH:MM` format.

- [ ] **Step 3: Commit**

Run:
```bash
git add src/components/ContentCard.jsx
git commit -m "refactor(card): use shared formatDate helper"
```

### Task 3: Adopt helper in `ReportsPanel.jsx` and `ReportModal.jsx`

**Files:**
- Modify: `src/components/ReportsPanel.jsx:1-15`
- Modify: `src/components/ReportModal.jsx:1-15`

- [ ] **Step 1: Replace local `formatDate` in `ReportsPanel.jsx`**

Replace the function definition and the call site:
```jsx
import { formatDate } from '../utils/formatDate';
// ...
<span className="text-xs text-slate-400">
  {formatDate(report.date)}
</span>
```

(Reports panel uses long month + no time — default behavior.)

- [ ] **Step 2: Replace local `formatDate` in `ReportModal.jsx`**

Same pattern:
```jsx
import { formatDate } from '../utils/formatDate';
// ...
<p className="text-xs text-slate-400 mt-0.5">
  {formatDate(report.date)}
  {/* tags block stays unchanged */}
</p>
```

- [ ] **Step 3: Build**

Run:
```bash
npm run build
```

Expected: passes.

- [ ] **Step 4: Commit**

Run:
```bash
git add src/components/ReportsPanel.jsx src/components/ReportModal.jsx
git commit -m "refactor(reports): use shared formatDate helper"
```

### Task 4: Memoize `filterData` (C3)

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: Locate the existing `filterData`**

In `src/App.jsx`, find:
```jsx
const filterData = () => {
  let result = items;
  // ...
};
```

- [ ] **Step 2: Convert to `useCallback`**

Replace with:
```jsx
import { useCallback, useEffect, useMemo, useState } from 'react';
// ...
const filterData = useCallback(() => {
  let result = items;

  if (searchQuery.trim()) {
    const searchResults = fuse.search(searchQuery);
    result = searchResults.map((r) => r.item);
  }

  if (selectedTags.length > 0) {
    result = result.filter((item) => {
      const itemTags = item.tags.split(',').map((tag) => tag.trim());
      return selectedTags.some((tag) => itemTags.includes(tag));
    });
  }

  setFilteredData(result);
}, [items, searchQuery, selectedTags, fuse]);
```

- [ ] **Step 3: Verify build**

Run:
```bash
npm run build
```

Expected: passes.

- [ ] **Step 4: Commit**

Run:
```bash
git add src/App.jsx
git commit -m "refactor(app): memoize filterData with useCallback"
```

### Task 5: Add `aria-posinset` to `WaterfallGrid` (C2)

**Files:**
- Modify: `src/components/WaterfallGrid.jsx`

- [ ] **Step 1: Update the map**

Change:
```jsx
{data.map((item) => (
  <div key={item.id} className="break-inside-avoid">
    <ContentCard item={item} />
  </div>
))}
```
to:
```jsx
{data.map((item, idx) => (
  <div
    key={item.id}
    className="break-inside-avoid"
    role="group"
    aria-posinset={idx + 1}
    aria-setsize={data.length}
  >
    <ContentCard item={item} />
  </div>
))}
```

This signals to AT software that items are linearized `idx + 1` of `data.length` even though visually they're laid out by CSS columns.

- [ ] **Step 2: Commit**

Run:
```bash
git add src/components/WaterfallGrid.jsx
git commit -m "a11y(grid): expose linear position for screen readers"
```

---

## Self-Review

- **Spec coverage:** Audit § C1 → Tasks 1, 2, 3; § C2 → Task 5; § C3 → Task 4. All covered.
- **Placeholder scan:** No "TBD"/"etc.". All code samples complete.
- **Type consistency:** `formatDate` signature used the same in all callers. `aria-posinset` is a valid ARIA 1.1 attribute (no new types introduced).
- **Risk:** low. Pure refactor + 2-line a11y hint.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-C-code-quality-utils.md`. Tasks 1–5 are independent and safely batchable. Recommended: **Inline execution**.
