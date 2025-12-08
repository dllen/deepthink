import React from 'react';

const ContentCard = ({ item }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="waterfall-item bg-white rounded-xl overflow-hidden flex flex-col h-full">
      <div className="p-5 flex-grow flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-medium text-blue-500 bg-blue-50 px-2 py-1 rounded">
            {formatDate(item.created_time)}
          </span>
          <a 
            href={item.original_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-blue-500 transition-colors"
          >
            查看原文
          </a>
        </div>
        
        <h3 className="text-lg font-semibold text-gray-800 mb-3 line-clamp-2">
          {item.title}
        </h3>
        
        <p className="text-gray-600 text-sm mb-4 flex-grow line-clamp-3">
          {item.summary}
        </p>
        
        <div className="mt-auto pt-3">
          <div className="flex flex-wrap gap-1">
            {item.tags.split(',').map((tag, index) => (
              <span 
                key={index}
                className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-1 rounded"
              >
                #{tag.trim()}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContentCard;