#!/usr/bin/env node
// MEASURE — 无人值守还原的测量中枢（只测量，不修复）
// 用法: node .claude/workflows/frontend-overnight/scripts/ui-restore/measure.mjs [--task home_page]
// 产出: .omc/ui-autopilot/<task>/measurements/latest/
//   impl.png | impl-styles.json | zone-report.json | style-diff.json | layout-diff.json | fix-list.json | score.json
//   （多断点时文件名自动加 -<w>x<h> 后缀，单断点保持 legacy 命名）
// 真值来源: gold/proto.png + gold/proto-styles.json（禁止从截图猜值）
// 视口铁律: gold 与 impl 必须同视口（见 task.json viewport/viewports）；不一致直接硬失败（坐标 diff 无意义）
// 多断点（§十二）: task.json viewports[] 逐断点测量，综合分取最短板（任一断点不达标即不达标）
// 通用化: 视口/区域/权重/URL 全部来自 .omc/ui-autopilot/<task>/task.json（task-config.mjs 加载）
import { chromium } from 'playwright';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { loadTask } from './task-config.mjs';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i > -1 ? args[i + 1] : d; };
const TASK = opt('--task', 'home_page');
const cfg = loadTask(TASK);
const IMPL = opt('--impl', cfg.impl);
const GOLD = cfg.goldDir;
const OUT = cfg.outDir;
const DSF = cfg.dsf;
const MULTI = cfg.viewports.length > 1;
mkdirSync(OUT, { recursive: true });

