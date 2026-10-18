# S1 数据真源统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `web_content.db` 成为站点唯一数据真源：`category` 落库、32 条手工内容入库、生成器单向可校验、CI 拦住数据漂移。

**Architecture:** 迁移脚本一次把 DB 补成完整真源（加列、补 uid、导入手工内容、LLM 分类）；分类器同时供迁移与抓取入库复用；生成器改为“DB → 校验 → 原子写 `static-data.json`/`.js`”；`check:data` 与生成器共用同一套规则，CI 在 build 前执行。

**Tech Stack:** Node 20+（ESM、`node:test`、sql.js）、Python 3.11（sqlite3、openai SDK、dotenv）、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-10-18-data-source-of-truth-design.md`

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `scripts/lib/data-rules.mjs` | 七类枚举 + 行校验 + DB/生成物一致性比较（生成器与检查脚本共用） |
| `scripts/lib/data-rules.test.mjs` | 规则单测 |
| `scripts/lib/db.mjs` | 用 sql.js 只读读取 DB 并返回行数组（生成器与检查脚本共用） |
| `scripts/generate-data.js` | 唯一生成入口：读 DB → 校验 → 原子写两个数据文件 |
| `scripts/check-data.mjs` | CI 用：校验 DB 与已提交生成物一致 |
| `python_scripts/category_classifier.py` | 七分类分类器（独立模块，不依赖 `web_content_system`） |
| `python_scripts/test_category_classifier.py` | 分类器单测（假 client） |
| `python_scripts/migrate_category.py` | 一次性迁移脚本（加列、补 uid、导入手工内容、回填分类） |
| `python_scripts/test_migrate_category.py` | 迁移脚本单测（临时 DB） |
| `python_scripts/set_category.py` | 人工修正分类 |
| `python_scripts/test_set_category.py` | 人工修正单测 |
| `python_scripts/test_ingestion_category.py` | 入库分类单测 |
| `python_scripts/fetch_from_params.py` | 修改：入库写分类、schema 补列 |
| `python_scripts/crawler_subpages.py` | 修改：入库写分类、schema 补列 |

---

## Task 1: JS 数据规则模块

**Files:**
- Create: `scripts/lib/data-rules.mjs`
- Test: `scripts/lib/data-rules.test.mjs`

- [ ] **Step 1: 写失败测试**

```js
// scripts/lib/data-rules.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateRows, compareDatasets } from './data-rules.mjs';

const base = {
  id: 1,
  title: '标题',
  category: '文章',
  tags: 'AI',
  created_time: '2026-08-28 13:22:58',
  summary: '摘要',
  original_url: 'https://example.com/a',
};

test('合法数据通过', () => {
  const r = validateRows([base]);
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.deepEqual(r.errors, []);
});

