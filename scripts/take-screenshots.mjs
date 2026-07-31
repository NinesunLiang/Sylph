// Take screenshots for orchestrator measurement
import { chromium } from 'playwright';

const VIEWPORT = { width: 1440, height: 900 };
const OUT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW/.omc/ui-autopilot/home_page/prototype';

import { mkdirSync, writeFileSync } from 'fs';

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });

// Screenshot the prototype (xsimplechat.com)
const protoPage = await browser.newPage({ viewport: VIEWPORT });
await protoPage.goto('https://xsimplechat.com/', { waitUntil: 'networkidle', timeout: 30000 });
await protoPage.screenshot({ path: `${OUT}/home-prototype.png`, fullPage: false });

// Extract DOM info
const protoDOM = await protoPage.evaluate(() => {
  const body = document.body;
  return {
    childElementCount: body ? body.children.length : 0,
    textContent: body ? body.textContent?.substring(0, 200) : '',
    title: document.title,
  };
});
writeFileSync(`${OUT}/home-prototype-dom.json`, JSON.stringify(protoDOM, null, 2));

// Screenshot the implementation (localhost:9001)
const implPage = await browser.newPage({ viewport: VIEWPORT });
await implPage.goto('http://localhost:9001/', { waitUntil: 'networkidle', timeout: 10000 });
await implPage.screenshot({ path: `${OUT}/home-implementation.png`, fullPage: false });

const implDOM = await implPage.evaluate(() => {
  const body = document.body;
  return {
    childElementCount: body ? body.children.length : 0,
    textContent: body?.textContent?.substring(0, 200) || '',
    title: document.title,
  };
});
writeFileSync(`${OUT}/home-implementation-dom.json`, JSON.stringify(implDOM, null, 2));

await browser.close();

const result = { prototype: protoDOM, implementation: implDOM };
console.log(JSON.stringify(result));
