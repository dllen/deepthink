import { useEffect } from 'react';
import { formatDate } from '../utils/formatDate';

const ReportModal = ({ report, onClose }) => {
  // 按 Escape 关闭
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* 遮罩 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 弹窗 */}
      <div className="relative w-full max-w-6xl h-[90vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        {/* 顶栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80 shrink-0">
          <div>
            <h2 className="text-lg font-bold text-slate-800">{report.title}</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {formatDate(report.date)}
              {report.tags?.length > 0 && (
                <span className="ml-2">
                  {report.tags.map((t) => (
                    <span key={t} className="inline-block ml-1 text-[10px] bg-amber-50 text-amber-600 px-1.5 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* 新窗口打开 */}
            <a
              href={report.path}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
              title="在新窗口打开"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
                <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
              </svg>
              新窗口
            </a>
            {/* 关闭按钮 */}
            <button
              onClick={onClose}
              aria-label="关闭"
              className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>

        {/* iframe 内容区 */}
        <div className="flex-1 bg-white">
          <iframe
            src={report.path}
            title={report.title}
            className="w-full h-full border-0"
            sandbox=""
          />
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
