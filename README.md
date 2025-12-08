# SQLite Waterfall Content Viewer

一个使用 React + TailwindCSS 构建的静态网站，用于离线读取 SQLite 数据并生成瀑布流内容展示，支持按标签筛选。

## 功能特点

- ✅ 瀑布流布局展示内容摘要
- ✅ 按标签筛选内容
- ✅ 响应式设计，支持 PC 和移动端访问
- ✅ 简洁明朗的界面风格
- ✅ 内容卡片包含标题、时间、摘要、原文链接和标签

## 项目结构

```
src/
├── components/
│   ├── ContentCard.jsx      # 内容卡片组件
│   ├── TagFilter.jsx        # 标签筛选组件
│   └── WaterfallGrid.jsx    # 瀑布流网格组件
├── utils/
│   └── sqliteReader.js      # SQLite读取工具
├── App.jsx                  # 主应用组件
├── main.jsx                 # 应用入口
├── index.css               # 全局样式
└── App.css                 # 应用样式
```

## 技术栈

- React 18
- TailwindCSS
- Vite
- JavaScript ES6+

## 安装和运行

1. 安装依赖：
```bash
npm install
# 或
yarn install
```

2. 启动开发服务器：
```bash
npm run dev
# 或
yarn dev
```

3. 构建生产版本：
```bash
npm run build
# 或
yarn build
```

## SQLite 数据读取

本项目设计用于读取包含以下字段的 SQLite 数据库：

- `id`: 内容唯一标识
- `title`: 标题
- `created_time`: 创建时间
- `summary`: 摘要内容
- `original_url`: 原文链接
- `tags`: 标签（逗号分隔）

在浏览器环境中，实际的 SQLite 文件读取需要使用 [sql.js](https://github.com/sql-js/sql.js) 库。当前实现使用模拟数据，实际部署时需要替换为真实的 SQLite 读取逻辑。

## 响应式设计

- 移动端：单列瀑布流
- 平板端：双列瀑布流
- 桌面端：三到四列瀑布流

## 使用说明

1. 启动应用后，系统会自动加载 SQLite 数据
2. 使用顶部标签筛选器筛选内容
3. 点击标签按钮可添加/移除筛选条件
4. 点击"查看原文"可跳转到原始链接
5. 悬停在卡片上可查看悬停效果

## 自定义

如需集成真实的 SQLite 文件读取功能，可以：

1. 安装 sql.js: `npm install sql.js`
2. 在 `src/utils/sqliteReader.js` 中实现真实的 SQLite 读取逻辑
3. 添加文件上传功能供用户上传 SQLite 文件

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 许可证

MIT