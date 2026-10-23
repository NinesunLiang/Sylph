#!/usr/bin/env node
// STATE-DIFF — 交互态/二级 UI 真值比对（机制 §十三·比对层）
// 用法: node scripts/ui-restore/state-diff.mjs --task home_page [--tol 2]
// 输入: gold/states/<name>.delta.json  vs  measurements/latest/states/<name>.delta.json
// 匹配: 文本节点按 ownText 精确匹配；容器按特征锚（ul/白底大面板/全屏遮罩/深色小气泡）
// 判定: 几何 |Δ|>tol(默认2px, 整数像素律) 或样式字段不一致 → 差异项
// 产出: measurements/latest/states-diff.json（可直接并入 fix-list 闭环）
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';
import { loadTask, REPO_ROOT } from './task-config.mjs';

const args = process.argv.slice(2);
const optNum = (n, d) => { const i = args.indexOf(n); return i > -1 ? +args[i + 1] : d; };
const optStr = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const TASK = optStr('--task', 'home_page');
const TOL = optNum('--tol', 2);
const cfg = loadTask(TASK);
const DIR = join(REPO_ROOT, '.omc', 'ui-autopilot', TASK);
const GOLD = join(DIR, 'gold', 'states');
const IMPL = join(DIR, 'measurements', 'latest', 'states');

const GEO = ['x', 'y', 'w', 'h'];
// 容器: fs/lh 被覆盖无意义；color 是继承文本色（mask rgb(8,8,8) vs rgb(0,0,0) 类噪声）
const CONTAINER_STYLE = ['bg', 'radius', 'pad', 'border', 'shadow'];
const TEXT_STYLE = ['fs', 'fw', 'color']; // 文本: w/h 是字体度量噪声，节奏由 y 捕获

// 零宽边框颜色无意义：0px none rgb(8,8,8) ≡ 0px none rgb(0,0,0)
const normBorder = v => String(v ?? '').replace(/^(0px\s+\S+)\s+.*$/, '$1');

function load(p) { try { return JSON.parse(readFileSync(p, 'utf8')); } catch { return null; } }

// 特征锚容器：面板 ul / 白底 dialog 壳 / 全屏遮罩 / 深色 tooltip 气泡（alpha≥0.5 排除 hover 底砖）
const isDarkSolid = r => {
  const m = (r.bg || '').match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
  return m && +m[1] < 60 && +m[2] < 60 && +m[3] < 60 && (m[4] === undefined || +m[4] >= 0.5);
};

// 特征锚容器：面板 ul / 白底 dialog 壳 / 全屏遮罩 / 深色 tooltip 气泡
// bubble 锚仅用于 tooltip 态——dialog 里的深色元素（关闭图标等）不是气泡
function anchors(rows, stateName) {
  const out = [];
  const ulCandidates = rows.filter(r => r.tag === 'ul');
  const ul = (stateName || '').startsWith('category-')
    ? ulCandidates.filter(r => r.x < 300).sort((a, b) => a.x - b.x || a.y - b.y)[0]
    : ulCandidates.sort((a, b) => b.w - a.w)[0];
  if (ul) out.push(['container<ul>', ul]);
  const shell = rows.find(r => r.w >= 400 && r.bg === 'rgb(255, 255, 255)' && r.h >= 200);
  if (shell) out.push(['dialog-shell', shell]);
  // 遮罩锚仅当 gold 遮罩有不透明背景——路由级全屏容器（launcher）是透明壳，bg 对比无意义（§十三 修正）
  const maskOpaque = r => {
    const m = (r.bg || '').match(/rgba?\([\d\s,]+?,\s*([\d.]+)\)/);
    return m && +m[1] > 0;
  };
  const mask = rows.find(r => r.w >= cfg.vw - 4 && r.h >= cfg.vh - 4 && maskOpaque(r));
  if (mask) out.push(['mask', mask]);
  if ((stateName || '').startsWith('tooltip')) {
    const bubble = rows.find(r => isDarkSolid(r) && r.w < 300);
    if (bubble) out.push(['bubble', bubble]);
  }
  return out;
}

function textNodes(rows) {
  const seen = new Set(), out = [];
  for (const r of rows) {
    const t = normText(r.text);
    if (!t || t.length > 40 || seen.has(t)) continue;
    seen.add(t); out.push([t, r]);
  }
  return out;
}

// 时变文本归一（§十三 修正）：问候语随采集时刻变化（gold 晚上好 vs impl 早上好 属同节点，不比文案只比位置）
const normText = t => {
  const s = (t || '').trim();
  return /^(早上好|下午好|晚上好)$/.test(s) ? 'GREETING' : s;
};

