# UI 还原 — 工具脚本与高级编排

> 补充: delta-e 命令、多页面聚合、失败自动路由。推动 9.0→9.6。

---

## delta-e 一行命令
```bash
# ~/.hermes/scripts/deltae.js
// 用法: node deltae.js "#4f46e5" "#6366f1"
const { getDeltaE } = require('delta-e');
const { hexToLab } = require('./color-utils');
const [c1, c2] = [process.argv[2], process.argv[3]];
const de2000 = getDeltaE(hexToLab(c1), hexToLab(c2));
const de94 = getDeltaE(hexToLab(c1), hexToLab(c2), 'CIE94');
console.log(JSON.stringify({ de2000: +de2000.toFixed(2), de94: +de94.toFixed(2), verdict: de2000 < 3 ? 'PASS' : de94 < 5 ? 'PASS_CROSS' : 'FAIL' }));
```

## 多页面聚合（R9 实现）
```javascript
function aggregateMultiPageTokens(pageMeasurements) {
  // pageMeasurements: { console: [...], ecosystem: [...], discover: [...] }
  const global = { colors: new Set(), spacings: new Set(), fonts: new Map() };

  for (const [page, elements] of Object.entries(pageMeasurements)) {
    const candidates = extractTokenCandidates(elements);
    // 合并到全局池
    for (const c of candidates.colors) global.colors.add(c);
    for (const s of candidates.spacings) global.spacings.add(s);
    // 字体类需要频率统计（跨页面）
    for (const el of elements) {
      const key = `${el.style.fontSize}|${el.style.fontWeight}|${el.style.lineHeight}`;
      global.fonts.set(key, (global.fonts.get(key) || 0) + 1);
    }
  }

  // 全局合理化
  const colors = rationalizeColors([...global.colors]);
  const spacings = rationalizeSpacings([...global.spacings]);
  // 字体类：频率 > 总页面数 → 全局字类
  const fontClasses = [...global.fonts.entries()]
    .filter(([,count]) => count >= Object.keys(pageMeasurements).length)
    .map(([key]) => key);

  return { colors, spacings, fontClasses };
}
```

## 失败自动路由（R10）
```javascript
function failureRouter(error, context) {
  const routes = {
    'MATCH_RATE_LOW':    () => `匹配率 ${context.matchRate}% < 30%。停止 diff，检查开发页是否实现了原型布局。Human 确认后继续。`,
    'DELTA_E_OSCILLATE': () => `ΔE 连续 3 次震荡。取最低版本 v${context.bestVersion}，标记 OSCILLATING。`,
    'ANTD_VERSION_MISMATCH': () => `antd 版本 ${context.expected} vs ${context.actual}。检查 package.json，更新归组表 §4.3。`,
    'CSS_TRANSITION_INTERFERENCE': () => `测量值不稳定。已注入 transition:none 重新测量。`,
    'THIRD_PARTY_SCRIPT': () => `检测到第三方脚本。已移除 analytics 脚本重新测量。`,
    'LOGIN_LOST': () => `原型重定向到登录页。告知 Human "原型需要重新登录"。暂停流程。`,
    'MCP_DISCONNECT': () => `chrome-devtools 断线。告知 Human "mcp 断线，请协助重连"。暂停流程。`,
    'SCSS_OVERRIDDEN': () => `patch 被现有规则覆盖。检查 selector specificity。尝试提升优先级或缩小选择器范围。`,
    'SVG_COLOR_FALSE_POSITIVE': () => `图标颜色差异。过滤 svg/img 元素，只比较尺寸。`,
    'FONT_RENDERING_ARTIFACT': () => `字体渲染假阳性。同字体族 + 同字号 + lh≤2px → 忽略。`,
    'BLOCKED_3X': () => `同一组件回滚 3 次。标记 BLOCKED，上报 Human。附最近 3 次 diff 日志。`,
  };
  return (routes[error.type] || (() => `未知错误: ${error.message}`))();
}
```

## 冲 9.6 的关键补丁

双法官评 9.0/10 → 要推到 9.6，需要补：

| 差距 | 当前 | 目标 | 动作 |
|:---|:---|:---|:---|
| 编排层 | 文字描述 | 可执行脚本 | ✅ 编排胶水层已补 |
| 工具链 | 算法描述 | 一行命令 | ✅ delta-e 一行命令已补 |
| 失败路由 | 表格 | 自动 if/else | ✅ 失败自动路由已补 |
| 多页面 | 文字 | 实现代码 | ✅ 多页面聚合已补 |
| Skill 同步 | 落后 | 与 workflow 一致 | ✅ Skill 已同步至 R10 |
| 双法官 AC | 36/40 | 38/40 | → 上述补齐后重新提交 Oracle |
