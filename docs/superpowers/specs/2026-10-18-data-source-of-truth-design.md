# S1 设计：数据真源统一与生成器重建

- **日期**：2026-10-18
- **状态**：已确认（第 1–3 节经用户逐节确认后定稿）
- **范围**：只做数据链路（DB → 生成物 → CI 校验 → 文档同步），不改前端组件、不处理明文 DB 去留、不重构 CI 与 Python 包结构
- **依据审计**：[汇总](../audits/2026-10-18/summary.md)、[数据链路](../audits/2026-10-18/data-pipeline.md)、[测试门禁](../audits/2026-10-18/testing-quality.md)、[Python 后端](../audits/2026-10-18/python-backend.md)

## 1. 背景与问题

当前站点数据存在三份互不一致的来源：

| 来源 | 行数 | 最新时间 | category |
|---|---|---|---|
| `python_scripts/web_content.db` | 192 | 2026-08-28 | 无此列 |
| `src/assets/static-data.json` | 111 | 2026-07-30 | 无 |
| `src/assets/static-data.js`（线上） | 143 | 2026-07-30 | 143/143，手工维护 |

后果：

1. DB 中 89 条 8 月内容从未上线；站点上有 39 个 DB 中已不存在的 URL（32 条手工内容 + 8 条已从 DB 删除的旧文）。
2. `scripts/generate-data.js` 以 `static-data.json` 为合并底、从 DB 取数，两者都没有 `category`，且 `mergeIncremental` 只增不改。按现状执行一次 `npm run gen:static-js` 会产出约 200 条、`category` 为 0 条，并丢掉 32 条手工内容，全程无报错。
3. `static-data.js` 里存在 8 组重复 id（13–17、30–32，正好是 8 条已从 DB 删除的旧文与 DB 复用 id 的新文冲突），导致搜索结果按 id 过滤时多出卡片。
4. 没有任何数据校验：CI 只 build，不检查数据；文档还把这个会毁数据的命令描述成常规操作。

## 2. 目标与非目标

**目标**

- DB 成为唯一数据真源；`category` 落库，生成物完全由 DB 派生。
- 32 条手工内容补录进 DB；8 条已从 DB 删除的旧文随真源切换移除。
- 生成器单向、写前校验、失败不落盘；CI 能拦住数据漂移。
- 每周内容更新流程收敛为：改 DB → `npm run gen:static-js` → 提交 → 自动部署。

**非目标**

- 前端组件、样式与交互 bug（S2）。
- 明文 DB 的跟踪与加密策略、供应链（S3）。
- CI 权限、并发、部署后冒烟、Cloudflare/`base` 问题（S4）。
- Python 包整体结构与 legacy 脚本归档（S5）。

## 3. 决策记录

| 决策 | 选择 | 说明 |
|---|---|---|
| 数据真源 | **DB 唯一真源** | `static-data.json`/`.js` 均为派生文件，不再手工编辑 |
| 分类来源 | **LLM 自动分类 + 人工可改** | 现有分类保留；缺失的用 DeepSeek 一次性补齐；人工值不被覆盖 |
| 发布流程 | **本地生成 + CI 校验** | CI 不生成数据，只校验一致性；校验失败阻断部署 |
| 8 条幽灵内容 | 随 DB 真源移除 | 用户已确认；数据仍可从 git 历史与旧 `static-data.js` 找回 |
| 32 条 `created_time` | 统一填 `2026-08-28 13:29:02` | 推断值（导入 commit `4da5d06` 的时间），迁移报告中标注 |
| 时间戳快照 | 取消 | 删除现有 7 个 `static-data-<ts>.json`，不再生成 |
| 缩水保护 | 行数下降 > 10% 默认拒绝 | `--allow-shrink` 显式放行 |
| 手工编辑数据文件 | 禁止 | 文档与生成器都会明确这一点 |

## 4. 数据模型

### 4.1 表结构变更

```sql
ALTER TABLE content_summary ADD COLUMN category TEXT;
ALTER TABLE content_summary ADD COLUMN category_source TEXT DEFAULT 'default';
```

