# 前端组件还原流水线 — 使用流程指南

> 从 HTML 原型 URL 到生产就绪 React 组件的完整操作流程。
> 跟着这个文档走，每步都有明确的输入、操作和输出。

──────────────────────
## 快速开始（5 分钟）

```bash
# 1. 确认 Puppeteer MCP 可用
# 在 Claude Code 中输入：
puppeteer_navigate url="你的原型URL"

# 2. 如果看到页面加载成功 → 继续
# 如果失败 → 检查 puppeteer MCP 配置
```

──────────────────────
## 完整流程概览

```
Phase 0: 准备 ──→ Phase 1: 测量 ──→ Phase 2: Token ──→ Phase 3: 组件 ──→ Phase 4: 门禁
  确认环境      采集DOM+CSS       提取颜色/间距      生成.tsx/.scss     编译+审查
  配置参数      多视口测量        聚类标准化         状态机stub         截图对比
```

──────────────────────
## Phase 0：准备（1 次性，首次使用）

### 0.1 确认 Puppeteer MCP 已注册

在 Claude Code 中执行：
```
puppeteer_navigate url="https://example.com"
```

如果成功 → 跳过本节。
如果失败 → 在 `.claude/settings.json` 中添加：

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

### 0.2 准备项目

```bash
# 创建输出目录
mkdir -p components tokens styles

# 初始化（如果还没有）
npm init -y
npm install sass typescript @types/react
```

### 0.3 收集用户输入

| 问题 | 默认值 | 说明 |
|:---|:---|:---|
| 原型 URL | 必填 | HTML 原型可访问的 URL |
| 组件库 | none | antd / mui / none |
| 样式格式 | scss | scss / css-modules / tailwind |
| 状态管理 | react-state | react-state / zustand / redux |
| 验证库 | zod | zod / yup / none |
| 已有 Token？ | 否 | 如果已有 tokens/ 目录，跳过 Phase 2 |
| 需要响应式？ | 是 | 4 断点 / 2 断点 / 不需要 |

> **重要**：如果用户已有 Token 文件，询问是否跳过 Phase 2，直接进入组件生成。

──────────────────────
## Phase 1：测量（每次执行必做）

### 1.1 导航到原型

```
puppeteer_navigate url="你的原型URL"
```

**验证**：页面加载成功，控制台无错误。

### 1.2 提取 DOM 结构

```
puppeteer_evaluate script="
(() => {
  const els = document.querySelectorAll('*');
  return Array.from(els).slice(0, 500).map(el => ({
    tag: el.tagName.toLowerCase(),
    id: el.id,
    className: el.className,
    rect: el.getBoundingClientRect(),
    children: Array.from(el.children).map(c => c.tagName.toLowerCase()),
    text: (el.textContent || '').trim().slice(0, 50),
    visible: el.offsetParent !== null,
  }));
})()
"
```

**输出**：`dom-structure.json` — 页面所有元素的标签、位置、层级关系。

### 1.3 提取 CSSOM + Computed Style

```
puppeteer_evaluate script="
(() => {
  // 1. CSSOM — 读取所有样式表
  const cssom = Array.from(document.styleSheets).map(sheet => {
    try {
      return {
        href: sheet.href,
        rules: Array.from(sheet.cssRules || []).map(r => r.cssText),
      };
    } catch(e) {
      return { href: sheet.href, error: 'CORS blocked' };
    }
  });

  // 2. Computed Style — 读取所有可见元素的样式
  const els = document.querySelectorAll('*');
  const computed = Array.from(els).slice(0, 500).map(el => {
    const style = getComputedStyle(el);
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id,
      className: el.className,
      display: style.display,
      position: style.position,
      color: style.color,
      backgroundColor: style.backgroundColor,
      fontSize: style.fontSize,
      fontWeight: style.fontWeight,
      lineHeight: style.lineHeight,
      fontFamily: style.fontFamily,
      margin: [style.marginTop, style.marginRight, style.marginBottom, style.marginLeft],
      padding: [style.paddingTop, style.paddingRight, style.paddingBottom, style.paddingLeft],
      borderRadius: style.borderRadius,
      boxShadow: style.boxShadow,
      gap: style.gap,
      gridTemplateColumns: style.gridTemplateColumns,
      flexDirection: style.flexDirection,
      flexWrap: style.flexWrap,
      opacity: style.opacity,
      visibility: style.visibility,
    };
  });

  return { cssom, computed };
})()
"
```

**输出**：`cssom-data.json` — 所有样式表规则 + 每个元素的 computed style。

### 1.4 区域分割

基于 DOM 结构和布局特征，将页面划分为独立区域：

```
页面
├── header（顶部导航区）
│   ├── logo
│   └── nav-links
├── main（主内容区）
│   ├── hero
│   ├── features（卡片列表）
│   └── cta
└── footer（底部）
    ├── links
    └── copyright
```

