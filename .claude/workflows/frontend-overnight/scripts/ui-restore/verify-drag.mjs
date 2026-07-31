#!/usr/bin/env node
// Verify DragHandle: drag resizes panel, mouseup stops dragging (no stuck state)
import { chromium } from 'playwright';

const b = await chromium.launch({ headless: true });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
await p.goto('http://localhost:9001/', { timeout: 15000 });
await p.waitForTimeout(2000);

const panelW = () => p.evaluate(() => {
  const els = document.querySelectorAll('aside');
  return Array.from(els).map(e => Math.round(e.getBoundingClientRect().width));
});

const before = await panelW();

// find drag handles (4px wide col-resize divs)
const handles = await p.$$('div[style*="col-resize"], div[class*="drag_handle"]');
console.log('handles found:', handles.length);
if (handles.length === 0) {
  // fallback: locate by cursor style via evaluate
  const pos = await p.evaluate(() => {
    const all = document.querySelectorAll('div');
    for (const d of all) {
      if (getComputedStyle(d).cursor === 'col-resize') {
        const r = d.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      }
    }
    return null;
  });
  if (!pos) { console.log('FAIL: no drag handle found'); process.exit(1); }
  var hx = pos.x, hy = pos.y;
} else {
  const box = await handles[0].boundingBox();
  var hx = box.x + box.width / 2, hy = box.y + box.height / 2;
}

// 1. press on divider and move +80px
await p.mouse.move(hx, hy);
await p.mouse.down();
await p.mouse.move(hx + 80, hy, { steps: 10 });
const during = await panelW();
await p.mouse.up();
const after = await panelW();

// 2. move mouse WITHOUT pressing — width must NOT change (stuck-drag check)
await p.mouse.move(hx + 200, hy, { steps: 5 });
const noPress = await panelW();

console.log('before   :', JSON.stringify(before));
console.log('during   :', JSON.stringify(during));
console.log('after up :', JSON.stringify(after));
console.log('no-press :', JSON.stringify(noPress));

const dragWorks = JSON.stringify(during) !== JSON.stringify(before);
const noStuck = JSON.stringify(noPress) === JSON.stringify(after);
console.log(dragWorks ? 'PASS: drag resizes panel' : 'FAIL: drag did not resize');
console.log(noStuck ? 'PASS: no stuck drag after mouseup' : 'FAIL: stuck in drag state');
await b.close();
process.exit(dragWorks && noStuck ? 0 : 1);
