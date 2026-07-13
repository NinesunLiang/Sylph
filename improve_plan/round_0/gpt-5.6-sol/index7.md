# CarrorOS 最终整合重构方案
## 第 7/8 部分：模型路由、多 Agent、Oracle、成本与审计治理

本部分承接前六章，冻结 CarrorOS 的智能调度与增强治理层：

- **DeepSeek V4 Flash**：窄上下文、原子执行、低成本确定性任务；
- **Opus 4.8**：跨模块推理、高风险规划、架构审查与冲突裁决；
- **Claude Code subagent**：fresh context 隔离研究和审查；
- **OpenCode 多会话**：execute / retrieve / review / govern 并行隔离；
- **VerifyGate**：仍是唯一完成门；
- **Oracle**：只提供增强意见，不能制造完成事实。

核心裁决：

> **模型路由决定“谁来思考”，PreActionGate 决定“能否行动”，VerifyGate 决定“是否完成”。Oracle、Multi-Judge、Meta-Oracle 均不得越权。**

---

# 一、治理拓扑

```text
                     ┌─────────────────┐
                     │  Governance     │
                     │  Router         │
                     └────────┬────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       Flash Execute     Reasoning/Plan     Govern/Audit
       原子执行轨         高阶推理轨          只读治理轨
             │                │                │
             ▼                ▼                ▼
       Action Proposal   Knowledge Patch   Metrics/Verdict
             │                │                │
             └──────────┬─────┴────────────────┘
                        ▼
                 Single State Writer
                        │
                        ▼
                  PreActionGate
                        │
                        ▼
                    Executor
                        │
                        ▼
             Artifact + Evidence Store
                        │
                        ▼
                   VerifyGate
```

硬边界：

```text
- Router 不写任务完成状态；
- 子 Agent 不直接修改主 state.json；
- Oracle 不执行未经 Gate 批准的业务动作；
- Meta-Oracle 不补造缺失证据；
- Govern 会话只读；
- execute 轨是唯一 State Writer；
- 所有平台共享领域 Contract，但使用不同隔离机制。
```

---

# 二、任务分类与模型路由

## 2.1 路由输入

模型路由必须基于结构化事实，而不是“更强模型总是更好”：

```yaml
routing_input:
  task_level: L1
  action_kind: atomic_edit
  scope:
    modules: 1
    files: 1
  risk:
    level: medium
    categories: [auth_change, concurrency]
  reasoning:
    ambiguity: low
    cross_module: false
    architecture_synthesis: false
  verification:
    deterministic: true
    command_available: true
  context:
    estimated_tokens: 7200
    disclosure_level: D2
  privacy:
    local_only_required: false
```

## 2.2 路由结果

```yaml
schema_version: carros.route_decision.v1
route_id: ROUTE-023
task_id: fix-auth-001
step_id: S2
action_id: A1
profile: deepseek-v4-flash
session_mode: main_execute
reason_codes:
  - ATOMIC_EDIT
  - SINGLE_MODULE
  - DETERMINISTIC_VERIFY
max_disclosure: D3
fallback_profile: opus-4.8
budget:
  max_input_tokens: 12000
  max_cost_usd: 0.05
created_at: "2026-07-12T10:20:00Z"
```

## 2.3 DeepSeek V4 Flash 路径

适合：

```text
- 精确搜索；
- 单符号或单文件修改；
- 已有明确 Contract；
- 测试命令确定；
- lint、格式化、局部修复；
- Artifact 分类与确定性 Preview；
- 低歧义文档补丁；
- 失败日志的结构化抽取。
```

限制：

```text
- 常态 D0～D2，D3 必须有理由；
- 每 tick 一个 action；
- 每 action 推荐 ≤2 个文件；
- 不承担仓库级架构综合；
- 不读取完整 Review；
- 不用扩大 Context 补偿模型能力；
- 连续两次能力型失败即升级，不重复消耗。
```

## 2.4 Opus 4.8 路径

适合：

```text
- L2 Research/Plan；
- 跨模块架构变化；
- Contract/ADR 冲突；
- 高风险权限、认证、迁移设计；
- 多方案权衡；
- Oracle 或 Multi-Judge 审查；
- Flash 连续出现能力型失败；
- 需要 D4 或隔离 D5 的任务。
```

限制：

```text
- 更强不等于加载更多历史；
- 主执行轨仍只做一个 action；
- D5 必须隔离；
- 输出必须结构化；
- 不直接改 state；
- 不替代 command/file/user 验证；
- 高成本调用必须有 reason_code 和预算授权。
```

## 2.5 规则表

| 条件 | 默认路由 | 会话模式 |
|---|---|---|
| 单文件、低歧义、有确定性测试 | Flash | 主 execute |
| 搜索、索引、日志抽取 | Flash | retrieve 或 execute |
| 跨 3+ 模块 | Opus | 隔离 reasoning |
| 修改公共 Contract | Opus | plan/review |
| 高风险外部副作用 | Opus + 用户确认 | 隔离 plan，execute 落地 |
| D5 全局审查 | Opus | 隔离 review |
| Flash 两次能力失败 | Opus | escalation |
| Provider 不可用 | 兼容模型 | 重新编译 Capsule |
| 隐私要求本地执行 | 本地模型 | OpenCode 本地轨 |

---

