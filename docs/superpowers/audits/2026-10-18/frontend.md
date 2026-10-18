# 前端审计：性能 / 状态管理 / 可访问性 / 交互 bug

- **审计人**：Pixel（Frontend Engineer）
- **日期**：2026-10-18（Asia/Shanghai）
- **模式**：**只读**。未修改任何源码、数据或配置；未执行 `git checkout/reset/fetch`，线上版本文件全部用 `git show origin/main:<path>` / `git archive` 读取。
- **审计对象（两条无共同祖先的历史，分开结论）**：
  - **本地版本**：工作区 `main`（HEAD `22544ca`，前端 143 条数据、单视图瀑布流）。构建：`npx vite build` ✅。
  - **线上版本**：`origin/main`（`997cd99`，2026-09-03；比本地多 10 个提交，新增 Tab 双视图 / Last30days 搜索页）。构建：`vite build` ✅；**`eslint` ❌ 3 errors**。
  - **线上部署**：`origin/gh-pages`（2026-09-03 构建，`https://dllen.github.io/deepthink/`）——用于生产可用性验证。
- **环境**：macOS · Chrome 155 headless（CDP 真实浏览器，1440×900 / 375×812 移动仿真）· Node 22 · 截图证据在 `docs/superpowers/audits/2026-10-18/assets/frontend/`。

---

## 0. 结论摘要

### 0.1 生产阻断（P0，必须先处理）

| 编号 | 结论 | 证据 |
|---|---|---|
| **FE-P0-1** | **线上站点白屏**：`gh-pages` 的 `index.html` 用根绝对路径 `/assets/*`，实际部署在 `/deepthink/` 子路径 → JS/CSS 全部 404，`#root` 为空；报告页链接也是根绝对路径，同样 404；favicon 404。 | 真实浏览器打开 `https://dllen.github.io/deepthink/`：`#root` 子节点 0，Net 404：`/assets/index-1a0092fe.js`、`/assets/index-bc685c66.css`、`/vite.svg`；正确子路径 `/deepthink/assets/...` 返回 200。见 `assets/frontend/01-live-deploy-blank.png` |

> 这一条与"线上版本新增了搜索页"无关：只要 `vite.config.js` 没有 `base`，任何一次部署都会白屏。修复后需重新部署并复验。

### 0.2 两版本共有（本地 `main` 与 `origin/main` 同样存在，浏览器已复现）

| 编号 | 级别 | 问题 | 关键证据 |
|---|---|---|---|
| FE-02 | **P1** | 搜索命中数与实际渲染卡片数不一致：数据里 8 组重复 id + `key={item.id}` → React 复用错节点、残留旧卡片；`idSet` 过滤把"同 id 兄弟"一起带出 | 搜「英伟达」头部「5 条内容」但 DOM 13 张卡；搜「王川」29 vs 38；随后改为无结果查询，头部「0 条内容」仍残留 8 张无关卡片 + 空态同时出现；dev 模式 8 条 `Encountered two children with the same key`（13–17、30–32）见 `02-duplicate-key-stale-cards.png` |
| FE-03 | **P1** | 两个筛选器 `sticky top-24 z-40` 同偏移互相覆盖；移动端标签筛选器高 **504px**，吸附后占视口 **62%**（叠加 97px 头部约 74%），分类筛选器被完全遮住 | 桌面滚动 1200/1600/2200 实测：分类 96–179、标签 96–222，重叠 83px；`elementFromPoint(300,130)` 命中的是标签容器。移动端滚动 2000+：两者 top 均 96，标签覆盖 96–600（视口 812）。见 `03`、`04` |
| FE-04 | **P1** | 空态按钮「清除所有筛选」只清标签（`clearFilters` 只 `setSelectedTags([])`），不清搜索词与分类 → 因搜索进入空态时按钮**完全无效** | 输入 `zzzz_none` → 点按钮 → 输入框仍为 `zzzz_none`、头部仍「0 条内容」、空态仍在 |
| FE-05 | **P1** | 报告弹窗 `sandbox=""` 阻断报告页全部脚本：象限图空白、筛选 chips 空、榜单/矩阵表空（报告是纯 JS 渲染） | 直开报告：canvas 691×520、两张表各 31 行、filter-bar 4/3 项；弹窗内同页：图表区空白、侧栏空。见 `05` vs `06`（安全侧见 Aegis M-1，功能修复见 §3） |
| FE-06 | P2 | 弹窗无 `role="dialog"`/`aria-modal`、打开后焦点不进入、关闭后不归还、背景内容仍可 Tab、遮罩不可键盘操作 | CDP：打开后 `document.activeElement === BODY`；无 dialog/aria-modal 节点；Esc 可关；关闭后焦点 BODY |
| FE-07 | P2 | 对比度不足：7 个激活分类 pill 全部 < 4.5:1；页脚 2.56；卡片标签 chip 4.34；已选标签删除按钮无名称且**焦点不可见** | 实测比值：科技 3.68 / 文章 4.47 / 工具 2.54 / 资源 2.15 / 图片 3.53 / 文摘 4.23 / 言论 2.80（14px/500）；页脚 `slate-400` 2.56；chip 4.34。删除按钮：`textarea=''`、无 `aria-label`，focus 时 `outline-style: none` |
| FE-08 | P2 | 32/143 条无 `created_time` → 卡片渲染 16×8px 的空日期徽章（可见空白块）；且前端不做排序，最新内容沉底 | 32 张空徽章卡片，示例 16×8px、背景 `slate-50`；数据侧见 Pipeline 报告 D-06，本报告只给前端兜底建议。见 `07` |
| FE-09 | P2 | 无 Error Boundary / `<noscript>` / iframe 失败态：JS 挂掉即整页空白（正是 FE-P0-1 的现象）；弹窗报告加载中无 loading、404/被阻断无提示 | `main.jsx` 无边界；`index.html` 无 `<noscript>`；`ReportModal` iframe 无 loading/onError |
| FE-10 | P3 | 派生状态反模式 + 假加载态：`filteredData` 存 state、在 `useEffect` 里二次 setState；`isLoading` 与数据同帧结束，加载态实际只闪一帧 | `App.jsx:16,53-79,161-170`；Fuse 实测：建索引 0.7ms、143 条查询 2.3–7.5ms（Node），当前不是瓶颈 |
| FE-11 | P3 | 无效 ARIA：`role="group"` 上放 `aria-posinset/aria-setsize`（该 role 不支持），且 `columns-*` 列优先 DOM 顺序问题仍未解决（旧审计 C2 部分未闭） | `WaterfallGrid.jsx:10-12`；无效属性被 AT 忽略，焦点顺序仍列优先 |
| FE-12 | P3 | CSS 重复/死规则：`App.css` 与 `index.css` 重复定义 `.waterfall-item`/`.tag-button`；`.tag-button.active` 从未被添加；`App.css` 全局 `.grid` 规则与 Tailwind `grid-cols-*` 层叠竞争（当前靠顺序侥幸不冲突） | 编译后 CSS 中 `.grid{display:grid;grid-template-columns:repeat(auto-fill,…)}` 位于 utilities 之前 |
| FE-13 | P3 | `item.tags.split(',')` 两处无空值保护（`App.jsx:68`、`ContentCard.jsx:45`）；卡片仅右上角图标可点、`title` 属性承担外链可访问名 | 当前 143 条都有 tags，属潜在崩溃/体验问题 |

