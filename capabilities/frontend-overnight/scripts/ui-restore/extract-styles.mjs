#!/usr/bin/env node
// Extract computed styles from a live page → JSON ground-truth table.
// Usage: node scripts/ui-restore/extract-styles.mjs <url> <out.json> [--dismiss-modal] [--vw N] [--vh N] [--wait ms]
// Replaces vision-model CSS guessing with real DOM computed values.
import { chromium } from 'playwright';
import { writeFileSync } from 'fs';

const [url, out, ...flags] = process.argv.slice(2);
if (!url || !out) { console.error('usage: extract-styles.mjs <url> <out.json> [--dismiss-modal] [--vw N] [--vh N] [--wait ms]'); process.exit(1); }
const fopt = (n, d) => { const i = flags.indexOf(n); return i > -1 ? +flags[i + 1] : d; };
const VW = fopt('--vw', 1510), VH = fopt('--vh', 860);
const WAIT = fopt('--wait', 3000); // proto RSC 慢流式 → gold-refresh 传 40000
const clickText = (() => { const i = flags.indexOf('--click-text'); return i > -1 ? flags[i + 1] : ''; })();

const b = await chromium.launch({ headless: true });
const p = await b.newPage({ viewport: { width: VW, height: VH } });
await p.goto(url, { timeout: 90000, waitUntil: 'domcontentloaded' });

if (flags.includes('--dismiss-modal')) {
  await p.waitForTimeout(Math.min(WAIT, 12000));
  const closed = await p.evaluate(() => {
    const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
    const button = [...document.querySelectorAll('button[aria-label="Close"], .ant-modal-close, button')].find(el => visible(el) && (el.getAttribute('aria-label') === 'Close' || el.classList.contains('ant-modal-close') || /确\s*定|确定|×/.test(el.textContent || '')));
    if (!button) return false;
    button.click();
    return true;
  });
  if (!closed) console.warn('dismiss-modal: visible close control not found');
  await p.waitForFunction(() => ![...document.querySelectorAll('.ant-modal-mask, [role="dialog"]')].some(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; }), null, { timeout: 10000 }).catch(() => {});
  await p.waitForTimeout(Math.max(800, WAIT - 12000));
} else {
  await p.waitForTimeout(WAIT);
}
if (clickText) {
  await p.getByText(clickText, { exact: true }).last().click({ timeout: 10000 });
  await p.waitForTimeout(1500);
}

const rows = await p.evaluate(() => {
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const ownText = [...el.childNodes]
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim()).join(' ').trim();
    out.push({
      tag: el.tagName.toLowerCase(),
      text: ownText.slice(0, 40),
      cls: String(el.className?.baseVal ?? el.className ?? '').slice(0, 80),
      src: el.tagName === 'IMG' ? (el.currentSrc || el.src || '') : '',
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      fs: cs.fontSize, fw: cs.fontWeight, lh: cs.lineHeight,
      color: cs.color, bg: cs.backgroundColor,
      radius: cs.borderRadius, pad: cs.padding, gap: cs.gap,
      border: cs.borderWidth + ' ' + cs.borderStyle + ' ' + cs.borderColor,
      font: cs.fontFamily.slice(0, 60),
    });
  });
  return out;
});

writeFileSync(out, JSON.stringify({ url, viewport: [VW, VH], count: rows.length, rows }, null, 1));
console.log(`extracted ${rows.length} elements → ${out}`);
await b.close();