# 三、路由引擎

```python
# routing.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    profile: str
    session_mode: str
    max_disclosure: str
    reason_codes: tuple[str, ...]
    max_cost_usd: float
    fallback_profile: str | None


def route_action(action: dict, task: dict, metrics: dict) -> RouteDecision:
    risk = task["risk"]["level"]
    cross_module = action.get("module_count", 1) >= 3
    architecture = action.get("architecture_synthesis", False)
    public_contract = action.get("public_contract_change", False)
    deterministic = action.get("deterministic_verify", False)

    if cross_module or architecture or public_contract or risk == "high":
        return RouteDecision(
            profile="opus-4.8",
            session_mode="isolated_reasoning",
            max_disclosure="D5",
            reason_codes=("HIGH_REASONING_REQUIREMENT",),
            max_cost_usd=1.00,
            fallback_profile=None,
        )

    if metrics.get("capability_failures", 0) >= 2:
        return RouteDecision(
            profile="opus-4.8",
            session_mode="isolated_reasoning",
            max_disclosure="D4",
            reason_codes=("FLASH_CAPABILITY_ESCALATION",),
            max_cost_usd=0.50,
            fallback_profile=None,
        )

    if deterministic and action.get("file_count", 1) <= 2:
        return RouteDecision(
            profile="deepseek-v4-flash",
            session_mode="main_execute",
            max_disclosure="D3",
            reason_codes=("ATOMIC_DETERMINISTIC_ACTION",),
            max_cost_usd=0.05,
            fallback_profile="opus-4.8",
        )

    return RouteDecision(
        profile="opus-4.8",
        session_mode="isolated_reasoning",
        max_disclosure="D4",
        reason_codes=("AMBIGUOUS_ACTION",),
        max_cost_usd=0.50,
        fallback_profile=None,
    )
```

路由结果必须写 audit，但不改变 step 状态。

---

# 四、多 Agent 角色协议

## 4.1 固定角色

```text
execute_agent
  唯一业务执行轨和 State Writer

retrieve_agent
  检索代码、文档和外部资料，只产 Knowledge Patch

plan_agent
  提议计划和风险，不直接推进任务状态

review_agent
  审查 patch、Contract 和 residual risk，只产 Verdict

verify_agent
  可运行确定性验证，但最终状态更新仍经 VerifyGate 服务

govern_agent
  只读成本、缓存、压缩和审计指标

oracle_agent
  高阶语义复核，只产 Oracle Verdict

meta_oracle
  聚合多个已有 Verdict，不读取或修改业务文件
```

## 4.2 权限矩阵

| 角色 | 读 docs/code | 写业务文件 | 写 Artifact | 写 state | 标 VERIFIED |
|---|---:|---:|---:|---:|---:|
| execute | 是 | Gate 后允许 | 是 | 是 | 否，调用 VerifyGate |
| retrieve | 是 | 否 | 是 | 否 | 否 |
| plan | 是 | 否 | 是 | 否 | 否 |
| review | 是 | 否 | 是 | 否 | 否 |
| verify | 是 | 否 | 是 | 仅 VerifyGate 服务 | 仅 VerifyGate |
| govern | 只读 | 否 | 治理报告 | 否 | 否 |
| oracle | 是 | 否 | Verdict | 否 | 否 |
| meta-oracle | Verdict-only | 否 | 聚合 Verdict | 否 | 否 |

## 4.3 单一 State Writer

```yaml
schema_version: carros.writer_lease.v1
task_id: fix-auth-001
session_id: execute-20260712-01
role: execute
acquired_at: "2026-07-12T10:00:00Z"
expires_at: "2026-07-12T10:05:00Z"
state_version: 7
pid: 4812
```

规则：

```text
- 只有 execute role 可以获取 lease；
- lease 续期采用 CAS；
- 子 Agent 返回 proposal，不持有 lease；
- lease 过期不代表外部 action 可重放；
- State Writer 切换前必须写 handoff；
- 双 writer 冲突立即 fail closed。
```

---

# 五、Claude Code 多 Agent 路径

Claude Code 使用 fresh-context subagent 隔离高体积工作。

## 5.1 主会话

主会话只持有：

```text
Stable Core
Hot Card
Current Step
必要 Contract/ADR section
精确代码切片
Evidence Preview
```

## 5.2 Subagent 输入

```yaml
schema_version: carros.subagent_request.v1
request_id: SA-014
role: retrieve
question: 认证刷新 single-flight 的直接调用链和公共错误约束是什么？
scope:
  allowed_paths:
    - src/auth/**
    - tests/auth/**
  denied_paths:
    - docs/reviews/**
    - .env
max_context_tokens: 24000
required_output: carros.knowledge_patch.v1
state_write: false
business_file_write: false
```

## 5.3 Subagent 输出

仅允许：

```text
Knowledge Patch
Plan Proposal
Review Verdict
Oracle Verdict
Evidence Reference
```

禁止返回：

```text
- 完整探索 transcript；
- chain-of-thought；
- 无来源“已完成”；
- 主状态修改建议的直接执行结果；
- 完整工具日志；
- 未脱敏秘密。
```

## 5.4 Claude 缓存治理