`category_source` 取值与语义：

| 值 | 含义 | 是否允许被 LLM 覆盖 |
|---|---|---|
| `manual` | 人工标注（`set_category.py` 或历史手工分类） | 否 |
| `llm` | LLM 分类结果 | 否（只在 NULL 时写入） |
| `legacy-default` | 2026-08 引入七分类时批量默认的「文章」 | 否 |
| `default` | 迁移/入库分类失败时的兜底「文章」（迁移中仅在显式 `--allow-fallback` 时写入） | 否（LLM 任务只处理 NULL；重跑需先清空该行） |

不加 `CHECK` 约束：SQLite 对 `ALTER TABLE ADD COLUMN` 的约束能力有限，校验放在生成器与 CI。

`uid`（`md5(original_url)`，`idx_uid` 唯一索引）当前有 2 行为 NULL，迁移时补全；若 `original_url` 为空，用 `md5(title + created_time)`。

**前置说明**：分类器实现为独立模块 `python_scripts/category_classifier.py`，直接用 `openai` SDK + `dotenv` 调 DeepSeek，不 import `web_content_system`，因此不受该包顶层拉起 selenium 的问题影响（包结构问题留给 S5）。

### 4.2 分类回填

按优先级执行，幂等：

1. **保留现有分类**：从 `static-data.js` 建立 `original_url → category` 映射（143 条）。命中 DB 的行写入 `category`，其中 32 条手工分类记 `manual`，其余（103 条旧文）记 `legacy-default`。
2. **补齐缺失**：DB 中 `category IS NULL` 的行（约 89 条 8 月内容）用 DeepSeek 分类，记 `llm`。按每批 10 条（标题 + 摘要）请求，要求返回 JSON 数组，校验只含七类之一；整批失败且拿到 client 时重试一次。仍失败的行**保持 `category=NULL`、`category_source=NULL`**，计入 `classify_failed`，迁移随后返回非 0——修复 key/网络后重跑即可重试；只有显式 `--allow-fallback` 才写「文章」+ `default`。
3. **人工修正**：`python_scripts/set_category.py <url|id> <分类>` 写入 `manual`。以后任何分类任务只处理 `category IS NULL` 的行，不覆盖已有值。
4. **新内容入库时分类**：`fetch_from_params.py` 的 `save_to_db()` 与 `crawler_subpages.py` 的 `insert_row()` 在写入前调用 `category_classifier.classify_one(title, summary)`，写入 `category` 与 `category_source`（成功 `llm`，失败 `default`）。已有行的 `update_content` 路径不改分类。

七类枚举：科技动态 / 文章 / 工具 / 资源 / 图片 / 文摘 / 言论（与 `src/utils/categories.js` 保持一致）。

LLM 不可用时（未安装 `openai`、未配置 `DEEPSEEK_API_KEY`、网络失败）：迁移**不静默兜底**——失败行保持 NULL、返回非 0 并提示修复后重跑（`--allow-fallback` 可显式接受「文章」兜底）。入库路径不同：为不阻塞抓取且保证站点可构建，`save_to_db`/`insert_row` 分类失败时落「文章」+ `default`（后续可对这些行重跑分类）。

### 4.3 32 条手工内容补录

从 `static-data.js` 取 `original_url` 不在 DB 且 `created_time` 为空的 32 条：

- 字段：`title`、`summary`、`original_url`、`tags`、`category` 原样写入；`content` 留空；`created_time = '2026-08-28 13:29:02'`。
- `uid`：正常为 `md5(original_url)`；其中两条共用 `https://www.ruanyifeng.com/blog/2026/08/weekly-issue-410.html`，第二条用 `md5(original_url + '|' + title)` 避免唯一索引冲突。
- 插入后 `id` 由 SQLite 自增分配（预计 487 起），取代旧的 172–203。

### 4.4 8 条幽灵内容

