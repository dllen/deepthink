// scripts/lib/generate.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import initSqlJs from 'sql.js';

import { generate } from './generate.mjs';
import { readGeneratedRows } from './generated-data.mjs';

let sqlPromise = null;
function getSql() {
  if (!sqlPromise) sqlPromise = initSqlJs();
  return sqlPromise;
}

function makeRow(overrides = {}) {
  return {
    id: 1,
    title: '标题',
    created_time: '2026-01-01 00:00:00',
    summary: '摘要',
    original_url: 'https://example.com/1',
    tags: 'AI',
    category: '文章',
    ...overrides,
  };
}

async function createDb(dbPath, rows) {
  const SQL = await getSql();
  const db = new SQL.Database();
  db.run(
    'CREATE TABLE content_summary ('
    + 'id INTEGER PRIMARY KEY, title TEXT, created_time TEXT, summary TEXT, '
    + 'original_url TEXT, tags TEXT, category TEXT)',
  );
  const insert = db.prepare(
    'INSERT INTO content_summary '
    + '(id, title, created_time, summary, original_url, tags, category) '
    + 'VALUES (?, ?, ?, ?, ?, ?, ?)',
  );
  try {
    for (const row of rows) {
      insert.run([
        row.id, row.title, row.created_time, row.summary,
        row.original_url, row.tags, row.category,
      ]);
    }
  } finally {
    insert.free();
  }
  fs.writeFileSync(dbPath, db.export());
  db.close();
}

function tempPaths(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'deepthink-generate-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return {
    dir,
    dbPath: path.join(dir, 'web_content.db'),
    jsonPath: path.join(dir, 'static-data.json'),
    jsPath: path.join(dir, 'static-data.js'),
  };
}

function assertNoTemps(...filePaths) {
  for (const filePath of filePaths) {
    assert.equal(fs.existsSync(`${filePath}.tmp`), false, `残留 ${filePath}.tmp`);
  }
}

function sha256(filePath) {
  return createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

test('正常生成：内容一致、按时间与 id 倒序、重复生成字节稳定', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [
    makeRow({ id: 1, created_time: '2026-01-01 00:00:00', original_url: 'https://example.com/1' }),
    makeRow({ id: 3, created_time: '2026-01-02 00:00:00', original_url: 'https://example.com/3' }),
    makeRow({ id: 2, created_time: '2026-01-02 00:00:00', original_url: 'https://example.com/2' }),
  ]);

  const first = await generate({ ...paths });
  assert.equal(first.ok, true, first.errors.join('\n'));
  assert.equal(first.count, 3);
  assert.equal(first.previousCount, null);

  const jsonRows = readGeneratedRows(paths.jsonPath);
  const jsRows = readGeneratedRows(paths.jsPath);
  assert.deepEqual(jsonRows, jsRows);
  assert.deepEqual(jsonRows.map((row) => row.id), [3, 2, 1]);
  assertNoTemps(paths.jsonPath, paths.jsPath);

  const firstJsonBytes = fs.readFileSync(paths.jsonPath);
  const firstJsBytes = fs.readFileSync(paths.jsPath);

  const second = await generate({ ...paths });
  assert.equal(second.ok, true, second.errors.join('\n'));
  assert.equal(second.previousCount, 3);
  assert.deepEqual(fs.readFileSync(paths.jsonPath), firstJsonBytes);
  assert.deepEqual(fs.readFileSync(paths.jsPath), firstJsBytes);
});

test('DB 不存在或损坏：ok:false 且不写文件', async (t) => {
  const paths = tempPaths(t);

  const missing = await generate({ ...paths });
  assert.equal(missing.ok, false);
  assert.match(missing.errors.join('\n'), /数据库不存在/);
  assert.match(missing.errors.join('\n'), /web_content\.db/);
  assert.equal(fs.existsSync(paths.jsonPath), false);
  assert.equal(fs.existsSync(paths.jsPath), false);

  fs.writeFileSync(paths.dbPath, 'this is definitely not a sqlite database');
  const corrupt = await generate({ ...paths });
  assert.equal(corrupt.ok, false);
  assert.match(corrupt.errors.join('\n'), /读取数据库失败/);
  assert.match(corrupt.errors.join('\n'), /web_content\.db/);
  assert.equal(fs.existsSync(paths.jsonPath), false);
  assert.equal(fs.existsSync(paths.jsPath), false);
});