**判断依据**：
- `position: absolute/fixed` → 独立层
- `<header>/<footer>/<main>/<nav>/<aside>/<section>` → 语义区域
- `display: grid/flex` 的父容器 → 区域边界
- `margin-top/bottom` 显著变化 → 区域分隔

**输出**：区域列表，每个区域有名称、语义角色、包含的元素列表。

──────────────────────
## Phase 2：Token 提取（首次运行或原型变更时执行）

> 如果用户已有 Token 文件，询问是否跳过此阶段。

### 2.1 提取颜色

```
puppeteer_evaluate script="
(() => {
  const els = document.querySelectorAll('*');
  const colors = new Set();
  Array.from(els).slice(0, 500).forEach(el => {
    const style = getComputedStyle(el);
    [style.color, style.backgroundColor, style.borderColor].forEach(c => {
      if (c && c !== 'transparent' && c !== 'rgba(0, 0, 0, 0)' && !c.startsWith('var(--')) {
        colors.add(c);
      }
    });
  });
  return Array.from(colors);
})()
"
```

**AI 处理**：将颜色值聚类（ΔE < 2 合并），生成 SCSS 变量：

```scss
// tokens/_variables.scss
$color-primary: #4f46e5;
$color-secondary: #6366f1;
$color-text: #1f2937;
$color-bg: #ffffff;
$color-border: #e5e7eb;
```

### 2.2 提取间距

从所有元素的 margin、padding、gap 中提取间距值 → 最近邻聚类（≤2px 合并）：

```scss
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;
```

### 2.3 提取字体

从所有元素的 font-family / font-size / font-weight / line-height 组合中提取 → 复合类聚类：

```scss
// 生成 font-xxx 复合类
.font-heading { font-family: 'Inter', sans-serif; font-size: 24px; font-weight: 700; line-height: 1.2; }
.font-body { font-family: 'Inter', sans-serif; font-size: 16px; font-weight: 400; line-height: 1.5; }
.font-small { font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 400; line-height: 1.4; }
```

### 2.4 提取圆角和阴影

```scss
$radius-sm: 4px;
$radius-md: 8px;
$radius-lg: 12px;
$radius-full: 9999px;

$shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
$shadow-md: 0 4px 6px rgba(0,0,0,0.1);
$shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
```

### 2.5 提取交互态

对比元素的 `:hover`、`:active`、`:focus` 状态与基线状态的差异：

```scss
// tokens/_interactions.scss
.btn-primary {
  background: $color-primary;
  &:hover { background: $color-secondary; }
  &:active { transform: scale(0.97); }
  &:focus-visible { outline: 2px solid $color-primary; outline-offset: 2px; }
}
```

**输出文件**：
```
tokens/_variables.scss      ← 颜色、间距、字体、圆角、阴影
tokens/_interactions.scss   ← 交互态变体
tokens/_breakpoints.scss    ← 响应式断点（Phase 3 后补充）
```

──────────────────────
## Phase 3：组件生成（核心步骤）

### 3.1 多视口测量（如果需要响应式）

对每个断点重复 Phase 1.2-1.3：

| 断点 | 宽度 | 操作 |
|:---|:---|:---|
| xs | 375px | `puppeteer_navigate` + 设置 viewport → 测量 |
| sm | 768px | 同上 |
| md | 1024px | 同上 |
| lg | 1280px | 同上 |

**Breakpoint 推断**：
- 尺寸变化 → fluid（百分比/rem/clamp）
- 布局变化（flex-direction row→column）→ breakpoint
- 显隐变化 → breakpoint
- 无变化 → 无需断点

**输出**：`tokens/_breakpoints.scss`

### 3.2 语义标签推断

将扁平 `<div>` 替换为 HTML5 语义标签：

| DOM 特征 | 推断标签 |
|:---|:---|
| 顶部 + logo + 导航链接 | `<header>` |
| 链接列表（≥3 个 `<a>`） | `<nav>` |
| 标题 + 内容块 | `<section>` |
| 卡片/文章预览 | `<article>` |
| 底部 + 版权信息 | `<footer>` |
| 侧边栏 | `<aside>` |
| 无明确语义 | `<div>` |

### 3.3 生成 SCSS

为每个区域生成 SCSS 文件：

```scss
// styles/_header.scss
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  background: $color-bg;
  border-bottom: 1px solid $color-border;

  &__logo { font-size: 24px; font-weight: 700; }
  &__nav { display: flex; gap: $spacing-md; }
}
```

### 3.4 生成组件

为每个区域生成 `.tsx` 文件：

