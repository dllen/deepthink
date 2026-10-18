# 测试与质量门禁审计

- **日期**：2026-10-18
- **审计者**：Sentinel（QA Engineer）
- **审计对象**：`deepthink` @ `main` / `22544ca`（工作区干净，无未提交改动）
- **审计性质**：**只读**。未改产品代码、未装依赖、未跑 build、未提交。
- **审计范围**：测试资产、可执行门禁、数据完整性、回归证明能力、发布就绪度。
- **配套产物**：`docs/superpowers/audits/2026-10-18/baseline-filter-expected.json`（当前 HEAD 的 144 组筛选期望结果基线）
- **同批审计**：`data-pipeline.md`（Pipeline，数据链路）、`security-privacy.md`（Aegis，安全隐私）；本报告与其结论一致，验收时三份需一起看

---

## 0. 结论摘要（TL;DR）

**站点现在是能跑的，但“这轮优化没改坏”目前无法被证明。**

三条要点：

1. **证据链缺失**：CI（`.github/workflows/deploy.yml`）只有 `npm install` + `npm run build` + 发布，没有任何测试、lint、数据校验、a11y 或性能门禁；前端 0 个测试（无 vitest/jest/playwright/axe 依赖，`package.json` 无 `test` 脚本）。
2. **后端测试事实上失效**：`python -m pytest test_*.py` → **exit 2，collection error**（缺 `selenium`）；单独跑 `test_modular.py` → “5 passed”，但 5 条全是 `PytestReturnNotNoneWarning`，**没有任何断言生效**（返回 `False` 也判 passed）。这是“假绿”。
3. **数据管道存在会“静默改坏功能”的缺陷**：`static-data.json`（111 条、无 `category`）与 `static-data.js`（143 条、有 `category`）已经分叉；`scripts/generate-data.js` 的 SELECT **不读 category**（DB 也无该列），且合并逻辑**只增不改**。任何人按文档跑一次 `npm run gen:static-js`，都会把七分类功能整体清空，且不会有任何报错。

**发布建议**：

| 判定对象 | 结论 |
|---|---|
| 本轮“整体优化”的验收 | **FAIL**（阻断）。不是站点坏了，而是“无证据可证明没改坏”，且数据管道有 P0 级静默破坏风险 |
| 当前仓库作为“优化前基线” | **CONDITIONAL PASS**（附 5 个前置条件，见 §9.2） |

---

## 1. 审计范围与方法

### 1.1 范围内

- 测试资产盘点（`python_scripts/test_*.py`、CI、`package.json` scripts、依赖）。
- 实际执行所有**只读/可重复**的检查：ESLint、pytest（两种调用方式）、静态数据一致性分析、构建产物体积统计。
- 需求 → 测试矩阵、P0/P1/P2 分阶段测试策略、缺陷报告、回归风险、发布建议。

### 1.2 范围外（本次不做）

- 不执行 `npm run build`、`npm run dev`（按任务要求）。
- 不安装 selenium / vitest / playwright / axe。
- 不修改任何产品代码、CI 配置、依赖或数据文件。
- 不访问网络（不验证外链可达性）、不使用任何密钥（`.env` 存在但未读取）。
- 不运行会写入数据库的代码路径（`test_system.py` 就属于这类，见 D-09）。

### 1.3 假设（必须显式声明）

- 任务板 `task-5` 在审计开始时**不存在**（`team_task_get` → not found，`team_task_list` → 空），因此未取得原始任务描述。本报告范围依据：Atlas 的任务消息 + 仓库当前状态（`docs/superpowers/specs/2026-07-30-deepthink-website-audit.md` 的 A–F 六块已落地 + 2026-08/09 的七分类与信息源功能）。
- “本轮整体优化”的具体改动集合在审计时**尚未落盘**（工作区干净、无新计划文档），因此测试矩阵按**仓库现有风险面**编写，可直接套用于任何一个后续改动集；若优化范围明确后需增删用例，只需在 §4 矩阵上裁剪。

### 1.4 实际执行的命令与耗时

| # | 命令 | 退出码 | 结果 | 耗时 |
|---|---|---|---|---|
| 1 | `git status --porcelain --untracked-files=all` | 0 | 干净 | <1s |
| 2 | `npm run lint` | **0** | 0 error / 0 warning | ~4s |
| 3 | `cd python_scripts && python -m pytest test_*.py -q` | **2** | collection error（selenium 缺失） | 0.15s |
| 4 | `cd python_scripts && python -m pytest test_modular.py -q` | **0** | 5 passed, 5 warnings（无断言） | 0.05s |
| 5 | `python -m pytest test_system.py -q` | **2** | ImportError: No module named 'selenium' | 0.10s |
| 6 | 静态数据一致性脚本（Node，只读） | 0 | 见 §2.3 | ~3s |
| 7 | DB↔发布数据比对（Python sqlite3，只读） | 0 | 见 §2.3 | ~1s |
| 8 | 筛选基线生成（Node + Fuse，只读） | 0 | 144 组用例已冻结 | ~5s |
| 9 | 产物体积统计（`wc -c` / `gzip -c`） | 0 | JS 297,388 B / gzip 103,892 B | <1s |

> 说明：`dist/` 存在今日 22:45 的构建产物，但**不是本次审计执行产生的**，因此不能作为“构建通过”的证据（见 §7 阻塞项 B-4）。

---

## 2. 现状基线（证据）

### 2.1 测试资产盘点

| 资产 | 位置 | 类型 | 能否进 CI | 现状 |
|---|---|---|---|---|
| 后端脚本式测试 | `python_scripts/test_modular.py`（238 行） | 打印 + 返回 bool | ❌ | pytest 下 0 断言，假绿 |
| 后端集成测试 | `python_scripts/test_system.py`（139 行） | 真跑抓取/DB 写入 | ❌ | import 即失败；可运行时会污染生产 DB |
| 前端单测 | — | — | — | **不存在** |
| 前端 E2E | — | — | — | **不存在** |
| a11y 自动扫描 | — | — | — | **不存在** |
| 视觉回归 | — | — | — | **不存在** |
| 性能预算 | — | — | — | **不存在** |
| 数据不变量校验 | — | — | — | **不存在** |
| CI 测试 job | `.github/workflows/deploy.yml` | — | — | **不存在** |
| CI lint | 同上 | — | — | **不存在** |

`package.json` 的 scripts：`dev / build / preview / lint / gen:static-js / gen:static-js:from-json` —— 没有 `test`。
`node_modules`（280 个包）中不存在 vitest / jest / playwright / puppeteer / cypress / axe-core / jsdom。

