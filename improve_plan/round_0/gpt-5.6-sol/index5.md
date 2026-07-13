# CarrorOS 最终整合重构方案
## 第 5/8 部分：Compact、Checkpoint、Handoff 与 Resume 双栈治理

本部分承接：

- 第 2/8：`state.json` 是唯一运行状态源，VerifyGate 是唯一完成门；
- 第 3/8：文档、任务状态、证据与审计分层持久化；
- 第 4/8：每轮重新编译 Context Capsule，不持续追加 transcript。

本章冻结 CarrorOS 在长会话、上下文高水位、模型切换、会话中断和压缩发生时的恢复机制。

> **Compact 负责释放短期上下文，Checkpoint 负责保护可回滚状态，Handoff 负责跨会话导航，Resume 负责从持久真相重建；四者都不能制造“任务已完成”的事实。**

---

# 一、最终治理顺序

CarrorOS 必须按以下顺序处理上下文压力：

```text
第一层：阻止无关内容进入 Context
  文档索引、精确切片、Artifact 落盘、Review 隔离

第二层：每轮重建最小 Context
  Stable Core + Hot Card + Current Step + Required Reads

第三层：无损释放可重建内容
  删除临时视图、裁剪已落盘工具结果、刷新 Capsule

第四层：写 Handoff 并切换会话
  从磁盘状态恢复，而不是依赖旧聊天

第五层：使用平台原生压缩
  Claude Code：L1→L5，最重手段最后使用
  OpenCode：Prune(hidden)→隐藏摘要 Agent
```

禁止反向处理：

```text
✗ 一达到水位就调用 LLM 摘要；
✗ 先压缩，再考虑工具结果落盘；
✗ 用摘要替代 state.json；
✗ 用更大上下文窗口掩盖持续增长；
✗ compact 后从模型记忆继续执行；
✗ compact 成功后直接标记 VERIFIED。
```

---

# 二、无损与有损边界

## 2.1 治理分类

| 操作 | 分类 | 可恢复来源 | 是否可作为常规路径 |
|---|---|---|---:|
| 工具完整输出写入 Artifact | **无损可回滚** | Artifact 原件 | 是 |
| 生成确定性 Preview | **无损源数据上的有界视图** | Artifact 原件 | 是 |
| 每轮重新编译 Capsule | **无损工作集重建** | Memory Plane | 是 |
| 丢弃旧 Capsule | **无损** | state/docs/evidence 可重建 | 是 |
| Git commit/checkpoint | **文件级可回滚** | Git/快照 | 是 |
| Claude 旧工具结果裁剪 | 原件已外置时**逻辑可恢复** | Artifact/transcript | 是 |
| OpenCode Prune(hidden) | **非物理删除、可审计回溯** | SQLite | 是 |
| 微压缩重复解释 | **轻度有损** | transcript/Artifact 部分兜底 | 谨慎 |
| 上下文折叠 | **有损** | handoff/持久文件重建 | 兜底 |
| LLM 会话摘要 | **有损** | 原始 transcript 或 SQLite | 最后使用 |
| Claude L5 AutoCompact | **有损不可逆于当前 Context** | 外部持久状态兜底 | 非常规 |
| 删除 Artifact 原件 | **不可逆数据删除** | 无，除非另有备份 | 归档策略控制 |

## 2.2 不可被摘要覆盖的内容

```text
- manifest.yaml 中的 goal、scope、acceptance；
- state.json 的 status、version、current_step、blocker；
- plan.md 的当前有效步骤与 verify 规则；
- ADR / Contract 的规范内容；
- evidence.jsonl 的事实索引；
- Artifact 原件和 hash；
- 用户显式确认记录；
- 权限、安全与外部副作用记录。
```

有损摘要只能包含导航性内容，例如：

```text
- 当前目标的短描述；
- 最近发生了什么；
- 建议先读取哪些持久文件；
- 未解决问题的索引；
- Artifact 和文档引用。
```

---

# 三、上下文水位与状态转换

## 3.1 水位输入

CarrorOS 不依赖单一 token 百分比。水位至少综合：

```text
input token estimate
turn count
prompt cache hit rate
Capsule mandatory section size
tool preview growth
current action 是否可安全停止
provider context limit
模型 profile hard limit
平台原生 compact 风险
```

## 3.2 决策枚举

```text
CONTINUE
COMPACT_SOON
COMPACT_NOW
RESUME_REQUIRED
DOWNGRADE_REQUIRED
RESUME_BLOCKED
```

## 3.3 推荐阈值

### L1 Base

```yaml
watermark:
  soft_turns: 15
  hard_turns: 20
  soft_context_percent: 80
  hard_context_percent: 95
  action_boundary_required: true
```

### L2 Enhance

```yaml
watermark:
  soft_context_percent: 70
  hard_context_percent: 85
  action_boundary_required: true
  global_review_requires_isolation: true
```

模型 profile 中更严格的阈值优先。

## 3.4 决策规则

```text
低于 soft：
  CONTINUE

达到 soft：
  COMPACT_SOON
  - 禁止扩大 scope；
  - 完成当前原子 action；
  - 刷新 state、evidence、handoff；
  - 预编译 Resume Capsule。

达到 hard：
  COMPACT_NOW
  - 不启动新业务 action；
  - 将未落盘结果写入 Artifact；
  - 写 checkpoint 和 handoff；
  - 尝试最小 Capsule 重建。

mandatory context 仍超过 hard：
  RESUME_REQUIRED 或 DOWNGRADE_REQUIRED
  - 拆分 step；
  - 切换更适合的模型；
  - 转隔离会话；
  - 改善结构化文档；
  - 不静默删除关键约束。

持久状态损坏或版本冲突：
  RESUME_BLOCKED
```

