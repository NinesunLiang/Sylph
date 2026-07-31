#!/usr/bin/env node
// EXTRACT-MODEL-ASSETS — 模型下拉的品牌资产真值采集（logo svg / flame 图标）
// 用法: node scripts/ui-restore/extract-model-assets.mjs <proto-url> <outDir> --task home_page [--wait ms]
// 原理: 模型 logo 的 svg path 不在 computed style 里，delta.json 只有几何——必须直接抓 DOM innerHTML
// 产出: <outDir>/<slug>.svg（去重后的品牌 logo）+ flame.* + models-assets.json（模型名→资产映射）
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { createHash } from 'crypto';
import { loadTask } from './task-config.mjs';

const [url, outDir, ...flags] = process.argv.slice(2);
const opt = (n, d) => { const i = flags.indexOf(n); return i > -1 ? +flags[i + 1] : d; };
if (!url || !outDir) { console.error('usage: extract-model-assets.mjs <url> <outDir> [--wait ms]'); process.exit(1); }
const cfg = loadTask(opt('--task', 0) || 'home_page');
const WAIT = opt('--wait', 40000);
mkdirSync(outDir, { recursive: true });

const b = await chromium.launch({ headless: true });
const page = await b.newPage({ viewport: { width: cfg.vw, height: cfg.vh } });
await page.goto(url, { timeout: 90000, waitUntil: 'domcontentloaded' });
await page.waitForTimeout(WAIT);
for (const label of ['确 定', '确定', '×']) {
  try { await page.click(`button:has-text("${label}")`, { timeout: 3000 }); break; } catch {}
}
await page.waitForTimeout(800);
// 打开模型下拉（输入区 pill = 同名文本中 y 最大者）
const pill = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('body *')].map(el => {
    const t = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    const r = el.getBoundingClientRect();
    return { t, y: r.y, x: r.x + r.width / 2, cy: r.y + r.height / 2 };
  }).filter(o => o.t === 'GPT-5.6 Luna');
  const hit = rows.sort((a, z) => z.y - a.y)[0];
  return hit ? { x: hit.x, y: hit.cy } : null;
});
if (!pill) { console.error('FATAL: 模型 pill 未找到'); process.exit(2); }
await page.mouse.click(pill.x, pill.y);
await page.waitForTimeout(1500);

// 逐行抓 logo svg innerHTML + flame img
const rows = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('li').forEach(li => {
    const nameEl = [...li.querySelectorAll('div,span')].find(el => {
      const t = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
      return t.length > 2 && el.getBoundingClientRect().height <= 24;
    });
    if (!nameEl) return;
    const name = nameEl.textContent.trim();
    const logoDiv = li.querySelector('div[style*="border-radius: 50%"], div[class*="center"]');
    const svg = li.querySelector('svg');
    const img = li.querySelector('img');
    out.push({
      name,
      logoHtml: logoDiv ? logoDiv.innerHTML.slice(0, 2000) : (svg ? svg.outerHTML.slice(0, 2000) : ''),
      flameSrc: img ? (img.currentSrc || img.src) : null,
    });
  });
  return out;
});

// 去重落盘：同 svg 内容 → 同 slug 文件
const slugOf = {};
const mapping = [];
let flameFile = null;
for (const r of rows) {
  if (!r.name) continue;
  let slug = null;
  if (r.logoHtml) {
    const hash = createHash('md5').update(r.logoHtml).digest('hex').slice(0, 8);
    if (!slugOf[hash]) {
      // 从模型名猜品牌 slug
      const brand = /gemini/i.test(r.name) ? 'gemini' : /deepseek/i.test(r.name) ? 'deepseek'
        : /claude/i.test(r.name) ? 'claude' : /grok/i.test(r.name) ? 'grok'
        : /nano/i.test(r.name) ? 'nano' : 'gpt';
      slug = slugOf[hash] = brand in Object.values(slugOf) ? `${brand}-${hash.slice(0, 4)}` : brand;
      const svg = r.logoHtml.startsWith('<svg') ? r.logoHtml : r.logoHtml;
      writeFileSync(`${outDir}/${slugOf[hash]}.svg`, svg.includes('<svg') ? svg : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">${svg}</svg>`);
    }
    slug = slugOf[hash];
  }
  if (r.flameSrc && !flameFile) {
    try {
      const buf = await (await fetch(r.flameSrc)).arrayBuffer();
      const ext = r.flameSrc.includes('.webp') ? 'webp' : 'png';
      flameFile = `flame.${ext}`;
      writeFileSync(`${outDir}/${flameFile}`, Buffer.from(buf));
    } catch { /* flame 下载失败不阻断 */ }
  }
  mapping.push({ name: r.name, logo: slug ? `/assets/models/${slug}.svg` : null, flame: !!r.flameSrc });
}
writeFileSync(`${outDir}/models-assets.json`, JSON.stringify(mapping, null, 1));
console.log(`assets: ${Object.keys(slugOf).length} logos + ${flameFile || 'no-flame'} → ${outDir} (${mapping.length} models)`);
await b.close();
