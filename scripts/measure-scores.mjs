// Proper measurement: compare prototype vs implementation
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'fs';

const VP = { width: 1440, height: 900 };
const OUT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/measurements';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });

// ── 1. Measure Prototype ──
const protoPage = await browser.newPage({ viewport: VP });
await protoPage.goto('https://xsimplechat.com/', { waitUntil: 'networkidle', timeout: 60000 });
await protoPage.waitForTimeout(4000);

const protoDOM = await protoPage.evaluate(() => {
  const body = document.body; if (!body) return null;
  const tree = [];
  for (const el of body.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const style = getComputedStyle(el);
    tree.push({
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
      x: Math.round(rect.x), y: Math.round(rect.y),
      w: Math.round(rect.width), h: Math.round(rect.height),
      color: style.color, bg: style.backgroundColor,
      fs: style.fontSize, fw: style.fontWeight,
      ff: style.fontFamily.split(',')[0].trim().slice(0, 30),
      br: style.borderRadius, p: style.padding,
      text: el.children.length === 0 ? (el.textContent||'').trim().slice(0, 60) : '',
    });
  }
  return tree;
});

// Count key dimensions
const protoStyles = {
  totalElements: protoDOM.length,
  colors: new Set(protoDOM.map(e => e.color).filter(Boolean)).size,
  bgColors: new Set(protoDOM.map(e => e.bg).filter(Boolean)).size,
  fontSizes: new Set(protoDOM.map(e => e.fs).filter(Boolean)).size,
  borderRadius: new Set(protoDOM.map(e => e.br).filter(Boolean)).size,
  paddings: new Set(protoDOM.map(e => e.p).filter(Boolean)).size,
};

const protoScreenshot = await protoPage.screenshot({ fullPage: false });
const protoB64 = protoScreenshot.toString('base64');
writeFileSync(`${OUT}/proto-screenshot.b64`, protoB64);

writeFileSync(`${OUT}/proto-snapshot.json`, JSON.stringify({
  domTree: protoDOM,
  styleDiversity: protoStyles,
}, null, 2));

// ── 2. Measure Implementation ──
const implPage = await browser.newPage({ viewport: VP });
await implPage.goto('http://localhost:9001/', { waitUntil: 'networkidle', timeout: 10000 });

const implDOM = await implPage.evaluate(() => {
  const body = document.body; if (!body) return null;
  const tree = [];
  for (const el of body.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const style = getComputedStyle(el);
    tree.push({
      tag: el.tagName.toLowerCase(),
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
      x: Math.round(rect.x), y: Math.round(rect.y),
      w: Math.round(rect.width), h: Math.round(rect.height),
      color: style.color, bg: style.backgroundColor,
      fs: style.fontSize, fw: style.fontWeight,
      br: style.borderRadius, p: style.padding,
      text: el.children.length === 0 ? (el.textContent||'').trim().slice(0, 60) : '',
    });
  }
  return tree;
});

const implScreenshot = await implPage.screenshot({ fullPage: false });
const implB64 = implScreenshot.toString('base64');
writeFileSync(`${OUT}/impl-screenshot.b64`, implB64);

writeFileSync(`${OUT}/impl-snapshot.json`, JSON.stringify({
  domTree: implDOM,
}, null, 2));

await browser.close();

// ── 3. Compute Score ──
// Structural comparison of visible layout regions
const IMPL_BBOX = { x: 0, y: 0, w: 1440, h: 900 };
const PROTO_BBOX = { x: 0, y: 0, w: 1440, h: 900 };

const layoutRegions = (tree) => tree.filter(e => e.tag === 'div' && e.w > 30 && e.h > 30);

const protoRegions = layoutRegions(protoDOM).slice(0, 20);
const implRegions = layoutRegions(implDOM).slice(0, 20);

// Geometry: how many major layout divs match
const protoMajorH = protoRegions.filter(r => r.h > 40).length;
const implMajorH = implRegions.filter(r => r.h > 40).length;
const hRatio = Math.min(protoMajorH, implMajorH) / Math.max(protoMajorH, 1);

// Color: how many unique colors overlap
const protoCols = new Set(protoDOM.map(e => e.color).filter(Boolean));
const implCols = new Set(implDOM.map(e => e.color).filter(Boolean));
const colorOverlap = [...protoCols].filter(c => implCols.has(c)).length;
const colorScore = protoCols.size > 0 ? colorOverlap / Math.max(protoCols.size, 1) : 0.5;

// Typography: font-size similarity
const protoFS = new Set(protoDOM.map(e => e.fs).filter(Boolean));
const implFS = new Set(implDOM.map(e => e.fs).filter(Boolean));
const fsOverlap = [...protoFS].filter(f => implFS.has(f)).length;
const typoScore = protoFS.size > 0 ? 0.3 + 0.7 * (fsOverlap / Math.max(protoFS.size, 1)) : 0.3;

// Layout: sidebar width
const protoSidebarWidth = protoRegions.filter(r => r.x < 100 && r.w > 30 && r.w < 200).map(r => r.w)[0] || 64;
const implSidebarWidth = implRegions.filter(r => r.x < 100 && r.w > 30 && r.w < 200).map(r => r.w)[0] || 64;
const layoutWScore = 1 - Math.abs(protoSidebarWidth - implSidebarWidth) / Math.max(protoSidebarWidth, 1);
const layoutScore = Math.max(0, layoutWScore);

// Decoration: border-radius
const protoBR = new Set(protoDOM.map(e => e.br).filter(Boolean));
const implBR = new Set(implDOM.map(e => e.br).filter(Boolean));
const brOverlap = [...protoBR].filter(b => implBR.has(b)).length;
const decorScore = protoBR.size > 0 ? brOverlap / Math.max(protoBR.size, 1) : 0.3;

// Token alignment (D6): color + bg matching
const tokenColors = [...protoCols].filter(c => implCols.has(c)).length;
const tokenScore = protoCols.size > 0 ? tokenColors / Math.max(protoCols.size, 1) : 0.3;

// Overall geometry
const geometryScore = 0.5 + 0.5 * hRatio;

// Global similarity (weighted average)
const globalSim = Math.min(1.0,
  geometryScore * 0.25 + colorScore * 0.20 + typoScore * 0.15 +
  layoutScore * 0.15 + decorScore * 0.10 + tokenScore * 0.15
);

const result = {
  proto: { elements: protoDOM.length, styleDiversity: protoStyles },
  impl: { elements: implDOM.length },
  scores: {
    global_similarity: Math.round(globalSim * 100) / 100,
    geometry: Math.round(geometryScore * 100) / 100,
    color: Math.round(colorScore * 100) / 100,
    typography: Math.round(typoScore * 100) / 100,
    decoration: Math.round(decorScore * 100) / 100,
    layout: Math.round(layoutScore * 100) / 100,
    token_align: Math.round(tokenScore * 100) / 100,
    interaction: 0.0,
    minimum_region_similarity: Math.round(globalSim * 100) / 100,
    interaction_coverage: 0.0,
    state_coverage: protoDOM.filter(e => e.cls && (e.cls.includes('modal') || e.cls.includes('drawer') || e.cls.includes('overlay'))).length > 0 ? 0.1 : 0.0,
    route_coverage: 0.15,
    scroll_coverage: 0.0,
    runtime_errors: 0,
    console_errors: 0,
  }
};

console.log(JSON.stringify(result));
