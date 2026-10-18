# 数据链路审计：DB → static-data → 部署的新鲜度与正确性

- 审计日期：2026-10-18（Asia/Shanghai）
- 审计人：Pipeline（Data Engineer）
- 审计模式：**只读**。未执行 `scripts/generate-data.js`（会覆盖 `static-data.*`），未执行任何写库/清理/加密脚本。
- 审计对象：`python_scripts/web_content.db` → `src/assets/static-data.json/.js` → `dist/` → `origin/gh-pages`。
- 结论：**链路是"手动、单向、不可复现"的，且当前处于分裂状态**。生产发布的是 143 条数据（含 40 条幽灵记录（39 个 DB 中已不存在的 URL）、32 条无 `created_time`、1 组重复 URL），而 DB 已有 192 行，最新 2026-08-28 13:22:58；`static-data.json` 停留在 2026-07-30（111 条）；7 类 `category` 只存在于 `static-data.js`，DB 无此列，**任何一次正规重生成都会清空分类**。

---

## 1. TL;DR（给决策者）

| 指标 | 值 | 判定 |
|---|---|---|
| DB `content_summary` 行数 | **192** | 权威源 |
| DB 最新 `created_time` | **2026-08-28 13:22:58** | 已 51 天未更新 |
| DB 最早 `created_time` | 2026-07-30 20:14:39 | — |
| `static-data.json` 条数 | **111** | 落后 DB 89 条 + 含 8 条 DB 已删除，已 80 天未更新 |
| `static-data.js` 条数 | **143**（142 个唯一 URL） | 生产实际使用；落后 DB 89 条，含 39 条幽灵 URL |
| DB 有、`static-data.js` 无 | **89**（2026-08-06 2 条 + 2026-08-28 87 条） | 未发布 |
| `static-data.js` 有、DB 无 | **39 个 URL / 40 条记录** | 幽灵数据，会永久累积 |
| `static-data.js` 无 `created_time` | **32 条**（id 172–203） | 卡片日期空白 |
| `category` 覆盖 | js 143/143，DB 0/192，json 0/111 | **不可复现** |
| 生产包（gh-pages）条数 | 143（bundle 中 `original_url` 出现 144 次 = 143 条 + 1 处代码） | 与 js 一致 |
| 最近一次部署 | 2026-09-03 11:56 (+08) | 45 天前 |
| 加密副本 `.enc` | 2026-07-31，1.42 MB | 落后当前明文 DB（2.68 MB） |

---

## 2. 审计范围与方法

只读操作清单（可复现）：

```bash
# 1) 表结构 / 计数 / 时间范围（sqlite3 -readonly）
sqlite3 -readonly python_scripts/web_content.db ".schema"
sqlite3 -readonly python_scripts/web_content.db "SELECT COUNT(*) FROM content_summary;"
# 2) 用 Python 解析 static-data.json 与 static-data.js（export default [...]）做集合差
# 3) 只读 git：git log/show/ls-tree origin/gh-pages，统计部署包内 original_url 数量
# 4) 只读 stat/mtime，不做任何写入
```

明确排除：
- 未运行 `node scripts/generate-data.js` / `npm run gen:static-js` / `--from-json`（会重写 json/js 并生成快照）。
- 未运行 `clean_db.py`、`encrypt-db.sh`、`backfill_content.py`、抓取脚本。
- 未解密 `web_content.db.enc`（不读取密钥）。

限制：本地 `main`(22544ca) 落后 `origin/main`(997cd99) 一个提交，审计基于本地工作区；远端 gh-pages 用本地 remote-ref 只读检查。

---

## 3. Source Tables and Schema Evidence

`python_scripts/web_content.db`：SQLite 3.x，262 页 × 4096B ≈ 2.68 MB 物理大小，`freelist_count=1`，`schema version=4`，`file counter=601`（说明经历过多次删除/重建——与 id 空洞一致）。

```sql
CREATE TABLE content_summary (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    created_time TEXT    NOT NULL,      -- 文本，'YYYY-MM-DD HH:MM:SS'，无时区
    summary      TEXT    NOT NULL,
    original_url TEXT    NOT NULL,
    tags         TEXT,                  -- 逗号分隔字符串，无规范化
    uid          TEXT,                  -- md5(original_url)，UNIQUE INDEX
    content      TEXT                   -- 全文备份，2026-07-31 后新增
);
CREATE UNIQUE INDEX idx_uid  ON content_summary (uid);
CREATE INDEX        idx_tags ON content_summary (tags);

CREATE TABLE manual_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
    content TEXT NOT NULL, created_time TEXT NOT NULL,
    summary TEXT, tags TEXT
);
```

