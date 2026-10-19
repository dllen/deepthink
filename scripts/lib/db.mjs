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
  let db;
  try {
    const SQL = await initSqlJs();
    db = new SQL.Database(fs.readFileSync(dbPath));
    const result = db.exec(
      `SELECT ${DB_COLUMNS.join(', ')} ` +
      'FROM content_summary ORDER BY created_time DESC, id DESC',
    );
    if (!result.length) return [];
    const { columns, values } = result[0];
    return values.map((row) =>
      Object.fromEntries(columns.map((column, index) => [column, row[index]])),
    );
  } catch (error) {
    throw new Error(`读取数据库失败 (${dbPath}): ${error.message}`);
  } finally {
    if (db) db.close();
  }
}