### 0.3 线上版本（`origin/main`）特有

| 编号 | 级别 | 问题 | 关键证据 |
|---|---|---|---|
| FE-O1 | **P1** | **搜索页"信息源卡片"功能是死的**：`Last30daysPage` 的 `query` 状态从未被更新，`setQuery` 无人调用（lint `no-unused-vars` 直接报错），`SearchHero` 自持 query、不通知父级 → `SourcesGrid` 永远收到 `query=''`：13 张卡永久 `opacity-60`（看似禁用），点击打开的是**空查询**链接 | SSR + 浏览器：13/13 卡带 `opacity-60`；在 SearchHero 输入 `AI agent` 后仍是 13/13；lint error `Last30daysPage.jsx:7 'setQuery' is assigned a value but never used` |
| FE-O2 | **P1** | Tab 切换无 URL/历史/刷新语义（spec 明确"无 URL 变化"，但任务要求审查）：刷新回"内容浏览"、无法分享"信息检索"、浏览器后退不切换；切换**保留滚动位置**（从瀑布流 1200px 切过去仍停在中部）；两视图状态策略不一致（浏览筛选保留、搜索输入丢失） | CDP：切换前后 `scrollY` 均 1200；URL/title 不变；hero 输入 `claude code` → 切到浏览再切回 → 值变空 |
| FE-O3 | P2 | Tab 按钮无 `role="tablist"/"tab"`、无 `aria-selected/aria-pressed`；搜索视图同时存在 2 个 `h1`（页头「观念棱镜」+ 页面「信息检索」） | CDP：两个 tab 按钮 `aria-pressed/current/selected` 全为 null；`h1` 数量 2 |
| FE-O4 | P2 | SearchHero 可达性/交互缺口：输入框无 label（仅 placeholder）、清除按钮无名称；无 `<form>` → **按 Enter 不触发任何动作**；spec 要求"输入时实时更新 URL 预览"未实现 | CDP：`input aria-label=null`、图标按钮 `aria-label=null`；`<form>` 数量 0；页面无 URL 预览文本元素 |
| FE-O5 | P2 | 全部跳转用 `window.open(url, '_blank')` 而不是 `<a>`：无 `noopener/noreferrer`（反向标签页劫持）、不支持中键/复制链接/右键、无链接语义与可访问名 | 搜索视图 `<a>` 数量 0；`SearchHero.jsx:9`、`SourcesGrid.jsx:6` |
| FE-O6 | P2 | arXiv 搜索链接参数错误，**打不开带关键词的搜索结果**（实测无结果）；spec 写 `search={q}`、代码写 `search_query={q}`，两者都不对，正确为 `searchtype=all&query={q}` | `curl 'https://arxiv.org/search/?search_query=electron'` → 无 "Showing … results"；`?searchtype=all&query=electron` → "Showing 1–50 of 187,658 results" |
| FE-O7 | P3 | `SourcesGrid` 用 `<button>` 包 `<h3>/<p>`（HTML 内容模型非法，标题语义被吞）；无 query 时只是 `opacity-60`，仍可点击、无说明 | SSR：`heading_inside_button: true`；13 张卡 `opacity-60` 且可聚焦 |
| FE-O8 | P3 | 375px 下页头被挤压换行：品牌标题换 2 行、两个 tab 文字各换 2 行，header 97px（本地单视图为 73px、单行）：无横向溢出但观感差 | CDP：header 97，brand 191×64，h1 高 64，tab 按钮高 56；`scrollWidth == 375`。见 `08` |
| FE-O9 | P2 | 线上版本 **lint 不通过**（3 errors），而 `deploy.yml` 只跑 build → 错误代码直接上线；`--max-warnings=999` 还会把 warning 全部压掉 | `eslint src scripts` → exit 1：`Last30daysPage.jsx:7`、`PhilosophySection.jsx:59` ×2 |
| FE-O10 | P3 | 体积：线上版本 JS 310,041B（gzip 106,288）/ CSS 35,427B（gzip 6,370）；本地版本 297,388B（gzip 103,688）/ 29,671B（gzip 5,730）。**部署产物 318,698B 与干净构建差 +2.8%**（无 lockfile、依赖漂移，不可字节复现） | `wc -c` / `gzip -9`；`curl` 线上 JS |
| FE-O11 | P3 | 死数据/死接口：`last30days-sources.js` 的 `nameCn`（13 处）无任何使用；`buildAllSearchUrls` 的 `sourceIds` 参数无调用者 | grep 全量 `src/` |

