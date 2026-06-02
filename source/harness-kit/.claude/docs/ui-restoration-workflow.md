# 前端组件还原流水线 v7.0.0 — Production Grade

> 从原型到生产就绪的完整 React 组件。CSS 视觉 + 响应式 + DOM 结构 + 内部状态管理。
> 覆盖「除业务逻辑以外」的全部前端开发工作。

──────────────────────
## 架构总览

```
                    Source Adapters
  Figma API ──────→ Figma Adapter（节点树 → computed-like）
  Chrome MCP ─────→ React Prototype Adapter（DOM + CSSOM + Fiber + Portal）
  HTML URL ──────→ HTML Prototype Adapter（DOM + CSSOM + 语义推断）
                         │  Unified Measurement Graph
                         ▼
┌───────────────────────── Core Engine ──────────────────────────┐
│                                                                 │
│  Layer 1: Visual (CSS)                                         │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Token     │ │Layout     │ │Style     │ │Inheritance       │ │
│  │Extractor │ │Analyzer   │ │Differ    │ │Cleaner           │ │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────┘ │
│                                                                 │
│  Layer 2: Structure (DOM + Responsive)                         │
│  ┌──────────────────┐ ┌───────────────────────────────────────┐ │
│  │Responsive Engine │ │DOM Structure Engine                   │ │
│  │· 3+视口测量      │ │· 语义标签推断 (div→nav/section/article)│ │
│  │· breakpoint推断  │ │· Fiber→组件边界映射                    │ │
│  │· 容器查询生成    │ │· JSX层级生成 (非扁平)                  │ │
│  │· 响应式Token     │ │· Portal/Modal 正确挂载                  │ │
│  └──────────┬───────┘ └───────────────┬───────────────────────┘ │
│             │                         │                          │
│  Layer 3: State (交互 + 表单)         │                          │
│  ┌────────────────────────────────┐   │                          │
│  │State Management Engine         │   │                          │
│  │· 加载态→loading 骨架/Spinner   │   │                          │
│  │· 空态→EmptyState 组件          │   │                          │
│  │· 错误态→ErrorBoundary + retry  │   │                          │
│  │· 交互态→hover/active/focus值   │   │                          │
│  │· 表单状态机→useReducer         │   │                          │
│  │· 提交→loading→success/error    │   │                          │
│  └────────────────┬───────────────┘   │                          │
│                   │                   │                          │
│                   ▼                   ▼                          │
│  ┌──────────────── Component Generator ──────────────────────┐  │
│  │· TypeScript props interface (从 Fiber 推断)                │  │
│  │· State machine stub (useReducer)                          │  │
│  │· Event handler stubs (onClick/onSubmit/onChange)          │  │
│  │· Responsive container (ResizeObserver)                    │  │
│  │· 整合所有 SCSS → className 映射                            │  │
│  └────────────────────┬───────────────────────────────────────┘  │
│                       ▼                                          │
│  ┌──────────┐ ┌──────────────────────────────────────────────┐  │
│  │SCSS Gen  │ │  _variables / _interactions / _breakpoints   │  │
│  │(保留)    │ │  _mixins / _{region}.scss / responsive       │  │
│  └──────────┘ └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         ▼
┌──────────────────── Output ────────────────────┐
│ tokens/_variables.scss                         │
│ tokens/_interactions.scss (交互态变体)          │
│ tokens/_breakpoints.scss (响应式断点)           │
│ styles/_mixins.scss (字体类 + 布局mixin)        │
│ styles/_{region}.scss                          │
│ styles/_{region}-responsive.scss               │
│ components/{Region}.tsx        ← 完整组件      │
│ components/{Region}.types.ts   ← TS 接口       │
│ components/{Region}.states.ts  ← 状态机定义    │
│ components/COMPONENT_MAP.json                  │
└────────────────────────────────────────────────┘
```

──────────────────────
## 四层引擎详解

──────────────────────
## 第一层：Visual Engine（CSS 视觉还原）

保留 v6.0 全部能力。核心不变：

