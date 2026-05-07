---

name: lx-style-guide

version: v4.0.0

description: "Tailwind CSS 规范检查 + Design Token 一致性 + 响应式断点验证 + CSS 变量管理。适用于任意 Tailwind 项目。"

when_to_use: "Use after writing frontend styles or components. Trigger: 'style check', 'check styles', 'tailwind review', 'design token check'."

model: sonnet

argument-hint: "[file path, component name, or directory]"

paths:

 - "*.tsx"

 - "*.css"

 - "tailwind.config.*"

 - "*.module.css"

harness_version: ">=1.1.0"

---

# 前端样式规范检查

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析样式检查目标|
|context_collector | `../../nodes/context_collector.md` | 收集 Tailwind 配置/项目惯例|
|scanner | `../../nodes/scanner.md` | 按样式规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | P0/P1 问题自动修复|
|verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证|
|report_generator | `../../nodes/report_generator.md` | 规范检查报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 检查阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 检查目标定义|
|severity | `../../schemas/atomic/severity.yaml` | 规范问题严重度|
|finding | `../../schemas/atomic/finding.yaml` | 规范问题发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 检查报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 检查判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长审查会话的上下文总结 |

### 状态机
本 skill 使用**私有 scan→fix→re-scan 循环**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [scan → fix → re-scan] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用检查阶段行为约束。

```bash
e
p
'"tailwindcss"' package.json 2>/dev/null # 缺失 → "不适用"
```

### Step 1: 解析检查目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 过滤：保留 `*.tsx`、`*.css`、`*.module.css`。排除：`node_modules/`、`.next/`、`dist/`、`*_test.*`、`*.stories.*`

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：Tailwind 配置（tailwind.config.js/ts）、Design Token 定义（CSS 变量/theme 扩展）、项目样式规范（frontend-style-guide.md）、已知问题模式（claude-next.md）。

### Step 3: 六类别并行扫描
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的规则集：
**类别 A — Tailwind 规范（4 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| A1 | 硬编码魔数（非 Token 颜色/间距） | P0 | grep 非 Token 颜色值（`#[0-9a-fA-F]`、`rgb(`） || A2 | 未使用响应式前缀的固定宽度 | P1 | grep `w-\\[.*px\]` 或 `w-[0-9]+` 无 `md:`/`lg:` 前缀 || A3 | 重复样式类（相同 className 出现 ≥3 次） | P2 | 提取所有 className，统计重复 || A4 | 未使用 Tailwind 工具类（内联 style 可替代） | P3 | grep `style={{` 检查是否可用 Tailwind 替代 |
**类别 B — Design Token 一致性（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| B1 | 使用未定义的 CSS 变量 | P0 | grep `var(--.*)` → 检查 :root 或 theme 中是否定义 || B2 | Token 命名不规范（非 kebab-case） | P2 | grep `var(--[A-Z_])` → 应使用 `--color-primary` 而非 `--COLOR_PRIMARY` || B3 | 硬编码 z-index 层级（非 Token） | P1 | grep `z-\\[.*\]` 或内联 `zIndex:` 检查是否使用 Token |
**类别 C — 响应式断点（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| C1 | 缺失移动端适配（仅 sm/md 无前缀） | P1 | 检查组件是否有无前缀（mobile-first）类 || C2 | 断点使用不当（sm 用于大屏布局） | P2 | grep `sm:` 用于布局类属性（grid/flex） || C3 | 隐藏元素未考虑可访问性 | P1 | grep `hidden` 检查是否有 `sr-only` 替代方案 |
**类别 D — CSS 模块/全局样式（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| D1 | 全局样式污染（非 :global 包裹） | P0 | grep 全局 CSS 文件中非模块化选择器 || D2 | CSS Modules 未使用 :export | P2 | 检查 CSS Modules 文件是否导出 Token || D3 | 样式覆盖顺序冲突 | P1 | 检查相同选择器多次定义 |
**类别 E — 性能相关（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| E1 | 过度使用 @apply（>10 行） | P2 | grep `@apply` 检查行数 || E2 | 未使用 content-visibility 优化长列表 | P3 | grep 长列表组件检查 content-visibility || E3 | 大型背景图未使用 image-set | P2 | grep `background-image` 检查 image-set |
**类别 F — 可访问性（2 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| F1 | 颜色对比度低于 WCAG AA | P1 | 检查前景/背景色对比度 || F2 | 焦点样式缺失（:focus 未定义） | P1 | grep 交互元素检查 :focus/:focus-visible |

### Step 4: 误报排除
**误报场景**：在注释/字符串中、有 `/* stylelint-disable */` 且理由合理、第三方库要求的样式、Storybook/测试文件中的样式。

### Step 5: 生成改进建议
对每个真阳性问题：位置（file:line）+ 问题本质 + 修改建议（含代码示例）。排序：P0 → P1 → P2 → P3。

### Step 6: Auto-Fix（P0 + P1）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略：
| 规则 | 修复模板|
|------|---------|
|A1 硬编码魔数 | 替换为 Token（`var(--color-*)` 或 `theme('colors.*')`）|
|B1 未定义 CSS 变量 | 在 :root 或 tailwind.config 中定义|
|C1 缺失移动端适配 | 添加 mobile-first 无前缀类|
|D1 全局样式污染 | 用 `:global()` 包裹或转为 CSS Modules|
|F1 颜色对比度 | 调整颜色至 WCAG AA 标准（≥4.5:1）|
|F2 焦点样式缺失 | 添加 `:focus-visible` 样式 |\|

### Step 6.5: Re-scan 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。重新执行 Step 3 的全部规则。

### Step 7: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件- 无 Tailwind 依赖 → "不适用"- 过滤后无样式文件 → "无样式变更"报告- 全部命中为误报 → "通过"报告- 待确认项超过 5 个 → 暂停，请求用户输入

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|ESLint/Prettier 未配置 | 运行检查 | 用 references/checklists/ 手动检查核心规则|
|项目规则与 references/ 冲突 | 使用内置规则 | 以项目 .eslintrc 为准，标注 [项目规则优先]|
|格式化变更 >30 文件 | 全量格式化 | 只格式化变更文件 |
