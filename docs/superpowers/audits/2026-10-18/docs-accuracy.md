# 文档准确性审计：README / AGENTS / CLAUDE / dev.md

- 审计日期：2026-10-18（Asia/Shanghai）
- 审计人：Scribe（Documentation Engineer）
- 审计模式：**只读**。未修改任何文档、代码、数据或 Git 状态；本次唯一写入是本报告。
- 审计对象：`README.md`、`AGENTS.md`、`CLAUDE.md`、`dev.md`（附带 `python_scripts/README.md`），对照当前工作区 `HEAD=22544ca`（本地 `main`）的实际代码与数据。
- 对照基准补充：`origin/main`（`997cd99`）包含本地 checkout **没有**的 2026-09-03「信息检索 / Last30Days」功能与其两份设计文档，本次以只读方式（`git show`，未 checkout/reset）一并审计，相关结论单独标注「origin/main」。
- 验证环境：macOS；Node v22.23.1 / npm 10.9.8；Python 3.11.15（pyenv，未安装 `selenium` / `openai`）。
- 关联审计：数据链路细节见同目录 `data-pipeline.md`；加密/泄密风险见 `security-privacy.md`。本报告不重复其结论，只引用。
- 严重度：🟥 高（会导致数据丢失或流程失败）/ 🟧 中（明显过时或缺失）/ 🟨 低（措辞、细节）

---

## 1. 结论摘要

四份文档描述的系统状态与仓库现状存在**结构性偏差**：README.md 与 dev.md 描述的是 2026-07 之前的设计，AGENTS.md 停留在旧目录结构，CLAUDE.md 最准确但有两处硬事实错误和三个关键流程缺口。

**最严重的一点**：文档把 `npm run gen:static-js` 写成"从 DB 重新生成站点数据"的常规动作，但按当前数据状态执行它，会**丢掉 32 条手工内容 + 全部 143 条 `category` 分类**（只读推演：`111 + 89 = 200` 条，`category` 0 条）。文档没有任何警告。

**第二点**：`origin/main` 上已上线「信息检索 / Last30Days」双视图功能，配有 156 行设计文档 + 738 行实现计划，但**没有任何面向用户的说明**（README/AGENTS/CLAUDE/dev.md 在本地和 origin/main 上都没有记载）；设计文档与线上代码还有 4 处偏差（arXiv 参数写错、URL 预览交互不存在、组件顺序不同、卡片查询功能实际未生效）。详见 §3.6。

| 文档 | 判定 | 主要问题 |
|---|---|---|
| `README.md` | 🟥 严重过时 | 仍写"浏览器用 sql.js 读 SQLite / 当前是模拟数据"，与"构建期静态 bundle"的现状完全相反；结构、功能、部署说明均缺项 |
| `AGENTS.md` | 🟥 结构性过时 | 目录结构含已删除的 `sqliteReader.js`；DB schema 缺 `uid`/`content` 列；`gen:static-js` 描述错误；测试命令当前跑不通 |
| `CLAUDE.md` | 🟧 基本准确 | 架构和 Gotchas 大部分经核对为真；但"category 由抽取/回填赋值"无任何代码支撑；三个实际写库脚本完全未提 |
| `dev.md` | 🟥 与 CI 现状矛盾 | 声称 CI 会解密数据库（实际解密步骤已移除）；声称明文 DB 被 git 忽略（实际是**故意 tracked**） |
| `python_scripts/README.md`（周围） | 🟧 过时 | 未提 `fetch_from_params.py` / `crawler_subpages.py` / `backfill_content.py` 三个现行脚本 |
| `origin/main` 独有文档（spec + plan，本地 checkout 不存在） | 🟧 部分准确 | 是「信息检索」新功能的唯一说明；与线上代码有 4 处偏差，且没有任何面向用户的使用说明（见 §3.6） |

---

## 2. 重点：每周新增内容的真实流程 vs 文档

> 这一节是本次审计要求的最有价值部分。流程是从**代码 + 提交历史 + 数据状态**重建的，**未经用户确认**；文档目前没有任何一处完整描述它。

### 2.1 真实流程（重建）

仓库里存在两条并行的"新增内容"路径，文档都没有写清楚：

**路径 A：从 URL 抓取入库**（脚本存在、可用、但文档未提）