```text
- subagent 结果放在高变后缀；
- 返回内容使用固定 Schema；
- 同一 Patch 按 hash 原样复用；
- 不把 subagent transcript 注入主会话；
- 主会话 Stable Core 不随 Agent 数量变化；
- 监控 cache hit rate 和 stable prefix hash。
```

可观测指标：

```text
subagent_context_isolation_rate = 100%
subagent_full_transcript_return_count = 0
main_context_growth_per_subagent ≈ patch_size
prompt_cache_hit_rate ≥ 70%，目标 ≥85%
L5_rate ≈ 0
```

---

# 六、OpenCode 多会话路径

OpenCode 使用同项目多会话隔离：

```text
/session execute
/session retrieve
/session review
/session govern
```

## 6.1 会话规则

### execute

```text
- 唯一 State Writer；
- 执行 Gate 批准的业务 action；
- 接纳或拒绝 Knowledge Patch；
- 调用 VerifyGate；
- 生成 handoff。
```

### retrieve

```text
- 读取 docs/code/SQLite 审计索引；
- 不修改业务文件；
- 不写 state；
- 输出 Knowledge Patch。
```

### review

```text
- 读取候选 patch、Contract 和验证结果；
- 输出 Review/Oracle Verdict；
- 不执行 patch。
```

### govern

```text
- 读取 token、cost、prune、summary、SQLite 指标；
- 不写业务状态；
- 输出治理报告或告警。
```

## 6.2 SQLite 边界

```text
SQLite transcript：审计链
hidden prune 标记：Context 可见性状态
.omc/tasks/**：任务运行真相
Artifact：原始执行证据
```

禁止：

```text
- 从 SQLite 最后一条 assistant 消息推断 current step；
- 把 hidden summary 当 state；
- retrieve/review 会话更新 task status；
- 多个 execute 会话同时获得 writer lease；
- prune 前未保存工具结果原件。
```

## 6.3 OpenCode 容灾优势

可按任务选择：

```text
- 云端 provider；
- BYOK provider；
- 本地 Ollama；
- 数据不出本机的检索/分类轨；
- provider 熔断后的替代模型。
```

但模型切换后必须重新编译 Capsule，不能复用旧模型的高体积 Context。

---

# 七、Knowledge Patch 接纳协议

隔离 Agent 的输出不能自动进入主任务事实链。

## 7.1 接纳流程

```text
1. 校验 Patch Schema；
2. 校验 producer role；
3. 校验每个 source_ref；
4. 校验 source hash/revision；
5. 检查 authority/freshness；
6. 检查是否越出任务 scope；
7. 识别冲突和 unsourced claim；
8. 主 execute 决定 ACCEPT / PARTIAL / REJECT；
9. 接受结果写 Artifact + audit；
10. 必要时更新 working-set，不直接更新 VERIFIED。
```

## 7.2 接纳 Verdict

```yaml
schema_version: carros.patch_acceptance.v1
patch_id: KP-018
decision: PARTIAL
accepted_claims: [C1, C2]
rejected_claims: [C3]
reasons:
  C3: source_is_stale
state_version: 7
accepted_by: execute-20260712-01
created_at: "2026-07-12T10:30:00Z"
```

Patch 接纳只表示“允许作为本轮知识输入”，不表示代码正确或任务完成。

---

# 八、Oracle 的严格边界

## 8.1 Oracle 的职责

Oracle 回答：

```text
- 实现是否符合架构意图？
- 是否存在遗漏的边界条件？
- Contract 是否有语义风险？
- 是否需要额外验证？
- 当前 residual risk 是否可接受？
- 哪些问题应升级 ADR 或用户裁决？
```

Oracle 不回答：

```text
✗ 必需测试是否真的退出 0；
✗ Artifact 是否存在且 hash 匹配；
✗ 用户是否已经明确确认；
✗ step 是否可以绕过 VerifyGate；
✗ 外部副作用是否实际完成；
✗ Archive 是否可执行。
```

## 8.2 Oracle 触发条件

默认不调用。满足以下条件才触发：

```text
- L2 manifest 显式要求；
- 公共 Contract 改变；
- 权限、认证、支付或迁移高风险；
- 两个 active 规范出现语义冲突；
- VerifyGate 基础验证通过但 residual risk 较高；
- Flash 连续两次能力型失败；
- 用户明确要求高阶审查；
- Archive policy 要求独立审查。
```

不得因为“还有预算”调用 Oracle。

## 8.3 Oracle Verdict

```yaml
schema_version: carros.oracle_verdict.v1
verdict_id: OV-009
task_id: fix-auth-001
step_id: S2
reviewed_revision: abc1234
model_profile: opus-4.8
verdict: WARN
basis:
  patch_artifact: artifacts/patch-E17.diff
  contracts:
    - CONTRACT-AUTH#error-semantics@v4
  verify_verdicts:
    - V-S2-005
findings:
  - id: O1
    severity: medium
    text: 失败后的 in-flight promise 清理路径尚缺并发回归测试。
    source_refs:
      - src/auth/refresh.ts#refreshToken@abc1234
required_actions:
  - add_failure_cleanup_concurrency_test
residual_risks:
  - failed_promise_reuse
created_at: "2026-07-12T10:40:00Z"
```

Oracle verdict：

```text
ACCEPT
WARN
REJECT
BLOCKED
```

映射规则：

