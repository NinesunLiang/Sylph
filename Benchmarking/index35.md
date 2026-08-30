# index35 — 修复 5 项既有测试失败（F2/water 债务）

> 日期：2026-08-30 | 目标：全量 pytest 回归清零（此前 345 项中 5 项既有失败）

## 结论

**全量 pytest 345 passed / 0 failed**——5 项既有失败（4 项 F2 依赖树门禁引入 + 1 项 water 评测断环）全部修复，
回归套件首次完全绿色。均为旧测试未同步新机制的"测试债务"，非新引入缺陷。

## 修复明细

### 1. F2 依赖树门禁（4 项，carros_base verify/PlanGate 现在要求 plan.md 含"## 依赖树"）

| 失败测试 | 根因 | 修复 |
|---|---|---|
| test_execution_boundary_immunity::test_cmd_verify_is_idempotent_for_completed_step | plan 无依赖树章节 → F2 exit 2 | plan 补 `## 依赖树\n- 无` |
| test_phase_contracts::test_plan_gate_accepts_uppercase_checkbox | 同上（PlanGate.validate） | plan 补依赖树 |
| test_phase_contracts::test_plan_gate_rejects_unprefixed_verify_before_execution | 同上（依赖树检查先于 verify 规则检查） | plan 补依赖树，原"Invalid verify rules"断言仍生效 |
| test_state_transitions_gate_integration::test_verify_full_completion_invokes_state_transitions_gate | PLAN_TEXT 无依赖树 → F2 exit 2 | PLAN_TEXT 补依赖树 |

**要点**：补依赖树使 plan 通过 F2 门后，各测试原本的断言目标（幂等 / uppercase checkbox / verify 规则拒绝 / state transition）全部正常生效，未削弱机制。

### 2. water 评测断环（1 项）

| 失败点 | 根因 | 修复 |
|---|---|---|
| negative_tests H-CRITICAL-CHECKPOINT | 引用 `.omc/knowledge/claude-next.md`，该文件已在知识库重组中移除 | 检查列表改为现存关键抗 compact 文件（tokens 目录 / invariants.md / working-set-template.yaml） |
| capture_evidence G4/G5 | 检查 h-water-*.json 但无人产生（ga_behavioral_validation 未在评测管线运行） | G 检查前新增 GA-BEHAVIORAL-VALIDATION 步骤（实测 6/6 PASS exit 0，产出 h-water-*.json），评测环闭环 |

## 测试证据

- 4 个 F2 修复测试：4 passed
- test_water_governance_loop：4 passed
- 全量回归：**345 passed / 0 failed**

## 残余说明

- 全量回归清零为长期治理健康的重要里程碑：F2/water 断环是机制演进中测试未同步的债务，现已闭环。
- 无新增机制改动，仅测试/评测管线同步到当前机制行为。