1. 把待抓 URL 写进 `python_scripts/grab_params.json`：`[{"url": "...", "tags": "...", "done": false}]`
   - 证据：`git show ce7b263` 只改了这个文件（"add ZAKER and arthurchiao AI articles to grab list"）。
2. `cd python_scripts && python3 fetch_from_params.py`
   - 只处理 `done:false`；HTTP 抓取 → DeepSeek 摘要（失败回退 Ollama → 截取前 200 字）→ 写 `content_summary`，按 `uid=md5(url)` 去重，成功后把 `done` 置回 true。
   - 证据：`fetch_from_params.py` 文件头 docstring（第 5–13 行）与 `main()`（第 262–371 行）；当前仍有 2 条 pending（`xueqiu.com/4855909358/361171647`、`wallstreetcn.com/articles/3761015`）。
3. 或跑源站批量爬取：`cd python_scripts && python3 crawler_subpages.py`
   - 13 个 `ROOT_URLS`：chuan.us、mywiki、xiaolai.co、lixiaolai.com、阮一峰周刊镜像（vibecodinghub）、GitHub `ruanyf/weekly/issues`、GitHub `ruanyf/weekly` 仓库，加 6 个热榜/聚合站；每站最多 30 个子页，`uid` 唯一索引保证可重跑。
   - 证据：`crawler_subpages.py` 第 47–140 行（含注释）；`git show 7bbd5f5` 显示它只提交了 `crawler_subpages.py + web_content.db`，**没有更新站点数据**。
4. 可选补正文：`python3 backfill_content.py [--all] [--limit N]`（只更新 `content` 列，保留摘要）。
5. 生成站点数据：`npm run gen:static-js` → 写 `src/assets/static-data.json` + `.js` + 时间戳快照。
6. **分类**：`category` 字段**不来自 DB**（DB 无此列），也没有任何脚本生成；`4da5d06` 是直接手改 `static-data.js` 单行、给 143 条打上 7 分类并追加 32 条周刊条目。
7. 构建/发布：`npm run build`，或 commit 后 push（CI 构建并推 `gh-pages`）。

**路径 B：手工精选条目**（当前 32 条 issue #410 内容就是这样进来的）
直接用编辑器改 `src/assets/static-data.js`，不经过 DB。仓库里没有脚本、没有记录，`created_time` 没填（32 条 id 172–203 全部缺 `created_time`）。

### 2.2 文档缺什么

| 步骤 | 实际命令/文件 | 文档现状 | 后果 |
|---|---|---|---|
| 1 收集 URL | `grab_params.json` / `crawler_subpages.py:ROOT_URLS` | CLAUDE 只说"`grab_params.json` drives batch scraping"，没说是哪个脚本；ROOT_URLS 无人提 | 找不到正确的抓取入口 |
| 2 抓取写库 | `fetch_from_params.py`、`crawler_subpages.py` | **四份文档全部未提**；AGENTS/CLAUDE 只指向 `main.py` 菜单 5（另一套走 `WebContentExtractor` 的旧路径） | 用了旧入口，行为/去重逻辑不同 |
| 3 补正文 | `backfill_content.py` | 未提 | 新内容 `content` 列为空 |
| 4 生成站点数据 | `npm run gen:static-js` | CLAUDE/AGENTS 有命令，但**没有破坏性警告** | 见 2.4：丢 32 条 + 全部分类 |
| 5 分类 | 手工改 `static-data.js` | 无任何说明；CLAUDE 反而说"由抽取/回填赋值"（不存在） | 改完数据分类消失，且无法复现 |
| 6 验证 | `npm run lint`、`npm run build`、`python -m pytest` | lint 未提；pytest 命令当前失败（见 4.3） | 无验收标准 |
| 7 发布 | push → CI → `gh-pages` | README/AGENTS 有；但没说"CI 不重生成数据，必须提交 static-data.*" | 只推代码，站点数据不变 |
| 环境 | 必须在 `python_scripts/` 下跑抓取脚本 | 未提；`fetch_from_params.py` 的 `DB_PATH="web_content.db"` 是**相对路径** | 从仓库根运行会写进根目录那个 0 字节 `web_content.db` |

### 2.3 正确命令（逐条验证状态）

