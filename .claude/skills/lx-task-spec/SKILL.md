---
name: lx-task-spec
version: v6.0.0
description: "统一任务驱动机制 — 三种模式：light（原 lx-todo，≤3文件快速闭环）、standard（原 lx-task-spec，需精确AC的中等任务）、deep（原 lx-stepwise，高难度串行攻坚）"
harness_version: ">=6.3.0"
status: stable
complexity: intermediate
role: "Unified task engine — light/standard/deep modes for different complexity levels"
execution_mode: stepwise
triggers:
  - "/lx-task-spec"
  - "/lx-todo"
  - "todo"
  - "quick fix"
  - "stepwise"
  - "single step"
  - "deep debug"
  - "step by step"
when_to_use: "Use for any task that isn't a full RPE feature. Light mode: ≤3 files quick fix. Standard mode: needs precise AC, multi-file. Deep mode: unknown root cause, cross-module, failed prior fixes."
argument-hint: "light <desc> | standard <desc> | deep <desc>"
nodes:
  - behavior_rules           # 自洽检查 + 3轮上限 + 范围冻结
  - interactive_prompt       # 无参数时引导
  - target_resolver          # 解析目标
  - context_collector        # 收集上下文
  - scanner                  # 定位扫描
  - auto_fixer               # P0/P1 自动修复
  - execute_node             # 修复执行
  - verifier                 # 每步验证
  - gate_checker             # 方案门禁
  - report_generator         # 报告生成
schemas:
  - atomic/scan_target
  - atomic/finding
  - atomic/fix_record
  - atomic/verdict
  - atomic/gate_result
  - output/acceptance_report
---

# lx-task-spec — 统一任务驱动机制

> 合并自 lx-todo v4.0.0 + lx-task-spec v5.1.0 + lx-stepwise v1.0.0

三种模式，按复杂度路由：

```
            ┌─ light（≤3 文件、单终端、不开 subagent）
任务到达 ───┼─ standard（需精确 AC，>3 文件或需设计）
            └─ deep（根因不明、跨模块、之前失败过）
```

---

## 模式选择

| 特征 | light | standard | deep |
|------|-------|----------|------|
| 原 skill | lx-todo | lx-task-spec | lx-stepwise |
| 触发 | `/lx-todo` / `quick fix` | `/lx-task-spec` | `stepwise` / `deep debug` |
| 文件范围 | ≤3 | >3 或需设计 | 不限 |
| 子任务 | 无 | 可拆分 | 串行深潜 |
| 每步验证 | 最终验证 | AC 逐条验证 | 每步必须验证 |
| subagent | 不开 | 可选 | 不开 |
| 上限 | 3 轮修复 | 5 轮 | 3 轮 → 升级 lx-root-cause-analysis |

---

## 一、light 模式 — 快速闭环

### 5 步闭环

```
捕获 → 分拣 → 执行 → 验证 → 关闭
```

#### Step 1: 捕获
```
/lx-task-spec light add 🐛 P1 用户登录时 OAuth 回调 500
/lx-task-spec light add ✨ P2 添加日志级别动态配置
```

#### Step 2: 分拣
```
/lx-task-spec light list       # 查看队列
/lx-task-spec light do <ID>    # 认领任务
/lx-task-spec light next       # 自动认领最高优先级
```

#### Step 3: 执行（单终端）
- 读取目标文件
- 修改（P0 可走 `../../nodes/auto_fixer.md`）
- 运行测试

#### Step 4: 验证
- `../../nodes/verifier.md` re-scan
- 手动验证逻辑

#### Step 5: 关闭
```
/lx-task-spec light review     # 审查当前 diff
/lx-task-spec light close      # 确认关闭
```

### 升级协议（超出 light 范围时）
| 特征 | 升级路径 |
|:-----|:---------|
| >3 文件修改 | → standard 模式 |
| 跨域重构 | → standard → deep |
| 根因不明 bug | → deep 模式 |

---

## 二、standard 模式 — 精确 AC

### 3 问引导 → 规划 → 执行 → 验收

#### Phase 1: 3 问引导
1. 任务名称是什么？
2. 目标是什么？
3. 验收标准（AC）是什么？

完成后生成 `task_input` YAML，确认后开始。

#### Phase 2: 规划
- 生成 plan.md（含 TODO + 文件范围）
- 写入 `.omc/plan/<task-id>/`

#### Phase 3: 执行
- 按 plan.md TODO 逐项执行
- 每项执行贴证据（`[已验证:file:line]`）

#### Phase 4: 验收
- AC 逐条验证
- 生成验收报告

### 降级策略
| 场景 | 主路径 | 降级 |
|------|--------|------|
| orchestrator 加载失败 | 状态机 | 跳过，直接 3 问 |
| AC 无法自动生成 | AI 草稿 | 提供模板让用户填写 |

---

## 三、deep 模式 — 串行攻坚

### 触发条件
| 条件 | 说明 |
|------|------|
| 根因不明 | 不知道 bug 在哪里 |
| 跨模块 | >3 文件 |
| 之前失败过 | 2 次以上修复失败 |
| 复杂逻辑 | 状态机/并发 |
| 安全相关 | 影响 permission/敏感文件 |

### 5 步执行
```
Step 1: 隔离 — 最小可复现用例，确认 bug 存在
  → 验证: 复现脚本 exit code ≠ 0
Step 2: 定位 — scanner + 二分法，找到根因 file:line
  → 验证: 根因假设可证伪 (有 file:line 证据)
Step 3: 方案 — 修复方案 + 影响分析
  → 验证: 方案经 gate_checker 审核通过
Step 4: 修复 — 单文件单修改，最小变更
  → 验证: 复现脚本 exit 0 + 回归测试通过
Step 5: 加固 — 添加测试，确保同类 bug 不再漏过
  → 验证: 新增测试覆盖根因路径
```

### 硬约束
- 不可跳过 Step（跳过一步 → 自行返回上一步）
- 每 Step 完成必须写验证证据（file:line 或命令输出）
- 3 轮上限适用（behavior_rules §修复上限）
- Step 3 涉及治理文件时触发 CAPTCHA

---

## 通用降级策略

| 场景 | 路径 |
|------|------|
| Step 验证失败 | 回到上一步重新执行 |
| 3 轮上限触发 | 标记 blocked，升级 lx-root-cause-analysis |
| 子步骤无法完成 | 标注 [blocked]，输出当前证据 |
| 脚本执行失败 | 直接调用原生工具手动判断 |
