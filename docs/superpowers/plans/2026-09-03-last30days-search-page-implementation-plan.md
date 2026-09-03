# Last30Days 信息检索页面实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 deepthink React 单页应用中新增「信息检索」Tab 页面，支持跨源搜索跳转

**Architecture:** 通过 App.jsx 添加 view 状态实现 Tab 切换，新建 Last30daysPage 组件包含 SearchHero、SourcesGrid、PhilosophySection 三个子组件，使用独立的数据文件和工具函数

**Tech Stack:** React + Tailwind CSS + Vite (现有技术栈)

**Spec:** `docs/superpowers/specs/2026-09-03-last30days-search-page-design.md`

## Global Constraints

- 纯前端实现，无需后端
- Tab 状态完全独立，切换时重置
- 与现有 deepthink 视觉风格一致（indigo/sky 配色）
- 新标签页打开外部链接

---

### Task 1: 创建信息源数据文件

**Files:**
- Create: `src/assets/last30days-sources.js`

**Interfaces:**
- Produces: `last30daysSources` (数组，包含 13 个信息源对象)

- [ ] **Step 1: 创建 src/assets/last30days-sources.js**

```javascript
export const last30daysSources = [
  {
    id: 'reddit',
    name: 'Reddit',
    nameCn: 'Reddit 社区',
    url: 'https://www.reddit.com/search/?q={q}',
    signal: 'Upvotes',
    description: '未经过滤的观点和评论',
    color: 'orange'
  },
  {
    id: 'x',
    name: 'X/Twitter',
    nameCn: 'X 社交',
    url: 'https://x.com/search?q={q}',
    signal: 'Engagements',
    description: '热点观点和专家讨论',
    color: 'blue'
  },
  {
    id: 'youtube',
    name: 'YouTube',
    nameCn: 'YouTube',
    url: 'https://www.youtube.com/results?search_query={q}',
    signal: 'Views',
    description: '视频内容及完整字幕',
    color: 'red'
  },
  {
    id: 'hackernews',
    name: 'Hacker News',
    nameCn: 'Hacker News',
    url: 'https://hn.algolia.com/?q={q}',
    signal: 'Points',
    description: '开发者共识',
    color: 'orange'
  },
  {
    id: 'github',
    name: 'GitHub',
    nameCn: 'GitHub',
    url: 'https://github.com/search?q={q}',
    signal: 'Stars',
    description: '代码项目和开发者动态',
    color: 'gray'
  },
  {
    id: 'arxiv',
    name: 'arXiv',
    nameCn: 'arXiv 论文',
    url: 'https://arxiv.org/search/?search_query={q}',
    signal: 'Citations',
    description: '学术研究论文',
    color: 'blue'
  },
  {
    id: 'polymarket',
    name: 'Polymarket',
    nameCn: 'Polymarket 预测',
    url: 'https://polymarket.com/search?q={q}',
    signal: 'Volume',
    description: '真金白银的预测市场',
    color: 'purple'
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    nameCn: 'TikTok',
    url: 'https://www.tiktok.com/search?q={q}',
    signal: 'Views',
    description: '短视频创作者互动',
    color: 'black'
  },
  {
    id: 'amazon',
    name: 'Amazon',
    nameCn: 'Amazon',
    url: 'https://www.amazon.com/s?k={q}',
    signal: 'Reviews',
    description: '商品评论和评分',
    color: 'orange'
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    nameCn: 'LinkedIn',
    url: 'https://www.linkedin.com/search/results/?keywords={q}',
    signal: 'Connections',
    description: '专业人脉和职位',
    color: 'blue'
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    nameCn: 'Pinterest',
    url: 'https://www.pinterest.com/search/?q={q}',
    signal: 'Saves',
    description: '创意收藏和灵感',
    color: 'red'
  },
  {
    id: 'duckduckgo',
    name: 'DuckDuckGo',
    nameCn: 'DuckDuckGo',
    url: 'https://duckduckgo.com/?q={q}',
    signal: 'Relevance',
    description: '隐私友好的通用搜索',
    color: 'gray'
  },
  {
    id: 'bluesky',
    name: 'Bluesky',
    nameCn: 'Bluesky',
    url: 'https://bsky.app/search?q={q}',
    signal: 'Likes',
    description: '去中心化社交讨论',
    color: 'blue'
  }
];
```

