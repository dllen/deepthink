# S2 前端缺陷修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复线上前端 5 个 P1 缺陷与关键 P2 可访问性问题，不引入新依赖、不改数据。

**Architecture:** 视图状态用 URL hash 承载；搜索页 query 上提到 `App`；`filteredData` 改成 `useMemo` 派生；筛选区合并为单个 sticky 容器；搜索页改受控组件 + 原生链接；报告弹窗放开脚本沙箱并补齐 dialog 语义；最后清理 CSS 与 lint。

**Tech Stack:** React 18、Vite 4、TailwindCSS 3、原生 DOM API（hash/history/焦点管理）。

**Spec:** `docs/superpowers/specs/2026-10-19-s2-frontend-fixes-design.md`

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `src/App.jsx` | 视图 hash、query 上提、派生数据、筛选区布局、Tab 语义、空态 |
| `src/components/Last30daysPage.jsx` | 搜索页容器：受控 query 透传 |
| `src/components/SearchHero.jsx` | 受控搜索框 + form/Enter + 可访问标签 |
| `src/components/SourcesGrid.jsx` | 源卡改原生链接，空查询链到平台首页 |
| `src/components/ReportModal.jsx` | sandbox、loading/error、dialog 语义、焦点管理 |
| `src/components/ErrorBoundary.jsx` | 全局错误兜底（新增） |
| `src/components/WaterfallGrid.jsx` / `ContentCard.jsx` | list 语义、标签空值保护、标题链接 |
| `src/components/TagFilter.jsx` / `CategoryFilter.jsx` | 删除按钮名称、对比度类名 |
| `src/utils/categories.js` / `searchUtils.js` | 激活 pill 配色、清理未用参数 |
| `src/assets/last30days-sources.js` | arXiv 模板、删除 `nameCn` |
| `src/main.jsx` / `index.html` / `public/logo.svg` | ErrorBoundary、noscript、favicon |
| `src/App.css` / `src/index.css` | 去重与死规则清理 |

---

## Task 1: 视图 hash + 搜索页 query 上提

**Files:**
- Modify: `src/App.jsx`
- Modify: `src/components/Last30daysPage.jsx`

- [ ] **Step 1: App 增加视图 hash 逻辑**

在 `App.jsx` 顶部、组件外加：

```js
const VIEW_BROWSE = 'browse';
const VIEW_SEARCH = 'search';
const VIEW_HASH = { [VIEW_BROWSE]: '#/browse', [VIEW_SEARCH]: '#/search' };

function readViewFromHash() {
  const raw = window.location.hash.replace(/^#\/?/, '');
  return raw === VIEW_SEARCH ? VIEW_SEARCH : VIEW_BROWSE;
}
```

组件内替换原 `currentView` state：

```js
const [currentView, setCurrentView] = useState(readViewFromHash);
const [searchPageQuery, setSearchPageQuery] = useState('');

useEffect(() => {
  const syncFromHash = () => setCurrentView(readViewFromHash());
  window.addEventListener('hashchange', syncFromHash);
  if (window.location.hash !== VIEW_HASH[readViewFromHash()]) {
    window.history.replaceState(null, '', VIEW_HASH[readViewFromHash()]);
  }
  return () => window.removeEventListener('hashchange', syncFromHash);
}, []);

const switchView = (view) => {
  if (view === currentView) return;
  window.location.hash = VIEW_HASH[view];
  window.scrollTo({ top: 0, behavior: 'auto' });
};
```

Tab 按钮 `onClick={() => switchView(VIEW_BROWSE)}` / `switchView(VIEW_SEARCH)`。

- [ ] **Step 2: 把搜索页 query 传给 Last30daysPage**

渲染处改为：

```jsx
<Last30daysPage query={searchPageQuery} onQueryChange={setSearchPageQuery} />
```

- [ ] **Step 3: Last30daysPage 去掉死状态，改受控**

`src/components/Last30daysPage.jsx` 整体改为：

