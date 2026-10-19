import { buildAllSearchUrls } from '../utils/searchUtils';
import { last30daysSources } from '../assets/last30days-sources';

const SearchHero = ({ query, onQueryChange }) => {
  const searchUrls = query.trim() ? buildAllSearchUrls(query) : {};

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    window.open(
      `https://duckduckgo.com/?q=${encodeURIComponent(trimmed)}`,
      '_blank',
      'noopener,noreferrer',
    );
  };

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

      <form onSubmit={handleSubmit}>
        {/* 搜索输入框 */}
        <div className="relative mb-6">
          <label htmlFor="search-hero-input" className="sr-only">
            跨源搜索关键词
          </label>
          <input
            id="search-hero-input"
            type="text"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="输入关键词，跨源搜索..."
            className="w-full px-5 py-4 text-lg border border-indigo-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
          />
          {query && (
            <button
              type="button"
              onClick={() => onQueryChange('')}
              aria-label="清除搜索词"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          )}
          <button type="submit" className="sr-only">
            搜索
          </button>
        </div>

        {/* 快速跳转链接组 */}
        {query.trim() && (
          <div>
            <p className="text-sm text-slate-500 mb-3">点击跳转搜索</p>
            <div className="flex flex-wrap gap-2">
              {last30daysSources.map((source) => (
                <a
                  key={source.id}
                  href={searchUrls[source.id]}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`inline-block px-4 py-2 rounded-lg text-sm font-medium transition-all hover:scale-105
                    ${source.color === 'orange' ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' : ''}
                    ${source.color === 'blue' ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : ''}
                    ${source.color === 'red' ? 'bg-red-100 text-red-700 hover:bg-red-200' : ''}
                    ${source.color === 'gray' ? 'bg-slate-100 text-slate-700 hover:bg-slate-200' : ''}
                    ${source.color === 'purple' ? 'bg-purple-100 text-purple-700 hover:bg-purple-200' : ''}
                    ${source.color === 'black' ? 'bg-slate-800 text-white hover:bg-slate-900' : ''}
                  `}
                >
                  {source.name}
                </a>
              ))}
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

export default SearchHero;
