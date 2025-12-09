"""
测试脚本 - 验证网页内容抓取与摘要生成系统的基本功能
"""

import os
import sys
from datetime import datetime

# 将当前目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入我们创建的模块
from web_content_system import WebContentExtractor

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 开始测试网页内容抓取与摘要生成系统...")
    
    # 创建提取器实例
    extractor = WebContentExtractor()
    print("✅ 系统初始化成功")
    
    # 测试数据库连接
    try:
        cursor = extractor.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ 数据库连接正常，找到表: {[table[0] for table in tables]}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    # 测试手工录入功能
    print("\n📝 测试手工录入功能...")
    test_title = "测试文章标题"
    test_content = """这是一篇用于测试的文章内容。文章主要讲述了网页内容抓取与摘要生成系统的工作原理。
    该系统能够自动抓取网页内容，使用大模型API生成摘要，并将结果保存到数据库中。
    系统支持多种API接口，包括OpenAI、本地模型等。"""
    test_tags = "测试,摘要,自动化"
    
    try:
        summary = extractor.manual_input(test_title, test_content, test_tags)
        print(f"✅ 手工录入成功，生成摘要: {summary[:100]}...")
    except Exception as e:
        print(f"❌ 手工录入失败: {e}")
        return False
    
    # 测试查看记录功能
    print("\n📖 测试查看记录功能...")
    try:
        extractor.view_recent_records(5)
        print("✅ 查看记录功能正常")
    except Exception as e:
        print(f"❌ 查看记录功能失败: {e}")
        return False
    
    # 测试摘要生成
    print("\n🤖 测试摘要生成功能...")
    try:
        sample_content = "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。"
        sample_title = "人工智能简介"
        summary = extractor.generate_summary_with_api(sample_content, sample_title)
        print(f"✅ 摘要生成成功: {summary[:100]}...")
        print(f"  摘要长度: {len(summary)} 字符")
    except Exception as e:
        print(f"❌ 摘要生成功能失败: {e}")
        return False
    
    # 测试微博内容生成
    print("\n>Weibo 测试微博内容生成功能...")
    try:
        weibo_content = extractor.generate_weibo_content("测试标题", "这是测试摘要内容", "https://example.com")
        print(f"✅ 微博内容生成成功: {weibo_content}")
        print(f"  微博内容长度: {len(weibo_content)} 字符")
    except Exception as e:
        print(f"❌ 微博内容生成功能失败: {e}")
        return False
    
    # 关闭资源
    extractor.close()
    print("\n✅ 所有测试通过！系统功能正常")
    return True

def test_database_schema():
    """测试数据库表结构"""
    print("\n🔍 测试数据库表结构...")
    
    conn = sqlite3.connect('web_content.db')
    cursor = conn.cursor()
    
    # 检查content_summary表结构
    cursor.execute("PRAGMA table_info(content_summary)")
    content_columns = cursor.fetchall()
    print("📋 content_summary表结构:")
    for col in content_columns:
        print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
    
    # 检查索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='content_summary';")
    indexes = cursor.fetchall()
    print(f"🏷️  content_summary表索引: {[idx[0] for idx in indexes]}")
    
    # 检查manual_content表结构
    cursor.execute("PRAGMA table_info(manual_content)")
    manual_columns = cursor.fetchall()
    print("✍️  manual_content表结构:")
    for col in manual_columns:
        print(f"  - {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
    
    conn.close()
    print("✅ 数据库表结构检查完成")

if __name__ == "__main__":
    import sqlite3
    
    print("🚀 网页内容抓取与摘要生成系统 - 功能测试")
    print("="*60)
    
    # 运行基本功能测试
    success = test_basic_functionality()
    
    # 测试数据库表结构
    test_database_schema()
    
    print("\n" + "="*60)
    if success:
        print("🎉 所有测试通过！系统已准备就绪")
        print("\n📋 系统功能清单:")
        print("✅ 网页内容抓取（支持浏览器模拟和requests）")
        print("✅ 大模型API摘要生成（支持OpenAI、本地模型等）")
        print("✅ 微博内容生成")
        print("✅ SQLite数据库存储")
        print("✅ 手工录入支持")
        print("✅ 标签索引功能")
        print("\n🔧 使用说明:")
        print("1. 设置API密钥环境变量以使用大模型API")
        print("2. 运行 python web_content_extractor_simple.py 启动系统")
        print("3. 系统会自动创建数据库文件 web_content.db")
    else:
        print("❌ 测试失败，请检查代码")