实测：

| 检查 | 结果 |
|---|---|
| `content_summary` 行数 | **192** |
| `manual_content` 行数 | **0**（`generate-data.js` 的 fallback 分支当前不会触发） |
| `MIN/MAX(created_time)` | 2026-07-30 20:14:39 / **2026-08-28 13:22:58** |
| 按日期分布 | 07-30: 103；08-06: 2；08-28: 87 |
| 空值 | title/summary/url/tags 空值 0；`uid` NULL 2；`content` 空 2 |
| URL | 192 条全部非空、全部唯一 |
| `uid` | 190 个不同值（2 NULL），UNIQUE 索引对 NULL 不去重 |
| id 范围 | 1–486，但只有 192 行 → **294 个 id 空洞**（删除/重插入历史） |
| 重复 title | **30 组**（最多 4 条同名，如"笑来搜" id 3/37/38/39） |

`created_time` 语义（证据 `crawler_subpages.py`）：

```python
datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # 无时区、无 UTC 后缀
```

→ **本地时间（假设 Asia/Shanghai）、无 tz 标记**。任何跨时区消费方都会误解。`clean_db.py` 是 **全表 TRUNCATE**，不是去重工具；它解释了 id 空洞与 8 条 json 幽灵的来源。

---

## 4. Data Lineage and Transformation Logic（实际 vs 文档）

文档声明（CLAUDE.md）：

```
web_content.db ──sql.js──▶ scripts/generate-data.js ──▶ static-data.json ──▶ static-data.js ──▶ App.jsx ──▶ build ──▶ gh-pages
```

实测这条链路**在 3 个地方断开**：

1. **增量合并只增不删**（`mergeIncremental`，`scripts/generate-data.js`）：以 `original_url || title-created_time` 为 key，只 `push` 新项，从不删除 → DB 删除的 8 条、39 条 URL 永久留在 js。
2. **`category` 不在 DB，也不在 json**：`content_summary` 无该列，`generate-data.js` 的 `SELECT` 不含该列。js 中 143 条 `category` 来自 2026-08-28 提交 `4da5d06` 的人工/一次性注入（commit message 原文："the 111 existing long-form items default to 文章, and 32 new items imported from issue #410..."）。→ **正规重生成 = 分类全部丢失**（UI 侧无 category 时 fallback 为"文章"，见 `src/utils/categories.js`）。
3. **最后一次 js 生成不是由当前 DB 产生的**：js 143 条中只有 103 条能在 DB 找到，且缺失的 89 条恰好是 DB 的 08-06/08-28 两批；39 条 URL 从未在 DB 出现。`static-data.js` mtime 10:45，DB 写入 13:22（同一天），说明 13:22 的抓取结果**从未进入前端数据**。

实际（反推）链路：

```
[外部抓取 + LLM 摘要] ──▶ web_content.db (192 行, 2026-08-28 13:22)
                              │
                              ├─(未执行)─▶ generate-data.js  ← 若执行：200 条 = json111 ∪ db192，且 category 归零
                              │
src/assets/static-data.json (111 条, 2026-07-30 23:24, 无 category, 已 tracked)
                              │
src/assets/static-data.js   (143 条, 2026-08-28 10:45, 含 category / 含幽灵 / 32 条无日期)
                              │
                       App.jsx（按数组顺序渲染，不排序）──▶ dist/ ──▶ gh-pages (143 条, 2026-09-03)
```

字段级一致性（好消息）：js 与 DB 能对上的 103 条，`title/summary/tags/created_time` **逐字段完全一致**；json 与 js 共享的 111 条也完全一致（差异仅为 js 新增 `category`）。问题集中在**集合完整性**与**不可复现字段**，不在已匹配行的内容质量。

### 4.1 差集明细

**A. DB 有但 `static-data.js`/json 都没有：89 条**