```text
Oracle ACCEPT：不能自动映射为 VERIFIED
Oracle WARN：任务进入 WARN 或返回 RUNNING，按 policy
Oracle REJECT：返回 RUNNING，建立修复 step/action
Oracle BLOCKED：进入 BLOCKED，记录缺失输入
```

基础验证失败时，即使 Oracle ACCEPT，VerifyGate 仍返回 `REJECTED/BLOCKED`。

---

# 九、Multi-Judge 与 Meta-Oracle

## 9.1 使用条件

Multi-Judge 只用于高价值、高风险或有争议任务：

```text
- 安全边界；
- 数据迁移；
- 公共协议变更；
- 多个架构路线难以裁决；
- 单一 Oracle 出现低置信度；
- 用户明确要求多模型复核。
```

不用于普通 lint、局部 bugfix 或每个 L1 step。

## 9.2 Judge 隔离

每个 Judge 获得相同的审查包：

```text
- 冻结的 patch revision；
- 相同 Contract/ADR section；
- 相同 VerifyGate verdict；
- 相同问题；
- 相同输出 Schema；
- 不读取其他 Judge 的结论。
```

这避免互相锚定。

## 9.3 Meta-Oracle 输入

Meta-Oracle 只接收：

```text
- Judge Verdict；
- Finding IDs；
- source_refs；
- severity；
- confidence；
- disagreement matrix。
```

默认不接收完整代码库和 transcript。

## 9.4 聚合规则

```python
def aggregate_judges(verdicts: list[dict], policy: dict) -> dict:
    if any(v["verdict"] == "BLOCKED" for v in verdicts):
        return {"verdict": "BLOCKED", "reason": "judge_input_incomplete"}

    critical_rejects = [
        v for v in verdicts
        if v["verdict"] == "REJECT"
        and any(f["severity"] == "critical" for f in v.get("findings", []))
    ]
    if critical_rejects:
        return {"verdict": "REJECT", "reason": "critical_finding"}

    rejects = sum(v["verdict"] == "REJECT" for v in verdicts)
    warns = sum(v["verdict"] == "WARN" for v in verdicts)

    if rejects >= policy.get("reject_quorum", 2):
        return {"verdict": "REJECT", "reason": "reject_quorum"}
    if rejects or warns:
        return {"verdict": "WARN", "reason": "residual_disagreement"}
    return {"verdict": "ACCEPT", "reason": "all_accept"}
```

硬规则：

```text
- Critical finding 不可被简单多数票覆盖；
- 无 source_ref 的 finding 不进入强制裁决；
- Judge 缺失不能由 Meta-Oracle 猜测补齐；
- 聚合 ACCEPT 仍不能替代 VerifyGate；
- 分歧必须保留，不能只输出平均结论。
```

---

# 十、Model Pass Curve

CarrorOS 不允许同一失败在模型间无限循环。

## 10.1 Pass 序列

```text
Pass 0：确定性工具与规则
Pass 1：Flash 原子执行
Pass 2：Flash 自修复一次
Pass 3：Opus 隔离诊断/规划
Pass 4：Oracle Review
Pass 5：Multi-Judge（仅高风险）
Pass 6：ASK_USER 或 BLOCKED
```

## 10.2 失败分类

```text
EXECUTION_FAILURE
  工具失败、语法错误、测试失败；可在同轨修复

CAPABILITY_FAILURE
  无法建立正确计划、反复误解 Contract；升级模型

CONTEXT_FAILURE
  必需上下文不适配 profile；拆 step 或切会话

PROVIDER_FAILURE
  超时、限流、服务不可用；执行 provider fallback

POLICY_FAILURE
  scope、权限、安全、预算被 Gate 拒绝；不能靠换模型绕过

EVIDENCE_FAILURE
  缺 Artifact/hash/user confirmation；不能靠 Oracle 修复
```

## 10.3 防循环规则

```text
- 同一 profile、同一输入、同一失败最多重试一次；
- 重试必须有新增证据或修改后的 action；
- 能力失败升级模型，不无限重试 Flash；
- Provider 失败可以切 provider，但保留相同治理 Contract；
- Policy/Evidence 失败禁止模型升级绕过；
- 达到 max_passes 后 ASK_USER 或 BLOCKED。
```

---

# 十一、Fallback、熔断与容灾

## 11.1 Provider 状态

```text
HEALTHY
DEGRADED
OPEN
HALF_OPEN
DISABLED
```

## 11.2 熔断输入

```text
timeout_rate
429_rate
5xx_rate
invalid_response_rate
schema_failure_rate
latency_p95
cost_spike
context_limit_failures
```

## 11.3 建议规则

```yaml
circuit_breaker:
  window: 20
  open_when:
    consecutive_failures: 3
    timeout_rate: 0.30
    invalid_schema_rate: 0.20
  cool_down_seconds: 120
  half_open_probes: 1
```

## 11.4 Fallback 矩阵

| 失败 | 合法处理 | 禁止处理 |
|---|---|---|
| Flash provider 超时 | 同能力 provider 或 Opus fallback | 忽略 Gate |
| Opus 不可用、Oracle 非强制 | 降回 Base 并记录 residual risk | 伪造 ACCEPT |
| Opus 不可用、Oracle 强制 | BLOCKED | 直接 Archive |
| 本地隐私任务云模型不可用 | 本地模型或 BLOCKED | 数据外传 |
| Context 超限 | 重编译/拆 step/新会话 | 删除 Contract |
| 预算耗尽 | ASK_USER/BLOCKED | 隐藏继续计费 |
| Schema 连续失败 | 熔断该 route | 把自由文本当结构化 Verdict |

