// scripts/lib/generated-data.mjs
// 统一解析生成的 `export default [...]` 数据模块。
import fs from 'fs';

const EXPORT_DEFAULT_RE = /^\s*export default\b/;

export function parseGeneratedModule(raw) {
  if (!EXPORT_DEFAULT_RE.test(raw)) throw new Error('生成物缺少 export default');
  const body = raw.trim().replace(/^export default\s*/, '').replace(/;\s*$/, '');
  const data = JSON.parse(body);
  if (!Array.isArray(data)) throw new Error('生成物不是数组');
  return data;
}

export function readGeneratedRows(filePath) {
  return parseGeneratedModule(fs.readFileSync(filePath, 'utf-8'));
}