| 目的 | 命令 | 状态 |
|---|---|---|
| 安装依赖 | `npm install` | 未重跑（`node_modules/` 已在；CI 用 `npm install --legacy-peer-deps`，无 lockfile） |
| 本地开发 | `npm run dev` | ✅ 已验证：Vite ready，`http://localhost:5173/` 返回 200 |
| 构建 | `npm run build` | ✅ 已验证：372 modules，`dist/assets/index-4b9e4ec2.js` 241 KB，约 0.85 s |
| Lint | `npm run lint` | ✅ 已验证：0 error / 0 warning |
| 抓取 URL 入库 | `cd python_scripts && python3 fetch_from_params.py` | 未执行（会联网 + 写 DB）；代码路径已核对 |
| 源站爬取 | `cd python_scripts && python3 crawler_subpages.py` | 未执行（会联网 + 写 DB）；13 个源站已核对 |
| 补正文 | `cd python_scripts && python3 backfill_content.py [--all] [--limit N]` | 未执行；参数已核对 |
| 生成站点数据 | `npm run gen:static-js` | ⛔ **禁止**：只读推演会丢 32 条 + 全部 category（见 2.4） |
| 从 JSON 生成 | `npm run gen:static-js:from-json` | ⛔ **禁止**：会把 `.js` 回退到 111 条且 0 category |
| 后端测试 | `cd python_scripts && python3 -m pytest test_*.py` | ❌ 收集失败：`ModuleNotFoundError: No module named 'selenium'` |
| 后端测试（可跑部分） | `cd python_scripts && python3 -m pytest test_modular.py` | ✅ 已验证：5 passed |
| 交互式 CLI | `cd python_scripts && python3 main.py` | ❌ 同一缺依赖问题（`selenium`） |
| 加密副本 | `SQLITE_KEY=... ./scripts/encrypt-db.sh` | 未执行（会覆盖 tracked 的 `web_content.db.enc`） |
| 发布 | `git push origin main` | ⛔ 当前分支与 `origin/main` 无共同祖先，普通 push 预计被拒（未实际推送验证） |

### 2.4 为什么"照文档跑一次重生成"会毁数据（只读推演）

`scripts/generate-data.js` 的合并基线是 **`static-data.json`**（第 153 行），不是 `static-data.js`：

- `static-data.json`：111 条、**0 条 `category`**、停留在 2026-07-30；
- `web_content.db`：192 行，其中 89 行的 URL 不在 json 里；
- `static-data.js`：143 条（142 个唯一 URL），其中 32 条 id 172–203（issue #410 手工条目）**只存在于 .js**。

在 `/tmp` 内用同一 SQL 与同一合并函数做无写出推演，结果：**200 条、`category` 0 条、重复 id 8 个、32 条手工条目消失**。即：文档里"刷新数据"的常规命令，实际是一次不可逆的内容与分类删除。

### 2.5 修复后应有的优雅流程（建议，未执行）

```bash
# 前置一次性修复：category 落库 + 生成器以 js 为基线（详见 §6 P0）
cd python_scripts
python3 fetch_from_params.py          # 或 python3 crawler_subpages.py
python3 backfill_content.py           # 可选，补 content 列
cd ..
npm run gen:static-js                 # 此时才安全（保留 category、不丢手工条目）
npm run lint && npm run build         # 验收
git add -A && git commit -m "feat(content): weekly update"
git push origin main                  # 需先解决分支分叉，见 §5 R-05 / §3.6.3
```

在修复完成之前，**每周新增内容的正确做法是显式二选一**，并在提交信息里注明：

- 纯抓取类内容 → 抓库后**手工**把新记录追加进 `static-data.js`（保留 category 字段），或先修生成器；
- 精选类内容 → 直接编辑 `static-data.js`（沿用 `4da5d06` 的做法），并补上 `created_time`。

---

## 3. 逐文档发现

### 3.1 `README.md`

