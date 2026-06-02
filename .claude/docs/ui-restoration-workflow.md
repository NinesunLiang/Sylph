# UI 还原通用工作流

> ⛔ **核心铁律**: 截图对比 = 死路。数值驱动（getComputedStyle + delta-e + Token 反向映射）是唯一可行路径。
> 适用场景: React + Sass/SCSS + CSS Modules 或 BEM 项目。原型为 HTML 页面。

### 极简哲学

```
1. 能 div 就 div — 原型用 antd Button 不代表开发页必须用。div + CSS ≥ antd 的地方，用 div
2. 继承优先 — 父级定义 font/color，子元素继承。不在每个 DOM 节点重复声明
3. 最少 DOM — 原型 5 层嵌套视觉，开发页用 2 层实现。每多一层 DOM 必须有理由
4. 最少属性 — 不写默认值 display:block/position:static。修复 diff 优先删属性而非加属性
5. 原子复用 — 识别重复 UI 模式，提取为原子组件。不复制粘贴样式
```

| 场景 | 原生 HTML+CSS | antd |
|:---|:---|:---|
| 按钮/标签/头像 | ✅ 优先 | 仅交互复杂时 |
| 布局 | ✅ flex/grid | 仅响应式断点 |
| 表单/表格/弹窗 | ❌ | ✅ 不可替代 |

---

## 前置依赖

| 信息 | 来源 |
|:---|:---|
| Token 文件列表 | AGENTS.md §Token 注入边界 |
| 样式方案 | AGENTS.md §样式规范 |
| UI 组件库 | package.json dependencies |
| 原型 URL + 开发服务 URL + 项目路径 | 项目提供 |

---

## 流水线架构

```
分割工作区 → 原型驱动Token初始化 → 区域N原型测量 → 区域N开发页测量 → 区域N智能匹配 → 区域N数值Diff → Token匹配 → SCSS生成 → 质量门禁 → 四遍迭代 → 区域N+1
```
---

## 工作区分割（Round 11 — 核心策略）

> ⛔ **一次只还原一个区域。范围越小，匹配越准。**

全页 500 元素 → 匹配噪音大、diff 范围失控。将页面按视觉边界切分为独立区域，每个区域独立走完整流水线。

### 分割算法

```javascript
function segmentPage(elements, screenshotWidth, screenshotHeight) {
  // 1. 全页截图 → chrome-devtools screenshot
  // 2. 从 extractPageStyles 结果中识别视觉边界:
  //    - 水平贯穿全宽的元素 → 上下分割线（topbar、footer）
  //    - 固定定位元素 → 独立区域（sidebar）
  //    - 其余按 rect.y 聚类 → 内容区
  //
  // 3. 输出区域列表:
  return [
    { name: 'topbar',   rect: { x:0, y:0, w:1440, h:56 },   elements: [...] },
    { name: 'sidebar',  rect: { x:0, y:56, w:240, h:844 },   elements: [...] },
    { name: 'content',  rect: { x:240, y:56, w:1200, h:844 }, elements: [...] },
    { name: 'footer',   rect: { x:0, y:900, w:1440, h:64 },  elements: [...] },
  ];
}
```

### 并发执行

```
Token 初始化（串行，一次性）

    ├─ Region topbar  ──→ 测 → 匹配 → diff → SCSS → 门禁 ──┐
    ├─ Region sidebar ──→ 测 → 匹配 → diff → SCSS → 门禁 ──┤
    ├─ Region content ──→ 测 → 匹配 → diff → SCSS → 门禁 ──┤
    └─ Region footer  ──→ 测 → 匹配 → diff → SCSS → 门禁 ──┘
                                                              ↓
                                                    全页复查（边界无缝）
```

**并行条件**：
- Token 文件已锁 → 所有区域共用同一套 Token
- 每个区域有独立 SCSS 文件 → 无写入冲突
- 共享文件（如 `_colors.scss`）→ Token 初始化后锁定，区域不写

### 区域边界规则

```
1. 固定定位元素（position:fixed）→ 独立区域
2. 水平贯穿全宽 90%+ 的元素 → 分割线
3. 其余按 rect.y 自然聚类（间距 > 50px = 新区块）
4. 每个区域用 chrome-devtools 单独截图 → region-proto.png / region-dev.png
5. 区域边界 ±10px 缓冲区 → 防边缘元素截断
```

### 为什么范围小 = 更准确

| 全页 (500元素) | 单区域 (30-80元素) |
|:---|:---|
| 匹配 O(n²) 计算量大 | 匹配快且准 |
| 元素间距接近 → 容易误匹配 | 元素少 → 误匹配概率低 |
| 差异 50+ → 不知道先修谁 | 差异 3-8 → 优先序清晰 |
| 验证困难 → "这一片好像都对" | 验证简单 → "topbar 0 diff ✅" |

