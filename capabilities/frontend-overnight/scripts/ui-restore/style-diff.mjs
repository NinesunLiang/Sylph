#!/usr/bin/env node
// Diff two computed-style tables (prototype vs implementation) → ranked numeric diff.
// Usage: node scripts/style-diff.mjs <proto.json> <impl.json> [--top 30]
// Matching: leaf elements keyed by tag|text; geometry tolerance 2px.
import { readFileSync } from 'fs';

const [protoPath, implPath, ...rest] = process.argv.slice(2);
const topN = rest[rest.indexOf('--top') + 1] ? +rest[rest.indexOf('--top') + 1] : 30;
const proto = JSON.parse(readFileSync(protoPath, 'utf8'));
const impl = JSON.parse(readFileSync(implPath, 'utf8'));

const key = r => `${r.tag}|${r.text}`.toLowerCase();
const group = rows => {
  const m = new Map();
  rows.forEach(r => { const k = key(r); if (!m.has(k)) m.set(k, []); m.get(k).push(r); });
  return m;
};
const P = group(proto.rows.filter(r => r.text));
const I = group(impl.rows.filter(r => r.text));

const px = v => parseFloat(v) || 0;
const rgbDist = (a, b) => {
  const pa = (a.match(/[\d.]+/g) || []).map(Number), pb = (b.match(/[\d.]+/g) || []).map(Number);
  if (pa.length < 3 || pb.length < 3) return 0;
  return Math.round(Math.hypot(pa[0]-pb[0], pa[1]-pb[1], pa[2]-pb[2]));
};

const diffs = [];
let matched = 0;
for (const [k, pRows] of P) {
  const iRows = I.get(k);
  if (!iRows) { diffs.push({ kind: 'MISSING_IN_IMPL', text: k.slice(0, 50), proto: pRows[0].cls.slice(0, 40) }); continue; }
  matched++;
  const pr = pRows[0], ir = iRows[0];
  const d = { text: k.slice(0, 50), items: [] };
  if (Math.abs(px(pr.fs) - px(ir.fs)) > 0.5) d.items.push(`font-size ${ir.fs} → ${pr.fs}`);
  if (pr.fw !== ir.fw) d.items.push(`font-weight ${ir.fw} → ${pr.fw}`);
  const cd = rgbDist(pr.color, ir.color);
  if (cd > 24) d.items.push(`color ${ir.color} → ${pr.color}`);
  const bd = rgbDist(pr.bg, ir.bg);
  if (bd > 24 && !pr.bg.includes('0, 0, 0, 0')) d.items.push(`background ${ir.bg} → ${pr.bg}`);
  if (Math.abs(pr.w - ir.w) > 4) d.items.push(`width ${ir.w}px → ${pr.w}px`);
  if (Math.abs(pr.h - ir.h) > 4) d.items.push(`height ${ir.h}px → ${pr.h}px`);
  if (pr.radius !== ir.radius) d.items.push(`radius ${ir.radius} → ${pr.radius}`);
  if (pr.pad !== ir.pad) d.items.push(`padding ${ir.pad} → ${pr.pad}`);
  if (d.items.length) { d.score = d.items.length; d.implCls = ir.cls.slice(0, 60); diffs.push(d); }
}

const missing = diffs.filter(d => d.kind === 'MISSING_IN_IMPL');
const styled = diffs.filter(d => !d.kind).sort((a, b) => b.score - a.score).slice(0, topN);

console.log(`proto text-elements: ${P.size}  matched in impl: ${matched}  missing: ${missing.length}`);
console.log(`\n== TOP STYLE DIFFS (impl value → proto ground truth) ==`);
styled.forEach(d => {
  console.log(`\n[${d.text}]  impl-cls: ${d.implCls}`);
  d.items.forEach(i => console.log(`   ${i}`));
});
if (missing.length) {
  console.log(`\n== MISSING IN IMPL (${missing.length}) ==`);
  missing.slice(0, 10).forEach(m => console.log(`   ${m.text}`));
}