| 批次 | 条数 | tags 分布 |
|---|---|---|
| 2026-08-06 | 2 | `AI` 1、`AI,商业` 1 |
| 2026-08-28 | 87 | `github,ruanyifeng,weekly,subpage` 30；`百科,百传中穿心龙爪手,subpage` 25；`github-issues,...,subpage` 13；`vibecodinghub,...,subpage` 12；`lixiaolai,subpage` 4；其它 3 |

其中 **17 条的 title 已经以另一条 URL 发布在 js 中**（镜像站/重复内容），其余 72 条是真正未发布的新内容。

**B. `static-data.js` 有但 DB 无：40 条记录 / 39 个 URL**

- 8 条来自 `static-data.json`（id 13–17、30–32，2025-12~2026-01 的微信/网页文章），DB 中已被删除（`clean_db` 或手工删除），但 json 和 js 仍保留 → 前端展示已下线内容。
- 32 条为 `4da5d06` 手工导入的 issue #410 条目（id 172–203），**不在 DB、不在 json、无 `created_time`**，仅存在于 js。7 类分布：文章 8、工具 10、言论 5、科技动态 3、资源 3、图片 2、文摘 1。
- 1 组 URL 重复：`https://www.ruanyifeng.com/blog/2026/08/weekly-issue-410.html` 对应 id 173、174（两条不同 title）。

**C. `static-data.json` vs DB**：json 111 条 = 103 条在 DB + 8 条已从 DB 删除；DB 另有 89 条不在 json。

**D. id 冲突**：js 中 8 个 id（13–17、30–32）各出现两次（幽灵 + 正常行）；js 的 id 172–203 与 DB 自增 id 空间重叠，其中 173/174 在 DB 中是两条完全不同的新抓取记录 → 未来合并/重生成会撞主键语义。前端 `WaterfallGrid` 用 `key={item.id}`，`App.jsx` 用 `id` 做搜索结果集合匹配，重复 id 会导致 React key 冲突与搜索结果串行。

**E. 无 `created_time` 的 32 条**：`formatDate(undefined)` → `new Date(undefined)` 为 Invalid Date → 返回 `''`，卡片日期空白；`mergeIncremental` 的排序按字符串比较，这 32 条被追加在数组末尾（实测 index 111–142），并非真实时间序。

**F. 分类分布（js 143 条）**：文章 119、工具 10、言论 5、科技动态 3、资源 3、图片 2、文摘 1。

### 4.2 "如果照文档跑一次 gen:static-js 会怎样"

只做只读推演（未执行）：`existing=json(111)` ∪ `DB(192)`，按 URL 去重后 **200 条**（保留 8 条 DB 已删的、丢失 32 条手工 issue #410 的？——不，这 32 条会保留在 json 里？**不保留**：它们只在 js，不在 json，脚本读的是 json，因此会被整体覆盖丢失）；同时 `category` 字段会从 143 条变成 **0 条**。即：**一次"正常"的数据刷新会丢 32 条内容和全部分类，并把 json/js 扩到 200 条**。这是本次审计最严重的可执行风险。

---

## 5. 新鲜度时间线（2026-10-18 23:02 观测）

| 事件 | 时间 | 距今 |
|---|---|---|
| DB 最后一条记录写入 | 2026-08-28 13:22:58 | 51 天 |
| DB 提交 `7bbd5f5` | 2026-08-28 13:29:06 | 51 天 |
| `static-data.js` 生成（mtime） | 2026-08-28 10:45:25 | 51 天（且早于同批 DB 写入 2h37m） |
| `static-data.js` 提交 `4da5d06` | 2026-08-28 13:29:02 | 51 天 |
| `static-data.json` 生成/提交 | 2026-07-30 23:24 / `30f3b0a` | 80 天 |
| `db.enc` 更新 `72ab498` | 2026-07-31 08:55 | 79 天（对应 103 行时代） |
| 最近部署 gh-pages `8349665` | 2026-09-03 11:56 +08 | 45 天 |
| 本地 HEAD `22544ca` | 2026-09-02 22:36 | 46 天 |
| 本地 `dist/` 构建 | 2026-10-18 22:45 | 今天（手工 build，未部署） |

关键结论：**DB 不是新鲜的**（自 8-28 起没有新抓取），**前端比 DB 更旧**（缺 89 条），**json 比 js 旧**（缺 31 个 js 独有 URL + 分类）。CI 不重生成（`deploy.yml` 注释明确：in-CI regeneration 已移除），因此"部署新鲜度 = 开发者是否记得手动跑脚本并提交"。当前没有任何自动化或告警保证这一点。

