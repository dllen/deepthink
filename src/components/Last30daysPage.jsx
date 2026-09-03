import { useState } from 'react';
import SearchHero from './SearchHero';
import SourcesGrid from './SourcesGrid';
import PhilosophySection from './PhilosophySection';

const Last30daysPage = () => {
  const [query, setQuery] = useState('');

  return (
    <div className="py-8">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-sky-500 mb-2">
          信息检索
        </h1>
        <p className="text-slate-500">
          跨越 13 个平台，追踪真实的人类声音
        </p>
      </div>

      {/* 搜索英雄区 */}
      <SearchHero />

      {/* 理念说明区 */}
      <PhilosophySection />

      {/* 信息源卡片网格 */}
      <SourcesGrid query={query} />
    </div>
  );
};

export default Last30daysPage;