- **Token Extractor**：颜色 ΔE<2 聚类、间距分组、字体复合类、交互态 Token
- **Layout Analyzer**：区域分割、Grid/Flex 检测、叠加检测、Portal 识别
- **Style Differ**：像素 ≤2px、ΔE<3、排版精确匹配
- **Inheritance Cleaner**：300+属性→差异属性、可继承白名单
- **SCSS Generator**：极简 div 优先、零裸值、Specificity≤2

13 条测量陷阱防御 + 交互态残缺标注协议全部保留。

──────────────────────
## 第二层：Structure Engine（DOM + 响应式）

### 2.1 Responsive Engine

#### 多视口测量协议

在 4 个断点分别全量采集：

| 断点 | 宽度 | 典型场景 |
|:---|:---|:---|
| xs | 375px | 手机竖屏 |
| sm | 768px | 平板竖屏 |
| md | 1024px | 平板横屏/小桌面 |
| lg | 1280px | 标准桌面 |

采集维度：
```javascript
// 每视口每个区域采集
{
  geometry: { x, y, width, height },        // 尺寸变化
  layout: { display, flexDirection, flexWrap, gap },  // 布局变化
  visibility: { display, visibility, opacity },       // 显隐
  order: el.offsetParent ? [...el.parentNode.children].indexOf(el) : -1,  // 顺序变化
  gridSpan: { gridColumn, gridRow },        // Grid 跨列变化
  fontScale: fontSize / BASE_FONT_SIZE,     // 字体缩放
  stacking: detectStackingChange(),          // 堆叠→平铺
  menuCollapse: detectMenuCollapse(),        // 导航折叠
}
```

#### Breakpoint 推断

从多视口数据推断：
- **无变化** → 无需断点
- **尺寸变化** → fluid（百分比/rem/clamp）
- **布局变化**（flex-direction 从 row 变 column）→ breakpoint at 变化点
- **显隐变化** → breakpoint at 变化点
- **顺序变化**（grid reorder）→ breakpoint at 变化点

推断结果写入 `tokens/_breakpoints.scss`：
```scss
$breakpoint-sm: 768px;
$breakpoint-md: 1024px;
$breakpoint-lg: 1280px;

// 断点类型
$bp-type-nav-collapse: 768px;   // 导航折叠点
$bp-type-layout-switch: 1024px; // 布局切换点
$bp-type-hide-sidebar: 768px;   // 侧栏隐藏点
```

#### 响应式 SCSS 生成

```scss
// styles/_topbar-responsive.scss
.topbar {
  // 基准：xs (375px)
  padding: $spacing-sm;
  
  @media (min-width: $bp-type-nav-collapse) {
    padding: $spacing-md;
    flex-direction: row;  // 从 column 变 row
  }
}

// 容器查询（现代方案）
.card-grid {
  container-type: inline-size;
  
  @container (min-width: 400px) {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

生成优先级：container query > media query > fluid。如果原型在同一视口内用 container query 布局 → 推断并生成 container query。

### 2.2 DOM Structure Engine

#### 语义标签推断

从扁平 `<div>` 推断正确的 HTML5 语义标签：

| DOM 特征 | 推断语义标签 | 置信度规则 |
|:---|:---|:---|
| 包含 logo + 导航链接，位于页面顶部 | `<header>` | Fiber componentName 含 "Header/Topbar/Navbar" → 高 |
| 包含链接列表（≥3 个 `<a>`），不在 header 内 | `<nav>` | `role="navigation"` 或 class 含 "nav/menu/sidebar" → 高 |
| 独占一行、包含标题+内容块 | `<section>` | Fiber 组件有 children props → 高 |
| 包含独立完整内容单元（卡片/文章预览） | `<article>` | class 含 "card/article/post" → 中 |
| 包含版权/联系方式，位于页面底部 | `<footer>` | componentName 含 "Footer" → 高 |
| 无明确语义信号 | `<div>` | 默认 |

#### JSX 层级生成

不生成扁平 DOM。按测量到的层级关系生成嵌套 JSX：

```tsx
// Bad (v6.0 会生成的)
<div className="page">
  <div className="topbar">...</div>
  <div className="sidebar">...</div>
  <div className="content">...</div>
</div>

// Good (v7.0 生成)
<header className="topbar">
  <nav className="topbar__nav">...</nav>
