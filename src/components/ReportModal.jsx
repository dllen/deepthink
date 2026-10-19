import { useEffect, useRef, useState } from 'react';
import { formatDate } from '../utils/formatDate';

const ReportModal = ({ report, onClose }) => {
  const [status, setStatus] = useState('loading'); // loading | ready | error
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const openerRef = useRef(null);

  useEffect(() => {
    // 记录打开弹窗前的焦点元素，关闭时归还
    openerRef.current = document.activeElement;
    closeRef.current?.focus();

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusables = dialogRef.current.querySelectorAll(
        'a[href], button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])',
      );
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      openerRef.current?.focus?.();
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
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-modal-title"
        className="relative w-full max-w-6xl h-[90vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* 顶栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80 shrink-0">
          <div>
            <h2 id="report-modal-title" className="text-lg font-bold text-slate-800">{report.title}</h2>
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
              ref={closeRef}
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
        <div className="relative flex-1 bg-white">
          {status === 'loading' && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500">
              报告加载中…
            </div>
          )}
          {status === 'error' && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500">
              报告加载失败，请尝试「新窗口」打开
            </div>
          )}
          <iframe
            src={report.path}
            title={report.title}
            className="w-full h-full border-0"
            sandbox="allow-scripts"
            onLoad={() => setStatus('ready')}
            onError={() => setStatus('error')}
          />
        </div>
      </div>
    </div>
  );
};

export default ReportModal;
