#!/usr/bin/env node
// RECLASSIFY-STATES — 交互态分类校正（机制 §十三·校正层）
// 用法: node scripts/ui-restore/reclassify-states.mjs --task home_page [--dry]
// 为什么: discover-states 在公告弹窗/慢渲染干扰下会把 tooltip 误判为 dialog/popover
//         （点击后鼠标静置 → 悬停气泡进 delta；弹窗遮罩进 delta → 误判 dialog）
// 真值源: gold/states/<name>.delta.json 的 delta 内容才是分类依据：
//   深色实心气泡(alpha≥0.5, w<300, 有文本) + delta≤16  → tooltip（action 改 hover，改名 tooltip-<文本>）
//   全屏遮罩 rgba 0.1-0.7                            → dialog（保持 click）
//   全屏透明容器 + 进度条特征                          → launcher（保持 click）
//   其余                                              → popover（保持 click）
// 去重: 动作签名相同（type+icon+text+y）的态只留一个（manual 优先，同名先到先得）
// 幂等: 重跑无变化则不写文件；文件改名同步处理 gold/impl 两侧 .delta.json/.png
import { readFileSync, writeFileSync, existsSync, renameSync, readdirSync } from 'fs';
import { join } from 'path';
import { loadTask, REPO_ROOT } from './task-config.mjs';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const TASK = opt('--task', 'home_page');
const DRY = args.includes('--dry');
const cfg = loadTask(TASK);
const DIR = join(REPO_ROOT, '.omc', 'ui-autopilot', TASK);
const taskPath = join(DIR, 'task.json');

const isDarkSolid = r => {
  const m = (r.bg || '').match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
  return m && +m[1] < 60 && +m[2] < 60 && +m[3] < 60 && (m[4] === undefined || +m[4] >= 0.5);
};

function classifyFromGold(name) {
  const f = join(DIR, 'gold', 'states', `${name}.delta.json`);
  if (!existsSync(f)) return null;
  const rows = JSON.parse(readFileSync(f, 'utf8')).rows;
  const mask = rows.find(r => r.w >= cfg.vw - 4 && r.h >= cfg.vh - 4 && /rgba?\(.*0\.[1-7]/.test(r.bg || ''));
  if (mask) return { kind: 'dialog' };
  const fullscreen = rows.filter(r => r.w >= cfg.vw - 4 && r.h >= cfg.vh - 4);
  const progress = rows.find(r => r.h <= 12 && r.w >= 100 && (r.radius || '').includes('100'));
  if (fullscreen.length && progress) return { kind: 'launcher' };
  const bubble = rows.find(r => isDarkSolid(r) && r.w < 300);
  if (bubble && rows.length <= 16) {
    // 气泡文本可能在子节点（gold tooltip-将当前会话保存为话题：气泡壳无 ownText，文本在内层 div）
    const text = (bubble.text || '').trim() || (rows.find(r => (r.text || '').trim())?.text || '').trim();
    if (text) return { kind: 'tooltip', text };
  }
  return { kind: 'popover' };
}

const task = JSON.parse(readFileSync(taskPath, 'utf8'));
const states = task.states || [];
const renames = new Map(); // oldName → newName
let changed = 0;

for (const s of states) {
  if (!s.auto) continue; // 手写态不碰
  const c = classifyFromGold(s.name);
  if (!c) continue;
  if (c.kind === 'tooltip' && s.action?.type !== 'hover') {
    const newName = `tooltip-${c.text}`.slice(0, 40);
    if (newName !== s.name) renames.set(s.name, newName);
    s.action = { ...s.action, type: 'hover' };
    s.name = newName;
    changed++;
  }
}

// 去重：动作签名相同只留一个（manual 优先）
const seen = new Map();
const kept = [];
for (const s of states) {
  const a = s.action || {};
  const sig = `${a.type}|${a.icon || ''}|${a.text || ''}|${a.y || ''}`;
  if (seen.has(sig)) {
    const prev = seen.get(sig);
    if (s.auto && !prev.auto) { changed++; continue; } // 丢 auto 重复
    if (s.auto && prev.auto) { changed++; continue; }  // auto 互重丢后者
  }
  seen.set(sig, s);
  kept.push(s);
}
if (kept.length !== states.length) changed += states.length - kept.length;
task.states = kept;

if (!changed) { console.log('RECLASSIFY: 无变化（幂等通过）'); process.exit(0); }
console.log(`RECLASSIFY: ${renames.size} 个改名, 去重后 ${kept.length} 个态${DRY ? '（dry-run 不落盘）' : ''}`);
for (const [o, n] of renames) console.log(`  ${o} → ${n}`);
if (DRY) process.exit(0);

writeFileSync(taskPath, JSON.stringify(task, null, 2) + '\n');
// 文件改名（gold/impl 两侧；impl 侧原名文件删除即可——hover 重采会生成新名文件）
for (const [o, n] of renames) {
  for (const side of ['gold/states', 'measurements/latest/states']) {
    for (const ext of ['delta.json', 'png']) {
      const from = join(DIR, side, `${o}.${ext}`);
      if (existsSync(from)) renameSync(from, join(DIR, side, `${n}.${ext}`));
    }
  }
}
console.log('→ task.json 已更新，gold/impl 文件已同步改名');
