// scripts/check-data.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import { readDatabaseRows } from './lib/db.mjs';
import { compareDatasets, validateRows } from './lib/data-rules.mjs';
import { readGeneratedRows } from './lib/generated-data.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const JSON_PATH = path.resolve(__dirname, '../src/assets/static-data.json');

async function main() {
  const dbRows = await readDatabaseRows(DB_PATH);
  const published = readGeneratedRows(JS_PATH);
  const publishedJson = JSON.parse(fs.readFileSync(JSON_PATH, 'utf-8'));

  const dbCheck = validateRows(dbRows);
  const pubCheck = validateRows(published);
  const errors = [...dbCheck.errors, ...pubCheck.errors];
  for (const warning of [...dbCheck.warnings, ...pubCheck.warnings]) {
    console.warn(`⚠️  ${warning}`);
  }
  if (dbCheck.ok && pubCheck.ok) {
    errors.push(...compareDatasets(dbRows, published).errors);
  }

  const jsonVsJs = JSON.stringify(publishedJson) === JSON.stringify(published);
  if (!jsonVsJs) errors.push('static-data.json 与 static-data.js 内容不一致');

  if (errors.length > 0) {
    for (const error of errors) console.error(`❌ ${error}`);
    console.error(`❌ check:data 失败（${errors.length} 项）`);
    process.exit(1);
  }
  console.log(`✅ check:data 通过：DB 与生成物一致，共 ${dbRows.length} 条`);
}

main().catch((error) => {
  console.error(`❌ check:data 异常: ${error.message}`);
  process.exit(1);
});
