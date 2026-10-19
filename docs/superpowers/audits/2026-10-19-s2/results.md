# S2 前端修复生产复验（2026-10-19）

- 环境：`https://deepthink.global`（部署 commit `6bf8b8b`），Chrome 155 headless + CDP，只读。
- 视口：桌面 **1440×900**、移动 **375×812**（DPR 2，移动仿真）。
- 数据量：224 条；报告页 1 篇；信息源 13 个。

| # | 检查项 | 结论 | 关键证据 |
|---|---|---|---|
| 1 | Tab 与 URL | **PASS** | 点「信息检索」→ `#/search`；刷新仍在 `#/search`（panel-search 可见、aria-selected 正确）；`history.back()` → `#/browse`（panel-browse）；搜索词 `AI agent` 浏览↔检索来回后保留 |
| 2 | 搜索页源卡 | **PASS** | 13 张源卡 + 13 个快速跳转链接，26 个链接全部带 `AI%20agent`，`target=_blank`、`rel="noopener noreferrer"`；arXiv 为 `searchtype=all&query=`，打开返回 12,373 条结果；Enter 打开新标签 `duckduckgo.com/?q=AI+agent`（标题 “AI agent at DuckDuckGo”） |
| 3 | 空态全清 | **PASS** | 选「工具」+ 标签「AI」+ 搜索 `zzzz_none` → 0 条/0 卡/空态；点「清除所有筛选」→ 搜索框 `''`、分类回「全部 224」、标签清空、224 卡恢复、空态消失 |
| 4 | Sticky | **PASS** | 桌面仅 1 个筛选吸附块（top 80、高 263、与页头 69 无重叠），滚动 3200px 仍无重叠，块下方可见 5 张卡且分类可点击（点「工具」→ 20 条）；375px 筛选块 `position: static`（不吸附）、页头 65px 单行、`scrollWidth=375` 无横向滚动 |
| 5 | 报告弹窗 | **PASS** | dialog + aria-modal + aria-labelledby；约 3s 后 loading 消失；iframe 内 canvas 574×520 已绘制（抽样 8212 个非透明像素）、两张表 31/31 行、榜单 155 节点、筛选 chips 4/3；焦点在「关闭」按钮，Tab 在「关闭 ↔ 新窗口」循环；Esc 关闭后焦点回到触发卡片 |
| 6 | 可访问性抽查 | **PASS** | `role=tab` + `aria-selected` + `aria-controls`，tabpanel 有 `aria-labelledby`；7 个激活分类 pill 对比度 5.02–7.90（≥4.5）；favicon `/logo.svg` 200（非 404）；页脚 4.76、日期 4.55、tag chip 6.92 |

## 观察（非 FAIL）

- 桌面合并后的筛选吸附块高 263px（约占 1440×900 视口的 29%），卡片在其下方可见、可点击；这是设计取舍，未遮挡可交互内容。
- 报告弹窗首屏约 3s 才 ready（报告页依赖 Google Fonts + Chart.js CDN）；loading 覆盖层会正常消失，未出现误判失败。
- 375px 下页头隐藏副标题与条数（`hidden sm:block`），品牌标题为 `div`（视觉标题不含语义），移动端仅靠 sr-only `h1` 提供标题语义。
- Enter 键行为依赖表单提交，实测有效；重复 submit 只在 CDP 同时派发 keydown+char 时出现，正常按键仅一次。
- Enter 打开的 DuckDuckGo 新标签 URL/标题正确（`?q=AI+agent` / "AI agent at DuckDuckGo"）；截图 `24` 显示的 CAPTCHA 是无头浏览器自动化触发，非站点问题。

## 截图（`docs/superpowers/audits/2026-10-19-s2/`）

- T1 桌面：`01-t1-desktop-search-url.png`、`02-t1-desktop-back-to-browse.png`、`03-t1-desktop-search-term-kept.png`、`23-t1-desktop-reload-search.png`
- T1 移动：`04-t1-mobile-search-url.png`
- T2 桌面：`05-t2-desktop-source-links.png`、`06-t2-arxiv-results.png`、`24-t2-enter-duckduckgo.png`
- T2 移动：`07-t2-mobile-source-links.png`、`08-t2-mobile-source-cards.png`
- T3 桌面：`10-t3-desktop-empty-state-before-clear.png`、`11-t3-desktop-after-clear-all.png`
- T3 移动：`12-t3-mobile-empty-state.png`、`13-t3-mobile-after-clear-all.png`
- T4 桌面：`14-t4-desktop-sticky.png`；移动：`15-t4-mobile-not-sticky.png`、`25-t4-mobile-scrolled.png`
- T5 桌面：`16-t5-desktop-report-modal.png`；移动：`17-t5-mobile-report-modal.png`
- T6 桌面：`20-t6-desktop-a11y.png`、`21-t6-desktop-footer.png`；移动：`22-t6-mobile-a11y.png`
