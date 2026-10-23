// 中转服务的契约校验测试（零依赖，node --test）
//
// 运行：
//   cd apps/photo_coach/server && node --test
//
// 为什么值得测：服务端和客户端各自有一份「契约」实现，
// 两边不一致的话，客户端解析失败率会莫名其妙变高。
// 这个测试锁住服务端这一侧的行为。

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { validateSuggestion, extractJson } from './server.mjs';

const good = {
  schema_version: '1.0',
  composition: { rule: 'rule_of_thirds', confidence: 0.8, horizon_tilt_deg: -1 },
  subject: {
    label: 'person',
    current_box: [0.4, 0.3, 0.2, 0.5],
    target_box: [0.33, 0.25, 0.2, 0.5],
  },
  camera_move: { pan_deg: -5, tilt_deg: 2, dolly_m: 0, zoom: 1, hint: '左一点' },
  exposure: { ev: -0.3, reason: '高光过曝' },
  tips: ['主体放三分之一线'],
};

test('合法建议：0 个问题', () => {
  assert.deepEqual(validateSuggestion(good), []);
});

test('缺字段：逐个报出来（不静默）', () => {
  const problems = validateSuggestion({
    composition: {},
    subject: {},
    camera_move: {},
    exposure: {},
  });
  assert.ok(problems.some((p) => p.includes('schema_version')));
  assert.equal(problems.length, 1);
});

test('顶层不是对象 / null / 数组都要报错', () => {
  assert.deepEqual(validateSuggestion(null), ['顶层不是对象']);
  assert.deepEqual(validateSuggestion([1, 2]), ['顶层不是对象']);
  assert.deepEqual(validateSuggestion('x'), ['顶层不是对象']);
});

test('坐标框必须是 4 个数字', () => {
  const problems = validateSuggestion({
    ...good,
    subject: { label: 'p', current_box: [1, 2], target_box: 'nope' },
  });
  assert.equal(problems.filter((p) => p.includes('box')).length, 2);
});

test('tips 不是数组要报错', () => {
  const problems = validateSuggestion({ ...good, tips: '不是数组' });
  assert.ok(problems.some((p) => p.includes('tips')));
});

test('缺 composition/subject/camera_move/exposure 各自报出', () => {
  const problems = validateSuggestion({ schema_version: '1.0' });
  assert.equal(problems.length, 4);
});

test('extractJson：纯 JSON / 围栏 / 带前后文 / 转义', () => {
  assert.deepEqual(extractJson('{"a":1}'), { a: 1 });
  assert.deepEqual(extractJson('```json\n{"a":1}\n```'), { a: 1 });
  assert.deepEqual(extractJson('好的：\n{"a":1}\n完'), { a: 1 });
  assert.deepEqual(extractJson('{"t":"说 \\"嗨\\" 了","n":2}'), {
    t: '说 "嗨" 了',
    n: 2,
  });
});

test('extractJson：没有 JSON 返回 null', () => {
  assert.equal(extractJson('我看不清这张图'), null);
  assert.equal(extractJson(''), null);
  assert.equal(extractJson(null), null);
});