---

## 1. 方法与可复现证据

### 1.1 只读读取线上版本

```bash
git log --oneline origin/main -12
git ls-tree -r --name-only origin/main
git show origin/main:src/App.jsx > /tmp/deepthink-online/src/App.jsx   # 逐文件 git show
git archive origin/main | tar -x -C /tmp/deepthink-online-tree          # 构建校验用，未触碰工作区
```

### 1.2 构建 / lint（两版本）

```bash
# 本地版本（工作区）
npm run lint          # 0 error / 0 warning
npx vite build        # ✅ 点击 297,388 B（gzip 103,688 B）

# 线上版本（/tmp 导出树，node_modules 软链到工作区）
./node_modules/.bin/eslint src scripts --max-warnings=999   # ❌ exit 1，3 errors
./node_modules/.bin/vite build                              # ✅ 310,041 B（gzip 106,288 B）
```

### 1.3 真实浏览器（Chrome 155 headless + CDP）

- 本地构建 / 线上构建分别用 `python3 -m http.server` 在 8200 / 8199 端口静态托管（未使用生产服务器）。
- 视口：桌面 1440×900；移动 375×812（`Emulation.setDeviceMetricsOverride`，DPR=2）。
- 采集：DOM 计数、`getBoundingClientRect`、`elementFromPoint`、`getComputedStyle` 对比度、焦点/`activeElement`、`Runtime.consoleAPICalled`（dev 模式 React 警告）、`Page.captureScreenshot`。
- 关键复现步骤（可逐条重放）：
  1. 输入搜索词（原生 setter + `input` 事件）→ 对比 `header` 文本与 `.waterfall-item` 数量；
  2. `window.scrollTo(0, 1200/1600/2200)` → 读两个 `[class*="sticky"][class*="top-24"]` 的 rect；
  3. 点「清除所有筛选」→ 读输入框值与空态；
  4. 打开报告卡片 → 读 `iframe.getAttribute('sandbox')`、`iframe.contentDocument`、`activeElement`；
  5. 点 Tab 切换 → 读 `scrollY`、`location.href`、`document.title`、hero 输入值。

### 1.4 数据侧测量（Node 22，同一份 `static-data.js`）

- 143 条，8 个重复 id（13–17、30–32），32 条无 `created_time`；
- Fuse 建索引 0.7ms；单次查询 2.3–7.5ms（143 条）→ 当前性能非瓶颈；
- 搜「王川」24 命中 → 29 行（重复 id 扩张），与浏览器现象一致。

### 1.5 线上部署验证

```bash
curl -s -o /dev/null -w '%{http_code}' https://dllen.github.io/deepthink/assets/index-1a0092fe.js   # 404（正确子路径 200）
curl -s -o /dev/null -w '%{http_code}' https://dllen.github.io/deepthink/assets/index-bc685c66.css   # 404（正确子路径 200）
curl -s -o /dev/null -w '%{http_code}' https://dllen.github.io/deepthink/A股…看板.html               # 200
curl -s -o /dev/null -w '%{http_code}' https://dllen.github.io/A股…看板.html                         # 404（代码里用的正是这条）
```

真实浏览器打开线上站点：`#root` 子节点 0；Net 三条 404；全页空白（`01-live-deploy-blank.png`）。

---

## 2. 生产/部署（与代码版本无关的 P0）

### FE-P0-1 线上白屏

- **现象**：`https://dllen.github.io/deepthink/` 返回 200 的 shell，但 JS/CSS 404，页面空白，favicon 404。
- **根因**：
  - `vite.config.js:5-11` 未设置 `base`，构建产物引用 `/assets/*`（根绝对）；
  - 仓库是 `dllen/deepthink` 项目页，站点根是 `/deepthink/`，`gh-pages` 分支无 `CNAME`（历史中亦无）→ 只能按子路径访问；
  - `src/assets/static-reports.js:11` 的 `path: '/A股…html'` 同样是根绝对；
  - `index.html:5` 的 `/vite.svg` 文件根本不存在（`public/` 只有报告页）→ 线上 404。
- **影响**：生产站点 100% 不可用（任何浏览器），本地 `npm run dev` 完全正常，极易漏测。
- **建议（不在本次实施）**：
  1. `base: '/deepthink/'`（或 `base: './'` + 报告路径改相对/`import.meta.env.BASE_URL`）；
  2. favicon 改用 `src/assets/logo.svg`（或补 `public/favicon.svg`），并去掉绝对根路径；
  3. 报告 `path` 统一走 `import.meta.env.BASE_URL`；
  4. 部署后加一条冒烟检查（`curl` 一个 `/deepthink/assets/*.js` 应为 200），避免再次白屏。
- **验收方式**：部署后刷新线上 URL，`#root` 有内容、Network 无 404、报告弹窗能打开。

---

## 3. 两版本共有问题（详情与修复建议）

### FE-02 搜索"命中数 ≠ 渲染数"，残留无关卡片（P1）

- **现象（浏览器实测，本地与线上版本一致）**：
  - 搜「英伟达」→ 头部「5 条内容」，页面上 13 张卡；
  - 搜「王川」→ 29 条 vs 38 张卡；
  - 先搜有结果的词、再改成 `zzzz_none` → 头部「0 条内容」、空态已出现，但下方仍残留 8 张与查询无关的卡片（`02-duplicate-key-stale-cards.png`）；
  - dev 模式控制台 8 条 `Warning: Encountered two children with the same key`（13–17、30–32）。