---

## 编排胶水层（Round 10 工程化）

### MCP 调用模式
```
测页面:
  mcp: puppeteer_navigate(url)
  mcp: evaluate(animationFreeze)       // 冻结动画 + 清除 timer
  mcp: waitForTimeout(1000)            // React hydration
  mcp: evaluate(extractPageStyles)     // 丢弃首次
  mcp: waitForTimeout(500)
  mcp: evaluate(extractPageStyles)     // 正式基线 → 写 JSON 文件
```

### 错误重试路由
```
puppeteer_navigate 超时 → retry × 2 → abort
evaluate 超时 → 检查连接 → 断线 report → 未断线缩小 scope
SCSS 编译失败 → 语法错修正 × 3
HMR 验证异常 → 差异不变 → 检查 specificity → 差异增加 → 回滚 → 泄漏 → 缩小选择器
```

---

## Step 1: 原型驱动 Token 初始化（R8/R9）

> ⛔ 原型是 Token 唯一真相源。

```
流程:
1. 测原型 → 提取所有唯一颜色/间距/字号/字重/行高/圆角/阴影
2. Token 合理化: 颜色 ΔE<2 合并、间距 ±1px 合并、字号取整 → 47候选 → ~16 Token
3. 合并已有 Token: 项目已有不覆盖，ΔE<3匹配，提案新增，UNUSED标注
4. 全局 vs 私有: ≥3组件共用 → 全局Token；1组件 → 私有
5. 多页面聚合: 先测所有页面 → 一次性出Token
6. 原子 Token: 自动命名 ($color-primary: #4f46e5) + 复合Token: 字体类 ($font-body: 14px/400/1.5)
7. 交互态: hover/active/disabled 填入 Token 的 default/hover/active/disabled 维度
8. Human 确认 → 写入 tokens/
```

---

## Step 2: 原型测量

### extractPageStyles (含 Portal 扫描 + viewport slicing 降级)

```javascript
function extractPageStyles(options = {}) {
  const { selector = 'body', includeChildren = true, maxDepth = 50, minSize = 4 } = options;
  const results = [];
  const KEY_PROPERTIES = [
    'display','position','width','height',
    'marginTop','marginRight','marginBottom','marginLeft',
    'paddingTop','paddingRight','paddingBottom','paddingLeft',
    'flexDirection','alignItems','justifyContent','gap',
    'gridTemplateColumns','gridTemplateRows','gridColumnGap','gridRowGap',
    'fontFamily','fontSize','fontWeight','lineHeight',
    'color','letterSpacing','textAlign',
    'backgroundColor','borderTop','borderRight','borderBottom','borderLeft',
    'borderRadius','boxShadow','opacity',
    'zIndex','overflow','transform',
  ];

  function extractElement(el, depth = 0) {
    if (depth > maxDepth || el.nodeType !== 1) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < minSize && rect.height < minSize) return;
    const style = getComputedStyle(el);
    const entry = {
      tag: el.tagName.toLowerCase(), id: el.id || null,
      classes: Array.from(el.classList), testid: el.dataset.testid || null,
      rect: { x: Math.round(rect.x*100)/100, y: Math.round(rect.y*100)/100,
              width: Math.round(rect.width*100)/100, height: Math.round(rect.height*100)/100 },
      style: {},
      parentTag: el.parentElement?.tagName?.toLowerCase() || null,
      childIndex: Array.from(el.parentElement?.children||[]).indexOf(el),
    };
    for (const prop of KEY_PROPERTIES) entry.style[prop] = style[prop];
    results.push(entry);
    if (includeChildren) for (const child of el.children) extractElement(child, depth+1);
  }

  const root = document.querySelector(selector);
  if (root) extractElement(root);

  // Portal 扫描（Modal/Drawer/Tooltip 挂载到 body）
  const PORTAL_SELECTORS = [
    '[class*="modal"]','[class*="drawer"]','[class*="tooltip"]',
    '[class*="popover"]','[class*="dropdown"]','[class*="select-dropdown"]',
    '[class*="picker"]','[class*="notification"]',
  ];
  for (const child of document.body.children) {
    for (const ps of PORTAL_SELECTORS) {
      if (child.matches?.(ps) || child.querySelector?.(ps)) { extractElement(child); break; }
    }
  }

  return JSON.stringify(results);
}
```

### Viewport Slicing 降级（无 data-measure 时）
按 500px 高度分片，每片内 `document.querySelectorAll('*')`，元素中心在当前片内 → 提取，按 rect(x,y,w,h) 去重。后备 Portal 扫描。

---

## Step 3: 开发页测量 + 基线存储