| # | 位置 | 严重度 | 现状 | 证据 |
|---|---|---|---|---|
| D-01 | L13–29 项目结构 | 🟥 | 列了 `src/utils/sqliteReader.js`（已不存在）；漏了 `SearchBar`、`CategoryFilter`、`ReportsPanel`、`ReportModal`、`LinksPanel`、`categories.js`、`formatDate.js`、`static-data.js/.json`、`static-reports.js`、`static-links.js` | `ls src/components src/utils`：8 个组件、2 个 utils |
| D-02 | L63–72「SQLite 数据读取」 | 🟥 | 说"浏览器中需用 sql.js 读取 SQLite""当前实现使用模拟数据" | `src/App.jsx:10` 直接 `import data from './assets/static-data.js'`；前端运行时不读 DB；`sql.js` 只是 devDependency，仅 `scripts/generate-data.js` 使用 |
| D-03 | L72、L91–95「自定义」 | 🟧 | 指导读者"实现真实 SQLite 读取 + 文件上传"，这是已完成且被放弃的方向 | 站点是构建期静态 bundle，无运行时 DB |
| D-04 | L87「点击顶部导航的 A股矩阵看板」 | 🟨 | 顶部没有导航；看板入口是 `ReportsPanel` 的报告卡片 | `grep -rn "看板" src/` 只命中 `static-reports.js`；`App.jsx` header 无 nav |
| D-05 | L5–11 功能特点 | 🟧 | 缺 7 类分类筛选、Fuse 搜索、分析报告栏目、信息源头栏目 | `App.jsx` 实际渲染这些组件 |
| D-06 | L38–59 安装运行 | 🟧 | 缺 Node ≥ 20、`npm run lint`、`npm run gen:static-js`、`:from-json`、`preview` | `package.json` engines/scripts |
| D-07 | L108–116 部署 | 🟧 | 只写"装依赖→构建→部署"；没写 CI **不重新生成数据**（必须提交 `static-data.*`），也没写站点 URL | `.github/workflows/deploy.yml` 注释明确移除 in-CI 重生成 |
| D-08 | 全文 | 🟨 | 无线上地址、无故障排查；浏览器兼容列表未经实测 | — |

### 3.2 `AGENTS.md`

| # | 位置 | 严重度 | 现状 | 证据 |
|---|---|---|---|---|
| D-09 | L9–31 项目结构 | 🟥 | 同 D-01；`utils/sqliteReader.js` 不存在；缺 5 个组件与 static 资产 | 同上 |
| D-10 | L40 `gen:static-js` 描述 | 🟥 | 写成 "Generate static JS from JSON data"；实际是 **DB → json + js**，读 JSON 的是 `gen:static-js:from-json` | `scripts/generate-data.js` L67–162 |
| D-11 | L101 DB schema | 🟥 | 写成 `id,title,created_time,summary,original_url,tags`；实际还有 `uid` 与 `content` | `sqlite3 ... ".schema content_summary"` |
| D-12 | L65 测试命令 | 🟧 | `python -m pytest test_*.py` 当前收集失败（缺 selenium）；且 `test_system.py` 是 print 风格脚本，不是 pytest 用例 | 实测报错；`test_system.py` 全文 |
| D-13 | L37–40 构建命令表 | 🟧 | 缺 `lint`、`gen:static-js:from-json`，未提 CI 的 `--legacy-peer-deps` | `package.json`、`deploy.yml` |
| D-14 | L91–96 配置 | 🟧 | 缺 `DB_PATH`、`DEEPSEEK_BASE_URL/MODEL`、`OLLAMA_MODEL`；`OLLAMA_API_URL` 默认值在 `.env.example` 写 `/api/generate`，而 `fetch_from_params.py` 用 base + `/api/chat` | `config.py`、`fetch_from_params.py:180–184` |
| D-15 | L84–88 Git 流程 | 🟨 | 未提 `pull_request` 也会触发部署工作流 | `deploy.yml` `on:` |

### 3.3 `CLAUDE.md`（最准确的一份）

| # | 位置 | 严重度 | 现状 | 证据 |
|---|---|---|---|---|
| D-16 | L71「category … assigned during extraction/backfill」 | 🟥 | 仓库里**没有任何**给 category 赋值的代码；php 中无此列。真实来源是手工改 `static-data.js` | `grep -rn category scripts/ python_scripts/*.py` 无命中；DB schema 无此列 |
| D-17 | L16–26 命令清单 | 🟧 | 正确但缺三个实际写库脚本：`fetch_from_params.py`、`crawler_subpages.py`、`backfill_content.py` | 见 §2 |
| D-18 | L64 schema 说明 | 🟧 | "`manual_content`（adds full `content`）"有误导：现在 `content_summary` **也有** `content` 列；`manual_content` 反而没有 `uid` | 实测 schema |
| D-19 | L51「Items lacking `category` render as `文章`」 | 🟧 | 只有徽章配色回退到"文章"；分类筛选是严格相等，缺 category 的条目在选"文章"时**不会**出现 | `ContentCard.jsx:6`；`App.jsx` `item.category === selectedCategory` |
| D-20 | L68–72 Gotchas | 🟧 | 缺最重要的一条：`gen:static-js` 会丢 category / 丢手工条目（见 2.4） | 推演结果 |
| D-21 | L20–21 重生成命令 | 🟧 | 没有说明合并基线是 `static-data.json`、没有"先备份"提示 | `generate-data.js:153` |
| D-22 | 全文 | 🟨 | 无线上 URL；未提 origin/main 上已有的 Last30days 页面（见 §3.6） | — |

