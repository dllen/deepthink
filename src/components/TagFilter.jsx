
const TagFilter = ({ tags, selectedTags, onTagToggle, onClearFilters }) => {
  return (
    <div className="bg-white/50 backdrop-blur-sm rounded-2xl p-1">
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onClearFilters}
          className={`text-sm px-4 py-1.5 rounded-full transition-all duration-200 font-medium ${
            selectedTags.length === 0
              ? 'bg-indigo-500 text-white shadow-md shadow-indigo-200 transform scale-105'
              : 'text-slate-600 hover:bg-white hover:shadow-sm'
          }`}
        >
          全部内容
        </button>
        {tags.map((tag) => (
          <button
            key={tag}
            onClick={() => onTagToggle(tag)}
            className={`tag-button text-sm px-4 py-1.5 rounded-full transition-all duration-200 border ${
              selectedTags.includes(tag)
                ? 'bg-indigo-500 text-white border-transparent shadow-md shadow-indigo-200 transform scale-105'
                : 'bg-white text-slate-600 border-slate-100 hover:border-indigo-200 hover:text-indigo-600'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
      
      {selectedTags.length > 0 && (
        <div className="mt-4 pt-3 border-t border-indigo-50 flex items-center animate-fadeIn">
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mr-3">已选标签:</span>
          <div className="flex flex-wrap gap-2">
            {selectedTags.map((tag) => (
              <span
                key={tag}
                className="flex items-center bg-indigo-50 text-indigo-700 text-xs px-3 py-1 rounded-full border border-indigo-100"
              >
                {tag}
                <button
                  onClick={() => onTagToggle(tag)}
                  className="ml-1.5 text-indigo-400 hover:text-indigo-600 focus:outline-none"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                    <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                  </svg>
                </button>
              </span>
            ))}
            <button
              onClick={onClearFilters}
              className="text-xs text-slate-400 hover:text-slate-600 ml-2 underline decoration-dashed underline-offset-2"
            >
              清除全部
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TagFilter;