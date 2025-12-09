import React from 'react';

const TagFilter = ({ tags, selectedTags, onTagToggle, onClearFilters }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-gray-700">标签筛选:</span>
        <button
          onClick={onClearFilters}
          className={`text-sm px-3 py-1 rounded-full border ${
            selectedTags.length === 0
              ? 'bg-blue-500 text-white border-blue-500'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }`}
        >
          全部
        </button>
        {tags.map((tag) => (
          <button
            key={tag}
            onClick={() => onTagToggle(tag)}
            className={`tag-button text-sm px-3 py-1 rounded-full border ${
              selectedTags.includes(tag)
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>
      
      {selectedTags.length > 0 && (
        <div className="mt-3 flex items-center">
          <span className="text-sm text-gray-600 mr-2">已选择:</span>
          <div className="flex flex-wrap gap-1">
            {selectedTags.map((tag) => (
              <span
                key={tag}
                className="flex items-center bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full"
              >
                {tag}
                <button
                  onClick={() => onTagToggle(tag)}
                  className="ml-1 text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
            <button
              onClick={onClearFilters}
              className="text-xs text-gray-500 hover:text-gray-700 ml-2"
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