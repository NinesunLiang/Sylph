## 原子化声明

> 本 skill 无私有 references，共享能力引用 @../references/oma/。


# lx-stepwise — 逐步攻坚模式

> 基础机制，非可选 skill。goal/ghost 模式自动路由。与 `lx-race` 互补：
> - **lx-race**: 快速并行处理简单同构任务（多 agent 同时认领）
> - **lx-stepwise**: 串行逐步处理高难度 bug（单 agent 逐步推进，每步验证）
> 
> 两种引擎由 goal/ghost 模式自动路由，不直接手动调用。

## 触发条件

当任务满足以下任一条件时，应路由到 stepwise 而非 race：

1. 根因不明（不知道 bug 在哪里）
2. 涉及跨模块/跨域修改（>3 文件）
3. 之前修复尝试失败过（2 次以上）
4. 需要理解复杂状态机或并发逻辑
5. 修改会影响安全门禁（CAPTCHA/permission/敏感文件）

## 执行协议

```
Step 1: 隔离 — 最小可复现用例，确认 bug 存在
  → 验证: 复现脚本 exit code ≠ 0
Step 2: 定位 — 二分法缩小范围，找到根因 file:line
  → 验证: 根因假设可证伪（有 file:line 证据）
Step 3: 方案 — 提出修复方案 + 影响分析（哪些文件/接口受影响）
  → 验证: 方案经 Oracle 审核或 self-review 通过
Step 4: 修复 — 单文件单修改，最小变更
  → 验证: 复现脚本 exit 0 + 回归测试通过
Step 5: 加固 — 添加/更新测试，确保同类 bug 不再漏过
  → 验证: 新增测试覆盖根因路径
```

## 与 lx-race 的路由规则

```
任务到达
  │
  ├─ 简单 + 同构 + 独立子任务 → lx-race（并行）
  │
  └─ 复杂 + 根因不明 + 跨模块 → lx-stepwise（串行）
```

## 硬约束

> **当前: 文档化协议（v1.0），非运行时强制。** 以下约束由 AI 读取 SKILL.md 后自觉遵守。
> 运行时 hook 强制执行（`stepwise-detect.sh`）为 Phase 2 计划，当前依赖 AI 遵循 skill 文档。

- 不可跳过 Step（跳过任何一步 → AI 应自行返回上一步，未完成不得声明 task-done）
- 每 Step 完成必须写验证证据（file:line 或 命令输出）
- 3 轮上限仍适用（铁律 #5）
- Step 3（方案）涉及治理文件时必须触发 pretool-sensitive-edit CAPTCHA

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| Step 验证失败 | 回到上一步重新执行 |
| 3 轮上限触发 | 标记 blocked，升级 lx-root-cause-analysis |
| 子步骤无法完成 | 标注 [blocked]，输出当前证据 |
