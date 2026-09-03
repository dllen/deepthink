
import Fuse from 'fuse.js';
import { useCallback, useEffect, useMemo, useState } from 'react';
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

const App = () => {
  const [items, setItems] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [categoryCounts, setCategoryCounts] = useState({});
  const [currentView, setCurrentView] = useState('browse'); // 'browse' | 'search'

  useEffect(() => {
    const allTags = new Set();
    data.forEach((item) => {
      if (!item.tags) return;
      item.tags.split(',').forEach((t) => {
        const trimmed = t.trim();
        if (trimmed) allTags.add(trimmed);
      });
    });
    const counts = {};
    data.forEach((item) => {
      if (item.category) counts[item.category] = (counts[item.category] || 0) + 1;
    });
    setItems(data);
    setFilteredData(data);
    setTags(Array.from(allTags));
    setCategoryCounts(counts);
    setIsLoading(false);
  }, []);

  const fuse = useMemo(() => {
    return new Fuse(items, {
      keys: ['title', 'summary'],
      threshold: 0.35,
      ignoreLocation: true,
      useExtendedSearch: true,
    });
  }, [items]);

  const filterData = useCallback(() => {
    let result = items;

    if (selectedCategory) {
      result = result.filter(item => item.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const searchResults = fuse.search(searchQuery);
      const idSet = new Set(searchResults.map(r => r.item.id));
      result = result.filter(item => idSet.has(item.id));
    }

    if (selectedTags.length > 0) {
      result = result.filter(item => {
        const itemTags = item.tags.split(',').map(tag => tag.trim());
        return selectedTags.some(tag => itemTags.includes(tag));
      });
    }

    setFilteredData(result);
  }, [items, searchQuery, selectedTags, selectedCategory, fuse]);

  // Re-filter when search query, tags, or category change
  useEffect(() => {
    filterData();
  }, [filterData, searchQuery, selectedTags, selectedCategory, items]);

  // 切换标签选择状态
  const toggleTag = (tag) => {
    if (selectedTags.includes(tag)) {
      setSelectedTags(selectedTags.filter(t => t !== tag));
    } else {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  // 清除所有标签筛选
  const clearFilters = () => {
    setSelectedTags([]);
  };

  // Search handlers
  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
  };



  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* 头部 */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-indigo-100 shadow-sm py-4 px-6 transition-all duration-300">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={logo} alt="DeepThink Logo" className="h-10 w-10 rounded-lg ring-1 ring-indigo-200 bg-white/70 p-1.5" />
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500">
              观念棱镜
            </h1>
            <p className="text-slate-500 text-xs mt-1">深度思考 • 智慧洞见</p>
          </div>

          {/* Tab Navigation */}
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

          <div className="hidden sm:block text-sm text-slate-400">
            {currentView === 'browse' ? `${filteredData.length} 条内容` : '跨源搜索'}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        {currentView === 'browse' ? (
          <>
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

            {/* 分类筛选器（七大类单选） */}
            <div className="mb-4 sticky top-24 z-40">
              <CategoryFilter
                selectedCategory={selectedCategory}
                onCategorySelect={setSelectedCategory}
                counts={categoryCounts}
              />
            </div>

            {/* 标签筛选器（次级，多选） */}
            <div className="mb-8 sticky top-24 z-40">
              <TagFilter
                tags={tags}
                selectedTags={selectedTags}
                onTagToggle={toggleTag}
                onClearFilters={clearFilters}
              />
            </div>

            {/* 瀑布流内容 */}
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
                  onClick={clearFilters}
                  className="mt-8 px-6 py-2.5 bg-indigo-500 text-white rounded-full font-medium shadow-lg shadow-indigo-200 hover:bg-indigo-600 hover:shadow-indigo-300 transform hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                >
                  清除所有筛选
                </button>
              </div>
            )}
          </>
        ) : (
          <Last30daysPage />
        )}
      </main>

      <footer className="bg-white border-t border-slate-100 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-400 text-sm">
            观念棱镜 © {new Date().getFullYear()} • Powered by DeepThink
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
