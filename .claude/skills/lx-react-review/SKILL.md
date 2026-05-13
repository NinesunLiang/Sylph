---

name: lx-react-review

version: v4.0.0

description: "React/Next.js 及前端框架代码审查：渲染性能、Hooks 规则、组件设计、状态管理、TypeScript 质量。适用于 React/Vue/Svelte 等现代前端项目。"

when_to_use: "Use after writing React/Next.js components. Trigger: 'react review', 'component review', 'check react', 'review component'."

model: sonnet

argument-hint: "[file path, component name, or directory]"

paths:

 - "*.tsx"

 - "*.jsx"

 - "*.ts"

harness_version: ">=1.1.0"
role: "React/Next.js code quality reviewer — component patterns, hooks, performance"
execution_mode: stepwise

triggers:
  - "/lx-react-review"
  - "react review"
---

# React/Next.js 代码质量审查

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析审查目标组件|
|context_collector | `../../nodes/context_collector.md` | 收集框架/版本/项目惯例|
|scanner | `../../nodes/scanner.md` | 按前端质量规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | P0/P1 问题自动修复|
|verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证|
|report_generator | `../../nodes/report_generator.md` | 审查报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 审查阶段行为约束 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 审查目标定义|
|severity | `../../schemas/atomic/severity.yaml` | P0-P3 严重度分级|
|finding | `../../schemas/atomic/finding.yaml` | 审查问题发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 审查报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 审查判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长审查会话的上下文总结 |

### 状态机
本 skill 使用**私有 scan→fix→re-scan 循环**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [collect_context → scan → fix → re-scan] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用审查阶段行为约束。

```bash
e
p
'"react"' package.json 2>/dev/null # 缺失 → "不适用"
```

### Step 1: 解析审查目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 过滤：保留 `*.tsx`、`*.jsx`。排除：`*.test.tsx`、`*.test.jsx`、`*.stories.tsx`、`*.spec.tsx`、`*.d.ts`、`node_modules/`、`.next/`、`dist/`、`build/`

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：React/Next.js 版本、Router 类型（App/Pages）、状态管理库（zustand/SWR/react-query）、Server/Client Component 模式、性能优化模式、错误处理模式、项目规范（react-style-guide.md）、已知问题模式（claude-next.md）。

### Step 3: 六类别并行扫描
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的规则集：
**类别 A — 渲染性能（4 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| A1 | 组件内创建新对象/数组作为 props | P1 | AST grep: `<$COMP $PROP={{$$$}}` 或 `$PROP={[$$$]}` || A2 | 大列表渲染无虚拟化（>50 项） | P1 | 检查 `.map(` 渲染列表长度，无 react-virtual || A3 | 缺少 React.memo 的频繁 re-render 组件 | P2 | 分析 props 变化频率 || A4 | useMemo/useCallback 依赖项过多（>5 个） | P2 | AST grep: `useMemo($FN, [$$$DEPS])` → 计算数量 |
**类别 B — Hooks 规则（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| B1 | useEffect 缺少必要依赖 | P0 | AST grep: `useEffect($FN, [$$$DEPS])` → 分析闭包捕获 vs 声明依赖 || B2 | useEffect 未返回清理函数 | P0 | AST grep: `useEffect` 内有 addEventListener/setInterval → 检查 return cleanup || B3 | 条件调用 hooks | P0 | AST grep: `if ($COND) { $$$BODY }` 内含 `use` 前缀函数 |
**类别 C — Next.js 最佳实践（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| C1 | Client Component 含可提升到 Server 的逻辑 | P1 | 检查 `'use client'` 文件纯数据获取/静态渲染 || C2 | 未使用 `next/image` 替代 `<img>` | P1 | AST grep: `<img ` → 应使用 `<Image>` || C3 | 未使用 `next/link` 替代 `<a>` | P1 | AST grep: `<a href="/"` → 内部链接应用 `<Link>` |
**类别 D — 状态管理（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| D1 | 在渲染路径中直接修改 state | P0 | AST grep: 对 useState 返回变量直接赋值 || D2 | prop drilling 超过 3 层 | P1 | 追踪 prop 传递层数 || D3 | 多个 useState 可合并为 useReducer（>4 个相关联） | P2 | 计算 `useState` 调用数 |
**类别 E — 组件设计（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| E1 | 组件超过 200 行 | P1 | 计算组件函数体行数 || E2 | key 使用数组 index 且列表可增删排序 | P1 | AST grep: `.map(($ITEM, $IDX) =>` → 检查 `key={$IDX}` || E3 | 缺少 ErrorBoundary（页面级组件） | P1 | 检查 `app/` 下页面是否有 `error.tsx` |
**类别 F — TypeScript 质量（2 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| F1 | Props 使用 `any` 类型 | P1 | AST grep: `$PROP: any` 或 `Props = any` || F2 | 事件处理器缺少类型标注 | P2 | AST grep: `on$EVENT={($E) =>` → 检查类型标注 |

