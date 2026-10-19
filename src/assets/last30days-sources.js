export const last30daysSources = [
  {
    id: 'reddit',
    name: 'Reddit',
    url: 'https://www.reddit.com/search/?q={q}',
    signal: 'Upvotes',
    description: '未经过滤的观点和评论',
    color: 'orange'
  },
  {
    id: 'x',
    name: 'X/Twitter',
    url: 'https://x.com/search?q={q}',
    signal: 'Engagements',
    description: '热点观点和专家讨论',
    color: 'blue'
  },
  {
    id: 'youtube',
    name: 'YouTube',
    url: 'https://www.youtube.com/results?search_query={q}',
    signal: 'Views',
    description: '视频内容及完整字幕',
    color: 'red'
  },
  {
    id: 'hackernews',
    name: 'Hacker News',
    url: 'https://hn.algolia.com/?q={q}',
    signal: 'Points',
    description: '开发者共识',
    color: 'orange'
  },
  {
    id: 'github',
    name: 'GitHub',
    url: 'https://github.com/search?q={q}',
    signal: 'Stars',
    description: '代码项目和开发者动态',
    color: 'gray'
  },
  {
    id: 'arxiv',
    name: 'arXiv',
    url: 'https://arxiv.org/search/?searchtype=all&query={q}',
    signal: 'Citations',
    description: '学术研究论文',
    color: 'blue'
  },
  {
    id: 'polymarket',
    name: 'Polymarket',
    url: 'https://polymarket.com/search?q={q}',
    signal: 'Volume',
    description: '真金白银的预测市场',
    color: 'purple'
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    url: 'https://www.tiktok.com/search?q={q}',
    signal: 'Views',
    description: '短视频创作者互动',
    color: 'black'
  },
  {
    id: 'amazon',
    name: 'Amazon',
    url: 'https://www.amazon.com/s?k={q}',
    signal: 'Reviews',
    description: '商品评论和评分',
    color: 'orange'
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    url: 'https://www.linkedin.com/search/results/?keywords={q}',
    signal: 'Connections',
    description: '专业人脉和职位',
    color: 'blue'
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    url: 'https://www.pinterest.com/search/?q={q}',
    signal: 'Saves',
    description: '创意收藏和灵感',
    color: 'red'
  },
  {
    id: 'duckduckgo',
    name: 'DuckDuckGo',
    url: 'https://duckduckgo.com/?q={q}',
    signal: 'Relevance',
    description: '隐私友好的通用搜索',
    color: 'gray'
  },
  {
    id: 'bluesky',
    name: 'Bluesky',
    url: 'https://bsky.app/search?q={q}',
    signal: 'Likes',
    description: '去中心化社交讨论',
    color: 'blue'
  }
];
