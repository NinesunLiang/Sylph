---

name: lx-web-perf

version: v4.0.0

description: "Web 性能审查：Bundle 分析 + Web Vitals 阈值 + Next.js 优化 + 渲染性能 + 网络性能 + 资产优化。6 大类别 24 条规则。适用于 React/Next.js 前端项目。"

when_to_use: "Use after building frontend features or before deployment. Trigger: 'perf check', 'web perf', 'performance audit', 'bundle check', 'web vitals', 'lighthouse check'."

model: sonnet

argument-hint: "[file path, component name, route, or directory]"

paths:

 - "*.tsx"

 - "*.ts"

 - "*.jsx"

 - "*.js"

 - "next.config.*"

 - "package.json"

harness_version: ">=1.1.0"
role: "Web performance auditor — bundle analysis, Web Vitals, Next.js optimization"
execution_mode: stepwise

triggers:
  - "/lx-web-perf"
---

# Web 性能审查

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 解析性能审查目标|
|context_collector | `../../nodes/context_collector.md` | 收集 Bundle/配置/项目惯例|
|scanner | `../../nodes/scanner.md` | 按 6 类别 24 条规则扫描|
|auto_fixer | `../../nodes/auto_fixer.md` | P0/P1 问题自动修复|
|verifier | `../../nodes/verifier.md` | 修复后 re-scan 验证|
|report_generator | `../../nodes/report_generator.md` | 性能审查报告|
|behavior_rules | `../../nodes/behavior_rules.md` | 审查阶段行为约束|
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 审查目标定义|
|severity | `../../schemas/atomic/severity.yaml` | 性能问题严重度|
|finding | `../../schemas/atomic/finding.yaml` | 性能问题发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 性能审查报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 审查判定 |

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
加载 `@../../nodes/behavior_rules.md`，应用审查阶段行为约束。

```bash
e
p
'"next"\|"react"' package.json 2>/dev/null # 缺失 → "不适用"
```

### Step 1: 解析审查目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 过滤：保留 `*.tsx`、`*.ts`、`*.jsx`、`*.js`、`next.config.*`、`package.json`。排除：`node_modules/`、`.next/`、`dist/`、`*_test.*`、`*.stories.*`

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：Next.js 版本、构建配置（next.config.js）、现有 Bundle 分析数据、已知性能问题（claude-next.md）。

### Step 3: 六类别并行扫描
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的规则集：
**类别 A — Bundle 分析（5 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| A1 | 单文件 >200KB（gzip 后） | P0 | 检查 .next/static/chunks/ 文件大小 || A2 | 未使用的依赖导入 | P1 | grep import 检查是否使用 || A3 | 大型库未使用 tree-shaking 版本 | P1 | grep `lodash`（应 `lodash-es`） || A4 | 重复包版本 | P2 | `npm ls` 检查重复 || A5 | Source Map 生产环境未禁用 | P0 | 检查 next.config.js `productionBrowserSourceMaps` |
**类别 B — Web Vitals（4 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| B1 | LCP >2.5s（ Largest Contentful Paint） | P0 | 检查 Lighthouse 报告或 `reportWebVitals` || B2 | CLS >0.1（Cumulative Layout Shift） | P1 | 检查无尺寸图片/动态内容 || B3 | INP >200ms（Interaction to Next Paint） | P1 | 检查重渲染/长任务 || B4 | FCP >1.8s（First Contentful Paint） | P2 | 检查首屏渲染阻塞 |
**类别 C — Next.js 优化（5 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| C1 | 未使用 `next/image` | P1 | grep `<img ` 检查是否用 `<Image>` || C2 | 未使用 `next/link` 做内部导航 | P1 | grep `<a href="/"` 检查内部链接 || C3 | 未使用动态导入（大组件） | P2 | grep 大组件检查 `next/dynamic` || C4 | getServerSideProps 未缓存 | P1 | grep `getServerSideProps` 检查缓存策略 || C5 | 未使用 ISR（静态可缓存页面） | P2 | grep `getStaticProps` 检查 revalidate |
**类别 D — 渲染性能（4 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| D1 | 不必要的 re-render（缺 memo） | P1 | 检查频繁更新组件缺 React.memo || D2 | 大列表无虚拟化 | P0 | grep `.map(` 渲染列表检查虚拟化 || D3 | useEffect 依赖不稳定引用 | P1 | 检查依赖含对象/数组字面量 || D4 | 同步阻塞渲染（长任务） | P2 | 检查复杂计算无 Web Worker |
**类别 E — 网络性能（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| E1 | 请求瀑布（串行 API 调用） | P1 | 检查 useEffect 链式 fetch || E2 | 未使用 HTTP/2 多路复用 | P2 | 检查服务器配置 || E3 | 未预连接关键域 | P2 | grep `<link rel="preconnect">` |
**类别 F — 资产优化（3 条）**| # | 规则 | 严重度 | 检查方式 ||---|------|--------|---------|| F1 | 图片未优化（未用 WebP/AVIF） | P1 | grep 图片扩展名 || F2 | 字体文件未子集化 | P2 | 检查字体文件大小 || F3 | 未使用 CDN 缓存策略 | P1 | 检查 Cache-Control 头 |

### Step 4: 误报排除
**误报场景**：开发环境代码（`process.env.NODE_ENV === 'development'`）、Storybook/测试文件、第三方库要求的模式、已有性能优化但检测工具未识别。

### Step 5: 生成改进建议
对每个真阳性问题：位置 + 问题本质 + 修改建议 + 预期性能提升。排序：P0 → P1 → P2 → P3。

### Step 6: Auto-Fix（P0 + P1）
加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略：
| 规则 | 修复模板|
|------|---------|
|A1 单文件过大 | 拆分为动态导入（`next/dynamic`）|
|A5 Source Map 未禁用 | 设置 `productionBrowserSourceMaps: false`|
|C1 未用 next/image | 替换为 `<Image>` + width/height|
|C2 未用 next/link | 替换为 `<Link>`|
|D2 大列表无虚拟化 | 添加 `react-window` 或 `@tanstack/virtual`|
|E1 请求瀑布 | 改为并行 `Promise.all()`|
|F1 图片未优化 | 转换为 WebP/AVIF 格式 |

### Step 6.5: Re-scan 验证
加载 `@../../nodes/verifier.md`，传入 `fix_record[]` + 原始 `finding[]`。重新执行 Step 3 的全部 24 条规则。

### Step 7: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。

## 错误恢复与中止条件- 无 React/Next.js 依赖 → "不适用"- 过滤后无前端文件 → "无前端变更"报告- 全部命中为误报 → "通过"报告- 待确认项超过 5 个 → 暂停，请求用户输入

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|Lighthouse 不可用 | CI 性能测试 | 静态分析 Bundle + 渲染路径，标注 [静态分析-无Lighthouse]|
|Bundle 分析工具缺失 | bundle-analyzer | ls -lh dist/ 估算，标注 [估算]|
|Web Vitals 无法测量 | 真实用户数据 | 提供优化建议，不给量化分数，标注 [无法测量] |


