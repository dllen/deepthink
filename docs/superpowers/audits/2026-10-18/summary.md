# 观念棱镜（deepthink）第二轮全面体检 · 汇总

- **日期**：2026-10-18
- **基线**：`origin/main` `997cd99`（2026-09-03）。体检开始时本地 `main` 为 `22544ca`，与远端无共同祖先；已按用户决定备份到 `backup/local-main-2026-10-18` 并把 `main` 同步到 `origin/main`。7 份分项报告在基线切换前后完成，涉及版本差异处均已标注。
- **方式**：7 路只读并行审计（前端 / Python 后端 / 数据链路 / 构建部署 / 测试门禁 / 安全隐私 / 文档）+ Lead 复核。未修改产品代码、未安装依赖、未跑写库脚本。
- **原始报告**：本目录下 `frontend.md`、`python-backend.md`、`data-pipeline.md`、`build-deploy-repo.md`、`testing-quality.md`、`security-privacy.md`、`docs-accuracy.md`；前端证据截图在 `assets/frontend/`。

## 0. 一句话结论

线上站点可用，但这套系统目前**不可复现**：站点数据与数据库已经分叉、生成器再跑一次会静默清空分类并丢内容、公开仓库里的"加密数据库"实际是明文全量数据、CI 绿色证明不了生产正确，另有一组已实测的线上功能缺陷。

## 1. 硬事实（实测值）

| 项目 | 实测 | 判定 |
|---|---|---|
| DB `content_summary` | **192 行**，最新 `created_time` **2026-08-28 13:22:58**（51 天未更新），190 行含全文（约 109 万字符） | 权威源 |
| 线上数据 `static-data.js` | **143 行** / 142 唯一 URL，全部带 `category`，内容截止 **2026-07-30**，32 行无 `created_time`，8 组重复 id（13–17、30–32） | 实际发布物 |
| 本地 `static-data.json` | **111 行**，无 `category`，截止 2026-07-30 | 已分叉的旧中间产物 |
| DB 有、站点无 | **89 行**（2026-08-06 2 行 + 08-28 87 行） | 内容没上线 |
| 站点有、DB 无 | **39 个 URL / 40 行**（32 行手工导入无来源、8 行 DB 已删） | 幽灵数据，会永久累积 |
| `category` 覆盖 | js 143/143；DB 0/192；json 0/111；`generate-data.js` 的 SELECT 不输出该字段 | **不可复现** |
| 仓库可见性 | `github.com/dllen/deepthink` 匿名 HTTP 200（公开） | 暴露面 |
| 数据库跟踪 | 明文 `web_content.db` 2.68MB 与 `web_content.db.enc` 1.42MB 同时被 git 跟踪（占跟踪体积 91%） | 加密失效 |
| 加密副本 | `.enc` 停留在 2026-07-31，仅 103 行（当前明文 192 行） | 过期且无完整性校验 |
| 部署 | GitHub Actions 31/31 成功，中位 22s，push→线上约 49s；最近部署 2026-09-03 | 流水线绿 |
| 生产入口 | `https://deepthink.global/` 200（Cloudflare 代理，仓库内无该层配置）；未知路径一律 `200 + index.html`；`/vite.svg` 返回 HTML | 监控盲区 |
| Pages 项目地址 | `https://dllen.github.io/deepthink/` 返回 200 但 `/assets/*` 404 → **白屏** | 损坏别名 |
| 构建 / Lint（线上基线） | `npm run build` 通过，产物约 310KB / gzip 106KB；`npm run lint` **3 errors** | 线上代码 lint 不通过 |
| Python | 27 文件 / 3,289 行；9 处 `CREATE TABLE` 分散在 6 个文件；全项目 0 处 logging；包顶层 eager import selenium | 结构与可测性 |
| 测试 | 前端 0 测试；CI 无 lint/test；`pytest test_*.py` 因缺 selenium 收集失败；`test_modular.py` 5 个"通过"实为 `return True`，无断言 | 假绿 |