- **根因（两层）**：
  1. 数据层：8 组重复 id（同一 id 两条不同文章，见 Pipeline D-03/D-05）——
     `App.jsx:62-65` 用 `new Set(hits.map(r => r.item.id))` 再按 `item.id` 过滤，重复 id 会把未命中的"同 id 兄弟"一起放行；
     `WaterfallGrid.jsx:8` 用 `key={item.id}`，重复 key 使 React 在列表变化时复用/残留节点（正是警告里说的 duplicated/omitted）。
  2. 渲染层：`key` 不稳定 → 列表更新后旧节点未被移除。
- **影响**：搜索结果"多出无关文章"、空态与卡片同屏、卡片数量与头部计数矛盾；用户会认为搜索坏了。这是本次审计**最直接的线上可见正确性 bug**。
- **建议**：
  - 前端：过滤改用 `hits.map(r => r.refIndex)`（或直接用命中的对象引用）而不是 id；`WaterfallGrid` 的 key 改用 `original_url`（或 `id + original_url` 复合 key）直到数据层强制唯一；
  - 数据层（交给 Pipeline）：生成时强制唯一 id / 改用 `original_url` 作为主键，并保证 `key` 稳定；
  - 回归用例：搜「英伟达」应只出现命中卡片；从有结果切到无结果时 DOM 卡片数必须为 0。
- **验证**：`header` 计数与 `.waterfall-item` 数量相等；空态出现时卡片数 0；dev 控制台无 duplicate key 警告。

### FE-03 双 sticky 筛选器互相覆盖 + 移动端筛选器吞掉大半屏（P1）

- **桌面实测**（滚动 1200 / 1600 / 2200 三处结果一致）：
  - 分类筛选器：top 96 → bottom 179；
  - 标签筛选器：top 96 → bottom 222；
  - 重叠 83px；`elementFromPoint(300, 130)` 命中标签筛选器 → **分类筛选器被压在下面，滚动后不可点**；
  - 根因：`App.jsx:142` 与 `App.jsx:151` 都是 `sticky top-24 z-40`，后出现的标签筛选器以同 z-index 覆盖前者。
- **移动端实测（375×812）**：
  - 分类筛选器自然高度 165px，标签筛选器 **504px**（44 个标签在窄屏折行）；
  - 滚动到 2000/2400 时两者都吸附在 top 96：分类 96–261、标签 96–600，标签**完全盖住分类**；
  - 吸附状态共占 96→600 = 504px ≈ 视口 62%（再加 97px 页头 ≈ 74%），正文只剩底部约 200px（`04-mobile-sticky-filters.png`）。
- **影响**：滚动后用户既看不到分类筛选、也没有多少正文空间；移动端体验显著受损。桌面同样存在"分类筛选被挡住"。
- **建议**：
  - 合并为**一个** sticky 容器（分类 + 标签一起），或只让搜索栏 sticky；
  - 标签筛选器在移动端改为横向滚动/折叠（"更多标签"），或只让桌面端 sticky（`lg:sticky`）；
  - 若两条都要 sticky，使用**顺序偏移**（第二条 `top = 第一条高度 + 96px`）并显式 z-index；
  - 验收：滚动到底部时两个筛选器都不互相遮挡，移动端 sticky 区域 ≤ 视口 30%。

### FE-04 空态"清除所有筛选"不完整（P1）

- **现象**：`clearFilters` 只 `setSelectedTags([])`（`App.jsx:91-93`），但按钮出现在**所有**空结果场景（`App.jsx:183-188`），文案是"清除所有筛选"。
- **实测**：搜索框输入 `zzzz_none` → 点按钮 → 输入框仍 `zzzz_none`、头部仍「0 条内容」、空态仍在（用户被卡死，只能手动删输入）。
- **建议**：拆分语义——`clearAllFilters()` 同时清 `selectedTags`、`selectedCategory`、`searchQuery`；TagFilter 里的「清除全部」保持只清标签并按文案区分（"清除标签"/"清除全部筛选"）。同一问题也存在于 TagFilter 的「全部内容」按钮（只清标签，分类/搜索仍在）。
- **验收**：任意筛选组合导致空态后，点按钮恢复 143 条。

### FE-05 报告弹窗 sandbox 阻断脚本 → 报告"只剩壳"（P1）

- **现象（截图对比）**：
  - 直开 `public/A股行业财政乘数矩阵看板.html`：象限气泡图（canvas 691×520）、两张表各 31 行、筛选 chips（4/3 个）全部渲染；
  - 在首页弹窗里：图表区白、筛选 chips 空、榜单/表空——因为 `ReportModal.jsx:79` 是 `sandbox=""`（禁止脚本），而报告 394–713 行是整页 JS 渲染（`new Chart`、`refreshAll()`、filter bar 构建）。
  - `iframe.contentDocument` 为 `null`（opaque origin），父页面也无法兜底。
- **影响**：用户点"分析报告"看到一张几乎空的页面，只有静态文案/指标卡；报告的核心价值（图表/矩阵/榜单）全部丢失。
- **建议**（与 Aegis M-1 的安全建议对齐，**不要**回到 `allow-scripts allow-same-origin`）：
  1. 自托管 Chart.js（去掉 CDN 依赖）后使用 `sandbox="allow-scripts"`（唯一 origin、可执行脚本、父页面不可访问）；
  2. 或图表改为由父页面拿数据渲染（`postMessage` 传数据、报告页只做渲染）；
  3. 无论哪种，补 iframe `loading` 态与"加载失败 → 在新窗口打开"的兜底。