---

## 6. 发现的问题（按严重度）

### P0

1. **分类数据不可复现 / 重生成即丢失**：`category` 只在 `static-data.js`；DB 无列、json 无字段、`generate-data.js` 不输出。运行 `npm run gen:static-js`（文档推荐动作）会清空全部 143 条分类，7 类筛选退化为全部"文章"。
2. **手工注入的 32 条内容没有任何可追溯来源**：不在 DB、不在 json、无 `created_time`、无抓取记录；`4da5d06` 只提交了 js 单行（`git show --numstat`：`1 1 src/assets/static-data.js`），无法从仓库重建。
3. **生产发布 39 条数据库中不存在的内容**（8 条已删 + 31 条从未入库），且增量合并无删除机制 → 错误会永久累积。

### P1

4. **89 条新内容未发布**（72 条净新增 + 17 条重复 title），包括 8-28 的全部抓取成果。
5. **32 条记录缺 `created_time`**：日期空白、排序落尾、无法按时间过滤。
6. **重复 URL / 重复 id / id 空间冲突**：1 组重复 URL（173/174），8 个重复 id，id 172–203 与 DB 自增 id 重叠。
7. **`static-data.json` 已失去"canonical"地位**：文档称其为 canonical，实际是 7-30 的陈旧快照；CI/前端只用 js；且它被 `.gitignore` 忽略却又 tracked（`git ls-files` 确认），行为容易误导。
8. **`.enc` 加密副本严重过期且无流程**：2026-07-31 从 103 行时代生成，当前 DB 192 行；`encrypt-db.sh` 仅手动、无 CI/钩子校验；明文 DB 本身按设计 tracked 在 git 中。任何人用旧 `.enc` 恢复都会丢掉 8-28 的 89 行。
9. **DB 重复内容未去重**：30 组重复 title（镜像站/聚合页），仅靠 `uid=md5(url)` 去重无法识别跨站同文，前端会出现重复卡片。

### P2

10. **0 字节的仓库根 `web_content.db`**：untracked（被 `*.db` 忽略），但多处以相对路径 `sqlite3.connect('web_content.db')` 打开（`fetch_from_params.py`、`web_content_extractor.py`、`test_system.py`）。若从仓库根运行，会写入这个空壳而不是 `python_scripts/web_content.db`。
11. **时间语义未声明**：`created_time` 为本地 naive 时间，无时区；文档未写。
12. **`manual_content` fallback 是死代码**：0 行；且其 `SELECT ... '' as original_url` 会让输出 URL 为空（`ContentCard` 外链失效），属于潜伏 bug。
13. **本地 `main` 落后 `origin/main` 一个提交**（`997cd99 feat: update gitignore`，未合并）；本次 `dist/` 是今天手工 build，与已部署包不同（部署仍是 9-03 包）。

---

## 7. Data-Quality Rules（建议落为检查）

| ID | 规则 | 当前状态 |
|---|---|---|
| R1 | `count(output) >= count(DB)`，且 `DB − output = ∅` | ❌ 89 条缺口 |
| R2 | `output − DB` 必须为空，或只允许 `legacy_allowlist` 中的 URL | ❌ 39 个 URL |
| R3 | `original_url` 非空且唯一 | ❌ 1 组重复 |
| R4 | `id` 唯一 | ❌ 8 个重复 |
| R5 | `created_time` 非空、`^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$`、可解析、≤ now+1d | ❌ 32 条空 |
| R6 | `category ∈ {科技动态,文章,工具,资源,图片,文摘,言论}` 且非空 | ✅（仅 js 内成立） |
| R7 | 输出必须带 `_meta: {generated_at, db_commit, db_rows, source_hash}` | ❌ 不存在 |
| R8 | 数据新鲜度：`now − max(created_time) ≤ 7d`，否则告警 | ❌ 51 天 |
| R9 | `.enc` 的 SHA256 必须对应最近一次生成的 DB（或从仓库移除） | ❌ 79 天 |
| R10 | 发布前 `git status --porcelain` 干净、DB/js/json 同批提交 | ⚠️ 历史上 DB 与 js 不同批（js 早 2.5h） |

验证 SQL（已实际执行的部分见 §9）：

