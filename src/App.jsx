
import Fuse from 'fuse.js';
import { useEffect, useMemo, useState } from 'react';
import './App.css';
import SearchBar from './components/SearchBar';
import TagFilter from './components/TagFilter';
import CategoryFilter from './components/CategoryFilter';
import WaterfallGrid from './components/WaterfallGrid';
import ReportsPanel from './components/ReportsPanel';
import LinksPanel from './components/LinksPanel';
import Last30daysPage from './components/Last30daysPage';
import data from './assets/static-data.js';
import logo from './assets/logo.svg';

const VIEW_BROWSE = 'browse';
const VIEW_SEARCH = 'search';
const VIEW_HASH = { [VIEW_BROWSE]: '#/browse', [VIEW_SEARCH]: '#/search' };

function readViewFromHash() {
  const raw = window.location.hash.replace(/^#\/?/, '');
  return raw === VIEW_SEARCH ? VIEW_SEARCH : VIEW_BROWSE;
}

const App = () => {
  const [selectedTags, setSelectedTags] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentView, setCurrentView] = useState(readViewFromHash);
  const [searchPageQuery, setSearchPageQuery] = useState('');

  // 标签与分类计数从静态数据一次性派生
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

  useEffect(() => {
    // 监听 hashchange；非法 hash 归一为规范路径，用 replaceState 不新增历史条目
    const syncFromHash = () => {
      const view = readViewFromHash();
      setCurrentView(view);
      if (window.location.hash !== VIEW_HASH[view]) {
        window.history.replaceState(null, '', VIEW_HASH[view]);
      }
    };
    window.addEventListener('hashchange', syncFromHash);
    syncFromHash();
    return () => window.removeEventListener('hashchange', syncFromHash);
  }, []);

  const fuse = useMemo(
    () =>
      new Fuse(data, {
        keys: ['title', 'summary'],
        threshold: 0.35,
        ignoreLocation: true,
        useExtendedSearch: true,
      }),
    []
  );

  // 派生筛选结果，不再写入 state
  const filteredData = useMemo(() => {
    let result = data;

    if (selectedCategory) {
      result = result.filter(item => item.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const idSet = new Set(fuse.search(searchQuery).map(r => r.item.id));
      result = result.filter(item => idSet.has(item.id));
    }

    if (selectedTags.length > 0) {
      result = result.filter(item => {
        const itemTags = (item.tags || '').split(',').map(tag => tag.trim());
        return selectedTags.some(tag => itemTags.includes(tag));
      });
    }

    return result;
  }, [fuse, searchQuery, selectedCategory, selectedTags]);

  // 切换标签选择状态
  const toggleTag = (tag) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  // 清除所有标签筛选（保留分类与搜索词）
  const clearTagFilters = () => {
    setSelectedTags([]);
  };

  // 清除全部筛选（标签 + 分类 + 搜索词）
  const clearAllFilters = () => {
    setSelectedTags([]);
    setSelectedCategory(null);
    setSearchQuery('');
  };

  // Search handlers
  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
  };

  // 切换视图：只写 hash，state 由 hashchange 同步
  const switchView = (view) => {
    if (view === currentView) return;
    window.location.hash = VIEW_HASH[view];
    window.scrollTo({ top: 0, behavior: 'auto' });
  };



  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* 头部 */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-indigo-100 shadow-sm py-3 px-4 sm:px-6 transition-all duration-300">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={logo} alt="DeepThink Logo" className="h-10 w-10 rounded-lg ring-1 ring-indigo-200 bg-white/70 p-1.5" />
            <div className="text-xl sm:text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500">
              观念棱镜
            </div>
            <p className="hidden sm:block text-slate-500 text-xs mt-1">深度思考 • 智慧洞见</p>
          </div>

          {/* Tab Navigation */}
          <div role="tablist" aria-label="视图切换" className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            <button
              role="tab"
              id="tab-browse"
              aria-selected={currentView === VIEW_BROWSE}
              aria-controls="panel-browse"
              onClick={() => switchView(VIEW_BROWSE)}
              className={`px-3 py-1.5 text-xs sm:px-4 sm:py-2 sm:text-sm rounded-md font-medium transition-all ${
                currentView === VIEW_BROWSE
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              内容浏览
            </button>
            <button
              role="tab"
              id="tab-search"
              aria-selected={currentView === VIEW_SEARCH}
              aria-controls="panel-search"
              onClick={() => switchView(VIEW_SEARCH)}
              className={`px-3 py-1.5 text-xs sm:px-4 sm:py-2 sm:text-sm rounded-md font-medium transition-all ${
                currentView === VIEW_SEARCH
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              信息检索
            </button>
          </div>

          <div className="hidden sm:block text-sm text-slate-400">
            {currentView === VIEW_BROWSE ? `${filteredData.length} 条内容` : '跨源搜索'}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        {currentView === VIEW_BROWSE ? (
          <div id="panel-browse" role="tabpanel" aria-labelledby="tab-browse">
            <h1 className="sr-only">观念棱镜 · 内容浏览</h1>
            {/* 分析报告栏目 */}
            <ReportsPanel />

            {/* 信息源头栏目 */}
            <LinksPanel />

            {/* 搜索栏 */}
            <div className="mb-6">
              <SearchBar
                searchQuery={searchQuery}
                onSearchChange={handleSearchChange}
                onClearSearch={handleClearSearch}
              />
            </div>

            {/* 筛选区：分类（七大类单选）+ 标签（次级多选）合并为一个 sticky 容器 */}
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
                onClearFilters={clearTagFilters}
              />
            </div>

            {/* 瀑布流内容 */}
            <div className="transition-opacity duration-500 ease-in-out">
              <WaterfallGrid data={filteredData} />
            </div>

            {filteredData.length === 0 && (
              <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-indigo-200 shadow-sm mx-auto max-w-2xl">
                <div className="mx-auto h-24 w-24 bg-indigo-50 rounded-full flex items-center justify-center mb-6">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-10 h-10 text-indigo-400">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-slate-900">没有找到匹配的内容</h3>
                <p className="mt-2 text-slate-500 max-w-sm mx-auto">
                  尝试选择不同的分类或标签，或者清除当前的筛选条件重新开始
                </p>
                <button
                  onClick={clearAllFilters}
                  className="mt-8 px-6 py-2.5 bg-indigo-500 text-white rounded-full font-medium shadow-lg shadow-indigo-200 hover:bg-indigo-600 hover:shadow-indigo-300 transform hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                >
                  清除所有筛选
                </button>
              </div>
            )}
          </div>
        ) : (
          <div id="panel-search" role="tabpanel" aria-labelledby="tab-search">
            <Last30daysPage query={searchPageQuery} onQueryChange={setSearchPageQuery} />
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-slate-100 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-500 text-sm">
            观念棱镜 © {new Date().getFullYear()} • Powered by DeepThink
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