test('空表：ok:false 且不写文件', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, []);

  const result = await generate({ ...paths });
  assert.equal(result.ok, false);
  assert.match(result.errors.join('\n'), /为空/);
  assert.equal(fs.existsSync(paths.jsonPath), false);
  assert.equal(fs.existsSync(paths.jsPath), false);
});

test('坏行（缺 category）：ok:false 且已有输出不变', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [makeRow({ category: null })]);
  fs.writeFileSync(paths.jsonPath, 'OLD JSON\n');
  fs.writeFileSync(paths.jsPath, 'export default [];\n');

  const result = await generate({ ...paths });
  assert.equal(result.ok, false);
  assert.match(result.errors.join('\n'), /category 非法/);
  assert.equal(fs.readFileSync(paths.jsonPath, 'utf-8'), 'OLD JSON\n');
  assert.equal(fs.readFileSync(paths.jsPath, 'utf-8'), 'export default [];\n');
  assertNoTemps(paths.jsonPath, paths.jsPath);
});

test('缩水拦截；allowShrink 放行并记录 warning', async (t) => {
  const paths = tempPaths(t);
  const previousRows = Array.from({ length: 10 }, (_, index) => makeRow({
    id: index + 1,
    original_url: `https://example.com/${index + 1}`,
  }));
  fs.writeFileSync(paths.jsPath, `export default ${JSON.stringify(previousRows)};\n`);
  fs.writeFileSync(paths.jsonPath, `${JSON.stringify(previousRows, null, 2)}\n`);
  const previousJs = fs.readFileSync(paths.jsPath, 'utf-8');
  const previousJson = fs.readFileSync(paths.jsonPath, 'utf-8');

  await createDb(paths.dbPath, Array.from({ length: 5 }, (_, index) => makeRow({
    id: index + 1,
    original_url: `https://example.com/${index + 1}`,
  })));

  const blocked = await generate({ ...paths });
  assert.equal(blocked.ok, false);
  assert.match(blocked.errors.join('\n'), /缩水阈值/);
  assert.equal(fs.readFileSync(paths.jsPath, 'utf-8'), previousJs);
  assert.equal(fs.readFileSync(paths.jsonPath, 'utf-8'), previousJson);
  assertNoTemps(paths.jsonPath, paths.jsPath);

  const allowed = await generate({ ...paths, allowShrink: true });
  assert.equal(allowed.ok, true, allowed.errors.join('\n'));
  assert.equal(allowed.count, 5);
  assert.equal(allowed.previousCount, 10);
  assert.match(allowed.warnings.join('\n'), /缩水|放行/);
  assert.equal(readGeneratedRows(paths.jsPath).length, 5);
  assert.equal(readGeneratedRows(paths.jsonPath).length, 5);
});

test('上一版无法解析：默认抛错且不写；allowShrink 放行', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [makeRow()]);
  const broken = 'export default [{"broken"';
  fs.writeFileSync(paths.jsPath, broken);
  fs.writeFileSync(paths.jsonPath, 'OLD JSON\n');

  await assert.rejects(
    () => generate({ ...paths }),
    (error) => {
      assert.match(error.message, /无法解析上一版/);
      assert.match(error.message, /--allow-shrink/);
      return true;
    },
  );
  assert.equal(fs.readFileSync(paths.jsPath, 'utf-8'), broken);
  assert.equal(fs.readFileSync(paths.jsonPath, 'utf-8'), 'OLD JSON\n');
  assertNoTemps(paths.jsonPath, paths.jsPath);

  const allowed = await generate({ ...paths, allowShrink: true });
  assert.equal(allowed.ok, true, allowed.errors.join('\n'));
  assert.equal(allowed.previousCount, null);
  assert.match(allowed.warnings.join('\n'), /无法解析上一版/);
  assert.equal(readGeneratedRows(paths.jsPath).length, 1);
  assert.equal(readGeneratedRows(paths.jsonPath).length, 1);
});

