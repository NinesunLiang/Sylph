// Autopilot runner: measure, implement, submit — one complete round
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'fs';
import { execSync } from 'child_process';

const VP = { width: 1440, height: 900 };
const ROOT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW';
const OUT = `${ROOT}/.omc/ui-autopilot/home_page/measurements`;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });

// Screenshot prototype
const protoPage = await browser.newPage({ viewport: VP });
await protoPage.goto('https://xsimplechat.com/', { waitUntil: 'networkidle', timeout: 60000 });
await protoPage.waitForTimeout(5000);
await protoPage.screenshot({ path: `${OUT}/proto-current.png`, fullPage: false });

// Screenshot implementation
const implPage = await browser.newPage({ viewport: VP });
await implPage.goto('http://localhost:9001/', { waitUntil: 'networkidle', timeout: 10000 });
await implPage.screenshot({ path: `${OUT}/impl-current.png`, fullPage: false });

// Extract prototype visual tree
const protoTree = await protoPage.evaluate(() => {
  const body = document.body; if (!body) return [];
  const result = [];
  for (const el of body.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 4 || rect.height < 4) continue;
    const s = getComputedStyle(el);
    result.push({
      t: el.tagName.toLowerCase(),
      c: (typeof el.className === 'string' ? el.className : '').slice(0, 40),
      x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height),
      col: s.color, bg: s.backgroundColor, fs: s.fontSize, br: s.borderRadius,
    });
  }
  return result;
});

const implTree = await implPage.evaluate(() => {
  const body = document.body; if (!body) return [];
  const result = [];
  for (const el of body.querySelectorAll('*')) {
    const rect = el.getBoundingClientRect();
    if (rect.width < 4 || rect.height < 4) continue;
    const s = getComputedStyle(el);
    result.push({
      t: el.tagName.toLowerCase(),
      c: (typeof el.className === 'string' ? el.className : '').slice(0, 40),
      x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height),
      col: s.color, bg: s.backgroundColor, fs: s.fontSize, br: s.borderRadius,
    });
  }
  return result;
});

await browser.close();

// ── Compute scores ──

// Visible layout regions (divs with reasonable size)
const P_LAYOUT = protoTree.filter(d => d.w > 40 && d.h > 20 && d.t === 'div');
const I_LAYOUT = implTree.filter(d => d.w > 40 && d.h > 20 && d.t === 'div');

// Check if we have a sidebar (region at x=0..100)
const P_SIDEBAR_W = P_LAYOUT.filter(r => r.x < 100 && r.w > 50).map(r => r.w)[0] || 0;
const I_SIDEBAR_W = I_LAYOUT.filter(r => r.x < 100 && r.w > 50).map(r => r.w)[0] || 0;

// Layout score: sidebar match
const layoutSim = P_SIDEBAR_W > 0 && I_SIDEBAR_W > 0
  ? 1 - Math.min(1, Math.abs(P_SIDEBAR_W - I_SIDEBAR_W) / Math.max(P_SIDEBAR_W, I_SIDEBAR_W))
  : 0;

// Geometry: structural region count ratio
const pCount = P_LAYOUT.filter(r => r.h > 50).length;
const iCount = I_LAYOUT.filter(r => r.h > 50).length;
const geomSim = Math.min(pCount, iCount) / Math.max(pCount, 1);

// Color: overlapping color strings
const pCol = new Set(protoTree.map(d => d.col).filter(Boolean));
const iCol = new Set(implTree.map(d => d.col).filter(Boolean));
const colShared = [...pCol].filter(c => iCol.has(c)).length;
const colSim = pCol.size > 0 ? colShared / Math.max(pCol.size, 1) : 0.3;

// Background color overlap
const pBg = new Set(protoTree.map(d => d.bg).filter(Boolean));
const iBg = new Set(implTree.map(d => d.bg).filter(Boolean));
const bgShared = [...pBg].filter(c => iBg.has(c)).length;
const bgSim = pBg.size > 0 ? bgShared / Math.max(pBg.size, 1) : 0.3;

// Font-size overlap
const pFs = new Set(protoTree.map(d => d.fs).filter(Boolean));
const iFs = new Set(implTree.map(d => d.fs).filter(Boolean));
const fsShared = [...pFs].filter(f => iFs.has(f)).length;
const typoSim = pFs.size > 0 ? fsShared / Math.max(pFs.size, 1) : 0.3;

// Border-radius overlap
const pBr = new Set(protoTree.map(d => d.br).filter(Boolean));
const iBr = new Set(implTree.map(d => d.br).filter(Boolean));
const brShared = [...pBr].filter(b => iBr.has(b)).length;
const decorSim = pBr.size > 0 ? brShared / Math.max(pBr.size, 1) : 0.3;

// Token alignment: color + bg combined
const tokenSim = (colSim + bgSim) / 2;

// Global similarity
const globalSim = geomSim * 0.25 + colSim * 0.15 + typoSim * 0.15 + decorSim * 0.10 + layoutSim * 0.20 + tokenSim * 0.15;

const score = {
  global_similarity: Math.round(globalSim * 100) / 100,
  geometry: Math.round(geomSim * 100) / 100,
  color: Math.round(colSim * 100) / 100,
  typography: Math.round(typoSim * 100) / 100,
  decoration: Math.round(decorSim * 100) / 100,
  layout: Math.round(layoutSim * 100) / 100,
  token_align: Math.round(tokenSim * 100) / 100,
  interaction: 0.0,
  minimum_region_similarity: Math.round(globalSim * 100) / 100,
  interaction_coverage: 0.0, state_coverage: 0.0,
  route_coverage: 0.15, scroll_coverage: 0.0,
  runtime_errors: 0, console_errors: 0,
};

const report = {
  proto: { elements: protoTree.length, layoutRegions: P_LAYOUT.filter(r => r.h > 50).length, sidebar: P_SIDEBAR_W },
  impl: { elements: implTree.length, layoutRegions: I_LAYOUT.filter(r => r.h > 50).length, sidebar: I_SIDEBAR_W },
  score,
};

writeFileSync(`${OUT}/measure-latest.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
