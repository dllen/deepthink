# Archive

These scripts are kept for historical reference.

## fetch_and_add.py

Early single-URL fetcher. Superseded by `crawler_subpages.py` which provides:

- 4-URL canned list (`crawler_subpages.py` TARGETS) — covers the same URLs `fetch_and_add.py` was used for
- Append-only mode by default (uses `INSERT OR IGNORE` on the `uid` unique index)
- Optional full wipe if you really want to start over
- Same-domain sub-URL discovery with link filtering

Use `python crawler_subpages.py` for any new content-add.

## crawler.py

Removed in commit `723b095`. Its wipe-and-refill behavior is now an
optional mode on `crawler_subpages.py` if you need it (add `--wipe`
and a `reset_db()` call — not implemented today as the append mode
covers the common case).
