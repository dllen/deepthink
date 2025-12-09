"""
简化测试脚本 - 验证模块化结构（不需要浏览器）
"""

import sys
import os

# 将当前目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有模块可以正确导入"""
    print("🧪 测试模块导入...")
    
    try:
        from web_content_system import WebContentExtractor
        print("✅ WebContentExtractor 导入成功")
        
        from web_content_system.config import Config, APIConfig, DatabaseConfig, BrowserConfig
        print("✅ Config 模块导入成功")
        
        from web_content_system.database import DatabaseManager
        print("✅ DatabaseManager 导入成功")
        
        from web_content_system.scrapers import BaseScraper, BrowserScraper, RequestsScraper
        print("✅ Scrapers 模块导入成功")
        
        from web_content_system.llm_clients import (
            BaseLLMClient, OpenAIClient, LocalModelClient, FallbackSummarizer
        )
        print("✅ LLM Clients 模块导入成功")
        
        from web_content_system.processors import ContentProcessor
        print("✅ ContentProcessor 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """测试数据库功能"""
    print("\n🧪 测试数据库功能...")
    
    try:
        from web_content_system.database import DatabaseManager
        
        # 使用临时数据库
        db = DatabaseManager("test_temp.db")
        print("✅ 数据库初始化成功")
        
        # 测试保存内容摘要
        record_id = db.save_content_summary(
            title="测试标题",
            summary="这是一个测试摘要",
            url="https://example.com",
            tags="测试,模块化"
        )
        print(f"✅ 保存内容摘要成功 (ID: {record_id})")
        
        # 测试查询
        results = db.get_recent_summaries(5)
        print(f"✅ 查询记录成功 (找到 {len(results)} 条记录)")
        
        # 测试手工内容
        manual_id = db.save_manual_content(
            title="手工测试",
            content="这是手工输入的内容",
            summary="手工内容摘要",
            tags="手工,测试"
        )
        print(f"✅ 保存手工内容成功 (ID: {manual_id})")
        
        db.close()
        
        # 清理测试数据库
        import os
        if os.path.exists("test_temp.db"):
            os.remove("test_temp.db")
        
        return True
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试配置管理"""
    print("\n🧪 测试配置管理...")
    
    try:
        from web_content_system.config import Config, APIConfig
        
        # 测试默认配置
        config = Config.default()
        print("✅ 默认配置创建成功")
        
        # 测试从环境变量加载
        config_env = Config.from_env()
        print("✅ 从环境变量加载配置成功")
        
        # 测试配置值
        assert config.database.db_path == "web_content.db"
        assert config.browser.headless == True
        print("✅ 配置值验证成功")
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_summarizer():
    """测试回退摘要生成器"""
    print("\n🧪 测试回退摘要生成器...")
    
    try:
        from web_content_system.llm_clients import FallbackSummarizer
        
        summarizer = FallbackSummarizer()
        
        test_content = """
        人工智能是计算机科学的一个分支，它企图了解智能的实质，
        并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
        人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。
        """
        
        summary = summarizer.generate_summary(test_content, "人工智能简介")
        print(f"✅ 摘要生成成功: {summary[:50]}...")
        
        assert summary is not None
        assert len(summary) > 0
        print("✅ 摘要验证成功")
        
        return True
    except Exception as e:
        print(f"❌ 摘要生成器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_content_processor():
    """测试内容处理器"""
    print("\n🧪 测试内容处理器...")
    
    try:
        from web_content_system.processors import ContentProcessor
        
        processor = ContentProcessor()
        print("✅ ContentProcessor 初始化成功")
        
        # 测试摘要生成（会使用fallback）
        summary = processor.generate_summary(
            "这是一段测试内容，用于验证摘要生成功能是否正常工作。",
            "测试标题"
        )
        print(f"✅ 摘要生成成功: {summary[:50]}...")
        
        # 测试微博内容生成
        weibo = processor.generate_weibo_content(
            "测试文章标题",
            "这是测试摘要内容",
            "https://example.com"
        )
        print(f"✅ 微博内容生成成功: {weibo}")
        
        # 测试内容验证
        long_content = "这是一段足够长的测试内容，用于验证内容验证功能是否正常工作。这段文字肯定超过了五十个字符的最小长度要求。"
        short_content = "太短"
        assert processor.validate_content(long_content) == True
        assert processor.validate_content(short_content) == False
        print("✅ 内容验证功能正常")
        
        return True
    except Exception as e:
        print(f"❌ 内容处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("🚀 模块化系统测试")
    print("=" * 60)
    
    tests = [
        ("模块导入", test_imports),
        ("配置管理", test_config),
        ("数据库功能", test_database),
        ("回退摘要生成器", test_fallback_summarizer),
        ("内容处理器", test_content_processor),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试出现异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！模块化系统工作正常")
        print("\n📋 系统功能清单:")
        print("✅ 模块化架构 - 配置、数据库、爬虫、LLM客户端、处理器分离")
        print("✅ 配置管理 - 支持环境变量和默认配置")
        print("✅ 数据库操作 - SQLite存储和查询")
        print("✅ 摘要生成 - 支持多种LLM API和回退机制")
        print("✅ 内容处理 - 摘要和微博内容生成")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