### 2.2 后端测试实际输出

```
$ cd python_scripts && python -m pytest test_*.py -q
...
E   ModuleNotFoundError: No module named 'selenium'
=========================== short test summary info ============================
ERROR test_system.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.15s
```

```
$ cd python_scripts && python -m pytest test_modular.py -q
test_modular.py::test_database
  PytestReturnNotNoneWarning: Test functions should return None, but
  test_modular.py::test_database returned <class 'bool'>.
  ...（同样的 warning 共 5 条）
5 passed, 5 warnings in 0.05s
```

**结论**：pytest 把 5 个“打印 + return bool”的函数当作测试，**返回值被丢弃**，因此业务失败也会显示 passed；唯一的失败方式是抛异常。`test_system.py` 因为顶层 `from web_content_system import WebContentExtractor` 链到 `selenium`，在任何测试执行前就中断了整个会话（`--exitfirst` 未用，collection error 会中断全集）。

### 2.3 数据一致性实测（核心证据）

用只读脚本对 `src/assets/static-data.js`、`src/assets/static-data.json`、`python_scripts/web_content.db` 三方交叉比对：

| 指标 | `static-data.js`（实际发布） | `static-data.json`（文档称 canonical） | `web_content.db`（源头） |
|---|---|---|---|
| 条目数 | **143** | **111** | **192** |
| 唯一 id | 135（**8 组 id 冲突**） | 103（8 组冲突） | 192（主键唯一） |
| 唯一 `original_url` | 142 | 111 | 192 |
| `category` 字段 | 有（143/143） | **无（0/111）** | **无此列** |
| `created_time` | **32 条缺失** | 0 缺失 | 0 缺失 |
| 排序（降序） | **否** | 是 | 按 id 递增 |
| 分类分布 | 文章 119 / 工具 10 / 言论 5 / 科技动态 3 / 资源 3 / 图片 2 / 文摘 1 | — | — |

DB 与发布数据的漂移：

- **89** 个 DB 中的 URL 未出现在线上数据里（DB 最新到 `2026-08-28 13:22:58`，id 486）。
- **39** 个线上数据的 URL 在 DB 中不存在。
- 也就是说：**“线上内容 = DB 内容的派生”这个基本事实当前不成立**，而且 CI 不重新生成数据（`deploy.yml` 注释说明是故意的）。

关键字段能力对比：

```
generate-data.js 的 SELECT：id, title, created_time, summary, original_url, tags
                                   ↑ 没有 category
DB content_summary 列：id, title, created_time, summary, original_url, tags, uid, content
                                   ↑ 没有 category（分类只存在于生成的 static-data.js 里）
```

因此：**`category` 的唯一真源是一个生成产物文件，任何再生成都会把它抹掉。**

### 2.4 构建 / 部署 / 门禁现状

- `.github/workflows/deploy.yml`：`checkout → setup-node@20 → npm install --legacy-peer-deps → npm run build → gh-pages`。
- 没有 `npm run lint`，没有测试，没有数据校验，没有产物体积检查。
- 触发条件 `push: main` 与 `pull_request: main` —— 也就是说 **PR 合并前 CI 只会“能 build 就算过”**。
- 本地 `npm run lint` 通过（exit 0），但 CI 不拦，等于没有约束力。

### 2.5 基线指纹（供后续差分使用）

| 文件 | SHA-256 | 字节 |
|---|---|---|
| `src/assets/static-data.js` | `9257b5f8d8d9e3b3a1409de8bd605944faf744c9606c81c21a259c3c171fe187` | 114,102 |
| `src/assets/static-data.json` | `11ac04b4fff8d49c1e788b58e5791758c13e4aa959fe152122c660d6d59e7415` | — |
| `python_scripts/web_content.db` | `bc545ebe20c81a43d455402ee46efdd8dd056cb109bc4e013464f7f1df35d892` | 2,682,880 |
| `baseline-filter-expected.json` | `80f5d7a7cbe0877220248c3d0d4136b70fa57a927d89a663262e5c56bc7f8044` | 33,166 |
| `dist/assets/index-4b9e4ec2.js`（非本次构建） | — | 297,388（gzip 103,892） |
| `dist/assets/index-105696ad.css`（非本次构建） | — | 29,671（gzip 5,749） |

---

## 3. 核心问题：优化做完后，怎么证明“没改坏”？

### 3.1 直接回答

“没改坏”不是一句结论，而是**五条可复核的证据**：

| 证据 | 内容 | 本仓库现状 | 缺了会怎样 |
|---|---|---|---|
| **E1 基线冻结** | 改动前冻结行为快照：数据指纹 + 筛选期望结果 + 页面 DOM/截图 + 产物体积 | ❌ 今天才第一次生成（部分） | 没有“改前”，就无法谈“改坏” |
| **E2 不变量** | 永远必须成立的断言（数据 schema/唯一性/排序/category 合法/链接完整…） | ❌ 无 | 缺陷会静默进入发布产物 |
| **E3 差分** | 改后重跑同一组输入，逐项与 E1 比较；差异必须为空或出现在 PR allowlist | ❌ 无 | 只能靠人眼看，漏检必然发生 |
| **E4 行为矩阵** | 真实浏览器跑通 22 个用户旅程用例（TC-001～018、024～027） | ❌ 无 | 交互/响应式/a11y 回归无法发现 |
| **E5 证据产物** | 每次合并/发布附上日志、截图、体积、耗时，可追溯 | ❌ 无 | “证明”变成口头承诺 |

**一句话**：证明 = “冻结基线 → 不变量常绿 → 差分可解释 → E2E 全通过 → 证据留档”。当前这五项全部缺失，所以本轮优化**无法证明没改坏**（D-11）。

本审计已经完成 E1 的数据部分：`baseline-filter-expected.json` 记录了当前 143 条数据下 **144 组“分类 × 标签 × 搜索”组合的期望 id 列表**（语义严格复刻 `App.jsx::filterData`）。优化后重跑同一脚本，任一用例的 id 集合发生变化，就必须解释。

### 3.2 P0 门禁（每次提交 / PR 必绿，≤5 分钟，阻断合并）

