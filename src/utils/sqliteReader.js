// SQLite Reader Utility for Browser Environment
// This implementation uses sql.js to read SQLite files in the browser
import initSqlJs from 'sql.js';

class SQLiteReader {
  constructor() {
    this.SQL = null;
  }

  // Initialize SQL.js
  async init() {
    if (!this.SQL) {
      this.SQL = await initSqlJs({
        locateFile: file => `https://sql.js.org/dist/${file}`
      });
    }
  }

  // Read data from SQLite file
  async readData(file) {
    if (!file) {
      // Return sample data if no file provided (for demo purposes)
      return [
        {
          id: 1,
          title: "AI技术在内容生成中的应用",
          created_time: "2023-10-15 14:30:00",
          summary: "人工智能技术正在改变内容生成的方式，自动化摘要和内容生成成为新的趋势。深度学习模型可以分析大量数据，提取关键信息并生成高质量的内容。",
          original_url: "https://example.com/article1",
          tags: "AI,技术,趋势"
        },
        {
          id: 2,
          title: "现代前端开发最佳实践",
          created_time: "2023-10-16 09:15:00",
          summary: "现代前端开发涉及多种技术和框架，React、Vue和Angular是主流选择。组件化开发、状态管理和性能优化是关键要素。",
          original_url: "https://example.com/article2",
          tags: "前端,React,开发"
        },
        {
          id: 3,
          title: "数据库设计与优化策略",
          created_time: "2023-10-17 16:45:00",
          summary: "良好的数据库设计是应用性能的基础。索引优化、查询优化和数据分区是提升数据库性能的关键策略。",
          original_url: "https://example.com/article3",
          tags: "数据库,优化,设计"
        },
        {
          id: 4,
          title: "移动应用开发趋势分析",
          created_time: "2023-10-18 11:20:00",
          summary: "移动应用开发正朝着跨平台方向发展，Flutter和React Native成为热门选择。用户体验和性能优化仍是核心关注点。",
          original_url: "https://example.com/article4",
          tags: "移动开发,Flutter,趋势"
        },
        {
          id: 5,
          title: "云计算架构设计模式",
          created_time: "2023-10-19 13:10:00",
          summary: "云计算架构需要考虑可扩展性、可靠性和安全性。微服务架构、容器化和无服务器架构是当前主流的解决方案。",
          original_url: "https://example.com/article5",
          tags: "云计算,架构,微服务"
        },
        {
          id: 6,
          title: "网络安全防护策略",
          created_time: "2023-10-20 10:30:00",
          summary: "网络安全威胁日益增多，企业需要建立多层次的防护体系。零信任架构、加密技术和安全监控是关键措施。",
          original_url: "https://example.com/article6",
          tags: "安全,网络,防护"
        },
        {
          id: 7,
          title: "数据分析与可视化技术",
          created_time: "2023-10-21 15:45:00",
          summary: "数据可视化帮助我们更好地理解复杂数据。D3.js、Tableau和Power BI是常用的数据可视化工具，各有其优势和适用场景。",
          original_url: "https://example.com/article7",
          tags: "数据分析,可视化,工具"
        },
        {
          id: 8,
          title: "DevOps实践与持续集成",
          created_time: "2023-10-22 08:20:00",
          summary: "DevOps文化强调开发与运维的协作，通过自动化工具链实现快速交付。CI/CD流水线是现代软件开发的重要组成部分。",
          original_url: "https://example.com/article8",
          tags: "DevOps,CI/CD,自动化"
        }
      ];
    }

    try {
      // Initialize SQL.js if not already done
      await this.init();
      
      // Read file as array buffer
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      // Load database
      const db = new this.SQL.Database(uint8Array);
      
      // Query data from the content_summary table
      // Adjust this query based on your actual table structure
      const result = db.exec(`
        SELECT 
          id,
          title,
          created_time,
          summary,
          original_url,
          tags
        FROM content_summary
        ORDER BY created_time DESC
      `);
      
      // Process the result
      if (result.length > 0) {
        const table = result[0];
        const columns = table.columns;
        const values = table.values;
        
        const data = values.map(row => {
          const item = {};
          columns.forEach((col, index) => {
            item[col] = row[index];
          });
          return item;
        });
        
        // Close database
        db.close();
        
        return data;
      } else {
        // If content_summary table doesn't exist, try manual_content
        const result2 = db.exec(`
          SELECT 
            id,
            title,
            content as summary,
            created_time,
            '' as original_url,
            tags
          FROM manual_content
          ORDER BY created_time DESC
        `);
        
        if (result2.length > 0) {
          const table = result2[0];
          const columns = table.columns;
          const values = table.values;
          
          const data = values.map(row => {
            const item = {};
            columns.forEach((col, index) => {
              item[col] = row[index];
            });
            return item;
          });
          
          // Close database
          db.close();
          
          return data;
        } else {
          // If no tables match, return empty array
          db.close();
          return [];
        }
      }
    } catch (error) {
      console.error('Error reading SQLite file:', error);
      // Return sample data if there's an error
      return [
        {
          id: 1,
          title: "AI技术在内容生成中的应用",
          created_time: "2023-10-15 14:30:00",
          summary: "人工智能技术正在改变内容生成的方式，自动化摘要和内容生成成为新的趋势。深度学习模型可以分析大量数据，提取关键信息并生成高质量的内容。",
          original_url: "https://example.com/article1",
          tags: "AI,技术,趋势"
        },
        {
          id: 2,
          title: "现代前端开发最佳实践",
          created_time: "2023-10-16 09:15:00",
          summary: "现代前端开发涉及多种技术和框架，React、Vue和Angular是主流选择。组件化开发、状态管理和性能优化是关键要素。",
          original_url: "https://example.com/article2",
          tags: "前端,React,开发"
        },
        {
          id: 3,
          title: "数据库设计与优化策略",
          created_time: "2023-10-17 16:45:00",
          summary: "良好的数据库设计是应用性能的基础。索引优化、查询优化和数据分区是提升数据库性能的关键策略。",
          original_url: "https://example.com/article3",
          tags: "数据库,优化,设计"
        },
        {
          id: 4,
          title: "移动应用开发趋势分析",
          created_time: "2023-10-18 11:20:00",
          summary: "移动应用开发正朝着跨平台方向发展，Flutter和React Native成为热门选择。用户体验和性能优化仍是核心关注点。",
          original_url: "https://example.com/article4",
          tags: "移动开发,Flutter,趋势"
        },
        {
          id: 5,
          title: "云计算架构设计模式",
          created_time: "2023-10-19 13:10:00",
          summary: "云计算架构需要考虑可扩展性、可靠性和安全性。微服务架构、容器化和无服务器架构是当前主流的解决方案。",
          original_url: "https://example.com/article5",
          tags: "云计算,架构,微服务"
        },
        {
          id: 6,
          title: "网络安全防护策略",
          created_time: "2023-10-20 10:30:00",
          summary: "网络安全威胁日益增多，企业需要建立多层次的防护体系。零信任架构、加密技术和安全监控是关键措施。",
          original_url: "https://example.com/article6",
          tags: "安全,网络,防护"
        },
        {
          id: 7,
          title: "数据分析与可视化技术",
          created_time: "2023-10-21 15:45:00",
          summary: "数据可视化帮助我们更好地理解复杂数据。D3.js、Tableau和Power BI是常用的数据可视化工具，各有其优势和适用场景。",
          original_url: "https://example.com/article7",
          tags: "数据分析,可视化,工具"
        },
        {
          id: 8,
          title: "DevOps实践与持续集成",
          created_time: "2023-10-22 08:20:00",
          summary: "DevOps文化强调开发与运维的协作，通过自动化工具链实现快速交付。CI/CD流水线是现代软件开发的重要组成部分。",
          original_url: "https://example.com/article8",
          tags: "DevOps,CI/CD,自动化"
        }
      ];
    }
  }

  // Extract unique tags from data
  extractTags(data) {
    const allTags = new Set();
    data.forEach(item => {
      if (item.tags) {
        // Split tags by comma and trim whitespace
        item.tags.split(',').forEach(tag => {
          const trimmedTag = tag.trim();
          if (trimmedTag) {
            allTags.add(trimmedTag);
          }
        });
      }
    });
    return Array.from(allTags);
  }
}

export default SQLiteReader;