```tsx
// components/Header.tsx
import styles from '../styles/Header.module.scss';

export interface HeaderProps {
  logo?: string;
  navItems?: { label: string; href: string }[];
}

export function Header({ logo = 'Logo', navItems = [] }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.header__logo}>{logo}</div>
      <nav className={styles.header__nav}>
        {navItems.map(item => (
          <a key={item.href} href={item.href}>{item.label}</a>
        ))}
      </nav>
    </header>
  );
}
```

### 3.5 注入状态管理

为每个组件添加 loading / empty / error 三态：

```tsx
// 在组件顶部添加
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

// 在 return 前添加守卫
if (loading) return <Skeleton />;
if (error) return <ErrorState message={error} onRetry={() => setError(null)} />;
```

### 3.6 表单状态机（如果检测到 `<form>`）

检测表单 → 提取字段 → 生成 useReducer + Zod schema：

```tsx
// components/LoginForm.states.ts (stub)
// TODO: 此 stub 将升级为共享 skill (lx-form-gen)
export type FormStatus = 'idle' | 'submitting' | 'success' | 'error';
export interface FormState { values: Record<string, string>; errors: Record<string, string>; status: FormStatus; }
export type FormAction =
  | { type: 'SET_FIELD'; field: string; value: string }
  | { type: 'SET_STATUS'; status: FormStatus; errorMessage?: string }
  | { type: 'RESET' };
```

──────────────────────
## Phase 4：质量门禁

### 4.1 编译检查

```bash
npx stylelint "styles/**/*.scss" --max-warnings 0
npx tsc --noEmit
```

### 4.2 截图对比

```
puppeteer_screenshot name="before"
# 生成组件后重新导航
puppeteer_screenshot name="after"
```

对比两张截图，检查 >10px 的视觉断裂。

### 4.3 门禁清单

- [ ] Stylelint 通过
- [ ] TypeScript 编译通过
- [ ] 零裸值（颜色/间距/字号来自 Token）
- [ ] 无重复继承样式
- [ ] `tokens/` 三个文件完整
- [ ] 每区域组件文件完整（.tsx + .scss）
- [ ] `<div>` 已替换为语义标签
- [ ] 重复 DOM 模式已生成 `.map()`
- [ ] 每个组件含 loading/empty/error 三态
- [ ] a11y 属性完整（alt / aria-label / role）

──────────────────────
## 失败处理

### 常见失败模式

| 现象 | 原因 | 处理 |
|:---|:---|:---|
| `document.styleSheets` 为空 | CSS 跨域 | 跳过 CSSOM 去重，只用 computed style |
| 测量波动 > 5% | 字体/图片未加载 | 等待 3s 后重试，取中位数 |
| Fiber 树为空 | 非 React 页面 | 降级为 DOM 结构分析 |
| Puppeteer 导航超时 | 页面加载慢 | 增加 timeout 到 30s |
| Token 聚类结果不合理 | 阈值不合适 | 人工调整 ΔE / 间距聚类阈值 |

### 记录失败

每次失败记录到 `.omc/state/ui-restoration-failures/YYYY-MM-DD-N.json`：

```json
{
  "id": "2026-06-02-1",
  "date": "2026-06-02",
  "mode": "html-prototype",
  "failure": "CSSOM 跨域空集",
  "severity": "HIGH",
  "evidence": "document.styleSheets.length = 0",
  "prototype_url": "https://example.com/prototype",
  "defense_triggered": "Input Defense -> DEGRADED",
  "recovery": "降级为内联样式测量"
}
```

──────────────────────
## 输出产物

```
project/
├── tokens/
│   ├── _variables.scss          ← 颜色、间距、字体、圆角、阴影 Token
│   ├── _interactions.scss       ← 交互态变体
│   └── _breakpoints.scss        ← 响应式断点（如有）
├── styles/
│   ├── _mixins.scss             ← 字体类 + 布局 mixin
│   ├── _header.scss
│   ├── _header-responsive.scss  ← 响应式变体（如有）
│   ├── _hero.scss
│   └── _footer.scss
├── components/
│   ├── Header.tsx
│   ├── Header.types.ts
│   ├── Hero.tsx
│   └── Footer.tsx
└── .omc/state/ui-restoration-failures/
    └── 2026-06-02-1.json
```

──────────────────────
## 常见问题

### Q: 已有 Token 文件，需要重新提取吗？
A: 不需要。Phase 2 可跳过，直接进入组件生成。

### Q: 原型不是 React 写的？
A: 没问题。HTML 原型路径不依赖 Fiber 树，通过 DOM + computed style 测量即可。

### Q: 页面需要登录？
A: 先用 Puppeteer 完成登录流程，然后执行测量。

### Q: 只还原部分区域？
A: 在 Phase 1.4 区域分割后，指定要还原的区域列表，其他区域跳过。

### Q: 响应式不需要？
A: 跳过 Phase 3.1，只用单视口（1280px）测量。
