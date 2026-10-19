import { last30daysSources } from '../assets/last30days-sources';
import { buildSearchUrl } from '../utils/searchUtils';

const SourcesGrid = ({ query }) => {
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

      <p className="text-xs text-slate-400 mb-3">
        输入关键词后点击卡片，直接打开该平台的搜索结果
      </p>

      {/* 卡片网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {last30daysSources.map((source) => {
          const trimmedQuery = query.trim();
          // 空 query 时直接打开平台首页，避免落到带空搜索词的路径
          const searchUrl = trimmedQuery
            ? buildSearchUrl(trimmedQuery, source.url)
            : `${new window.URL(source.url).origin}/`;

          return (
            <a
              key={source.id}
              href={searchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="group block text-left bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300 overflow-hidden cursor-pointer"
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
            </a>
          );
        })}
      </div>
    </div>
  );
};

export default SourcesGrid;
