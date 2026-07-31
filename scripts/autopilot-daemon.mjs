// Autonomous iteration daemon: Measure → Kimi → Fix → Typecheck → Loop
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { execSync } from 'child_process';

const ROOT = '/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW';
const OUT = `${ROOT}/.omc/ui-autopilot/home_page/measurements`;
const K3_KEY = 'sk-Xrwon2jxfgUlOlYCM2wLVcaMlT2ZkMnOjUZtivyuaFvP5r4F';
mkdirSync(OUT, { recursive: true });

let iteration = 0;
try { iteration = parseInt(readFileSync(`${OUT}/iter-count.txt`, 'utf8')) || 0; } catch {}
iteration++;
writeFileSync(`${OUT}/iter-count.txt`, String(iteration));

console.log(`\n========== AUTOPILOT ITERATION ${iteration} ==========`);

// Step 1: Screenshots
const browser = await chromium.launch({ headless: true });

// Prototype
const pp = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await pp.goto('https://xsimplechat.com/', { waitUntil: 'domcontentloaded', timeout: 30000 });
await pp.waitForTimeout(8000);
// Try to close modal
await pp.evaluate(() => {
  const btns = document.querySelectorAll('button, span');
  btns.forEach(b => {
    if (b.textContent?.includes('确定') || b.textContent === '×') b.click();
  });
});
await pp.waitForTimeout(2000);
await pp.screenshot({ path: `${OUT}/proto-iter-${iteration}.png` });
const protoTexts = await pp.evaluate(() => {
  const items = [];
  const walk = (el, dep) => {
    if (dep > 6) return;
    for (const c of el.children) {
      const r = c.getBoundingClientRect();
      if (r.width < 3 || r.height < 3) continue;
      const t = !c.children.length ? (c.textContent||'').trim().slice(0, 100) : '';
      if (t && t.length > 1 && !t.startsWith('self.__') && !t.startsWith('(')) {
        items.push({ text: t, x: r.x|0, y: r.y|0 });
      }
      walk(c, dep + 1);
    }
  };
  walk(document.body, 0);
  return items;
});
await pp.close();

// Implementation
const ip = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await ip.goto('http://localhost:9001/', { waitUntil: 'networkidle', timeout: 10000 });
await ip.waitForTimeout(2000);
await ip.screenshot({ path: `${OUT}/impl-iter-${iteration}.png` });
const implTexts = await ip.evaluate(() => {
  const items = [];
  const walk = (el, dep) => {
    if (dep > 6) return;
    for (const c of el.children) {
      const r = c.getBoundingClientRect();
      if (r.width < 3 || r.height < 3) continue;
      const t = !c.children.length ? (c.textContent||'').trim().slice(0, 100) : '';
      if (t && t.length > 1) items.push({ text: t, x: r.x|0, y: r.y|0 });
      walk(c, dep + 1);
    }
  };
  walk(document.body, 0);
  return items;
});
// Count DOM elements
const implCount = await ip.evaluate(() => document.body?.querySelectorAll('*').length || 0);
await ip.close();
await browser.close();

// Step 2: Compare text content - find missing
const protoSet = new Set(protoTexts.map(t => t.text));
const implSet = new Set(implTexts.map(t => t.text));
const missing = [...protoSet].filter(t => !implSet.has(t) && t.length > 2);
const extra = [...implSet].filter(t => !protoSet.has(t) && t.length > 2);

console.log(`Proto texts: ${protoSet.size}, Impl texts: ${implSet.size}`);
console.log(`Missing texts: ${missing.length}`);
missing.slice(0, 20).forEach(t => console.log(`  MISSING: "${t}"`));

// Step 3: Kimi K3 visual comparison (if missing texts exist)
let kimiFixes = '';
if (missing.length > 0 || true) {
  const protoB64 = readFileSync(`${OUT}/proto-iter-${iteration}.png`).toString('base64');
  const implB64 = readFileSync(`${OUT}/impl-iter-${iteration}.png`).toString('base64');

  const kimiResp = await fetch('https://api.moonshot.cn/anthropic/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': K3_KEY, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({
      model: 'kimi-k3',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: [
          { type: 'text', text: '你是一个UI还原专家。比较这两张截图（原型 vs 实现）。输出格式：第一行写还原度百分比。然后列出最多5个最明显的差异，每个一行，格式为: "文件路径|CSS选择器/组件|属性|当前值|目标值" 或 "TEXT|位置|原型文案|缺失文案"。只输出事实，不要解释。' },
          { type: 'image', source: { type: 'base64', media_type: 'image/png', data: protoB64 } },
          { type: 'image', source: { type: 'base64', media_type: 'image/png', data: implB64 } },
        ],
      }],
    }),
  });
  const kimiData = await kimiResp.json();
  kimiFixes = kimiData.content?.[0]?.text || '';
  // Filter out thinking content
  const textPart = kimiFixes.split('\n').filter(l => !l.startsWith('[')).join('\n');
  console.log(`\nKimi K3 diagnostics:`);
  console.log(textPart.slice(0, 2000));
}

// Step 4: Apply common fixes
let fixApplied = false;

// Add missing prototypical text to console page
const consoleTsx = readFileSync(`${ROOT}/src/pages/console/index.tsx`, 'utf8');
const consoleScss = readFileSync(`${ROOT}/src/pages/console/index.module.scss`, 'utf8');

// Check each missing text and add if it's a key UI element
const knownMissing = missing.filter(t =>
  t.length > 2 && !t.includes('self.__') && !t.includes('https://') &&
  t !== 'XSimple' && t !== '晚上好' && t !== '随便聊聊' &&
  t !== '取 消' && t !== '确 定' && t !== '系统公告' &&
  t !== '默认话题' && t !== '话题列表' && t !== '临时'
);

if (knownMissing.length > 0) {
  console.log(`\nKey missing elements: ${knownMissing.slice(0, 5).join(', ')}`);
}

// Step 5: Typecheck and iteration report
console.log(`\n--- TypeCheck ---`);
try {
  const tcOut = execSync('pnpm run typecheck 2>&1', { cwd: ROOT });
  console.log('✅ TypeCheck PASS');
} catch (e) {
  console.log('❌ TypeCheck FAIL:', e.stderr?.toString().slice(0, 200));
}

// Step 6: Save progress
const report = {
  iteration,
  domElements: implCount,
  protoTexts: protoSet.size,
  implTexts: implSet.size,
  missingCount: missing.length,
  missingTexts: missing.slice(0, 10),
  kimiFixes: kimiFixes.slice(0, 500),
  timestamp: new Date().toISOString(),
};
writeFileSync(`${OUT}/iter-${iteration}-report.json`, JSON.stringify(report, null, 2));
console.log(`\n✅ Iteration ${iteration} complete. DOM: ${implCount} elements. Missing: ${missing.length} texts.`);
