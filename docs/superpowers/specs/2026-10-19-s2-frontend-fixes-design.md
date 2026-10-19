# S2 设计：前端线上缺陷修复

- **日期**：2026-10-19
- **状态**：已确认（两节设计经用户逐节确认）
- **依据审计**：[前端审计](../audits/2026-10-18/frontend.md)
- **范围**：前端 P1 缺陷 + 高价值 P2（可访问性、结构语义、错误兜底）；不引入路由库、不重写瀑布流、不做全量 URL 状态。

## 1. 背景

线上版本（`origin/main` 双视图）在前端审计中有 5 个 P1 与一组 P2：

- 信息检索页 `Last30daysPage` 的 `query` 状态从未被赋值，`SearchHero` 自持状态，13 张源卡永远收到空查询（lint 也报错）。
- Tab 视图无 URL 语义：刷新回浏览、无法分享信息检索页、切换丢搜索输入、保留滚动位置。
- 两个筛选器同为 `sticky top-24`，滚动时重叠 83px；移动端筛选区占视口 62%。
- 空态「清除所有筛选」只清标签，因搜索进入空态时按钮无效。
- 报告弹窗 `sandbox=""` 阻断报告页脚本，图表/表格空白。
- P2：弹窗无 dialog 语义与焦点管理；分类 pill 对比度不足；`window.open` 取代链接；arXiv 参数错误；`<button>` 包标题；移动端页头挤压；无 ErrorBoundary/noscript；lint 3 个 error；CSS 重复。

S1 已在数据层解决：224 条 id 唯一（FE-02 重复 key 根因消失）、全部条目有 `created_time`（FE-08 空日期消失）。

## 2. 决策

| 决策 | 选择 |
|---|---|
| 视图状态 | URL hash（`#/browse`、`#/search`），不引入 React Router |
| 搜索页 query | 上提到 `App`，切 Tab 不丢；暂不进 URL |
| 浏览筛选状态 | 保持组件内 state，不进 URL（后续再做） |
| 数据派生 | `filteredData` 用 `useMemo`；删除 `items`/`filteredData`/`isLoading` state 与二次 effect |
| Sticky | 分类 + 标签合并为一个 sticky 容器；`<md` 不吸附 |
| 空态 | 新增 `clearAllFilters()`，清标签 + 分类 + 搜索词 |
| 弹窗 sandbox | `allow-scripts`（不放开 `allow-same-origin`），保证报告脚本可运行 |
| 弹窗可访问性 | `role="dialog"` + `aria-modal` + 焦点进入/循环/归还 |
| Enter 行为 | SearchHero 用 `<form>`，Enter 默认打开 DuckDuckGo 搜索（源列表已有 DDG） |
| 源卡链接 | `<a target="_blank" rel="noopener noreferrer">`；无 query 时链到平台首页 |
| 标题层级 | 品牌词改非 `h1`；浏览视图 sr-only `h1`，信息检索页保留 `h1` |
| 瀑布流语义 | 去无效 `aria-posinset/setsize`，改 `role="list"/"listitem"` |
| 错误兜底 | `ErrorBoundary` 包裹 `App`；`index.html` 加 `<noscript>`；favicon 换本地文件 |
| 依赖 | 不新增任何 npm 依赖 |

## 3. 设计

### 3.1 视图与状态

- `src/App.jsx`
  - `readViewFromHash()`：`#/search` → `'search'`，其他/空 → `'browse'`。
  - `useEffect` 监听 `hashchange`；Tab 点击写 `window.location.hash`；非法 hash 用 `history.replaceState` 归一为 `#/browse`。
  - 视图切换后 `window.scrollTo({ top: 0 })`。
  - 搜索页关键词状态 `searchPageQuery` 上提到 `App`，传入 `Last30daysPage`。
  - 删除 `items`、`filteredData`、`isLoading` state；`tags`/`categoryCounts` 用 `useMemo` 从 `data` 派生；`filteredData` 用 `useMemo` 依赖 `[data, searchQuery, selectedCategory, selectedTags, fuse]`。
  - `clearAllFilters()`：清 `selectedTags`、`selectedCategory`、`searchQuery`。

### 3.2 筛选区与布局

- `src/App.jsx`：分类筛选器与标签筛选器包进一个 `sticky top-20 z-40` 容器（背景 `bg-slate-50/95 backdrop-blur`），容器在 `max-md` 下 `static`；内部两层之间保留间距，不再各自 sticky。
- 空态按钮调用 `clearAllFilters`。

### 3.3 信息检索页

- `src/components/Last30daysPage.jsx`：接收 `query`/`onQueryChange`，传给 `SearchHero` 与 `SourcesGrid`；删除本地死状态。
- `src/components/SearchHero.jsx`：
  - 受控输入（`value={query}`、`onChange`）。
  - 外层 `<form onSubmit>`：query 非空时 `window.open('https://duckduckgo.com/?q=' + encodeURIComponent(query), '_blank', 'noopener,noreferrer')`，并 `preventDefault`。
  - 输入 sr-only `<label>`，清除按钮 `aria-label="清除搜索词"`。
  - 快捷平台按钮改为 `<a href=... target="_blank" rel="noopener noreferrer">`。
- `src/components/SourcesGrid.jsx`：
  - 卡片改为 `<a>`，保留现有视觉；query 为空时 `href` 为平台首页（模板去掉 `{q}`），并可点击，去掉 `opacity-60` 与"禁用"观感；顶部提示"输入关键词后点击卡片打开该平台搜索结果"。
