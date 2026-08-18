#!/usr/bin/env node
// SHOT-PAGE — 通用页面截图（UI 还原视觉验收闭环的标准截图入口）
// 用法: node .claude/workflows/frontend-overnight/scripts/ui-restore/shot-page.mjs <url> <out.png> [--viewport 1440x900] [--wait 800] [--console]
// 说明:
//   - 等待 networkidle + 自定义延时（让 mock 数据/弹窗动画稳定后再拍）
//   - --console 时把页面 console.error / pageerror 打到 stdout（C6 无 console error 检查）
//   - 输出路径相对仓库根解析
// 沉淀来源: 2026-08-18 xsimplechat chat-inbox 还原（.omc/scripts/shot-chat.mjs 通用化）
import { chromium } from 'playwright';
import path from 'node:path';

const [url, out] = process.argv.slice(2);
if (!url || !out) {
  console.error('usage: shot-page.mjs <url> <out.png> [--viewport WxH] [--wait ms] [--console]');
  process.exit(2);
}
const opt = (n, d) => { const i = process.argv.indexOf(n); return i > -1 ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes(n);
const [vw, vh] = opt('--viewport', '1440x900').split('x').map(Number);
const waitMs = Number(opt('--wait', '800'));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: vw, height: vh } });
if (has('--console')) {
  page.on('console', (msg) => { if (msg.type() === 'error') console.log('[console.error]', msg.text()); });
  page.on('pageerror', (err) => console.log('[pageerror]', err.message));
}
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(waitMs);
const outAbs = path.resolve(out);
await page.screenshot({ path: outAbs });
console.log('saved:', outAbs);
await browser.close();
