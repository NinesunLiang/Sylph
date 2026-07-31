#!/usr/bin/env node
// DISCOVER-STATES — 二级 UI 触发器自动发现（机制 §十三·发现层）
// 用法: node scripts/ui-restore/discover-states.mjs <url> --task home_page [--dismiss-modal] [--wait ms] [--max N]
// 原理: 枚举页面可交互元素 → 逐个 hover（单页面顺序扫，hover 态自动消失）
//       → 逐个 click（每候选独立新页面，防状态污染）→ DOM delta 检测
//       delta>0 即发现二级 UI；按 delta 特征分类 tooltip/dialog/popover
// 产出: 合并写入 task.json states[]（auto:true 标记，幂等——重跑只替换 auto 项，保留手写项）
// 无人值守设计: DOM 静默等待 / 全超时兜底 / 失败跳过不中断
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { loadTask, REPO_ROOT } from './task-config.mjs';

const [url, ...flags] = process.argv.slice(2);
const opt = (n, d) => { const i = flags.indexOf(n); return i > -1 ? +flags[i + 1] : d; };
if (!url) { console.error('usage: discover-states.mjs <url> --task X [--dismiss-modal] [--wait ms] [--max N]'); process.exit(1); }
const TASK = opt('--task', 0) || 'home_page';
const cfg = loadTask(TASK);
const WAIT = opt('--wait', 3000);
const MAX = opt('--max', 60);
const DISMISS = flags.includes('--dismiss-modal');

const EXTRACT = () => {
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    out.push({
      tag: el.tagName.toLowerCase(), text: ownText.slice(0, 60),
      cls: String(el.className?.baseVal ?? el.className ?? '').slice(0, 100),
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
      bg: cs.backgroundColor, fs: cs.fontSize,
    });
  });
  return out;
};
const sig = r => `${r.tag}|${r.cls}|${r.text}|${r.x},${r.y},${r.w},${r.h}`;

// 候选触发器：可见、小尺寸（图标/按钮级）、可交互特征
const CANDIDATES = () => {
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8 || r.width > 220 || r.height > 80) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const clickable = cs.cursor === 'pointer' || el.tagName === 'BUTTON' || el.getAttribute('role') === 'button';
    if (!clickable) return;
    const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    const svgCls = [...el.querySelectorAll('svg')].map(s => String(s.className?.baseVal ?? s.className ?? '')).find(c => c.includes('lucide-'));
    const icon = svgCls ? (svgCls.match(/lucide-([a-z0-9-]+)/) || [])[1] : null;
    out.push({
      x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2),
      text: ownText.slice(0, 30), icon, w: Math.round(r.width), h: Math.round(r.height),
    });
  });
  // 去重：同中心点只留一个（父子嵌套都 pointer 时取子级=后出现的）
  const seen = new Set();
  return out.filter(c => { const k = `${c.x},${c.y}`; if (seen.has(k)) return false; seen.add(k); return true; });
};

async function domQuiet(page, quiet = 1000) {
  await page.evaluate((q) => new Promise(res => {
    let timer;
    const done = () => { obs.disconnect(); res(true); };
    const obs = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(done, q); });
    timer = setTimeout(done, q);
    obs.observe(document.body, { childList: true, subtree: true, attributes: true });
    setTimeout(done, 12000);
  }), quiet).catch(() => {});
}

async function newPage(b) {
  const page = await b.newPage({ viewport: { width: cfg.vw, height: cfg.vh } });
  // 站点限流/网络抖动重试（无人值守：单点失败不得炸掉整轮）
  for (let attempt = 0; attempt < 3; attempt++) {
    try { await page.goto(url, { timeout: 90000, waitUntil: 'domcontentloaded' }); break; }
    catch (e) {
      if (attempt === 2) throw e;
      console.log(`  goto 重试 ${attempt + 1}/2: ${e.message.slice(0, 50)}`);
      await page.waitForTimeout(3000 + attempt * 5000);
    }
  }
  await page.waitForTimeout(WAIT);
  if (DISMISS) {
    for (const label of ['确 定', '确定', '×']) {
      try { await page.click(`button:has-text("${label}")`, { timeout: 2500 }); break; } catch {}
    }
    await page.waitForTimeout(600);
  }
  await domQuiet(page);
  return page;
}

const diff = (before, after) => {
  const bs = new Set(before.map(sig));
  return after.filter(r => !bs.has(sig(r)));
};