</header>
<aside className="sidebar">
  <nav className="sidebar__menu">...</nav>
</aside>
<main className="content">
  <section className="content__hero">...</section>
  <section className="content__cards">
    {cards.map(card => <article key={card.id} className="card">...</article>)}
  </section>
</main>
```

#### 重复模式检测

DOM 中同一结构出现 ≥ 2 次 → 识别为列表 → 生成 `.map()` 模式：
- 兄弟元素相同的 className + 层级结构 → `data.map()`
- Fiber 树中同一 componentName 出现 ≥ 2 次 → 组件列表

```tsx
// 检测到 3 个 .card 结构完全相同
// 生成:
{items.map(item => (
  <article key={item.id} className="card">
    <img src={item.image} alt={item.title} />
    <h3>{item.title}</h3>
    <p>{item.description}</p>
  </article>
))}
```

#### Portal 内容挂载

Modal/Drawer/Popover 不在主 DOM 树内。检测后生成：
```tsx
{isOpen && createPortal(
  <div className="modal-overlay">
    <div className="modal-content">...</div>
  </div>,
  document.getElementById('modal-root')!
)}
```

──────────────────────
## 第三层：State Engine（状态管理）

### 3.1 交互态变化系统

从 CSS 测量扩展到组件状态。6 种 CSS 交互态 + 3 种业务态：

| 态 | 触发条件 | 组件行为 | 生成代码 |
|:---|:---|:---|:---|
| **loading** | 数据加载中 | 显示骨架屏/Spinner | `<Skeleton>` 或 `<Spinner>` + `aria-busy="true"` |
| **empty** | 数据为空 | 显示空状态组件 | `<EmptyState icon={...} description="暂无数据" />` |
| **error** | 请求失败 | 显示错误+重试按钮 | `<ErrorState message={...} onRetry={...} />` |
| **hover** | 鼠标悬停 | CSS 变体 | `&:hover { background: $hover-bg; }` |
| **active** | 按下 | CSS + scale | `&:active { transform: scale(0.97); }` |
| **focus** | 聚焦 | outline + ring | `&:focus-visible { outline: ...; }` |
| **disabled** | 禁用 | opacity + cursor | `&:disabled { opacity: 0.5; cursor: not-allowed; }` |
| **submitting** | 表单提交中 | 按钮 loading + 禁用 | `isSubmitting ? <Spinner /> : '提交'` |
| **success** | 提交成功 | 成功提示 + 重置 | `setStatus('success')` → 3 秒后重置 |

### 3.2 表单状态机

检测 `<form>` 元素 → 分析输入字段 → 推断验证规则 → 生成 useReducer 状态机。

#### 表单检测

```javascript
// 注入原型页面
(() => {
  const forms = document.querySelectorAll('form');
  return Array.from(forms).map(form => ({
    id: form.id || form.getAttribute('name'),
    action: form.action,
    method: form.method,
    fields: Array.from(form.querySelectorAll('input, select, textarea')).map(f => ({
      name: f.name,
      type: f.type || f.tagName.toLowerCase(),
      required: f.required,
      placeholder: f.placeholder,
      pattern: f.getAttribute('pattern'),
      minLength: f.getAttribute('minlength'),
      maxLength: f.getAttribute('maxlength'),
      min: f.getAttribute('min'),
      max: f.getAttribute('max'),
      autocomplete: f.autocomplete,
      options: f.tagName === 'SELECT' ? Array.from(f.options).map(o => o.value) : [],
    })),
    submitButton: form.querySelector('button[type="submit"], input[type="submit"]')?.textContent,
    hasFileUpload: !!form.querySelector('input[type="file"]'),
  }));
})()
```

#### 状态机类型定义

```typescript
// components/forms/LoginForm.states.ts (自动生成)

export interface LoginFormValues {
  email: string;
  password: string;
}

export interface LoginFormErrors {
  email?: string;
  password?: string;
}

export type FormStatus = 'idle' | 'submitting' | 'success' | 'error';

export interface LoginFormState {
  values: LoginFormValues;
  errors: LoginFormErrors;
  touched: Record<keyof LoginFormValues, boolean>;
  status: FormStatus;
  errorMessage?: string;
}