```sql
-- R1/R2 需要在生成后对输出集合做，DB 侧参照集：
SELECT COUNT(*) AS db_rows, COUNT(DISTINCT original_url) AS distinct_urls,
       MIN(created_time) AS oldest, MAX(created_time) AS newest
FROM content_summary;

-- R3 重复 URL / R4 重复 title
SELECT original_url, COUNT(*) FROM content_summary GROUP BY 1 HAVING COUNT(*)>1;
SELECT title, COUNT(*), GROUP_CONCAT(id) FROM content_summary GROUP BY 1 HAVING COUNT(*)>1;

-- R5 时间格式与 NULL
SELECT COUNT(*) FROM content_summary WHERE created_time IS NULL
   OR created_time NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]';

-- uid 与 url 不一致（潜在篡改/拼接错误）
SELECT id, original_url FROM content_summary WHERE uid IS NOT NULL AND uid <> lower(hex(md5(original_url)));
```

> 注：SQLite 默认无 `md5()`；最后一条需在 Python/应用层实现（`uid_for()` 已有实现）。

---

## 8. Partition and Incremental Strategy（建议）

当前规模（192 行）不需要分区；但需要**可复现的增量协议**：

1. **单一权威源**：`content_summary` 增加 `category TEXT`、`created_at_utc TEXT`、`updated_at_utc TEXT`；分类写进 DB（或独立 `item_category` 表 + `assigned_by`/`assigned_at`），不再只存在 js。
2. **增量水位**：以 `MAX(id)` + `MAX(updated_at_utc)` 双水位；`uid` 仍是去重主键（`md5(url)`），但需处理 url 规范化（去 query/trailing slash）。若引入，旧 uid 需一次性回填。
3. **删除语义**：DB 用软删 `deleted_at`，生成脚本据 `deleted_at IS NULL` 过滤；`mergeIncremental` 必须支持 prune（当前只增不删）。
4. **输出带版本元数据**：`static-data.json` 写 `{_meta:{generated_at, db_git_sha, db_rows, schema_version}, items:[...]}`，js 由 json 派生（`--from-json`），保证两者永不分叉。
5. **生成即校验**：脚本末尾断言 R1–R6，失败 exit 1；CI 增加 "data freshness" job（只读校验，不重生成），R8 超阈告警。
6. **提交原子性**：DB、json、js 必须在同一 commit；建议 pre-commit hook 检查三者 mtime/内容一致性。
7. **加密副本**：从仓库移除 `.enc`（与"明文 DB 已 tracked"的设计矛盾且当前过期），或改为发布流程中由 CI 用 secret 生成并只作为 release artifact。

---

## 9. Validation Queries and Actual Results

已执行（只读，全部返回如上表）：

```sql
-- 1. 行数与时间范围
SELECT 'content_summary', COUNT(*) FROM content_summary
UNION ALL SELECT 'manual_content', COUNT(*) FROM manual_content;
-- → content_summary|192 ; manual_content|0

SELECT MIN(created_time), MAX(created_time) FROM content_summary;
-- → 2026-07-30 20:14:39 | 2026-08-28 13:22:58

-- 2. 日期分布
SELECT substr(created_time,1,10) d, COUNT(*) n FROM content_summary GROUP BY d ORDER BY d;
-- → 2026-07-30|103, 2026-08-06|2, 2026-08-28|87

-- 3. 唯一性与空值
SELECT COUNT(*), COUNT(DISTINCT original_url), COUNT(DISTINCT uid), SUM(uid IS NULL) FROM content_summary;
-- → 192 | 192 | 190 | 2

-- 4. 重复 title
SELECT COUNT(*) FROM (SELECT title FROM content_summary GROUP BY title HAVING COUNT(*)>1);
-- → 30
```

Python 集合运算（只读解析）：

```
json=111(111 unique)  js=143(142 unique)  db=192(192 unique)
J−S=0   S−J=31   S−D=39   D−S=89   D−J=89   J−D=8
J∩S∩D=103
js 与 DB 匹配行字段差异：{}（0）
js 与 json 共享行字段差异：{}（0，除新增 category）
js 缺 created_time：32（全部为 S−D 幽灵）
js 重复 id：{13,14,15,16,17,30,31,32} 各 2 次
js 重复 URL：weekly-issue-410 ×2（id 173,174）
js category：文章119 工具10 言论5 科技动态3 资源3 图片2 文摘1
```