```jsx
import SearchHero from './SearchHero';
import SourcesGrid from './SourcesGrid';
import PhilosophySection from './PhilosophySection';

const Last30daysPage = ({ query, onQueryChange }) => {
  return (
    <div className="py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500 mb-2">
          信息检索
        </h1>
        <p className="text-slate-500">跨越 13 个平台，追踪真实的人类声音</p>
      </div>

      <SearchHero query={query} onQueryChange={onQueryChange} />
      <PhilosophySection />
      <SourcesGrid query={query} />
    </div>
  );
};

export default Last30daysPage;
```

- [ ] **Step 4: 验证**

Run: `npm run lint 2>&1 | tail -20`（此时 `Last30daysPage` 的 setQuery 错误应消失，剩余 2 个 PhilosophySection 引号错误）
Run: `npm run build`
Expected: build 成功。

- [ ] **Step 5: 提交**

```bash
git add src/App.jsx src/components/Last30daysPage.jsx
git commit -m "fix(frontend): drive view state from URL hash and lift search query"
```

---

## Task 2: 派生数据用 useMemo + 空态全清

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: 删除假加载与派生 state**

删除 `items`、`filteredData`、`isLoading` 三个 `useState`，以及初始化它们的 `useEffect`。改为：

```js
const [tags, setTags] = useState([]);
const [selectedTags, setSelectedTags] = useState([]);
const [selectedCategory, setSelectedCategory] = useState(null);
const [searchQuery, setSearchQuery] = useState('');
const [categoryCounts, setCategoryCounts] = useState({});
```

在 `App` 顶部用 `useMemo` 直接从 `data` 派生 tags 与计数：

```js
const { tags, categoryCounts } = useMemo(() => {
  const tagSet = new Set();
  const counts = {};
  for (const item of data) {
    if (item.tags) {
      for (const tag of item.tags.split(',')) {
        const trimmed = tag.trim();
        if (trimmed) tagSet.add(trimmed);
      }
    }
    if (item.category) counts[item.category] = (counts[item.category] || 0) + 1;
  }
  return { tags: Array.from(tagSet), categoryCounts: counts };
}, []);
```

删除对应的 `setTags`/`setCategoryCounts`/`setItems`/`setFilteredData`/`setIsLoading` 调用。

- [ ] **Step 2: filteredData 用 useMemo**

保留 `fuse = useMemo(...)`，把 `filterData` 与 effect 替换为：

```js
const filteredData = useMemo(() => {
  let result = data;

  if (selectedCategory) {
    result = result.filter((item) => item.category === selectedCategory);
  }

  if (searchQuery.trim()) {
    const idSet = new Set(fuse.search(searchQuery).map((r) => r.item.id));
    result = result.filter((item) => idSet.has(item.id));
  }

  if (selectedTags.length > 0) {
    result = result.filter((item) => {
      const itemTags = (item.tags || '').split(',').map((tag) => tag.trim());
      return selectedTags.some((tag) => itemTags.includes(tag));
    });
  }

  return result;
}, [data, fuse, searchQuery, selectedCategory, selectedTags]);
```

删除原 `filterData` 的 `useCallback` 与 `useEffect`。

- [ ] **Step 3: 空态全清**

```js
const clearAllFilters = () => {
  setSelectedTags([]);
  setSelectedCategory(null);
  setSearchQuery('');
};
```

空态按钮 `onClick={clearAllFilters}`；标签筛选器仍用 `clearFilters`（只清标签）或统一用 `clearAllFilters`，二选一，保持按钮语义一致。

- [ ] **Step 4: 删除 loading 分支**

去掉 `isLoading ? (...spinner...) : (...)`，直接渲染 `<WaterfallGrid data={filteredData} />`；空态判断保留 `filteredData.length === 0`。

- [ ] **Step 5: 验证**

Run: `npm run lint`（应仍只剩 PhilosophySection 2 个引号错误）
Run: `npm run build`
Expected: build 成功。

- [ ] **Step 6: 提交**

```bash
git add src/App.jsx
git commit -m "refactor(frontend): derive filtered data with useMemo and clear all filters"
```