| ID | 证明什么 | 命令 / 方式 | 通过标准 | 失败动作 | 证据产物 |
|---|---|---|---|---|---|
| **P0-1** | 静态检查无回归 | `npm run lint` | exit 0，0 error | 阻断合并 | lint 日志 |
| **P0-2** | **数据不变量**（12 项，见 §6.2） | `node scripts/check-data-integrity.mjs`（待建，只读） | 12/12 通过 | 阻断合并 | `data-integrity.json` |
| **P0-3** | 数据未被“静默重置” | 与 E1 指纹比对 + 条目集合差分 | 删除条目数 = 0，或全部在 PR allowlist；新增条目必须带 `category` | 阻断合并 | 差分报告 |
| **P0-4** | 筛选逻辑无回归 | `vitest run`（待建；纯函数 `filterData`/`getCategoryCounts`/`formatDate`） | 全部通过（≥18 用例，见 §6.3） | 阻断合并 | vitest 报告 |
| **P0-5** | 构建可用 | `npm run build` | exit 0 | 阻断合并 | 构建日志 |
| **P0-6** | 产物体积未失控 | 对比 `dist/assets/*.js|c ss` gzip 体积 | JS gzip ≤ 基线 +10%（≤114.3 KB）；CSS gzip ≤ 基线 +10%（≤6.3 KB） | 需 QA + 架构师批准 | bundle 统计 |
| **P0-7** | 产品主路径可用 | 3 分钟手工/脚本冒烟（§4.1 的 TC-001～TC-008） | 首屏 143 条、分类计数正确、搜索有结果、标签可切换、空态正常、弹窗可开关、移动端 1 列 | 阻断合并 | 截图 |

**P0 的判定原则**：任何一项红 → 不允许进入 main。P0 不做“warning 放行”。

### 3.3 P1 门禁（每个 PR / 每次发布前，≤30 分钟；或每晚定时）

| ID | 证明什么 | 命令 / 方式 | 通过标准 |
|---|---|---|---|
| **P1-1** | 真实浏览器行为无回归 | Playwright E2E，22 条浏览器用例（TC-001～018、024～027），Chromium | 22/22 通过；0 console error |
| **P1-2** | 无障碍不回退 | `@axe-core/playwright` 扫描首页 + 弹窗 | 0 critical / 0 serious；已知 C2 masonry 顺序问题记入 allowlist |
| **P1-3** | 数据再生成不破坏数据 | 临时目录跑 `gen:static-js`（拷贝 DB + json），对比输出 | 条目集合、`category` 保留率 100%、排序、id 唯一性均符合预期（**当前必失败，见 D-02/D-03**） |
| **P1-4** | 筛选组合无回归 | 重跑 `baseline-filter-expected.json` 的 144 组用例 | id 集合差异为空（或 allowlist） |
| **P1-5** | 后端逻辑可验证 | 重构后的 `pytest`（真断言 + `tmp_path` + marker） | 单元/契约测试全绿；**任何用例不写仓库内 DB** |
| **P1-6** | 外链可用 | 抽样 20 条 URL 做 HEAD/GET（限速） | ≥95% 2xx/3xx；404 登记到 issue |
| **P1-7** | 跨浏览器 | Chromium + WebKit 冒烟（TC-001～TC-008） | 全部通过 |
| **P1-8** | 视觉无意外变化 | Playwright 截图对比（首页 + 弹窗，桌面/移动） | 像素差异 < 0.1%（或人工确认） |

### 3.4 P2 门禁（里程碑 / 每季度 / 数据规模变化时）

| ID | 证明什么 | 方式 | 目标 |
|---|---|---|---|
| **P2-1** | 性能预算 | Lighthouse mobile（4G 模拟） | LCP < 2.5 s，CLS < 0.1，TBT < 300 ms，性能分 ≥ 90 |
| **P2-2** | 规模上限 | 生成 1,000 / 5,000 条测试数据跑首屏 + 搜索 | 首屏 < 2 s、输入延迟 < 100 ms；否则触发虚拟化（F3） |
| **P2-3** | 端到端管道 | mock 抓取 → DB → generate-data → build → preview | 全链路可复现，无人工步骤 |
| **P2-4** | 加密链路 | 用测试密钥执行 `scripts/encrypt-db.sh` + 解密读取 | 可加密、可解密、CI secret 配置可演练 |
| **P2-5** | 依赖安全 | `npm audit --omit=dev`、`pip-audit` | 0 high/critical（或已登记豁免） |
| **P2-6** | 搜索质量 | 针对 20 个真实查询人工标注预期结果 | Top-5 命中率 ≥ 80%（当前 threshold 0.35 无任何评测） |

### 3.5 变更类型 → 必跑门禁映射

| 改动位置 | 必跑 | 附加动作 |
|---|---|---|
| `docs/**`、`*.md` | P0-1 | — |
| `src/components/**`、`src/utils/**` | P0 全部 + P1-1/2/8 | 若动 `filterData`：P0-4 + P1-4 |
| `src/assets/static-data.{js,json}` | P0-1/2/3/5/6 + P1-3/4 | 附数据差分报告；对照 E1 基线 |
| `scripts/generate-data.js` | P0-2/3 + P1-3/4 | 必须在临时目录跑，禁止直接覆盖产物 |
| `python_scripts/**` | P1-5 + P2-3 | 禁用生产 DB |
| `package.json` / `vite.config.js` / 依赖 | P0-1/5/6 | 附 bundle 前后对比 |
| `index.html` / `public/**` | P0-1 + P1-1/2/6 | 链接完整性 |
| `.github/**` | 在分支上 dry-run | 至少跑一次完整 CI |

### 3.6 基线与差分流程（可执行步骤）

1. **改动前（今天）**：冻结基线 —— 已完成数据部分；待补 DOM 截图与 bundle 统计（需允许跑 dev/build）。
2. **PR 提交时**：CI 跑 P0，把 `data-integrity.json`、`bundle-stats.json`、`vitest.json` 作为 artifact。
3. **合并前**：重跑 P1-4（144 组筛选），把 diff 写进 PR 描述；空 diff 才可合并。
4. **发布前**：P1-1/2/8 + P0 全绿；QA 在发布记录里签名。
5. **发布后**：对比线上 `index.html` 的 asset hash 与 `dist/` 一致，抽查 3 个用户旅程。
6. **基线更新**：只有**经批准的预期变更**才能更新基线；更新必须单独提交并附理由（防止“为了让测试变绿而改基线”）。

### 3.7 CI 落地设计（建议新增 `.github/workflows/ci.yml`）

```yaml
jobs:
  quality:            # P0，PR 必跑，< 5 min
    - npm install --legacy-peer-deps
    - npm run lint
    - node scripts/check-data-integrity.mjs
    - node scripts/diff-static-data.mjs --baseline <committed-baseline>
    - npx vitest run
    - npm run build
    - node scripts/check-bundle-budget.mjs
  e2e:                # P1，main 分支或 label: e2e
    - npx playwright install --with-deps chromium webkit
    - npx playwright test
  backend:            # P1
    - pip install -r python_scripts/requirements.txt
    - cd python_scripts && python -m pytest -q
```