export type LoginFormAction =
  | { type: 'SET_FIELD'; field: keyof LoginFormValues; value: string }
  | { type: 'SET_ERRORS'; errors: Partial<LoginFormErrors> }
  | { type: 'SET_STATUS'; status: FormStatus; errorMessage?: string }
  | { type: 'TOUCH_FIELD'; field: keyof LoginFormValues }
  | { type: 'RESET' };
```

#### 表单 useReducer

```typescript
// components/forms/LoginForm.tsx (自动生成，验证逻辑为 stub -- 待实现为可共享 skill)

function loginFormReducer(state: LoginFormState, action: LoginFormAction): LoginFormState {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, values: { ...state.values, [action.field]: action.value } };
    case 'SET_ERRORS':
      return { ...state, errors: { ...state.errors, ...action.errors } };
    case 'SET_STATUS':
      return { ...state, status: action.status, errorMessage: action.errorMessage };
    case 'TOUCH_FIELD':
      return { ...state, touched: { ...state.touched, [action.field]: true } };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

// TODO: 业务逻辑——此 stub 将升级为共享 skill (lx-form-gen)
async function submitLoginForm(values: LoginFormValues): Promise<void> {
  // STUB: 替换为实际 API 调用
  throw new Error('Not implemented');
}
```

#### 验证规则推断

从 HTML5 属性推断验证规则，生成 Yup/Zod schema stub：

```typescript
// 从 <input required type="email" minLength="6" /> 推断:
const loginFormSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址').min(1, '邮箱不能为空'),
  password: z.string().min(6, '密码至少6位').min(1, '密码不能为空'),
});
```

验证规则来源：
- `required` → `.min(1, '...')`
- `type="email"` → `.email()`
- `minlength` → `.min(N)`
- `maxlength` → `.max(N)`
- `pattern` → `.regex()`
- `type="number"` + `min/max` → `.min(N).max(N)`

### 3.3 非表单状态推断

检测无 `<form>` 但有交互的元素：

- **按钮 + 列表** → 推断为「加载更多/刷新」模式 → 生成 `useLoadMore()`
- **搜索输入 + 结果列表** → 推断为「搜索/过滤」模式 → 生成 `useSearch()`
- **Tab 切换** → 检测 `role="tablist"` 或同类元素 → 生成 `useTabs()`
- **展开/折叠** → 检测 `details/summary` 或 toggle 模式 → 生成 `useCollapse()`

──────────────────────
## 第四层：Component Generator（组件生成器）

前三层引擎所有输出 → 组合为一个完整的 `.tsx` 文件。

### 输出示例

```tsx
// components/CardList.tsx — 自动生成，未修改

import { useState, useReducer } from 'react';
import { createPortal } from 'react-dom';
import styles from './CardList.module.scss';

// ═══════════ TYPES (从 Fiber 树推断) ═══════════
export interface CardListProps {
  title?: string;           // 从 Fiber props 提取
  cards?: Card[];           // 从重复 DOM 模式推断
  onCardClick?: (id: string) => void;  // 从 onClick 推断
  loading?: boolean;        // 从未实现但应该有的状态推断
}

interface Card {
  id: string;
  image: string;
  title: string;
  description: string;
  // 从 DOM 结构推断的字段
}

// ═══════════ STATE (交互态推断) ═══════════
type ViewMode = 'grid' | 'list';  // 从原型未实现但常见推断

