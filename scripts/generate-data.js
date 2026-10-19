// scripts/generate-data.js
import path from 'path';
import { fileURLToPath } from 'url';

import { generate } from './lib/generate.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../python_scripts/web_content.db');
const JSON_PATH = path.resolve(__dirname, '../src/assets/static-data.json');
const JS_PATH = path.resolve(__dirname, '../src/assets/static-data.js');
const USAGE = '用法: node scripts/generate-data.js [--allow-shrink]';

function parseArgs(argv) {
  let allowShrink = false;
  for (const arg of argv) {
    if (arg === '--allow-shrink') {
      allowShrink = true;
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  return { allowShrink };
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`❌ ${error.message}`);
    console.error(USAGE);
    process.exitCode = 2;
    return;
  }

  try {
    const result = await generate({
      dbPath: DB_PATH,
      jsonPath: JSON_PATH,
      jsPath: JS_PATH,
      allowShrink: options.allowShrink,
    });

    for (const warning of result.warnings) console.warn(`⚠️  ${warning}`);

    if (!result.ok) {
      for (const error of result.errors) console.error(`❌ ${error}`);
      console.error('❌ 生成失败，未写入任何文件。');
      process.exitCode = 1;
      return;
    }

    console.log(`✅ 生成 ${result.count} 条（上一版 ${result.previousCount ?? '无'} 条）`);
    console.log(`   ${JSON_PATH}`);
    console.log(`   ${JS_PATH}`);
  } catch (error) {
    console.error(`❌ 生成失败: ${error.message}`);
    process.exitCode = 1;
  }
}

main();
