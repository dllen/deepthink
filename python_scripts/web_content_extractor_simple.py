"""
网页内容抓取与摘要生成系统（简化版）
功能：
1. 抓取网页链接内容
2. 调用大模型API生成摘要
3. 生成微博内容
4. 存储到SQLite数据库
5. 支持手工录入
6. 使用浏览器模拟用户访问
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI
import sys


class WebContentExtractor:
    def __init__(self):
        self.setup_database()
        self.setup_browser()
        
    def setup_database(self):
        """创建SQLite数据库和表"""
        self.conn = sqlite3.connect('web_content.db')
        cursor = self.conn.cursor()
        
        # 创建内容表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_time TEXT NOT NULL,
                summary TEXT NOT NULL,
                original_url TEXT NOT NULL,
                tags TEXT
            )
        ''')
        
        # 为tags字段创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON content_summary (tags)')
        
        # 创建手工录入表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manual_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_time TEXT NOT NULL,
                summary TEXT,
                tags TEXT
            )
        ''')
        
        self.conn.commit()
    
    def setup_browser(self):
        """设置浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 后台运行
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            print(f"无法启动Chrome浏览器: {e}")
            print("请确保已安装Chrome浏览器和ChromeDriver")
            # 如果Chrome不可用，使用requests作为备选
            self.driver = None
    
    def extract_content_with_browser(self, url):
        """使用浏览器模拟用户访问抓取内容"""
        if self.driver is None:
            return self.extract_content_with_requests(url)
        
        try:
            self.driver.get(url)
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 获取页面标题
            title = self.driver.title
            
            # 尝试获取更精确的内容（文章类）
            content = ""
            
            # 优先查找文章相关标签
            article_elements = self.driver.find_elements(By.TAG_NAME, "article")
            if article_elements:
                content = " ".join([elem.text for elem in article_elements])
            else:
                # 尝试获取主要内容区域
                main_elements = self.driver.find_elements(By.TAG_NAME, "main")
                if main_elements:
                    content = main_elements[0].text
                else:
                    # 尝试获取有特定类名的div
                    content_divs = self.driver.find_elements(By.CSS_SELECTOR, 
                        "div[class*='content'], div[class*='article'], div[class*='post'], div[class*='main']")
                    if content_divs:
                        content = " ".join([elem.text for elem in content_divs])
                    else:
                        # 获取所有段落
                        p_elements = self.driver.find_elements(By.TAG_NAME, "p")
                        content = " ".join([p.text for p in p_elements if len(p.text) > 20])
            
            # 如果内容太短，尝试获取body内容
            if len(content) < 100:
                body_element = self.driver.find_element(By.TAG_NAME, "body")
                content = body_element.text
            
            return title.strip(), content.strip()
            
        except Exception as e:
            print(f"浏览器抓取失败，尝试使用requests: {e}")
            return self.extract_content_with_requests(url)
    
    def extract_content_with_requests(self, url):
        """使用requests库抓取内容（备用方法）"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式元素
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            title = soup.title.string if soup.title else "无标题"
            
            # 尝试获取文章内容
            article_content = soup.find('article')
            if article_content:
                content = article_content.get_text()
            else:
                # 尝试获取主要文章区域
                main_content = (soup.find('main') or 
                               soup.find('div', class_=re.compile(r'article|content|main|post|entry')) or
                               soup.find('section', class_=re.compile(r'article|content|main|post|entry')))
                if main_content:
                    content = main_content.get_text()
                else:
                    # 获取所有段落
                    paragraphs = soup.find_all('p')
                    content = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
            
            # 清理内容
            content = re.sub(r'\s+', ' ', content).strip()
            
            return title.strip(), content
            
        except Exception as e:
            print(f"使用requests抓取失败: {e}")
            return "抓取失败", "无法获取页面内容"
    
    def generate_summary_with_api(self, content, title):
        """使用大模型API生成摘要"""
        # 尝试多种API
        summary = self.try_openai_api(content, title)
        if summary and summary != "摘要生成失败":
            return summary
        
        summary = self.try_local_model_api(content, title)
        if summary and summary != "摘要生成失败":
            return summary
        
        # 如果API都失败，使用简单摘要算法
        return self.generate_simple_summary(content, title)
    
    def try_openai_api(self, content, title):
        """尝试使用OpenAI API"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return "摘要生成失败"
                
            client = OpenAI(
                api_key=api_key
            )
            
            prompt = f"""
            请为以下文章生成一个简洁准确的摘要，字数在100-200字之间：

            文章标题: {title}

            文章内容: {content[:3000]}

            请生成摘要:
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API调用失败: {e}")
            return "摘要生成失败"
    
    def try_local_model_api(self, content, title):
        """尝试使用本地模型API（如Ollama）"""
        try:
            # 尝试Ollama API
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
            import json
            
            prompt = f"""
            请为以下文章生成一个简洁准确的摘要，字数在100-200字之间：

            文章标题: {title}

            文章内容: {content[:3000]}

            请生成摘要:
            """
            
            data = {
                "model": os.getenv("OLLAMA_MODEL", "llama2"),
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(ollama_url, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "摘要生成失败").strip()
            
        except Exception as e:
            print(f"本地模型API调用失败: {e}")
        
        return "摘要生成失败"
    
    def generate_simple_summary(self, content, title):
        """使用简单算法生成摘要（当API不可用时的备选方案）"""
        try:
            # 简单摘要算法：提取前几段落的关键句子
            paragraphs = [p.strip() for p in content.split('\n') if len(p.strip()) > 20]
            
            if not paragraphs:
                return content[:200] + "..." if len(content) > 200 else content
            
            # 取前几个段落
            summary_parts = []
            total_chars = 0
            
            for para in paragraphs:
                if total_chars >= 100:  # 至少100字
                    break
                summary_parts.append(para)
                total_chars += len(para)
            
            summary = " ".join(summary_parts)
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            return summary
        except Exception as e:
            print(f"简单摘要生成失败: {e}")
            return content[:200] + "..." if len(content) > 200 else content
    
    def generate_weibo_content(self, title, summary, url):
        """生成微博内容"""
        # 微博标题限制
        title_part = title[:20] if len(title) > 20 else title
        # 摘要部分
        summary_part = summary[:80] if len(summary) > 80 else summary
        
        weibo_content = f"【{title_part}】{summary_part} 更多内容: {url}"
        
        # 确保总长度适合微博
        if len(weibo_content) > 140:
            weibo_content = f"【{title_part}】{summary_part[:60]}... 详情: {url}"
        
        return weibo_content
    
    def save_to_database(self, title, summary, url, tags=""):
        """保存到数据库"""
        cursor = self.conn.cursor()
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO content_summary (title, created_time, summary, original_url, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, created_time, summary, url, tags))
        
        self.conn.commit()
        print(f"✓ 内容已保存到数据库: {title[:50]}...")
    
    def manual_input(self, title, content, tags=""):
        """手工录入内容"""
        print("正在生成摘要...")
        summary = self.generate_summary_with_api(content, title)
        
        cursor = self.conn.cursor()
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO manual_content (title, content, created_time, summary, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, created_time, summary, tags))
        
        self.conn.commit()
        print(f"✓ 手工录入内容已保存: {title[:50]}...")
        return summary
    
    def scrape_and_process(self, url, tags=""):
        """抓取并处理网页"""
        print(f"🔍 开始抓取: {url}")
        
        title, content = self.extract_content_with_browser(url)
        
        if not content or len(content.strip()) == 0 or "抓取失败" in title:
            print("❌ 无法抓取到有效内容")
            return False
        
        print(f"✅ 抓取成功 - 标题: {title[:50]}{'...' if len(title) > 50 else ''}")
        print(f"📊 内容长度: {len(content)} 字符")
        
        # 生成摘要
        print("⏳ 正在生成摘要...")
        summary = self.generate_summary_with_api(content, title)
        print(f"📋 摘要: {summary}")
        
        # 生成微博内容
        weibo_content = self.generate_weibo_content(title, summary, url)
        print(f">Weibo: {weibo_content}")
        
        # 保存到数据库
        self.save_to_database(title, summary, url, tags)
        
        return True
    
    def view_recent_records(self, limit=10):
        """查看最近的记录"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM content_summary ORDER BY id DESC LIMIT ?", (limit,))
        results = cursor.fetchall()
        
        if not results:
            print("暂无抓取记录")
            return
        
        print(f"\n📊 最近{len(results)}条抓取记录:")
        print("="*80)
        for row in results:
            print(f"ID: {row[0]}")
            print(f"标题: {row[1][:50]}{'...' if len(row[1]) > 50 else ''}")
            print(f"时间: {row[2]}")
            print(f"摘要: {row[3][:100]}{'...' if len(row[3]) > 100 else ''}")
            print(f"URL: {row[4][:50]}{'...' if len(row[4]) > 50 else ''}")
            print(f"标签: {row[5] if row[5] else '无'}")
            print("-" * 80)
    
    def close(self):
        """关闭资源"""
        if hasattr(self, 'conn'):
            self.conn.close()
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()