test('上一版不是数组：默认抛错且不写；allowShrink 放行', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [makeRow()]);
  const nonArray = 'export default {};\n';
  fs.writeFileSync(paths.jsPath, nonArray);
  fs.writeFileSync(paths.jsonPath, 'OLD JSON\n');

  await assert.rejects(
    () => generate({ ...paths }),
    (error) => {
      assert.match(error.message, /无法解析上一版/);
      assert.match(error.message, /生成物不是数组/);
      assert.match(error.message, /--allow-shrink/);
      return true;
    },
  );
  assert.equal(fs.readFileSync(paths.jsPath, 'utf-8'), nonArray);
  assert.equal(fs.readFileSync(paths.jsonPath, 'utf-8'), 'OLD JSON\n');
  assertNoTemps(paths.jsonPath, paths.jsPath);

  const allowed = await generate({ ...paths, allowShrink: true });
  assert.equal(allowed.ok, true, allowed.errors.join('\n'));
  assert.equal(allowed.previousCount, null);
  assert.match(allowed.warnings.join('\n'), /无法解析上一版/);
  assert.equal(readGeneratedRows(paths.jsPath).length, 1);
  assert.equal(readGeneratedRows(paths.jsonPath).length, 1);
});

test('warning 只返回给调用方，库内不重复打印', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [makeRow()]);
  fs.writeFileSync(paths.jsPath, 'export default {};\n');
  fs.writeFileSync(paths.jsonPath, 'OLD JSON\n');

  const printed = [];
  const originalWarn = console.warn;
  console.warn = (...args) => printed.push(args.join(' '));
  let allowed;
  try {
    allowed = await generate({ ...paths, allowShrink: true });
  } finally {
    console.warn = originalWarn;
  }

  assert.equal(allowed.ok, true, allowed.errors.join('\n'));
  // 库内不再 log.warn；CLI 统一打印 result.warnings，每条仅一次。
  assert.equal(allowed.warnings.length, 1, allowed.warnings.join('\n'));
  assert.match(allowed.warnings[0], /无法解析上一版/);
  assert.match(allowed.warnings[0], /生成物不是数组/);
  assert.deepEqual(printed, []);
});

test('写入失败：抛错、json 回滚、无 .tmp 残留', async (t) => {
  const paths = tempPaths(t);
  await createDb(paths.dbPath, [makeRow()]);
  const oldJson = '{"old":true}\n';
  fs.writeFileSync(paths.jsonPath, oldJson);

  const jsAsDirectory = path.join(paths.dir, 'static-data-dir');
  fs.mkdirSync(jsAsDirectory);

  await assert.rejects(
    () => generate({ ...paths, jsPath: jsAsDirectory }),
    /写入失败.*回滚.*重跑/,
  );

  assert.equal(fs.readFileSync(paths.jsonPath, 'utf-8'), oldJson);
  assert.equal(fs.statSync(jsAsDirectory).isDirectory(), true);
  assertNoTemps(paths.jsonPath, jsAsDirectory);
});

test('CLI 拒绝未知参数，非 0 退出且不改输出文件', () => {
  const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
  const files = [
    path.join(repoRoot, 'src/assets/static-data.json'),
    path.join(repoRoot, 'src/assets/static-data.js'),
  ];
  const before = files.map(sha256);

  const result = spawnSync(
    process.execPath,
    ['scripts/generate-data.js', '--from-json'],
    { cwd: repoRoot, encoding: 'utf-8' },
  );

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /未知参数/);
  assert.deepEqual(files.map(sha256), before);
  assertNoTemps(...files);
});
