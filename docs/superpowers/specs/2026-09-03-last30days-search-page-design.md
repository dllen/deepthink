# Last30Days 信息检索页面设计

**日期**: 2026-09-03
**状态**: 已批准

## 概述

将 Last30Days AI Skill 的理念和功能抽取为一个独立的「信息检索」页面，集成到现有 deepthink React 单页应用中。

## 用户故事

用户想在 deepthink 中快速访问多个社交平台和聚合网站进行跨源搜索，无需运行完整的 AI agent，直接跳转到信息源进行人工筛选。

## 架构

### 路由设计

- **现有**: `/` → 单页应用，瀑布流内容
- **新增**: Tab 切换 (无 URL 变化)
  - Tab 1: "内容浏览" → 当前瀑布流界面
  - Tab 2: "信息检索" → Last30Days 搜索页

### 组件结构

```
App.jsx
├── Header (Logo + 两个 Tab)
├── [Tab1] WaterfallContent (现有瀑布流)
└── [Tab2] Last30daysPage (新)
    ├── SearchHero (搜索英雄区)
    ├── SourcesGrid (信息源卡片网格)
    └── PhilosophySection (理念说明)
```

## 功能规格

### 1. 搜索英雄区 (SearchHero)

**UI**:
- 大型搜索输入框，placeholder: "输入关键词，跨源搜索..."
- 输入关键词后，下方显示「快速跳转」按钮组

**行为**:
- 输入时实时更新 URL 预览
- 点击任一信息源按钮 → 新标签页打开该平台搜索页

### 2. 信息源卡片网格 (SourcesGrid)

**数据源**: 13 个信息源

| ID | 名称 | 搜索 URL 模板 | 信号类型 | 图标 |
|----|------|--------------|----------|------|
| reddit | Reddit | `https://www.reddit.com/search/?q={q}` | Upvotes | orange |
| x | X/Twitter | `https://x.com/search?q={q}` | Engagements | blue |
| youtube | YouTube | `https://www.youtube.com/results?search_query={q}` | Views | red |
| hackernews | Hacker News | `https://hn.algolia.com/?q={q}` | Points | orange |
| github | GitHub | `https://github.com/search?q={q}` | Stars | gray |
| arxiv | arXiv | `https://arxiv.org/search/?search={q}` | Citations | blue |
| polymarket | Polymarket | `https://polymarket.com/search?q={q}` | Volume | purple |
| tiktok | TikTok | `https://www.tiktok.com/search?q={q}` | Views | black |
| amazon | Amazon | `https://www.amazon.com/s?k={q}` | Reviews | orange |
| linkedin | LinkedIn | `https://www.linkedin.com/search/results/?keywords={q}` | Connections | blue |
| pinterest | Pinterest | `https://www.pinterest.com/search/?q={q}` | Saves | red |
| duckduckgo | DuckDuckGo | `https://duckduckgo.com/?q={q}` | Relevance | gray |
| bluesky | Bluesky | `https://bsky.app/search?q={q}` | Likes | blue |

**卡片 UI**:
- 平台名称 + 图标
- 信号类型标签 (Upvotes / Stars / Points 等)
- 点击 → `window.open(url, '_blank')`

### 3. 理念说明区 (PhilosophySection)

**内容**:

**核心主张**:
> 「由 upvotes、likes 和真金白银驱动，而非编辑筛选」
> AI agent 驱动的搜索引擎，由真实人类参与度评分，而非编辑推荐。

**设计原则**:
1. **自带 API Key** — 没有单一 AI 能原生访问所有平台；用户供应自己的 API keys 和浏览器会话
2. **你无法从别处获得这种搜索** — Google 不会搜 Reddit 评论或 X 帖子
3. **社交相关性，而非 SEO 相关性** — 1500 upvotes 的 Reddit 帖子胜过无人阅读的博客文章

**最佳实践**:
- 使用特定平台语法优化搜索 (如 Reddit: `site:reddit.com`, X: `from:@username`)
- 使用 "X vs Y" 格式进行对比搜索
- 组合多个平台获取更全面的视角

## 工具函数

```javascript
// src/utils/searchUtils.js

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
 * @param {string[]} sourceIds - 要搜索的信息源 ID 列表
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

## 数据文件

```javascript
// src/assets/last30days-sources.js

export const last30daysSources = [
  {
    id: 'reddit',
    name: 'Reddit',
    nameCn: 'Reddit 社区',
    url: 'https://www.reddit.com/search/?q={q}',
    signal: 'Upvotes',
    description: '未经过滤的观点和评论'
  },
  // ... 其他信息源
];
```

## 技术决策

1. **纯前端实现** — 无需后端，所有跳转在客户端完成
2. **Tab 状态完全独立** — 切换 Tab 时重置状态
3. **与现有 deepthink 风格一致** — 同样的配色、卡片风格、渐变色条
4. **新标签页打开** — 保持用户在本网站

## 验收标准

- [ ] Header 显示两个 Tab
- [ ] Tab 切换正常工作
- [ ] 搜索输入框可用
- [ ] 点击信息源卡片正确跳转
- [ ] 理念说明区正确展示
- [ ] 与现有 deepthink 视觉风格一致
- [ ] 构建通过
