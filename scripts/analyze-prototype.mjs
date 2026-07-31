// Deep analyze prototype page structure
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto('https://xsimplechat.com/', { waitUntil: 'networkidle', timeout: 30000 });

const analysis = await page.evaluate(() => {
  const body = document.body;
  if (!body) return { error: 'no body' };

  const allElements = body.querySelectorAll('*');
  const tags = {};
  const textNodes = [];
  const layout = {};

  for (const el of allElements) {
    const tag = el.tagName.toLowerCase();
    tags[tag] = (tags[tag] || 0) + 1;

    // Top-level sections
    if (el.parentElement === body) {
      const rect = el.getBoundingClientRect();
      layout[tag + '-' + (el.className || el.id || 'anon')] = {
        className: (typeof el.className === 'string' ? el.className : '').slice(0, 100) || '',
        id: el?.id || '',
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        children: el.children.length,
        text: el.textContent?.trim()?.slice(0, 80) || '',
      };
    }
  }

  // Collect all text content by element
  for (const el of allElements) {
    if (el.children.length === 0 && el.textContent?.trim()) {
      const trimmed = el.textContent.trim().slice(0, 120);
      textNodes.push(trimmed);
    }
  }

  // Collect all class names used
  const classNames = new Set();
  allElements.forEach(el => {
    const cn = typeof el.className === 'string' ? el.className : '';
    cn.split(/\s+/).filter(Boolean).forEach(c => classNames.add(c));
  });

  // Collect CSS variables used
  const cssVars = new Set();
  const style = getComputedStyle(document.documentElement);
  for (let i = 0; i < style.length; i++) {
    const prop = style[i];
    if (prop.startsWith('--')) cssVars.add(`${prop}: ${style.getPropertyValue(prop).trim()}`);
  }

  return {
    tags,
    topLevelSections: layout,
    textSamples: textNodes.slice(0, 40),
    classNames: [...classNames].slice(0, 40),
    cssVariables: [...cssVars],
  };
});

// Also get computed styles for key colors
const colors = await page.evaluate(() => {
  const body = document.body;
  if (!body) return {};
  const style = getComputedStyle(body);
  return {
    bgColor: style.backgroundColor,
    textColor: style.color,
    fontFamily: style.fontFamily,
    fontSize: style.fontSize,
  };
});

await browser.close();

console.log(JSON.stringify({ analysis, colors }, null, 2));
