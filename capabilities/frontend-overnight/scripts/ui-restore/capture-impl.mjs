#!/usr/bin/env node
// Capture a page screenshot (viewport via flags; gold-refresh 从 task.json 传入).
// Usage: node scripts/ui-restore/capture-impl.mjs <url> <out.png> [--wait ms] [--dismiss-modal] [--vw N] [--vh N] [--dsf N]
import { chromium } from 'playwright';
const args = process.argv.slice(2);
const [url, out] = args;
const opt = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const WAIT = +opt('--wait', 2500);
const VW = +opt('--vw', 1510), VH = +opt('--vh', 860), DSF = +opt('--dsf', 2);
const DISMISS = args.includes('--dismiss-modal');

const b = await chromium.launch({ headless: true });
const p = await b.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: DSF });
await p.goto(url || 'http://localhost:9001/', { timeout: 90000, waitUntil: 'domcontentloaded' });
await p.waitForTimeout(WAIT);
if (DISMISS) {
  for (const label of ['确 定', '确定', '×']) {
    try { await p.click(`button:has-text("${label}")`, { timeout: 3000 }); break; } catch {}
  }
  await p.waitForTimeout(800);
}
await p.screenshot({ path: out });
console.log('saved', out);
await b.close();