id 13–17、30–32 共 8 条只存在于 `static-data.js`、DB 中已删除。按 DB 真源原则不再进入生成物，重复 id 问题随之消失。保留记录：旧文件仍在 git 历史；如需恢复，从 `4da5d06` 的 `static-data.js` 提取后重新入库。

### 4.5 目标行数

`192 + 32 = 224` 行；站点、DB、生成物三方一致。

## 5. 迁移脚本

`python_scripts/migrate_category.py`：

- 先备份 DB 到 `python_scripts/backups/web_content-<ts>.db`，迁移报告写到 `python_scripts/backups/migration-report-<ts>.json`（该目录 gitignored），再执行变更。
- `--dry-run` 输出完整迁移报告，不写库。
- 步骤：加列 → 补 `uid` → 写回现有分类 → 插入 32 条 → LLM 补齐（可 `--skip-llm`）→ 输出报告。
- 幂等：列已存在则跳过；32 条按 `original_url` 判重；分类只写 `category IS NULL` 的行。
- 报告内容：新增条数、uid 补全数、分类分布（按 source 分列）、LLM 失败数、总行数、耗时。
- 失败时事务回滚，DB 保持迁移前状态。

## 6. 生成器

`scripts/generate-data.js` 重写为单向管线，保留现有 npm 命令名 `gen:static-js`：

1. 只读打开 `python_scripts/web_content.db`（`sql.js`，devDependency）。
2. 查询：`SELECT id, title, created_time, summary, original_url, tags, category FROM content_summary ORDER BY created_time DESC, id DESC`。
3. 校验（规则实现在 `scripts/lib/data-rules.mjs`，生成器与检查脚本共用）：
   - `rows.length > 0`
   - `category` 100% ∈ 七类
   - `id` 唯一
   - `tags` 非空
   - `created_time` 可解析（`YYYY-MM-DD HH:MM:SS`）
   - 行数相对现有 `static-data.js` 下降不超过 10%（否则拒绝，`--allow-shrink` 放行）
   - `original_url` 重复只告警不阻断（合并后仍允许同一 URL 对应不同标题）
4. 任何校验失败：打印具体违约行，退出码非 0，两个输出文件都不改动。
5. 输出（临时文件 + 原子 rename）：
   - `src/assets/static-data.json`：2 空格格式化，供 diff review
   - `src/assets/static-data.js`：`export default [...]`，构建实际使用
6. 不再生成 `static-data-<ts>.json` 快照；删除仓库现有 7 个快照。
7. 移除 `--from-json` 模式及其 npm 脚本 `gen:static-js:from-json`（避免再次从旧 json 派生）。
8. 调整 `.gitignore`：把 `src/assets/static-data*.json` 改为只匹配快照的前缀规则 `src/assets/static-data-*.json`，使 canonical 的 `static-data.json` 不被忽略（当前它虽被跟踪，但规则语义矛盾）。

## 7. `check:data` 与 CI

- 新增 `npm run check:data` → `scripts/check-data.mjs`：读 DB 与 `static-data.js`，按同一套规则校验字段与一致性（条数、id 集合、分类覆盖、时间可解析），并校验 `static-data.json` 与 `static-data.js` 是同一份数据；不一致或违约时非零退出。
- 单测：用 Node 内置 `node --test`，覆盖 `data-rules.mjs` 的关键规则（缺分类、重复 id、断崖缩水、空 tags、坏时间）与生成器的纯函数。
- CI（`.github/workflows/deploy.yml`）在 S1 只加校验步骤，其余不动：
  - PR：`npm ci` 不可用（无 lockfile），维持 `npm install --legacy-peer-deps` → `test:data` → `check:data` → `build`
  - push main：`test:data` → `check:data` → `build` → 部署（校验失败即不部署）
  - lint 门禁暂不加：线上代码当前有 3 个已存在的 lint error（属 S2 修复范围），现在加会让部署变红；S2 修完、S4 再接。
- 完整的 `permissions`/`concurrency`/部署后冒烟留给 S4。

## 8. 人工修正闭环

`python_scripts/set_category.py <url|id> <分类>`：

