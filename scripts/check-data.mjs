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

function readJson(filePath) {
  let raw;
  try {
    raw = fs.readFileSync(filePath, 'utf-8');
  } catch (error) {
    throw new Error(`读取/解析 ${filePath} 失败: ${error.message}`);
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`读取/解析 ${filePath} 失败: ${error.message}`);
  }
}

function readJsRows(filePath) {
  try {
    return readGeneratedRows(filePath);
  } catch (error) {
    throw new Error(`读取/解析 ${filePath} 失败: ${error.message}`);
  }
}

function jsonVsJsErrors(publishedJson, published) {
  if (!Array.isArray(publishedJson)) {
    return ['[生成物] static-data.json 不是数组'];
  }
  if (publishedJson.length !== published.length) {
    return [
      `[差异] static-data.json ${publishedJson.length} 条 vs static-data.js `
      + `${published.length} 条；请重跑 npm run gen:static-js`,
    ];
  }
  const index = publishedJson.findIndex(
    (row, i) => JSON.stringify(row) !== JSON.stringify(published[i]),
  );
  if (index === -1) return [];
  const id = publishedJson[index]?.id ?? published[index]?.id;
  const where = id === undefined ? `索引 ${index}` : `索引 ${index}（id=${id}）`;
  return [`[差异] static-data.json 与 static-data.js 在${where}不一致；请重跑 npm run gen:static-js`];
}

async function main() {
  const dbRows = await readDatabaseRows(DB_PATH);
  const published = readJsRows(JS_PATH);
  const publishedJson = readJson(JSON_PATH);

  const dbCheck = validateRows(dbRows);
  const pubCheck = validateRows(published);
  const errors = [
    ...dbCheck.errors.map((e) => `[DB] ${e}`),
    ...pubCheck.errors.map((e) => `[生成物] ${e}`),
  ];
  for (const warning of new Set([...dbCheck.warnings, ...pubCheck.warnings])) {
    console.warn(`⚠️  ${warning}`);
  }
  if (dbCheck.ok && pubCheck.ok) {
    errors.push(...compareDatasets(dbRows, published).errors.map((e) => `[差异] ${e}`));
  }

  errors.push(...jsonVsJsErrors(publishedJson, published));

  if (errors.length > 0) {
    for (const error of errors) console.error(`❌ ${error}`);
    console.error(`❌ check:data 失败（${errors.length} 项）`);
    process.exitCode = 1;
    return;
  }
  console.log(`✅ check:data 通过：DB 与生成物一致，共 ${dbRows.length} 条`);
}

main().catch((error) => {
  console.error(`❌ check:data 异常: ${error.message}`);
  process.exitCode = 1;
});