与 Step 2 一致。额外：Vite HMR 完成后等 500ms。

```
.omc/screenshots/{task}/
├── proto-baseline.json
├── dev-baseline-v1.json → v2.json → v3.json
└── diffs/diff-v1-v2.json
```

---

## Step 4: 智能匹配（4层回退）

```
L1 Semantic: data-testid === data-testid
L2 Structural: parentTag + childIndex ±1
L3 Spatial: IoU > 0.7 或 (IoU > 0.4 && centerDist < 20px)
L4 antd Group: select → .ant-select, table → thead/tbody, input → .ant-input-affix-wrapper, button → .ant-btn, modal → .ant-modal-content
```

---

## Step 5: 数值 Diff

### 属性阈值
| 类别 | 阈值 |
|:---|:---|
| Layout (w/h/m/p) | ≤ 0.5px |
| Typography (fs/fw) | fs≤0.5px, fw=0 |
| LineHeight | ≤1px (排除 RENDERING_ARTIFACT) |
| Color | CIEDE2000 ΔE<3; 黑白灰 CIE94 交叉验证 |

### Diff 优先级: P0(布局>10px) → P1(ΔE>5,fs>1px) → P2(m/p>2px,br>2px) → P3(≤0.5px,跳过)

### 继承属性检测（R6）
子元素 color 不对 → 先查父级值。双方都继承 → 差异在上层 → 修父级一条替代 N 条。可继承属性: color, font-*, line-height, letter-spacing, text-align。

### CSS 变量风格匹配（R6）
原型用 var(--xxx) → 生成也用；原型用 SCSS token → 生成用 $；原型混合 → 保持。

---

## Step 6: Token 匹配

```
Diff值 → 反向映射表 → 精确/±1px模糊/ΔE<3 → token变量 → darken衍生 → untokenized+TODO
```

---

## Step 7: SCSS 生成（四遍迭代）

```
Pass 1 Layout (display/position/w/h/m/p/flex/grid/gap)
Pass 2 Typography (font-*/color/lh/ls)
Pass 3 Decoration (border-*/br/shadow/bg/opacity)
Pass 4 Polish (残余/交互态/z-index)
```

### 最少属性原则（R7）
默认值不写: display:block, position:static, visibility:visible, opacity:1, flex-direction:row。父级定义 → 子元素不重复。

### DOM 嵌套层级生成（R6）
从 dev DOM 树生成嵌套 SCSS。BEM → `&__element`; CSS Modules → `.className`; antd外层 → `:global(.ant-xxx)`; antd内部 → 不生成。

### 交互态测量
hover(puppeteer_hover+200ms) / active(mousedown) / focus(focus-visible) / disabled([disabled])。每种独立 before/after diff。

### 写入保护
cp backup → 写 patch → HMR验证 → 差异减少保留 / 不变或增加回滚 / 泄漏检测回滚。上限3次 → BLOCKED。

---

## Step 8: 质量门禁

```bash
npx stylelint --fix <target> && npx sass --no-source-map <target> && npx tsc --noEmit && npm run build
```

---

## 验收标准

- [ ] Layout 像素差 ≤ 0.5px
- [ ] 全部颜色 ΔE < 3
- [ ] fontSize 精确匹配
- [ ] stylelint + SCSS + tsc + build pass
- [ ] Token 变量使用（无硬编码）
- [ ] 交互四态已还原
- [ ] 三态 UI 覆盖
- [ ] 无 ORPHAN 元素

---

## 常见失败模式

| # | 症状 | 对策 |
|:---|:---|:---|
| 1 | 匹配率<30% | 停止，确认布局 |
| 2 | 大量untokenized | 原始值+TODO |
| 3 | ΔE震荡 | 取最低版本 |
| 4 | antd版本不匹配 | 检查package.json |
| 5 | transition干扰 | 注入冻结CSS |
| 6 | 登录丢失 | 告知Human |
| 7 | chrome-devtools断线 | 告知Human |
| 8 | patch被覆盖 | 检查specificity |
| 9 | 图标颜色误报 | 过滤svg/img |
| 10 | 字体渲染假阳性 | 同字体族+lh≤2px忽略 |

---

## 关键教训

1. 截图对比是死路 — LLM 看不出 2px 差异
2. 首次测量不稳 — 丢弃第一次
3. Portal 不能漏 — Modal 挂载到 body 必须单独扫描
4. ΔE 双算法 — CIEDE2000 对黑白灰盲区
5. 仅输出差异 — 重写 SCSS = 引入新 bug
6. 回滚上限 3 次
7. 跨组件泄漏检测
8. 继承属性上提 — 修父级一条替代 N 条
9. Token 从原型反推 — 不是项目先定义
10. 能 div 就 div — 不盲目用 antd