test('缺 category 报错', () => {
  const r = validateRows([{ ...base, category: undefined }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /category 非法/);
});

test('重复 id 报错', () => {
  const r = validateRows([base, { ...base, title: '另一条' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /id 重复/);
});

test('空 tags 报错', () => {
  const r = validateRows([{ ...base, tags: '  ' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /tags 为空/);
});

test('坏时间报错', () => {
  const r = validateRows([{ ...base, created_time: '2026/08/28' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /created_time 无法解析/);
});

test('缩水超过 10% 报错，allowShrink 放行', () => {
  const rows = [base, { ...base, id: 2 }, { ...base, id: 3 }];
  const blocked = validateRows(rows, { previousCount: 4 });
  assert.equal(blocked.ok, false);
  assert.match(blocked.errors.join('\n'), /缩水阈值/);

  const allowed = validateRows(rows, { previousCount: 4, allowShrink: true });
  assert.equal(allowed.ok, true, JSON.stringify(allowed.errors));
});

test('compareDatasets 发现条数与字段差异', () => {
  const published = [
    { ...base, category: '工具' }, // 字段不同
    { ...base, id: 3 },             // 多出
  ];
  const r = compareDatasets([base], published);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /条数不一致/);
  assert.match(r.errors.join('\n'), /字段 category 不一致/);
  assert.match(r.errors.join('\n'), /生成物多出/);
});

test('compareDatasets 一致时通过', () => {
  const r = compareDatasets([base], [{ ...base }]);
  assert.equal(r.ok, true, JSON.stringify(r.errors));
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test scripts/lib/data-rules.test.mjs`
Expected: FAIL，报错 `Cannot find module './data-rules.mjs'` 或 `validateRows is not a function`。

- [ ] **Step 3: 实现规则模块**

```js
// scripts/lib/data-rules.mjs
export const CATEGORIES = ['科技动态', '文章', '工具', '资源', '图片', '文摘', '言论'];
export const TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
export const SHRINK_TOLERANCE = 0.1;
export const COMPARED_FIELDS = [
  'title', 'category', 'created_time', 'summary', 'original_url', 'tags',
];

export function validateRows(rows, { previousCount = null, allowShrink = false } = {}) {
  const errors = [];
  const warnings = [];
  if (!Array.isArray(rows) || rows.length === 0) {
    return { ok: false, errors: ['数据为空'], warnings };
  }

  const ids = new Set();
  for (const [i, row] of rows.entries()) {
    const where = row && row.id !== undefined ? `id=${row.id}` : `第 ${i} 行`;
    if (!row || typeof row !== 'object' || Array.isArray(row)) {
      errors.push(`${where}: 不是对象`);
      continue;
    }
    if (!Number.isInteger(row.id)) errors.push(`${where}: id 不是整数`);
    if (!String(row.title ?? '').trim()) errors.push(`${where}: title 为空`);
    if (!CATEGORIES.includes(row.category)) {
      errors.push(`${where}: category 非法 (${JSON.stringify(row.category)})`);
    }
    if (!String(row.tags ?? '').trim()) errors.push(`${where}: tags 为空`);
    if (!TIMESTAMP_RE.test(String(row.created_time ?? ''))) {
      errors.push(`${where}: created_time 无法解析 (${JSON.stringify(row.created_time)})`);
    }
    if (row.original_url != null && typeof row.original_url !== 'string') {
      errors.push(`${where}: original_url 类型错误`);
    }
    if (ids.has(row.id)) errors.push(`${where}: id 重复`);
    ids.add(row.id);
  }

  if (previousCount != null && previousCount > 0) {
    const limit = Math.ceil(previousCount * (1 - SHRINK_TOLERANCE));
    if (rows.length < limit && !allowShrink) {
      errors.push(
        `行数从 ${previousCount} 降到 ${rows.length}，超过 ${SHRINK_TOLERANCE * 100}% 缩水阈值（用 --allow-shrink 放行）`,
      );
    }
  }

  const seenUrl = new Map();
  for (const row of rows) {
    const key = row.original_url || '';
    if (!key) continue;
    if (seenUrl.has(key)) {
      warnings.push(`original_url 重复: ${key}（id ${seenUrl.get(key)} 与 ${row.id}）`);
    } else {
      seenUrl.set(key, row.id);
    }
  }

  return { ok: errors.length === 0, errors, warnings };
}

export function compareDatasets(dbRows, publishedRows) {
  const errors = [];
  const dbById = new Map(dbRows.map((r) => [r.id, r]));
  const pubById = new Map(publishedRows.map((r) => [r.id, r]));

  if (dbRows.length !== publishedRows.length) {
    errors.push(`条数不一致: DB ${dbRows.length} vs 生成物 ${publishedRows.length}`);
  }
  for (const id of dbById.keys()) {
    if (!pubById.has(id)) errors.push(`生成物缺少 DB 行 id=${id}`);
  }
  for (const id of pubById.keys()) {
    if (!dbById.has(id)) errors.push(`生成物多出 DB 不存在的行 id=${id}`);
  }
  for (const [id, dbRow] of dbById) {
    const pub = pubById.get(id);
    if (!pub) continue;
    for (const field of COMPARED_FIELDS) {
      if ((pub[field] ?? null) !== (dbRow[field] ?? null)) {
        errors.push(`id=${id} 字段 ${field} 不一致`);
      }
    }
  }
  return { ok: errors.length === 0, errors };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test scripts/lib/data-rules.test.mjs`
Expected: `# pass 8`、`# fail 0`。

- [ ] **Step 5: 提交**

```bash
git add scripts/lib/data-rules.mjs scripts/lib/data-rules.test.mjs
git commit -m "feat(data): add shared validation rules for dataset generation"
```

---

## Task 2: Python 七分类分类器

**Files:**
- Create: `python_scripts/category_classifier.py`
- Test: `python_scripts/test_category_classifier.py`

- [ ] **Step 1: 写失败测试**

```python
# python_scripts/test_category_classifier.py
import json
from unittest.mock import patch

from category_classifier import CATEGORIES, DEFAULT_CATEGORY, classify_batch, classify_one


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self._content)


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content):
        self.chat = FakeChat(content)


def test_batch_maps_valid_labels():
    payload = json.dumps([
        {"index": 0, "category": "工具"},
        {"index": 1, "category": "言论"},
    ])
    out = classify_batch([{"title": "a"}, {"title": "b"}], client=FakeClient(payload))
    assert out == ["工具", "言论"]


def test_batch_ignores_invalid_label_and_index():
    payload = json.dumps([
        {"index": 0, "category": "不存在的类"},
        {"index": 9, "category": "文章"},
    ])
    out = classify_batch([{"title": "a"}], client=FakeClient(payload))
    assert out == [None]


def test_batch_returns_none_on_bad_json():
    out = classify_batch([{"title": "a"}], client=FakeClient("not json"))
    assert out == [None]


def test_batch_returns_none_on_client_error():
    class Broken:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("boom")

    out = classify_batch([{"title": "a"}], client=Broken())
    assert out == [None]


def test_classify_one_defaults_when_client_missing():
    with patch("category_classifier.make_client", return_value=None):
        assert classify_one("标题", "摘要") is None
    assert DEFAULT_CATEGORY in CATEGORIES


def test_prompt_contains_all_categories():
    client = FakeClient(json.dumps([{"index": 0, "category": "文章"}]))
    classify_batch([{"title": "a"}], client=client)
    user_msg = client.chat.completions.last_kwargs["messages"][1]["content"]
    for category in CATEGORIES:
        assert category in client.chat.completions.last_kwargs["messages"][0]["content"]
    assert "a" in user_msg
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_scripts && python3 -m pytest test_category_classifier.py -q`
Expected: FAIL / ERROR，`ModuleNotFoundError: No module named 'category_classifier'`。

- [ ] **Step 3: 实现分类器**

```python
"""七分类分类器：用 DeepSeek 给内容打上唯一分类。

独立模块，不依赖 web_content_system（那个包顶层会拉起 selenium）。
"""

from __future__ import annotations

import json
import os

CATEGORIES = ["科技动态", "文章", "工具", "资源", "图片", "文摘", "言论"]
DEFAULT_CATEGORY = "文章"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = (
    "你是内容分类器。把每个条目归入且仅归入以下七类之一："
    + "、".join(CATEGORIES)
    + '。只输出 JSON 数组，元素为 {"index": 输入序号, "category": 分类}，'
    "不要输出任何其他文字。"
)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


def make_client():
    """返回 OpenAI 兼容客户端；缺少 key 或 SDK 时返回 None。"""
    _load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )


def build_messages(items):
    lines = []
    for index, item in enumerate(items):
        lines.append(
            f"{index}. 标题：{item.get('title', '')}\n"
            f"摘要：{str(item.get('summary', ''))[:200]}"
        )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(lines)},
    ]


def classify_batch(items, client=None, model=DEFAULT_MODEL):
    """把一批条目分类；返回与输入等长的列表，无法判断的位置为 None。"""
    result = [None] * len(items)
    if not items:
        return result
    client = client or make_client()
    if client is None:
        return result
    try:
        response = client.chat.completions.create(
            model=model,
            messages=build_messages(items),
            temperature=0,
            max_tokens=512,
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        payload = json.loads(raw)
        for entry in payload:
            index = entry.get("index")
            category = entry.get("category")
            if (
                isinstance(index, int)
                and 0 <= index < len(items)
                and category in CATEGORIES
            ):
                result[index] = category
    except Exception:
        return [None] * len(items)
    return result


def classify_one(title, summary="", client=None, model=DEFAULT_MODEL):
    """单条分类；失败返回 None（调用方决定兜底）。"""
    items = [{"title": title, "summary": summary}]
    return classify_batch(items, client=client, model=model)[0]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_scripts && python3 -m pytest test_category_classifier.py -q`
Expected: `6 passed`。

- [ ] **Step 5: 提交**

```bash
git add python_scripts/category_classifier.py python_scripts/test_category_classifier.py
git commit -m "feat(data): add seven-category classifier module"
```

---

## Task 3: 人工修正 CLI

**Files:**
- Create: `python_scripts/set_category.py`
- Test: `python_scripts/test_set_category.py`

- [ ] **Step 1: 写失败测试**

```python
# python_scripts/test_set_category.py
import sqlite3

import pytest

from set_category import update_category


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE content_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, created_time TEXT, summary TEXT,
            original_url TEXT, tags TEXT, uid TEXT,
            content TEXT, category TEXT, category_source TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO content_summary (title, original_url, category, category_source) "
        "VALUES ('t1', 'https://e.com/1', NULL, NULL)"
    )
    conn.execute(
        "INSERT INTO content_summary (title, original_url, category, category_source) "
        "VALUES ('t2', 'https://e.com/2', '文章', 'legacy-default')"
    )
    conn.commit()
    return conn


def test_update_by_url_sets_manual():
    conn = make_db()
    row_id = update_category(conn, "工具", url="https://e.com/1")
    assert row_id == 1
    assert conn.execute(
        "SELECT category, category_source FROM content_summary WHERE id=1"
    ).fetchone() == ("工具", "manual")


def test_update_by_id():
    conn = make_db()
    update_category(conn, "言论", row_id=2)
    assert conn.execute(
        "SELECT category, category_source FROM content_summary WHERE id=2"
    ).fetchone() == ("言论", "manual")


def test_rejects_invalid_category():
    conn = make_db()
    with pytest.raises(ValueError):
        update_category(conn, "随笔", row_id=1)


def test_missing_row_raises():
    conn = make_db()
    with pytest.raises(LookupError):
        update_category(conn, "工具", url="https://e.com/nope")


def test_ambiguous_url_raises():
    conn = make_db()
    conn.execute(
        "INSERT INTO content_summary (title, original_url) VALUES ('dup', 'https://e.com/1')"
    )
    conn.commit()
    with pytest.raises(LookupError):
        update_category(conn, "工具", url="https://e.com/1")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_scripts && python3 -m pytest test_set_category.py -q`
Expected: ERROR，`No module named 'set_category'`。

- [ ] **Step 3: 实现 CLI**

```python
#!/usr/bin/env python3
"""人工修正单条内容的七分类。"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from category_classifier import CATEGORIES

DB_PATH = Path(__file__).resolve().parent / "web_content.db"


def update_category(conn, category, *, url=None, row_id=None):
    if category not in CATEGORIES:
        raise ValueError(f"非法分类: {category}，可选：{'、'.join(CATEGORIES)}")
    if row_id is not None:
        rows = list(conn.execute("SELECT id FROM content_summary WHERE id=?", (row_id,)))
    else:
        rows = list(
            conn.execute(
                "SELECT id FROM content_summary WHERE original_url=?", (url,)
            )
        )
    if not rows:
        raise LookupError(f"找不到对应行（url={url} id={row_id}）")
    if len(rows) > 1:
        ids = [row[0] for row in rows]
        raise LookupError(f"匹配到 {len(ids)} 行: {ids}，请用 --id 指定")
    target = rows[0][0]
    conn.execute(
        "UPDATE content_summary SET category=?, category_source='manual' WHERE id=?",
        (category, target),
    )
    conn.commit()
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="人工修正一条内容的分类")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="按 original_url 定位")
    group.add_argument("--id", type=int, help="按 id 定位")
    parser.add_argument("category", help="七类之一")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        row_id = update_category(
            conn, args.category, url=args.url, row_id=args.id
        )
    except (ValueError, LookupError) as exc:
        print(f"❌ {exc}")
        return 1
    finally:
        conn.close()
    print(f"✅ id={row_id} → {args.category} (source=manual)")
    print("   记得运行: npm run gen:static-js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_scripts && python3 -m pytest test_set_category.py -q`
Expected: `5 passed`。

- [ ] **Step 5: 提交**

```bash
git add python_scripts/set_category.py python_scripts/test_set_category.py
git commit -m "feat(data): add manual category override CLI"
```

---

## Task 4: 迁移脚本

**Files:**
- Create: `python_scripts/migrate_category.py`
- Create: `python_scripts/test_migrate_category.py`
- Modify: `.gitignore`（新增备份目录）

- [ ] **Step 1: 先把备份目录加进 .gitignore**

在 `.gitignore` 的 “Database files” 段之前追加：

```gitignore
# One-off migration backups and reports (local only)
python_scripts/backups/
```

- [ ] **Step 2: 写失败测试**

```python
# python_scripts/test_migrate_category.py
import json
import sqlite3

from migrate_category import run_migration

SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT, tags TEXT, uid TEXT, content TEXT
);
CREATE UNIQUE INDEX idx_uid ON content_summary (uid);
"""


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid) "
        "VALUES ('旧文', '2026-07-30 20:14:39', '摘要', 'https://e.com/legacy', 'AI', NULL)"
    )
    conn.execute(
        "INSERT INTO content_summary (title, created_time, summary, original_url, tags, uid) "
        "VALUES ('新文', '2026-08-28 13:22:58', '摘要', 'https://e.com/new', 'AI', 'x')"
    )
    conn.commit()
    conn.close()


def write_site_js(path):
    items = [
        {   # 命中 DB 的旧文
            "id": 1, "title": "旧文", "created_time": "2026-07-30 20:14:39",
            "summary": "摘要", "original_url": "https://e.com/legacy",
            "tags": "AI", "category": "工具",
        },
        {   # 只在站点里的手工内容
            "id": 172, "title": "手工", "created_time": None,
            "summary": "摘要", "original_url": "https://e.com/manual",
            "tags": "观点", "category": "言论",
        },
    ]
    path.write_text("export default " + json.dumps(items) + ";", encoding="utf-8")


def test_migration_adds_columns_and_rows(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)

    report = run_migration(db, site, skip_llm=True)
    conn = sqlite3.connect(db)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    assert {"category", "category_source"} <= columns
    assert conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0] == 3
    legacy = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/legacy'"
    ).fetchone()
    assert legacy == ("工具", "legacy-default")
    manual = conn.execute(
        "SELECT category, category_source, created_time FROM content_summary "
        "WHERE original_url='https://e.com/manual'"
    ).fetchone()
    assert manual == ("言论", "manual", "2026-08-28 13:29:02")
    assert report["inserted_manual"] == 1
    assert report["updated_from_site"] == 1
    assert report["uid_backfilled"] == 1
    assert report["category_coverage"] == 2  # skip_llm 时“新文”仍为空
    assert report["total_rows"] == 3
    conn.close()


def test_migration_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    write_site_js(site)

    first = run_migration(db, site, skip_llm=True)
    second = run_migration(db, site, skip_llm=True)
    assert first["inserted_manual"] == 1
    assert second["inserted_manual"] == 0
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0] == 3
    conn.close()


def test_migration_dedupes_duplicate_url_by_title(tmp_path):
    db = tmp_path / "test.db"
    site = tmp_path / "static-data.js"
    make_db(db)
    items = [
        {
            "title": "同一期 A", "created_time": None, "summary": "s",
            "original_url": "https://e.com/issue", "tags": "t", "category": "文章",
        },
        {
            "title": "同一期 B", "created_time": None, "summary": "s",
            "original_url": "https://e.com/issue", "tags": "t", "category": "言论",
        },
    ]
    site.write_text("export default " + json.dumps(items) + ";", encoding="utf-8")

    report = run_migration(db, site, skip_llm=True)
    assert report["inserted_manual"] == 2
    conn = sqlite3.connect(db)
    uids = [row[0] for row in conn.execute(
        "SELECT uid FROM content_summary WHERE original_url='https://e.com/issue' ORDER BY id"
    )]
    assert len(uids) == 2 and len(set(uids)) == 2
    conn.close()
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd python_scripts && python3 -m pytest test_migrate_category.py -q`
Expected: ERROR，`No module named 'migrate_category'`。

- [ ] **Step 4: 实现迁移脚本**

```python
#!/usr/bin/env python3
"""一次性迁移：加 category 列、补 uid、导入手工内容、回填分类。

默认先备份、再在事务里执行；--dry-run 在临时副本上执行，不改真实 DB。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from category_classifier import CATEGORIES, DEFAULT_CATEGORY, classify_batch

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "web_content.db"
SITE_JS = BASE.parent / "src/assets/static-data.js"
BACKUP_DIR = BASE / "backups"
IMPORT_TIME = "2026-08-28 13:29:02"
BATCH_SIZE = 10


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_site_items(path: Path):
    raw = path.read_text(encoding="utf-8")
    body = re.sub(r"^export default\s*", "", raw.strip()).rstrip(";")
    return json.loads(body)


def ensure_columns(conn) -> list:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(content_summary)")}
    added = []
    if "category" not in columns:
        conn.execute("ALTER TABLE content_summary ADD COLUMN category TEXT")
        added.append("category")
    if "category_source" not in columns:
        conn.execute(
            "ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default'"
        )
        added.append("category_source")
    return added


def backfill_uid(conn) -> int:
    rows = list(
        conn.execute(
            "SELECT id, original_url, title, created_time FROM content_summary "
            "WHERE uid IS NULL OR uid = ''"
        )
    )
    for row_id, url, title, created_time in rows:
        key = url or f"{title}|{created_time}"
        conn.execute("UPDATE content_summary SET uid=? WHERE id=?", (md5(key), row_id))
    return len(rows)


def apply_site_categories(conn, site_items) -> int:
    mapping = {}
    for item in site_items:
        url = item.get("original_url") or ""
        if url and item.get("category") in CATEGORIES:
            mapping.setdefault(url, item)
    updated = 0
    rows = list(conn.execute("SELECT id, original_url FROM content_summary"))
    for row_id, url in rows:
        item = mapping.get(url or "")
        if not item:
            continue
        source = "manual" if item.get("created_time") is None else "legacy-default"
        cur = conn.execute(
            "UPDATE content_summary SET category=?, category_source=? "
            "WHERE id=? AND (category IS NULL OR category='')",
            (item["category"], source, row_id),
        )
        updated += cur.rowcount
    return updated


def insert_manual_items(conn, site_items) -> int:
    existing_urls = {row[0] for row in conn.execute("SELECT original_url FROM content_summary")}
    existing_uids = {row[0] for row in conn.execute("SELECT uid FROM content_summary")}
    inserted = 0
    for item in site_items:
        if item.get("created_time"):  # 旧文（含已从 DB 删除的幽灵行）不补录
            continue
        url = item.get("original_url") or ""
        if not url or url in existing_urls:
            continue
        title = item.get("title") or ""
        uid = md5(url)
        if uid in existing_uids:
            uid = md5(f"{url}|{title}")
        if uid in existing_uids:
            continue
        conn.execute(
            "INSERT INTO content_summary "
            "(title, created_time, summary, original_url, tags, uid, content, category, category_source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                IMPORT_TIME,
                item.get("summary"),
                url,
                item.get("tags"),
                uid,
                None,
                item.get("category") if item.get("category") in CATEGORIES else DEFAULT_CATEGORY,
                "manual",
            ),
        )
        existing_urls.add(url)
        existing_uids.add(uid)
        inserted += 1
    return inserted


def classify_missing(conn, client=None, batch_size: int = BATCH_SIZE):
    rows = list(
        conn.execute(
            "SELECT id, title, summary FROM content_summary "
            "WHERE category IS NULL OR category='' ORDER BY id"
        )
    )
    classified = failed = 0
    for start in range(0, len(rows), batch_size):
        chunk = rows[start : start + batch_size]
        items = [{"title": row[1], "summary": row[2] or ""} for row in chunk]
        categories = classify_batch(items, client=client)
        for (row_id, _, _), category in zip(chunk, categories):
            if category:
                conn.execute(
                    "UPDATE content_summary SET category=?, category_source='llm' WHERE id=?",
                    (category, row_id),
                )
                classified += 1
            else:
                conn.execute(
                    "UPDATE content_summary SET category=?, category_source='default' WHERE id=?",
                    (DEFAULT_CATEGORY, row_id),
                )
                failed += 1
    return classified, failed


def run_migration(db_path, site_js_path, *, skip_llm=False, client=None) -> dict:
    site_items = load_site_items(Path(site_js_path))
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        added = ensure_columns(conn)
        uid_backfilled = backfill_uid(conn)
        updated = apply_site_categories(conn, site_items)
        inserted = insert_manual_items(conn, site_items)
        classified = failed = 0
        if not skip_llm:
            classified, failed = classify_missing(conn, client=client)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    total = conn.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0]
    coverage = conn.execute(
        "SELECT COUNT(*) FROM content_summary WHERE category IS NOT NULL AND category != ''"
    ).fetchone()[0]
    distribution = dict(
        conn.execute(
            "SELECT COALESCE(category, '(空)'), COUNT(*) FROM content_summary GROUP BY category"
        )
    )
    sources = dict(
        conn.execute(
            "SELECT COALESCE(category_source, '(空)'), COUNT(*) FROM content_summary GROUP BY category_source"
        )
    )
    conn.close()
    return {
        "added_columns": added,
        "uid_backfilled": uid_backfilled,
        "updated_from_site": updated,
        "inserted_manual": inserted,
        "classified": classified,
        "classify_failed": failed,
        "total_rows": total,
        "category_coverage": coverage,
        "distribution": distribution,
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="迁移 DB 到 category 真源模型")
    parser.add_argument("--dry-run", action="store_true", help="在临时副本上执行，不改真实 DB")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM 分类")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--site-js", default=str(SITE_JS))
    args = parser.parse_args()

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.dry_run:
        tmp_dir = Path(tempfile.mkdtemp(prefix="deepthink-migrate-"))
        target = tmp_dir / "dryrun.db"
        shutil.copy2(args.db, target)
    else:
        backup = BACKUP_DIR / f"web_content-{stamp}.db"
        shutil.copy2(args.db, backup)
        target = Path(args.db)
        print(f"🗄  备份: {backup}")

    report = run_migration(
        target, Path(args.site_js), skip_llm=args.skip_llm
    )
    report["mode"] = "dry-run" if args.dry_run else "apply"
    report_path = BACKUP_DIR / f"migration-report-{stamp}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"📄 报告: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd python_scripts && python3 -m pytest test_migrate_category.py -q`
Expected: `3 passed`。

- [ ] **Step 6: 提交**

```bash
git add .gitignore python_scripts/migrate_category.py python_scripts/test_migrate_category.py
git commit -m "feat(data): add one-off category migration script"
```

---

## Task 5: 执行迁移（dry-run → 正式）

**Files:**
- Modify: `python_scripts/web_content.db`（数据变更）
- Output: `python_scripts/backups/migration-report-*.json`（不提交）

- [ ] **Step 1: 确认前置依赖**

Run: `python3 -c "import openai, dotenv; print('ok')"`
Expected: `ok`。若失败：Run: `pip3 install "openai>=1.3.0" "python-dotenv>=1.0.0"`，然后重跑确认。

- [ ] **Step 2: dry-run（跳过 LLM，先看结构）**

Run: `cd python_scripts && python3 migrate_category.py --dry-run --skip-llm`
Expected（关键字段）：
- `"inserted_manual": 32`
- `"total_rows": 224`
- `"uid_backfilled": 2`
- `"updated_from_site": 103`
- `"category_coverage": 135`（103 条旧文 + 32 条手工内容已分类；89 条 8 月内容仍是 `(空)`，因为跳过了 LLM）
- 真实 DB 未被修改：`git status --short python_scripts/web_content.db` 无输出。

- [ ] **Step 3: 正式执行（含 LLM 分类）**

Run: `cd python_scripts && python3 migrate_category.py`
Expected：
- `"mode": "apply"`，`"inserted_manual": 32`，`"total_rows": 224`
- `"classified"` + `"classify_failed"` = 89
- `"category_coverage": 224`
- `distribution` 中七类之和 = 224
- 备份与报告路径打印出来

- [ ] **Step 4: 核对数据**

Run:

```bash
python3 - <<'PY'
import sqlite3
con = sqlite3.connect("file:python_scripts/web_content.db?mode=ro", uri=True)
print("rows:", con.execute("SELECT COUNT(*) FROM content_summary").fetchone()[0])
print("category null:", con.execute("SELECT COUNT(*) FROM content_summary WHERE category IS NULL OR category=''").fetchone()[0])
print("dup ids:", con.execute("SELECT COUNT(*) FROM (SELECT id FROM content_summary GROUP BY id HAVING COUNT(*)>1)").fetchone()[0])
print("sources:", list(con.execute("SELECT category_source, COUNT(*) FROM content_summary GROUP BY category_source")))
PY
```

Expected：`rows: 224`、`category null: 0`、`dup ids: 0`，sources 包含 `manual`/`legacy-default`/`llm`（或 `default`）。

- [ ] **Step 5: 提交 DB 变更**

```bash
git add python_scripts/web_content.db
git commit -m "chore(data): migrate database to category source-of-truth schema"
```

---

## Task 6: 入库路径写入分类

**Files:**
- Modify: `python_scripts/fetch_from_params.py:206-233`（`save_to_db`）
- Modify: `python_scripts/fetch_from_params.py` 建表处（文件内 `CREATE TABLE IF NOT EXISTS content_summary`）
- Modify: `python_scripts/crawler_subpages.py:257-306`（`insert_row`）与建表/补列处
- Test: `python_scripts/test_ingestion_category.py`

- [ ] **Step 1: 写失败测试**

```python
# python_scripts/test_ingestion_category.py
import sqlite3
from unittest.mock import patch

import fetch_from_params
import crawler_subpages

SCHEMA = """
CREATE TABLE content_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, created_time TEXT, summary TEXT,
    original_url TEXT UNIQUE, tags TEXT, uid TEXT UNIQUE, content TEXT,
    category TEXT, category_source TEXT
);
"""


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    return conn


def test_save_to_db_writes_llm_category():
    conn = make_db()
    with patch.object(fetch_from_params, "classify_one", return_value="工具"):
        inserted = fetch_from_params.save_to_db(
            conn, "https://e.com/1", "标题", "摘要", "AI", "正文"
        )
    assert inserted is True
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/1'"
    ).fetchone()
    assert row == ("工具", "llm")


def test_save_to_db_falls_back_to_default():
    conn = make_db()
    with patch.object(fetch_from_params, "classify_one", return_value=None):
        fetch_from_params.save_to_db(
            conn, "https://e.com/2", "标题", "摘要", "AI", "正文"
        )
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/2'"
    ).fetchone()
    assert row == ("文章", "default")


def test_crawler_insert_row_writes_llm_category():
    conn = make_db()
    with patch.object(crawler_subpages, "classify_one", return_value="言论"):
        crawler_subpages.insert_row(
            conn, "https://e.com/3", "标题", "摘要", "AI", "正文"
        )
    row = conn.execute(
        "SELECT category, category_source FROM content_summary WHERE original_url='https://e.com/3'"
    ).fetchone()
    assert row == ("言论", "llm")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_scripts && python3 -m pytest test_ingestion_category.py -q`
Expected: FAIL，`AttributeError: module 'fetch_from_params' has no attribute 'classify_one'` 或 INSERT 列数不匹配。

- [ ] **Step 3: 修改 `fetch_from_params.py`**

文件顶部 import 区加入：

```python
from category_classifier import DEFAULT_CATEGORY, classify_one
```

`ensure_schema()`（`python_scripts/fetch_from_params.py:56`）中：

1. `CREATE TABLE IF NOT EXISTS content_summary (...)` 的 `content TEXT` 之后追加两行：

```sql
            category TEXT,
            category_source TEXT DEFAULT 'default'
```

2. 在 `if "content" not in cols:` 的 ALTER 之后追加：

```python
    if "category" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN category TEXT")
    if "category_source" not in cols:
        cur.execute(
            "ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default'"
        )
```

替换 `save_to_db` 的 INSERT 段：

```python
    created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    category = classify_one(title, summary)
    category_source = "llm" if category else "default"
    cur.execute(
        """
        INSERT INTO content_summary
        (title, created_time, summary, original_url, tags, uid, content, category, category_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            created_time,
            summary,
            url,
            tags,
            uid,
            body,
            category or DEFAULT_CATEGORY,
            category_source,
        ),
    )
```

- [ ] **Step 4: 修改 `crawler_subpages.py`**

顶部 import 区加入：

```python
from category_classifier import DEFAULT_CATEGORY, classify_one
```

建表/补列处（`get_conn()`，`python_scripts/crawler_subpages.py:238` 附近，已有 `content` 补列逻辑）追加：

```python
    cur.execute("PRAGMA table_info(content_summary)")
    cols = [row[1] for row in cur.fetchall()]
    if "category" not in cols:
        cur.execute("ALTER TABLE content_summary ADD COLUMN category TEXT")
    if "category_source" not in cols:
        cur.execute(
            "ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default'"
        )
    conn.commit()
```

`insert_row` 的 INSERT 段替换为：

```python
    category = classify_one(title, summary)
    cur.execute(
        "INSERT OR IGNORE INTO content_summary "
        "(title, created_time, summary, original_url, tags, uid, content, category, category_source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            title,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary,
            url,
            tags,
            uid,
            body,
            category or DEFAULT_CATEGORY,
            "llm" if category else "default",
        ),
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd python_scripts && python3 -m pytest test_ingestion_category.py -q`
Expected: `3 passed`。

- [ ] **Step 6: 提交**

```bash
git add python_scripts/fetch_from_params.py python_scripts/crawler_subpages.py python_scripts/test_ingestion_category.py
git commit -m "feat(data): classify new content on ingestion"
```

---

## Task 7: 生成器重写为 DB 单向管线

**Files:**
- Create: `scripts/lib/db.mjs`
- Modify: `scripts/generate-data.js`（整体替换）
- Delete: `src/assets/static-data-20260730-*.json`（7 个快照）
- Modify: `.gitignore`（快照规则）
- Modify: `package.json`（移除 `gen:static-js:from-json`）

- [ ] **Step 1: 实现 DB 读取模块**

```js
// scripts/lib/db.mjs
import fs from 'fs';
import initSqlJs from 'sql.js';

export const DB_COLUMNS = [
  'id', 'title', 'created_time', 'summary', 'original_url', 'tags', 'category',
];

export async function readDatabaseRows(dbPath) {
  if (!fs.existsSync(dbPath)) {
    throw new Error(`数据库不存在: ${dbPath}`);
  }
  const SQL = await initSqlJs();
  const db = new SQL.Database(fs.readFileSync(dbPath));
  try {
    const result = db.exec(
      'SELECT id, title, created_time, summary, original_url, tags, category ' +
      'FROM content_summary ORDER BY created_time DESC, id DESC',
    );
    if (!result.length) return [];
    const { columns, values } = result[0];
    return values.map((row) =>
      Object.fromEntries(columns.map((column, index) => [column, row[index]])),
    );
  } finally {
    db.close();
  }
}
```

- [ ] **Step 2: 重写生成器**

```js
// scripts/generate-data.js
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { readDatabaseRows } from './lib/db.mjs';
import { validateRows } from './lib/data-rules.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const JSON_PATH = path.resolve(__dirname, '../src/assets/static-data.json');
const JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const allowShrink = process.argv.includes('--allow-shrink');

function readPreviousCount() {
  if (!fs.existsSync(JS_PATH)) return null;
  try {
    const raw = fs.readFileSync(JS_PATH, 'utf-8').trim();
    const body = raw.replace(/^export default\s*/, '').replace(/;\s*$/, '');
    const data = JSON.parse(body);
    return Array.isArray(data) ? data.length : null;
  } catch {
    return null;
  }
}

function writeAtomic(filePath, content) {
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, content, 'utf-8');
  fs.renameSync(tempPath, filePath);
}

async function main() {
  const rows = await readDatabaseRows(DB_PATH);
  const previousCount = readPreviousCount();
  const { ok, errors, warnings } = validateRows(rows, { previousCount, allowShrink });

  for (const warning of warnings) console.warn(`⚠️  ${warning}`);
  if (!ok) {
    for (const error of errors) console.error(`❌ ${error}`);
    console.error('❌ 校验失败，未写入任何文件。');
    process.exit(1);
  }

  writeAtomic(JSON_PATH, `${JSON.stringify(rows, null, 2)}\n`);
  writeAtomic(JS_PATH, `export default ${JSON.stringify(rows)};\n`);

  console.log(`✅ 生成 ${rows.length} 条（上一版 ${previousCount ?? '无'} 条）`);
  console.log(`   ${JSON_PATH}`);
  console.log(`   ${JS_PATH}`);
}

main().catch((error) => {
  console.error(`❌ 生成失败: ${error.message}`);
  process.exit(1);
});
```

- [ ] **Step 3: 清理快照与旧脚本入口**

```bash
rm -f src/assets/static-data-20260730-*.json
```

> 这些快照是 gitignored、未被跟踪的本地文件，不需要 `git rm`。

在 `package.json` 中删除这一行：

```json
    "gen:static-js:from-json": "node scripts/generate-data.js --from-json"
```

并把 `.gitignore` 中：

```gitignore
src/assets/static-data*.json
```

改为：

```gitignore
src/assets/static-data-*.json
```

- [ ] **Step 4: 运行生成器并核对**

Run: `npm run gen:static-js`
Expected：
- `✅ 生成 224 条（上一版 143 条）`
- `git diff --stat src/assets/static-data.json src/assets/static-data.js` 显示两个文件更新
- `git status --short` 中不再出现新的 `static-data-*.json`

- [ ] **Step 5: 构建与 lint**

Run: `npm run build && npm run lint`
Expected: build 成功；lint 仍可能有之前就存在的 3 个 error（`Last30daysPage.jsx:7`、`PhilosophySection.jsx:59` 两处），它们属于 S2，本任务不修；不得新增其他错误。

- [ ] **Step 6: 提交**

```bash
git add scripts/lib/db.mjs scripts/generate-data.js package.json .gitignore \
  src/assets/static-data.json src/assets/static-data.js
git commit -m "refactor(data): generate static data solely from database"
```

---

## Task 8: `check:data` 与 npm 脚本

**Files:**
- Create: `scripts/check-data.mjs`
- Modify: `package.json`

- [ ] **Step 1: 实现检查脚本**

```js
// scripts/check-data.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { readDatabaseRows } from './lib/db.mjs';
import { compareDatasets, validateRows } from './lib/data-rules.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const JSON_PATH = path.resolve(__dirname, '../src/assets/static-data.json');

function readPublished(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8').trim();
  const body = raw.replace(/^export default\s*/, '').replace(/;\s*$/, '');
  return JSON.parse(body);
}

async function main() {
  const dbRows = await readDatabaseRows(DB_PATH);
  const published = readPublished(JS_PATH);
  const publishedJson = JSON.parse(fs.readFileSync(JSON_PATH, 'utf-8'));

  const errors = [];
  const rowCheck = validateRows(dbRows);
  errors.push(...rowCheck.errors);
  errors.push(...compareDatasets(dbRows, published).errors);

  const jsonVsJs = JSON.stringify(publishedJson) === JSON.stringify(published);
  if (!jsonVsJs) errors.push('static-data.json 与 static-data.js 内容不一致');

  if (errors.length > 0) {
    for (const error of errors) console.error(`❌ ${error}`);
    console.error(`❌ check:data 失败（${errors.length} 项）`);
    process.exit(1);
  }
  console.log(`✅ check:data 通过：DB 与生成物一致，共 ${dbRows.length} 条`);
}

main().catch((error) => {
  console.error(`❌ check:data 异常: ${error.message}`);
  process.exit(1);
});
```

- [ ] **Step 2: 加 npm 脚本**

`package.json` 的 `scripts` 中加入：

```json
    "check:data": "node scripts/check-data.mjs",
    "test:data": "node --test scripts/lib/*.test.mjs"
```

- [ ] **Step 3: 验证通过**

Run: `npm run check:data && npm run test:data`
Expected：`✅ check:data 通过：DB 与生成物一致，共 224 条`；测试 `# fail 0`。

- [ ] **Step 4: 验证能拦住漂移**

Run:

```bash
cp src/assets/static-data.js /tmp/static-data.js.bak
node -e "const fs=require('fs');const p='src/assets/static-data.js';const d=JSON.parse(fs.readFileSync(p,'utf8').replace(/^export default /,'').replace(/;\\s*$/,''));d.pop();fs.writeFileSync(p,'export default '+JSON.stringify(d)+';')"
npm run check:data; echo "exit=$?"
cp /tmp/static-data.js.bak src/assets/static-data.js
```

Expected：中间输出 `❌` 且 `exit=1`，最后恢复原文件（`git diff --stat` 无变化）。

- [ ] **Step 5: 提交**

```bash
git add scripts/check-data.mjs package.json
git commit -m "feat(data): add CI data consistency check"
```

---

## Task 9: CI 加校验

**Files:**
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: 在 Install 之后、Build 之前插入两步**

```yaml
    - name: Run data rule tests
      run: npm run test:data

    - name: Check data consistency
      run: npm run check:data
```

> 本任务**不加 lint 门禁**：线上代码当前有 3 个已存在的 lint error（`Last30daysPage.jsx` 未使用 `setQuery`、`PhilosophySection.jsx` 两处未转义引号），加门禁会直接让部署变红；它们属于 S2，修完后在 S4 再把 lint 接进 CI。

- [ ] **Step 2: 验证 YAML 结构**

Run: `sed -n '1,60p' .github/workflows/deploy.yml`
Expected：`Install dependencies` 之后依次是 Run data rule tests / Check data consistency / Build project / Deploy。

> 注意：本任务不改 PR 触发条件、权限、并发与部署冒烟，这些属于 S4。

- [ ] **Step 3: 提交**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: validate data before building and deploying"
```

---

## Task 10: 文档更新

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `dev.md`
- Modify: `README.md`

- [ ] **Step 1: `CLAUDE.md` 数据管线段替换**

把 “Data pipeline” 代码块与说明替换为：

```markdown
### 数据管线（唯一真源）

```
python_scripts/web_content.db ──scripts/generate-data.js──▶ src/assets/static-data.json
   (SQLite, 唯一真源)                     │                 src/assets/static-data.js
                                          │
                                          ▼
                                  src/App.jsx imports static-data.js
```

- DB 是唯一真源；两个数据文件都是生成物，**禁止手工编辑**。
- `category` 是 DB 的列（七类之一），抓取入库时由 `category_classifier.py` 自动分类，可用 `set_category.py` 人工修正。
- 更新内容：改 DB → `npm run gen:static-js` → 提交 → 推送自动部署。
- `npm run check:data` 校验 DB 与生成物一致，CI 在 build 前执行。
```

同时删除 “`category` is not in the original DB schema” 那条 Gotcha。

- [ ] **Step 2: `AGENTS.md` 目录与命令补充**

在 Project Structure 的 `python_scripts/` 段补：

```text
│   ├── migrate_category.py     # 一次性分类迁移（已完成）
│   ├── set_category.py         # 人工修正单条分类
│   ├── category_classifier.py  # LLM 七分类
```

在 Build Commands 的 Frontend 表补一行：

| `npm run check:data` | 校验 DB 与生成物一致（CI 使用） |

- [ ] **Step 3: `dev.md` 更正加密说明**

把 “Database Content Security” 段开头改成：

```markdown
> ⚠️ 现状说明（2026-10-18）：`python_scripts/web_content.db` 目前是**明文且被 git 跟踪**的，`dev.md` 旧版声称的“明文被忽略、CI 解密数据库”与事实不符。仓库为 public，明文 DB 的全部内容已随历史公开；加密策略的调整见后续 S3。
```

- [ ] **Step 4: `README.md` 重写数据与构建段**

把 “安装和运行” 之后的内容替换为：

```markdown
## 数据从哪来

- 真源：`python_scripts/web_content.db`（SQLite）
- 生成：`npm run gen:static-js` 把 DB 导出为 `src/assets/static-data.json` 与 `static-data.js`
- 校验：`npm run check:data` 确认生成物与 DB 一致
- 两个数据文件都是生成物，不要手工编辑；改内容请改 DB 或用 `python_scripts/set_category.py` 修正分类

## 每周更新内容

1. 抓取：`cd python_scripts && python3 fetch_from_params.py` 或 `python3 crawler_subpages.py`
2. 生成：`npm run gen:static-js`
3. 本地预览：`npm run dev`
4. 提交并推送：`git add -A && git commit -m "chore(content): ..." && git push`
5. 推送后 GitHub Actions 自动部署到 GitHub Pages（生产域名另行说明）
```

- [ ] **Step 5: 检查没有残留错误表述**

Run: `grep -rn "sqliteReader\|不要跑.*gen:static-js\|浏览器.*sql.js" README.md AGENTS.md CLAUDE.md dev.md`
Expected：无输出（或仅剩 S3 相关的已知说明）。

- [ ] **Step 6: 提交**

```bash
git add README.md AGENTS.md CLAUDE.md dev.md
git commit -m "docs: align data pipeline docs with single-source-of-truth model"
```

---

## Task 11: 全量验收与部署

**Files:** 无新增

- [ ] **Step 1: 跑全部检查**

Run:

```bash
npm run test:data
npm run check:data
npm run lint
npm run build
cd python_scripts && python3 -m pytest test_category_classifier.py test_set_category.py test_migrate_category.py test_ingestion_category.py -q
```

Expected：
- `test:data` 0 fail
- `check:data` 通过，224 条
- `lint` 预期仍失败，且错误数仍为 3（S2 之前不修，不得新增）
- `build` 成功
- pytest 全部通过

- [ ] **Step 2: 核对站点数据**

Run:

```bash
node -e "const fs=require('fs');const d=JSON.parse(fs.readFileSync('src/assets/static-data.json','utf8'));console.log(d.length, new Set(d.map(x=>x.category)).size, new Set(d.map(x=>x.id)).size)"
```

Expected：`224 7 224`。

- [ ] **Step 3: 推送前向用户确认**

> 这一步会触发生产部署。运行前必须得到用户明确同意。

- [ ] **Step 4: 推送并观察 CI**

```bash
git push origin main
```

用 GitHub Actions 页面或 `gh run watch` 确认 workflow 成功。

- [ ] **Step 5: 部署后冒烟**

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://deepthink.global/
curl -s https://deepthink.global/ | grep -o 'assets/index-[^"]*\.js'
```

Expected：首页 200；拿到 js 路径后再请求一次，确认 200 与 `content-type: text/javascript`；线上 bundle 内条目数应为 224（可通过 grep 统计 `"category"` 出现次数近似验证）。

---

## Self-Review

- **Spec 覆盖**：§4.1 列/uid → Task 4；§4.2 回填与入库分类 → Task 4/5/6；§4.3 手工内容 → Task 4/5；§4.4 幽灵行 → Task 5（不补录）；§4.5 行数 → Task 5/11；§5 迁移脚本 → Task 4；§6 生成器 → Task 7；§7 check/CI → Task 8/9；§8 人工修正 → Task 3；§9 文档 → Task 10；§10 验收 → Task 11。
- **占位符扫描**：无 TBD/TODO；每个代码步骤都有完整代码。
- **类型/命名一致性**：`validateRows`、`compareDatasets`、`readDatabaseRows`、`classify_batch`、`classify_one`、`update_category`、`run_migration` 在各任务中签名一致；`category_source` 取值 `manual`/`llm`/`legacy-default`/`default` 全文一致。