### 3.4 `dev.md`

| # | 位置 | 严重度 | 现状 | 证据 |
|---|---|---|---|---|
| D-23 | L5、L35–44「deploy.yml 会自动解密数据库」 | 🟥 | CI 没有解密步骤，也不读 DB；明文 DB/加密副本都只是被提交 | `deploy.yml` 注释："in-CI regeneration … intentionally removed" |
| D-24 | L31「raw `web_content.db` is ignored by git」 | 🟥 | 与实际相反：`web_content.db` 与 `.enc` 都**故意 tracked** | `git ls-files`、`.gitignore` 内注释 |
| D-25 | L5–31 加密流程 | 🟧 | 加密脚本存在且可用，但没有任何消费者（CI/前端都不用）；照文档做只是多改一个 tracked 文件 | `scripts/encrypt-db.sh`、`deploy.yml` |
| D-26 | L9–21 列表编号 | 🟨 | 缩进错乱：`1.` 之后又是 `2.`，Markdown 渲染成两层 | 原文 |
| D-27 | 全文 | 🟧 | 完全没有"每周新增内容"流程；对当前运维最关键的文档反而最不相关 | — |

### 3.5 `python_scripts/README.md`（相邻，建议一并更新）

- 描述的是 `main.py` + Selenium 的老系统；未提 `fetch_from_params.py` / `crawler_subpages.py` / `backfill_content.py`。
- `OLLAMA_API_URL` 示例为 `http://localhost:11434/api/generate`，与 `fetch_from_params.py` 的 `/api/chat` 用法不一致。
- 自称 Python 3.8+，实际未在任何环境验证。

---

### 3.6 `origin/main` 上「信息检索 / Last30Days」新功能的文档

这两份文档**只在 `origin/main`，本地 checkout 不存在**（`git ls-tree HEAD -- docs/superpowers` 无 09-03 条目）：

| 文档（origin/main） | 行数 | 性质 |
|---|---|---|
| `docs/superpowers/specs/2026-09-03-last30days-search-page-design.md` | 156 | 设计规格，状态「已批准」 |
| `docs/superpowers/plans/2026-09-03-last30days-search-page-implementation-plan.md` | 738 | 8 个任务 + 验收清单 |

#### 3.6.1 设计文档与线上代码的一致性（origin/main ↔ gh-pages bundle）

线上 bundle `.../deepthink/assets/index-1a0092fe.js`（318 698 B）含 `内容浏览` / `信息检索` / `跨源搜索` 字符串，确认该功能已发布；`App.jsx` 用 `currentView` 状态切换双视图（无路由，URL 不变）。

| # | 设计文档写的 | 实际代码（origin/main） | 判定 |
|---|---|---|---|
| O-01 | arXiv 模板 `https://arxiv.org/search/?search={q}` | `last30days-sources.js`：`?search_query={q}` | 🟧 文档错、代码对 |
| O-02 | SearchHero「输入时实时更新 URL 预览」 | 只渲染「快速跳转」按钮组，无 URL 预览 | 🟧 文档描述了不存在的交互 |
| O-03 | 页面组件顺序 SearchHero → SourcesGrid → PhilosophySection | 实际 SearchHero → PhilosophySection → SourcesGrid | 🟨 顺序不同 |
| O-04 | 13 个信息源及 ID / 模板 / signal 表 | 代码 13 个，ID 与 signal 全部一致 | ✅ 一致 |
| O-05 | 卡片点击 `window.open(url, '_blank')` | 一致 | ✅ 一致 |
| O-06 | SourcesGrid 按当前查询词生成各平台搜索链接 | `Last30daysPage` 的 `query` state 从未被 set，`SourcesGrid` 恒收到空串：卡片恒半透明，点击打开的是 `?q=` 空搜索页 | 🟥 文档假设的功能未生效（代码缺陷，非文档错） |