- [ ] **Step 2: 提交**

```bash
git add src/assets/last30days-sources.js
git commit -m "feat: add last30days sources data (13 platforms)"
```

---

### Task 2: 创建搜索工具函数

**Files:**
- Create: `src/utils/searchUtils.js`

**Interfaces:**
- Consumes: `last30daysSources`
- Produces: `buildSearchUrl(query, urlTemplate)`, `buildAllSearchUrls(query, sourceIds)`

- [ ] **Step 1: 创建 src/utils/searchUtils.js**

```javascript
import { last30daysSources } from '../assets/last30days-sources';

/**
 * 构建搜索 URL
 * @param {string} query - 搜索关键词
 * @param {string} urlTemplate - URL 模板，{q} 会被替换
 * @returns {string} 编码后的搜索 URL
 */
export const buildSearchUrl = (query, urlTemplate) => {
  return urlTemplate.replace('{q}', encodeURIComponent(query));
};

/**
 * 批量构建所有信息源的搜索 URL
 * @param {string} query - 搜索关键词
 * @param {string[]} sourceIds - 要搜索的信息源 ID 列表，null 表示全部
 * @returns {Object} { sourceId: url } 映射
 */
export const buildAllSearchUrls = (query, sourceIds = null) => {
  const sources = sourceIds
    ? last30daysSources.filter(s => sourceIds.includes(s.id))
    : last30daysSources;

  return sources.reduce((acc, source) => {
    acc[source.id] = buildSearchUrl(query, source.url);
    return acc;
  }, {});
};
```

- [ ] **Step 2: 提交**

```bash
git add src/utils/searchUtils.js
git commit -m "feat: add searchUtils for URL building"
```

---

### Task 3: 创建 SearchHero 组件

**Files:**
- Create: `src/components/SearchHero.jsx`

**Interfaces:**
- Props: 无 (自包含组件)

- [ ] **Step 1: 创建 src/components/SearchHero.jsx**

