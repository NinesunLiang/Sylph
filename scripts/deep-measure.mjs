// Deep measurement: wait for full RSC streaming then measure
import { chromium } from 'playwright';

const VP = { width: 1440, height: 900 };
const OUT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/measurements';
import { mkdirSync, writeFileSync } from 'fs';
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: VP });

// Monitor console for RSC streaming to complete
const rscComplete = new Promise(resolve => {
  page.on('console', msg => {
    if (msg.text().includes('self.__next_f')) resolve(true);
  });
  // Also look for DOM changes
  setTimeout(() => resolve(true), 15000);
});

await page.goto('https://xsimplechat.com/', { waitUntil: 'domcontentloaded', timeout: 30000 });
await rscComplete;
await page.waitForTimeout(3000);

// After wait, check if we see actual UI elements
const uiState = await page.evaluate(() => {
  const body = document.body;
  if (!body) return { loaded: false };

  const all = body.querySelectorAll('*');
  const visible = [];
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width > 10 && r.height > 10) {
      const s = getComputedStyle(el);
      if (s.display !== 'none' && s.visibility !== 'hidden') {
        visible.push({
          tag: el.tagName.toLowerCase(),
          cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
          x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
        });
      }
    }
  }
  return { loaded: true, totalElements: all.length, visibleElements: visible.length, visible };
});

// Take screenshot after full load
await page.screenshot({ path: `${OUT}/proto-full-loaded.png`, fullPage: false });

writeFileSync(`${OUT}/proto-ui-state.json`, JSON.stringify(uiState, null, 2));
await browser.close();

console.log(JSON.stringify({
  totalElements: uiState.totalElements,
  visibleElements: uiState.visibleElements,
  elementSummary: uiState.visible.slice(0, 30).map(e => `${e.tag}.${e.cls.slice(0,30)} [${e.w}×${e.h} @${e.x},${e.y}]`),
}, null, 2));