## 11.5 模型切换

任何 fallback 后必须：

```text
1. 保存当前 state；
2. 记录 provider failure Artifact；
3. 选择兼容 profile；
4. 按新预算重编译 Capsule；
5. 生成新 Disclosure Receipt；
6. 重跑 PreActionGate；
7. 不重放非幂等 action；
8. 不继承旧模型的隐藏推断。
```

---

# 十二、预算闸门

## 12.1 预算层级

```text
action budget
step budget
task budget
session budget
daily/project budget
provider budget
```

## 12.2 配置

```yaml
schema_version: carros.cost_policy.v1

currency: USD

budgets:
  action:
    flash: 0.05
    reasoning: 0.50
    oracle: 0.75
  task:
    L1_soft: 0.50
    L1_hard: 1.00
    L2_soft: 5.00
    L2_hard: 10.00
  daily_project_hard: 50.00

approval:
  require_user_above_task_usd: 10.00
  require_reasoning_route_reason: true
  require_multi_judge_reason: true

limits:
  max_oracle_calls_per_task: 2
  max_judges_per_round: 3
  max_model_passes: 5
  max_same_failure_retries: 1

on_soft_limit:
  decision: WARN
  actions:
    - prefer_flash
    - reduce_disclosure
    - disable_optional_oracle

on_hard_limit:
  decision: ASK_USER_OR_BLOCK
  allow_safety_verification: true
```

## 12.3 预算原则

```text
- 安全验证不能因预算软限被静默跳过；
- 达到硬限时允许完成正在进行的最小安全收尾；
- 新增高阶调用必须重新授权；
- 已花成本不能成为继续错误路线的理由；
- 成本优化以 verified step 为单位，而不是只看单次调用价格。
```

---

# 十三、成本归因

每次模型调用写入：

```json
{
  "schema_version": "carros.model_usage.v1",
  "usage_id": "MU-081",
  "task_id": "fix-auth-001",
  "step_id": "S2",
  "action_id": "A1",
  "session_role": "execute",
  "route_id": "ROUTE-023",
  "provider": "configured-provider",
  "model_profile": "deepseek-v4-flash",
  "input_tokens": 7200,
  "output_tokens": 640,
  "cache_read_tokens": 5100,
  "cache_write_tokens": 900,
  "estimated_cost_usd": 0.034,
  "pricing_revision": "2026-07-12",
  "compaction_generation": 0,
  "result": "ACTION_PROPOSAL",
  "created_at": "2026-07-12T10:25:00Z"
}
```

若 provider 不提供真实 cache 指标：

```json
{
  "cache_read_tokens": null,
  "cache_metric_source": "unavailable"
}
```

禁止用估算值冒充真实命中。

## 13.1 核心公式

```text
model_cost
  = input_tokens × input_price
  + output_tokens × output_price
  + cache_write_tokens × cache_write_price
  + cache_read_tokens × cache_read_price

token_$/session
  = Σ model_cost in session

token_$/verified_step
  = Σ step model_cost / verified step count

effective_cache_hit_rate
  = cache_read_tokens / cache_eligible_input_tokens

compaction_savings
  = projected_uncompacted_tokens - actual_post_compact_tokens

oracle_roi
  = avoided_rework_cost - oracle_cost
```

`oracle_roi` 无法可靠量化时应标记 unknown，不编造收益。

---

# 十四、成本看板

最低看板：

```text
By Task
- total tokens
- total USD
- USD / verified step
- model pass count
- Oracle calls
- compaction events

By Model/Profile
- success rate
- first-pass verify rate
- average cost/action
- capability escalation rate
- schema failure rate

Claude Code
- prompt cache hit rate
- stable prefix hash changes
- cache read/write tokens
- CC-L1～L5 分布
- L5 占比

OpenCode
- prune frequency
- prune-before-summary rate
- hidden summary count
- SQLite audit retention
- session writer conflicts

Context
- median/P95 input tokens
- full document load rate
- unused context ratio
- disclosure level distribution
```

目标指标：

```text
cache_hit_rate ≥70%，目标≥85%             # Claude 可观测时
L5_rate ≈0                               # Claude
prune_before_summary_rate =100%           # OpenCode
compaction_trigger_frequency <0.2/session # 初始目标，按基线调整
token_$/session 持续下降
token_$/verified_step 相比基线下降≥70%
verified_without_evidence =0
oracle_bypass_count =0
```

---

# 十五、合规、隐私与审计

## 15.1 数据分类

```text
PUBLIC
INTERNAL
CONFIDENTIAL
SECRET
REGULATED
```

每个 route 必须检查：

```text
- provider 是否允许该数据等级；
- 是否要求本地模型；
- Artifact 是否需要加密；
- transcript 是否允许保留；
- retention 多久；
- 是否允许进入外部 Oracle。
```

## 15.2 路由约束

```yaml
privacy:
  PUBLIC:
    allowed_routes: [cloud, local]
  INTERNAL:
    allowed_routes: [approved_cloud, local]
  CONFIDENTIAL:
    allowed_routes: [approved_cloud_private, local]
  SECRET:
    allowed_routes: [local]
  REGULATED:
    allowed_routes: [policy_specific]
    require_audit: true
```

