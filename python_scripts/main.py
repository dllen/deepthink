#!/usr/bin/env python3
"""
Main CLI entry point for web content extraction system.
"""

import sys
from web_content_system import WebContentExtractor


def print_menu():
    """Print main menu."""
    print("\n" + "=" * 50)
    print("📋 请选择操作:")
    print("1. 🕸️  抓取网页内容")
    print("2. ✍️  手工录入内容")
    print("3. 📖 查看数据库内容")
    print("4. ❓ 帮助信息")
    print("5. 🚪 退出系统")
    print("6. 🚀 批量抓取 (grab_params.json)")

def process_batch_scraping(extractor):
    """Process batch scraping from grab_params.json."""
    import json
    import os
    
    file_path = "grab_params.json"
    
    if not os.path.exists(file_path):
        print(f"❌ 未找到配置文件: {file_path}")
        print("请在当前目录下创建 grab_params.json，格式如下:")
        print('[{"url": "...", "tags": "...", "done": false}]')
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        
        if not isinstance(items, list):
            print("❌ JSON格式错误: 根节点必须是列表")
            return
            
        count = 0
        total = len(items)
        print(f"\n📦 开始批量处理，共 {total} 个任务")
        
        for i, item in enumerate(items):
            if item.get('done', False):
                continue
                
            url = item.get('url')
            if not url:
                print(f"⚠️  跳过无效任务 (缺少URL): 任务 #{i+1}")
                continue
                
            print(f"\n🔄 处理任务 {i+1}/{total}...")
            tags = item.get('tags', '')
            
            try:
                success = extractor.scrape_and_process(url, tags)
                if success:
                    item['done'] = True
                    count += 1
                    
                    # Immediate save to prevent data loss
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(items, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"❌ 处理失败: {e}")
                
        print(f"\n✅ 批量处理完成! 成功处理 {count} 个新任务")
            
    except json.JSONDecodeError:
        print("❌ JSON文件解析失败，请检查语法")
    except Exception as e:
        print(f"❌ 批量处理出错: {e}")


def print_help():
    """Print help information."""
    print("\n📖 使用帮助:")
    print("• 抓取网页内容: 输入网页URL，系统将自动抓取内容、生成摘要并保存")
    print("• 手工录入内容: 手动输入标题和内容，系统生成摘要并保存")
    print("• 查看数据库内容: 显示最近抓取的记录")
    print("\n🔧 API配置:")
    print("• 设置环境变量 OPENAI_API_KEY 来使用OpenAI API")
    print("• 设置环境变量 OLLAMA_API_URL 来使用本地模型")
    print("• 如果未配置API，系统将使用简单摘要算法")


def main():
    """Main CLI loop."""
    print("🚀 网页内容抓取与摘要生成系统 v2.0")
    print("初始化中...")
    
    try:
        extractor = WebContentExtractor()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("请确保已安装所需依赖包: pip install -r requirements.txt")
        return 1
    
    print("✅ 系统初始化完成")
    
    try:
        while True:
            print_menu()
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
                print_help()
            
            elif choice == "5":
                print("\n👋 感谢使用，再见！")
                break
            
            elif choice == "6":
                process_batch_scraping(extractor)
            
            else:
                print("\n❌ 无效选择，请重新输入")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
    
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        return 1
    
    finally:
        extractor.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