```jsx
import { useState } from 'react';
import { buildAllSearchUrls } from '../utils/searchUtils';
import { last30daysSources } from '../assets/last30days-sources';

const SearchHero = () => {
  const [query, setQuery] = useState('');

  const handleSearch = (url) => {
    window.open(url, '_blank');
  };

  const searchUrls = query.trim() ? buildAllSearchUrls(query) : {};

  return (
    <div className="bg-white rounded-2xl border border-indigo-100 shadow-lg shadow-indigo-50 p-8 mb-8">
      {/* 标题 */}
      <h2 className="text-2xl font-bold text-slate-800 mb-2 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-indigo-500">
          <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
        </svg>
        跨源搜索
      </h2>
      <p className="text-slate-500 mb-6">输入关键词，跨越 13 个平台搜索真实的人类观点</p>

      {/* 搜索输入框 */}
      <div className="relative mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入关键词，跨源搜索..."
          className="w-full px-5 py-4 text-lg border border-indigo-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        )}
      </div>

      {/* 快速跳转按钮组 */}
      {query.trim() && (
        <div>
          <p className="text-sm text-slate-500 mb-3">点击跳转搜索</p>
          <div className="flex flex-wrap gap-2">
            {last30daysSources.map((source) => (
              <button
                key={source.id}
                onClick={() => handleSearch(searchUrls[source.id])}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105
                  ${source.color === 'orange' ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' : ''}
                  ${source.color === 'blue' ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : ''}
                  ${source.color === 'red' ? 'bg-red-100 text-red-700 hover:bg-red-200' : ''}
                  ${source.color === 'gray' ? 'bg-slate-100 text-slate-700 hover:bg-slate-200' : ''}
                  ${source.color === 'purple' ? 'bg-purple-100 text-purple-700 hover:bg-purple-200' : ''}
                  ${source.color === 'black' ? 'bg-slate-800 text-white hover:bg-slate-900' : ''}
                `}
              >
                {source.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchHero;
```

- [ ] **Step 2: 提交**

```bash
git add src/components/SearchHero.jsx
git commit -m "feat: add SearchHero component for cross-source search"
```

---

### Task 4: 创建 SourcesGrid 组件

**Files:**
- Create: `src/components/SourcesGrid.jsx`

**Interfaces:**
- Props: `query` (string) - 当前搜索关键词

- [ ] **Step 1: 创建 src/components/SourcesGrid.jsx**

```jsx
import { last30daysSources } from '../assets/last30days-sources';
import { buildSearchUrl } from '../utils/searchUtils';

const SourcesGrid = ({ query }) => {
  const handleCardClick = (url) => {
    window.open(url, '_blank');
  };

  return (
    <div className="mb-8">
      {/* 栏目标题 */}
      <div className="flex items-center gap-3 mb-5">
        <div className="h-1 w-8 rounded-full bg-gradient-to-r from-indigo-500 to-sky-500" />
        <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-indigo-500">
            <path d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.06l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06l-1.06-1.06a.75.75 0 10-1.061 1.06l1.06 1.06z" />
          </svg>
          信息源
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {last30daysSources.length} 个平台
        </span>
      </div>

      {/* 卡片网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {last30daysSources.map((source) => {
          const searchUrl = query.trim()
            ? buildSearchUrl(query, source.url)
            : source.url.replace('{q}', '');

          return (
            <button
              key={source.id}
              onClick={() => handleCardClick(searchUrl)}
              className={`group text-left bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300 overflow-hidden cursor-pointer
                ${!query.trim() ? 'opacity-60' : ''}
              `}
            >
              {/* 顶部色条 */}
              <div className={`h-1.5 
                ${source.color === 'orange' ? 'bg-gradient-to-r from-orange-400 to-amber-400' : ''}
                ${source.color === 'blue' ? 'bg-gradient-to-r from-blue-400 to-cyan-400' : ''}
                ${source.color === 'red' ? 'bg-gradient-to-r from-red-400 to-pink-400' : ''}
                ${source.color === 'gray' ? 'bg-gradient-to-r from-slate-400 to-gray-400' : ''}
                ${source.color === 'purple' ? 'bg-gradient-to-r from-purple-400 to-violet-400' : ''}
                ${source.color === 'black' ? 'bg-gradient-to-r from-slate-700 to-slate-900' : ''}
              `} />

              <div className="p-5">
                {/* 平台名称 */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-base font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">
                    {source.name}
                  </h3>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 transition-colors">
                    <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
                    <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
                  </svg>
                </div>

                {/* 信号类型 */}
                <span className={`inline-block text-[10px] font-medium px-2 py-0.5 rounded mb-2
                  ${source.color === 'orange' ? 'text-orange-600 bg-orange-50' : ''}
                  ${source.color === 'blue' ? 'text-blue-600 bg-blue-50' : ''}
                  ${source.color === 'red' ? 'text-red-600 bg-red-50' : ''}
                  ${source.color === 'gray' ? 'text-slate-600 bg-slate-50' : ''}
                  ${source.color === 'purple' ? 'text-purple-600 bg-purple-50' : ''}
                  ${source.color === 'black' ? 'text-slate-600 bg-slate-100' : ''}
                `}>
                  {source.signal}
                </span>

                {/* 描述 */}
                <p className="text-sm text-slate-500 leading-relaxed">
                  {source.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SourcesGrid;
```

- [ ] **Step 2: 提交**

```bash
git add src/components/SourcesGrid.jsx
git commit -m "feat: add SourcesGrid component for platform cards"
```

---

### Task 5: 创建 PhilosophySection 组件

**Files:**
- Create: `src/components/PhilosophySection.jsx`

**Interfaces:**
- Props: 无 (自包含组件)

- [ ] **Step 1: 创建 src/components/PhilosophySection.jsx**

```jsx
const PhilosophySection = () => {
  return (
    <div className="bg-gradient-to-br from-indigo-50 to-sky-50 rounded-2xl border border-indigo-100 p-8 mb-8">
      {/* 核心主张 */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          <span className="text-2xl">💡</span>
          核心主张
        </h2>
        <blockquote className="text-lg text-indigo-700 font-medium italic border-l-4 border-indigo-400 pl-4">
          「由 upvotes、likes 和真金白银驱动，而非编辑筛选」
        </blockquote>
        <p className="text-slate-600 mt-3">
          AI agent 驱动的搜索引擎，由真实人类参与度评分，而非编辑推荐。
        </p>
      </div>

      {/* 设计原则 */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          <span className="text-2xl">⚙️</span>
          设计原则
        </h2>
        <div className="space-y-4">
          <div className="bg-white rounded-lg p-4 border border-indigo-100">
            <h3 className="font-bold text-slate-800 mb-1">自带 API Key</h3>
            <p className="text-slate-600 text-sm">
              没有单一 AI 能原生访问所有平台；用户供应自己的 API keys 和浏览器会话
            </p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-indigo-100">
            <h3 className="font-bold text-slate-800 mb-1">你无法从别处获得这种搜索</h3>
            <p className="text-slate-600 text-sm">
              Google 不会搜 Reddit 评论或 X 帖子；ChatGPT 有 Reddit 但没有 X 或 TikTok
            </p>
          </div>
          <div className="bg-white rounded-lg p-4 border border-indigo-100">
            <h3 className="font-bold text-slate-800 mb-1">社交相关性，而非 SEO 相关性</h3>
            <p className="text-slate-600 text-sm">
              1500 upvotes 的 Reddit 帖子胜过无人阅读的博客文章
            </p>
          </div>
        </div>
      </div>

      {/* 最佳实践 */}
      <div>
        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
          <span className="text-2xl">🎯</span>
          最佳实践
        </h2>
        <ul className="space-y-2">
          <li className="flex items-start gap-2 text-slate-600">
            <span className="text-indigo-500 mt-0.5">•</span>
            <span>使用特定平台语法优化搜索（如 Reddit: <code className="bg-slate-100 px-1 rounded">site:reddit.com</code>，X: <code className="bg-slate-100 px-1 rounded">from:@username</code>）</span>
          </li>
          <li className="flex items-start gap-2 text-slate-600">
            <span className="text-indigo-500 mt-0.5">•</span>
            <span>使用 <strong>"X vs Y"</strong> 格式进行对比搜索</span>
          </li>
          <li className="flex items-start gap-2 text-slate-600">
            <span className="text-indigo-500 mt-0.5">•</span>
            <span>组合多个平台获取更全面的视角</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default PhilosophySection;
```

- [ ] **Step 2: 提交**

```bash
git add src/components/PhilosophySection.jsx
git commit -m "feat: add PhilosophySection component with design principles"
```

---

### Task 6: 创建 Last30daysPage 主组件

**Files:**
- Create: `src/components/Last30daysPage.jsx`

**Interfaces:**
- Props: 无 (自包含组件)

- [ ] **Step 1: 创建 src/components/Last30daysPage.jsx**

```jsx
import { useState } from 'react';
import SearchHero from './SearchHero';
import SourcesGrid from './SourcesGrid';
import PhilosophySection from './PhilosophySection';

const Last30daysPage = () => {
  const [query, setQuery] = useState('');

  return (
    <div className="py-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500 mb-2">
          信息检索
        </h1>
        <p className="text-slate-500">
          跨越 13 个平台，追踪真实的人类声音
        </p>
      </div>

      {/* 搜索英雄区 */}
      <SearchHero />

      {/* 理念说明区 */}
      <PhilosophySection />

      {/* 信息源卡片网格 */}
      <SourcesGrid query={query} />
    </div>
  );
};

export default Last30daysPage;
```

- [ ] **Step 2: 提交**

```bash
git add src/components/Last30daysPage.jsx
git commit -m "feat: add Last30daysPage main component"
```

---

### Task 7: 修改 App.jsx 添加 Tab 切换

**Files:**
- Modify: `src/App.jsx`

**Interfaces:**
- 新增: `currentView` state, `'browse'` | `'search'` 两个视图

- [ ] **Step 1: 修改 src/App.jsx 添加 view 状态和 Tab 切换**

修改 App.jsx 的导入部分，添加 Last30daysPage:
```jsx
import Last30daysPage from './components/Last30daysPage';
```

修改 App 组件，添加 view 状态和 Tab UI:
```jsx
const App = () => {
  // ... 现有状态 ...

  // 新增: 视图状态
  const [currentView, setCurrentView] = useState('browse'); // 'browse' | 'search'
```

修改 Header，添加 Tab:
```jsx
<header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-indigo-100 shadow-sm py-4 px-6 transition-all duration-300">
  <div className="max-w-7xl mx-auto flex items-center justify-between">
    {/* Logo 部分保持不变 */}
    <div className="flex items-center gap-3">
      <img src={logo} alt="DeepThink Logo" className="h-10 w-10 rounded-lg ring-1 ring-indigo-200 bg-white/70 p-1.5" />
      <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500">
        观念棱镜
      </h1>
    </div>

    {/* 新增: Tab 导航 */}
    <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
      <button
        onClick={() => setCurrentView('browse')}
        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
          currentView === 'browse'
            ? 'bg-white text-indigo-600 shadow-sm'
            : 'text-slate-600 hover:text-slate-800'
        }`}
      >
        内容浏览
      </button>
      <button
        onClick={() => setCurrentView('search')}
        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
          currentView === 'search'
            ? 'bg-white text-indigo-600 shadow-sm'
            : 'text-slate-600 hover:text-slate-800'
        }`}
      >
        信息检索
      </button>
    </div>

    {/* 内容计数保持不变 */}
    <div className="hidden sm:block text-sm text-slate-400">
      {currentView === 'browse' ? `${filteredData.length} 条内容` : '跨源搜索'}
    </div>
  </div>
</header>
```

修改 main 内容区，根据 view 条件渲染:
```jsx
<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
  {currentView === 'browse' ? (
    <>
      {/* 现有瀑布流内容 */}
      <ReportsPanel />
      <LinksPanel />
      <div className="mb-6">
        <SearchBar
          searchQuery={searchQuery}
          onSearchChange={handleSearchChange}
          onClearSearch={handleClearSearch}
        />
      </div>
      <div className="mb-4 sticky top-24 z-40">
        <CategoryFilter
          selectedCategory={selectedCategory}
          onCategorySelect={setSelectedCategory}
          counts={categoryCounts}
        />
      </div>
      <div className="mb-8 sticky top-24 z-40">
        <TagFilter
          tags={tags}
          selectedTags={selectedTags}
          onTagToggle={toggleTag}
          onClearFilters={clearFilters}
        />
      </div>
      {isLoading ? (
        <div className="flex flex-col justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-100 border-t-indigo-500"></div>
          <p className="mt-4 text-indigo-400 font-medium animate-pulse">正在加载精彩内容...</p>
        </div>
      ) : (
        <div className="transition-opacity duration-500 ease-in-out">
          <WaterfallGrid data={filteredData} />
        </div>
      )}
      {filteredData.length === 0 && !isLoading && (
        <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-indigo-200 shadow-sm mx-auto max-w-2xl">
          {/* 现有空状态内容 */}
          ...
        </div>
      )}
    </>
  ) : (
    <Last30daysPage />
  )}
</main>
```

- [ ] **Step 2: 运行构建验证**

```bash
npm run build
```

- [ ] **Step 3: 提交**

```bash
git add src/App.jsx
git commit -m "feat: add tab navigation for browse/search views"
```

---

### Task 8: 最终验证

- [ ] **Step 1: 本地测试**

```bash
npm run dev
# 浏览器打开 http://localhost:5173
# 1. 点击「信息检索」Tab
# 2. 输入关键词测试搜索
# 3. 点击卡片测试跳转
```

- [ ] **Step 2: 生产构建**

```bash
npm run build
# 验证构建成功
```

- [ ] **Step 3: Git 推送**

```bash
git push origin main
```

---

## 验收标准检查

- [ ] Header 显示两个 Tab（内容浏览 / 信息检索）
- [ ] Tab 切换正常工作
- [ ] 搜索输入框可用
- [ ] 点击信息源卡片正确跳转
- [ ] 理念说明区正确展示
- [ ] 与现有 deepthink 视觉风格一致
- [ ] 构建通过