### Step 4: 误报排除
**误报场景**：在注释或字符串中、第三方库 API 要求的模式（如 `style` prop）、有 `// eslint-disable` 且理由合理、Server Component 文件（无 `'use client'`）中的 hooks 类规则不适用、已经使用 `React.memo` 或 `useMemo` 包裹的引用（A1 类）、`useRef` 返回值作为 useEffect 依赖的误报（B1 类）。

### Step 5: 生成改进建议
对每个真阳性问题：位置（file:line）+ 问题本质 + 修改建议（含代码示例）。排序：P0 → P1 → P2 → P3。

### Step 6: Auto-Fix（P0 + P1）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略：
| 规则 | 修复模板|
|------|---------|
|B1 useEffect 依赖 | 添加缺失依赖；若依赖为对象/数组 → 用 useMemo 包裹|
|B2 未清理副作用 | 添加 `return () => { cleanup }`|
|B3 条件 hooks | 重构为无条件调用 + 条件逻辑在 hook 内部|
|C2 img → Image | 替换为 `import Image from 'next/image'` + `<Image>`|
|C3 a → Link | 替换为 `import Link from 'next/link'` + `<Link>`|
|D1 直接修改 state | 替换为 setter 函数调用|
|E2 index key | 替换为稳定的唯一标识（`item.id`）|
|F1 any 类型 | 使用 LSP hover 推断实际类型并替换|
|A1 内联对象 props | 提取到组件外 const 或 useMemo 包裹|
|E3 缺 ErrorBoundary | App Router → 创建 `error.tsx` |\|

### Step 6.5: Re-scan 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。重新执行 Step 3 的全部规则，输出 before/after 对比表。若有 LSP → 执行 `lsp_diagnostics` 检查 TypeScript 错误。

### Step 6.7: 经验沉淀
成功修复 P0/P1 后，自动追加到 `.claude/claude-next.md`：

```markdown
##
[React Review 反哺] {规则号} {问题简述}- **文件**: `{file:line}` - **问题**: {问题描述} - **改进**: {修复方式}- **来源**: lx-react-review auto-fix - **严重度**: {P0 🔴 / P1 🟠}

```

### Step 7: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与升级路径
| 场景 | 恢复动作|
|------|---------|
|re-scan 发现修复引入新类别问题 | 回退本次修复 → 标记原始问题 + 新问题为 blocked|
|git 不可用 | 回退到 `$ARGUMENTS` 指定的文件列表扫描|
|react-rules.md 缺失 | AI 使用通用前端规则执行扫描|
|react-style-guide.md 缺失 | 使用本 Skill 内置规范，降级通知用户|
|2 次修复失败 + 根因不明 | 升级至 `/lx-debug-spec`|
|AST grep 不支持 TSX 模式 | 回退到 grep + readFile 手动匹配|
|LSP 无响应或超时 | 回退到 grep + readFile 手动提取类型签名 |\|

## 中止条件- 过滤后无 React 文件 → "无 React 变更"报告- 非 React 项目（无 react 依赖在 package.json）→ "不适用"- 全部命中为误报 → "通过"报告- 待确认项超过 5 个 → 暂停，请求用户输入

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|skill 不可用 | Invoke lx-react-review | 用 references/checklists/ 直接审查，标注 [降级审查]|
|组件 >200 行 | 全量审查 | 只审查 hooks 规则和 state 管理（最高风险）|
|P0 auto-fix 破坏功能 | 自动修复 | 回退，改为只报告不修复，让用户决定 |