> O-06：`Last30daysPage.jsx` 第 6 行 `const [query, setQuery] = useState('')` 的 setter 未被使用，`SearchHero` 维护自己的 state。结果「信息源卡片」退化为「打开平台」入口；计划 Task 8 的验收项「点击信息源卡片正确跳转」只在空查询下成立。本项为只读代码推断，未在浏览器实测。

#### 3.6.2 新功能在面向用户的文档里完全没有记载

本地与 `origin/main` 的 README / AGENTS / CLAUDE / dev.md **内容完全相同**（`git diff HEAD origin/main` 无文档差异），且四份都**未出现**「信息检索」「Last30Days」「Tab / 双视图」等字样（已 grep 核实）。缺失的具体内容：

- README 的功能列表（L5–11）与使用说明（L80–87）没有 Tab 说明；
- 未说明两个视图各自做什么、默认进入「内容浏览」、切换后浏览筛选状态会保留（组件未卸载）；
- 未说明「信息检索」只做**跨站跳转**：不站内搜索、不调 API，需要浏览器允许新标签页；
- 未说明 13 个外链平台（Reddit/X/YouTube/HN/GitHub/arXiv/Polymarket/TikTok/Amazon/LinkedIn/Pinterest/DuckDuckGo/Bluesky）可能触发登录墙或风控；
- 唯一"使用说明"是计划文档 Task 8 里的 `npm run dev` + 手工点击清单，普通读者不会去看。

#### 3.6.3 本地 checkout 与 origin/main 的差异（文档视角）

| 项 | 本地 HEAD `22544ca` | `origin/main` `997cd99` |
|---|---|---|
| 09-03 spec / plan | ❌ 不存在 | ✅ 存在（156 + 738 行） |
| `Last30daysPage` / `SearchHero` / `SourcesGrid` / `PhilosophySection` / `last30days-sources.js` / `searchUtils.js` | ❌ 不存在 | ✅ 存在 |
| `App.jsx` | 单视图瀑布流 | 双 Tab（`currentView`） |
| README / AGENTS / CLAUDE / dev.md | 与 origin/main 逐字节相同 | 同左 |
| 线上部署 | — | `gh-pages` 由 `997cd99` 构建，已含该功能 |
| Git 关系 | 与 origin/main **无共同祖先**（`git merge-base` 为空；`ahead 75 / behind 85`） | — |

> 结论：审计"现状"必须同时覆盖两份代码树。在本地拉齐 `origin/main` 之前，本地文档描述的 App 结构与线上不一致；而新功能本身在两边都没有用户文档。

---

## 4. 整体层面的文档缺口

1. **没有运维 Runbook**：「每周更新内容」是本项目唯一的周期性操作，却没有一处文档按"命令 + 顺序 + 校验 + 回滚"写出来。
2. **没有"数据文件即产物"的说明**：`static-data.json/.js` 是提交进仓库的构建输入，不是构建输出；`static-data-<ts>.json` 快照被 gitignore 且已堆积 7 个（未清理）。
3. **没有数据契约**：`category` 的取值/默认值/过滤语义无文档；`created_time` 时区、`uid` 算法（`md5(url)`）、`content` 截断上限（100 000 字符）都只存在于代码里。
4. **没有验收标准**：`npm run lint` / `npm run build` 从未写进"提交前检查"清单（AGENTS L60 只写 build）。
5. **没有环境区分**：所有命令都假设"本机 + 已装 selenium/openai + 已配 .env"，没有说明哪些步骤需要网络与 API Key。
6. **没有故障排查**：`python main.py` 报 `ModuleNotFoundError` 是当前环境最常见的失败，文档无指引。

---

## 5. 顺带发现（非文档问题，供修复任务拆分）

> 详细证据见同目录 `data-pipeline.md`，此处只列与文档结论直接相关的部分。

