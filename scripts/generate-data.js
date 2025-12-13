
import fs from 'fs';
import path from 'path';
import initSqlJs from 'sql.js';
import { fileURLToPath } from 'url';
import JavaScriptObfuscator from 'javascript-obfuscator';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const OUTPUT_PATH = path.resolve(__dirname, '../src/assets/static-data.json');
const OUTPUT_JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');

const args = process.argv.slice(2);
const FROM_JSON = args.includes('--from-json');

function writeJsModule(result) {
  const jsModule = `export default ${JSON.stringify(result)};`;
  const obfuscated = JavaScriptObfuscator.obfuscate(jsModule, {
    compact: true,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.75,
    deadCodeInjection: false,
    stringArray: true,
    stringArrayThreshold: 1,
    renameGlobals: false,
  });
  fs.writeFileSync(OUTPUT_JS_PATH, obfuscated.getObfuscatedCode());
  console.log(`🔐 Obfuscated JS generated at: ${OUTPUT_JS_PATH}`);
}

async function generateFromJson() {
  console.log('📦 Generating static-data.js from existing static-data.json...');
  if (!fs.existsSync(OUTPUT_PATH)) {
    console.error(`❌ ${OUTPUT_PATH} not found. Aborting JSON→JS generation.`);
    process.exit(1);
  }
  const raw = fs.readFileSync(OUTPUT_PATH, 'utf-8');
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    console.error('❌ Failed to parse static-data.json:', e);
    process.exit(1);
  }
  writeJsModule(data);
}

async function generateData() {
  console.log('📦 Starting static data generation...');
  console.log(`📂 Database path: ${DB_PATH}`);

  if (FROM_JSON) {
    await generateFromJson();
    return;
  }

  if (!fs.existsSync(DB_PATH)) {
    console.warn('⚠️  Database file not found. Falling back to JSON→JS generation if available.');
    if (fs.existsSync(OUTPUT_PATH)) {
      await generateFromJson();
    } else {
      console.warn('ℹ️  No static-data.json found. Preserving existing static-data.js.');
    }
    return;
  }

  try {
    const filebuffer = fs.readFileSync(DB_PATH);
    const SQL = await initSqlJs();
    const db = new SQL.Database(filebuffer);

    // Try reading from content_summary first
    let result = [];
    try {
      const query = `
        SELECT 
          id,
          title,
          created_time,
          summary,
          original_url,
          tags
        FROM content_summary
        ORDER BY created_time DESC
      `;
      const res = db.exec(query);
      if (res.length > 0) {
        const columns = res[0].columns;
        result = res[0].values.map(row => {
          return columns.reduce((obj, col, i) => {
            obj[col] = row[i];
            return obj;
          }, {});
        });
        console.log(`✅ Found ${result.length} records in content_summary`);
      }
    } catch (e) {
      console.log('ℹ️  content_summary table not found or empty, trying manual_content...');
    }

    // specific fallback logic if result is empty
    if (result.length === 0) {
      try {
        const query = `
          SELECT 
            id,
            title,
            content as summary,
            created_time,
            '' as original_url,
            tags
          FROM manual_content
          ORDER BY created_time DESC
        `;
        const res = db.exec(query);
        if (res.length > 0) {
          const columns = res[0].columns;
          result = res[0].values.map(row => {
            return columns.reduce((obj, col, i) => {
              obj[col] = row[i];
              return obj;
            }, {});
          });
          console.log(`✅ Found ${result.length} records in manual_content`);
        }
      } catch (e) {
        console.log('ℹ️  manual_content table not found or empty.');
      }
    }

    db.close();

    // Ensure output directory exists
    fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
    
    // Write data
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2));
    console.log(`🎉 Static data generated at: ${OUTPUT_PATH}`);
    
    writeJsModule(result);

  } catch (error) {
    console.error('❌ Error generating data:', error);
    process.exit(1);
  }
}

generateData();
