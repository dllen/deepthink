# 观念棱镜（DeepThink）

一个使用 React + Vite + TailwindCSS 构建的静态内容瀑布流站点。内容由 Python 后端抓取、摘要、分类后写入 SQLite；构建前把 DB 导出为静态数据模块，站点运行时不需要服务器或数据库。

## 功能特点

- ✅ 瀑布流布局展示内容摘要
- ✅ 按七分类筛选：科技动态 / 文章 / 工具 / 资源 / 图片 / 文摘 / 言论
- ✅ 按标签筛选内容
- ✅ 基于 Fuse.js 的标题/摘要搜索
- ✅ 分析报告与信息源头栏目
- ✅ 信息检索视图（跨源搜索入口）
- ✅ 响应式设计，支持 PC 和移动端访问

## 项目结构

```
public/                     # 独立静态页面
src/
├── components/             # 内容卡片、筛选器、瀑布流、报告/信息源等组件
├── utils/                  # categories.js、formatDate.js、searchUtils.js
├── assets/                 # static-data.json/.js（生成物）、报告/链接/信息源数据
├── App.jsx                 # 主应用组件
├── main.jsx                # 应用入口
└── App.css                 # 应用样式
python_scripts/             # 抓取、摘要、分类并写入 SQLite
scripts/                    # generate-data.js、check-data.mjs、加密脚本
```

## 技术栈

- React 18
- TailwindCSS
- Vite
- JavaScript ES6+

## 安装和运行

要求 Node.js ≥ 20.0.0。

```bash
npm install     # 安装依赖
npm run dev     # 启动开发服务器
npm run build   # 构建生产版本
npm run preview # 预览生产构建
npm run lint    # ESLint
```

仓库不跟踪 `package-lock.json`，CI 使用 `npm install --legacy-peer-deps`。

## 数据从哪来

- 真源：`python_scripts/web_content.db`（SQLite）
- 生成：`npm run gen:static-js` 把 DB 导出为 `src/assets/static-data.json` 与 `src/assets/static-data.js`
- 校验：`npm run check:data` 确认生成物与 DB 一致
- 两个数据文件都是生成物，不要手工编辑；改内容请改 DB，或用 `python_scripts/set_category.py` 修正分类
- `category` 是 DB 的列（七类之一），抓取入库时由 `python_scripts/category_classifier.py` 自动分类
- 生成器只读 `content_summary`，一次性重写两个生成物；不做增量合并，也不产生快照

## 每周更新内容

1. 抓取：`cd python_scripts && python3 fetch_from_params.py` 或 `python3 crawler_subpages.py`
2. 生成：`npm run gen:static-js`
3. 校验（可选）：`npm run check:data`
4. 本地预览：`npm run dev`
5. 提交并推送：`git add -A && git commit -m "chore(content): ..." && git push`
6. 推送后 GitHub Actions 自动部署到 GitHub Pages

需要人工修正某条内容的分类时：

```bash
cd python_scripts
python3 set_category.py --url <原文链接> <七类之一>
# 或用 --id <行 id> 定位
```

## 构建与部署

- `npm run build` 生成 `dist/`。
- CI（`.github/workflows/deploy.yml`）在 build 前执行 `npm run test:data` 与 `npm run check:data`。
- CI **不重新生成数据**，直接部署提交的 `static-data.json` / `static-data.js`；更新内容后必须提交这两个生成物。
- 推送到 `main` 后自动部署到 `gh-pages` 分支。

## 使用说明

1. 启动应用后，页面加载构建时打包的静态内容
2. 使用顶部分类或标签筛选器筛选内容
3. 使用搜索框按标题、摘要搜索
4. 点击"查看原文"可跳转到原始链接
5. 通过顶部"信息检索"切换到跨源搜索视图

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 许可证

MIT