- **验收**：弹窗内图表/筛选/榜单与直开一致；父页面无法读取 iframe DOM。

### FE-06 弹窗缺少 dialog 语义与焦点管理（P2）

- 实测：无 `role="dialog"`/`aria-modal`；打开后 `activeElement` 仍是 `BODY`（焦点留在背景）；关闭后焦点不回到触发卡片；遮罩是 `<div onClick>`（键盘不可用）；背景内容未 `aria-hidden`/`inert`，Tab 会跑到弹窗外。
- **建议**：`role="dialog" aria-modal="true" aria-labelledby`；打开时把焦点移到关闭按钮（或 `h2` 需 `tabIndex=-1`）；关闭时恢复到触发元素；用 `inert`/`aria-hidden` 隔开背景；遮罩用 `<button aria-label="关闭">` 或保留 Esc 即可（Esc 已有）。
- **验收**：键盘 Tab 只在弹窗内循环；Esc 关闭后焦点回到报告卡片。

### FE-07 对比度与"无名称/无焦点"控件（P2）

**实测对比度**（WCAG AA：14px 普通文本需 ≥4.5:1）：

| 元素 | 前景/背景 | 实测 | 结论 |
|---|---|---|---|
| 激活分类 pill「科技动态」 | white / blue-500 | 3.68 | ❌ |
| 「文章」 | white / indigo-500 | 4.47 | ❌（临界） |
| 「工具」 | white / emerald-500 | 2.54 | ❌ |
| 「资源」 | white / amber-500 | 2.15 | ❌ |
| 「图片」 | white / pink-500 | 3.53 | ❌ |
| 「文摘」 | white / violet-500 | 4.23 | ❌ |
| 「言论」 | white / orange-500 | 2.80 | ❌ |
| 「全部」 | white / slate-800 | 14.63 | ✅ |
| 页脚版权 | slate-400 / white | 2.56 | ❌ |
| 卡片 tag chip | slate-500 / slate-100 | 4.34 | ❌ |
| 日期徽章 | slate-500 / slate-50 | 4.55 | ✅ |
| 卡片摘要 | slate-600 / white | 7.58 | ✅ |

**其他 a11y 实测**：
- 已选标签的删除按钮：`textContent=''`、无 `aria-label`、SVG 无 `<title>` → **无可访问名称**；focus 后 `outline-style: none` → **焦点不可见**（`TagFilter.jsx:43-50`）。
- 卡片外链只有图标，`title="查看原文"` 充当可访问名（弱，且键盘聚焦时无可见焦点环，`ContentCard.jsx:21-32`）；搜索框清除按钮同样无 focus-visible 样式（`SearchBar.jsx:19-26`）。
- 弹窗"新窗口"链接、关闭按钮有文本/aria，✅。

**建议**：激活 pill 用 `-600/-700` 背景或加深文字（如 `text-slate-900`）；页脚改 `slate-500`；chip 改 `slate-600`；删除按钮补 `aria-label={\`移除标签 ${tag}\`}` + `focus-visible:ring-*`。

### FE-08 无日期的 32 张卡片渲染空徽章（P2）

- `formatDate` 对无效输入返回 `''`（`formatDate.js:14` 兜底正确），但 `ContentCard.jsx:17-19` **无条件渲染** badge → 32 张卡出现 16×8px 的空灰块（`07-undated-card-empty-badge.png`，示例标题「宁夏沙坡头景区的巨型蒙眼雕塑」）。
- 且前端完全不排序，无 `created_time` 的 32 条（最新内容，id 172–203）沉在 143 条末尾；数据排序逻辑见 `scripts/generate-data.js` 的 `mergeIncremental`（数据侧问题归 Pipeline D-06）。
- **建议**：`{dateText && <span>…</span>}`；数据补齐后前端可按 `created_time` 倒序兜底排序（缺时间放最后并标注）。

### FE-09 无全局错误兜底（P2）

- `src/main.jsx:6-10` 没有 ErrorBoundary；`index.html` 没有 `<noscript>`。FE-P0-1 的白屏就是"JS 挂了什么都没有"的现实版本。
- 报告 iframe 无加载中/失败态：网络慢/文件不存在时只有长期空白。
- **建议**：`ReactDOM.createRoot(...).render(<ErrorBoundary><App/></ErrorBoundary>)`，兜底 UI 带"刷新"按钮；`<noscript>` 提示；iframe 加 loading 骨架与"在新窗口打开"链接。

### FE-10 派生状态与假加载态（P3）

- `filteredData` 作为 state + `useEffect` 里 `setFilteredData` → 每次输入至少两轮渲染；`filterData` 同时被 `useEffect` 依赖与列表重复声明（`App.jsx:53-79`）。可直接 `useMemo` 派生。
- Fuse 实测（Node，143 条）：索引 0.7ms、查询 2.3–7.5ms；143 张卡片的 React 渲染耗时未测（无 Lighthouse/Profiler）。**当前不是瓶颈**，但卡片到 500+ 时应按旧审计 F3 虚拟化。
- 加载态：数据同步，`isLoading` 只闪一帧 → 可删除或改为骨架屏逻辑（等真实异步）。
- 建议：`const filteredData = useMemo(...)`；输入 100–150ms 防抖（可选）；标签 key 用 `original_url`。

### FE-11 无效 ARIA / 列优先顺序（P3）

- `WaterfallGrid.jsx:10-12`：`role="group"` + `aria-posinset`/`aria-setsize` 不被支持 → 屏幕阅读器无收益；多列布局的 DOM 顺序仍是"逐列"，Tab 顺序与视觉行序不一致（旧审计 C2 未真正关闭）。
- 建议：要么改成列表语义（`role="list"/"listitem"` + 真实行优先 DOM），要么接受视觉顺序并移除无效属性；长期用 JS masonry/虚拟化解决。

