// scripts/lib/db.mjs
import fs from 'fs';
import initSqlJs from 'sql.js';

export const DB_COLUMNS = [
  'id', 'title', 'created_time', 'summary', 'original_url', 'tags', 'category',
];

export async function readDatabaseRows(dbPath) {
  if (!fs.existsSync(dbPath)) {
    throw new Error(`数据库不存在: ${dbPath}`);
  }
  const SQL = await initSqlJs();
  const db = new SQL.Database(fs.readFileSync(dbPath));
  try {
    const result = db.exec(
      'SELECT id, title, created_time, summary, original_url, tags, category ' +
      'FROM content_summary ORDER BY created_time DESC, id DESC',
    );
    if (!result.length) return [];
    const { columns, values } = result[0];
    return values.map((row) =>
      Object.fromEntries(columns.map((column, index) => [column, row[index]])),
    );
  } finally {
    db.close();
  }
}
