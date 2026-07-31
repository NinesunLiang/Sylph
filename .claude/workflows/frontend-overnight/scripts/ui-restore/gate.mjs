#!/usr/bin/env node
// GATE — 闭环门禁。任何一轮修复后必须过闸；红灯可选自动回滚。
// 用法: node scripts/ui-restore/gate.mjs [--task home_page] [--rollback]
// 门禁: hook污染, typecheck=0, dev server 200, DOM>100, console error=0, vite overlay 无, 禁页面级滚动
// --rollback: 任一红灯 → git checkout -- <srcDirs>（撤销本轮全部改动）并 exit 1
// 通用化: URL/typecheck/源码目录全部来自 .omc/ui-autopilot/<task>/task.json（task-config.mjs 加载）
import { execSync } from 'child_process';
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { loadTask, REPO_ROOT } from './task-config.mjs';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const TASK = opt('--task', 'home_page');
const cfg = loadTask(TASK);
const ROLLBACK = args.includes('--rollback');
const OUT = cfg.outDir;
mkdirSync(OUT, { recursive: true });
process.chdir(REPO_ROOT);

const gates = {};

// 0. hook 污染检查（claim-audit G1 会在 Edit/Write 后向 SCSS 值注入 [内部自检，非行业标准]
//    → 无效 CSS，浏览器静默丢弃该声明。任一命中即红灯。清理: sed -i.bak 's/ \[内部自检，非行业标准\]//g' <file>）
try {
  const out = execSync(`grep -rn "内部自检" ${cfg.srcDirs.join(' ')} || true`, { encoding: 'utf8' }).trim();
  gates.noHookPollution = out === '';
  if (out) console.error('HOOK POLLUTION FOUND:\n' + out);
} catch { gates.noHookPollution = true; }

// 0.5 几何单位铁律（§十二）：border/padding/margin/radius/gap/width/height/inset 必须固定 px 整数，
//     禁止 rem/em（rem 随 root font-size 浮动会间接拖动几何）；font-size/line-height/letter-spacing 例外
try {
  const out = execSync(
    `grep -rnE --include='*.scss' --include='*.css' '[0-9](rem|em)(;| |\\))' ${cfg.srcDirs.join(' ')} | grep -vE 'font-size|line-height|letter-spacing|font:' || true`,
    { encoding: 'utf8' }).trim();
  gates.geometryUnitsPx = out === '';
  if (out) console.error('GEOMETRY UNIT VIOLATION（几何必须固定 px，见 §十二）:\n' + out);
} catch { gates.geometryUnitsPx = true; }

// 1. typecheck
try { execSync(cfg.typecheck, { stdio: 'pipe' }); gates.typecheck = true; }
catch { gates.typecheck = false; }

// 2. dev server + DOM + console + vite overlay
try {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  let errs = 0;
  p.on('console', m => { if (m.type() === 'error') errs++; });
  const resp = await p.goto(cfg.impl, { timeout: 15000 });
  await p.waitForTimeout(2000);
  gates.server200 = resp?.status() === 200;
  gates.domCount = await p.evaluate(() => document.querySelectorAll('*').length);
  gates.consoleErrors = errs;
  gates.viteOverlay = await p.evaluate(() => !!document.querySelector('vite-error-overlay'));
  // 布局铁律：禁止页面级滚动（html/body 出现滚动条 = 布局溢出走漏）
  gates.noPageScroll = await p.evaluate(() => {
    const d = document.documentElement;
    return d.scrollWidth <= d.clientWidth && d.scrollHeight <= d.clientHeight;
  });
  await b.close();
} catch (e) {
  gates.server200 = false; gates.domCount = 0; gates.consoleErrors = -1; gates.viteOverlay = true; gates.noPageScroll = false;
}

gates.domOk = gates.domCount > 100;
gates.pass = gates.noHookPollution && gates.geometryUnitsPx !== false && gates.typecheck && gates.server200 && gates.domOk && gates.consoleErrors === 0 && !gates.viteOverlay && gates.noPageScroll !== false;

writeFileSync(`${OUT}/gates.json`, JSON.stringify(gates, null, 1));
console.log(JSON.stringify(gates));

if (!gates.pass && ROLLBACK) {
  console.error(`GATE RED → rollback: git checkout -- ${cfg.srcDirs.join(' ')}`);
  execSync(`git checkout -- ${cfg.srcDirs.join(' ')}`);
  process.exit(1);
}
process.exit(gates.pass ? 0 : 1);