## 2. 分级发现

### P0 — 会造成数据丢失、安全暴露或线上功能错误

**P0-1 数据真源分裂，生成器会静默毁数据**
`scripts/generate-data.js` 以 `static-data.json` 为合并底、从 DB 取数，但两者都没有 `category`，且 `mergeIncremental` 只增不改。实测在当前状态跑一次 `npm run gen:static-js` 会产出约 200 条、`category` 0 条，并丢掉 32 条只存在于 `static-data.js` 的手工内容，全程无报错。同时 DB 的 89 条新内容从未上线。
证据：`scripts/generate-data.js:91-104,120-162`；`static-data.js` / `static-data.json` / DB 三方对比（`data-pipeline.md` §1、`testing-quality.md` D-01/02/03）。

**P0-2 公开仓库里的明文全量数据库，加密控制实际不生效**
仓库公开，明文 DB 与 `.enc` 同时被跟踪，190 行全文已随历史公开；`.enc` 只有 103 行且过期，`dev.md` 声称"明文被 git 忽略、CI 会解密"与事实相反。加密脚本用 `openssl -k`（密钥进 argv）、CBC 无完整性校验。
证据：`security-privacy.md` H-1/H-2/M-2；`dev.md:5,31`；`scripts/encrypt-db.sh:17`。

**P0-3 线上已实测的功能缺陷（Chrome CDP，1440×900 与 375×812）**
- 「信息检索」页 13 个平台卡片永远打开空搜索：`Last30daysPage` 的 `query` 状态从未被赋值（`setQuery` 未使用，lint 报错），搜索状态只存在于 `SearchHero` 内部。`Last30daysPage.jsx:7,26`、`SourcesGrid.jsx:28-30`。
- 重复 id 导致搜索错乱：Fuse 命中按 `id` 过滤 + `key={item.id}`，实测搜「英伟达财报」计数 5 但显示 13、搜「AI」29→38；dev 控制台 8 条 duplicate-key 警告。`App.jsx:62-65`、`WaterfallGrid.jsx:7`。
- 空态「清除所有筛选」只清标签，不清分类和搜索。`App.jsx:93-95,211-216`。
- 报告弹窗 `iframe sandbox=""` 阻断报告页脚本，图表区空白（直开报告页正常）。`ReportModal.jsx:79`。
- 两个筛选条同为 `sticky top-24`，滚动时重叠 83px；移动端吸附筛选占视口约 62%。`App.jsx:170,179`。
- 32 条无 `created_time` 的卡片日期显示为空。
- 「信息检索」页 Enter 不触发搜索（`SearchHero` 没有 `<form>`）；arXiv 链接参数错误（`?search_query` 实测不执行搜索，应为 `searchtype=all&query=`）；外链 `window.open` 缺 `noopener/noreferrer`。
- 线上代码 lint 3 errors。证据：`frontend.md` FE-P0-1…P1-6。

### P1 — 可靠性与可维护性风险

**P1-1 部署链路不可验证且依赖仓库外的一层**
PR 也会触发部署步骤；无 `permissions:` / `concurrency` / `timeout`；无 lockfile（`npm install --legacy-peer-deps`，CI Node20 vs 本地 Node22）；无部署后冒烟；线上产物 318,698B 与干净构建 310,041B 相差 2.8%，不可字节复现；生产 404 伪装成 200，只看状态码的监控会漏掉资源缺失；`deepthink.global` 的 Cloudflare 重写不在仓库内，不可 code review、不可重建；GitHub Pages 项目地址白屏。
证据：`build-deploy-repo.md` BD 系列、`deploy.yml`。

**P1-2 Python 包边界与可测试性**
`web_content_system/__init__.py` 顶层 eager import 链拉到 selenium，导致连 `database`/`config` 都无法导入；9 处 `CREATE TABLE` 各自定义 schema（含 `uid`/`content` 列不一致）；`DatabaseManager` 初始化在旧库上会 `IntegrityError` 或静默清行；无 logging / retry / WAL；两个 legacy 抽取器 893 行无调用方；根目录与 `python_scripts/` 两份 requirements 已漂移。
证据：`python-backend.md` F1–F12。

