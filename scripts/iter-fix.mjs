// Iteration fixer: measure → compare → patch → loop
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { execSync } from 'child_process';

const ROOT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW';
const OUT = `${ROOT}/.omc/ui-autopilot/home_page/measurements`;

let iter = 1;
try { iter = parseInt(readFileSync(`${OUT}/iter.txt`, 'utf8')) + 1; } catch {}
writeFileSync(`${OUT}/iter.txt`, String(iter));

console.log(`\n=== ITERATION ${iter} ===`);

// ── 1. Screenshot prototype ──
const b = await chromium.launch({ headless: true });
const pp = await b.newPage({ viewport: { width: 1440, height: 900 } });
try { await pp.goto('https://xsimplechat.com/', { timeout: 15000 }); } catch {}
await pp.waitForTimeout(12000);

// Force-close modal by clicking overlay
try { await pp.click('.ant-modal-wrap, [class*="modal-wrap"], .ant-modal-mask', { timeout: 3000 }); } catch {}
await pp.waitForTimeout(1000);
// Try escape key
await pp.keyboard.press('Escape');
await pp.waitForTimeout(500);

await pp.screenshot({ path: `${OUT}/p-${iter}.png` });

// ── 2. Screenshot implementation ──
const ip = await b.newPage({ viewport: { width: 1440, height: 900 } });
await ip.goto('http://localhost:9001/', { timeout: 10000 });
await ip.waitForTimeout(2000);
await ip.screenshot({ path: `${OUT}/i-${iter}.png` });
const implEls = await ip.evaluate(() => document.body?.querySelectorAll('*').length || 0);
await b.close();

// ── 3. Kimi K3 comparison ──
const png = readFileSync(`${OUT}/p-${iter}.png`).toString('base64');
const ing = readFileSync(`${OUT}/i-${iter}.png`).toString('base64');

let kimiText = '';
try {
  const resp = await fetch('https://api.moonshot.cn/anthropic/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': 'sk-Xrwon2jxfgUlOlYCM2wLVcaMlT2ZkMnOjUZtivyuaFvP5r4F', 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({
      model: 'kimi-k3',
      max_tokens: 1024,
      messages: [{
        role: 'user',
        content: [
          { type: 'text', text: `你是一位严格的UI审查员。比较原型(第一张)与实现(第二张)。
仅输出一个数字(0-100)表示还原度评分。然后换行。然后列出最多3个最具体、最容易修复的差异。
每个差异一行，格式: "FILE|PROPERTY|CURRENT|TARGET"。
例如: "console/index.module.scss|button background-color|#0072f5|#1c1c1e"
或: "TEXT|文案"missingText|目标文案"
不要解释，不要思考过程。只输出事实。` },
          { type: 'image', source: { type: 'base64', media_type: 'image/png', data: png } },
          { type: 'image', source: { type: 'base64', media_type: 'image/png', data: ing } },
        ],
      }],
    }),
  });
  const d = await resp.json();
  kimiText = (d.content?.[0]?.text || '').split('\n').filter(l => !l.startsWith('[')).join('\n');
} catch {}
console.log('Kimi:', kimiText.slice(0, 1500));

// ── 4. Apply Kimi's suggestions (parse | format) ──
const fixes = kimiText.split('\n').filter(l => l.includes('|'));
let fixesApplied = 0;

for (const fix of fixes) {
  const parts = fix.split('|').map(s => s.trim());
  if (parts.length < 4) continue;
  const [file, prop, current, target] = parts;

  // Find the file
  let filePath = '';
  for (const p of ['src/layouts/AppLayout.module.scss', 'src/pages/console/index.module.scss', 'src/layouts/AppLayout.tsx', 'src/pages/console/index.tsx', 'src/components/AnnouncementModal/index.module.scss', 'src/styles/tokens/_colors.scss']) {
    if (p.includes(file.replace('src/', '')) || file.includes(p)) { filePath = `${ROOT}/${p}`; break; }
  }

  // Apply CSS property fix if we found the file
  if (filePath && prop !== '文案' && current && target) {
    let content = readFileSync(filePath, 'utf8');
    const escaped = current.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (content.includes(current)) {
      content = content.replace(new RegExp(escaped, 'g'), target);
      writeFileSync(filePath, content);
      fixesApplied++;
      console.log(`  ✅ ${file}: ${prop} ${current}→${target}`);
    }
  }
}

// ── 5. Typecheck ──
try {
  execSync('pnpm run typecheck 2>&1', { cwd: ROOT });
  console.log('  ✅ TypeCheck');
} catch(e) {
  console.log('  ❌ TypeCheck failed, reverting');
  // Revert: restore from git
  execSync('git checkout -- src/', { cwd: ROOT });
  fixesApplied = 0;
}

// ── 6. Report ──
const report = { iter, implEls, fixesApplied, kimiPreview: kimiText.slice(0, 300), ts: new Date().toISOString() };
writeFileSync(`${OUT}/r-${iter}.json`, JSON.stringify(report, null, 2));
console.log(`\n=== Iter ${iter}: ${implEls} DOM els, ${fixesApplied} fixes applied ===`);