| # | 发现 | 证据 |
|---|---|---|
| R-01 | 数据三源漂移：DB 192 行 / `static-data.js` 143 条 / `static-data.json` 111 条；89 行未发布，39 个 URL 是 DB 中不存在的"幽灵" | 集合差计算 |
| R-02 | 32 条条目（id 172–203）无 `created_time`，卡片日期为空 | 遍历 `static-data.js` |
| R-03 | 8 个重复 id（13–17、30–32 各 2 条），`WaterfallGrid` 用 `key={item.id}` → React key 冲突 | `WaterfallGrid.jsx:8` |
| R-04 | 仓库根目录有一个 0 字节 `web_content.db`：抓取脚本 `DB_PATH="web_content.db"` 是相对路径，从根目录运行会写错库 | `fetch_from_params.py:26`；`ls -la web_content.db` |
| R-05 | 本地 `main`（75 commits）与 `origin/main`（85 commits）**无共同祖先**（`git merge-base` 为空）；两边文件树只差 10 个文件（origin 多出 09-03 的「信息检索」功能：6 个源文件 + 2 份文档 + `.gitignore`/`App.jsx` 改动）。普通 push 预计被拒 | `git status -sb`、`git diff --stat HEAD origin/main` |
| R-06 | 线上站点资源 404：`gh-pages` 的 `index.html` 引用绝对路径 `/assets/...`，而项目页挂在 `/deepthink/` 下（`https://dllen.github.io/assets/index-1a0092fe.js` → 404，`.../deepthink/assets/...` → 200）。`vite.config.js` 没有设置 `base: '/deepthink/'` | curl 实测两个 URL |
| R-07 | `index.html` 引用 `/vite.svg`，`public/` 下不存在 → favicon 404 | `ls public/` |
| R-08 | `src/assets/` 有 7 个 `static-data-<ts>.json` 快照（被 gitignore），可清理 | `git status --ignored` |
| R-09 | 「信息检索」Tab 无路由：`currentView` 只是内存状态，URL 恒为 `/`，无法分享/深链到该视图 | `App.jsx:24,121–151`（origin/main） |

---

## 6. 建议修复顺序

### P0（先做，防止下一次操作毁数据）
1. **在 CLAUDE.md 与 AGENTS.md 的重生成命令处加醒目警告**：修复前禁止 `npm run gen:static-js` / `:from-json`。
2. **修生成器**：`generate-data.js` 的合并基线改为 `static-data.js`（或先把 json 从 js 无损重建）；`SELECT` 增加 `category`、`uid`、`content`。
3. **`category` 落库**：`ALTER TABLE content_summary ADD COLUMN category TEXT` + 按 `original_url` 从 js 回填 143 条；新条目默认 `文章`。
4. 完成 1–3 后，在文档中给出 §2.5 的唯一标准流程。

### P1（本周内）
5. 重写 `README.md`：数据来源改为"构建期静态 bundle"；补分类/搜索/报告/源头栏目；补 Node ≥ 20、lint、gen 命令；补线上 URL；补「内容浏览 / 信息检索」双视图及"仅跨站跳转、不站内搜索"的说明（该功能在 origin/main）。
6. 修 `AGENTS.md`：目录结构（含 `Last30daysPage` 等 6 个 origin/main 源文件）、schema（加 `uid`/`content`）、命令表、`gen:static-js` 描述、测试命令的环境前置条件。
7. 修 `CLAUDE.md`：D-16 / D-18 / D-19 三处事实错误；补三个写库脚本；加"重生成会丢分类"的 Gotcha；在架构段补双视图与 `last30days-sources.js` 数据契约。
8. 对齐 09-03 设计文档与实现：修正 O-01（arXiv 参数）与 O-02（URL 预览不存在的交互），或把该 spec 标注为"设计稿，实现有偏差"；O-06 的 `query` 状态缺陷属代码问题，修复前不要在文档里承诺"卡片按关键词搜索"。
9. 重写或删除 `dev.md`：加密流程标记为"遗留/不参与 CI"；明文 DB 是 tracked 的说明与安全审计结论对齐（见 `security-privacy.md` H-1）。
10. 新增 `docs/RUNBOOK-weekly-content.md`（或扩写 CLAUDE.md 的 Commands + Runbook 段），内容即 §2.1/2.3/2.5。