> 注意：E2E 与 Python 依赖装在全量 CI 会拉长耗时，建议 `paths` 过滤 + 只在相关目录变更时触发。

---

## 4. 需求 → 测试矩阵

### 4.1 需求与覆盖现状

| ID | 需求（验收点） | 来源 | 当前自动覆盖 | 目标门禁 | 用例 |
|---|---|---|---|---|---|
| R1 | 首屏加载并渲染全部内容卡片（143 条） | 产品基本盘 | ❌ | P0-7 / P1-1 | TC-001 |
| R2 | 每条记录具备 id/title/summary/original_url/tags | 数据契约 | ❌ | P0-2 | TC-020 |
| R3 | id 唯一、URL 唯一 | 数据契约 | ❌（实测违反） | P0-2 | TC-021 |
| R4 | `created_time` 有效且按时间倒序 | 数据契约 | ❌（实测违反） | P0-2 | TC-022 |
| R5 | `category` ∈ 7 类；缺失回退“文章” | 7 分类功能 | ❌ | P0-2 / P0-4 | TC-023 |
| R6 | 分类为单选、互斥；计数 = 该分类条目数 | 7 分类功能 | ❌ | P0-4 | TC-010 |
| R7 | 标签多选为 OR 语义、可清除 | 标签筛选 | ❌ | P0-4 | TC-011 |
| R8 | 搜索覆盖 title+summary，中英文均可，命中高亮/结果正确 | 搜索功能 | ❌ | P0-4 / P1-4 | TC-012–015 |
| R9 | 分类 × 标签 × 搜索 组合为 AND 组合 | App.jsx | ❌ | P1-4 | TC-016 |
| R10 | 顶栏计数 `{filteredData.length} 条内容` 与卡片数一致 | UI 一致性 | ❌ | P1-1 | TC-017 |
| R11 | 卡片正确显示日期/分类徽章/标签/摘要排序 | 卡片 | ❌ | P1-1 | TC-002 |
| R12 | 宽度断点 1/2/3/4 列；长文本不溢出 | 瀑布流 | ❌ | P1-1/8 | TC-006 |
| R13 | 报告弹窗打开/关闭（X、遮罩、Esc）；iframe sandbox 生效 | ReportsPanel | ❌ | P1-1/2 | TC-004 |
| R14 | 信息源面板 6 个外链可点、`target=_blank` + `rel=noopener` | LinksPanel | ❌ | P1-1 | TC-005 |
| R15 | 空态显示“没有找到匹配的内容”并可一键清除筛选 | 空态 | ❌ | P1-1 | TC-008 |
| R16 | a11y：`lang=zh-CN`、`aria-pressed`、搜索 `aria-label`、focus ring、`aria-posinset/setsize` | Area D | ❌ | P1-2 | TC-024–027 |
| R17 | `vite build` 成功；产物引用完整；无 console error；体积在预算内 | 构建 | 部分（CI 只跑 build） | P0-5/6 | TC-018 |
| R18 | DB → static-data 生成：保留 category、更新既有行、快照有保留策略 | 数据管道 | ❌（实测会破坏，见 D-02/03） | P1-3 | TC-028–030 |
| R19 | Python：模块可导入、DB CRUD、摘要回退、内容校验 | 后端 | 部分（假绿） | P1-5 | TC-031–034 |
| R20 | 安全：iframe 收紧、外链 rel、`.env` 不入库、DB 加密可解密 | 安全基线 | ❌ | P1-2 / P2-4 | TC-035 |
| R21 | 性能：LCP/CLS/TBT 达标；500 条规模不卡 | 性能 | ❌ | P2-1/2 | TC-036 |

覆盖统计：**21 项需求中，0 项被可靠的自动化门禁覆盖**，2 项被 CI 部分覆盖（构建），1 项有“假绿”测试。

### 4.2 关键用例明细（节选，共 36 条）

| 用例 | 前置 | 步骤 | 期望 | 级别 |
|---|---|---|---|---|
| TC-001 | 构建产物可服务 | 打开首页 | 143 张卡片；顶栏显示“143 条内容”；无 console error | P0-7 |
| TC-002 | 首页 | 检查首张卡片 | 标题/摘要/日期/分类徽章/标签/外链箭头齐全；日期非空 | P1-1 |
| TC-003 | 首页 | 点击卡片外链 | 新标签打开原文；`rel="noopener noreferrer"` | P1-1 |
| TC-004 | 首页 | 打开报告弹窗 → Esc → 点遮罩 | 均可关闭；iframe 无 script 执行能力 | P1-1/2 |
| TC-005 | 首页 | 滚动到信息源面板 | 6 个来源链接可点；新标签打开 | P1-1 |
| TC-006 | 首页 | 视口 375/768/1024/1280 | 分别为 1/2/3/4 列（`columns-1 md:2 lg:3 xl:4`）；无横向滚动 | P1-8 |
| TC-007 | 首页 | 输入“AI” | 结果数 > 0；每张卡片标题或摘要含 AI | P1-1 |
| TC-008 | 首页 | 搜索“zzzz不存在的词” | 空态出现；点“清除所有筛选”恢复 143 条 | P1-1 |
| TC-009 | 首页 | 输入“AI”再清空 | 恢复 143 条；输入框清空 | P1-1 |
| TC-010 | 首页 | 依次点 7 个分类 | 每类卡片全部属于该分类；计数 = 分类分布（119/10/5/3/3/2/1）；再次点击取消 | P0-4 |
| TC-011 | 首页 | 选标签 A、标签 B | 卡片满足 A 或 B（OR）；计数正确；可清除 | P0-4 |
| TC-012 | 首页 | 搜“英伟达财报” | 仅显示匹配卡片（**当前会多显示 1 张王川文章，见 D-05**） | P1-4 |
| TC-013 | 首页 | 搜“人工智能” | 结果非空且相关 | P1-4 |
| TC-014 | 首页 | 搜“AI” + 分类=工具 | 结果同时满足两个条件 | P1-4 |
| TC-015 | 首页 | 搜“ ”（空格） | 视为空查询，返回全部 | P0-4 |
| TC-016 | 首页 | 分类=工具 + 标签 + 搜索 三者叠加 | 交集正确、计数一致 | P1-4 |
| TC-017 | 首页 | 任意筛选后对比顶栏数字与卡片数 | 完全一致 | P1-1 |
| TC-018 | 构建 | `npm run build` 后检查 `dist/index.html` | 引用的 js/css 均存在；无 404 | P0-5 |
| TC-019 | 数据 | 对 `static-data.js` 求 sha256 | 与基线一致或差异已在 allowlist | P0-3 |
| TC-020 | 数据 | 校验必填字段 | 143/143 通过 | P0-2 |
| TC-021 | 数据 | 校验 id/url 唯一 | **当前失败**：8 组 id 冲突 | P0-2 |
| TC-022 | 数据 | 校验 created_time 与排序 | **当前失败**：32 条缺失、整体非降序 | P0-2 |
| TC-023 | 数据 | 校验 category | 143/143 ∈ 7 类；缺失回退“文章” | P0-2 |
| TC-024 | 首页 | 检查 `<html lang>` | `zh-CN` | P1-2 |
| TC-025 | 首页 | 键盘 Tab 遍历 | 焦点顺序合理、focus ring 可见；搜索框可由键盘到达 | P1-2 |
| TC-026 | 首页 | 标签按钮 | 选中项 `aria-pressed="true"` | P1-2 |
| TC-027 | 首页 | 卡片容器 | `aria-posinset`/`aria-setsize` 正确 | P1-2 |
| TC-028 | 临时目录 | 拷贝 DB + `static-data.json`，跑 `gen:static-js` | 输出保留全部 `category`；既有条目字段不被覆盖为旧值 | P1-3 |
| TC-029 | 临时目录 | DB 中修改某条 summary 后重生成 | 输出反映新 summary（不是旧值） | P1-3 |
| TC-030 | 临时目录 | 连续跑两次 `gen:static-js` | 条目数稳定、快照不无限堆积（或策略明确） | P1-3 |
| TC-031 | 后端 | `python -c "import web_content_system"` | 成功（当前缺 selenium 失败） | P1-5 |
| TC-032 | 后端 | DB 增删查（临时库） | 结果正确、不触碰仓库 DB | P1-5 |
| TC-033 | 后端 | FallbackSummarizer 生成摘要 | 非空、长度合理 | P1-5 |
| TC-034 | 后端 | `ContentProcessor.validate_content` 长短文本 | 长 True / 短 False | P1-5 |
| TC-035 | 安全 | 检查 iframe sandbox 与仓库无 `.env` | `sandbox=""`（或等价收紧）；`git ls-files` 无 `.env` | P1-2 |
| TC-036 | 性能 | Lighthouse mobile + 500 条压测 | 见 P2-1/P2-2 目标 | P2 |

