# Performance Backlog (Area F)

Captured during the 2026-07-30 audit.
All items are deferred — there is no current user-visible perf complaint.

---

## F1 — Trim unused fields from `static-data.json`

**Status:** Resolved as a no-op.

The shipped dataset columns are: `id, title, created_time, summary,
original_url, tags`. Every column is consumed by the UI:

| Column | Where used |
|---|---|
| `id` | React `key` on cards & grid items |
| `title` | ContentCard heading + Fuse search |
| `created_time` | ContentCard timestamp + `created_time DESC` ordering |
| `summary` | ContentCard body text + Fuse search |
| `original_url` | ContentCard external-link icon |
| `tags` | TagFilter + ContentCard chip strip + tag-based Fuse filtering |

No trim is available without removing visible functionality. Future-proofing:
if a field stops being used, the `SELECT` in `scripts/generate-data.js` should
drop it.

---

## F2 — Profile `backdrop-blur` scroll impact

**Status:** Not measured (no browser session in the audit pipeline).

When you have access to Chrome DevTools:

1. `npm run build && npm run preview`
2. Open the preview URL in Chrome.
3. DevTools → Performance → record a 5-second trace while scrolling
   the page top-to-bottom at moderate speed.
4. Inspect the "Painting" / "Compositing" sections:
   - **Decision threshold:** if frames exceed 16 ms during scroll and
     `backdrop-blur-md` appears as the dominant compositor cost, replace
     it with a solid `bg-white/95` plus a subtle border.
   - **If frames stay under 16 ms:** keep `backdrop-blur-md` as-is.

The header (which is `sticky top-0 z-50 bg-white/80 backdrop-blur-md`)
is the only consumer of `backdrop-blur` in this codebase, so the fix is
a single substring change in `src/App.jsx`.

---

## F3 — Virtualize `WaterfallGrid` when scale grows

**Status:** Deferred.

- **Trigger condition:** when `static-data.json` exceeds ~500 rows
  AND Lighthouse INP (Interaction to Next Paint) exceeds 200 ms.
- **Library choice:** `react-window` (lightweight, 1D virtualizer) or
  `react-virtuoso` (better for masonry / variable heights) — switch to
  the latter if CSS columns are still in use at that point.
- **Files affected:** `src/components/WaterfallGrid.jsx` (the wrapper),
  `src/components/ContentCard.jsx` (no virtualization hooks, but the
  component must remain cheap to render off-screen).

Currently 70 rows render in well under 16 ms. No action today.

---

## How to use this file

This is a **planning artifact, not a spec**. When picking up one of these
items, copy it to `docs/superpowers/specs/YYYY-MM-DD-<feature>-design.md`
and run it through the brainstorming skill before implementing.
