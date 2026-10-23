#!/usr/bin/env node
// CAPTURE-STATES — 交互态/二级 UI 真值采集（机制 §十三）
// 用法: node scripts/ui-restore/capture-states.mjs <url> <outDir> --task home_page [--dismiss-modal] [--wait ms]
// 原理: 动作前提取一次全量样式 → 执行动作（click/hover 语义锚点）→ 再提取一次
//       delta = 动作后新增的 DOM 节点 = 下拉/弹窗/气泡等二级 UI 的精确真值（禁止凭截图猜）
// 锚点定义在 task.json states[]:
//   {name, action:{type:'click'|'hover', text?|icon?, y?}, settle?}
//   或动作序列 {name, actions:[{...},{...}], settle?}（如: 先开弹窗再切 tab 采第二态）
//   text = ownText 精确匹配；icon = lucide 图标名；y = '>600' 这类消歧过滤（同名文本多处出现时）
// 产出: <outDir>/<name>.png（全页截图）+ <name>.delta.json（新增元素样式表）
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { loadTask } from './task-config.mjs';

const [url, outDir, ...flags] = process.argv.slice(2);
const opt = (n, d) => { const i = flags.indexOf(n); return i > -1 ? flags[i + 1] : d; };
const numOpt = (n, d) => { const value = opt(n, d); const parsed = Number(value); return Number.isFinite(parsed) ? parsed : d; };
if (!url || !outDir) { console.error('usage: capture-states.mjs <url> <outDir> --task X [--dismiss-modal] [--wait ms]'); process.exit(1); }
const TASK = opt('--task', 'home_page') || 'home_page';
const cfg = loadTask(TASK);
const WAIT = numOpt('--wait', 3000);
const ONLY = (() => { const i = flags.indexOf('--only'); return i > -1 ? flags[i + 1].split(',') : null; })();
const DISMISS = flags.includes('--dismiss-modal');
mkdirSync(outDir, { recursive: true });

const STATES = (cfg.states || []).filter(s => !ONLY || ONLY.includes(s.name));
if (!STATES.length) { console.error(`FATAL: task.json 缺少 states[]（交互态定义，见 §十三）`); process.exit(2); }

const EXTRACT = () => {
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    out.push({
      tag: el.tagName.toLowerCase(), text: ownText.slice(0, 200),
      cls: String(el.className?.baseVal ?? el.className ?? '').slice(0, 100),
      x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
      fs: cs.fontSize, fw: cs.fontWeight, lh: cs.lineHeight,
      ff: cs.fontFamily.slice(0, 60), ls: cs.letterSpacing, // 字体族/字距也是真值（文本宽度差异的唯一来源）
      color: cs.color, bg: cs.backgroundColor, radius: cs.borderRadius,
      pad: cs.padding, gap: cs.gap, border: `${cs.borderWidth} ${cs.borderStyle} ${cs.borderColor}`,
      shadow: cs.boxShadow.slice(0, 120),
    });
  });
  return out;
};

const sig = r => `${r.tag}|${r.cls}|${r.text}|${r.x},${r.y},${r.w},${r.h}`;

// 语义锚点 → 页面坐标（live 解析，proto/impl 通用）
async function resolveAnchor(page, action) {
  return page.evaluate(a => {
    const rows = [...document.querySelectorAll('body *')].map(el => {
      const r = el.getBoundingClientRect();
      const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
      return { el, r, ownText, cls: String(el.className?.baseVal ?? el.className ?? '') };
    }).filter(o => o.r.width >= 2 && o.r.height >= 2);
    const yOk = o => {
      if (!a.y) return true;
      const m = a.y.match(/^([><])(\d+)$/);
      return m ? (m[1] === '>' ? o.r.y > +m[2] : o.r.y < +m[2]) : true;
    };
    const xOk = o => a.xMax === undefined || o.r.x <= a.xMax;
    let hit = null;
    // 图标匹配：精确 lucide-<icon>；lucide 版本改名（align-justify→text-align-justify，
    // message-circle-question→message-circle-question-mark）→ 长名（≥6）允许子串，短名后缀防误配
    const aliases = {
      'message-circle-question-mark': ['message-circle-question', 'message-circle-question-mark'],
      'message-circle-question': ['message-circle-question', 'message-circle-question-mark'],
    };
    const iconNames = aliases[a.icon] || [a.icon];
    const iconHit = o => o.cls.split(/\s+/).some(c =>
      iconNames.some(name => c === `lucide-${name}` || c.endsWith(`-${name}`) || (name.length >= 6 && c.includes(`-${name}`))));
    if (a.icon) hit = rows.find(o => iconHit(o) && yOk(o));
    if (!hit && a.text) {
      const cands = rows.filter(o => o.ownText === a.text && yOk(o) && xOk(o));
      hit = cands[cands.length - 1] || null; // 多个同名取最后（DOM 序后者通常为主区域）
    }
    if (!hit) return null;
    return { x: Math.round(hit.r.x + hit.r.width / 2), y: Math.round(hit.r.y + hit.r.height / 2), found: hit.ownText || hit.cls.slice(0, 40) };
  }, action);
}

const b = await chromium.launch({ headless: true });