## 15.3 OpenCode SQLite

OpenCode 的本地 SQLite 与 non-destructive prune 可用于：

```text
- 会话审计；
- hidden 前后可见性追踪；
- 争议调查；
- provider/模型调用关联；
- 多会话行为审计。
```

但必须：

```text
- 设置文件权限；
- 按组织策略加密磁盘或数据库；
- 记录 retention；
- 防止任意 retrieve Agent 全库读取；
- 不把 SQLite 当 state.json；
- 删除请求同时处理 SQLite、Artifact 和索引。
```

## 15.4 Claude Code

Claude 侧企业治理应对齐：

```text
- Permission Modes；
- .claude/settings.json 细粒度权限；
- transcript 保留策略；
- CLAUDE.md 不写秘密；
- MCP server allowlist；
- 组织层密钥和访问策略；
- checkpoint 与 Git 审计。
```

---

# 十六、Error DNA 学习飞轮

只有可复现、经验证的失败模式才能进入 Error DNA。

```yaml
schema_version: carros.error_dna.v1
error_id: EDNA-017
category: concurrency
signature:
  command: pnpm test tests/auth/refresh.test.ts
  diagnostic_pattern: "received [2-9] upstream calls"
root_cause:
  summary: in-flight promise 在异步调用后才注册
  source_task: fix-auth-001
  source_verdict: V-S2-005
prevention:
  contract_ref: ADR-014#single-flight
  required_test: concurrent_refresh_single_call
applicability:
  paths: [src/auth/**]
confidence: verified
```

禁止写入：

```text
- Oracle 未验证猜测；
- 单次 provider 输出错误；
- 无 Artifact 的“模型记得”；
- 用户未确认的业务偏好；
- 过度泛化的项目规则。
```

用途：

```text
- Intake 风险分类；
- PlanBuilder 自动建议验证；
- PreActionGate 风险升级；
- Oracle 触发条件；
- 成本路由优化。
```

Error DNA 不能自动把任务标完成。

---

# 十七、可粘贴路由配置

```yaml
# .omc/model-routing.yaml
schema_version: carros.model_routing.v1

profiles:
  deepseek-v4-flash:
    class: flash
    roles: [execute, retrieve]
    max_disclosure: D3
    max_files_per_action: 2
    deterministic_verify_preferred: true
    architecture_synthesis: false

  opus-4.8:
    class: reasoning
    roles: [plan, review, oracle, meta_oracle]
    max_disclosure: D4
    d5_requires_isolation: true
    max_files_per_action: 4

routes:
  - when:
      action_kind: [search, atomic_edit, targeted_test, log_extract]
      max_risk: medium
      max_files: 2
    use: deepseek-v4-flash

  - when:
      any:
        - cross_module: true
        - architecture_synthesis: true
        - public_contract_change: true
        - risk: high
    use: opus-4.8
    isolated_session: true

escalation:
  capability_failures_before_upgrade: 2
  same_failure_retries: 1
  max_model_passes: 5

oracle:
  default_enabled: false
  triggers:
    - high_risk
    - public_contract_change
    - unresolved_normative_conflict
    - explicit_user_request
  max_calls_per_task: 2

multi_judge:
  default_enabled: false
  max_judges: 3
  reject_quorum: 2
  critical_finding_veto: true

fallback:
  recompile_context_on_model_change: true
  preserve_governance_contract: true
  forbid_policy_bypass: true
  forbid_evidence_bypass: true
```

---

# 十八、Claude Code 配置片段

```json
{
  "env": {
    "CARROS_ROUTING_CONFIG": ".omc/model-routing.yaml",
    "CARROS_COST_POLICY": ".omc/cost-policy.yaml",
    "CARROS_DEFAULT_EXEC_PROFILE": "deepseek-v4-flash",
    "CARROS_REASONING_PROFILE": "opus-4.8",
    "CARROS_ORACLE_DEFAULT": "0",
    "CARROS_SINGLE_STATE_WRITER": "1",
    "CARROS_SUBAGENT_STATE_WRITE": "0",
    "CARROS_FAIL_CLOSED": "1"
  },
  "permissions": {
    "defaultMode": "default"
  }
}
```

Claude 路径额外规则：

```text
- 研究和 Oracle 使用 fresh-context subagent；
- subagent 返回固定 Schema；
- 主会话只接收 Patch/Verdict；
- Prompt Cache 指标可用时必须采集；
- 同一工具 Preview 原样复用；
- L5 AutoCompact 不作为模型路由策略。
```

---

# 十九、OpenCode 配置片段

以下为 CarrorOS 包装器配置，不冒充 OpenCode 原生 Schema：

```json
{
  "carros": {
    "routing": {
      "config": ".omc/model-routing.yaml",
      "defaultExecuteProfile": "deepseek-v4-flash",
      "reasoningProfile": "opus-4.8",
      "recompileOnSwitch": true
    },
    "sessions": {
      "roles": ["execute", "retrieve", "review", "govern"],
      "singleStateWriter": true,
      "writerRole": "execute"
    },
    "oracle": {
      "defaultEnabled": false,
      "isolatedSession": true,
      "stateWrite": false
    },
    "privacy": {
      "allowLocalModels": true,
      "denyCloudForSecret": true
    },
    "audit": {
      "preserveSQLite": true,
      "recordModelUsage": true,
      "recordRouteDecision": true
    },
    "compaction": {
      "pruneBeforeSummary": true,
      "summaryAuthoritative": false
    }
  }
}
```