### P2
11. 更新 `python_scripts/README.md`（三个现行脚本、Ollama 端点不一致）。
12. 清理 7 个快照、根目录 0 字节 DB；补 `public/vite.svg` 或改 favicon。
13. 修部署 `base` 路径并加"部署后自检 URL"步骤（R-06）；为双视图加路由/深链并写入文档（R-09）。
14. 给 `docs/superpowers/` 建一个索引（specs / plans / audits / runbooks 各是什么），避免新文档继续"只存在于分支上"。

---

## 7. 未验证事项（明确声明）

- 未执行任何抓取（`fetch_from_params.py` / `crawler_subpages.py` / `backfill_content.py`），未联网访问抓取目标。
- 未执行 `npm run gen:static-js` 及其 `:from-json` 变体（会覆盖 tracked 数据文件）；§2.4 的结论来自**只读推演**（同一 SQL + 同一合并函数，在 `/tmp` 内运行、不写仓库）。
- 未执行 `./scripts/encrypt-db.sh`（会覆盖 tracked 的 `web_content.db.enc`）；未解密任何副本。
- 未执行 `git push` / `git fetch`，未改变分支或远端状态；R-05 的"push 会被拒"是基于"无共同祖先"的推断，非实测。
- 未 checkout / reset 到 `origin/main`；§3.6 与 R-05/R-09 的 origin/main 结论全部通过 `git show origin/main:<path>` 只读获得。
- 未在浏览器中实测「信息检索」Tab 切换与卡片点击；O-06（卡片恒空查询）是代码推断，R-06（线上白屏）是资源 404 推断。
- 线上 bundle 只用字符串匹配确认包含该功能（`跨源搜索`/`信息检索`/`内容浏览`），未执行其 JS，也未截图。
- 未重新执行 `npm install`（`node_modules/` 为既有状态）。
- `npm run dev` 仅验证进程启动与 `curl` 返回 200，未在浏览器中检查渲染。
- 线上站点"白屏"是从资源 404 推断（R-06），未在真实浏览器中截图确认。
- "用户实际每周操作习惯"只能从提交历史重建（路径 A/B），未经用户确认。
- 文档中"浏览器兼容性"列表（Chrome 60+ 等）未实测。

---

## 8. 复现命令（本次审计实际执行）

```bash
# 文档与结构
ls src/components src/utils; cat package.json vite.config.js index.html
grep -n "sqliteReader\|模拟数据\|顶部导航" README.md AGENTS.md CLAUDE.md dev.md

# 数据与 schema（只读）
sqlite3 python_scripts/web_content.db ".schema content_summary"
sqlite3 python_scripts/web_content.db "SELECT count(*) FROM content_summary;"
node --input-type=module -e "import d from './src/assets/static-data.js'; console.log(d.length)"
node --input-type=module -e "import d from './src/assets/static-data.json' with {type:'json'}; console.log(d.length)"

# 重生成行为推演（不写仓库）
node --input-type=module -e "<同 generate-data.js 的 SQL + mergeIncremental，见 §2.4>"

# 命令验证
npm run lint
npm run build
npm run dev            # 后台启动后 curl localhost:5173，随即关闭
cd python_scripts && python3 -m pytest test_modular.py -q
cd python_scripts && python3 -m pytest test_*.py -q      # 预期失败：缺 selenium
cd python_scripts && python3 main.py                     # 预期失败：缺 selenium

# 线上/部署（只读）
curl -s -o /dev/null -w '%{http_code}\n' https://dllen.github.io/assets/index-1a0092fe.js
curl -s -o /dev/null -w '%{http_code}\n' https://dllen.github.io/deepthink/assets/index-1a0092fe.js
git merge-base HEAD origin/main; git status -sb; git log -1 --format=%h origin/gh-pages

# origin/main 只读对照（不 checkout）
git show origin/main:docs/superpowers/specs/2026-09-03-last30days-search-page-design.md
git show origin/main:docs/superpowers/plans/2026-09-03-last30days-search-page-implementation-plan.md
git show origin/main:src/App.jsx | grep -n "currentView\|Last30daysPage"
git show origin/main:src/assets/last30days-sources.js | grep -c "id: '"
git show origin/main:src/components/SourcesGrid.jsx
curl -s -o /tmp/deployed.js https://dllen.github.io/deepthink/assets/index-1a0092fe.js
grep -c "跨源搜索\|信息检索\|内容浏览" /tmp/deployed.js
```