- `src/utils/searchUtils.js`：`buildAllSearchUrls` 去掉未使用的 `sourceIds` 参数；`buildSearchUrl` 保持单一 `{q}` 替换。
- `src/assets/last30days-sources.js`：arXiv 模板改为 `https://arxiv.org/search/?searchtype=all&query={q}`；删除 13 处未使用的 `nameCn`。

### 3.4 报告弹窗

- `src/components/ReportModal.jsx`
  - iframe：`sandbox="allow-scripts"`、`title`、`onLoad`、`onError`；加载中显示遮罩 + 文案，失败显示"报告加载失败"提示。
  - 容器：`role="dialog"`、`aria-modal="true"`、`aria-labelledby` 指向标题 id。
  - 打开时记录 `document.activeElement` 并聚焦关闭按钮；`keydown` 处理 Tab 循环（焦点限制在弹窗内可聚焦元素）；关闭时把焦点还原给打开前的元素。Esc/遮罩关闭行为保留。

### 3.5 可访问性与语义

- Tab：外层 `role="tablist"`，按钮 `role="tab"` + `aria-selected` + `aria-controls`，内容面板 `role="tabpanel"` + `aria-labelledby`。
- 标题层级：品牌 `<h1>` 改 `<div>`；浏览视图顶部加 `<h1 className="sr-only">观念棱镜</h1>`；信息检索页保留现有 `h1`。
- 对比度：
  - `src/utils/categories.js`：`pill` 从 `bg-*-500` 改为 `bg-*-700`（白字对比度达标）。
  - 页脚文案 `text-slate-400` → `text-slate-500`。
  - 卡片标签 chip `text-slate-500` → `text-slate-600`。
  - 标签删除按钮：加 `aria-label={'移除标签 ' + tag}` 与 `focus-visible` ring。
- 瀑布流：`WaterfallGrid` 外层 `role="list"`，每项 `role="listitem"`，删除 `aria-posinset/aria-setsize`。
- 卡片：标题改为 `<a href={original_url}>`（`rel="noopener noreferrer"`），保留右上角外链图标；`(item.tags || '')` 空值保护（`App.jsx` 的标签解析与 `ContentCard` 的 tags 渲染）。
- `src/App.jsx`：`Data` 中无 tags 的行不再导致崩溃。

### 3.6 兜底、移动端与样式

- 新增 `src/components/ErrorBoundary.jsx`（class 组件），`src/main.jsx` 用它包 `<App />`，fallback 为可读错误页 + 刷新按钮。
- `index.html`：加 `<noscript>`；favicon 改为 `/logo.svg`；新增 `public/logo.svg`（从 `src/assets/logo.svg` 复制）。
- `src/App.jsx` 页头：小屏隐藏副标题（`hidden sm:block`），Tab 文案小屏缩小，`py-3` 收紧，375px 单行。
- CSS 去重：
  - `.waterfall-item` / `.tag-button` 只保留一处（`index.css` 保留基础样式，`App.css` 删除重复与死规则 `.tag-button.active`、全局 `.grid` 覆盖、重复 media query）。
- lint：`PhilosophySection.jsx` 两处引号改为 `{'"'}`；`setQuery` 未使用随状态上提消失。

## 4. 验收

- `npm run lint` → 0 problem。
- `npm run build` 通过；`npm run check:data` 仍通过（S2 不改数据）。
- 本地 `npm run preview` 可访问；人工/浏览器验证：
  1. 信息检索页输入关键词 → 13 张源卡链接包含该关键词；arXiv 链接能打开搜索结果。
  2. Tab 切换写入 `#/browse` / `#/search`，刷新与后退保持视图；切走再切回搜索词仍在。
  3. 桌面滚动时分类与标签筛选不重叠；375px 下筛选区不吸附、页头单行。
  4. 搜索无结果 → 点「清除所有筛选」→ 搜索词、分类、标签全清。
  5. 报告弹窗内图表与表格渲染（与直开报告一致）；Esc 关闭后焦点回到触发卡片。
- 部署后由 Pixel 用 Chrome 在 1440×900 与 375×812 复验以上 5 项并留存截图。

## 5. 风险与回滚

| 风险 | 缓解 |
|---|---|
| hash 路由改变分享链接形态 | 保留旧 URL（无 hash）默认 browse；`replaceState` 归一，不新增历史条目 |
| iframe `allow-scripts` 的安全面 | 不放开 `allow-same-origin`；报告为自有静态页；与 Aegis M-1 结论一致 |
| 焦点陷阱实现不完整 | 只在弹窗打开时启用；实现后手动 Tab/Esc 验证 |
| 移动端布局回归 | 375px 视口截图核对；不引入横向滚动 |
| 大量小改分散 | 按组件分任务提交，每步 lint + build，最后由 Pixel 复验 |

## 6. 不在范围

- 分类/标签/搜索词进 URL（全量状态路由）。
- 瀑布流 DOM 顺序与视觉顺序不一致的重写。
- 前端测试框架引入与 CI lint 门禁（S5/S4）。
- 内容清理（抓取噪声、周刊重复）。
- 构建可复现性、`base` 与生产入口（S4）。

## 7. 文件清单

新增：

- `src/components/ErrorBoundary.jsx`
- `public/logo.svg`

修改：

- `src/App.jsx`
- `src/components/Last30daysPage.jsx`、`SearchHero.jsx`、`SourcesGrid.jsx`、`ReportModal.jsx`、`WaterfallGrid.jsx`、`ContentCard.jsx`、`TabFilter`（现为 `TagFilter.jsx`）、`CategoryFilter.jsx`、`PhilosophySection.jsx`
- `src/utils/categories.js`、`src/utils/searchUtils.js`
- `src/assets/last30days-sources.js`
- `src/main.jsx`、`index.html`
- `src/App.css`、`src/index.css`