部署侧只读核对：

```
origin/gh-pages 最新提交 8349665 (2026-09-03 03:56:48 +0000) "deploy: 997cd99..."
assets/index-1a0092fe.js 中 "original_url" 出现 144 次（143 条数据 + 1 处代码引用）
→ 线上就是这 143 条（含 39 条幽灵、32 条无日期），不是 DB 的 192 条
```

git 取证：

```
4da5d06^:static-data.js → 111 items, 111 with created_time, 0 with category
4da5d06 :static-data.js → 143 items, 111 with created_time, 143 with category
4da5d06 numstat: 1 1 src/assets/static-data.js   （单行全量替换，非脚本产物 diff）
```

---

## 10. Performance and Cost Considerations

- DB 物理 2.68 MB / 655 页；有效内容：`content` 1,090,718 B（占 ~41%，但**完全不参与前端**）、`summary` 42,452 B、`title` 7,927 B、`tags` 4,322 B。
- `generate-data.js` 用 sql.js 把**整个 DB 文件读进 WASM**；2.7 MB 目前无感，但 `content` 列是随抓取线性增长的"死重"，会放大内存与仓库体积（DB 已 tracked 进 git）。建议 `content` 拆到 `content_archive` 表或导出到 release artifact。
- 生成 + 构建成本可忽略：全表 192 行、输出 114 KB；`dist` 主 bundle 297 KB。真正的成本在抓取 + LLM 摘要（外部），不在查询。
- 查询侧：`idx_uid` 唯一索引保证 `INSERT OR IGNORE` 为 O(log n)；`idx_tags` 对 `tags` 前缀匹配用途有限（逗号串不是规范化多值），建议改 `item_tag` 关联表（当前 192 行无性能压力，属结构改进）。
- CI 每次 `npm install --legacy-peer-deps`（无 lockfile）是构建时间大头，与数据链路无关。

---

## 11. Unresolved Metadata Questions

1. `static-data.js` 里 32 条 issue #410 条目的原始 URL 来源与标题/摘要生成方式？仓库里没有对应脚本或数据文件（仅 commit message 声称"imported from issue #410"）。
2. `category` 是谁、用什么规则/模型标的？无 `assigned_by`/`assigned_at` 记录，无法复现或审计。
3. DB 中 8 条（id 13–32 的微信/网页文章）为何被删？`clean_db.py` 是 TRUNCATE，未发现局部删除脚本；删除事件无日志。
4. 2026-08-28 10:45 的 js 由哪份数据生成？当时 DB 应含 143 条左右，但 13:22 又写入 87 条并删除若干；无快照留证（`static-data-*.json` 快照只到 7-30，且被 gitignore）。
5. `created_time` 的业务时区是否确为 Asia/Shanghai？代码用 `datetime.now()`，没有 tz 配置。
6. `static-data.json` 究竟是不是 canonical？CLAUDE.md 说是，但 `.gitignore` 忽略、`deploy.yml` 不用、实际已落后 80 天。
7. `.enc` 是否仍是流程的一部分？谁在何时用它恢复过？密钥轮换策略？
8. 仓库根 0 字节 `web_content.db` 是谁创建的、是否可删？
9. 抓取侧是否计划恢复（自 8-28 起无新数据）？还是项目已进入"冻结发布"状态？

---

## 12. 建议的修复顺序（供后续任务拆解，本次不执行）

1. 先把**分类落库**（新增 `category` 列/表，从 js 回填 143 条，含 89 条未发布项的分类策略），否则任何数据刷新都会回退功能。
2. 把 js 的 32 条手工 issue #410 条目**补进 DB**（含 `created_time` 与来源），消灭唯一不可追溯数据。
3. 重写生成器：读 DB 为准、json 派生、带 `_meta` 与 R1–R6 断言、支持 prune；`--from-json` 只做格式转换不做合并。
4. 一次性重建 json+js（200 条左右），提交同一 commit，补 CI 只读校验与新鲜度告警。
5. 清理幽灵（39 URL）与重复 id/URL；决定 `.enc` 去留；删除根目录 0 字节 DB。
6. 重新部署（当前线上仍是 9-03 的 143 条）。

> 本次审计未修改任何数据文件、未运行生成器、未触碰加密脚本。
