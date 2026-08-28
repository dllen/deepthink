import { CATEGORIES, getCategoryStyle } from '../utils/categories';

const CategoryFilter = ({ selectedCategory, onCategorySelect, counts }) => {
  return (
    <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-3 ring-1 ring-indigo-100">
      <div className="flex items-center justify-between mb-2.5 px-1">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">内容分类</h3>
        <span className="text-[10px] text-slate-400">七大类 · 单选</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onCategorySelect(null)}
          aria-pressed={!selectedCategory}
          className={`text-sm px-3.5 py-1.5 rounded-full font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 ${
            !selectedCategory
              ? 'bg-slate-800 text-white shadow-md scale-105'
              : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-slate-400'
          }`}
        >
          全部
          <span className="ml-1.5 text-[10px] opacity-70">
            {Object.values(counts || {}).reduce((a, b) => a + b, 0)}
          </span>
        </button>
        {CATEGORIES.map(({ key, icon }) => {
          const style = getCategoryStyle(key);
          const isActive = selectedCategory === key;
          const count = counts?.[key] || 0;
          return (
            <button
              key={key}
              onClick={() => onCategorySelect(key)}
              aria-pressed={isActive}
              className={`text-sm px-3.5 py-1.5 rounded-full font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ${
                isActive
                  ? `${style.pill} text-white shadow-md scale-105`
                  : `bg-white ${style.badge.split(' ')[1]} ring-1 ${style.badge.split(' ')[2]} hover:scale-105`
              }`}
            >
              <span className="mr-1">{icon}</span>{key}
              <span className={`ml-1.5 text-[10px] ${isActive ? 'opacity-80' : 'opacity-60'}`}>{count}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default CategoryFilter;