import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';

const SearchBar = ({ searchQuery, onSearchChange, onClearSearch }) => {
  return (
    <div className="bg-white/50 backdrop-blur-sm rounded-2xl p-4">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-5 w-5 text-slate-400" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索标题、内容或摘要..."
          className="block w-full pl-11 pr-12 py-3 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
        />
        {searchQuery && (
          <button
            onClick={onClearSearch}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Clear search"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        )}
      </div>
      {searchQuery && (
        <div className="mt-2 text-xs text-slate-500">
          <span className="font-medium">搜索中:</span> {searchQuery}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