// 遮罩守卫：公告弹窗可能晚于 dismiss 渲染（慢加载/限流），动作前必须确保无遮罩拦截
// 无人值守铁律：遮罩存在时动作点击必然落空（delta 失真为 0/4）
async function clearModal(page) {
  for (let i = 0; i < 12; i++) {
    const hasMask = await page.evaluate(() =>
      [...document.querySelectorAll('body *')].some(el => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return r.width >= innerWidth - 4 && r.height >= innerHeight - 4 && /rgba?\(.*0\.[1-7]/.test(cs.backgroundColor);
      })).catch(() => false);
    if (!hasMask) return;
    for (const label of ['确 定', '确定', '×', '关闭']) {
      try { await page.click(`button:has-text("${label}")`, { timeout: 800 }); break; } catch {}
    }
    await page.waitForTimeout(700);
  }
}

for (const st of STATES) {
  const page = await b.newPage({ viewport: { width: cfg.vw, height: cfg.vh }, deviceScaleFactor: cfg.dsf });
  // 站点限流/网络抖动重试（与 discover-states 同策略：3 次 [内部自检，非行业标准]，3s/8s 退避）
  for (let attempt = 0; attempt < 3; attempt++) {
    try { await page.goto(url, { timeout: 90000, waitUntil: 'domcontentloaded' }); break; }
    catch (e) {
      if (attempt === 2) { console.error(`SKIP ${st.name}: goto 失败 ${e.message.slice(0, 60)}`); }
      else { console.log(`  goto 重试 ${attempt + 1}/2: ${e.message.slice(0, 50)}`); await page.waitForTimeout(3000 + attempt * 5000); }
    }
  }
  if (page.url() === 'about:blank') { await page.close(); continue; }
  await page.waitForTimeout(WAIT);
  if (DISMISS) {
    for (const label of ['确 定', '确定', '×']) {
      try { await page.click(`button:has-text("${label}")`, { timeout: 3000 }); break; } catch {}
    }
    await page.waitForTimeout(800);
  }
  await clearModal(page); // 晚渲染遮罩兜底（DISMISS 未开时也执行——impl 无遮罩秒过）
  let lastAnchor = null, failed = false, before = null;
  const preactions = st.preactions || [];
  for (const act of preactions) {
    const anchor = await resolveAnchor(page, act);
    if (!anchor) { console.error(`SKIP ${st.name}: preaction 锚点未找到 ${JSON.stringify(act)}`); failed = true; break; }
    await page.mouse.click(anchor.x, anchor.y);
    await page.waitForTimeout(act.settle ?? st.settle ?? 800);
  }
  if (failed) { await page.close(); continue; }
  const actions = st.actions || [st.action];
  const routeBefore = page.url();
  for (const act of actions) {
    // 锚点就绪轮询：慢站/异步渲染下固定 wait 不可靠（铁律：无人值守必须自适应）
    let anchor = null;
    const deadline = Date.now() + (act.anchorTimeout ?? 15000);
    while (Date.now() < deadline) {
      anchor = await resolveAnchor(page, act);
      if (anchor) break;
      await page.waitForTimeout(500);
    }
    if (!anchor) { console.error(`SKIP ${st.name}: 锚点未找到 ${JSON.stringify(act)}`); failed = true; break; }
    // before 快照必须在首个锚点就绪后采集——否则慢渲染站点的 app 外壳会被误计入 delta
    // 且必须等 DOM 静默（异步弹窗/徽标挂载完毕），否则 delta 混入动作无关节点
    if (!before) {
      await page.evaluate((quiet) => new Promise(res => {
        let timer;
        const obs = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(done, quiet); });
        const done = () => { obs.disconnect(); res(true); };
        timer = setTimeout(done, quiet);
        obs.observe(document.body, { childList: true, subtree: true, attributes: true });
        setTimeout(done, 12000); // 兜底上限
      }), 1000).catch(() => {});
      before = await page.evaluate(EXTRACT);
    }
    lastAnchor = anchor;
    if (act.type === 'hover') await page.mouse.move(anchor.x, anchor.y, { steps: 5 });
    else await page.mouse.click(anchor.x, anchor.y);
    await page.waitForTimeout(act.settle ?? st.settle ?? 800);
  }
  if (failed) { await page.close(); continue; }
  const after = await page.evaluate(EXTRACT);
  const routeAfter = page.url();
  const beforeSet = new Set(before.map(sig));
  const delta = after.filter(r => !beforeSet.has(sig(r)));
  const rows = st.capture === 'full' ? after : delta;
  await page.screenshot({ path: `${outDir}/${st.name}.png` });
  writeFileSync(`${outDir}/${st.name}.delta.json`, JSON.stringify({
    state: st.name, actions, preactions, capture: st.capture || 'delta', anchor: lastAnchor, url, routeBefore, routeAfter, viewport: [cfg.vw, cfg.vh],
    beforeCount: before.length, afterCount: after.length, deltaCount: delta.length, rows,
  }, null, 1));
  console.log(`${st.name}: anchor=(${lastAnchor.x},${lastAnchor.y}) "${lastAnchor.found}" route=${routeBefore}→${routeAfter} delta=${delta.length} → ${outDir}/${st.name}.{png,delta.json}`);
  await page.close();
}
await b.close();
