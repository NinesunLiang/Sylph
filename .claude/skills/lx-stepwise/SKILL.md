---
name: lx-stepwise
version: v1.0.0
description: 逐步攻坚模式 — 高难度 bug 单步推进，每步需验证，不可跳过。与 lx-race 互补。
category: infrastructure
type: orchestrator
execution_mode: stepwise
enabled_by_default: true
harness_version: ">=6.3.0"
status: stable
role: "Stepwise debugger — serial deep-dive, each step verified"
evidence_level: L3
triggers:
  - "stepwise"
  - "single step"
  - "deep debug"
  - "step by step"
when_to_use: "Use for high-difficulty serial debugging: unknown root cause, cross-module (>3 files), failed prior fixes (2+), complex state machines or concurrency. Auto-routed by goal/ghost, not manually invoked."
nodes:
  - behavior_rules          # 自洽检查 + 3轮上限
  - target_resolver         # 解析分析目标
  - context_collector       # 收集项目上下文
  - scanner                 # Step 2 定位扫描
  - execute_node            # Step 4 修复执行
  - verifier                # 每步验证
  - a_terminal              # AC 验收标准
  - b_terminal              # 验收执行
  - gate_checker            # Step 3 方案门禁
schemas:
  - atomic/scan_target
  - atomic/finding
  - atomic/verdict
  - atomic/gate_result
---
# lx-stepwise — 逐步攻坚模式

基础机制，goal/ghost 自动路由。与 lx-race 互补：
- **lx-race**: 快速并行处理简单同构任务
- **lx-stepwise**: 串行逐步处理高难度 bug，每步验证

## 触发条件

| 条件 | 说明 |
|------|------|
| 根因不明 | 不知道 bug 在哪里 |
| 跨模块 | >3 文件 |
| 之前失败过 | 2 次以上修复失败 |
| 复杂逻辑 | 状态机/并发 |
| 安全相关 | 影响 CAPTCHA/permission/敏感文件 |

## 执行协议

```
Step 1: 隔离 — 最小可复现用例，确认 bug 存在
  → 验证: 复现脚本 exit code ≠ 0
Step 2: 定位 — scanner 扫描 + 二分法，找到根因 file:line
  → 验证: 根因假设可证伪 (有 file:line 证据)
Step 3: 方案 — 修复方案 + 影响分析
  → 验证: 方案经 gate_checker 审核或 self-review 通过
Step 4: 修复 — 单文件单修改，最小变更
  → 验证: 复现脚本 exit 0 + 回归测试通过
Step 5: 加固 — 添加测试，确保同类 bug 不再漏过
  → 验证: 新增测试覆盖根因路径
```

## 路由规则

```
任务到达
  ├─ 简单 + 同构 + 独立子任务 → lx-race（并行）
  └─ 复杂 + 根因不明 + 跨模块 → lx-stepwise（串行）
```

## 硬约束

- 不可跳过 Step（跳过一步 → 自行返回上一步）
- 每 Step 完成必须写验证证据 (file:line 或 命令输出)
- 3 轮上限适用（behavior_rules §修复上限）
- Step 3 涉及治理文件时触发 CAPTCHA

## 降级策略

| 场景 | 路径 |
|------|------|
| Step 验证失败 | 回到上一步重新执行 |
| 3轮上限触发 | 标记 blocked，升级 lx-root-cause-analysis |
| 子步骤无法完成 | 标注 [blocked]，输出当前证据 |
