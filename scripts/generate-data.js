// scripts/generate-data.js
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { readDatabaseRows } from './lib/db.mjs';
import { validateRows } from './lib/data-rules.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const JSON_PATH = path.resolve(__dirname, '../src/assets/static-data.json');
const JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const allowShrink = process.argv.includes('--allow-shrink');

function readPreviousCount() {
  if (!fs.existsSync(JS_PATH)) return null;
  try {
    const raw = fs.readFileSync(JS_PATH, 'utf-8').trim();
    const body = raw.replace(/^export default\s*/, '').replace(/;\s*$/, '');
    const data = JSON.parse(body);
    return Array.isArray(data) ? data.length : null;
  } catch {
    return null;
  }
}

function writeAtomic(filePath, content) {
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, content, 'utf-8');
  fs.renameSync(tempPath, filePath);
}

async function main() {
  const rows = await readDatabaseRows(DB_PATH);
  const previousCount = readPreviousCount();
  const { ok, errors, warnings } = validateRows(rows, { previousCount, allowShrink });

  for (const warning of warnings) console.warn(`⚠️  ${warning}`);
  if (!ok) {
    for (const error of errors) console.error(`❌ ${error}`);
    console.error('❌ 校验失败，未写入任何文件。');
    process.exit(1);
  }

  writeAtomic(JSON_PATH, `${JSON.stringify(rows, null, 2)}\n`);
  writeAtomic(JS_PATH, `export default ${JSON.stringify(rows)};\n`);

  console.log(`✅ 生成 ${rows.length} 条（上一版 ${previousCount ?? '无'} 条）`);
  console.log(`   ${JSON_PATH}`);
  console.log(`   ${JS_PATH}`);
}

main().catch((error) => {
  console.error(`❌ 生成失败: ${error.message}`);
  process.exit(1);
});