### FE-12 CSS 重复与全局覆盖（P3）

- `src/App.css:1-19,36-59` 与 `src/index.css:16-37` 重复定义 `.waterfall-item`/`.tag-button`（同规则两处）；`.tag-button.active` 从未被添加（死代码）；`App.css` 的全局 `.grid { grid-template-columns: repeat(auto-fill, minmax(280px,1fr)) }` 会影响所有 `.grid` 使用处（当前被 Tailwind utilities 覆盖，属"靠顺序侥幸"）。
- 建议：删 `App.css` 的重复段与 `.grid` 全局规则；若保留 hover 效果，统一到 Tailwind（`hover:-translate-y-1`）避免两套 transform。

### FE-13 潜在崩溃与卡片可点击性（P3）

- `App.jsx:68`、`ContentCard.jsx:45` 直接 `item.tags.split(',')`，数据里一旦出现空 tags 会整页崩（`App.jsx:27-31` 自己却做了空值保护，说明契约不一致）。
- 卡片只有右上角图标可点，标题不可点；建议整卡可点或标题变链接，外链加 `aria-label`。

---

## 4. 线上版本特有（`origin/main` 新增的双视图 / 搜索页）

### FE-O1 搜索页"信息源卡片"永久禁用态（P1，功能级）

- **链路**：`App.jsx`（origin/main）`currentView` 切换到 `<Last30daysPage />`；`Last30daysPage.jsx:7` 持有 `query` 但**从未 set**（`22` 行 `<SearchHero />` 无 props，`28` 行 `<SourcesGrid query={query} />` 恒为 `''`）；`SearchHero.jsx:6` 自己又有一份 `query`。两份状态互不相通。
- **实测**：搜索视图 13 张卡全部 `opacity-60`；在 SearchHero 输入 `AI agent` 后仍是 13 张 `opacity-60`；`SourcesGrid` 用 `source.url.replace('{q}','')` 得到 `https://www.reddit.com/search/?q=` 这类空查询 URL，点击仍可跳转（看着禁用其实能点）。
- **证据**：lint `Last30daysPage.jsx:7 'setQuery' is assigned a value but never used`；实现计划 `docs/superpowers/plans/2026-09-03-…md` Task 6 的示例代码**本身就有这个缺陷**（`<SearchHero />` 无 props + 未使用的 setQuery），计划没有经过自洽性检查。
- **建议**：把 query 提升到 `Last30daysPage`，`SearchHero` 受控（`value/onChange` 由父传入），`SourcesGrid` 只读；或删除父级死状态，让 SourcesGrid 不依赖 query（并去掉永久 `opacity-60`）。
- **验收**：在 hero 输入词后，13 张卡恢复不透明、点击落到带关键词的搜索页；输入清空后回到初始态且卡片有明确禁用说明。

### FE-O2 Tab 状态 / URL / 历史（P1 体验，与 spec 决策相关）

- spec 明确"Tab 切换（无 URL 变化）"，因此**不是 bug 而是产品决策**；但审查结论是：该决策带来四类用户可见后果，需要显式确认：
  1. 无法分享/收藏"信息检索"页；刷新回"内容浏览"；
  2. 浏览器后退不切 Tab（可能直接退出站点）；
  3. 切换保留滚动位置：实测 `scrollY` 1200 在切换前后不变 → 从瀑布流中部切到搜索页会落在页面中部（本 run `scrollY=0` 是因为刚导航）；
  4. 状态策略不一致：浏览视图的筛选/搜索保留（state 在 App），搜索视图的输入随卸载丢失（实测 `claude code` 切走再切回变空）。
- **建议**（任选，需产品确认）：hash 路由 `#/browse`、`#/search`（最小改动、可分享、后退可用）；切换时 `window.scrollTo(0,0)`；搜索视图 query 提升到 App 或 `sessionStorage` 持久化。
- **验收**：`#/search` 可直接打开；后退键在两个视图间切换；切换后滚动到顶部；切回搜索页输入保留。

### FE-O3 Tab 语义与标题层级（P2）

- 两个 tab 只是 `<button>`：无 `role="tablist"/tab`、无 `aria-selected`/`aria-pressed`/`aria-controls`，屏幕阅读器无法知道当前视图（实测属性全为 null）。
- 搜索视图同时存在 2 个 `<h1>`（页头「观念棱镜」+ 页面「信息检索」），标题层级重复。
- **建议**：按 ARIA tabs 模式补齐（或至少 `aria-pressed`）；页面级标题降为 `h2`（页头保留唯一 `h1`）。

### FE-O4 SearchHero 交互/可访问性（P2）

- 输入框只有 placeholder、无 `<label>`/`aria-label`；清除按钮只有图标、无名称（实测 `aria-label=null`）；
- 无 `<form>` → **Enter 无任何反应**（实测 `<form>` 数 0）；跨源搜索场景里"输入完按回车"是强预期；
- spec 要求"输入时实时更新 URL 预览"**未实现**（实测页面无 URL 预览元素）；
- 无 `maxLength`/长度校验（超长关键词会拼进 13 个 URL）。
- **建议**：`aria-label="跨源搜索关键词"`；清除按钮 `aria-label="清除关键词"`；包一层 `<form onSubmit>` 聚焦到第一个平台或直接打开默认源；按 spec 补 URL 预览（或明确砍掉并更新 spec）；`maxLength={100}` + trim。

### FE-O5 `window.open` 取代链接（P2）

