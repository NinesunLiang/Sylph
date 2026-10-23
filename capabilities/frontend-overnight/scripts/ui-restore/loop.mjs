#!/usr/bin/env node
// UI autopilot 健康探针：截图 + DOM + console + vite overlay + typecheck → loop.log
// 用法: node scripts/ui-restore/loop.mjs [--task home_page]
// 通用化: ROOT 由脚本位置推导，视口/URL 来自 task.json
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { execSync } from 'child_process';
import { loadTask, REPO_ROOT } from './task-config.mjs';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const TASK = opt('--task', 'home_page');
const cfg = loadTask(TASK);
const ROOT = REPO_ROOT;
const OUT = `${ROOT}/.omc/ui-autopilot/${TASK}/measurements`;
const K3 = process.env.K3_API_KEY || '';
mkdirSync(OUT, { recursive: true });
mkdirSync(`${OUT}/latest`, { recursive: true }); // base.json 落地目录

// Tee stdout/stderr to loop.log — eliminates shell-redirect dependency
import { createWriteStream } from 'fs';
const _logStream = createWriteStream(`${OUT}/loop.log`, { flags: 'a' });
const _origWrite = process.stdout.write.bind(process.stdout);
const _origErrWrite = process.stderr.write.bind(process.stderr);
process.stdout.write = (chunk, ...a) => { _logStream.write(chunk); return _origWrite(chunk, ...a); };
process.stderr.write = (chunk, ...a) => { _logStream.write(chunk); return _origErrWrite(chunk, ...a); };

let iter = 1;
try { iter = parseInt(readFileSync(`${OUT}/loop.txt`, 'utf8')) + 1; } catch {}
writeFileSync(`${OUT}/loop.txt`, String(iter));
console.log(`\n=== LOOP ${iter} ===`);

try {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage({ viewport: { width: cfg.vw, height: cfg.vh } });
  let errs = 0;
  p.on('console', msg => { if (msg.type() === 'error') errs++; });
  await p.goto(cfg.impl, { timeout: 15000 });
  await p.waitForTimeout(2000);
  await p.screenshot({ path: `${OUT}/loop-${iter}.jpg`, quality: 25 });
  const dom = await p.evaluate(() => document.querySelectorAll('*').length);
  const viteErr = await p.evaluate(() => !!document.querySelector('.vite-error-overlay'));
  // 基页快照：state-diff 用它排除「gold hover 重挂载但 impl 基页已有」的伪缺失
  const base = await p.evaluate(() => {
    const out = [];
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
      out.push({ tag: el.tagName.toLowerCase(), text: ownText.slice(0, 200), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) });
    });
    return out;
  });
  writeFileSync(`${OUT}/latest/base.json`, JSON.stringify({ rows: base }));
  await b.close();  console.log(` DOM=${dom} Err=${errs} Vite=${viteErr}`);
} catch (e) {
  console.log(` Error: ${e.message.slice(0,100)}`);
}

try {
  execSync(`${cfg.typecheck} 2>&1`, { cwd: ROOT, timeout: 20000 });
  console.log(' TC: OK');
} catch { console.log(' TC: FAIL'); }

// 交互态闭环（§十三）：task.json 有 states[] 时每轮自动采集 impl 交互态 + 与 gold 比对
// 失败不致命——只记录，不阻断主探针
if ((cfg.states || []).length) {
  try {
    const cap = execSync(`node ${ROOT}/.claude/workflows/frontend-overnight/scripts/ui-restore/capture-states.mjs ${cfg.impl} ${OUT}/latest/states --task ${TASK} --wait 2500 2>&1`, { cwd: ROOT, timeout: 180000 }).toString();
    const deltas = [...cap.matchAll(/(\S+): anchor=.*delta=(\d+)/g)].map(m => `${m[1]}=${m[2]}`).join(' ');
    console.log(` States: ${deltas}`);
    const diff = execSync(`node ${ROOT}/.claude/workflows/frontend-overnight/scripts/ui-restore/state-diff.mjs --task ${TASK} 2>&1 || true`, { cwd: ROOT, timeout: 30000 }).toString();
    const total = (diff.match(/STATE-DIFF 总计 (\d+)/) || [])[1];
    console.log(` StateDiff: ${total} 项`);
  } catch (e) { console.log(` States: FAIL ${e.message.slice(0, 80)}`); }
}

console.log(`=== END ${iter} ===`);