---

## Task 3: 筛选区合并为单个 sticky

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: 合并筛选容器**

把两个独立的 `sticky top-24` div 替换为：

```jsx
<div className="mb-8 sticky top-20 z-40 max-md:static bg-slate-50/95 backdrop-blur-sm rounded-2xl">
  <div className="mb-3">
    <CategoryFilter
      selectedCategory={selectedCategory}
      onCategorySelect={setSelectedCategory}
      counts={categoryCounts}
    />
  </div>
  <TagFilter
    tags={tags}
    selectedTags={selectedTags}
    onTagToggle={toggleTag}
    onClearFilters={clearAllFilters}
  />
</div>
```

- [ ] **Step 2: 验证**

Run: `npm run build`
Expected: 成功。

- [ ] **Step 3: 提交**

```bash
git add src/App.jsx
git commit -m "fix(frontend): merge sticky filter bars into one container"
```

---

## Task 4: SearchHero 受控 + form/Enter + 可访问标签

**Files:**
- Modify: `src/components/SearchHero.jsx`
- Modify: `src/utils/searchUtils.js`

- [ ] **Step 1: SearchHero 改受控并加 form**

组件签名改为 `const SearchHero = ({ query, onQueryChange }) => {`，删除内部 `useState`。输入框：

```jsx
<form
  onSubmit={(event) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    window.open(
      `https://duckduckgo.com/?q=${encodeURIComponent(trimmed)}`,
      '_blank',
      'noopener,noreferrer',
    );
  }}
>
  <label htmlFor="search-hero-input" className="sr-only">跨源搜索关键词</label>
  <input
    id="search-hero-input"
    type="text"
    value={query}
    onChange={(event) => onQueryChange(event.target.value)}
    placeholder="输入关键词，跨源搜索..."
    className="..."
  />
  ...
  <button type="submit" className="sr-only">搜索</button>
</form>
```

清除按钮加 `aria-label="清除搜索词"`；快捷平台按钮改为链接：

```jsx
<a
  key={source.id}
  href={searchUrls[source.id]}
  target="_blank"
  rel="noopener noreferrer"
  className="..."
>
  {source.name}
</a>
```

- [ ] **Step 2: searchUtils 清理未用参数**

```js
export const buildAllSearchUrls = (query) => {
  return last30daysSources.reduce((acc, source) => {
    acc[source.id] = buildSearchUrl(query, source.url);
    return acc;
  }, {});
};
```

- [ ] **Step 3: 验证**

Run: `npm run build`
Expected: 成功；无 `setQuery` 相关 lint 报错。

- [ ] **Step 4: 提交**

```bash
git add src/components/SearchHero.jsx src/utils/searchUtils.js
git commit -m "fix(frontend): make search hero controllable with working submit"
```

---

## Task 5: SourcesGrid 原生链接 + arXiv 修正 + 数据清理

**Files:**
- Modify: `src/components/SourcesGrid.jsx`
- Modify: `src/assets/last30days-sources.js`

- [ ] **Step 1: 卡片改链接**

```jsx
{last30daysSources.map((source) => {
  const searchUrl = query.trim()
    ? buildSearchUrl(query, source.url)
    : source.url.replace('{q}', '');
  return (
    <a
      key={source.id}
      href={searchUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="group block text-left bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300 overflow-hidden cursor-pointer"
    >
      {/* 保留原卡片内容，去掉 button 语义 */}
    </a>
  );
})}
```

删除 `handleCardClick` 与 `opacity-60`。在网格上方加提示：

```jsx
<p className="text-xs text-slate-400 mb-3">
  输入关键词后点击卡片，直接打开该平台的搜索结果
</p>
```

- [ ] **Step 2: 修 arXiv 模板、删 nameCn**

`last30days-sources.js`：arXiv 的 `url` 改为 `'https://arxiv.org/search/?searchtype=all&query={q}'`；删除全部 `nameCn` 字段（13 处）。

- [ ] **Step 3: 验证**

Run: `grep -n "nameCn" src/`（应无输出）
Run: `npm run build`
Expected: 成功。

- [ ] **Step 4: 提交**

```bash
git add src/components/SourcesGrid.jsx src/assets/last30days-sources.js
git commit -m "fix(frontend): render source cards as links and correct arXiv search"
```

---

## Task 6: 报告弹窗 sandbox、loading、dialog 语义与焦点

**Files:**
- Modify: `src/components/ReportModal.jsx`
- Modify: `src/components/ReportsPanel.jsx`（如有需要，传 opener ref）

- [ ] **Step 1: 弹窗状态与焦点管理**

在 `ReportModal` 内新增：

```js
const [status, setStatus] = useState('loading'); // loading | ready | error
const dialogRef = useRef(null);
const closeRef = useRef(null);
const openerRef = useRef(null);

useEffect(() => {
  openerRef.current = document.activeElement;
  closeRef.current?.focus();
  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      onClose();
      return;
    }
    if (event.key !== 'Tab' || !dialogRef.current) return;
    const focusables = dialogRef.current.querySelectorAll(
      'a[href], button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])',
    );
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
  document.addEventListener('keydown', onKeyDown);
  document.body.style.overflow = 'hidden';
  return () => {
    document.removeEventListener('keydown', onKeyDown);
    document.body.style.overflow = '';
    openerRef.current?.focus?.();
  };
}, [onClose]);
```

容器：

```jsx
<div
  ref={dialogRef}
  role="dialog"
  aria-modal="true"
  aria-labelledby="report-modal-title"
  className="relative w-full max-w-6xl h-[90vh] ..."