> 说明：TC-012 是**已经确认会失败**的用例（D-05 的 id 冲突），用于防止“修了但没修好”的回归。

---

## 5. 缺陷清单

> 严重度定义：🟥 P0 = 阻断（静默破坏功能/无证据可验收）；🟧 P1 = 发布前应修；🟨 P2 = 技术债/抛光。
> 状态：全部为“审计发现，未修复”。

### D-01 🟥 P0 — `static-data.json` 与 `static-data.js` 已分叉，`--from-json` 会让站点倒退

- **证据**：JSON 111 条、无 `category`；JS 143 条、含 `category`；两者 SHA 不同、字段集不同（§2.3）。
- **复现**：`npm run gen:static-js:from-json`（等价 `node scripts/generate-data.js --from-json`）→ 产物从 143 条退回 111 条，32 条新内容消失，所有分类丢失。
- **影响**：文档把 JSON 称为 canonical（`CLAUDE.md`），任何人选择“从 JSON 再生成”就会发布一个功能倒退版本；且 lint/CI 都不会报警。
- **建议**：二选一 —— (a) 废弃 `--from-json` 与 JSON 产物，只保留 JS；或 (b) 让 JSON 与 JS 始终同步生成，并在 P0-2 中强制校验二者语义一致。
- **验证**：新增 P0-2 一致性检查 + P1-3 黄金测试。

### D-02 🟥 P0 — 数据再生成会清空全部 `category`（静默、无报错）

- **证据**：`scripts/generate-data.js` 的 SELECT 仅取 6 列，不含 `category`；`web_content.db` 的 `content_summary` 无 `category` 列；`category` 只存在于 `static-data.js`。
- **复现**：`npm run gen:static-js` → 新产物所有条目无 `category` → `CategoryFilter` 计数全空、卡片徽章消失、按分类筛选只能靠 `getCategoryStyle` 回退成“文章”。
- **影响**：这是“优化顺手刷新一下数据”最常见的操作，破坏面 100%，且**没有任何错误输出**——正是“改坏了也不知道”的典型。
- **建议**：把 `category` 落到 DB（迁移列 + 回填脚本）或建立独立映射文件，让生成器可复现；短期至少在生成器里从旧 `static-data.js` 继承 `category`（按 `original_url` 匹配）。
- **验证**：P1-3 TC-028。

### D-03 🟥 P0 — `mergeIncremental` 只增不改，历史错误永远固化

- **证据**：`mergeIncremental()` 仅在 `!map.has(k)` 时 `existing.push(it)`；已存在 key 的字段从不更新。
- **复现**：改 DB 中某行 `summary` → 跑 `gen:static-js` → JSON/JS 中仍是旧 `summary`。
- **影响**：任何“修正摘要/标签/标题/日期”的行为都不会生效；数据修复类需求天然失败。与 `db_manager.py` 的 `ON CONFLICT(uid) DO UPDATE`（upsert）语义相反，两层行为不一致。
- **建议**：改为 upsert（按 `original_url` 覆盖可更新字段），并加“删除/下线”策略；同时明确 `category` 继承规则（见 D-02）。
- **验证**：P1-3 TC-029。

### D-04 🟧 P1 — 发布数据与 DB 严重漂移，“内容新鲜度”无法证明

- **证据**：DB 192 行；发布 143 行；89 个 DB URL 未上线；39 个上线 URL（40 条记录）不在 DB。
- **影响**：用户看到的不是抓取结果；也无法用“DB 变了 → 站点变了”做验收。CI 明确不重新生成数据（`deploy.yml` 注释），使漂移成为常态。
- **建议**：确立单一真源；若坚持“静态产物即真源”，必须在站点/文档标注数据截止日期，并把 DB 视为工作区而非发布输入。
- **验证**：P1-3 + 发布记录里的数据指纹。

### D-05 🟧 P1 — 8 组 id 冲突导致搜索“多显示无关卡片”（已复现）

