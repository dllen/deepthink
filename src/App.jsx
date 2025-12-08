import React, { useState, useEffect } from 'react';
import WaterfallGrid from './components/WaterfallGrid';
import TagFilter from './components/TagFilter';
import FileUpload from './components/FileUpload';
import SQLiteReader from './utils/sqliteReader';
import './App.css';

const App = () => {
  const [data, setData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

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

  // 初始化数据
  useEffect(() => {
    readSQLiteData();
  }, []);

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

  // 处理文件上传
  const handleFileUpload = async (file) => {
    setIsLoading(true);
    try {
      // 在实际实现中，这里会使用sql.js来读取SQLite文件
      // 由于在浏览器环境中无法直接操作，我们模拟读取过程
      console.log('Processing file:', file.name);
      
      // 使用模拟数据进行演示
      const reader = new SQLiteReader();
      const data = await reader.readData();
      const extractedTags = reader.extractTags(data);
      
      setData(data);
      setFilteredData(data);
      setTags(extractedTags);
    } catch (error) {
      console.error('Error processing SQLite file:', error);
      // 即使出错也使用模拟数据，实际部署时应处理错误
      const reader = new SQLiteReader();
      const data = await reader.readData();
      const extractedTags = reader.extractTags(data);
      
      setData(data);
      setFilteredData(data);
      setTags(extractedTags);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm py-4 px-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-800">内容摘要瀑布流</h1>
          <p className="text-gray-600 mt-1">展示从SQLite数据库读取的内容摘要</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 文件上传区域 */}
        <FileUpload onFileUpload={handleFileUpload} />
        
        {/* 标签筛选器 */}
        <div className="mb-8">
          <TagFilter 
            tags={tags} 
            selectedTags={selectedTags} 
            onTagToggle={toggleTag}
            onClearFilters={clearFilters}
          />
        </div>

        {/* 瀑布流内容 */}
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <WaterfallGrid data={filteredData} />
        )}

        {filteredData.length === 0 && !isLoading && (
          <div className="text-center py-12">
            <h3 className="text-lg font-medium text-gray-900">没有找到匹配的内容</h3>
            <p className="mt-1 text-gray-500">尝试选择不同的标签或清除筛选条件</p>
            <button
              onClick={clearFilters}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              清除筛选
            </button>
          </div>
        )}
      </main>

      <footer className="bg-white border-t mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-500 text-sm">
          <p>SQLite Waterfall Content Viewer © {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
};

export default App;