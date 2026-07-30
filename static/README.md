# 静态页面 / Static Pages

此目录存放独立的静态 HTML 页面，与 Vite 构建流程分离。

## 已有页面

| 文件 | 描述 |
|------|------|
| `A股行业财政乘数矩阵看板.html` | A股行业财政乘数 × 信贷传导矩阵看板 |

## 使用方式

在浏览器中直接打开 `.html` 文件，或通过任意静态服务器托管：

```bash
# 使用 Python 内置服务器
python3 -m http.server 8080 --directory static

# 使用 Node.js serve
npx serve static
```
