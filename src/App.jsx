
import { useEffect, useState } from 'react';
import './App.css';
import TagFilter from './components/TagFilter';
import WaterfallGrid from './components/WaterfallGrid';
import SQLiteReader from './utils/sqliteReader';

// Try to use static data
import staticDataRaw from './assets/static-data.json?url';

const App = () => {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load static data on mount
  useEffect(() => {
    const loadStaticData = async () => {
      try {
        // Fetch the static data file
        const response = await fetch(staticDataRaw);
        if (response.ok) {
           const jsonData = await response.json();
           if (jsonData && jsonData.length > 0) {
             const reader = new SQLiteReader();
             const extractedTags = reader.extractTags(jsonData);
             setData(jsonData);
             setFilteredData(jsonData);
             setTags(extractedTags);
             setIsLoading(false);
             return;
           }
        }
        // Fallback to initial load logic if fetch fails or data is empty
        readSQLiteData();
      } catch (e) {
        console.warn('Failed to load static data, falling back:', e);
        readSQLiteData(); // Fallback to reading simulated data
      }
    };
    
    loadStaticData();
  }, []);

  // 从SQLite文件读取数据的函数
  const readSQLiteData = async () => {
    try {
      const reader = new SQLiteReader();
      // 实际使用时，这里会从用户上传的SQLite文件中读取数据
      // const data = await reader.readData('path/to/file.sqlite');
      const data = await reader.readData(); // 使用模拟数据
      
      const tags = reader.extractTags(data);

      setData(data);
      setFilteredData(data);
      setTags(tags);
      setIsLoading(false);
    } catch (error) {
      console.error('Error reading SQLite data:', error);
      setIsLoading(false);
    }

  };

  // 筛选数据
  const filterDataByTags = () => {
    if (selectedTags.length === 0) {
      setFilteredData(data);
    } else {
      const filtered = data.filter(item => {
        const itemTags = item.tags.split(',').map(tag => tag.trim());
        return selectedTags.some(tag => itemTags.includes(tag));
      });
      setFilteredData(filtered);
    }
  };

  // 当选中的标签改变时，重新过滤数据
  useEffect(() => {
    filterDataByTags();
  }, [selectedTags]);

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



  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* 头部 */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-indigo-100 shadow-sm py-4 px-6 transition-all duration-300">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500">
              观念棱镜
            </h1>
            <p className="text-slate-500 text-xs mt-1">深度思考 • 智慧洞见</p>
          </div>
          <div className="hidden sm:block text-sm text-slate-400">
            {filteredData.length} 条内容
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-grow w-full">
        
        {/* 标签筛选器 */}
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
              尝试选择不同的标签，或者清除当前的筛选条件重新开始
            </p>
            <button
              onClick={clearFilters}
              className="mt-8 px-6 py-2.5 bg-indigo-500 text-white rounded-full font-medium shadow-lg shadow-indigo-200 hover:bg-indigo-600 hover:shadow-indigo-300 transform hover:-translate-y-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              清除所有筛选
            </button>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-slate-100 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-slate-400 text-sm">
          <p className="text-slate-400 text-sm">
            观念棱镜 © {new Date().getFullYear()} • Powered by DeepThink
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;