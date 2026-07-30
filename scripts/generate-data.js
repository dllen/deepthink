
import fs from 'fs';
import path from 'path';
import initSqlJs from 'sql.js';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const OUTPUT_PATH = path.resolve(__dirname, '../src/assets/static-data.json');
const OUTPUT_JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const OUTPUT_DIR = path.dirname(OUTPUT_PATH);

const args = process.argv.slice(2);
const FROM_JSON = args.includes('--from-json');

function writeJsModule(result) {
  const jsModule = `export default ${JSON.stringify(result)};`;
  fs.writeFileSync(OUTPUT_JS_PATH, jsModule);
  console.log(`📦 static-data.js generated at: ${OUTPUT_JS_PATH}`);
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

function formatTs(d) {
  const pad = n => String(n).padStart(2, '0');
  const yyyy = d.getFullYear();
  const mm = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const hh = pad(d.getHours());
  const mi = pad(d.getMinutes());
  const ss = pad(d.getSeconds());
  return `${yyyy}${mm}${dd}-${hh}${mi}${ss}`;
}

function mergeIncremental(existing, incoming) {
  const keyOf = item => item.original_url || `${item.title}-${item.created_time}`;
  const map = new Map(existing.map(x => [keyOf(x), x]));
  let added = 0;
  for (const it of incoming) {
    const k = keyOf(it);
    if (!map.has(k)) {
      existing.push(it);
      map.set(k, it);
      added++;
    }
  }
  existing.sort((a, b) => String(b.created_time).localeCompare(String(a.created_time)));
  return { merged: existing, added };
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

    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    const existing = fs.existsSync(OUTPUT_PATH) ? JSON.parse(fs.readFileSync(OUTPUT_PATH, 'utf-8')) : [];
    const { merged, added } = mergeIncremental(existing, result);
    const ts = formatTs(new Date());
    const snapshotPath = path.resolve(OUTPUT_DIR, `static-data-${ts}.json`);
    fs.writeFileSync(snapshotPath, JSON.stringify(merged, null, 2));
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(merged, null, 2));
    console.log(`➕ Incremental merge complete. Added ${added} new records.`);
    console.log(`🗂 Snapshot written: ${snapshotPath}`);
    console.log(`🎉 Latest data written: ${OUTPUT_PATH}`);
    writeJsModule(merged);

  } catch (error) {
    console.error('❌ Error generating data:', error);
    process.exit(1);
  }
}

generateData();