def main():
    print("🚀 网页内容抓取与摘要生成系统")
    print("初始化中...")
    
    try:
        extractor = WebContentExtractor()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("请确保已安装所需依赖包: pip install -r requirements.txt")
        return
    
    print("✅ 系统初始化完成")
    
    try:
        while True:
            print("\n" + "="*50)
            print("📋 请选择操作:")
            print("1. 🕸️  抓取网页内容")
            print("2. ✍️  手工录入内容")
            print("3. 📖 查看数据库内容")
            print("4. ❓ 帮助信息")
            print("5. 🚪 退出系统")
            
            choice = input("\n请输入选择 (1-5): ").strip()
            
            if choice == "1":
                url = input("\n🔗 请输入网页URL: ").strip()
                if url:
                    tags = input("🏷️  请输入标签 (可选，多个标签用逗号分隔): ").strip()
                    extractor.scrape_and_process(url, tags)
                else:
                    print("❌ URL不能为空")
            
            elif choice == "2":
                title = input("\n📝 请输入标题: ").strip()
                content = input("📄 请输入内容: ").strip()
                if title and content:
                    tags = input("🏷️  请输入标签 (可选，多个标签用逗号分隔): ").strip()
                    summary = extractor.manual_input(title, content, tags)
                    print(f"\n📋 生成的摘要: {summary}")
                else:
                    print("❌ 标题和内容不能为空")
            
            elif choice == "3":
                try:
                    limit = input("\n📊 查看最近几条记录? (默认10条): ").strip()
                    limit = int(limit) if limit else 10
                except ValueError:
                    limit = 10
                extractor.view_recent_records(limit)
            
            elif choice == "4":
                print("\n📖 使用帮助:")
                print("• 抓取网页内容: 输入网页URL，系统将自动抓取内容、生成摘要并保存")
                print("• 手工录入内容: 手动输入标题和内容，系统生成摘要并保存")
                print("• 查看数据库内容: 显示最近抓取的记录")
                print("\n🔧 API配置:")
                print("• 设置环境变量 OPENAI_API_KEY 来使用OpenAI API")
                print("• 设置环境变量 OLLAMA_API_URL 来使用本地模型")
            
            elif choice == "5":
                print("\n👋 感谢使用，再见！")
                break
            
            else:
                print("\n❌ 无效选择，请重新输入")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
    
    finally:
        extractor.close()


if __name__ == "__main__":
    main()