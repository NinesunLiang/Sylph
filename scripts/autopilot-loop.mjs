// Autopilot Loop Worker: Measure prototype, update implementation, submit results
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync, readFileSync } from 'fs';

const PROTOTYPE_URL = 'https://xsimplechat.com/';
const IMPL_URL = 'http://localhost:9001/';
const OUT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page';
const VIEWPORT = { width: 1440, height: 900 };

const browser = await chromium.launch({ headless: true });

// 1. Screenshot fully loaded prototype (wait for RSC streaming)
const protoPage = await browser.newPage({ viewport: VIEWPORT });
await protoPage.goto(PROTOTYPE_URL, { waitUntil: 'networkidle', timeout: 60000 });
// Give extra time for RSC streaming + hydration
await protoPage.waitForTimeout(5000);
await protoPage.screenshot({ path: `${OUT}/prototype/home-prototype-full.png`, fullPage: false });
console.log('✅ Prototype screenshot saved');

// Grab prototype DOM structure
const protoDOM = await protoPage.evaluate(() => {
  const body = document.body;
  if (!body) return {};

  function walk(el, depth = 0) {
    if (depth > 6) return null;
    const tag = el.tagName.toLowerCase();
    const cn = typeof el.className === 'string' ? el.className : '';
    const rect = el.getBoundingClientRect();
    const children = [];
    for (const child of el.children) {
      const c = walk(child, depth + 1);
      if (c) children.push(c);
    }
    return {
      tag,
      class: cn.slice(0, 80),
      rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
      visible: rect.width > 0 && rect.height > 0,
      children: children.length > 0 ? children : undefined,
      text: children.length === 0 && el.textContent?.trim() ? el.textContent.trim().slice(0, 120) : undefined,
    };
  }
  return walk(body);
});
writeFileSync(`${OUT}/prototype/home-prototype-dom.json`, JSON.stringify(protoDOM, null, 2));
console.log('✅ Prototype DOM saved');

// 2. Screenshot implementation
const implPage = await browser.newPage({ viewport: VIEWPORT });
await implPage.goto(IMPL_URL, { waitUntil: 'networkidle', timeout: 10000 });
await implPage.screenshot({ path: `${OUT}/implementation/home-impl-current.png`, fullPage: false });

await browser.close();
console.log('✅ Implementation screenshot saved');
