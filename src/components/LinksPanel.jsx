import staticLinks from '../assets/static-links';

const LinksPanel = () => {
  if (!staticLinks || staticLinks.length === 0) return null;

  return (
    <section className="mb-8">
      {/* 栏目标题 */}
      <div className="flex items-center gap-3 mb-2">
        <div className="h-1 w-8 rounded-full bg-gradient-to-r from-sky-500 to-cyan-500" />
        <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-sky-500">
            <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
          </svg>
          信息源头
        </h2>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {staticLinks.length} 个
        </span>
      </div>
      <p className="text-xs text-slate-400 mb-5 pl-11">
        在信息过载的时代，比「知道更多」更重要的，是「知道该看什么」。
      </p>

      {/* 链接卡片列表 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {staticLinks.map((link) => (
          <a
            key={link.id}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`访问链接: ${link.title}`}
            className="group bg-white rounded-xl border border-slate-200 hover:border-sky-300 hover:shadow-lg hover:shadow-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 transition-all duration-300 overflow-hidden"
          >
            {/* 卡片顶部色条 */}
            <div className="h-1.5 bg-gradient-to-r from-sky-400 to-cyan-400 group-hover:from-sky-500 group-hover:to-cyan-500 transition-colors" />

            <div className="p-5">
              {/* 分类徽章 + 外链图标 */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-medium text-sky-600 bg-sky-50 px-2 py-0.5 rounded">
                  {link.category}
                </span>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-slate-300 group-hover:text-sky-500 transition-colors">
                  <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
                  <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
                </svg>
              </div>

              {/* 标题 */}
              <h3 className="text-base font-bold text-slate-800 mb-2 group-hover:text-sky-600 transition-colors leading-snug">
                {link.title}
              </h3>

              {/* 描述 */}
              <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                {link.description}
              </p>

              {/* 跳转提示 */}
              <div className="flex items-center gap-1.5 text-sm font-medium text-sky-600 group-hover:text-sky-700 transition-colors">
                <span>访问链接</span>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 group-hover:translate-x-0.5 transition-transform">
                  <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
};

export default LinksPanel;