- **证据**：143 条中仅 135 个唯一 id；8 组（13–17、30–32）各有两个不同文章共用同一 id。另有一条 `original_url` 重复：id 173 / 174 都指向 `ruanyifeng.com/blog/2026/08/weekly-issue-410.html`（同一期周刊里的两篇不同文章），说明数据层没有稳定唯一键。
- **复现**（实测输出）：
  - 搜“英伟达财报” → Fuse 命中 1 条，界面显示 **2** 条，多出“王川：当隔壁老王投资存储股票赚了三十倍后…（二）”。
  - 搜“纳德拉” → 显示 2 条，多出“王川：每天睡到自然醒你就赢了…”。
  - 搜“中国AI全明星” → 显示 2 条，多出“2015年伯克希尔股东大会 - 个人维基”。
  - 量化：搜“AI”51 命中 → 55 张卡片；搜“投资”47 → 54；搜“王川”24 → 29。
- **根因**：`filterData()` 用 `Set<id>` 过滤（`idSet`），重复 id 会把未命中的“同 id 兄弟条目”一并带入；`WaterfallGrid` 的 `key={item.id}` 也会触发 React key 冲突。
- **建议**：数据层消除重复 id（P0-2 强制唯一）；代码层改用 `original_url` 或复合 key 做过滤/渲染 key。
- **验证**：TC-012 + P0-2。

### D-06 🟧 P1 — 32 条记录缺 `created_time`，导致排序错乱/日期空白

- **证据**：JS 中 32 条无 `created_time`（id 172–203 段新增内容），整体非降序；`static-data.json` 则 0 缺失。
- **影响**：卡片日期为空；`mergeIncremental` 的排序把 `undefined` 排到末尾/中间不稳定；未来做“按时间分页/最新内容”会直接错。
- **建议**：补数据（从抓取时间回填）；P0-2 把“时间可解析”设为硬性检查；`formatDate` 已对无效输入返回 `''`，属于兜底而非修复。
- **验证**：TC-002 / TC-022。

### D-07 🟥 P0 — 后端测试套件无法运行（缺 selenium）

- **证据**：`python -m pytest test_*.py` → exit 2，`ModuleNotFoundError: No module named 'selenium'`；`requirements.txt` 声明 `selenium>=4.15.0`，但环境未安装。
- **影响**：`python_scripts` 的任何改动都**没有回归测试保护**；且 collection error 会中断整个 pytest 会话（连 `test_modular.py` 都跑不到）。
- **建议**：把浏览器依赖改为可选导入（`try/except ImportError` + skip marker），或把 selenium 移入 `requirements-dev.txt`；CI 中显式安装。
- **验证**：TC-031。

### D-08 🟧 P1 — `test_modular.py` 是假绿：5 个测试无断言

- **证据**：`pytest -q` → `5 passed, 5 warnings`，每条都是 `PytestReturnNotNoneWarning`；函数体是 `print` + `return True/False`，断言只在个别分支里出现。
- **影响**：把“测试通过”当作质量证据会直接误导验收（Atlas 若看到 “5 passed” 会以为后端健康）。
- **建议**：重写为 `assert` 驱动；使用 `pytest.mark.skipif` 处理可选依赖；CI 中把 `filterwarnings = error::pytest.PytestReturnNotNoneWarning` 设为错误。
- **验证**：P1-5。

### D-09 🟥 P0 — `test_system.py` 会写生产数据库（一旦可运行）

- **证据**：`WebContentExtractor.__init__` → `DatabaseManager(Config.from_env().database.db_path)`，默认 `web_content.db`（相对 cwd）；`test_basic_functionality()` 调用 `extractor.manual_input(...)` → `save_manual_content(...)` → INSERT 到 `manual_content`。
- **现状**：因 selenium 缺失而未执行（DB mtime 仍为 `Aug 28 13:22:58`，未被污染）。
- **影响**：装上 selenium 后跑测试 = 向被 git 跟踪的 `python_scripts/web_content.db` 写入“测试文章标题”等脏数据，并可能被提交。
- **建议**：测试强制 `tmp_path`/内存库；在 `conftest.py` 里把 DB 路径重定向；对生产 DB 加只读保护。
- **验证**：P1-5 + TC-032。

### D-10 🟧 P1 — 前端零测试基础设施

- **证据**：无 vitest/jest/playwright/axe 依赖；`package.json` 无 `test` 脚本；`node_modules` 无相关包；CI 无 test job。
- **影响**：`filterData`、Fuse 配置、分类计数、`formatDate` 等核心逻辑改动只能靠人眼；本轮优化涉及 UI/筛选的概率最高，风险最大。
- **建议**：先加 Vitest（纯函数优先，成本最低），再加 Playwright 冒烟；不要一上来就做全量 E2E。
- **验证**：P0-4 / P1-1。

### D-11 🟧 P1 — 没有数据不变量与产物自检

- **证据**：仓库无 schema 校验脚本；CI 只 build；数据缺陷（D-01/02/05/06）全部能通过现有流程进入发布。
- **影响**：这是“怎么证明没改坏”最关键的缺口（E1/E2/E3 全空）。
- **建议**：立即落地 `scripts/check-data-integrity.mjs`（§6.2），接入 P0；把 `baseline-filter-expected.json` 作为差分基准。
- **验证**：P0-2 / P0-3。

### D-12 🟨 P2 — CI 不跑 lint，也不设 bundle 预算

- **证据**：`deploy.yml` 只有 build + deploy；本地 lint 通过但 CI 无约束。
- **影响**：lint 规则形同虚设；体积增长无人拦（当前 JS gzip 103.9 KB 已含 143 条数据）。
- **建议**：CI 加 `npm run lint` + 体积阈值对比。
- **验证**：P0-1 / P0-6。

### D-13 🟨 P2 — favicon 404

- **证据**：`index.html` 引用 `/vite.svg`，`public/` 与 `dist/` 均无该文件（只有 `logo-*.svg`）。
- **影响**：控制台 404，无功能影响。
- **建议**：改为 `/logo.svg` 或补文件。

### D-14 🟨 P2 — 快照文件无保留策略

- **证据**：`src/assets/static-data-20260730-*.json` 共 7 个（已 gitignore 但未清理）；`generate-data.js` 每次运行都新写一个快照，从不删除。
- **影响**：长期运行的开发者目录膨胀；与“仓库干净”的验收标准冲突。
- **建议**：保留最近 N 份或改为输出到 `.cache/`。

### 缺陷汇总

| 严重度 | 数量 | 编号 |
|---|---|---|
| 🟥 P0 | 4 | D-01, D-02, D-03, D-07（D-09 同为 P0 风险） |
| 🟧 P1 | 8 | D-04, D-05, D-06, D-08, D-10, D-11（+ D-09 计 P0） |
| 🟨 P2 | 3 | D-12, D-13, D-14 |