>
  <h2 id="report-modal-title" ...>{report.title}</h2>
  ...
  <div className="relative flex-1 bg-white">
    {status === 'loading' && (
      <div className="absolute inset-0 flex items-center justify-center text-slate-500">
        报告加载中…
      </div>
    )}
    {status === 'error' && (
      <div className="absolute inset-0 flex items-center justify-center text-slate-500">
        报告加载失败，请尝试「新窗口」打开
      </div>
    )}
    <iframe
      src={report.path}
      title={report.title}
      className="w-full h-full border-0"
      sandbox="allow-scripts"
      onLoad={() => setStatus('ready')}
      onError={() => setStatus('error')}
    />
  </div>
</div>
```

关闭按钮加 `ref={closeRef}`。

- [ ] **Step 2: 验证**

Run: `npm run build`
Expected: 成功。

- [ ] **Step 3: 提交**

```bash
git add src/components/ReportModal.jsx src/components/ReportsPanel.jsx
git commit -m "fix(frontend): allow report scripts and add dialog accessibility"
```

---

## Task 7: Tab 语义与标题层级

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: Tab 改 ARIA**

```jsx
<div role="tablist" aria-label="视图切换" className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
  <button
    role="tab"
    id="tab-browse"
    aria-selected={currentView === 'browse'}
    aria-controls="panel-browse"
    onClick={() => switchView(VIEW_BROWSE)}
    className="..."
  >
    内容浏览
  </button>
  <button
    role="tab"
    id="tab-search"
    aria-selected={currentView === 'search'}
    aria-controls="panel-search"
    onClick={() => switchView(VIEW_SEARCH)}
    className="..."
  >
    信息检索
  </button>
</div>
```

主内容区按视图包 panel：

```jsx
<div id="panel-browse" role="tabpanel" aria-labelledby="tab-browse" hidden={currentView !== 'browse'}>
  ...
</div>
<div id="panel-search" role="tabpanel" aria-labelledby="tab-search" hidden={currentView !== 'search'}>
  <Last30daysPage ... />