- `SearchHero.jsx:9`、`SourcesGrid.jsx:6` 都是 `window.open(url, '_blank')`：无 `noopener/noreferrer`（新页面可通过 `window.opener` 反控本站）、不支持中键/右键/复制链接/浏览器"在新标签打开"、无链接语义与键盘原生行为。
- **建议**：改为 `<a href target="_blank" rel="noopener noreferrer">`（卡片整体做链接、内部不再放交互元素），既解决安全又拿到原生行为；若必须 JS，加 `window.open(url,'_blank','noopener,noreferrer')`。

### FE-O6 arXiv 链接参数错误（P2，外链正确性）

- `last30days-sources.js:51`：`https://arxiv.org/search/?search_query={q}`；spec 写 `search={q}`；实测两者都**不会**执行搜索（页面无结果），正确格式是 `https://arxiv.org/search/?searchtype=all&query={q}`（实测返回 187,658 条结果）。
- 其余 12 个平台的模板抽查与常见用法一致（Reddit `search/?q=`、YouTube `results?search_query=`、GitHub `search?q=`、Bing/DDG `?q=` 等）；Polymarket 等 SPA 无法离线验证，标注为未验证。
- **建议**：修 URL 模板；加一条"外链模板必须包含 `{q}` 且能被实际解析"的轻量测试（可只做字符串断言）。

### FE-O7 SourcesGrid 结构与禁用态（P3）

- `<button>` 内包 `<h3>`/`<p>`（按钮内容模型只允许 phrasing content）→ 标题不会被 AT 识别，也是无效 HTML；
- 无 query 时只是 `opacity-60`，仍可点击且无说明；`source.color` 的 6 组条件类里没有兜底（新增颜色会没有背景）；
- `nameCn` 13 个字段全未使用。
- **建议**：卡片改 `<a>` + 普通 `<div>/<h3>/<p>`；无 query 时 `aria-disabled` + 提示"输入关键词后再点击"；颜色映射改查表并给默认值；删除未用字段或接入 UI。

### FE-O8 移动端页头挤压（P3）

- 375px 实测：header 97px；品牌块 191×64（`h1`「观念棱镜」换 2 行，高 64）；tab 区 136×64（两个按钮各 56px、文字换 2 行）；`scrollWidth=375` 无横向溢出。
- 本地版本（无双 tab）同一视口 header 73px、单行，对比明显。
- **建议**：品牌副标题 `hidden sm:block`；tab 文案移动端缩短（"浏览"/"检索"）或只留图标 + `aria-label`；`h1` 加 `whitespace-nowrap`。见 `08-mobile-header-wrap.png`。

### FE-O9 线上版本 lint 失败且 CI 不跑 lint（P2）

- `eslint src scripts`（origin/main）→ exit 1：`Last30daysPage.jsx:7`（未使用 setQuery）、`PhilosophySection.jsx:59` ×2（未转义引号）；build 仍然成功 → 坏代码直接部署。
- `deploy.yml` 只有 `npm install` + `npm run build` + 发布；`npm run lint` 的 `--max-warnings=999` 还会吞掉所有 warning。
- **建议**：CI 加 `npm run lint`（去掉 `--max-warnings=999`，改为 `--max-warnings=0`）；与 Sentinel 的 P0 门禁设计合并。
- 注：本轮测试与门禁问题另见 `testing-quality.md`，这里只记录"线上代码当前不绿"。

### FE-O10/O11 体积与死代码（P3）

- 线上版本 JS 310,041B（gzip 106,288）、CSS 35,427B（gzip 6,370）；本地版本 297,388B / 29,671B——新增两视图成本 +12,653B raw（+2.6KB gzip），可接受。
- `static-data.js` 114,102B 直接内联进主 chunk（占线上 JS 约 37%）：**每次内容更新都会改变主 chunk 文件名**，React/Fuse 缓存全失效；数据改用 `import()` 或作为独立资源可更好利用缓存（当前站点规模不必急做）。
- 部署产物 318,698B 与本地干净构建 310,041B 差 +2.8%，且无 lockfile（`npm install`）→ 产物不可字节复现（供应链侧另见 Aegis H-2）。
- 死代码：`nameCn`（13 处）、`buildAllSearchUrls` 的 `sourceIds` 参数。

---

## 5. 旧审计（2026-07-30）已修复项核对（不重复报告）

| 旧编号 | 状态 | 证据 |
|---|---|---|
| B1 `sqliteReader.js` + `sql.js` 依赖 | ✅ 已删（sql.js 仅作 `generate-data.js` 的 devDependency） | `src/utils/` 无该文件 |
| B3 Fuse 索引不存在字段 | ✅ `keys: ['title','summary']` | `App.jsx:44-52` |
| B4 数据 JS 混淆 | ✅ 普通 `export default [...]`（114KB 纯数据） | `src/assets/static-data.js:1` |
| C1 重复 formatDate | ✅ 已抽 `src/utils/formatDate.js` 并三处复用 | grep |
| C3 filterData 未 memo | ✅ 已 `useCallback`（但派生状态反模式仍在，见 FE-10） | `App.jsx:53-76` |
| D1 弹窗动画类无效 | ✅ 已装 `tailwindcss-animate` 并生效 | 编译 CSS 含 `animate-in`/`animation-duration:.2s` |
| D2 `lang="en"` | ✅ `lang="zh-CN"` | `index.html:2` |
| D3 标签按钮缺 `aria-pressed` | ✅ 已加（含分类） | `TagFilter.jsx:21`、`CategoryFilter.jsx:13,33` |
| D4 搜索框无 label | ✅ `aria-label="搜索内容"` | `SearchBar.jsx:15` |
| D6 焦点环不统一 | ◐ 分类/标签/搜索框/弹窗按钮已统一为 `focus-visible:ring-*`；**但卡片外链图标、搜索清除按钮、已选标签删除按钮仍无可见焦点**（FE-07） | `ContentCard.jsx:21-32`、`SearchBar.jsx:19-26`、`TagFilter.jsx:43-50` |
| D5 iframe sandbox 无效 | ⚠️ 已改为 `sandbox=""`，但**过度收紧**导致报告功能失效（FE-05/原 D5 的"修复"引入新问题） | `ReportModal.jsx:79` |
| C2 瀑布流 DOM 顺序 | ◐ 加了 `aria-posinset/setsize`，但语义无效且顺序问题未解（FE-11） | `WaterfallGrid.jsx:10-12` |
| E1/E2/E3 | ✅ gitignore 注释、lint 脚本、去 manualChunks 均已完成 | — |

