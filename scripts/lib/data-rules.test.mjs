// scripts/lib/data-rules.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateRows, compareDatasets } from './data-rules.mjs';

const base = {
  id: 1,
  title: '标题',
  category: '文章',
  tags: 'AI',
  created_time: '2026-08-28 13:22:58',
  summary: '摘要',
  original_url: 'https://example.com/a',
};

test('合法数据通过', () => {
  const r = validateRows([base]);
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.deepEqual(r.errors, []);
});

test('缺 category 报错', () => {
  const r = validateRows([{ ...base, category: undefined }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /category 非法/);
});

test('重复 id 报错', () => {
  const r = validateRows([base, { ...base, title: '另一条' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /id 重复/);
});

test('空 tags 报错', () => {
  const r = validateRows([{ ...base, tags: '  ' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /tags 为空/);
});

test('坏时间报错', () => {
  const r = validateRows([{ ...base, created_time: '2026/08/28' }]);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /created_time 无法解析/);
});

test('缩水超过 10% 报错，allowShrink 放行', () => {
  const rows = [base, { ...base, id: 2 }, { ...base, id: 3 }];
  const blocked = validateRows(rows, { previousCount: 4 });
  assert.equal(blocked.ok, false);
  assert.match(blocked.errors.join('\n'), /缩水阈值/);

  const allowed = validateRows(rows, { previousCount: 4, allowShrink: true });
  assert.equal(allowed.ok, true, JSON.stringify(allowed.errors));
});

test('compareDatasets 发现条数与字段差异', () => {
  const published = [
    { ...base, category: '工具' }, // 字段不同
    { ...base, id: 3 },             // 多出
  ];
  const r = compareDatasets([base], published);
  assert.equal(r.ok, false);
  assert.match(r.errors.join('\n'), /条数不一致/);
  assert.match(r.errors.join('\n'), /字段 category 不一致/);
  assert.match(r.errors.join('\n'), /生成物多出/);
});

test('compareDatasets 一致时通过', () => {
  const r = compareDatasets([base], [{ ...base }]);
  assert.equal(r.ok, true, JSON.stringify(r.errors));
});