</div>
```

（保持现有条件渲染也可，但需给当前 panel 正确的 `role`/`aria-labelledby`。）

- [ ] **Step 2: 标题层级**

品牌 `<h1>` 改为 `<div className="text-2xl font-bold ...">观念棱镜</div>`；在浏览 panel 顶部加 `<h1 className="sr-only">观念棱镜 · 内容浏览</h1>`；信息检索页原有 `<h1>信息检索</h1>` 保留。

- [ ] **Step 3: 验证**

Run: `npm run build`
Expected: 成功。

- [ ] **Step 4: 提交**

```bash
git add src/App.jsx
git commit -m "fix(frontend): add tab semantics and single h1 per view"
```

---

## Task 8: 对比度、标签删除按钮、瀑布流与卡片语义

**Files:**
- Modify: `src/utils/categories.js`
- Modify: `src/components/TagFilter.jsx`
- Modify: `src/components/WaterfallGrid.jsx`
- Modify: `src/components/ContentCard.jsx`
- Modify: `src/App.jsx`

- [ ] **Step 1: 激活 pill 用深色背景**

`categories.js` 中 `CATEGORY_STYLES` 的 `pill` 从 `bg-*-500` 改为 `bg-*-700`（例如 `'文章': { ..., pill: 'bg-indigo-700' }`），保持 `badge` 不变。逐个七个分类替换。

- [ ] **Step 2: 标签删除按钮可访问**

`TagFilter.jsx` 中每个标签的删除按钮（若有）加：

```jsx
aria-label={`移除标签 ${tag}`}
className="... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
```

若删除交互是整颗标签点击，则给按钮加 `aria-pressed={isSelected}` 或说明。

- [ ] **Step 3: 瀑布流改 list 语义**

`WaterfallGrid.jsx`：

```jsx
<div role="list" className="columns-1 md:columns-2 lg:columns-3 xl:columns-4 gap-6 space-y-6 px-2">
  {data.map((item) => (
    <div key={item.id} role="listitem" className="break-inside-avoid">
      <ContentCard item={item} />
    </div>
  ))}
</div>
```

- [ ] **Step 4: 卡片标题变链接、tags 空值保护**

`ContentCard.jsx`：

```jsx
<h3 className="...">
  <a
    href={item.original_url}
    target="_blank"
    rel="noopener noreferrer"
    className="hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
  >
    {item.title}
  </a>