async function measureVp(vp) {
  const [VW, VH] = [vp.w, vp.h];
  const SUF = MULTI ? `-${VW}x${VH}` : '';
  const G = { png: `${GOLD}/proto${SUF}.png`, styles: `${GOLD}/proto-styles${SUF}.json` };
  if (!existsSync(G.png) || !existsSync(G.styles)) {
    console.error(`FATAL: 缺少断点 ${VW}x${VH} 的 gold（${G.png}）→ 重采: bash .claude/workflows/frontend-overnight/scripts/ui-restore/gold-refresh.sh ${TASK}`);
    process.exit(2);
  }

  // ── 语义区域（task.json 定义，CSS px；内部乘 dsf 对齐 device px）──
  const ZONES = vp.zones.map(z => ({ name: z.name, box: z.box.map(v => v * DSF) }));

  // ── 1. 采集 impl ──
  const b = await chromium.launch({ headless: true });
  const page = await b.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: DSF });
  await page.goto(IMPL, { timeout: 30000 });
  await page.waitForTimeout(cfg.wait);
  const pngBuf = await page.screenshot();
  writeFileSync(`${OUT}/impl${SUF}.png`, pngBuf);
  const implRows = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
      out.push({
        tag: el.tagName.toLowerCase(), text: ownText.slice(0, 40),
        cls: String(el.className?.baseVal ?? el.className ?? '').slice(0, 80),
        x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
        fs: cs.fontSize, fw: cs.fontWeight, color: cs.color, bg: cs.backgroundColor,
        radius: cs.borderRadius, pad: cs.padding,
      });
    });
    return out;
  });
  await b.close();
  writeFileSync(`${OUT}/impl-styles${SUF}.json`, JSON.stringify({ url: IMPL, count: implRows.length, rows: implRows }, null, 1));

  // 空壳/未挂载页面不能生成可消费的分数，否则 loop 会把失效测量误判为收敛。
  const goldRows = JSON.parse(readFileSync(G.styles, 'utf8')).rows || [];
  if (goldRows.length < cfg.domMin) {
    console.error(`GOLD_INCOMPLETE: gold rows ${goldRows.length} < domMin ${cfg.domMin} — 重采 gold 后再测量`);
    process.exit(2);
  }
  const minRows = Math.max(20, Math.ceil(goldRows.length * 0.2));
  if (implRows.length < minRows) {
    console.error(`BLOCKED_CONTENT_NOT_MOUNTED: impl rows ${implRows.length} < minimum ${minRows} (gold ${goldRows.length})`);
    process.exit(3);
  }

  // ── 2. 加载 gold ──
  const protoPng = PNG.sync.read(readFileSync(G.png));
  const protoStyles = JSON.parse(readFileSync(G.styles, 'utf8'));
  const implPng = PNG.sync.read(pngBuf);

  // 视口一致性铁律：gold 与 impl 不同视口 → 一切坐标 diff 都是垃圾，硬失败并提示重采
  const [GVW, GVH] = protoStyles.viewport || [VW, VH];
  if (GVW !== VW || GVH !== VH) {
    console.error(`FATAL: gold viewport ${GVW}x${GVH} ≠ impl ${VW}x${VH} — 重采 gold: bash .claude/workflows/frontend-overnight/scripts/ui-restore/gold-refresh.sh ${TASK}`);
    process.exit(2);
  }
  // 离屏元素过滤（portal/隐藏抽屉等越出视口的元素不参与 diff，否则产生幻影真值）
  // 注意顺序：必须先在原始 rows 上检测抽屉归属，再剔除离屏容器本身——
  // 否则抽屉容器先被删掉，其内部"坐标在视口内"的元素就失去判定依据（inbox/origami 幻影教训）
  {
    const origRows = protoStyles.rows;
    var protoStylesAllRows = origRows; // 过滤前快照（幻影名全集判定用）
    const wide = origRows.filter(r => r.w >= 300);
    const offscreen = r => r.x < 0 || r.y < 0 || r.x + r.w > GVW || r.y + r.h > GVH;
    const inDrawer = el => el.w < 300 && wide.some(r => r !== el && offscreen(r) &&
      r.x <= el.x && r.y <= el.y && r.x + r.w >= el.x + el.w && r.y + r.h >= el.y + el.h);
    protoStyles.rows = origRows.filter(r => !offscreen(r) && !inDrawer(r));
  }

  // ── 3. 区域像素 diff ──
  const zoneReport = ZONES.map(z => {
    const [x, y, w, h] = z.box;
    const cw = Math.min(w, protoPng.width - x, implPng.width - x);
    const ch = Math.min(h, protoPng.height - y, implPng.height - y);
    const ca = new PNG({ width: cw, height: ch }), cb = new PNG({ width: cw, height: ch });
    PNG.bitblt(protoPng, ca, x, y, cw, ch, 0, 0);
    PNG.bitblt(implPng, cb, x, y, cw, ch, 0, 0);
    const diffPx = pixelmatch(ca.data, cb.data, null, cw, ch, { threshold: 0.15 });
    return { zone: z.name, diffPct: +(100 * diffPx / (cw * ch)).toFixed(2) };
  }).sort((p, q) => q.diffPct - p.diffPct);
  writeFileSync(`${OUT}/zone-report${SUF}.json`, JSON.stringify(zoneReport, null, 1));

  // ── 4. 计算样式 diff（空白归一 + tag 失配回退）──
  const norm = t => t.replace(/\s+/g, ' ').trim().toLowerCase();
  const px = v => parseFloat(v) || 0;
  const rgbDist = (a, b) => {
    const pa = (String(a).match(/[\d.]+/g) || []).map(Number), pb = (String(b).match(/[\d.]+/g) || []).map(Number);
    return pa.length < 3 || pb.length < 3 ? 0 : Math.round(Math.hypot(pa[0] - pb[0], pa[1] - pb[1], pa[2] - pb[2]));
  };
  const protoTexts = protoStyles.rows.filter(r => r.text);
  const implTexts = implRows.filter(r => r.text);
  // 同名文本可能多处出现（如"随便聊聊"在助手列表和 topbar 各一个）：
  // 按归一化相对坐标 (x/vw, y/vh) 最近邻匹配，消除跨元素错配
  const [PVW, PVH] = protoStyles.viewport || [VW, VH];
  const IVW = VW, IVH = VH;
  const implByText = new Map();
  implTexts.forEach(r => {
    const k = norm(r.text);
    if (!implByText.has(k)) implByText.set(k, []);
    implByText.get(k).push(r);
  });
  const pickNearest = (pr, candidates) => {
    const px = pr.x / PVW, py = pr.y / PVH;
    let best = null, bestD = Infinity;
    for (const ir of candidates) {
      const d = Math.hypot(ir.x / IVW - px, ir.y / IVH - py);
      if (d < bestD) { bestD = d; best = ir; }
    }
    return bestD < 0.08 ? best : null; // 相对位移超 8% 视为未匹配
  };

  let matched = 0, propTotal = 0, propEqual = 0;
  const styleDiffs = [], missing = [];
  for (const pr of protoTexts) {
    const candidates = implByText.get(norm(pr.text));
    const ir = candidates ? pickNearest(pr, candidates) : null;
    if (!ir) { missing.push(pr.text.slice(0, 50)); continue; }
    matched++;
    const items = [];
    const cmp = (prop, cond, fix) => { propTotal++; if (cond) propEqual++; else items.push(fix); };
    cmp('font-size', Math.abs(px(pr.fs) - px(ir.fs)) <= 0.5, `font-size ${ir.fs} → ${pr.fs}`);
    cmp('font-weight', pr.fw === ir.fw, `font-weight ${ir.fw} → ${pr.fw}`);
    cmp('color', rgbDist(pr.color, ir.color) <= 24, `color ${ir.color} → ${pr.color}`);
    cmp('background', rgbDist(pr.bg, ir.bg) <= 24 || pr.bg.includes('0, 0, 0, 0'), `background ${ir.bg} → ${pr.bg}`);
    cmp('width', Math.abs(pr.w - ir.w) <= 4, `width ${ir.w}px → ${pr.w}px`);
    cmp('height', Math.abs(pr.h - ir.h) <= 4, `height ${ir.h}px → ${pr.h}px`);
    cmp('radius', Math.round(parseFloat(pr.radius) || 0) === Math.round(parseFloat(ir.radius) || 0), `radius ${ir.radius} → ${pr.radius}`);
    if (items.length) styleDiffs.push({ text: pr.text.slice(0, 40), implCls: ir.cls, items });
  }
  writeFileSync(`${OUT}/style-diff${SUF}.json`, JSON.stringify({ matched, missing: missing.length, styleDiffs, missingTexts: missing }, null, 1));

  // ── 4.5 布局锚点 diff（机制 v3）──
  // 为什么需要：文本 diff 只覆盖"带文字的元素"，按钮高度/命中区/容器 padding/flex 对齐
  // 等无文本布局从来不会进入 fix-list → AI 只能凭截图估值 → 同类错误复发。
  // v3 三路真值：
  //   a) 图标锚定：lucide 图标名 1:1 贪心最近匹配，比对 svg 位置 + 命中区（最小容器祖先）
  //   b) 容器铬层：文本元素的最小带背景祖先（按钮/标签外壳）比对 bg/w/h
  //   c) 幻影检测：impl 中未匹配的多余图标实例（原型没有的元素必须删除）
  const LUCIDE_ALIAS = { 'message-circle-question-mark': 'message-circle-question', 'text-align-justify': 'align-justify' };
  const iconOf = r => {
    if (r.tag !== 'svg') return null;
    const m = r.cls.match(/lucide-([a-z0-9-]+)/);
    if (!m) return null;
    const name = m[1];
    return LUCIDE_ALIAS[name] || name;
  };
  // 从扁平 rows 用包含关系重建"最小容器祖先"（提取时无父指针）
  const enclosing = (rows, el, pred) => {
    let best = null;
    for (const r of rows) {
      if (r === el) continue;
      if (!['div', 'button', 'span', 'a', 'aside'].includes(r.tag)) continue;
      if (!(r.x <= el.x && r.y <= el.y && r.x + r.w >= el.x + el.w && r.y + r.h >= el.y + el.h)) continue;
      if (pred && !pred(r)) continue;
      if (!best || r.w * r.h < best.w * best.h) best = r;
    }
    return best;
  };
  // 命中区定义：优先最小可点击祖先（button/a），否则最大的 ≤60px “磁贴”容器；都没有 = 不可比（跳过防噪声）
  // 返回 {area, source}：source 不一致（原型 div 按钮 vs 实现真 button）时不可比，调用方须跳过
  // （案例：proto kefu 是 div 按钮 → 命中区回退到 20x20 磁贴；impl 是真 <button> 106x32 → 幻影修复项）
  const hitAreaOf = (rows, el) => {
    const click = enclosing(rows, el, r => r.tag === 'button' || r.tag === 'a');
    if (click) return { area: click, source: 'click' };
    let best = null;
    for (const r of rows) {
      if (r === el) continue;
      if (!['div', 'button', 'span', 'a'].includes(r.tag)) continue;
      if (!(r.x <= el.x && r.y <= el.y && r.x + r.w >= el.x + el.w && r.y + r.h >= el.y + el.h)) continue;
      if (r.w > 60 || r.h > 60) continue;
      if (!best || r.w * r.h > best.w * best.h) best = r;
    }
    return best ? { area: best, source: 'tile' } : null;
  };
  // 铬层定义：元素自身带背景则自身即铬层（文本直接写在按钮上），否则爬最小"带背景或带圆角"的祖先
  // 注意必须精确匹配 'rgba(0, 0, 0, 0)'：includes 子串会把 rgba(0,0,0,0.06) 半透明误判为透明
  // 圆角也算铬层锚点：proto 卡片常无边框底色透明但有 r5 圆角（提取无 border 字段，
  // 案例：话题卡片 gold bg 透明 r5 → 铬层误爬到 281x812 面板）
  const withBg = r => r.bg && r.bg !== 'rgba(0, 0, 0, 0)' && r.bg !== 'transparent';
  const withRadius = r => r.radius && r.radius !== '0px';
  const chromeOf = (rows, el) =>
    (withBg(el) && ['button', 'a', 'span', 'div'].includes(el.tag)) ? el
      : enclosing(rows, el, r => withBg(r) || withRadius(r));
  const layoutFixes = [];
  // 幻影判定用"原始 gold 图标名全集"：抽屉过滤会把与抽屉几何重叠的合法面板图标一并剔除
  // （右面板 281px 与 400px 离屏抽屉坐标完全重叠，扁平 rows 无法按包含关系区分层级）——
  // 若图标名在原型中存在过，impl 实例就不是幻影（幻影检测专为"原型里从未有过的发明元素"，如绿色语音 FAB）
  const goldIconNamesAll = new Set(protoStylesAllRows.map(iconOf).filter(Boolean));
  const goldIcons = protoStyles.rows.map(r => ({ r, icon: iconOf(r) })).filter(o => o.icon);
  const implIcons = implRows.map(r => ({ r, icon: iconOf(r) })).filter(o => o.icon);
  const usedImpl = new Set();
  for (const g of goldIcons) {
    let best = null, bestD = Infinity;
    for (const i of implIcons) {
      if (i.icon !== g.icon || usedImpl.has(i)) continue;
      const d = Math.hypot(i.r.x / IVW - g.r.x / PVW, i.r.y / IVH - g.r.y / PVH);
      if (d < bestD) { bestD = d; best = i; }
    }
    if (!best || bestD > 0.15) { layoutFixes.push({ anchor: `icon:${g.icon}`, kind: 'missing-icon', gold: `(${g.r.x},${g.r.y})` }); continue; }
    usedImpl.add(best);
    if (Math.abs(best.r.x - g.r.x) > 8 || Math.abs(best.r.y - g.r.y) > 8)
      layoutFixes.push({ anchor: `icon:${g.icon}`, kind: 'position', impl: `(${best.r.x},${best.r.y})`, gold: `(${g.r.x},${g.r.y})`, fix: `${best.r.cls} 位置 (${best.r.x},${best.r.y}) → (${g.r.x},${g.r.y})` });
    const gh = hitAreaOf(protoStyles.rows, g.r), ih = hitAreaOf(implRows, best.r);
    if (gh && ih && gh.source === ih.source && (Math.abs(gh.area.w - ih.area.w) > 4 || Math.abs(gh.area.h - ih.area.h) > 4))
      layoutFixes.push({ anchor: `icon:${g.icon}`, kind: 'hit-area', fix: `${ih.area.cls} 命中区 ${ih.area.w}x${ih.area.h} → ${gh.area.w}x${gh.area.h}` });
  }
  for (const i of implIcons) if (!usedImpl.has(i) && !goldIconNamesAll.has(i.icon))
    layoutFixes.push({ anchor: `icon:${i.icon}`, kind: 'phantom', fix: `删除幻影元素 ${i.r.cls} @(${i.r.x},${i.r.y})（原型无此图标实例）` });
  // 容器铬层：已匹配文本对的铬层比对（bg/w/h）
  for (const pr of protoTexts) {
    const candidates = implByText.get(norm(pr.text));
    const ir = candidates ? pickNearest(pr, candidates) : null;
    if (!ir) continue;
    const gp = chromeOf(protoStyles.rows, pr), ip = chromeOf(implRows, ir);
    if (!gp || !ip) continue;
    if (rgbDist(gp.bg, ip.bg) > 24)
      layoutFixes.push({ anchor: `chrome:${pr.text.slice(0, 16)}`, kind: 'chrome-bg', fix: `${ip.cls} 背景 ${ip.bg} → ${gp.bg}` });
    if (Math.abs(gp.h - ip.h) > 2)
      layoutFixes.push({ anchor: `chrome:${pr.text.slice(0, 16)}`, kind: 'chrome-h', fix: `${ip.cls} 外壳高 ${ip.h}px → ${gp.h}px` });
    if (Math.abs(gp.w - ip.w) > 6)
      layoutFixes.push({ anchor: `chrome:${pr.text.slice(0, 16)}`, kind: 'chrome-w', fix: `${ip.cls} 外壳宽 ${ip.w}px → ${gp.w}px` });
  }
  // 去重：同一 fix 只报一次（如 4 张卡片各自文本产生相同 chrome 修复项）
  const seenFix = new Set();
  const dedupedFixes = layoutFixes.filter(f => {
    const k = `${f.kind}|${f.fix || `${f.anchor}:${f.gold || ''}`}`;
    if (seenFix.has(k)) return false;
    seenFix.add(k);
    return true;
  });
  writeFileSync(`${OUT}/layout-diff${SUF}.json`, JSON.stringify(dedupedFixes, null, 1));

  // ── 5. 综合分（权重来自 task.json）──
  const pixelScore = 1 - zoneReport.reduce((s, z) => s + z.diffPct, 0) / zoneReport.length / 100;
  const styleScore = propTotal ? propEqual / propTotal : 0;
  const textScore = protoTexts.length ? matched / protoTexts.length : 0;
  const W = cfg.weights;
  const score = +(W.pixel * pixelScore + W.style * styleScore + W.text * textScore).toFixed(4);
  writeFileSync(`${OUT}/score${SUF}.json`, JSON.stringify({ score, pixelScore: +pixelScore.toFixed(4), styleScore: +styleScore.toFixed(4), textScore: +textScore.toFixed(4) }, null, 1));

  // ── 6. fix-list（AI worker 的唯一输入）──
  const fixList = {
    score,
    zones: zoneReport.filter(z => z.diffPct > 3),
    styleFixes: styleDiffs.slice(0, 20),
    layoutFixes: dedupedFixes.slice(0, 20),
    missingTexts: missing.slice(0, 10),
  };
  writeFileSync(`${OUT}/fix-list${SUF}.json`, JSON.stringify(fixList, null, 1));

  const tag = MULTI ? `[${VW}x${VH}] ` : '';
  console.log(`${tag}score=${score}  pixel=${pixelScore.toFixed(3)} style=${styleScore.toFixed(3)} text=${textScore.toFixed(3)}`);
  console.log(`${tag}zones>3%: ${fixList.zones.map(z => `${z.zone}=${z.diffPct}%`).join(' ') || 'none'}`);
  console.log(`${tag}styleDiffs=${styleDiffs.length} layoutFixes=${dedupedFixes.length} missingTexts=${missing.length}`);
  if (!MULTI) console.log(`→ ${OUT}/fix-list.json`);
  return score;
}

// ── 逐断点测量，综合分取最短板（§十二：任一断点不达标即不达标）──
const scores = [];
for (const vp of cfg.viewports) scores.push(await measureVp(vp));
if (MULTI) {
  console.log(`OVERALL(min)=${Math.min(...scores).toFixed(4)} — 最短板断点门禁`);
  console.log(`→ ${OUT}/fix-list-<w>x<h>.json（逐断点）`);
}