---

## 6. 建议补充的最小测试资产（本次**未创建**，仅规格）

> 任务要求只读审计；以下为“下一步该写什么”，不是已交付代码。

### 6.1 文件清单

| 文件 | 类型 | 作用 | 落地门禁 |
|---|---|---|---|
| `scripts/check-data-integrity.mjs` | Node（只读） | 12 项数据不变量 | P0-2 |
| `scripts/diff-static-data.mjs` | Node（只读） | 与基线/HEAD 做集合差分 | P0-3 |
| `scripts/check-bundle-budget.mjs` | Node（只读） | 体积阈值 | P0-6 |
| `src/utils/filterData.js` + `src/utils/filterData.test.js` | 重构 + Vitest | 把筛选逻辑抽成纯函数并单测 | P0-4 |
| `tests/e2e/smoke.spec.js` | Playwright | TC-001～009 | P0-7 / P1-1 |
| `tests/e2e/a11y.spec.js` | Playwright + axe | TC-024～027 | P1-2 |
| `python_scripts/tests/conftest.py` | pytest | 隔离 DB（`tmp_path`） | P1-5 |
| `python_scripts/tests/test_*.py` | pytest | 真断言、marker（unit/integration/network） | P1-5 |
| `.github/workflows/ci.yml` | CI | 门禁编排 | P0/P1 |

### 6.2 数据不变量脚本规格（12 项）

对 `src/assets/static-data.js` 逐项断言：

1. 可被 ESM 成功 import，`export default` 是数组。
2. 数组非空，条数 ≥ 基线（默认 143）。
3. 每条为对象，必填 `id`、`title`、`summary`、`original_url`、`tags` 均非空。
4. `id` 唯一（当前**失败**：8 组冲突）。
5. `original_url` 唯一（当前 142/143，1 条重复）。
6. `original_url` 匹配 `^https?://`。
7. `created_time` 可被 `new Date()` 解析（当前**失败**：32 条缺失）。
8. 数组按 `created_time` 降序（当前**失败**）。
9. `category` 存在且 ∈ 7 类之一，或为 `undefined`（回退“文章”）。
10. `tags` 为逗号分隔字符串，去重后无空项。
11. 与基线相比：删除条目为 0，或删除清单已在 allowlist。
12. 分类分布与基线相比无未解释变化（允许新增带来变化，但要输出 diff）。

输出 `data-integrity.json`（通过/失败项 + 计数 + sha256），CI 上传 artifact。

### 6.3 前端单测规格（≥18 条）

把 `App.jsx` 中的 `filterData` 抽成 `src/utils/filterData.js`（纯函数，入参：`items, { query, category, tags, fuse }`）：

- 空筛选 → 全量；分类单选 → 精确；标签 OR；搜索（中文/英文/大小写/空串/空格）；三者组合；无结果；计数一致；排序保持；重复 id 行为（锁死 D-05 修复）。

### 6.4 E2E 规格

Playwright + Chromium（P1 加 WebKit）：TC-001～009 作为 `smoke.spec.js`；TC-024～027 用 `@axe-core/playwright`；截图对比在 P1-8。

### 6.5 Python 测试重构规格

- `conftest.py`：`db_path=tmp_path/"test.db"`；`monkeypatch` 环境变量；任何用例禁止访问仓库内 `web_content.db`（可用 fixture 断言路径）。
- `markers`：`@pytest.mark.unit`（无网络/无浏览器）、`@pytest.mark.integration`（DB）、`@pytest.mark.network`（默认 skip）。
- 把 `test_modular.py` 的 5 个函数改为真断言；`test_system.py` 拆成“可离线契约测试”+“人工联调脚本”（不进 CI）。

---

## 7. 未测试区域与环境阻塞

| ID | 区域 | 状态 | 原因 | 解除条件 |
|---|---|---|---|---|
| B-1 | 后端测试全集 | **阻塞** | 缺 `selenium`，collection error | 安装依赖或改可选导入 |
| B-2 | 浏览器 E2E | **未执行** | 无 Playwright/驱动；任务禁止装依赖 | 批准安装 `@playwright/test` |
| B-3 | a11y 扫描 | **未执行** | 无 axe 依赖 | 同上 |
| B-4 | 构建验证 | **未执行** | 任务明确禁止跑 build；`dist/` 是他人产物 | 允许跑 `npm run build` |
| B-5 | 数据再生成验证 | **未执行（设计为只读）** | 会写 `src/assets/*`；按只读要求未跑 | 在临时目录拷贝后执行 |
| B-6 | DB 加密/解密 | **未测试** | 无可用 `SQLITE_KEY`（`.env` 未读取） | 提供测试密钥或 CI secret 演练 |
| B-7 | 外链可达性 | **未测试** | 未访问网络 | P1-6 抽样 |
| B-8 | 移动端真机 / Safari | **未测试** | 无设备 | P1-7 |
| B-9 | 报告 HTML 内容 | **未测试** | 需浏览器打开 iframe | P1-1 |
| B-10 | 抓取器选择器 | **未测试** | 依赖真实站点 + 网络 | P2-3（fixture/mock） |
| B-11 | LLM 摘要质量 | **未测试** | 需 API key；非确定性 | 人工/离线评测集 |

**未覆盖结论**：本次审计覆盖了“可离线、只读、无需构建”的部分（lint、pytest 调用、数据一致性、筛选基线）。**所有发布级证据（E2E、a11y、构建、性能）都仍需在获批环境中执行**，在此之前任何“优化没问题”的结论都不成立。

---

## 8. 回归风险评估

### 8.1 风险热区

| 区域 | 典型改动 | 回归概率 | 影响 | 现有防线 | 风险 |
|---|---|---|---|---|---|
| 数据管道（generate-data + static-data） | “顺便刷新数据”、改字段 | **高** | **高（功能整体消失）** | 无 | 🟥 最高 |
| 分类筛选 / 搜索 / 标签组合 | 重构 `filterData`、改 Fuse 参数 | 中高 | 中高（用户核心操作） | 无 | 🟥 |
| 数据本身（id 冲突/缺时间） | 新增内容、导入 | 高 | 中（搜索错、日期空） | 无 | 🟧 |
| 组件/样式（瀑布流、卡片、弹窗） | 视觉优化 | 中 | 中（布局/交互） | 人眼 | 🟧 |
| 构建配置 / 依赖 | 升级 Vite/Tailwind、去依赖 | 低 | 中（白屏） | CI build | 🟨 |
| Python 后端 | 抓取/摘要/DB | 中 | 中（数据进不来） | 假绿测试 | 🟧 |
| a11y | aria/焦点调整 | 中 | 低中 | 无 | 🟨 |
| 性能 | 新增依赖/大图 | 低 | 中 | 无 | 🟨 |

