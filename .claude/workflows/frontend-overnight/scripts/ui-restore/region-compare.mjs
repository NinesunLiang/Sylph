#!/usr/bin/env node
// Region-split pixel comparison: full screenshot → N×M regions → per-region diff score.
// Usage: node scripts/region-compare.mjs <proto.png> <impl.png> [--cols 4] [--rows 3] [--out dir]
// Output: ranked region diff table + cropped region pairs for high-res vision inspection.
// Mechanism: 低像素整页定结构 + 高像素区域定数值。diff% 驱动修复优先级，不靠猜。
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

const args = process.argv.slice(2);
const [protoPath, implPath] = args;
const opt = (name, dflt) => { const i = args.indexOf(name); return i > -1 ? args[i + 1] : dflt; };
const COLS = +opt('--cols', 4), ROWS = +opt('--rows', 3);
const OUT = opt('--out', '.omc/ui-autopilot/home_page/measurements/regions');
mkdirSync(OUT, { recursive: true });

const a = PNG.sync.read(readFileSync(protoPath));
const b = PNG.sync.read(readFileSync(implPath));
// normalize: crop both to common size (top-left aligned)
const W = Math.min(a.width, b.width), H = Math.min(a.height, b.height);
console.log(`proto ${a.width}x${a.height}  impl ${b.width}x${b.height}  compare ${W}x${H}  grid ${COLS}x${ROWS}`);

const cw = Math.floor(W / COLS), ch = Math.floor(H / ROWS);
const results = [];

for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    const x0 = c * cw, y0 = r * ch;
    const cropA = new PNG({ width: cw, height: ch });
    const cropB = new PNG({ width: cw, height: ch });
    PNG.bitblt(a, cropA, x0, y0, cw, ch, 0, 0);
    PNG.bitblt(b, cropB, x0, y0, cw, ch, 0, 0);
    const diffPx = pixelmatch(cropA.data, cropB.data, null, cw, ch, { threshold: 0.15 });
    const pct = +(100 * diffPx / (cw * ch)).toFixed(2);
    results.push({ region: `R${r + 1}C${c + 1}`, x: x0, y: y0, w: cw, h: ch, diffPct: pct });
    if (pct > 3) {
      writeFileSync(`${OUT}/R${r + 1}C${c + 1}-proto.png`, PNG.sync.write(cropA));
      writeFileSync(`${OUT}/R${r + 1}C${c + 1}-impl.png`, PNG.sync.write(cropB));
    }
  }
}

results.sort((p, q) => q.diffPct - p.diffPct);
console.log('\n== REGION DIFF RANK (>3% saved as crop pairs) ==');
results.forEach(r => console.log(` ${r.region}  ${String(r.diffPct).padStart(6)}%   (${r.x},${r.y} ${r.w}x${r.h})`));
writeFileSync(`${OUT}/report.json`, JSON.stringify({ grid: [COLS, ROWS], compareSize: [W, H], regions: results }, null, 1));
console.log(`\nreport → ${OUT}/report.json`);
