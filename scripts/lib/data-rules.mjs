// scripts/lib/data-rules.mjs
export const CATEGORIES = ['科技动态', '文章', '工具', '资源', '图片', '文摘', '言论'];
export const TIMESTAMP_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
export const SHRINK_TOLERANCE = 0.1;
export const COMPARED_FIELDS = [
  'title', 'category', 'created_time', 'summary', 'original_url', 'tags',
];

export function validateRows(rows, { previousCount = null, allowShrink = false } = {}) {
  const errors = [];
  const warnings = [];
  if (!Array.isArray(rows) || rows.length === 0) {
    return { ok: false, errors: ['数据不是数组或为空'], warnings };
  }

  const ids = new Set();
  const seenUrl = new Map();
  for (const [i, row] of rows.entries()) {
    const where = row && row.id !== undefined ? `id=${row.id}` : `第 ${i} 行`;
    if (!row || typeof row !== 'object' || Array.isArray(row)) {
      errors.push(`${where}: 不是对象`);
      continue;
    }
    if (Number.isInteger(row.id)) {
      if (ids.has(row.id)) errors.push(`${where}: id 重复`);
      ids.add(row.id);
    } else {
      errors.push(`${where}: id 不是整数`);
    }
    if (!String(row.title ?? '').trim()) errors.push(`${where}: title 为空`);
    if (!CATEGORIES.includes(row.category)) {
      errors.push(`${where}: category 非法 (${JSON.stringify(row.category)})`);
    }
    if (!String(row.tags ?? '').trim()) errors.push(`${where}: tags 为空`);
    if (!TIMESTAMP_RE.test(String(row.created_time ?? ''))) {
      errors.push(`${where}: created_time 格式应为 YYYY-MM-DD HH:MM:SS (${JSON.stringify(row.created_time)})`);
    }
    if (row.original_url != null && typeof row.original_url !== 'string') {
      errors.push(`${where}: original_url 类型错误`);
    }
    const url = row.original_url || '';
    if (url) {
      if (seenUrl.has(url)) {
        warnings.push(`original_url 重复: ${url}（id ${seenUrl.get(url)} 与 ${row.id}）`);
      } else {
        seenUrl.set(url, row.id);
      }
    }
  }

  if (previousCount != null && previousCount > 0) {
    const minRows = Math.ceil(previousCount * (1 - SHRINK_TOLERANCE));
    if (rows.length < minRows && !allowShrink) {
      errors.push(
        `行数从 ${previousCount} 降到 ${rows.length}，超过 ${SHRINK_TOLERANCE * 100}% 缩水阈值（用 --allow-shrink 放行）`,
      );
    }
  }

  return { ok: errors.length === 0, errors, warnings };
}

export function compareDatasets(dbRows, publishedRows) {
  if (!Array.isArray(dbRows) || !Array.isArray(publishedRows)) {
    return { ok: false, errors: ['compareDatasets 输入必须是数组'] };
  }
  const errors = [];
  const dbById = new Map(dbRows.map((r) => [r.id, r]));
  const pubById = new Map(publishedRows.map((r) => [r.id, r]));

  if (dbRows.length !== publishedRows.length) {
    errors.push(`条数不一致: DB ${dbRows.length} vs 生成物 ${publishedRows.length}`);
  }
  for (const id of dbById.keys()) {
    if (!pubById.has(id)) errors.push(`生成物缺少 DB 行 id=${id}`);
  }
  for (const id of pubById.keys()) {
    if (!dbById.has(id)) errors.push(`生成物多出 DB 不存在的行 id=${id}`);
  }
  for (const [id, dbRow] of dbById) {
    const pub = pubById.get(id);
    if (!pub) continue;
    for (const field of COMPARED_FIELDS) {
      if ((pub[field] ?? null) !== (dbRow[field] ?? null)) {
        errors.push(`id=${id} 字段 ${field} 不一致`);
      }
    }
  }
  return { ok: errors.length === 0, errors };
}
