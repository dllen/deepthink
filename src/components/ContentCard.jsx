
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
    <div className="waterfall-item group bg-white rounded-2xl overflow-hidden flex flex-col h-full border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-indigo-100/50 hover:-translate-y-1 transition-all duration-300">
      <div className="p-5 flex-grow flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] font-bold tracking-wider text-indigo-500 bg-indigo-50 px-2 py-1 rounded-md uppercase">
            {formatDate(item.created_time)}
          </span>
          <a 
            href={item.original_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-indigo-500 transition-colors bg-slate-50 hover:bg-indigo-50 p-1.5 rounded-full"
            title="查看原文"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
              <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
            </svg>
          </a>
        </div>
        
        <h3 className="text-lg font-bold text-slate-800 mb-3 line-clamp-2 leading-snug group-hover:text-indigo-600 transition-colors">
          {item.title}
        </h3>
        
        <p className="text-slate-600 text-sm mb-5 flex-grow line-clamp-4 leading-relaxed">
          {item.summary}
        </p>
        
        <div className="mt-auto pt-4 border-t border-slate-50">
          <div className="flex flex-wrap gap-1.5">
            {item.tags.split(',').map((tag, index) => (
              <span 
                key={index}
                className="text-[11px] font-medium text-slate-500 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 px-2 py-1 rounded transition-colors cursor-default"
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