### 8.2 评分与建议

- **总体回归风险：高**。不是因为代码质量差，而是因为**没有防线**：0 个有效自动断言 + 数据管道 3 个静默破坏点。
- 建议把 80% 的测试投入放在 **P0-2/P0-3（数据不变量与差分）** 和 **P0-4（筛选纯函数单测）**——这两块覆盖了本仓库历史缺陷（D-01/02/03/05/06）的绝大多数。
- 不建议本轮投入：视觉回归、完整 E2E 全矩阵、性能基准——收益低于成本，放到 P2。

---

## 9. 发布建议

### 9.1 判定

**本轮“整体优化”完成后是否可发布：FAIL。**

理由（证据充分）：

1. 没有基线冻结（E1 今天才生成数据部分，DOM/构建/性能均无）。
2. 没有不变量校验（E2），而数据层已存在 4 个可静默破坏功能的缺陷（D-01/02/03/09）。
3. 没有差分机制（E3），无法回答“改后与改前差在哪”。
4. 没有 E2E/a11y/性能（E4），交互回归只能靠人眼。
5. 后端测试不可运行且会假绿（D-07/D-08），等于后端无保护。

**对当前仓库作为“优化前基线”的判定：CONDITIONAL PASS。**

站点主路径可用（lint 0 error、静态数据可加载、构建链路存在），可作为改动起点；但必须在**开工前**补齐 §9.2 的 5 条，否则后面的“验收”无从谈起。

### 9.2 转为 PASS 的必要条件（按优先级）

| # | 条件 | 负责 | 完成判据 |
|---|---|---|---|
| 1 | 落地数据不变量脚本并接入 CI（P0-2/P0-3） | QA + Backend | CI 上 `check-data-integrity.mjs` 全绿；已知 4 项违规先修或显式 allowlist |
| 2 | 修掉 D-02/D-03（category 可复现 + 合并语义改 upsert） | Data/Pipeline | TC-028/029 通过；生成后 category 保留率 100% |
| 3 | 清理 D-05/D-06（id 冲突、缺时间） | Data | TC-021/022 通过；搜索误显示消失 |
| 4 | 让后端测试真正可运行（selenium 可选 + 真断言 + 隔离 DB） | Backend | `pytest` exit 0 且有断言；无仓库 DB 写入 |
| 5 | 建前端最小测试 + 冒烟（Vitest 18 条 + Playwright 9 条） | Frontend + QA | P0-4 / P0-7 在 CI 绿；灯号可查 |

补齐后：任何优化 PR 只要 P0 全绿 + P1 差分无未解释变化，即可给出 **PASS**；若 P0 有红或差分有未解释项，保持 **FAIL**。

### 9.3 建议执行顺序

1. **今天（30 分钟）**：把本报告 §9.2-1 的脚本建起来（只读），先让 D-01/02/05/06 变成“红灯”，而不是“没人知道”。
2. **本周**：修数据（D-05/D-06）、修生成器（D-02/D-03）、修后端测试（D-07/D-08/D-09）。
3. **开始优化前**：冻结 E1 基线（DOM 截图 + bundle 统计 + 144 组筛选结果）。
4. **优化 PR 期间**：P0 全绿 + P1-4 差分无未解释变化。
5. **发布前**：P1-1/2/8 + 人工抽查；发布记录附证据产物。

---

## 附录 A：完整命令与关键输出

```text
$ git status --porcelain --untracked-files=all
（空）

$ npm run lint
> eslint src scripts --max-warnings=999
exit 0（0 error / 0 warning）

$ cd python_scripts && python -m pytest test_*.py -q
E   ModuleNotFoundError: No module named 'selenium'
ERROR test_system.py
1 error in 0.15s
exit 2

$ cd python_scripts && python -m pytest test_modular.py -q
5 passed, 5 warnings in 0.05s
exit 0
（5 条 warnings 均为 PytestReturnNotNoneWarning）

$ node（静态数据一致性）
count json/js 111 143
deep-equal false
missing keys { category: 111 }
categories { undefined: 111 }
dup ids count 8
no created_time 32
unique ids 135 rows 143
sorted desc false

$ python3（DB 只读）
content_summary 192 行；列 = id,title,created_time,summary,original_url,tags,uid,content
DB 中有、线上无：89；线上有、DB 中无：39

$ node（搜索重复 id 复现）
问: 英伟达财报 | Fuse 命中 1 | 界面显示 2 条
  ❌ 误显示: 13 王川：当隔壁老王投资存储股票赚了三十倍后…（二）
问: 纳德拉 | Fuse 命中 1 | 界面显示 2 条
  ❌ 误显示: 15 王川：每天睡到自然醒你就赢了…
问: 中国AI全明星 | Fuse 命中 1 | 界面显示 2 条
  ❌ 误显示: 32 2015年伯克希尔股东大会 - 个人维基

$ shasum -a 256 src/assets/static-data.js …
9257b5f8…  static-data.js
11ac04b4…  static-data.json
bc545ebe…  web_content.db
```

## 附录 B：基线产物说明

`baseline-filter-expected.json`：

- 生成方式：只读 import `src/assets/static-data.js`，用仓库自带 `fuse.js@7` 按 `App.jsx` 的参数（`keys:['title','summary']`, `threshold:0.35`, `ignoreLocation:true`, `useExtendedSearch:true`）复刻 `filterData()`。
- 内容：`rows:143`、`unique_ids:135`、`tag_count:44`、七分类分布、**144 组**（`q ∈ {AI, 人工智能, 投资, 王川, 开源, 空}` × `category ∈ {无 + 7 类}` × `tag ∈ {无, 标签1, 标签2}`）的期望 id 列表。
- 用途：P1-4 差分测试的黄金基线；优化后重跑同一脚本，逐用例比较 id 集合。
- 注意：该基线**固化了当前的错误**（重复 id 导致的搜索误命中）。修 D-05 之后，基线需要按“修复后期望值”重建一次，并在 PR 中说明这是**有意变更**。

## 附录 C：本次审计的改动清单

```text
新增：
  docs/superpowers/audits/2026-10-18/testing-quality.md        （本报告）
  docs/superpowers/audits/2026-10-18/baseline-filter-expected.json（基线）
未修改任何产品代码、配置、依赖、数据文件、CI。
```

```text
$ git status --porcelain --untracked-files=all
?? docs/superpowers/audits/2026-10-18/
```