## 3.5 状态写入

达到 soft 水位：

```json
{
  "status": "COMPACT_SOON",
  "context": {
    "decision": "COMPACT_SOON",
    "watermark": 82,
    "handoff_required": true
  }
}
```

达到 hard 水位并必须切会话：

```json
{
  "status": "RESUME_REQUIRED",
  "context": {
    "decision": "COMPACT_NOW",
    "watermark": 96,
    "handoff_required": true,
    "resume_reason": "hard_context_watermark"
  }
}
```

Context Engine 不得在这些转换中修改 step 的验证状态。

---

# 四、Checkpoint、Git 与外部副作用的边界

## 4.1 三类回滚域

```text
A. Context 回滚域
   Capsule、Preview、披露清单、会话历史

B. Workspace 回滚域
   文件修改、配置、生成代码、测试夹具

C. External Side-Effect 回滚域
   数据库写入、云资源、部署、消息发送、付款、外部 API 变更
```

三者不得混为一谈。

## 4.2 能力矩阵

| 机制 | Context | 文件 | Git 历史 | 外部副作用 |
|---|---:|---:|---:|---:|
| 重建 Capsule | 是 | 否 | 否 | 否 |
| Claude checkpoint/ESC | 部分 | 是 | 否 | 否 |
| Git stash/commit/revert | 否 | 是 | 是 | 否 |
| Artifact | 证据 | 不自动回滚 | 不自动回滚 | 仅记录 |
| 补偿事务 | 否 | 可选 | 否 | 是 |
| 用户确认 | 治理授权 | 治理授权 | 治理授权 | 必需时授权 |

## 4.3 Checkpoint 规则

高风险 action 前必须记录：

```yaml
schema_version: carros.checkpoint.v1
checkpoint_id: CP-004
task_id: fix-auth-001
state_version: 7
step_id: S2
action_id: A1
workspace:
  git_head: abc1234
  dirty_paths:
    - src/auth/refresh.ts
  patch_artifact: artifacts/preaction-CP-004.diff
external_side_effects:
  planned: false
created_at: "2026-07-12T09:28:00Z"
```

Checkpoint 通过以下方式创建：

```text
- Git commit；
- Git stash；
- diff Artifact；
- Claude Code 文件级 checkpoint；
- 数据库快照或外部资源快照；
- 补偿操作定义。
```

## 4.4 外部副作用

外部副作用必须有独立策略：

```yaml
external_effect:
  type: database_migration
  reversible: conditional
  confirmation_required: true
  precondition_check: scripts/check-migration.sh
  compensation_command: scripts/rollback-migration.sh
  evidence_required:
    - pre_state_snapshot
    - operation_receipt
    - post_state_verification
```

禁止：

```text
✗ 用“Git 可回滚”代表数据库可回滚；
✗ 用 Claude ESC 代表部署已撤销；
✗ compact 前遗漏正在进行的外部操作；
✗ 恢复后重复执行非幂等副作用；
✗ 无 idempotency key 时自动重放外部命令。
```

---

# 五、`handoff.md` 最终协议

## 5.1 定位

`handoff.md` 是跨会话恢复导航，不是运行状态真相源。

```text
state.json     决定“现在是什么状态”
plan.md        决定“接下来允许做什么”
evidence       证明“已经发生过什么”
handoff.md     告诉新会话“从哪里开始读取”
```

## 5.2 完整模板

