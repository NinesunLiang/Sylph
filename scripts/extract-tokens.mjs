// Extract CSS computed style observations from xsimplechat.com using Playwright
import { chromium } from 'playwright';

const URL = 'https://xsimplechat.com/';

const PROPERTIES = [
  'color', 'background-color', 'border-color',
  'font-size', 'font-weight', 'line-height',
  'border-radius', 'gap', 'padding',
  'width', 'height', 'box-shadow',
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });

// Extract computed style values
const observations = await page.evaluate((props) => {
  const results = [];
  const body = document.querySelector('body');
  if (!body) return results;

  const elements = body.querySelectorAll('*');
  for (const el of elements) {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);

    if (rect.width < 2 || rect.height < 2 ||
        style.display === 'none' || style.visibility === 'hidden') {
      continue;
    }

    const area = rect.width * rect.height;
    for (const prop of props) {
      const value = style.getPropertyValue(prop).trim();
      if (!value || value === 'none' || value === 'normal' ||
          value === 'auto' || value === 'transparent' ||
          value === 'rgba(0, 0, 0, 0)') {
        continue;
      }
      results.push({ property: prop, value, area });
    }
  }
  return results;
}, PROPERTIES);

// Extract CSS custom properties
const customProperties = await page.evaluate(() => {
  const result = {};
  const root = getComputedStyle(document.documentElement);
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (!(rule instanceof CSSStyleRule)) continue;
        for (const name of rule.style) {
          if (name.startsWith('--')) {
            const resolved = root.getPropertyValue(name).trim();
            if (resolved) result[name] = resolved;
          }
        }
      }
    } catch (e) {
      // Cross-origin stylesheet: skip
    }
  }
  return result;
});

await browser.close();

const output = {
  source_url: URL,
  observations_count: observations.length,
  observations: observations.slice(0, 500), // Top 500
  custom_properties: customProperties,
};

process.stdout.write(JSON.stringify(output));