</h3>
...
{(item.tags || '').split(',').filter(Boolean).map((tag, index) => (
  <span key={`${tag}-${index}`} ...>#{tag.trim()}</span>
))}
```

`App.jsx` 标签解析处同样用 `(item.tags || '')`。

- [ ] **Step 5: 页脚与 chip 对比度**

`App.jsx` 页脚 `text-slate-400` → `text-slate-500`；`ContentCard.jsx` 标签 chip `text-slate-500` → `text-slate-600`。

- [ ] **Step 6: 验证**

Run: `npm run build`
Expected: 成功。

- [ ] **Step 7: 提交**

```bash
git add src/utils/categories.js src/components/TagFilter.jsx src/components/WaterfallGrid.jsx src/components/ContentCard.jsx src/App.jsx
git commit -m "fix(frontend): improve contrast semantics and list accessibility"
```

---

## Task 9: ErrorBoundary、noscript、favicon、移动端页头

**Files:**
- Create: `src/components/ErrorBoundary.jsx`
- Create: `public/logo.svg`
- Modify: `src/main.jsx`
- Modify: `index.html`
- Modify: `src/App.jsx`

- [ ] **Step 1: ErrorBoundary**

```jsx
import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('页面渲染失败', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50 text-slate-600">
          <h1 className="text-xl font-bold">页面出错了</h1>
          <p className="text-sm">请刷新重试；若持续出现，请反馈。</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white"
          >
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

- [ ] **Step 2: main.jsx 包裹 App**

```jsx
import ErrorBoundary from './components/ErrorBoundary.jsx';
...
<React.StrictMode>
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
</React.StrictMode>
```

- [ ] **Step 3: index.html**

- favicon：`href="/logo.svg"`；
- `<body>` 内 `<div id="root"></div>` 之后加：

```html
<noscript>这个站点需要启用 JavaScript 才能浏览内容。</noscript>
```

- [ ] **Step 4: public/logo.svg**

复制 `src/assets/logo.svg` 到 `public/logo.svg`（内容原样）。

- [ ] **Step 5: 移动端页头**

`App.jsx` 页头：副标题加 `hidden sm:block`；容器 `py-4 px-6` → `py-3 px-4 sm:px-6`；Tab 按钮 `px-4 py-2 text-sm` → `px-3 py-1.5 text-xs sm:px-4 sm:py-2 sm:text-sm`；品牌 `h1` 已改 div，字号 `text-xl sm:text-2xl`。

- [ ] **Step 6: 验证**

Run: `npm run build`
Expected: 成功。

- [ ] **Step 7: 提交**

```bash
git add src/components/ErrorBoundary.jsx src/main.jsx index.html public/logo.svg src/App.jsx
git commit -m "fix(frontend): add error boundary, noscript and mobile header polish"
```

---

## Task 10: CSS 去重 + 最后两个 lint error

**Files:**
- Modify: `src/App.css`
- Modify: `src/index.css`
- Modify: `src/components/PhilosophySection.jsx`

- [ ] **Step 1: 清理 CSS**

- `App.css`：删除 `.grid` 全局规则与对应 media query；删除重复的 `.waterfall-item`/`.tag-button` 定义（保留 `index.css` 中的一份）；删除死规则 `.tag-button.active` 与 `:not(.active):hover`（组件已用条件类名）。
- `index.css`：保留基础 `body` 与 `.waterfall-item`/`.tag-button` 一份即可；若 `App.css` 仍引用 `.line-clamp-*`，保留。
- 确认没有类名仍被使用：`grep -rn "tag-button\|waterfall-item\|className=\"grid\"" src/`。

- [ ] **Step 2: 修 PhilosophySection 引号**

把第 59 行的两个裸 `"` 改为 `{'"'}` 或 `&quot;`。

- [ ] **Step 3: 验证**

Run: `npm run lint`
Expected: `0 problems`（exit 0）
Run: `npm run build`
Expected: 成功。

- [ ] **Step 4: 提交**

```bash
git add src/App.css src/index.css src/components/PhilosophySection.jsx
git commit -m "chore(frontend): dedupe styles and fix lint errors"
```

---

## Task 11: 全量验收与部署

**Files:** 无新增

- [ ] **Step 1: 本地检查**

```bash
npm run lint
npm run test:data
npm run check:data
npm run build
```
Expected：lint 0；test:data 23 pass；check:data 224 条；build 成功。

- [ ] **Step 2: 预览关键行为**

Run: `npm run preview`（后台）后人工或用浏览器核对：
- `#/search` 可直达信息检索页；刷新保持；
- 信息检索页输入词后，源卡 `href` 含关键词；arXiv 链接可打开搜索结果；
- 搜索无结果后空态按钮清空搜索词/分类/标签；
- 桌面滚动筛选区不重叠；
- 报告弹窗图表渲染。

- [ ] **Step 3: 推送（需用户批准）**

```bash
git push origin main
```

- [ ] **Step 4: 等待 CI 并冒烟**

用 GitHub Actions 页面确认 workflow 成功；`curl` 生产首页 200；确认 bundle 更新。

- [ ] **Step 5: 请 Pixel 用 Chrome 复验**

给 Pixel 发任务：在生产域名用 1440×900 与 375×812 复验 5 项 P1（源卡带词跳转、Tab hash/刷新、sticky 不重叠、空态全清、弹窗图表），留存截图与结论。

---

## Self-Review

- **Spec 覆盖**：§3.1 → Task 1/2；§3.2 → Task 2/3；§3.3 → Task 4/5；§3.4 → Task 6；§3.5 → Task 7/8；§3.6 → Task 9/10；§4 验收 → Task 11。
- **占位符**：无 TBD；每个改动文件都有具体类名/代码。
- **一致性**：`switchView`、`clearAllFilters`、`readViewFromHash`、`searchPageQuery` 命名在各任务中一致；CSS 类名沿用现有 Tailwind 工具类。