```markdown
---
schema_version: carros.handoff.v1
handoff_id: HO-fix-auth-001-0007
task_id: fix-auth-001
from_session: claude-session-abc
state_version: 7
manifest_version: 1
plan_version: 2
capsule_version: 12
profile: deepseek-v4-flash
reason: soft_context_watermark
created_at: 2026-07-12T09:35:00Z
expires_on_state_change: true
---

# Resume Capsule

## Goal

修复同一用户并发刷新导致多次上游调用的问题，不改变公共错误类型。

## Current State

- status: COMPACT_SOON
- step: S2
- action: A1
- last_verified_step: S1
- blocker: none

## Scope

Allowed:
- `src/auth/refresh.ts`
- `tests/auth/refresh.test.ts`

Denied:
- `.env`
- `secrets/**`
- `docs/reviews/**`

## Confirmed Decisions

- `D-001`：保留现有 `RefreshError` 公共类型。
- `ADR-014#single-flight`：同一用户复用 in-flight promise。

## Last Durable Events

- `E17`：竞态测试失败，收到 3 次上游调用。
- `E18`：修改前 checkpoint 已建立。
- `CP-004`：workspace checkpoint。

## Current Work

- intent: 调整 `refreshToken` 中 promise 注册时机
- target: `src/auth/refresh.ts#refreshToken`
- action_started: false
- external_side_effect_in_flight: false

## Required Reads

1. `state.json`
2. `plan.md#S2`
3. `working-set.yaml`
4. `ADR-014#single-flight@abc1234`
5. `CONTRACT-AUTH#error-semantics@v4`
6. `evidence:E17`
7. `src/auth/refresh.ts#refreshToken@abc1234`

## Optional Reads

- `tests/auth/refresh.test.ts:40-130@abc1234`

## Do Not Reload

- 完整 transcript
- 完整 executor.md
- `docs/reviews/**`
- 完整测试日志
- 已 VERIFIED 的 S1 详情

## Resume Instructions

1. 校验 state/plan/handoff 版本；
2. 重新计算 current step；
3. 验证 E17 和 CP-004 的 Artifact hash；
4. 按新 profile 编译 Context Capsule；
5. 通过 PreActionGate 后才能执行 A1；
6. 不得依据本 handoff 把 S2 标为 VERIFIED。
```

## 5.3 禁止写入 Handoff

```text
✗ chain-of-thought；
✗ 完整 prompt；
✗ API key、cookie、private key；
✗ 未脱敏日志；
✗ 完整工具输出；
✗ “我记得已经完成”；
✗ 无 evidence 引用的完成声明；
✗ 自动生成的用户确认；
✗ 模型无法验证的推测。
```

## 5.4 Handoff 失效条件

任一条件成立，旧 handoff 失效：

```text
- state_version 已变化；
- plan_version 已变化；
- current_step 已变化；
- 关键 source hash 变化；
- manifest scope 变化；
- 外部副作用状态变化；
- blocker/question 已更新；
- handoff Schema 不兼容。
```

失效不代表删除。保留旧 handoff 供审计，但不得用于执行恢复。

---

# 六、Handoff 的确定性生成

## 6.1 输入

```text
manifest.yaml
state.json
plan 当前 step
working-set.yaml
decisions.md 当前有效决策
evidence.jsonl 尾部相关事件
checkpoint 索引
当前 Capsule Receipt
```

## 6.2 输出规则

Handoff 应通过程序生成主体，禁止让 LLM自由总结运行事实。

```python
def generate_handoff(task_id: str, reason: str) -> dict:
    manifest = load_manifest(task_id)
    state = load_state(task_id)
    plan = load_plan(task_id)
    step = resolve_current_step(state, plan)
    working_set = load_working_set(task_id)
    evidence = select_resume_evidence(task_id, step["id"])
    decisions = select_active_task_decisions(task_id)
    checkpoints = select_current_checkpoints(task_id, step["id"])

    required_reads = build_required_reads(
        state=state,
        step=step,
        working_set=working_set,
        evidence=evidence,
    )

    handoff = render_handoff_fixed_template(
        manifest=manifest,
        state=state,
        step=step,
        decisions=decisions,
        evidence=evidence,
        checkpoints=checkpoints,
        required_reads=required_reads,
        reason=reason,
    )

    validate_no_secrets(handoff)
    validate_refs(handoff)
    write_handoff_atomically(task_id, handoff)
    append_audit_event(task_id, "HANDOFF_CREATED", handoff.meta)
    return handoff
```

## 6.3 可选 LLM 文本

若希望增加人读说明，可以让模型生成一个 `Notes` 段，但必须：

```text
- 标记 `lossy: true`；
- 不参与 Resume 决策；
- 不改变 Required Reads；
- 不声明验证结果；
- 不包含无来源事实；
- 可在预算紧张时完全删除。
```

---

# 七、Resume 重建算法

## 7.1 恢复原则

旧方案常见顺序为：

```text
token → handoff → prompts → plan → executor tail → audit tail
```

最终版根据分责七件套升级为：

```text
1. manifest
2. state
3. plan 当前 step
4. handoff 导航
5. working-set
6. decisions / required documents
7. evidence index + 必需 Artifact 校验
8. checkpoint / 外部副作用状态
9. 编译新 Capsule
10. PreActionGate
```

`handoff` 不排在 `state` 前面，因为它不是权威状态源。

## 7.2 完整算法

```python
def resume_task(task_id: str, target_profile: str | None = None) -> dict:
    # 1. 定位任务真相
    manifest = load_manifest(task_id)
    state = load_state(task_id)
    plan = load_plan(task_id)
    handoff = load_latest_handoff(task_id)

    # 2. Schema 与版本校验
    validate_manifest_schema(manifest)
    validate_state_schema(state)
    validate_plan_schema(plan)
    validate_legal_status_for_resume(state["status"])

    # 3. 从 state + plan 重新计算，不信任 handoff 声明
    computed_step = resolve_first_non_verified_step(state, plan)
    assert_step_consistency(state, computed_step)

    # 4. handoff 只作导航
    handoff_status = validate_handoff(
        handoff=handoff,
        state=state,
        plan=plan,
        computed_step=computed_step,
    )

    if handoff_status == "STALE":
        handoff = regenerate_handoff_from_durable_state(task_id)

    # 5. 校验 unresolved 状态
    if state.get("question") and not state["question"].get("answered_at"):
        return block_resume(task_id, "ASK_USER_UNRESOLVED")

    if state.get("blocker") and not blocker_is_resolved(state["blocker"]):
        return block_resume(task_id, "BLOCKER_UNRESOLVED")

    # 6. 校验证据与失败覆盖关系
    evidence = load_evidence_index(task_id)
    validate_required_artifact_hashes(evidence, computed_step)
    unresolved_failures = find_unresolved_failures(
        evidence=evidence,
        step_id=computed_step["id"],
    )

    # 7. 校验 workspace 与外部副作用
    checkpoint_status = validate_checkpoint_state(task_id, computed_step["id"])
    effect_status = validate_external_effect_state(task_id)

    if effect_status in {"UNKNOWN", "IN_FLIGHT_UNSAFE"}:
        return block_resume(task_id, "EXTERNAL_EFFECT_STATE_UNKNOWN")

    # 8. 按目标模型重建工作集和 Capsule
    profile = target_profile or state["context"]["profile"]
    reconcile_working_set(task_id, computed_step, profile)
    compiled = compile_context(
        task_id=task_id,
        user_delta="Resume from durable state.",
        profile_name=profile,
    )

    if compiled["decision"] in {"DOWNGRADE_REQUIRED", "RESUME_BLOCKED"}:
        return compiled

    # 9. 状态转换，只恢复为 RUNNING，不标记完成
    update_state_compare_and_swap(
        task_id=task_id,
        expected_version=state["state_version"],
        patch={
            "status": "RUNNING",
            "current_step": computed_step["id"],
            "context.profile": profile,
            "context.decision": "RESUME_OK",
            "verification.residual_failures": unresolved_failures,
        },
    )

    append_audit_event(task_id, "RESUME_OK", {
        "step": computed_step["id"],
        "profile": profile,
        "handoff_status": handoff_status,
        "checkpoint_status": checkpoint_status,
    })

    return {
        "decision": "RESUME_OK",
        "current_step": computed_step["id"],
        "capsule_id": compiled["capsule"].capsule_id,
        "unresolved_failures": unresolved_failures,
    }
```

## 7.3 Resume 必须重新计算

```text
1. state.current_step 是否与 plan 一致；
2. plan 中第一个非 VERIFIED step；
3. VERIFIED step 是否都有 verdict_id；
4. 当前 step 有哪些有效 evidence；
5. 旧失败是否已被更新、更相关的成功证据覆盖；
6. Artifact hash 是否匹配；
7. workspace revision 是否与 checkpoint 一致；
8. 外部副作用是否完成、失败或未知；
9. 当前模型 profile 是否可以容纳 mandatory Context；
10. PreActionGate 是否仍允许 next action。
```

禁止：

```text
✗ compact 后凭记忆继续标记 [x]；
✗ handoff 写“已完成”就跳过 VerifyGate；
✗ 将用户的普通“继续”当作 user_confirmation；
✗ 重放可能已执行的非幂等 action；
✗ Artifact 缺失时用摘要替代；
✗ 恢复后跳过 denied path 检查。
```

---

# 八、失败覆盖与幂等恢复

## 8.1 失败不能因 Compact 消失

例如：

```text
E17  test_result exit=1
E18  file_change
E19  test_result exit=0
```

只有当 `E19`：

```text
- 针对同一个 verify_id；
- 产生于相关代码变更之后；
- Artifact 有效；
- 命令和环境符合计划；
```

才可以覆盖 `E17`。Compact 或摘要不能把 `E17` 从逻辑状态中“忘掉”。

## 8.2 Action 执行状态

为防止恢复后重复执行，action 应记录：

```json
{
  "action_id": "A1",
  "execution_id": "EXEC-009",
  "status": "PREPARED",
  "idempotency_key": "fix-auth-001:S2:A1:9",
  "started_at": null,
  "finished_at": null,
  "external_side_effect": false
}
```

状态：

```text
PREPARED
STARTED
SUCCEEDED
FAILED
UNKNOWN
```

恢复规则：

```text
PREPARED：可安全重新进入 Gate；
STARTED + 纯文件动作：检查 diff/checkpoint 后裁决；
STARTED + 外部副作用：先查询外部结果，禁止盲目重放；
SUCCEEDED：读取 evidence，不重复执行；
FAILED：保留失败，进入修复或重新验证；
UNKNOWN：BLOCKED，除非有确定性 reconciliation。
```

---

# 九、Claude Code 路径

Claude Code 的压缩治理采用“最便宜、最可逆的手段优先”。

## 9.1 五级路径

| 层级 | 操作 | CarrorOS 要求 | 性质 |
|---:|---|---|---|
| CC-L1 | 工具全文落盘，只留稳定 Preview | 所有长结果先进入 Artifact | **无损可回滚** |
| CC-L2 | 裁剪已外置旧工具结果 | 先校验 Artifact/hash | 逻辑可恢复 |
| CC-L3 | 微压缩重复解释 | 不压缩 state/Contract/evidence | **轻度有损** |
| CC-L4 | 上下文折叠 | 先生成 handoff/checkpoint | **有损，可从外部状态重建** |
| CC-L5 | AutoCompact LLM 摘要 | 仅最后兜底，禁止作为真相源 | **有损不可逆于当前上下文** |

目标：绝大多数会话停在 CC-L1～CC-L2，不到 CC-L5。

## 9.2 ContentReplacementState 范式

同一个 `tool_result` 被替换为 Preview 后，必须稳定复用完全相同的文本：

```text
artifact_sha256
   ↓
preview_cache[sha256]
   ↓
固定 Preview 字节串
```

禁止：

```text
- 每轮让 LLM 重写 Preview；
- 同一 Artifact 有时显示 head、有时显示 summary；
- 改变字段顺序；
- 加入动态时间或随机措辞；
- 重新格式化已经进入缓存的旧结果。
```

推荐索引：

```json
{
  "artifact_sha256": "...",
  "preview_sha256": "...",
  "preview_path": ".omc/cache/previews/abc.txt",
  "strategy": "head_diagnostics_tail.v1"
}
```

## 9.3 Prompt Cache 稳定策略

```text
稳定前缀：
  CLAUDE.md Slim Core
  固定工具契约
  固定安全规则

高变后缀：
  Hot Card
  Current Step
  File Slices
  Evidence Preview
  User Delta
```

要求：

```text
- Stable Core 不写动态状态；
- 同一 section 确定性渲染；
- tool schema 顺序稳定；
- 非必要 MCP 不进入本轮；
- 不频繁重写 CLAUDE.md；
- 子 Agent 使用 fresh context，避免主会话污染。
```

## 9.4 Claude Code Checkpoint

Claude Code 文件级 checkpoint 可用于：

```text
- 撤回文件修改；
- 比较 Agent action 前后差异；
- 在 compact 前保存 workspace 状态。
```

不能用于：

```text
- 回滚数据库；
- 撤回发送的消息；
- 撤销部署；
- 证明测试通过；
- 替代 Git 历史；
- 替代 VerifyGate。
```

## 9.5 Claude Code 配置示例

以下是 CarrorOS 层约定；实际 Hook 事件名应按部署时的 Claude Code 版本核对：

```json
{
  "env": {
    "CARROS_PLATFORM": "claude-code",
    "CARROS_CONTEXT_CONFIG": ".omc/context-engine.yaml",
    "CARROS_ARTIFACT_STORE": ".omc/artifacts",
    "CARROS_PREVIEW_CACHE": ".omc/cache/previews",
    "CARROS_REUSE_PREVIEW_BY_HASH": "1",
    "CARROS_WRITE_HANDOFF_AT_SOFT": "1",
    "CARROS_STOP_ACTION_AT_HARD": "1",
    "CARROS_L5_IS_MEMORY": "0",
    "CARROS_FAIL_CLOSED": "1"
  },
  "permissions": {
    "defaultMode": "default"
  }
}
```

## 9.6 Claude 指标

```text
prompt_cache_hit_rate ≥70%，目标≥85%
cache_read_tokens / eligible_prefix_tokens
stable_prefix_hash_changes/session ≈0
artifact_preview_reuse_rate ≥95%
CC-L1/CC-L2 resolution rate ≥95%
CC-L5_rate ≈0
CC-L5_as_resume_source =0
token_$/verified_step
```

---

# 十、OpenCode 路径

OpenCode 必须使用其非物理 Prune 与多会话能力，不复制 Claude 的压缩命名。

## 10.1 正确顺序

```text
OC-1  Context Compiler 先减少新内容进入
OC-2  Artifact + SQLite 保存原始证据和会话审计
OC-3  Prune：将旧消息标记 hidden，非物理删除
OC-4  保留近约 40K token 安全垫
OC-5  保护最近两个完整回合
OC-6  保护 skill 输出
OC-7  仍不足时调用隐藏摘要 Agent
OC-8  自动重放最后一条用户消息
OC-9  CarrorOS 从 state/handoff 重新编译 Capsule
```

## 10.2 OpenCode Prune 的治理价值

```text
- hidden 不等于删除；
- 原始会话仍在 SQLite；
- 可用于审计、争议调查和离线重建；
- 正常 Context 不再携带隐藏消息；
- CarrorOS 不把 SQLite 会话当作 state.json。
```

性质：**非物理删除、可审计回溯**。

## 10.3 隐藏摘要 Agent

摘要格式建议固定为五标题：

```markdown
# Goal
# Current State
# Confirmed Decisions
# Evidence References
# Next Required Reads
```

必须附加：

```yaml
lossy: true
authoritative: false
source_session: session-id
created_at: timestamp
```

摘要禁止：

```text
- 覆盖 state；
- 把未验证 step 写成完成；
- 删除失败证据引用；
- 伪造用户确认；
- 代替 handoff；
- 作为 Archive 输入的唯一证据。
```

## 10.4 多会话 Resume

```text
execute：唯一 State Writer
retrieve：只读 docs/code，产 Knowledge Patch
review：只读 patch/contracts，产 Review Verdict
govern：只读 SQLite/metrics，产治理报告
```

切换会话前：

```text
1. execute 写 state/handoff；
2. 所有子会话提交 Artifact；
3. 主会话记录接受或拒绝的 patch；
4. 新 execute 会话从 task-id 恢复；
5. 不复制其它会话聊天全文。
```

## 10.5 OpenCode CarrorOS 配置

以下是 CarrorOS 插件/包装器配置，不冒充 OpenCode 原生 Schema：

```json
{
  "carros": {
    "platform": "opencode",
    "context": {
      "rebuildEachTurn": true,
      "sourceOfTruth": ".omc/tasks",
      "summaryIsAuthoritative": false
    },
    "prune": {
      "enabled": true,
      "nonDestructive": true,
      "preserveRecentTurns": 2,
      "preserveRecentTokenBuffer": 40000,
      "preserveSkillOutputs": true,
      "beforeSummary": true
    },
    "summary": {
      "enabled": true,
      "onlyAfterPrune": true,
      "lossy": true,
      "replayLastUserMessage": true
    },
    "sessions": {
      "singleStateWriter": true,
      "writerRole": "execute",
      "readOnlyRoles": ["retrieve", "review", "govern"]
    },
    "audit": {
      "preserveSQLite": true,
      "preserveArtifacts": true,
      "recordHiddenMarkers": true
    }
  }
}
```

## 10.6 OpenCode 指标

```text
prune_before_summary_rate =100%
non_destructive_prune_rate =100%
recent_two_turn_preservation_rate =100%
skill_output_preservation_rate =100%
summary_as_authority_count =0
SQLite_audit_retention_rate 按组织策略达标
multi_session_state_write_conflicts =0
resume_without_transcript_success_rate ≥95%
```

---

# 十一、Claude Code 与 OpenCode 对照

| 维度 | Claude Code | OpenCode |
|---|---|---|
| 主体优势 | Prompt Cache、渐进压缩、subagent、checkpoint | 多会话、SQLite、非物理 Prune、源码可 Hook |
| 第一动作 | 工具落盘 + 稳定 Preview | Context Compiler + Artifact/SQLite |
| 历史裁剪 | 先裁已外置结果 | hidden 标记，非物理删除 |
| 摘要 | L5 最后兜底 | Prune 不足后隐藏 Agent 摘要 |
| 摘要性质 | **有损不可逆于当前 Context** | **有损，但 SQLite 原始数据仍在** |
| 恢复真相 | `.omc/tasks/**` + docs + Artifact | `.omc/tasks/**` + docs + Artifact |
| 审计兜底 | transcript | SQLite |
| 隔离方式 | fresh-context subagent | 独立 sessions |
| 回滚 | checkpoint + Git | undo/redo + Git +自研 hook |
| 关键风险 | 缓存前缀抖动、依赖 L5 | 多会话写冲突、误把 SQLite 当状态源 |

两套路径共享 CarrorOS 上层 Contract，但不共享平台内部压缩实现。

---

# 十二、Compact 与 Resume 审计事件

每次事件追加到 `.omc/audit/events.jsonl`：

```json
{"schema_version":"carros.audit_event.v1","event_id":"AU-091","task_id":"fix-auth-001","type":"CONTEXT_WATERMARK","decision":"COMPACT_SOON","state_version":7,"profile":"deepseek-v4-flash","estimated_tokens":10120,"soft_limit":10000,"created_at":"2026-07-12T09:34:00Z"}
{"schema_version":"carros.audit_event.v1","event_id":"AU-092","task_id":"fix-auth-001","type":"HANDOFF_CREATED","handoff_id":"HO-fix-auth-001-0007","state_version":7,"created_at":"2026-07-12T09:35:00Z"}
{"schema_version":"carros.audit_event.v1","event_id":"AU-093","task_id":"fix-auth-001","type":"SESSION_RESUMED","decision":"RESUME_OK","from_session":"claude-session-abc","to_session":"claude-session-def","state_version_before":7,"state_version_after":8,"created_at":"2026-07-12T09:42:00Z"}
```

必需字段：

```text
event_id
task_id
type
actor/platform/session
state_version
reason/decision
source references
created_at
```

不得记录 secrets 或未脱敏完整命令输出。

---

# 十三、统一配置

```yaml
# .omc/continuity-policy.yaml
schema_version: carros.continuity_policy.v1

truth:
  runtime_state: state.json
  completion_gate: VerifyGate
  transcript_is_resume_source: false
  summary_is_authoritative: false

watermark:
  base:
    soft_turns: 15
    hard_turns: 20
    soft_percent: 80
    hard_percent: 95
  enhance:
    soft_percent: 70
    hard_percent: 85

handoff:
  generate_at_soft: true
  regenerate_on_state_change: true
  include_required_reads: true
  include_artifact_bodies: false
  include_transcript: false
  max_chars: 6000

checkpoint:
  required_for_high_risk: true
  require_git_head: true
  require_patch_artifact_when_dirty: true
  external_effect_requires_compensation: true

resume:
  recompute_current_step: true
  verify_artifact_hashes: true
  verify_checkpoint: true
  reconcile_external_effects: true
  recompile_capsule: true
  rerun_preaction_gate: true
  never_mark_verified: true

failure:
  fail_closed_on_state_conflict: true
  fail_closed_on_missing_evidence: true
  fail_closed_on_unknown_external_effect: true
```

---

# 十四、CLI 冻结

```bash
# 查看连续性状态
python3 .claude/scripts/carros_base.py context status \
  --task-id fix-auth-001

# 创建 checkpoint
python3 .claude/scripts/carros_base.py checkpoint create \
  --task-id fix-auth-001 \
  --step S2 \
  --action A1

# 生成 handoff
python3 .claude/scripts/carros_base.py context handoff \
  --task-id fix-auth-001 \
  --reason soft_context_watermark

# 检查是否可以 compact
python3 .claude/scripts/carros_base.py context compact-check \
  --task-id fix-auth-001

# 执行 CarrorOS 逻辑压缩
python3 .claude/scripts/carros_base.py context compact \
  --task-id fix-auth-001 \
  --mode lossless-first

# 恢复前预检
python3 .claude/scripts/carros_base.py resume preflight \
  --task-id fix-auth-001

# 从持久状态恢复
python3 .claude/scripts/carros_base.py resume \
  --task-id fix-auth-001 \
  --profile deepseek-v4-flash

# 检查外部副作用
python3 .claude/scripts/carros_base.py effects reconcile \
  --task-id fix-auth-001
```

CLI 语义：

```text
context compact：不得修改 step 完成状态；
resume：最多恢复到 RUNNING；
checkpoint create：不代表 action 成功；
resume preflight：不代表 VerifyGate 通过；
effects reconcile：只确认副作用状态，不确认整个任务完成。
```

---

# 十五、故障处理矩阵

| 故障 | 裁决 | 处理 |
|---|---|---|
| handoff 缺失，但 state/plan 完整 | 可恢复 | 重新生成 handoff |
| handoff 与 state 版本冲突 | `RESUME_BLOCKED` 或重建 | 以 state 为准 |
| Artifact 缺失 | `RESUME_BLOCKED` | 不用摘要替代 |
| Artifact hash 不匹配 | `RESUME_BLOCKED` | 证据标无效，调查审计 |
| plan 与 state current_step 冲突 | `RESUME_BLOCKED` | 一致性修复 |
| Capsule 版本过期 | 重编译 | 丢弃旧 Capsule |
| Claude 快触发 L5 | `COMPACT_NOW` | handoff + 新会话优先 |
| OpenCode Prune 不足 | 有损摘要 | 仍从持久状态恢复 |
| Prompt Cache 命中骤降 | `WARN` | 检查 Stable Core/Preview 漂移 |
| 外部副作用状态未知 | `BLOCKED` | reconciliation，禁止重放 |
| Git workspace 与 checkpoint 不符 | `BLOCKED/WARN` | diff 审计后裁决 |
| 目标模型装不下 mandatory Context | `DOWNGRADE_REQUIRED` | 拆 step 或换模型 |
| Hook 失效 | fail closed | Fallback，不默认放行 |

---

# 十六、可观测指标

## 16.1 连续性

| 指标 | 目标 |
|---|---:|
| `resume_without_transcript_success_rate` | ≥95% |
| `context_rebuild_success_rate` | ≥99% |
| `handoff_version_match_rate` | ≥99% |
| `resume_preflight_failure_rate` | 建基线并持续下降 |
| `compact_to_verify_bypass_count` | 0 |
| `handoff_claim_used_as_evidence_count` | 0 |

## 16.2 压缩健康度

| 指标 | Claude Code | OpenCode |
|---|---:|---:|
| `lossless_first_rate` | 100% | 100% |
| `compaction_events/session` | <0.2 | <0.5 |
| `L5_rate` | 接近 0 | 不适用 |
| `prune_before_summary_rate` | 不适用 | 100% |
| `lossy_summary_as_truth` | 0 | 0 |
| `artifact_before_prune_rate` | 100% | 100% |

## 16.3 Cache 与成本

```text
prompt_cache_hit_rate ≥70%，目标≥85%
stable_prefix_hash_changes/session ≈0
artifact_preview_reuse_rate ≥95%
token_$/session
token_$/verified_step
input_tokens_before_after_compact
lossy_compaction_token_savings
resume_rebuild_token_cost
```

## 16.4 回滚健康

```text
high_risk_actions_with_checkpoint_rate =100%
external_effects_with_compensation_plan_rate =100%
unknown_action_execution_state_count =0
checkpoint_workspace_mismatch_rate <1%
non_idempotent_replay_count =0
```

---

# 十七、验收测试

## Test R-01：软水位

```text
任务达到 soft watermark。
```

通过：

```text
状态进入 COMPACT_SOON；
当前原子 action 可安全收尾；
handoff 自动生成；
不启动新 step；
不触发 VerifyGate 完成。
```

## Test R-02：硬水位

```text
任务达到 hard watermark。
```

通过：

```text
停止新 action；
未落盘工具结果进入 Artifact；
生成 checkpoint/handoff；
状态进入 RESUME_REQUIRED；
不依赖 LLM 摘要继续执行。
```

## Test R-03：冷恢复

```text
删除当前会话，只保留任务目录和 docs。
```

通过：

```text
从 manifest/state/plan/handoff/working-set/evidence 恢复；
不读取 transcript；
重新编译 Capsule；
current step 一致。
```

## Test R-04：Handoff 伪完成

```text
手工把 handoff 写成“S2 已完成”，state 仍是 RUNNING。
```

通过：

```text
以 state 为准；
不修改 plan；
不跳过 VerifyGate；
记录 handoff 冲突。
```

## Test R-05：失败证据保留

```text
compact 前存在失败测试 E17，之后无新成功证据。
```

通过：

```text
Resume 后 E17 仍为 unresolved failure；
不得因摘要未提到 E17 而消失。
```

## Test R-06：Artifact 损坏

```text
修改 Artifact 内容，使 hash 不匹配。
```

通过：

```text
RESUME_BLOCKED；
证据失效；
不使用 Preview 或 summary 代替。
```

## Test R-07：非幂等副作用

```text
外部 API action 状态停在 STARTED。
```

通过：

```text
恢复时先 reconciliation；
不自动重放；
无法确定时 BLOCKED。
```

## Test R-08：Claude Preview 稳定

```text
同一 Artifact 在 compact 前后重新引用。
```

通过：

```text
Preview 字节完全一致；
render hash 一致；
Prompt Cache 前缀不因改写抖动。
```

## Test R-09：Claude L5 防依赖

```text
模拟平台触发 AutoCompact。
```

通过：

```text
即使摘要遗漏当前 step，CarrorOS 仍从持久状态恢复；
L5 摘要不覆盖 state/handoff；
VerifyGate 不被绕过。
```

## Test R-10：OpenCode 非物理 Prune

```text
Prune 旧回合。
```

通过：

```text
旧消息不进入当前 Context；
SQLite 原始记录仍可审计；
最近两个回合和 skill 输出保留。
```

## Test R-11：OpenCode 摘要冲突

```text
隐藏 Agent 摘要与 state 冲突。
```

通过：

```text
summary 标记 non-authoritative；
以 state 为准；
记录冲突，不静默合并。
```

## Test R-12：模型切换恢复

```text
从 Opus 会话切换到 DeepSeek V4 Flash。
```

通过：

```text
按 Flash profile 重新编译；
D4 全文不被继承；
任务事实不丢失；
mandatory Context 超预算时拆 step，而不是删 Contract。
```

## Test R-13：Checkpoint 边界

```text
文件可回滚，但数据库操作已执行。
```

通过：

```text
系统不声称整体回滚完成；
单独执行数据库补偿或进入 BLOCKED；
Git restore 只处理文件域。
```

## Test R-14：30 Tick 稳定性

```text
执行 30 个 tick，并在中间发生两次会话恢复。
```

通过：

```text
第 30 轮输入不超过第 5 轮的 1.5 倍；
没有 transcript 线性累积；
未依赖 Claude L5；
OpenCode 先 Prune 后 Summary；
最终完成仍有完整 VerifyGate verdict。
```

---

# 十八、最低自动测试签名

```python
def test_soft_watermark_writes_handoff(): ...
def test_hard_watermark_stops_new_action(): ...
def test_handoff_is_not_state_source(): ...
def test_resume_recomputes_current_step(): ...
def test_resume_never_marks_verified(): ...
def test_unresolved_failure_survives_compaction(): ...
def test_artifact_hash_mismatch_blocks_resume(): ...
def test_stale_capsule_is_recompiled(): ...
def test_non_idempotent_action_is_not_replayed(): ...
def test_external_effect_requires_reconciliation(): ...
def test_git_rollback_does_not_claim_external_rollback(): ...
def test_same_artifact_preview_is_byte_stable(): ...
def test_claude_l5_summary_cannot_override_state(): ...
def test_opencode_prune_is_non_destructive(): ...
def test_opencode_prune_precedes_summary(): ...
def test_summary_is_marked_lossy_and_non_authoritative(): ...
def test_recent_two_turns_and_skills_are_preserved(): ...
def test_only_execute_session_can_write_state(): ...
def test_profile_switch_recompiles_context(): ...
def test_thirty_ticks_do_not_grow_context_linearly(): ...
```

---

# 十九、实施顺序

```text
P0：连续性止血
  1. 完整工具结果落 Artifact；
  2. 建稳定 Preview cache；
  3. 建 handoff 模板；
  4. 禁止 transcript 正常恢复；
  5. soft/hard 水位停止规则。

P1：可靠恢复
  6. 实现 Resume Preflight；
  7. state/plan/evidence/hash 一致性校验；
  8. current step 重新计算；
  9. Capsule 重编译；
  10. Resume 后重跑 PreActionGate。

P2：回滚边界
  11. Checkpoint Schema；
  12. Git/workspace 校验；
  13. Action execution ID；
  14. 外部副作用 reconciliation；
  15. 非幂等重放保护。

P3：Claude Code 接入
  16. Stable Core 冻结；
  17. ContentReplacementState 式 Preview 复用；
  18. Cache 指标；
  19. L1-L4 cheapest-first；
  20. L5 依赖告警。

P4：OpenCode 接入
  21. SQLite 审计映射；
  22. hidden Prune；
  23. 最近回合与 skill 保护；
  24. Prune 后有损摘要；
  25. 多会话单一 State Writer。
```

---

# 二十、本部分最终裁决

```text
1. Compact 只能释放上下文，不能制造完成事实；
2. 所有平台压缩之前，先执行 Artifact 落盘和最小 Context 重建；
3. Handoff 是恢复导航，不是状态真相源；
4. Resume 必须从 manifest、state、plan、working-set、documents、evidence 和 checkpoint 重建；
5. Resume 必须重新计算 current step、失败覆盖和外部副作用状态；
6. compact 后禁止依据聊天记忆、handoff 或摘要跳过 VerifyGate；
7. Checkpoint、Git 和外部副作用属于三个不同回滚边界；
8. 非幂等 action 状态不明时必须 BLOCKED，禁止自动重放；
9. Claude Code 采用工具落盘→历史裁剪→微压缩→折叠→L5 的 cheapest-first 路径；
10. Claude L5 是有损不可逆兜底，CarrorOS 对其依赖必须为 0；
11. 同一 Claude tool_result 的 Preview 必须按 hash 原样复用，保护 Prompt Cache；
12. OpenCode 先使用 non-destructive Prune，再使用有损摘要；
13. OpenCode SQLite 是审计链，不是任务状态源；
14. Claude subagent 与 OpenCode 多会话都只能通过结构化 Patch/Verdict 回传；
15. 成功标准是会话丢失后仍可恢复，而不是摘要看起来完整。
```

---

# 下一部分：第 6/8 部分

将完整输出 **代码、Schema、CLI 与 Hook 实现规范**：

```text
- Python 包最终模块结构
- carros_base.py / carros_enhance.py CLI
- task_store.py 原子状态写入
- document_index.py
- context_engine.py
- artifact_store.py
- preaction_gate.py
- verify_gate.py
- continuity.py / resume.py
- JSON Schema 与 YAML 配置
- Claude Code Hook 单入口
- OpenCode 包装器/插件接口
- fail-closed 错误处理
- 可直接建立的最小可运行骨架
- 单元测试目录与执行命令
```

