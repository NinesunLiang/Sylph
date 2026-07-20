# Mechanism Evaluations - 机制验收用例

> >
> ⚠️ **仅在回归测试时加载**（修改 CLAUDE.md 或 task_sys 文件后）
> 正常任务流不需要加载此文件
> 用于验证 Harness 任务系统是否正常工作
> 版本：v1.0.0

---

## M1: 任务触发与澄清机制
**目标**：验证 task_input 能正确触发 A0 Clarifier，并在信息缺失时进入 need_clarification。

### 测试用例 M1.1：完整输入 → ready
**输入**：

```yaml
e
: test-m1-completerole: gotarget: 在 pkg/handler 中新增 GetUser 接口，返回 JSONpass_criteria: - id: AC1 type: build description: 编译通过 how_to_check: go build ./... expected: exit code 0pass_example: "类似 pkg/handler/GetHealth 的结构"executor_mode: stepwisepriority: p1
yamltask_name: test-m1-completerole: gotarget: 在 pkg/handler 中新增 GetUser 接口，返回 JSONpass_criteria: - id: AC1 type: build description: 编译通过 how_to_check: go build ./... expected: exit code 0pass_example: "类似 pkg/handler/GetHealth 的结构"executor_mode: stepwisepriority: p1

```
**期望**：- state = `ready`- 无澄清问题- 可直接进入 planning

### 测试用例 M1.2：缺失 pass_criteria → need_clarification
**输入**：

```yaml
e
: test-m1-missing-criteriarole: gotarget: 优化数据库查询性能executor_mode: stepwisepriority: p2
yamltask_name: test-m1-missing-criteriarole: gotarget: 优化数据库查询性能executor_mode: stepwisepriority: p2
```
**期望**：- state = `need_clarification`- 提出 ≤3 个澄清问题，优先问验收方式- 不允许猜测验收标准

### 测试用例 M1.3：缺失 role → 推断 + 确认
**输入**：

```yaml
e
: test-m1-missing-roletarget: 新增用户登录页面executor_mode: stepwisepriority: p1
yamltask_name: test-m1-missing-roletarget: 新增用户登录页面executor_mode: stepwisepriority: p1

```
**期望**：- 通过仓库结构推断候选 role（如存在 package.json + src/ → front）- 输出 `role: [推断, 待确认] front`- 请求用户确认

---

## M2: 规划机制
**目标**：验证非琐碎任务必须进入 planning，计划必须写入 plan.md 且为可勾选清单。

### 测试用例 M2.1：非琐碎任务 → planning
**输入**：一个 ≥3 步的任务（如"新增完整的 CRUD API"）
**期望**：- state = `planning`- 计划写入 `.omc/state/{date}/{task_name}/output/plan.md`- 每步包含：验收标准 + 回退方式- 包含影响范围预估

### 测试用例 M2.2：计划范围冻结
**期望**：- 计划中不包含未请求的重构- 非核心能力标记为 TODO- 无"顺手优化"

---

## M3: 执行与证据机制
**目标**：验证每个 step 必须产生证据，否则不得勾选完成。

### 测试用例 M3.1：证据缺失 → 不得完成
**场景**：executor 声称某步完成但未提供 file:line 或命令输出
**期望**：- 该步不得标记 [x]- state 保持 `executing`- 提示补充证据

### 测试用例 M3.2：3 轮修复上限
**场景**：同一问题修复 3 次均失败
**期望**：- state = `blocked`- 报告已尝试方案 + 失败证据- 请求用户决策

---

## M4: 验收机制（A/B 终端）
**目标**：验证 A 终端生成可观测标准，B 终端执行验收并产出报告。

### 测试用例 M4.1：A 终端生成标准
**输入**：target = "新增 /api/users 接口"
**期望**：- 产出 criteria.md- 每条标准包含：how_to_check（具体命令/路径）+ expected（期望现象）- 无"看起来没问题"类表述

### 测试用例 M4.2：B 终端执行验收
**输入**：实际产出 + criteria.md
**期望**：- 产出 acceptance_report.md- 表格形式对比标准 vs 实际- 明确判定通过/不通过- 不通过项包含根因分析

---

## 回归检查清单
每次修改 CLAUDE.md 或 task_sys 文件后，执行：
- [ ] M1.1：完整输入能正确触发 ready- [ ] M1.2：缺失 criteria 能进入 need_clarification- [ ] M1.3：缺失 role 能推断并请求确认- [ ] M2.1：非琐碎任务进入 planning- [ ] M2.2：计划范围冻结，无越界- [ ] M3.1：无证据不得完成- [ ] M3.2：3 轮修复失败后 blocked- [ ] M4.1：A 终端生成可观测标准- [ ] M4.2：B 终端产出验收报告
