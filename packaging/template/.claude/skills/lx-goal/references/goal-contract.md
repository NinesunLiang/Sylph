# GoalContract — Phase 0 输出协议

> 目标模式执行契约。Phase 0 产出此 yaml 作为全自动执行的唯一依据。
> 引用: `@references/goal-contract.md`

## 用途

GoalContract 替代 Phase 0 的自由格式澄清，改为结构化输出。
- L1 任务：必须产出 goal_type / risk_level / allowed_scope / success_criteria
- L2 任务：额外产出 A-E 阶段计划 + oracle_required

## 模板

```yaml
# GoalContract v1
goal_type: code_change    # audit | refactor | test_fix | research | ops | doc
risk_level: L1            # L1 | L2
origin:                   # 用户请求原文

allowed_scope:
  files: []               # 允许修改的文件列表
  commands: []            # 允许执行的命令模式
  network: false          # 是否允许网络请求

blocked_scope:
  files: []               # 禁止触碰的文件
  commands: []            # 禁止执行的命令

success_criteria:
  - ""                    # 可验证的验收标准列表

verification:
  method: test            # test | file-check | user-confirm | command
  command: ""             # 验证命令

rollback_policy:
  reversible: true        # 是否可回滚
  method: ""              # 回滚方法

escalation_policy:
  on_unexpected_scope: check_continue   # check_continue | skip | block
  on_failure: retry_once                # retry_once | skip | block
  on_l2_trigger: auto_escalate          # auto_escalate | skip | block

# L2 only
l2:
  phases:
    A_cognition: ""
    B_plan: ""
    C_review: false       # 是否需要 Oracle 审核
    D_execute: ""
    E_acceptance: ""
  oracle_required: false

metadata:
  created_at: ""
  source: "Phase 0 clarification"
```

## 使用规则

1. Phase 0 必须产出 GoalContract，否则不得进入 Phase 1→N 执行
2. 模糊目标给默认解释：`goal_type: unknown` + `risk_level: L1` + `allowed_scope: { files: [], commands: ["read only"] }`
3. 执行中发现 scope 外文件 → 按 escalation_policy.on_unexpected_scope 处理
4. success_criteria 必须可验证（非"优化完成"类模糊描述）
5. rollback_policy 缺失时默认为不可回滚（走 blocked_human）
