import { chromium } from 'playwright';
const urls = { proto: 'https://xsimplechat.com/', impl: 'http://localhost:9001/' };
const browser = await chromium.launch();
for (const [label, url] of Object.entries(urls)) {
  const page = await browser.newPage({ viewport: { width: 1510, height: 860 } });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
  await page.waitForSelector('text=GPT-5.6 Luna', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const r = await page.evaluate(() => {
    const rect = el => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const cands = [...document.querySelectorAll('body *')].filter(e => (e.textContent || '').trim() === 'GPT-5.6 Luna' && e.getBoundingClientRect().y > 600);
    cands.sort((a, b) => a.getBoundingClientRect().width - b.getBoundingClientRect().width);
    const pill = cands[0];
    if (!pill) return null;
    // 可点击宿主 = 含 pill 且带 img 的最近祖先（或自身）
    let host = pill;
    for (let p = pill; p && p !== document.body; p = p.parentElement) { host = p; if (p.querySelector('img') && p.getBoundingClientRect().height <= 40) break; }
    // 输入区容器：从 host 向上找 h>150 的第一层
    let area = host; for (let p = host; p && p !== document.body; p = p.parentElement) { if (p.getBoundingClientRect().height > 150) { area = p; break; } }
    return { pill: rect(pill), host: { tag: host.tagName, cls: (host.className + '').slice(0, 40), ...rect(host) }, area: { tag: area.tagName, cls: (area.className + '').slice(0, 40), ...rect(area) } };
  });
  console.log(`--- ${label} ---`, JSON.stringify(r));
  if (r) {
    await page.mouse.click(r.host.x + r.host.w / 2, r.host.y + r.host.h / 2);
    await page.waitForTimeout(1200);
    const f = await page.evaluate(() => {
      const cands = [...document.querySelectorAll('body *')].filter(e => (e.textContent || '').trim() === 'GPT-5.6 Luna' && e.children.length === 0 && e.getBoundingClientRect().y < 400);
      cands.sort((a, b) => a.getBoundingClientRect().width - b.getBoundingClientRect().width);
      const el = cands[0];
      if (!el) return null;
      const cs = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return { font: cs.fontFamily.slice(0, 100), ls: cs.letterSpacing, fs: cs.fontSize, fw: cs.fontWeight, w: +b.width.toFixed(1) };
    });
    console.log(`${label} model-name:`, JSON.stringify(f));
  }
  await page.close();
}
await browser.close();
