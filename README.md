# 网页内容抓取与摘要生成系统

## 项目概述

这是一个功能完整的Python程序，用于抓取网页内容、调用大模型API生成摘要，并将结果保存到SQLite数据库中。系统支持自动抓取和手工录入两种方式。

## 功能特性

### 1. 网页内容抓取
- 使用Selenium模拟浏览器访问，支持JavaScript渲染的页面
- 备用requests方法，兼容静态网页
- 智能内容提取，优先获取文章主体内容

### 2. 摘要生成
- 支持多种大模型API（OpenAI、本地模型等）
- 备用简单摘要算法
- 生成100-200字的核心观点摘要

### 3. 微博内容生成
- 自动格式化为适合微博发布的内容
- 控制内容长度，符合平台限制

### 4. 数据库管理
- SQLite数据库存储
- 包含标题、时间、摘要、原链接、标签等字段
- 标签字段支持索引，便于查询

### 5. 手工录入
- 支持手动输入内容进行处理
- 与自动抓取使用相同的处理流程

## 数据库表结构

### content_summary 表
- `id`: 主键，自增
- `title`: 标题，非空
- `created_time`: 创建时间，非空
- `summary`: 摘要内容，非空
- `original_url`: 原始链接，非空
- `tags`: 标签，可为空
- `idx_tags`: 标签索引

### manual_content 表
- `id`: 主键，自增
- `title`: 标题，非空
- `content`: 原始内容，非空
- `created_time`: 创建时间，非空
- `summary`: 摘要内容，可为空
- `tags`: 标签，可为空

## 安装依赖

```bash
pip install -r requirements.txt
```

需要的依赖包：
- requests
- beautifulsoup4
- selenium
- openai
- lxml
- urllib3

## 配置API密钥

### OpenAI API
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

### 本地模型（如Ollama）
```bash
export OLLAMA_API_URL="http://localhost:11434/api/generate"
export OLLAMA_MODEL="llama2"
```

## 使用方法

### 1. 启动系统
```bash
python web_content_extractor_simple.py
```

### 2. 系统菜单
- **1. 抓取网页内容**: 输入URL自动抓取并处理
- **2. 手工录入内容**: 手动输入内容进行处理
- **3. 查看数据库内容**: 显示最近的抓取记录
- **4. 帮助信息**: 显示使用帮助
- **5. 退出系统**: 退出程序

### 3. 示例使用

#### 抓取网页
```
选择 1 → 输入URL → 输入标签（可选）→ 系统自动处理
```

#### 手工录入
```
选择 2 → 输入标题 → 输入内容 → 输入标签（可选）→ 系统处理
```

## 技术实现细节

### 内容抓取策略
1. 优先使用Selenium模拟浏览器访问
2. 获取页面标题和主要内容
3. 尝试定位article、main等语义化标签
4. 备用方案：提取所有段落内容

### 摘要生成策略
1. 优先调用OpenAI API
2. 尝试本地模型API（如Ollama）
3. 备用简单摘要算法

### 错误处理
- 浏览器启动失败时使用requests备选
- API调用失败时使用简单摘要
- 内容抓取失败时提供错误提示

## 文件结构

```
/workspace/
├── web_content_extractor_simple.py    # 主程序文件
├── requirements.txt                   # 依赖包列表
├── test_system.py                     # 功能测试脚本
├── web_content.db                     # 生成的数据库文件（运行后创建）
└── README.md                          # 本说明文档
```

## 环境要求

- Python 3.8+
- Chrome浏览器（可选，用于Selenium）
- ChromeDriver（可选，用于Selenium）

## 扩展功能

系统设计具有良好的扩展性，可以轻松添加：

1. 更多API支持（DeepSeek、通义千问等）
2. 更多内容抓取方法
3. 不同的摘要生成策略
4. 导出功能
5. 定时任务功能

## 注意事项

1. 首次运行会自动创建数据库文件
2. API密钥需要自行配置
3. 某些网站可能有反爬虫机制
4. 本地模型需要单独部署（如Ollama）

## 许可证

本项目为示例代码，可根据需要自由使用和修改。