export function CardList({ title, cards = [], onCardClick, loading = false }: CardListProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ═══════════ RENDER: Loading State ═══════════
  if (loading) {
    return (
      <section className={styles['card-list']} aria-busy="true">
        {title && <h2 className={styles['card-list__title']}>{title}</h2>}
        <div className={styles['card-list__grid']}>
          {[1, 2, 3].map(i => (
            <div key={i} className={styles['card-list__skeleton']} aria-hidden="true">
              <div className={styles['card-list__skeleton-image']} />
              <div className={styles['card-list__skeleton-text']} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  // ═══════════ RENDER: Empty State ═══════════
  if (!cards.length) {
    return (
      <section className={styles['card-list']}>
        {title && <h2 className={styles['card-list__title']}>{title}</h2>}
        <div className={styles['card-list__empty']} role="status">
          <span className={styles['card-list__empty-icon']} aria-hidden="true">📭</span>
          <p>暂无内容</p>
        </div>
      </section>
    );
  }

  // ═══════════ RENDER: Error State ═══════════
  if (error) {
    return (
      <section className={styles['card-list']}>
        {title && <h2 className={styles['card-list__title']}>{title}</h2>}
        <div className={styles['card-list__error']} role="alert">
          <p>{error}</p>
          <button onClick={() => { setError(null); /* TODO: retry fetch */ }}>
            重试
          </button>
        </div>
      </section>
    );
  }

  // ═══════════ RENDER: Normal ═══════════
  return (
    <section className={styles['card-list']} aria-label={title || '卡片列表'}>
      {title && <h2 className={styles['card-list__title']}>{title}</h2>}
      
      <div 
        className={styles['card-list__grid']}
        data-view={viewMode}
        role="list"
      >
        {cards.map(card => (
          <article 
            key={card.id} 
            className={styles['card']}
            role="listitem"
            onClick={() => onCardClick?.(card.id)}
            onKeyDown={(e) => { if (e.key === 'Enter') onCardClick?.(card.id); }}
            tabIndex={0}
          >
            <img 
              src={card.image} 
              alt={card.title}
              className={styles['card__image']}
              loading="lazy"
            />
            <h3 className={styles['card__title']}>{card.title}</h3>
            <p className={styles['card__description']}>{card.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
```

### 生成规则

| 规则 | 说明 |
|:---|:---|
| **CSS Module 导入** | `import styles from './CardList.module.scss'` |
| **语义标签** | 从 DOM Structure Engine 推断，不生成纯 `<div>` |
| **a11y 属性** | `aria-label`、`aria-busy`、`role`、`tabIndex`、`aria-hidden` |
| **键盘导航** | 可点击元素自动加 `onKeyDown` + `tabIndex={0}` |
| **图片 lazy** | 所有 `<img>` 加 `loading="lazy"` |
| **Portal** | `createPortal()` 包裹 Modal/Drawer 内容 |
| **State hooks** | `useState` 用于本地状态，复杂状态用 `useReducer` |
| **Event stubs** | 所有 handler 生成类型签名 + `// TODO: 业务逻辑` |
| **响应式** | 通过 CSS Module class 控制，复杂响应式逻辑加 `useMediaQuery` |

──────────────────────
## 完整流水线（6 Steps）

### Step 0：预检 & 源分析

双源适配：

| 源类型 | 适配器 | 数据来源 | 限制 |
|:---|:---|:---|:---|
| **Figma API** | Figma Adapter | 节点树 -> computed-style 映射 | 需 Figma API Token，Figma 渲染与浏览器有亚像素偏差 |
| **HTML 原型 (URL)** | HTML Prototype Adapter | DOM + CSSOM + 语义推断 | 需可访问 URL，CSSOM 可能受跨域限制 |

公共流程：CSS 框架检测 + CSSOM 去重扫描 + Fiber 组件边界识别（React 原型）或 DOM 结构分析（HTML 原型）。

### Step 1：页面分割 + 语义标注
区域分割后，每个区域标注语义角色（header/nav/main/section/article/aside/footer/form/modal）。

### Step 2：Token 初始化（串行唯一依赖 -- 测量精度基石）

全量扫描原型，抽离所有一致性像素级参数：

| Token 类别 | 提取内容 | 聚类算法 | 精度 |
|:---|:---|:---|:---|
| **颜色** | hex/rgb/hsl 值 | DE < 2 色差聚类 | 去重后 <= 20 色 |
| **间距** | margin/padding/gap | 最近邻聚类 (<=2px 合并) | 标准化到 spacing-xs/sm/md/lg/xl |
| **字体** | font-family/size/weight/line-height | 复合类聚类 | 生成 font-xxx 复合类 |
| **圆角** | border-radius | 等值聚类 | 标准化到 radius-sm/md/lg/full |
| **阴影** | box-shadow | 参数分解聚类 | 标准化到 shadow-sm/md/lg |
| **交互态** | hover/active/focus 变体 | 差异检测 | 生成 interactions.scss |

这是唯一串行步骤。所有后续区域的测量以 Token 为基准，确保跨区域一致性。

### Step 3：多视口测量 + 响应式推断
4 个断点分别测量 → 推断 breakpoint → 生成响应式 SCSS。

### Step 4：并发区域还原
每个区域独立运行完整流水线：
```
测量(单视口基线) → Diff → DOM结构生成 → 语义标签推断 
→ 交互态注入 → 状态机生成 → SCSS生成 → 组件.tsx生成
```

### Step 5：全页复查
同 v6.0。截图对比（>10px 断裂）+ 区域边界衔接 + Portal 验证 + a11y 审计。

### Step 6：质量门禁

- [ ] Stylelint 通过 + TypeScript 编译通过
- [ ] 零裸值（CSS）
- [ ] 无重复继承样式
- [ ] `tokens/` 三个文件完整（variables + interactions + breakpoints）
- [ ] 每区域组件文件完整（.tsx + .types.ts + .states.ts）
- [ ] `COMPONENT_MAP.json` 生成
- [ ] a11y 审计通过（`eslint-plugin-jsx-a11y`）
- [ ] 所有语义 `<div>` 已替换为 HTML5 标签
- [ ] 所有 `.map()` 模式已检测并生成列表组件
- [ ] 表单验证 schema (Zod/Yup) 已生成
- [ ] 每个组件含 loading/empty/error 三态
- [ ] Portal 内容正确挂载

──────────────────────
## 极简主义约束（扩展）

| 原则 | CSS 层 | 组件层 |
|:---|:---|:---|
| **能 div 就 div** | 保留 | div → 语义标签 |
| **复杂才用组件库** | antd 表单/表格 | 推断为 antd 组件？→ 生成 antd `<Form>` |
| **继承优先** | 12 个可继承属性 | 状态管理不重复声明 |
| **不重复** | mixin 复用 | 抽象为自定义 hook |
| **Specificity ≤ 2** | 保留 | — |
| **TypeScript 严格** | — | 所有 props 带类型 |

──────────────────────
## 第五层：Defense Layer（防御层）

> 不在引擎内部加功能——在引擎外围布防。防御层独立存在，引擎不改一行。

```
                    Input Defense (入口哨兵)
                         │
                         ▼
                    Validation Defense (测量质量)
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
     Visual          Structure          State
     Engine           Engine           Engine
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                    Output Defense (生成后门禁)
                         │
                         ▼
                    Rollback Safety (回滚)
```

### 防线 1：Input Defense（入口哨兵）

| 检查点 | 阻断条件 | Action |
|:---|:---|:---|
| 原型可达性 HTTP 200 + < 5s | 不可达 | BLOCKED 全流程 |
| DOM 加载完整性 `readyState === 'complete'` | 3s重试仍失败 | BLOCKED |
| React 版本兼容（`__REACT_DEVTOOLS_GLOBAL_HOOK__`） | 15.x 无 Fiber | BLOCKED |
| CSSOM 可用性 `document.styleSheets.length` | =0 | DEGRADED（跳过去重） |
| 测量可行性 ≥50 个可见元素 rect 非零 | < 50 | 等待 3s → 仍 < 50 → BLOCKED |
| 断点一致性 4 视口中 ≥2 个采集成功 | < 2 | DEGRADED（单视口模式） |
| Fiber 树完整性 ≥10 个 Fiber 节点 | < 10 | DEGRADED（跳过组件识别） |

产物：`DEFENSE_LOG.json`，每项含 status/action/detail。

### 防线 2：Validation Defense（测量质量）

**测量数据进入引擎前，先过数据质量门禁。**

| 检查 | 规则 | 失败处置 |
|:---|:---|:---|
| 颜色异常值 | hex 不含 `#` 或长度 ≠ 7 | `[INVALID_COLOR]` 排除 |
| 尺寸异常值 | w/h < 0 或 > 10000px | 从测量集移除 |
| 排版缺失 | fontSize=0 或 undefined | `[MISSING_TYPO]` 从父继承 |
| 视口内稳定性 | 同视口 3 次测量波动 > 5% | 取中位数，`[UNSTABLE]` |
| 跨视口一致性 | 相邻视口同属性突变 > 50% | `[ANOMALY]` 人工确认 |
| CSS 变量残留 | 值以 `var(--` 开头 | `[UNRESOLVED_VAR]` 降级 |
| 继承污染 | 子元素 95%+ 同父 | 重测父 1 次 |
| z-index 爆炸 | 同区域 10+ 个唯一 z-index | `[Z_INDEX_CHAOS]` DOM 顺序重建 |

产物：`MEASUREMENT_QUALITY_REPORT.json`，含每区域信噪比。

### 防线 3：Output Defense（生成后门禁）

#### 3.1 语法门禁
```bash
npx stylelint "styles/**/*.scss" --max-warnings 0 && \
npx tsc --noEmit && \
npx eslint "components/**/*.tsx" --max-warnings 0 && \
npx eslint "components/**/*.tsx" --rule 'jsx-a11y/*: error'
```
任一失败 → `npx xxx --fix` → 重跑。3 轮 → BLOCKED。

#### 3.2 语义门禁
- 裸值扫描：颜色/间距/字号必须来自 Token → `[NAKED_VALUE]` → 自动替换
- 语义标签：`<div>` 在 header/main 位置 → 自动推断并替换
- a11y 属性：`<img>` 缺 `alt` / `<button>` 缺 label → `[A11Y_GAP]` → 自动补
- 响应式覆盖：非 responsive 文件含 `@media` → 警告
- State 完整性：每组件必须有 loading/empty/error 三态 → `[STATE_GAP]` → 自动补骨架

#### 3.3 回归门禁
生成前跑基线测试 → 生成后重跑 → 新增失败分析：是生成代码引起 → 3 轮修复。非生成引起 → 记录放行。

#### 3.4 性能门禁
SCSS 编译 < 5s / 区域 `.scss` < 200 行 / 组件 `.tsx` < 300 行 / CSS bundle < 50KB gzipped。超标 → 警告不阻断。

### 防线 4：Runtime Defense（运行中）

#### 4.1 自愈协议（3 级）
| 级别 | 触发 | 动作 |
|:---:|:---|:---|
| L1: AutoFix | lint/format/import | 自动修复 → 重跑 → 记录 |
| L2: Degraded | CSSOM 不可读/单视口 | 降级 → 标记 → 继续 |
| L3: Break | 原型崩溃/3 轮失败 | 保存状态 → 中断 → 报告 |

#### 4.2 熔断器
连续 3 次失败 → OPEN（全阻断）→ 冷却 30s → HALF_OPEN（试 1 区域）→ 成功则 CLOSED，失败则 OPEN（冷却 ×2）。按区域粒度独立熔断。

#### 4.3 断点续跑
每区域完成后写 checkpoint → 会话中断/重启时跳过已完成 checkpoint。

#### 4.4 并发安全 — Carror OS 竞争锁/排队机制

参考 Carror OS 的竞争锁模型，所有并发操作通过排队机制协调：

| 锁类型 | 作用域 | 实现 | 说明 |
|:---|:---|:---|:---|
| **全局锁** | Token 初始化 | `.omc/state/locks.json` 排队写入 | 唯一串行步骤，后续所有区域依赖 Token |
| **区域锁** | 单区域还原 | 每个 worker 按区域排队，同一区域不可并行 | 区域间无依赖 → 可并行；同区域串行 |
| **共享锁** | Token/SCSS 读取 | 只读不锁 | 所有 worker 可同时读取已生成的 Token |
| **死锁预防** | 全局 | 锁获取设超时 30s，超时 → 释放并重试（最多 3 次） | 防止 worker 崩溃导致的锁残留 |

排队机制：worker 启动时向 `locks.json` 注册排队序号 → 按序获取全局锁 → 释放后进入区域锁队列 → 完成后注销。

### 防线 5：Rollback Safety（回滚）

#### 5.1 Git 策略
执行前：`git stash && git checkout -b polish/YYYY-MM-DD`。执行后：`git add + commit`。回滚：`git checkout main && git branch -D polish/...`。

#### 5.2 增量模式
同一原型二次运行 → 差异检测（rect 5% 阈值 + ΔE < 3）→ 只跑变化区域。未变化区域直接跳过。

──────────────────────
## 可分发清单

接收方需提供 AGENTS.md 配置段：

```markdown
## 前端还原配置
- 组件库: antd | mui | none
- Token路径: tokens/
- 样式格式: scss | css-modules | tailwind
- 状态管理: react-state | zustand | redux
- 验证库: zod | yup | none
- 原型URL: [URL]
- 管道类型: figma | react-prototype | html-prototype
```


──────────────────────
## 失败模式目录

> 失败用例储存在 .omc/state/ui-restoration-failures/ 目录下，按日期组织。
> 每次流水线执行后，自动将失败模式写入该目录，供后续分析、防御升级和 skill 迭代。

### 已记录失败模式

| 失败模式 | 严重度 | 触发条件 | 处置 | 首次记录 |
|:---|:---:|:---|:---|:---:|
| Figma API 不可达 | HIGH | Token 过期 / API 限频 / 网络不可达 | 切换 HTML Prototype Adapter 降级 | TBD |
| CSSOM 跨域空集 | HIGH | 原型 CSS 通过 link 引用外部样式表 | 跳过 CSSOM 去重，降级为内联样式测量 | TBD |
| Fiber 树为空 | HIGH | 非 React 页面或 React 版本 < 16 | 降级为 DOM 结构分析模式 | TBD |
| 测量波动 > 5% | MEDIUM | 字体加载延迟 / 图片未加载完成 | 重试 3 次取中位数 | TBD |
| Token 聚类漂移 | MEDIUM | 同色系值跨聚类边界 | 人工确认后调整 DE 阈值 | TBD |
| 表单字段推断失败 | LOW | 自定义 input 组件未暴露原生属性 | 生成通用表单骨架，标注 [INFERRED] | TBD |
| Portal 内容缺失 | MEDIUM | Modal 在 DOM 树外不可测量 | 标记 [PORTAL_GAP]，生成占位 | TBD |
| 断点采集不足 | MEDIUM | 4 视口中 < 2 个成功 | 降级为单视口模式 | TBD |

### 失败用例记录格式

每个失败用例记录在 .omc/state/ui-restoration-failures/YYYY-MM-DD-N.json：

```json
{
  "id": "YYYY-MM-DD-N",
  "date": "2026-06-02",
  "mode": "html-prototype",
  "failure": "CSSOM 跨域空集",
  "severity": "HIGH",
  "evidence": "document.styleSheets.length = 0",
  "prototype_url": "https://example.com/prototype",
  "defense_triggered": "Input Defense -> DEGRADED",
  "recovery": "降级为内联样式测量",
  "lesson": "HTML 原型应优先使用内联样式或同域 CSS"
}
```

### 失败模式 -> 防御层映射

每条失败模式映射到 Defense Layer 的具体防线和处置策略，确保防御层随失败模式目录同步演进。

──────────────────────
## 版本

| 版本 | 变更 |
|:---|:---|
| v4.0 | 工作区分割、Token 初始化、并发执行、极简主义 |
| v5.0 | 45+ 篇人类实战——13 条测量陷阱防御 |
| v5.1 | React 原型特殊场景——样式表扫描、fiber 树识别、交互态残缺检测 |
| v6.0 | 双管道架构。CSSOM 去重、Fiber 组件边界识别（3 级判定）、交互态残缺标注协议。15 种失败路由。可独立分发 |
| **v7.0** | **四层引擎——CSS 视觉 + 响应式(4断点+container query) + DOM 结构(语义标签+JSX层级) + 状态管理(loading/empty/error三态+表单useReducer+Zod schema)。完整 .tsx 组件输出。除业务逻辑外全覆盖。** |
| **v7.1** | **第五层 Defense Layer——5 道防线：Input(7项哨兵WARN/DEGRADE/BLOCKED) + Validation(8项数据质量门禁) + Output(语法/语义/回归/性能4类门禁) + Runtime(自愈/熔断/断点续跑/并发安全) + Rollback(git分支+增量模式)。防御层独立于引擎层，不增加引擎复杂度。** |
