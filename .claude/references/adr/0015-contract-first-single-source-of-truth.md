# 0015. 契约收敛到 Contract-first 单一真源

**日期**: 2026-08-12
**来源**: /grill-me 审阅会话（CarrorOS 工作流契约强度审计）

## 上下文

用户审阅 CarrorOS 是否做到「工作流」：每个步骤有 schema、流程固定、入参出参一一匹配、路径错误时找补。审计发现：

- 独立 schema 文件仅 2 个存活，但 `phase_handoff.yaml` / `state_transitions.yaml` **零代码消费者**，只是文档镜像；
- 真正被消费的契约是代码内嵌 dict（`phase_contracts.PHASE_CONTRACTS`、`step_contracts.parse_plan_steps`），运行时写 `state/phase-handoff-*.json` 供 verify/archive 门禁消费；
- `start_step_atomic` / `complete_step_atomic` **无出参契约**（返回 None），调用方无法判断事务成败；
- 路径找补资产（`escape-patches.json`、`anti-pattern-redirects.jsonl`）**分散、事后、非强制**（status: pending，升华产物）。

用户裁决标尺为「必须独立 schema 文件」，并要求按此逻辑**清空旁支末节、保留唯一正确路径与策略模式入参出参设定**。

## 决策

契约收敛到 Contract-first 单一真源，分两期隔离风险。

**一期（契约层重构，可独立回归）：**
1. `phase_contracts.py` 改为从 `schemas/contract/phase_handoff.yaml` 加载契约，删除代码内嵌 `PHASE_CONTRACTS` dict（真源化后成为旁支）；
2. 补 `schemas/contract/step_contract.yaml` 作为 step 契约唯一真源，`step_contracts` 消费；
3. `state_transitions.yaml` 从「参考文档」升级为强制 gate（非法转换禁止）；
4. 删真孤儿 `schemas/output/review_report.yaml`、`schemas/output/block-output.yaml`（0 引用，贯彻 registry「零消费者应删除」审计规则）；文档级引用（acceptance_report / task_spec / gov_report / context_summary）保留，registry 标注「文档/参考」；
5. 一致性测试 + verify/archive 全链路回归。

**二期（运行时门禁，风险隔离）：**
6. G2 出参契约：`start_step_atomic` / `complete_step_atomic` 返回结构化结果 `{ok, step_id, errors}`；
7. `escape-patches` 从「记录」升级为运行时 REDIRECT（检测到 governance_bypass / 偏离标准流程 → 软门禁 REDIRECT 回正确路径，不 BLOCK）。

## 替代方案

1. **镜像 + 一致性测试**：代码保持真源，YAML 补全并用测试锁定一致性。改动小，但 YAML 严格说仍是镜像，未达「独立 schema 文件」标尺。
2. **只出审计报告**：不落代码，仅记录 G1/G2/G3。被用户否决（选真源时排除）。
3. **全清含 skill 引用**：所有 registry 标注非真源 schema 全部收敛/删除，会断 `skill-dependencies.yaml` / `lx-task-spec` / `lx-root-cause-analysis` 引用，风险高。被否决。

## 理由

- **哲学「少即是多」**：收敛单一真源，删真孤儿，不增殖 schema；
- **registry 审计规则**「零消费者 schema 应删除」——被删文件正是 0 引用孤儿，规则得以贯彻；
- **REDIRECT 不 BLOCK**：与 agentic-ui 软锁哲学一致（公开拒绝仅 REDIRECT/ASK_USER），运行时软门禁而非硬阻断；
- **两期隔离**：一期是纯契约层重构，可独立回归 verify/archive；二期涉及运行时门禁，风险隔离，一次修一个机制边界。

## 后果

- 契约行为不变：YAML 真源与现有 `PHASE_CONTRACTS` 语义必须一致，回归靠 `test_phase_contracts.py` 锁定；
- 一期完成后 `PHASE_CONTRACTS` dict 删除，未来契约变更只改 YAML；
- `state_transitions` 变强制后，非法状态转换会被 gate 拒绝（需补充状态转换埋点）；
- 二期 REDIRECT 上线后，governance_bypass 类工具调用被软纠正，不阻断合法操作；
- skill 文档引用（acceptance_report 等）不受影响，registry 标注明确化。
