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
