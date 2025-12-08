#!/bin/bash

# 构建 SQLite Waterfall Content Viewer 项目

echo "开始构建项目..."

# 安装依赖
echo "安装依赖..."
npm install

# 构建项目
echo "构建项目..."
npm run build

echo "构建完成！静态文件位于 dist/ 目录中。"

# 显示构建的文件
echo "构建的文件列表："
ls -la dist/