- 校验分类 ∈ 七类，写入 `category` 且 `category_source='manual'`。
- 找到多条时报错并列出候选，要求用 `--id` 精确指定。
- 之后执行 `npm run gen:static-js` 并提交数据文件。

## 9. 文档更新

- `CLAUDE.md`：数据链路改为 DB 唯一真源；删掉"category 由抽取/回填赋值但不在 schema"的错误说法；补迁移与分类命令。
- `AGENTS.md`：目录结构去掉已删除文件，补 `migrate_category.py`/`set_category.py`/`check:data`。
- `dev.md`：更正加密数据库与 CI 解密的错误描述（仅描述现状，策略留 S3）。
- `README.md`：按现状重写数据来源与构建说明，补"每周更新内容"流程。
- 删除所有"不要跑 gen:static-js"的警告（届时已不成立），改为"不要手工编辑 static-data.\*"。

## 10. 验收标准

- DB 224 行；`category` 覆盖 100%；迁移报告包含 source 分布与 LLM 失败数；apply 模式下 `classify_failed` 必须为 0 且退出码 0（失败则退出码 2、失败行保持 NULL，修复后重跑）。
- 生成物 224 条；`id` 唯一；`created_time` 全部可解析；无 DB 中不存在的 URL。
- `npm run check:data`、`npm run test:data`、`npm run build` 通过；`npm run lint` 不新增错误（已知 3 个 error 属 S2）。
- 生成器对三类坏输入有单测并通过：缺分类、重复 id、断崖缩水。
- 抓取入库路径的新条目在模拟分类器下能写入 `category`/`category_source`（单测覆盖）；分类器不可用时落「文章」+ `default`。
- 线上站点显示 224 条；分类计数与 DB 分布一致；搜索"英伟达财报"不再多出卡片。
- `static-data.json` 与 `static-data.js` 内容一致（同一生成结果）。

## 11. 风险与回滚

| 风险 | 缓解 |
|---|---|
| LLM 分类质量不稳 | 抽样 10 条人工核对；错的一键 `set_category` 修正 |
| 32 条日期为推断值 | 文档与迁移报告标注；后续可逐条修正 |
| 8 条内容消失 | 已确认接受；数据可从 git 历史恢复 |
| DB 变更不可逆 | 迁移前备份；迁移幂等；回滚 = 还原备份 + `git revert` 数据/代码 commit |
| 生成器误拦正常更新 | 缩水阈值可调，`--allow-shrink` 显式放行并在日志中记录 |
| 分类枚举两处定义漂移 | `check:data` 校验；后续可抽共享常量 |

## 12. 交付物

新增：

- `python_scripts/migrate_category.py`
- `python_scripts/set_category.py`
- `python_scripts/category_classifier.py`
- `python_scripts/test_category_classifier.py`
- `scripts/lib/data-rules.mjs` + `scripts/lib/data-rules.test.mjs`
- `scripts/check-data.mjs`
- 迁移报告 `python_scripts/backups/migration-report-<ts>.json`（运行后生成，gitignored）

修改：

- `scripts/generate-data.js`（重写）
- `python_scripts/fetch_from_params.py`（入库时写分类）
- `python_scripts/crawler_subpages.py`（入库时写分类）
- `package.json`（`check:data`、`test:data` 脚本）
- `.github/workflows/deploy.yml`（加 lint/check 步骤）
- `src/assets/static-data.json`、`src/assets/static-data.js`（重新生成）
- `CLAUDE.md`、`AGENTS.md`、`dev.md`、`README.md`
- `.gitignore`（快照与备份目录）

删除：

- `src/assets/static-data-20260730-*.json`（7 个快照）

## 13. 后续（不在本设计内）

- S2：前端重复 id 的防御性处理、`SourcesGrid` query 打通、空态、弹窗、sticky。
- S3：明文 DB 跟踪策略与加密控制、供应链。
- S4：CI 权限/并发/冒烟、`base` 与生产入口。
- S5：Python 包结构、logging/retry、legacy 归档、测试体系。
