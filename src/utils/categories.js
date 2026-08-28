// 七大类：阮一峰《科技爱好者周刊》分类结构
// 七类互斥，每个内容项只属于一类
export const CATEGORIES = [
  { key: '科技动态', icon: '⚡' },
  { key: '文章',     icon: '📰' },
  { key: '工具',     icon: '🔧' },
  { key: '资源',     icon: '📚' },
  { key: '图片',     icon: '🖼️' },
  { key: '文摘',     icon: '📖' },
  { key: '言论',     icon: '💬' },
];

// 每类配色 (Tailwind classes)
export const CATEGORY_STYLES = {
  '科技动态': { badge: 'bg-blue-50 text-blue-700 ring-blue-200',     pill: 'bg-blue-500' },
  '文章':     { badge: 'bg-indigo-50 text-indigo-700 ring-indigo-200', pill: 'bg-indigo-500' },
  '工具':     { badge: 'bg-emerald-50 text-emerald-700 ring-emerald-200', pill: 'bg-emerald-500' },
  '资源':     { badge: 'bg-amber-50 text-amber-700 ring-amber-200',   pill: 'bg-amber-500' },
  '图片':     { badge: 'bg-pink-50 text-pink-700 ring-pink-200',       pill: 'bg-pink-500' },
  '文摘':     { badge: 'bg-violet-50 text-violet-700 ring-violet-200', pill: 'bg-violet-500' },
  '言论':     { badge: 'bg-orange-50 text-orange-700 ring-orange-200', pill: 'bg-orange-500' },
};

export const getCategoryStyle = (cat) => CATEGORY_STYLES[cat] || CATEGORY_STYLES['文章'];