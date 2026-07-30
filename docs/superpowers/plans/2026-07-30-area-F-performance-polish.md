# Area F — Performance Polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the two small performance improvements that are actionable today (F1 trim unused fields, F2 snapshot perf of `backdrop-blur` on scroll), and document the forward-looking items (F3 virtualization).

**Architecture:** One optional data trim + one optional measurement. No new code path.

**Tech Stack:** Node · browser devtools

**Scope note:** F1 and F2 are optional/measurable; F3 is documented as future work.

---

## File Structure

| Path | Change |
|---|---|
| `scripts/generate-data.js` | Modify (optional) — trim unused fields from emitted JSON |
| (no new files) | F2 — measure, no commit |
| `docs/superpowers/TODO.md` (new) | Optional — log forward-looking perf items |

---

## Tasks

### Task 1: Trim emitted fields from `static-data.json` (F1, optional)

**Files:**
- Modify: `scripts/generate-data.js`

- [ ] **Step 1: Verify the field set in source**

Current emit (from `generate-data.js`):
```js
result = res[0].values.map(row => {
  return columns.reduce((obj, col, i) => {
    obj[col] = row[i];
    return obj;
  }, {});
});
```

The columns in the SQL query are: `id, title, created_time, summary, original_url, tags`. All six are used in the UI; `tags` is split in the UI, `summary` is rendered.

- [ ] **Step 2: Skip — all fields are used**

After audit, **no trim is needed**. Mark this task as completed without a code change, or remove this task from the plan once acknowledged.

- [ ] **Step 3: Document this finding**

Add a note to a perf log:
```markdown
# Future Performance Improvements

## Tracked but no-op
- **F1:** `static-data.json` ships with all 6 columns (id, title, created_time, summary, original_url, tags). All 6 are used in the UI, so no trim opportunity today.

## Pending measurement
- **F2:** Measure FPS impact of `backdrop-blur-md` on sticky header in Chrome DevTools "Performance Insights" pane. Acceptable as-is for current content size.
```

(No commit required; this is a planning artifact.)

### Task 2: Profile `backdrop-blur` impact (F2, measurement only)

**Files:** None

- [ ] **Step 1: Build**

Run:
```bash
npm run build && npm run preview
```

Open the preview URL in Chrome.

- [ ] **Step 2: Open DevTools → Performance Insights**

Record a 5-second trace while scrolling the page top-to-bottom at moderate speed.

- [ ] **Step 3: Inspect frame timing**

If frames are > 16ms during scroll AND `backdrop-blur-md` is a top compositor cost, consider replacing with a solid `bg-white/90` or `bg-white/95` with a subtle border. Otherwise leave as-is (accept the visual cost for the polish).

- [ ] **Step 4: Document the finding**

Add a single line to `docs/superpowers/TODO.md`:
```markdown
## F2 — backdrop-blur impact (date)
Scroll FPS average: <X> ms; backdrop cost: <Y>%; decision: keep / replace with bg-white/95.
```

### Task 3: Document virtualization plan (F3, future)

**Files:**
- Create (optional): `docs/superpowers/TODO.md` (same file as Task 1/2) OR no action

- [ ] **Step 1: Record a tech-debt note**

If creating `TODO.md`, append:
```markdown
## F3 — Virtualize WaterfallGrid when >500 rows

- Library choice: `react-window` or `react-virtuoso`
- Trigger: when static-data.json exceeds 500 rows AND Lighthouse INP > 200ms
- Defer until either condition is met.
```

If not creating the file, skip — F3 is a known future item, tracked in the audit spec.

---

## Self-Review

- **Spec coverage:** Audit § F1 → Task 1 (resolved: no-op); § F2 → Task 2 (measurement); § F3 → Task 3 (deferred).
- **Placeholder scan:** No placeholders.
- **Type consistency:** n/a.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-30-area-F-performance-polish.md`. All three tasks are small / non-blocking. Recommended: **Inline execution** at your convenience, or skip if no perf complaints surface.