---

## 6. 与其他审计报告的重叠与分工（避免重复报告）

- **重复 id 与搜索多显示**：`testing-quality.md` D-05 已从数据/用例角度记录；本报告补充**前端根因**（`idSet` 过滤 + `key` 不稳定）与浏览器实测的"计数不一致/残留卡片"现象与修复方案（§3 FE-02）。
- **32 条无 `created_time`**：`data-pipeline.md` / `testing-quality.md` D-06 已覆盖数据侧；本报告只补前端表现（空徽章、不排序）与兜底建议（§3 FE-08）。
- **报告页 CDN JS / sandbox 安全**：`security-privacy.md` M-1 已从 XSS/供应链角度分析；本报告给功能影响（图表空）+ 与安全建议兼容的修复选项（§3 FE-05）。
- **CI 门禁 / 假绿**：`testing-quality.md` P0 门禁设计；本报告只补"origin/main 当前 lint 不通过、deploy 不跑 lint"（FE-O9）。
- **部署白屏**（FE-P0-1）目前仅本报告记录；建议与 `data-pipeline.md`（发布新鲜度）一并纳入发布 checklist。

---

## 7. 假设、局限、风险

- **假设**：`https://dllen.github.io/deepthink/` 就是本项目生产 URL（仓库 `dllen/deepthink`、`deploy.yml` 发布 `gh-pages`、分支无 `CNAME`）。若实际有自定义域名/反向代理，FE-P0-1 的影响面需重新评估（但"根绝对路径 + 无 base"本身仍是缺陷）。
- **局限**：
  - 未做 Lighthouse / axe / INP 等定量性能与自动化 a11y 扫描（环境无对应工具链）；交互耗时只测了 Fuse（2.3–7.5ms）与构建体积，**未测 143 卡片的渲染/首屏耗时**。
  - 弹窗内 iframe 因 opaque origin 无法读取其 DOM，图表是否渲染是通过"直开报告 vs 弹窗"两张截图 + sandbox 语义判定的，未逐像素比对。
  - 移动端结论来自 Chrome 375×812 仿真，未在真机/微信内置浏览器验证；iOS Safari 的 `body overflow` 锁滚、`new Date('YYYY-MM-DD HH:mm:ss')` 解析差异未实测（后者可能让 `formatDate` 返回空，属潜在风险）。
  - 线上版本是"导出 origin/main 到 /tmp 后本地构建 + 本地托管"测试的，不是直接测生产；生产当前是白屏（FE-P0-1）。
- **风险**：修复 FE-02（key 改 `original_url`）会让 React 在筛选/更新时重建卡片，需回归收起/展开等交互（当前无此类交互，风险低）；修复 FE-05 放开 `allow-scripts` 需与 Aegis 确认安全边界；`base` 变更会同时影响报告静态资源路径，需一次改全。

---

## 8. 建议优先级（供排期，不含实施）

1. **P0**：FE-P0-1 部署 `base` + favicon + 报告路径 → 重新部署复验线上。
2. **P1**：
   - FE-02 搜索/重复 id（前端过滤 + key 先兜底，数据侧并行）；
   - FE-03 sticky 筛选器（合并/移动端折叠）；
   - FE-04 空态清除全部；
   - FE-05 报告弹窗脚本（`allow-scripts` + 自托管 Chart.js）；
   - FE-O1 搜索页 query 提升；
   - FE-O2 URL/滚动/状态策略（需产品确认 hash 路由）。
3. **P2**：FE-06、FE-07、FE-08、FE-09、FE-O3、FE-O4、FE-O5、FE-O6、FE-O9。
4. **P3**：FE-10 ~ FE-13、FE-O7、FE-O8、FE-O10/O11。

**建议的最小验收清单（前端回归）**：
- 搜「英伟达」：头部计数 === 卡片数（且无重复 key 警告）；
- 空态 → 点「清除所有筛选」→ 恢复 143；
- 桌面滚动到中部：分类筛选可点、两个筛选器不重叠；
- 375px：sticky 筛选区 ≤ 视口 30%，页头不换行/不溢出；
- 报告弹窗：图表、筛选、榜单与直开一致；Esc 关闭且焦点回到卡片；
- 搜索页：输入关键词后 13 张卡可用、点击落到带关键词的结果页；Tab 可分享/可后退（若采用 hash）。

---

## 附录：证据文件

- `assets/frontend/01-live-deploy-blank.png` — 线上 `/deepthink/` 白屏（#root 空）
- `assets/frontend/02-duplicate-key-stale-cards.png` — 头部「0 条内容」时残留 8 张旧卡片
- `assets/frontend/03-sticky-overlap-desktop.png` — 桌面双 sticky 重叠 83px
- `assets/frontend/04-mobile-sticky-filters.png` — 移动端吸附筛选器占 62% 视口
- `assets/frontend/05-report-modal-blank.png` — 弹窗内报告图表/榜单空白
- `assets/frontend/06-report-direct-rendered.png` — 直开同一报告的正常渲染
- `assets/frontend/07-undated-card-empty-badge.png` — 无日期卡片的空徽章
- `assets/frontend/08-mobile-header-wrap.png` — 线上版本 375px 页头换行
