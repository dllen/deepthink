import { useState } from 'react';
import staticReports from '../assets/static-reports';
import ReportModal from './ReportModal';
import { formatDate } from '../utils/formatDate';

const ReportsPanel = () => {
  const [activeReport, setActiveReport] = useState(null);

  if (!staticReports || staticReports.length === 0) return null;

  return (
    <>
      <section className="mb-8">
        {/* 栏目标题 */}
        <div className="flex items-center gap-3 mb-5">
          <div className="h-1 w-8 rounded-full bg-gradient-to-r from-amber-500 to-orange-500" />
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-amber-500">
              <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clipRule="evenodd" />
            </svg>
            分析报告
          </h2>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {staticReports.length} 篇
          </span>
        </div>

        {/* 报告卡片列表 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {staticReports.map((report) => (
            <div
              key={report.id}
              role="button"
              tabIndex={0}
              aria-label={`查看分析报告: ${report.title}`}
              onClick={() => setActiveReport(report)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setActiveReport(report);
                }
              }}
              className="group bg-white rounded-xl border border-slate-200 hover:border-amber-300 hover:shadow-lg hover:shadow-amber-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 transition-all duration-300 overflow-hidden cursor-pointer"
            >
              {/* 卡片顶部色条 */}
              <div className="h-1.5 bg-gradient-to-r from-amber-400 to-orange-400 group-hover:from-amber-500 group-hover:to-orange-500 transition-colors" />

              <div className="p-5">
                {/* 日期和标签 */}
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-slate-400">
                    {formatDate(report.date)}
                  </span>
                  <div className="flex gap-1">
                    {report.tags?.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* 标题 */}
                <h3 className="text-base font-bold text-slate-800 mb-2 group-hover:text-amber-600 transition-colors leading-snug">
                  {report.title}
                </h3>

                {/* 描述 */}
                <p className="text-sm text-slate-500 leading-relaxed line-clamp-2 mb-4">
                  {report.description}
                </p>

                {/* 查看按钮 */}
                <div className="flex items-center gap-1.5 text-sm font-medium text-amber-600 group-hover:text-amber-700 transition-colors">
                  <span>查看详情</span>
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 group-hover:translate-x-0.5 transition-transform">
                    <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 详情弹窗 */}
      {activeReport && (
        <ReportModal
          report={activeReport}
          onClose={() => setActiveReport(null)}
        />
      )}
    </>
  );
};

export default ReportsPanel;