---

# 二十、CLI 冻结

```bash
# 查看路由建议
python3 .claude/scripts/carros_enhance.py route \
  --task-id fix-auth-001 \
  --action-file action.json \
  --json

# 启动隔离研究
python3 .claude/scripts/carros_enhance.py research \
  --task-id fix-auth-001 \
  --question-file research.yaml \
  --profile opus-4.8

# 接纳 Knowledge Patch
python3 .claude/scripts/carros_enhance.py knowledge-patch accept \
  --task-id fix-auth-001 \
  --patch KP-018 \
  --claims C1,C2

# 条件触发 Oracle
python3 .claude/scripts/carros_enhance.py oracle \
  --task-id fix-auth-001 \
  --if-required

# Multi-Judge
python3 .claude/scripts/carros_enhance.py multi-judge \
  --task-id migration-001 \
  --judges 3

# 聚合已有 Verdict
python3 .claude/scripts/carros_enhance.py meta-oracle \
  --task-id migration-001 \
  --verdicts OV-01,OV-02,OV-03

# 成本状态
python3 .claude/scripts/carros_base.py cost status \
  --task-id fix-auth-001

# Provider 熔断状态
python3 .claude/scripts/carros_base.py provider health --json

# 审计单一 Writer
python3 .claude/scripts/carros_base.py sessions writer \
  --task-id fix-auth-001
```

CLI 不得：

```text
- 把 Oracle ACCEPT 显示为任务 VERIFIED；
- 把估算 cache hit 冒充真实指标；
- 自动启动高成本 Multi-Judge；
- 因 provider fallback 跳过 Capsule 重编译；
- 允许 govern/retrieve/review 会话写 state。
```

---

# 二十一、可观测指标

## 21.1 模型路由

```text
route_count_by_profile
flash_first_pass_verify_rate
flash_to_reasoning_escalation_rate
reasoning_route_reason_distribution
same_failure_retry_count
model_passes_per_task
profile_switch_recompile_rate = 100%
```

## 21.2 多 Agent

```text
subagent_context_isolation_rate = 100%
knowledge_patch_source_valid_rate = 100%
full_subagent_transcript_return_count = 0
single_state_writer_violation_count = 0
multi_session_state_conflict_rate = 0
patch_acceptance_rate
```

## 21.3 Oracle

```text
oracle_calls/task
oracle_trigger_reason_distribution
oracle_accept_warn_reject_rate
oracle_bypass_verify_count = 0
multi_judge_disagreement_rate
critical_finding_override_count = 0
oracle_cost/verified_task
```

## 21.4 成本与压缩

```text
input_tokens/session
output_tokens/session
token_$/session
token_$/verified_step
cache_hit_rate                         # 可观测时
compaction_trigger_frequency
L5_share                               # Claude
prune_before_summary_rate              # OpenCode
context_tokens_before_after_compaction
provider_cost_by_role
```

## 21.5 合规

```text
secret_route_violation_count = 0
unauthorized_cloud_route_count = 0
SQLite_retention_compliance_rate = 100%
Artifact_encryption_required_but_missing = 0
review_or_oracle_unsourced_claim_rate
model_usage_records_with_pricing_revision = 100%
```

---

# 二十二、验收测试

## Test A-01：Flash 原子路由

```text
单文件修改，有确定性测试，风险 medium。
```

通过：路由到 Flash；D3 上限；一个 action；成本预算生效。

## Test A-02：架构升级

```text
跨四个模块并修改公共 Contract。
```

通过：路由 Opus 隔离会话；主执行 Context 不加载全局探索过程。

## Test A-03：Subagent 状态越权

```text
Claude retrieve subagent 尝试写 state.json。
```

通过：Gate 拒绝；只允许返回 Knowledge Patch。

## Test A-04：OpenCode 双 Writer

```text
两个 execute 会话同时申请 lease。
```

通过：仅一个成功；另一个 fail closed；无状态覆盖。

## Test A-05：Patch 无来源

```text
Knowledge Patch 的关键 claim 无 source_ref。
```

通过：不能作为 normative 输入；拒绝或降为 unsourced advisory。

## Test A-06：Oracle 越权

```text
基础测试失败，Oracle 返回 ACCEPT。
```

通过：任务仍为 REJECTED/BLOCKED；不得 VERIFIED。

## Test A-07：Multi-Judge Critical

```text
两个 ACCEPT，一个带来源的 critical REJECT。
```

通过：Meta-Oracle 不用多数票覆盖 critical finding。

## Test A-08：Provider 熔断

```text
Flash provider 连续三次超时。
```

通过：熔断；切换 provider/profile；重新编译 Capsule；不重复非幂等 action。

## Test A-09：预算硬限

```text
L1 task 达到 hard budget。
```

通过：ASK_USER 或 BLOCKED；不静默启动 Opus/Oracle；必需安全验证不被伪造通过。

## Test A-10：真实 Cache 指标缺失

