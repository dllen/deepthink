# 内容清理记录（2026-10-19）

一次性的数据清理：删除抓取噪声与重复内容，并给抓取脚本加入库过滤规则，防止再次发生。

## 决策规则（用户确认）

1. **噪声全删**：导航 / 登录 / 特殊页面 / 列表页 / 招聘帖一律删除。
2. **周刊只保留 GitHub 官方源**（`github.com/ruanyf/weekly/blob/master/docs/issue-N.md`），
   vibecodinghub 镜像全部删除。
3. **wiki 文章重复只保留内容更长的一版**（同一篇文章被 `/index.php/<标题>` 与
   `/<标题>` 两种 URL 形式各抓了一次）。
4. 一次性删除用「精确 id 列表 + 事务 + 删除前后计数断言」，不用启发式 SQL。

## 删除明细（38 行，224 → 186）

| 分组 | 行数 | id |
| --- | --- | --- |
| 抓取噪声 | 8 | 129, 225, 226, 227, 229, 230, 473, 474 |
| 周刊镜像（保留 GitHub 288–299） | 13 | 273–285 |
| wiki URL 变体重复（保留内容更长者） | 17 | 21, 22, 23, 24, 26, 28, 29, 30, 31, 33, 34, 35, 116, 118, 120, 128, 210 |

删除的噪声：`所有页面`（2 条）、`登录`、`个人维基`首页、`需要登录`、`特殊页面`、
`Issues · ruanyf/weekly` 列表页、`谁在招人？（2026年8月）`。

删除前备份：`python_scripts/backups/web_content-cleanup-20261019-130729.db`（本地、gitignored、chmod 600）。

## 清理后状态

- `content_summary` **186 行**；`PRAGMA integrity_check` = ok；id 唯一；`category` 无缺失；`uid` 无 NULL。
- 分类分布：文章 111 / 文摘 35 / 工具 20 / 言论 8 / 资源 6 / 科技动态 4 / 图片 2。
- 来源分布：legacy-default 86 / llm 68 / manual 32。
- 生成物：`src/assets/static-data.json` + `static-data.js` 各 186 条（`npm run gen:static-js -- --allow-shrink`，224 → 186 = −17% 触发缩水保护，已显式放行）。
- 加密副本：`python_scripts/web_content.db.enc` 2,101,280 B；解密往返 sha256 与明文一致（`cee6db0c64fb74bd23c53d105c8cda3de92aeff3ab1e8862d1ed7f1eaf23d897`）。

## 防止复发（代码改动）

`python_scripts/crawler_subpages.py`：

- `is_skippable_link()`：新增 MediaWiki `特殊:`/`Special:` 路径与 `returnto=`、`title=special:`、
  `pagesetting` 查询参数过滤（同时匹配解码后的中文与百分号编码形式）。
- `is_noise_title()`：站点 chrome 标题（`所有页面` / `特殊页面` / `登录` / `需要登录` /
  `个人维基` 首页 / `Issues · …` 列表）不入库。
- `title_exists()`：入库前若 DB 已有完全相同标题则跳过，挡住「同一文章两种 URL」的镜像重复。
- `ROOT_URLS`：移除 vibecodinghub 镜像根；GitHub issues 列表页与仓库根标记 `skip_root`，
  列表页本身不再被当成内容入库。
- 新增 `python_scripts/test_crawler_filters.py`（30 个用例）覆盖以上规则。

## 验证证据

- `python3 -m pytest test_category_classifier.py test_set_category.py test_migrate_category.py test_ingestion_category.py test_crawler_filters.py test_modular.py -q` → 82 passed。
- `npm run test:data` → 23/23 pass；`npm run check:data` → 「DB 与生成物一致，共 186 条」。
- `npm run lint` → 0 problems；`npm run build` → 成功（`dist/assets/index-dd97e602.js` 287.45 kB / gzip 125.58 kB）。
- 解密 `.enc` 后行数 186、sha256 与明文一致。

## 已知遗留（本轮未处理）

- `chuan.us`（id 1、6）、`笑来搜`（id 3/37/38/39，4 个不同页面）、`首页 - 个人维基`（id 2/123/126）
  仍是同标题多行；用户选择的清理范围只到 wiki 文章与周刊。
- `original_url` 重复 1 组：id 488/489 是同一期周刊（issue 410）里的两篇文章，指向同一 URL，
  生成器会给出警告但不阻塞。若要消除，需人工改其中一条的 `original_url`。
