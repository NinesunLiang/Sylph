import { chromium } from 'playwright';

// 一次性侦查脚本（已通用化）: 探测目标页中指定文本元素的位置与样式。
// 用法: node probe-states.mjs <url> [--text "要定位的文本"] [--viewportW 1510 --viewportH 860]
// 默认: url=进程首个参数; text=首个非 flag 参数后的 --text 值; 未指定则用 'GPT-5.6 Luna' 的旧示例。
// 目的: 定位页面某文本所在宿主/输入区, 供 task-config zones 设计参考。零引用、按需调用。

const args = process.argv.slice(2);
const urlArg = args.find(a => !a.startsWith('--'));
const textIdx = args.indexOf('--text');
const text = textIdx >= 0 ? args[textIdx + 1] : null;
const wIdx = args.indexOf('--viewportW');
const hIdx = args.indexOf('--viewportH');
const urls = { target: urlArg || 'http://localhost:9001/' };
const targetText = text || 'GPT-5.6 Luna'; // 旧示例保留, 建议显式传 --text

const browser = await chromium.launch();
for (const [label, url] of Object.entries(urls)) {
  const page = await browser.newPage({
    viewport: {
      width: wIdx >= 0 ? +args[wIdx + 1] : 1510,
      height: hIdx >= 0 ? +args[hIdx + 1] : 860,
    },
  });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
  await page.waitForSelector(`text=${targetText}`, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const r = await page.evaluate((sel) => {
    const rect = el => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const cands = [...document.querySelectorAll('body *')].filter(e => (e.textContent || '').trim() === sel && e.getBoundingClientRect().y > 600);
    cands.sort((a, b) => a.getBoundingClientRect().width - b.getBoundingClientRect().width);
    const pill = cands[0];
    if (!pill) return null;
    // 可点击宿主 = 含 pill 且带 img 的最近祖先（或自身）
    let host = pill;
    for (let p = pill; p && p !== document.body; p = p.parentElement) { host = p; if (p.querySelector('img') && p.getBoundingClientRect().height <= 40) break; }
    // 输入区容器：从 host 向上找 h>150 的第一层
    let area = host; for (let p = host; p && p !== document.body; p = p.parentElement) { if (p.getBoundingClientRect().height > 150) { area = p; break; } }
    return { pill: rect(pill), host: { tag: host.tagName, cls: (host.className + '').slice(0, 40), ...rect(host) }, area: { tag: area.tagName, cls: (area.className + '').slice(0, 40), ...rect(area) } };
  }, targetText);
  console.log(`--- ${label} ---`, JSON.stringify(r));
  if (r) {
    await page.mouse.click(r.host.x + r.host.w / 2, r.host.y + r.host.h / 2);
    await page.waitForTimeout(1200);
    const f = await page.evaluate((sel) => {
      const cands = [...document.querySelectorAll('body *')].filter(e => (e.textContent || '').trim() === sel && e.children.length === 0 && e.getBoundingClientRect().y < 400);
      cands.sort((a, b) => a.getBoundingClientRect().width - b.getBoundingClientRect().width);
      const el = cands[0];
      if (!el) return null;
      const cs = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return { font: cs.fontFamily.slice(0, 100), ls: cs.letterSpacing, fs: cs.fontSize, fw: cs.fontWeight, w: +b.width.toFixed(1) };
    }, targetText);
    console.log(`${label} text-style:`, JSON.stringify(f));
  }
  await page.close();
}
await browser.close();