```text
Provider 不返回 cache usage。
```

通过：指标为 null/unavailable；不生成虚假命中率。

## Test A-11：Secret 路由

```text
任务数据分类为 SECRET，云模型候选成本更低。
```

通过：仍只允许本地 route；成本不能覆盖隐私策略。

## Test A-12：OpenCode Prune 审计

```text
会话消息被 hidden prune。
```

通过：当前 Context 不加载；SQLite 仍保留审计；summary 不成为任务真相。

## Test A-13：模型失败循环

```text
同一 Flash 输入连续失败。
```

通过：最多一次同轨重试；随后升级、ASK_USER 或 BLOCKED，不无限循环。

## Test A-14：成本归因

```text
一个 step 使用 Flash、Opus Review 和一次 compact。
```

通过：所有 usage 归因到同一 task/step/route；可计算 `$/verified_step`。

---

# 二十三、最低自动测试签名

```python
def test_atomic_action_routes_to_flash(): ...
def test_architecture_change_routes_to_reasoning(): ...
def test_route_does_not_modify_state(): ...
def test_profile_switch_recompiles_capsule(): ...
def test_subagent_cannot_write_state(): ...
def test_only_execute_session_gets_writer_lease(): ...
def test_knowledge_patch_requires_source_refs(): ...
def test_oracle_accept_cannot_bypass_failed_verify(): ...
def test_meta_oracle_preserves_critical_reject(): ...
def test_multi_judge_outputs_are_isolated(): ...
def test_same_failure_retry_is_bounded(): ...
def test_policy_failure_cannot_be_solved_by_model_upgrade(): ...
def test_provider_circuit_breaker_opens(): ...
def test_non_idempotent_action_is_not_replayed_after_fallback(): ...
def test_hard_budget_requires_user_or_blocks(): ...
def test_missing_cache_metrics_are_marked_unavailable(): ...
def test_secret_data_never_routes_to_cloud(): ...
def test_opencode_sqlite_is_audit_not_state(): ...
def test_oracle_usage_is_attributed_to_task_and_step(): ...
def test_token_cost_per_verified_step_is_computable(): ...
```

---

# 二十四、实施顺序

```text
P0：路由与成本底座
  1. RouteDecision Schema；
  2. Flash/Opus profile；
  3. model usage 记录；
  4. action/task 预算 Gate；
  5. provider health 与熔断。

P1：Agent 隔离
  6. 固定角色权限矩阵；
  7. Knowledge Patch；
  8. Claude subagent adapter；
  9. OpenCode session role；
  10. 单一 State Writer lease。

P2：Oracle
  11. Oracle trigger policy；
  12. Oracle Verdict Schema；
  13. VerifyGate 越权测试；
  14. residual risk 写回；
  15. Oracle 成本归因。

P3：Multi-Judge
  16. 同构审查包；
  17. Judge 隔离；
  18. Meta-Oracle 聚合；
  19. critical veto；
  20. 分歧审计。

P4：合规与优化
  21. 数据分类路由；
  22. 本地模型策略；
  23. SQLite/Artifact retention；
  24. 成本看板；
  25. Error DNA 学习飞轮。
```

---

# 二十五、本部分最终裁决

```text
1. 模型路由只决定执行/推理资源，不决定完成状态；
2. DeepSeek V4 Flash 用于窄 scope、原子动作和确定性验证场景；
3. Opus 4.8 用于跨模块、高风险、架构综合与隔离审查；
4. 更强模型不能成为加载完整历史和无关上下文的理由；
5. Claude Code 使用 fresh-context subagent，主会话只接收结构化 Patch/Verdict；
6. OpenCode 使用 execute/retrieve/review/govern 多会话，只有 execute 可以写 state；
7. Knowledge Patch 必须带来源、revision 和 hash，接纳后也不等于验证通过；
8. Oracle 只做语义复核，不能替代 command/file/user VerifyGate；
9. Multi-Judge 必须隔离，Meta-Oracle 只能聚合已有 Verdict；
10. Critical finding 不得被简单多数票覆盖；
11. 同一失败的重试次数必须有界，Policy/Evidence 失败不能通过换模型绕过；
12. Provider fallback 后必须重新编译 Capsule 并重跑 PreActionGate；
13. 成本必须归因到 task/step/action/role，核心指标是 token $/verified step；
14. Claude 必须监控 cache hit、compaction 和 L5 占比；
15. OpenCode 必须监控 prune-before-summary、SQLite 审计和 writer conflict；
16. 数据分类和隐私策略优先于成本最优路由；
17. Error DNA 只吸收经 VerifyGate 支撑的可复现失败模式；
18. 成功标准是更低成本获得可验证结果，而不是调用更多模型。
```

---

# 下一部分：第 8/8 部分

将完成 **最终归档、迁移、删除清单与 Sovereign Verdict**：

```text
- Archive 最终触发条件与事务
- Final Report / Tombstone / Evidence Root
- BASE / ENHANCE 最终文件集
- 旧 token.json、executor.md、长 CLAUDE.md 的迁移
- 保留、改造、删除清单
- Claude Code / OpenCode 上线顺序
- 30/60/90 天实施路线图
- SLO、告警与治理看板
- 回滚和灾难恢复
- 全系统端到端验收矩阵
- 最终架构全览图
- Sovereign Verdict
```