**P1-3 前端可维护性与性能**
双视图和筛选状态不进 URL（刷新/分享/后退都丢）；切换视图保留滚动位置但丢失搜索输入；移动端页头被挤成两行（header 97px）；`items`/`filteredData`/`tags` 用 `useState + useEffect` 派生，多一轮渲染；143 条数据整包进主 chunk，随内容线性增长；组件未做 memo；a11y 对比度 7 个激活 pill 低于 4.5:1（最低 2.15）；Tab 按钮无 `role/aria-selected`。
证据：`frontend.md`；`App.jsx:26-81`。

**P1-4 质量门禁缺失**
前端 0 测试、CI 不跑 lint/test/数据校验、pytest 假绿、无筛选基线固化（`baseline-filter-expected.json` 已生成可作起点）。
证据：`testing-quality.md` §0/§9。

### P2 — 卫生与文档

- **P2-1 文档**：README/dev.md 描述的是 2026-07 之前的设计（仍写浏览器 sql.js 读库、明文被忽略、CI 解密），AGENTS.md 目录结构与 schema 过时，CLAUDE.md 有两处硬错误；线上「信息检索」功能没有任何面向用户的说明。`docs-accuracy.md`。
- **P2-2 仓库卫生**：7 个 `static-data-<ts>.json` 快照 576KB、`static/` 与 `public/` 重复 45KB 看板、根目录 0 字节 `web_content.db`、`browserslist` 数据 10 个月未更新。
- **P2-3 Python 收敛**：legacy 893 行归档、crawler 系列合并、统一入口。
- **P2-4 测试补齐**：Vitest 单测（筛选/搜索/URL 构造）+ 数据完整性检查脚本 + CI 门禁。

## 3. 建议的子项目拆分与顺序

| 顺序 | 子项目 | 覆盖 | 依赖 |
|---|---|---|---|
| S1 | **数据真源与生成器重建** | P0-1 | 需先决定 32 条手工内容去留、`category` 赋值方式 |
| S2 | **线上功能修复** | P0-3 | 需先决定生产入口（自定义域 vs Pages）以正确设置 `base` |
| S3 | **安全与仓库治理** | P0-2、供应链 | 需先决定明文 DB 历史处理方式 |
| S4 | **CI / 部署可靠性** | P1-1 | 需要 GitHub/Cloudflare 的配置记录或凭证 |
| S5 | **Python 结构与质量底座** | P1-2、P1-4、P2 | 可与 S1 合并设计 |

推荐先做 **S1**：它是所有内容更新的前提，且当前状态下任何一次"正常刷新数据"都会造成不可逆的数据丢失。S2 体量小、用户可见，可紧随其后或并行。

## 4. 需要拍板的决策

1. **生产入口**：以 `deepthink.global` 为准，还是回归 GitHub Pages？Cloudflare 那层有配置记录吗？这决定 `base` 修复方向，也决定"白屏"算不算线上故障。
2. **明文数据库**：从跟踪中移除即可（历史仍公开），还是重写历史 + force push 彻底清除，还是接受公开？
3. **32 条手工内容**：补录进 DB（保留）还是从站点移除？
4. **分类来源**：`category` 今后由人工标注、规则映射还是 LLM 赋值？决定它如何落库。
5. **本轮范围**：只做 P0，还是 P0 + P1，还是一次做完全部。

## 5. 本次体检的边界

- 所有结论基于 2026-10-18 的代码与线上状态；未做性能基准（Lighthouse/INP）、未做真机/微信内验证、未做 E2E。
- 未执行任何写操作（抓取、生成、加密、清理、部署），未安装依赖，未读取 `.env` 值。
- 历史提交中的明文 DB 无法通过后续删除消除；彻底清除需要重写历史并协调所有克隆。