const results = [];
let totalDiffs = 0;
// 迭代 task.json states[]（真值源），不是 gold 目录——已删除的态不应再比对（orphan 文件仅告警）
const baseRows = (() => { try { return JSON.parse(readFileSync(join(DIR, 'measurements', 'latest', 'base.json'), 'utf8')).rows; } catch { return null; } })();
const baseTexts = new Set((baseRows || []).map(r => (r.text || '').trim()).filter(Boolean));
const orphan = existsSync(GOLD) ? readdirSync(GOLD).filter(f => f.endsWith('.delta.json')).map(f => f.replace('.delta.json', '')).filter(n => !(cfg.states || []).some(s => s.name === n)) : [];
if (orphan.length) console.log(`orphan gold 文件（task.json 已移除，跳过）: ${orphan.join(', ')}`);
for (const st of cfg.states || []) {
  const name = st.name;
  const f = `${name}.delta.json`;
  const gd = load(join(GOLD, f));
  const id = existsSync(join(IMPL, f)) ? load(join(IMPL, f)) : null;
  if (!gd) { results.push({ state: name, error: 'gold 未采集（先跑 capture-states）' }); totalDiffs++; continue; }
  if (!id) { results.push({ state: name, error: 'impl 未采集（先跑 capture-states）' }); totalDiffs++; continue; }
  const g = gd.rows || [];
  const i = id.rows || [];
  const fullState = gd.capture === 'full' || id.capture === 'full';
  const diffs = [];
  const goldRouteChanged = gd.routeBefore && gd.routeAfter && new URL(gd.routeBefore).pathname !== new URL(gd.routeAfter).pathname;
  const implRouteChanged = id.routeBefore && id.routeAfter && new URL(id.routeBefore).pathname !== new URL(id.routeAfter).pathname;
  if (goldRouteChanged || implRouteChanged) {
    const goldPath = new URL(gd.routeAfter || gd.url).pathname;
    const implPath = new URL(id.routeAfter || id.url).pathname;
    const samePathState = goldPath === implPath;
    if (goldRouteChanged && implRouteChanged && samePathState && !name.startsWith('category-')) {
      results.push({ state: name, routeGold: gd.routeAfter, routeImpl: id.routeAfter, routeChanged: true, routeMatched: true, goldNodes: g.length, implNodes: i.length, diffs: [], diffCount: 0 });
      console.log(`${name}: 路由转换已匹配 ${goldPath}`);
      continue;
    }
    if (goldPath !== implPath) {
      results.push({ state: name, routeGold: gd.routeAfter, routeImpl: id.routeAfter, routeChanged: true, routeMatched: false, goldNodes: g.length, implNodes: i.length, diffs: [{ node: 'route', field: 'pathname', impl: implPath, gold: goldPath }], diffCount: 1 });
      totalDiffs++;
      continue;
    }
  }
  // 容器锚比对：full 快照包含整页基线，不使用 delta 专用 dialog/tooltip 锚
  for (const [label, gr] of (fullState ? [] : anchors(g, name))) {
    const ir = label.startsWith('container')
      ? i.filter(r => r.tag === 'ul').sort((a, b) => b.w - a.w)[0]
      : anchors(i, name).find(([l]) => l === label)?.[1];
    if (!ir) { diffs.push({ node: label, field: 'missing', gold: 'exists' }); continue; }
    for (const k of [...GEO, ...CONTAINER_STYLE]) {
      let gv = gr[k], iv = ir[k];
      if (gv === undefined || iv === undefined) continue;
      if (k === 'border') { gv = normBorder(gv); iv = normBorder(iv); }
      if (GEO.includes(k) ? Math.abs(+gv - +iv) > TOL : gv !== iv) {
        diffs.push({ node: label, field: k, impl: iv, gold: gv });
      }
    }
  }
  // 文本节点比对（位置 + 字体样式，不比 w/h）
  const implTexts = textNodes(i);
  for (const [t, gr] of textNodes(g)) {
    const hit = implTexts.find(([it]) => it === t);
    // gold 的 hover 重挂载会把基页已有文本带进 delta（如 默认列表 行）——impl 基页存在即非缺失
    if (!hit) {
      if (baseTexts.has(t)) continue;
      diffs.push({ node: `text:${t.slice(0, 16)}`, field: 'missing', gold: 'exists' });
      continue;
    }
    const ir = hit[1];
    for (const k of ['x', 'y', ...TEXT_STYLE]) {
      const gv = gr[k], iv = ir[k];
      if (gv === undefined || iv === undefined) continue;
      if (GEO.includes(k) ? Math.abs(+gv - +iv) > TOL : gv !== iv) {
        diffs.push({ node: `text:${t.slice(0, 16)}`, field: k, impl: iv, gold: gv });
      }
    }
  }
  totalDiffs += diffs.length;
  results.push({ state: name, goldNodes: g.length, implNodes: i.length, diffs: diffs.slice(0, 40), diffCount: diffs.length });
  console.log(`${name}: 差异 ${diffs.length} 项${diffs.length ? '（首项: ' + JSON.stringify(diffs[0]).slice(0, 90) + '）' : ''}`);
}
writeFileSync(join(DIR, 'measurements', 'latest', 'states-diff.json'), JSON.stringify({ tolerance: TOL, totalDiffs, results }, null, 1));
console.log(`STATE-DIFF 总计 ${totalDiffs} 项 → measurements/latest/states-diff.json`);
process.exit(totalDiffs ? 1 : 0);
