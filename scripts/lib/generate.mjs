// scripts/lib/generate.mjs
// 从 DB 单向生成 static-data.json / static-data.js，可被测试直接调用。
import fs from 'fs';

import { readDatabaseRows } from './db.mjs';
import { validateRows, SHRINK_TOLERANCE } from './data-rules.mjs';
import { readGeneratedRows } from './generated-data.mjs';

function removeQuietly(filePath) {
  try {
    fs.rmSync(filePath, { force: true });
  } catch {
    // 清理失败不应掩盖原始错误；下方错误信息会提示重跑。
  }
}

/**
 * 先写两个 .tmp，再依次 rename。任一步失败时清理 tmp，并回滚已 rename 的 json。
 * 跨文件无法做到绝对原子，但保证失败后不会只更新一半且无 tmp 残留。
 */
export function writePairAtomic({ jsonPath, jsPath, jsonContent, jsContent }) {
  const jsonTmp = `${jsonPath}.tmp`;
  const jsTmp = `${jsPath}.tmp`;
  const hadJson = fs.existsSync(jsonPath);
  const previousJson = hadJson ? fs.readFileSync(jsonPath, 'utf-8') : null;
  let jsonRenamed = false;

  try {
    fs.writeFileSync(jsonTmp, jsonContent, 'utf-8');
    fs.writeFileSync(jsTmp, jsContent, 'utf-8');
    fs.renameSync(jsonTmp, jsonPath);
    jsonRenamed = true;
    fs.renameSync(jsTmp, jsPath);
  } catch (error) {
    removeQuietly(jsonTmp);
    removeQuietly(jsTmp);
    let rollbackNote = '';
    if (jsonRenamed) {
      try {
        if (hadJson) fs.writeFileSync(jsonPath, previousJson, 'utf-8');
        else removeQuietly(jsonPath);
      } catch (rollbackError) {
        rollbackNote = `；回滚 ${jsonPath} 也失败: ${rollbackError.message}`;
      }
    }
    const summary = jsonRenamed
      ? '写入失败，已回滚，请重跑'
      : '写入失败，未写入任何文件，请重跑';
    throw new Error(`${summary}${rollbackNote}: ${error.message}`);
  }
}

/**
 * @returns {Promise<{ok: boolean, count: number, previousCount: number|null,
 *   errors: string[], warnings: string[]}>}
 * 失败（DB 读取/校验）时 ok:false 且不写任何文件；
 * 上一版无法解析且未 allowShrink 时抛错；写入失败时抛错（已尽量回滚）。
 */
export async function generate({
  dbPath, jsonPath, jsPath, allowShrink = false,
}) {
  const errors = [];
  const warnings = [];

  let rows;
  try {
    rows = await readDatabaseRows(dbPath);
  } catch (error) {
    errors.push(error.message);
    return { ok: false, count: 0, previousCount: null, errors, warnings };
  }

  let previous = null;
  if (fs.existsSync(jsPath) && fs.statSync(jsPath).isFile()) {
    try {
      previous = readGeneratedRows(jsPath);
    } catch (error) {
      if (!allowShrink) {
        throw new Error(
          `无法解析上一版 ${jsPath}（${error.message}）；确认覆盖请加 --allow-shrink`,
        );
      }
      warnings.push(`无法解析上一版 ${jsPath}（${error.message}），已按 --allow-shrink 忽略并继续`);
      previous = null;
    }
  }
  const previousCount = previous ? previous.length : null;

  const validation = validateRows(rows, { previousCount, allowShrink });
  warnings.push(...validation.warnings);

  if (allowShrink && previousCount != null && previousCount > 0) {
    const minRows = Math.ceil(previousCount * (1 - SHRINK_TOLERANCE));
    if (rows.length < minRows) {
      warnings.push(`行数从 ${previousCount} 降到 ${rows.length}，已按 --allow-shrink 放行`);
    }
  }

  if (!validation.ok) {
    return {
      ok: false, count: rows.length, previousCount, errors: validation.errors, warnings,
    };
  }

  const jsonContent = `${JSON.stringify(rows, null, 2)}\n`;
  const jsContent = `export default ${JSON.stringify(rows)};\n`;
  writePairAtomic({ jsonPath, jsPath, jsonContent, jsContent });

  return { ok: true, count: rows.length, previousCount, errors: [], warnings };
}