// 分类：tooltip（小增量+深色小气泡）/ dialog（全屏遮罩）/ popover（其余）
function classify(delta) {
  if (!delta.length) return null;
  const mask = delta.find(r => r.w >= cfg.vw - 4 && r.h >= cfg.vh - 4 && /rgba?\(.*0\.[1-7]/.test(r.bg));
  if (mask) return 'dialog';
  const bubble = delta.find(r => {
    const m = r.bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m && +m[1] < 60 && +m[2] < 60 && +m[3] < 60 && r.text && r.w < 300;
  });
  if (bubble && delta.length <= 12) return 'tooltip';
  return 'popover';
}

function anchorOf(c, used) {
  const a = {};
  if (c.icon) a.icon = c.icon;
  else if (c.text) a.text = c.text;
  else return null;
  // 同名/同图标消歧：记录 y 过滤
  const key = `${a.icon || ''}|${a.text || ''}`;
  if (used.has(key)) a.y = c.y > cfg.vh / 2 ? `>${cfg.vh / 2}` : `<${cfg.vh / 2}`;
  used.add(key);
  return a;
}

const b = await chromium.launch({ headless: true });
const found = new Map(); // name → state def
const usedAnchors = new Set();

// ── 增量落盘：每发现一个/每完成一阶段立即写回 task.json（崩溃不丢已发现结果）──
const taskPath = join(REPO_ROOT, '.omc', 'ui-autopilot', TASK, 'task.json');
function saveCheckpoint(stage) {
  const task = JSON.parse(readFileSync(taskPath, 'utf8'));
  const manual = (task.states || []).filter(s => !s.auto);
  task.states = [...manual, ...found.values()];
  writeFileSync(taskPath, JSON.stringify(task, null, 2) + '\n');
  console.log(`[checkpoint:${stage}] 已发现 ${found.size} 个 → task.json`);
}

// ── Pass 1: hover 扫描（单页面，tooltip 类）──
{
  const page = await newPage(b);
  const cands = (await page.evaluate(CANDIDATES)).slice(0, MAX);
  console.log(`hover 候选 ${cands.length} 个`);
  for (const c of cands) {
    try {
      await page.mouse.move(cfg.vw - 5, cfg.vh - 5, { steps: 3 }); // 先移到死角重置 hover（避开侧栏/输入区）
      await page.waitForTimeout(400); // 等上一个 tooltip 淡出
      const before = await page.evaluate(EXTRACT);
      await page.mouse.move(c.x, c.y, { steps: 4 });
      await page.waitForTimeout(900);
      const delta = diff(before, await page.evaluate(EXTRACT));
      if (classify(delta) === 'tooltip') {
        const tip = delta.find(r => r.text && r.bg.includes('rgb'));
        const name = `tooltip-${(tip?.text || c.text || c.icon || 'x').slice(0, 20)}`;
        if (!found.has(name)) {
          const anchor = anchorOf(c, usedAnchors);
          if (anchor) found.set(name, { name, auto: true, action: { type: 'hover', ...anchor }, settle: 900 });
        }
      }
    } catch (e) { console.log(`hover (${c.x},${c.y}) 失败跳过: ${e.message.slice(0, 60)}`); }
  }
  await page.close();
  saveCheckpoint('hover');
}

// ── Pass 2: click 扫描（每候选独立页面，dropdown/dialog/popover 类）──
{
  const page0 = await newPage(b);
  const cands = (await page0.evaluate(CANDIDATES)).slice(0, MAX);
  await page0.close();
  console.log(`click 候选 ${cands.length} 个`);
  for (const c of cands) {
    await new Promise(r => setTimeout(r, 400)); // 礼貌间隔，降低限流概率
    let page;
    try {
      page = await newPage(b);
      const before = await page.evaluate(EXTRACT);
      await page.mouse.click(c.x, c.y);
      await page.waitForTimeout(1000);
      const delta = diff(before, await page.evaluate(EXTRACT));
      const kind = classify(delta);
      if (kind && kind !== 'tooltip') {
        const anchor = anchorOf(c, usedAnchors);
        if (anchor) {
          const base = `${kind}-${c.text || c.icon || 'x'}`.slice(0, 30);
          let name = base; let i = 2;
          while (found.has(name)) name = `${base}-${i++}`;
          found.set(name, { name, auto: true, action: { type: 'click', ...anchor }, settle: 1000 });
          saveCheckpoint(`click:${name}`);
        }
      }
    } catch (e) { console.log(`click (${c.x},${c.y}) 失败跳过: ${e.message.slice(0, 60)}`); }
    await page?.close().catch(() => {});
  }
  saveCheckpoint('click');
}
await b.close();

console.log(`发现 ${found.size} 个二级 UI 态 → task.json states[]`);
[...found.keys()].forEach(n => console.log('  +', n));
