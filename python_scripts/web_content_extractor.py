"""
网页内容抓取与摘要生成系统
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
import time
from datetime import datetime
import webbrowser
import tempfile
import os
from urllib.parse import urljoin, urlparse
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import openai
from openai import OpenAI


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
                tags TEXT,
                INDEX idx_tags (tags)
            )
        ''')
        
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
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"无法启动Chrome浏览器: {e}")
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
            
            # 获取页面内容
            body_element = self.driver.find_element(By.TAG_NAME, "body")
            content = body_element.text
            
            # 尝试获取更精确的内容（文章类）
            article_elements = self.driver.find_elements(By.TAG_NAME, "article")
            if article_elements:
                content = " ".join([elem.text for elem in article_elements])
            else:
                # 尝试获取主要内容区域
                main_elements = self.driver.find_elements(By.TAG_NAME, "main")
                if main_elements:
                    content = main_elements[0].text
                else:
                    # 获取所有段落
                    p_elements = self.driver.find_elements(By.TAG_NAME, "p")
                    content = " ".join([p.text for p in p_elements if len(p.text) > 20])
            
            return title, content
            
        except Exception as e:
            print(f"浏览器抓取失败，尝试使用requests: {e}")
            return self.extract_content_with_requests(url)
    
    def extract_content_with_requests(self, url):
        """使用requests库抓取内容（备用方法）"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式元素
            for script in soup(["script", "style"]):
                script.decompose()
            
            title = soup.title.string if soup.title else "无标题"
            
            # 尝试获取文章内容
            article_content = soup.find('article')
            if article_content:
                content = article_content.get_text()
            else:
                # 尝试获取主要文章区域
                main_content = soup.find('main') or soup.find('div', class_=re.compile(r'article|content|main'))
                if main_content:
                    content = main_content.get_text()
                else:
                    # 获取所有段落
                    paragraphs = soup.find_all('p')
                    content = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 20])
            
            return title.strip(), content.strip()
            
        except Exception as e:
            print(f"使用requests抓取失败: {e}")
            return None, None
    
    def generate_summary_with_api(self, content, title):
        """使用大模型API生成摘要"""
        # 这里实现多种API的支持
        # 首先尝试DeepSeek API
        summary = self.try_deepseek_api(content, title)
        if summary:
            return summary
        
        # 如果DeepSeek不可用，尝试通义千问
        summary = self.try_qwen_api(content, title)
        if summary:
            return summary
        
        # 最后使用OpenAI兼容API
        summary = self.try_openai_compatible_api(content, title)
        return summary if summary else "摘要生成失败"
    
    def try_deepseek_api(self, content, title):
        """尝试使用DeepSeek API"""
        try:
            # 这里需要用户配置API密钥
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                return None
                
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            
            prompt = f"""
            请为以下文章生成100-200字的摘要：
            
            标题: {title}
            
            内容: {content[:4000]}  # 限制内容长度
            
            摘要:
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"DeepSeek API调用失败: {e}")
            return None
    
    def try_qwen_api(self, content, title):
        """尝试使用通义千问API"""
        try:
            # 这里需要用户配置API密钥
            api_key = os.getenv("QWEN_API_KEY")
            if not api_key:
                return None
                
            import dashscope
            dashscope.api_key = api_key
            
            prompt = f"""
            请为以下文章生成100-200字的摘要：
            
            标题: {title}
            
            内容: {content[:4000]}  # 限制内容长度
            
            摘要:
            """
            
            response = dashscope.Generation.call(
                model="qwen-max",
                prompt=prompt,
                max_tokens=300,
                temperature=0.5
            )
            
            if response.status_code == 200:
                return response.output.text.strip()
            else:
                print(f"通义千问API调用失败: {response.code}")
                return None
                
        except Exception as e:
            print(f"通义千问API调用失败: {e}")
            return None
    
    def try_openai_compatible_api(self, content, title):
        """尝试使用OpenAI兼容API"""
        try:
            # 使用OpenAI兼容接口（如本地部署的模型）
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            
            if not api_key:
                return None
                
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            prompt = f"""
            请为以下文章生成100-200字的摘要：
            
            标题: {title}
            
            内容: {content[:4000]}  # 限制内容长度
            
            摘要:
            """
            
            response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI兼容API调用失败: {e}")
            return None
    
    def generate_weibo_content(self, title, summary, url):
        """生成微博内容"""
        weibo_content = f"【{title[:30]}】{summary} 更多内容: {url}"
        # 确保微博内容不超过140字（实际限制可能更宽松，这里保守处理）
        if len(weibo_content) > 140:
            weibo_content = f"【{title[:20]}】{summary[:80]}... 更多内容: {url}"
        
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
        print(f"内容已保存到数据库: {title}")
    
    def manual_input(self, title, content, tags=""):
        """手工录入内容"""
        summary = self.generate_summary_with_api(content, title)
        
        cursor = self.conn.cursor()
        created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO manual_content (title, content, created_time, summary, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, content, created_time, summary, tags))
        
        self.conn.commit()
        print(f"手工录入内容已保存: {title}")
        return summary
    
    def scrape_and_process(self, url, tags=""):
        """抓取并处理网页"""
        print(f"开始抓取: {url}")
        
        title, content = self.extract_content_with_browser(url)
        
        if not content or len(content.strip()) == 0:
            print("无法抓取到有效内容")
            return False
        
        print(f"抓取成功 - 标题: {title}")
        print(f"内容长度: {len(content)} 字符")
        
        # 生成摘要
        summary = self.generate_summary_with_api(content, title)
        print(f"摘要: {summary}")
        
        # 生成微博内容
        weibo_content = self.generate_weibo_content(title, summary, url)
        print(f"微博内容: {weibo_content}")
        
        # 保存到数据库
        self.save_to_database(title, summary, url, tags)
        
        return True
    
    def close(self):
        """关闭资源"""
        if hasattr(self, 'conn'):
            self.conn.close()
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()


def main():
    extractor = WebContentExtractor()
    
    try:
        while True:
            print("\n=== 网页内容抓取与摘要生成系统 ===")
            print("1. 抓取网页内容")
            print("2. 手工录入内容")
            print("3. 查看数据库内容")
            print("4. 退出")
            
            choice = input("请选择操作 (1-4): ").strip()
            
            if choice == "1":
                url = input("请输入网页URL: ").strip()
                if url:
                    tags = input("请输入标签 (可选，多个标签用逗号分隔): ").strip()
                    extractor.scrape_and_process(url, tags)
                else:
                    print("URL不能为空")
            
            elif choice == "2":
                title = input("请输入标题: ").strip()
                content = input("请输入内容: ").strip()
                if title and content:
                    tags = input("请输入标签 (可选，多个标签用逗号分隔): ").strip()
                    summary = extractor.manual_input(title, content, tags)
                    print(f"生成的摘要: {summary}")
                else:
                    print("标题和内容不能为空")
            
            elif choice == "3":
                cursor = extractor.conn.cursor()
                cursor.execute("SELECT * FROM content_summary ORDER BY id DESC LIMIT 10")
                results = cursor.fetchall()
                
                print("\n最近10条抓取记录:")
                for row in results:
                    print(f"ID: {row[0]}, 标题: {row[1][:30]}..., 时间: {row[2]}")
                    print(f"摘要: {row[3][:100]}...")
                    print(f"URL: {row[4]}")
                    print(f"标签: {row[5] if row[5] else '无'}")
                    print("-" * 50)
            
            elif choice == "4":
                print("退出系统")
                break
            
            else:
                print("无效选择，请重新输入")
    
    except KeyboardInterrupt:
        print("\n用户中断操作")
    
    finally:
        extractor.close()


if __name__ == "__main__":
    main()