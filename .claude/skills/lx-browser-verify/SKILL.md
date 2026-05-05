---

name: lx-browser-verify

version: v4.0.0

description: "Browser visual verification & acceptance testing via Playwright. 5 categories, 24 check items covering multi-resolution screenshots, visual regression, interactive flows, cross-browser checks, responsive layout, and dark mode verification."

when_to_use: "Use after frontend implementation to visually verify rendering. Trigger: 'browser verify', 'visual check', 'screenshot check', 'visual regression', 'responsive verify', 'browser test'."

model: sonnet

argument-hint: "[URL, component name, page route, or flow description]"

paths:

 - "*.tsx"

 - "*.jsx"

 - "*.test.ts"

 - "*.spec.ts"

 - "playwright.config.*"

 - "*.css"

harness_version: ">=1.1.0"

---

# Browser Visual Verification

## 原子化声明
> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|target_resolver | `../../nodes/target_resolver.md` | 从参数/git diff 解析验证目标|
|context_collector | `../../nodes/context_collector.md` | 收集 Playwright 配置和基线|
|scanner | `../../nodes/scanner.md` | 按 5 类别 24 项扫描|
|verifier | `../../nodes/verifier.md` | 截图对比验证|
|report_generator | `../../nodes/report_generator.md` | 验证报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 验证阶段行为约束 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|scan_target | `../../schemas/atomic/scan_target.yaml` | 验证目标定义|
|severity | `../../schemas/atomic/severity.yaml` | P0-P3 视觉问题分级|
|finding | `../../schemas/atomic/finding.yaml` | 视觉问题发现项|
|scan_report | `../../schemas/atomic/scan_report.yaml` | 验证报告|
|fix_record | `../../schemas/atomic/fix_record.yaml` | 修复记录|
|verdict | `../../schemas/atomic/verdict.yaml` | 验证判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 各 Step 输出格式统一|
|上下文守卫 | `../../task_sys/context_guard.md` | 长验证会话的上下文总结 |

### 状态机
本 skill 使用**私有 scan→verify 流程**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [scan → verify → report] → done

### 私有节点
本 skill 无私有节点。

---

## 执行流程

### Step 0: 入口检查
无参数时加载 `@../../nodes/interactive_prompt.md`，进入引导式问答。
加载 `@../../nodes/behavior_rules.md`，应用验证阶段行为约束。

```bash
e
p
'"playwright"' package.json 2>/dev/null # 缺失 → "不适用"
```

### Step 1: 解析验证目标
加载 `@../../nodes/target_resolver.md`，传入 `$ARGUMENTS`。- 若 $ARGUMENTS 为 URL → 直接使用- 若为组件名 → 定位组件文件，查找使用位置/路由- 若为页面路由 → 构建完整 URL- 若为空 → 从 `git diff HEAD` 提取变更的 `*.tsx`/`*.jsx`/`*.css` 文件，推断受影响的路由/页面

### Step 2: 收集项目上下文
加载 `@../../nodes/context_collector.md`，收集：Playwright 配置（playwright.config.*）、视觉基线（.claude/visual-baselines/ 目录）、开发服务器地址、已知视觉问题（claude-next.md）。

### Step 3: 五类别验证扫描
加载 `@../../nodes/scanner.md`，传入 `scan_target` + 本 skill 的验证规则：
**类别 A — 多分辨率截图（5 项）**| # | 检查项 | 严重度 | 验证方式 ||---|--------|--------|---------|| A1 | 桌面端（1920px）渲染正确 | P0 | Playwright 截图 + 基线对比 || A2 | 平板端（768px）渲染正确 | P1 | Playwright 截图 + 基线对比 || A3 | 移动端（375px）渲染正确 | P0 | Playwright 截图 + 基线对比 || A4 | 超宽屏（2560px）无布局断裂 | P2 | Playwright 截图检查 || A5 | 截图无空白/遮挡 | P0 | 检查截图完整性 |
**类别 B — 视觉回归（5 项）**| # | 检查项 | 严重度 | 验证方式 ||---|--------|--------|---------|| B1 | 与基线像素差异 <3% | P1 | Playwright toHaveScreenshot || B2 | 无意外颜色变化 | P1 | 像素对比检查 || B3 | 无布局偏移（CLS <0.1） | P0 | Web Vitals 检查 || B4 | 字体渲染一致 | P2 | 视觉对比检查 || B5 | 动画/过渡效果正常 | P3 | 截图序列检查 |
**类别 C — 交互式流程（5 项）**| # | 检查项 | 严重度 | 验证方式 ||---|--------|--------|---------|| C1 | 核心用户路径可完成 | P0 | Playwright 交互流程测试 || C2 | 按钮/链接可点击 | P0 | Playwright click 检查 || C3 | 表单输入/提交正常 | P1 | Playwright fill/submit 检查 || C4 | 弹窗/下拉/菜单正常 | P1 | Playwright 交互检查 || C5 | 加载/错误状态正确显示 | P2 | Playwright 状态检查 |
**类别 D — 响应式布局（5 项）**| # | 检查项 | 严重度 | 验证方式 ||---|--------|--------|---------|| D1 | 无水平滚动条（移动端） | P1 | Playwright 检查 overflow || D2 | 导航菜单正确折叠 | P1 | 截图检查 || D3 | 图片/媒体正确缩放 | P2 | 截图检查 || D4 | 网格/弹性布局正确重排 | P1 | 截图对比 || D5 | 触摸目标 ≥44x44px | P2 | Playwright boundingBox 检查 |
**类别 E — 暗色模式（4 项）**| # | 检查项 | 严重度 | 验证方式 ||---|--------|--------|---------|| E1 | 暗色模式可切换 | P1 | Playwright 主题切换检查 || E2 | 文字可读（对比度 ≥4.5:1） | P0 | Playwright 颜色对比检查 || E3 | 图标/图片在暗色背景下可见 | P1 | 截图检查 || E4 | 无白色背景泄漏 | P1 | 截图检查 |

### Step 4: 误报排除
**误报场景**：基线截图过期、动态内容（时间/随机数）导致像素差异、浏览器渲染引擎差异（Chromium vs Firefox vs WebKit）、CSS 动画/过渡中间帧截图。

### Step 5: 输出报告
加载 `@../../nodes/report_generator.md`，传入 `scan_report` + `verdict`。
**✅ 通过** / **⚠️ 需改进** / **⏭️ 无验证目标**：按需输出对应报告（含截图证据、before/after 对比表、blocked 项）。

## 错误恢复与中止条件- 无 Playwright 依赖 → "不适用"- 开发服务器无法启动 → "受阻"报告- 过滤后无可验证目标 → "无验证目标"报告- 全部命中为误报 → "通过"报告- 待确认项超过 5 个 → 暂停，请求用户输入

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|Playwright 不可用 | 浏览器自动化 | 提供手动验收步骤，生成 checklist 给用户|
|截图对比失败 | 视觉验证 | 标注差异区域，由用户确认是否可接受|
|页面加载超时 | 等待 | 重试一次，仍失败则记录"[加载超时]" |
