# CarrorOS 最终整合重构方案
## 第 8/8 部分：Archive、迁移、上线与 Sovereign Verdict

本部分完成最终封存，承接前七章：

```text
第 1/8  四平面架构
第 2/8  任务状态与完成协议
第 3/8  Document-First Memory Plane
第 4/8  Context Engine 与渐进式披露
第 5/8  Compact / Checkpoint / Handoff / Resume
第 6/8  代码、Schema、CLI 与 Hook
第 7/8  模型路由、多 Agent、Oracle、成本与审计
第 8/8  Archive、迁移、上线、SLO 与最终裁决
```

本章冻结 CarrorOS 的最终生命周期：

> **Archive 不是移动文件，而是对“任务状态、验证证据、长期记忆写回和审计链已经一致封存”的事务性证明。**

---

# 一、Archive 的职责边界

## 1.1 Archive 负责

```text
1. 确认任务和全部必需 step 已通过 VerifyGate；
2. 校验 verdict、evidence、Artifact 和 source hash；
3. 确认不存在未解决 question、blocker 和外部副作用；
4. 完成或明确跳过 Memory Writeback；
5. 生成 Final Report；
6. 生成 Evidence Root；
7. 构建不可变归档包；
8. 写 Tombstone；
9. 更新归档索引和 retention 元数据；
10. 将状态原子转换为 ARCHIVED。
```

## 1.2 Archive 不负责

```text
✗ 补造缺失证据；
✗ 把 Oracle ACCEPT 转成 VERIFIED；
✗ 用 handoff 或 summary 证明完成；
✗ 自动接受 WARN；
✗ 删除 unresolved failure；
✗ 猜测外部副作用是否成功；
✗ 静默删除 transcript、SQLite 或 Artifact；
✗ 在归档阶段修改业务实现以“顺便修复”。
```

## 1.3 唯一合法入口

```text
VERIFIED → ARCHIVING → ARCHIVED
```

禁止：

```text
RUNNING → ARCHIVED
WARN → ARCHIVED
REJECTED → ARCHIVED
BLOCKED → ARCHIVED
RESUME_REQUIRED → ARCHIVED
Oracle ACCEPT → ARCHIVED
```

取消任务使用独立终态 `CANCELLED`，不能伪装成成功 Archive。

---

# 二、Archive 触发条件

归档前必须全部成立：

```text
ARC-01 state.status == VERIFIED
ARC-02 每个 required step.status == VERIFIED
ARC-03 每个 verified step 都有 verify_verdict_id
ARC-04 每个 verdict Artifact 存在且 hash 匹配
ARC-05 必需 command/file/user 验证全部 PASS
ARC-06 不存在未覆盖的失败证据
ARC-07 blocker == null
ARC-08 question == null 或已明确回答
ARC-09 无 UNKNOWN / IN_FLIGHT_UNSAFE 外部副作用
ARC-10 workspace 与最终 revision 一致
ARC-11 Memory Writeback 已 APPLIED 或显式 NOT_REQUIRED
ARC-12 文档索引、Contract 测试和链接检查通过
ARC-13 预算、模型、Oracle 记录已完成归因
ARC-14 secrets 扫描通过
ARC-15 retention 和数据分类策略已确定
```

对于 `WARN`：

```text
- 默认禁止 Archive；
- 必须增加风险处置 action；或
- 由 manifest 预先声明的授权主体接受 residual risk；
- 接受记录必须是结构化 user/owner confirmation；
- 之后重新运行 VerifyGate；
- VerifyGate 产生 VERIFIED 后才可 Archive。
```

---

# 三、Archive 事务

## 3.1 最终流程

```text
1. PRECHECK
   读取 manifest/state/plan/verdict/evidence/effects。

2. FREEZE
   获取 State Writer lease 和 archive lock；冻结业务写入。

3. VERIFY
   重新校验 Schema、revision、Artifact hash、失败覆盖链。

4. WRITEBACK
   应用或关闭 Memory Writeback Proposal。

5. REPORT
   生成 Final Report、Evidence Root 和成本摘要。

6. STAGE
   在临时目录构建完整归档包。

7. VALIDATE
   校验归档 manifest、文件 hash、链接、秘密和 retention。

8. PUBLISH
   原子发布归档目录并更新 archive index。

9. TOMBSTONE
   在原任务位置写最小恢复指针。

10. COMMIT
    CAS：ARCHIVING → ARCHIVED。

11. AUDIT
    写 ARCHIVE_COMMITTED 事件并释放 lease。
```

## 3.2 归档目录

```text
.omc/archive/<year>/<task-id>/
├── archive-manifest.yaml
├── final-report.md
├── evidence-root.json
├── manifest.yaml
├── state.final.json
├── plan.md
├── decisions.md
├── handoff.final.md
├── evidence.jsonl
├── verdicts/
├── artifacts/
├── memory-writeback/
├── metrics/
│   ├── model-usage.jsonl
│   ├── context-metrics.jsonl
│   └── cost-summary.json
└── audit/
    └── events.jsonl
```

默认不复制：

```text
- 完整 Claude transcript；
- OpenCode SQLite 全库；
- 未授权 Review 全文；
- cache 文件；
- 临时 Capsule 历史；
- provider 原始秘密；
- 可重建 generated cache。
```

这些按平台和组织 retention 独立管理，并在 archive manifest 中保存审计指针。

## 3.3 原子发布

```text
.omc/archive/.staging/<archive-id>/
    ↓ 全部验证通过
rename / publish
    ↓
.omc/archive/<year>/<task-id>/
```

失败处理：

```text
- 归档包未发布：状态保持 ARCHIVING 或转 BLOCKED；
- 已发布但 state CAS 失败：通过 transaction journal 对账；
- 不允许同一 task-id 存在两个 active archive；
- 重试使用相同 archive_id 和内容 hash，保持幂等；
- 禁止半归档后删除源任务目录。
```

---

# 四、`archive-manifest.yaml`

```yaml
schema_version: carros.archive_manifest.v1
archive_id: AR-fix-auth-001-20260712
 task_id: fix-auth-001
result: VERIFIED
archived_at: "2026-07-12T12:00:00Z"

revisions:
  task_state_version: 18
  manifest_version: 2
  plan_version: 4
  repository_commit: def5678

verification:
  task_verdict_id: V-TASK-004
  step_verdicts:
    S1: V-S1-003
    S2: V-S2-005
  residual_risks: []

memory_writeback:
  status: APPLIED
  writeback_ids: [MW-009]
  documents:
    - CONTRACT-AUTH#error-semantics@v5

integrity:
  evidence_root_sha256: "..."
  archive_tree_sha256: "..."
  artifact_count: 14
  evidence_event_count: 31

cost:
  total_input_tokens: 84200
  total_output_tokens: 9100
  total_cost_usd: 0.82
  verified_steps: 2
  cost_per_verified_step_usd: 0.41

platforms:
  claude_code:
    transcript_ref: audit://claude/session-abc
    l5_count: 0
    cache_metric_source: provider
  opencode:
    sqlite_session_refs: []
    prune_count: 0

retention:
  classification: INTERNAL
  archive_days: 365
  artifact_days: 365
  transcript_policy: organization_default
  legal_hold: false
```

---

# 五、Final Report

Final Report 是可读结论，不是证据替代品。

```markdown
---
schema_version: carros.final_report.v1
task_id: fix-auth-001
result: VERIFIED
task_verdict_id: V-TASK-004
repository_revision: def5678
---

# Final Report

## Goal

修复同一用户并发刷新产生多次上游调用的问题，同时保持公共错误类型。

## Scope Delivered

- 修改 `src/auth/refresh.ts#refreshToken`；
- 增加并发成功和失败清理测试；
- 未修改公共 `RefreshError` 类型。

## Verification

| Verify ID | 结果 | Evidence |
|---|---|---|
| VFY-01 | PASS | E24 |
| VFY-02 | PASS | E27 |
| VFY-03 | PASS | E29 |

## Decisions

- `D-001`：保留 RefreshError；
- `ADR-014#single-flight`：同一用户复用 in-flight promise。

## Residual Risks

无未接受的 residual risk。

## Memory Writeback

- 更新 `CONTRACT-AUTH#error-semantics@v5`；
- Error DNA：`EDNA-017`。

## Cost

- 总成本：$0.82；
- 已验证步骤：2；
- 成本/已验证步骤：$0.41。

## Integrity

- task verdict: `V-TASK-004`；
- evidence root: `...`；
- archive root: `...`。
```

规则：

```text
- 所有完成声明必须能追溯到 verdict；
- 所有测试声明必须能追溯到 Evidence；
- 所有代码状态必须绑定 repository revision；
- 报告不得包含 chain-of-thought；
- WARN、例外和风险接受不得省略。
```

---

# 六、Evidence Root

## 6.1 目的

Evidence Root 给归档证据建立可校验的完整性根。

```json
{
  "schema_version": "carros.evidence_root.v1",
  "task_id": "fix-auth-001",
  "algorithm": "sha256-merkle-v1",
  "event_count": 31,
  "artifact_count": 14,
  "leaves": [
    {
      "ref": "evidence:E24",
      "sha256": "..."
    },
    {
      "ref": "artifact:artifacts/test-E24.log",
      "sha256": "..."
    },
    {
      "ref": "verdict:V-S2-005",
      "sha256": "..."
    }
  ],
  "root_sha256": "...",
  "created_at": "2026-07-12T12:00:00Z"
}
```

## 6.2 规则

```text
- leaf 排序固定；
- hash 算法版本化；
- Artifact 元数据与正文分别校验；
- 缺失 Artifact 不允许生成成功 root；
- 归档后修改任一证据会导致 root 失配；
- 加密 Artifact 的 hash 应针对规定的明文或密文形态，并在策略中固定。
```

---

# 七、Tombstone：删除 token，而不是删除任务身份

旧 `token.json` 不应继续作为活跃状态源，也不应完全无痕删除。

最终方案：

```text
- 活跃任务：使用 state.json；
- 迁移完成：旧 token.json 改名为 token.legacy.json，只读保留一段迁移期；
- 归档成功：删除活跃 state 副本，仅保留 tombstone 指针；
- 任务身份、归档位置和完整性根永久可定位。
```

`.omc/tasks/<date>/<task-id>/tombstone.yaml`：

```yaml
schema_version: carros.task_tombstone.v1
task_id: fix-auth-001
final_status: ARCHIVED
archive_id: AR-fix-auth-001-20260712
archive_path: .omc/archive/2026/fix-auth-001
archived_at: "2026-07-12T12:00:00Z"
repository_revision: def5678
task_verdict_id: V-TASK-004
evidence_root_sha256: "..."
archive_tree_sha256: "..."
```

Tombstone 不包含：

```text
- 完整任务状态；
- 完整 evidence；
- secrets；
- transcript；
- 可被误当作活跃任务的 current_step。
```

---

# 八、BASE / ENHANCE 最终文件集

## 8.1 L1 BASE 必需文件

```text
CLAUDE.md                              Slim Runtime Contract
AGENTS.md                              OpenCode/通用 Agent 入口
.omc/context-engine.yaml
.omc/continuity-policy.yaml
.omc/document-policy.yaml
.omc/model-routing.yaml                仅基础 Flash/Reasoning route
.omc/cost-policy.yaml
.omc/mcp-policy.yaml

.claude/scripts/carros_base.py
.claude/scripts/carros/
  task_store.py
  state_machine.py
  intake_gate.py
  plan_builder.py
  preaction_gate.py
  artifact_store.py
  evidence_store.py
  verify_gate.py
  document_index.py
  context_engine.py
  disclosure_gate.py
  checkpoint.py
  continuity.py
  resume.py
  archive.py
  metrics.py
  platform/claude_code.py
  platform/opencode.py

schemas/**
docs/INDEX.yaml
docs/project/**
docs/architecture/**
docs/contracts/**
docs/adr/**
docs/runbooks/**
tests/unit/**
tests/integration/**
tests/conformance/**
```

## 8.2 L2 ENHANCE 增量文件

```text
.claude/scripts/carros_enhance.py
.claude/scripts/carros/
  routing.py
  research.py
  knowledge_patch.py
  oracle.py
  multi_judge.py
  meta_oracle.py
  provider_health.py
  error_dna.py

schemas/
  knowledge-patch.schema.json
  oracle-verdict.schema.json
  route-decision.schema.json
  model-usage.schema.json

docs/contracts/
  knowledge-patch.md
  oracle-verdict.md

docs/runbooks/
  provider-fallback.md
  multi-agent-conflict.md
```

硬规则：

```text
- ENHANCE 依赖 BASE；
- BASE 不依赖 ENHANCE；
- 关闭 ENHANCE 后，任务仍可通过确定性 VerifyGate 完成；
- Oracle、Multi-Judge、Research 都是可选增强；
- 两条轨共享 state/evidence/archive Contract。
```

---

# 九、Slim `CLAUDE.md` 与 `AGENTS.md`

## 9.1 `CLAUDE.md`

```markdown
# CarrorOS Runtime Contract

1. `state.json` 是唯一任务运行状态源。
2. 每个 tick 只执行一个 action。
3. 工具完整输出写 Artifact，Prompt 只保留稳定 Preview。
4. `denied_paths` 优先于所有允许规则。
5. Context 每轮从持久状态重建，不加载完整 transcript。
6. 额外读取必须提交 Context Request。
7. 只有 VerifyGate 可以将 step/task 标记为 VERIFIED。
8. Handoff、summary、Oracle 和 Review 都不能替代 evidence。
9. Context 达硬水位时停止新 action，写 handoff 后恢复。
10. 高风险或外部副作用必须通过 PreActionGate 和 checkpoint。

入口：
- `python3 .claude/scripts/carros_base.py status --hot`
- `docs/INDEX.yaml`
```

## 9.2 `AGENTS.md`

```markdown
# CarrorOS Agent Entry

- execute：唯一 State Writer；
- retrieve：只产 Knowledge Patch；
- review/oracle：只产 Verdict；
- govern：只读指标和审计；
- OpenCode SQLite 是审计链，不是任务状态源；
- Prune 优先于有损 Summary；
- Summary 必须标记 non-authoritative；
- 所有 action、Context 和完成裁决走 CarrorOS CLI/Gate。
```

这两个入口必须保持短小稳定，禁止复制完整架构文档。

---

# 十、旧系统迁移矩阵

| 旧载体 | 新位置 | 迁移后处理 |
|---|---|---|
| `token.json` | `state.json` | 只读保留迁移期，后转 tombstone |
| `executor.md` | `evidence.jsonl` + `artifacts/**` | 冻结为历史审计，不再追加 |
| 长 `CLAUDE.md` | Slim Core + `docs/**` | 删除动态状态和长说明 |
| `session-handoff.md` | `handoff.md` v1 | 只作导航 |
| 完整审核文档 | `docs/reviews/<source>/**` | authority=advisory，默认拒绝 |
| 长 plan 历史 | 当前 `plan.md` + archive | 活跃任务只保留当前有效计划 |
| transcript 状态恢复 | `state/plan/evidence/handoff` | transcript 仅审计 |
| 工具输出粘贴 | Artifact + Preview | 禁止全文入模 |
| 模型摘要记忆 | 可选 lossy navigation | 禁止覆盖规范和状态 |
| 多 Agent 自由写文件 | Proposal/Patch + 单一 Writer | fail closed |

## 10.1 `token.json` 字段映射

```text
token.task_id          → state.task_id
token.status           → state.status（需合法枚举映射）
token.current_step     → state.current_step
token.turns            → state.context.turns
token.watermark        → state.context.watermark
token.oracle           → verification.oracle（非完成事实）
token.fallback         → context/provider failure records
token.completed_steps  → 仅在存在有效 verdict 时映射 VERIFIED
```

无法证明的旧 `[x]`：

```text
- 不直接迁为 VERIFIED；
- 标为 `LEGACY_UNVERIFIED` 迁移异常；
- 重新运行 VerifyGate；
- 无法重验则 BLOCKED 或历史归档，不得伪造成功。
```

## 10.2 `executor.md` 提取

```text
确定性命令结果     → evidence command_result
文件修改记录       → evidence file_change + patch Artifact
用户确认           → question/confirmation event
失败日志           → Artifact
自然语言推测       → historical note，不成为 evidence
完成声明           → 忽略，等待 VerifyGate
```

---

# 十一、保留、改造、删除清单

## 11.1 保留

```text
✓ Git 历史；
✓ 原始 Artifact；
✓ 已验证 Evidence；
✓ active ADR/Contract；
✓ Claude transcript（按策略）；
✓ OpenCode SQLite（按策略）；
✓ Review 原文，但隔离为 advisory；
✓ 旧 task 归档和 tombstone；
✓ 用户确认的结构化记录。
```

## 11.2 改造

```text
△ token.json → state.json；
△ executor.md → Evidence Ledger；
△ 长 CLAUDE.md → Slim Core；
△ Review 注入 → docs/reviews 默认拒绝；
△ 每五轮状态注入 → 每轮确定性 Capsule 重建；
△ 全 transcript resume → durable-state resume；
△ 模型自由读取 → working-set + DisclosureGate；
△ 模型说完成 → VerifyGate verdict；
△ 多 Agent 直接协作 → Knowledge Patch/Verdict；
△ 单一总 token 预算 → 分区预算与模型 profile。
```

## 11.3 删除

仅在迁移验收和备份完成后删除：

```text
✗ CLAUDE.md 中的动态任务状态；
✗ 每轮重复注入的完整治理文档；
✗ 默认加载的 Grok/Opus/DeepSeek/GPT Review；
✗ Prompt 中的完整工具日志；
✗ 重复状态真相源；
✗ 无来源的“已完成”标记；
✗ 主会话中的 subagent 探索 transcript；
✗ cache 中无法关联 Artifact hash 的 Preview；
✗ 已由新实现替代的重复脚本；
✗ 失效且无审计价值的临时 Capsule。
```

不得自动删除：

```text
- Artifact 原件；
- 审计记录；
- OpenCode SQLite；
- Claude transcript；
- superseded ADR；
- 旧 Review；
- 法律保留数据。
```

它们由 retention policy 决定，而不是由 Context 优化脚本决定。

---

# 十二、Claude Code 上线顺序

```text
CC-1  冻结 Slim CLAUDE.md；
CC-2  工具结果 Artifact 化；
CC-3  建确定性 Preview cache；
CC-4  接入 state/CAS/VerifyGate；
CC-5  接入 Context Capsule 和 Receipt；
CC-6  部署 PreTool Hook，并运行 capability probe；
CC-7  接入 soft/hard watermark 和 handoff；
CC-8  接入 fresh-context subagent；
CC-9  采集 Prompt Cache 指标；
CC-10  启用 L5 依赖告警。
```

上线门：

```text
- Hook probe 通过；
- 同 Artifact Preview 字节稳定；
- prompt cache 指标可用时命中率达到基线；
- L5 不作为恢复源；
- checkpoint 不被误认为外部副作用回滚；
- 删除 transcript 后可恢复任务。
```

Claude 压缩标签必须持续标注：

```text
CC-L1 工具落盘：无损可回滚
CC-L2 已外置历史裁剪：逻辑可恢复
CC-L3 微压缩：轻度有损
CC-L4 折叠：有损
CC-L5 AutoCompact：有损不可逆于当前 Context
```

---

# 十三、OpenCode 上线顺序

```text
OC-1  建 execute/retrieve/review/govern session roles；
OC-2  部署单一 State Writer lease；
OC-3  接入 Artifact/Evidence；
OC-4  接入 Context Capsule；
OC-5  启用 non-destructive Prune；
OC-6  保护最近两回合和 skill 输出；
OC-7  Prune 不足后才启用隐藏摘要 Agent；
OC-8  摘要标记 lossy/non-authoritative；
OC-9  SQLite 接入审计和 retention；
OC-10 启用 BYOK/本地模型隐私路由与 provider 熔断。
```

上线门：

```text
- prune_before_summary_rate = 100%；
- hidden 消息仍可从 SQLite 审计；
- retrieve/review/govern 无 state 写权限；
- 双 writer 测试 fail closed；
- SQLite 不参与 current_step 推断；
- Resume 不依赖隐藏摘要。
```

OpenCode 压缩标签：

```text
Prune(hidden)：非物理删除，可审计回溯
隐藏 Agent Summary：有损，只可导航
SQLite：审计原件，不是任务状态源
```

---

# 十四、30/60/90 天路线图

## 0～30 天：止血与真相统一

目标：先阻止上下文和完成事实继续失控。

```text
- 冻结 state.json；
- 建 CAS 和状态机；
- 建 Artifact/Evidence；
- 建 VerifyGate；
- 缩短 CLAUDE.md/AGENTS.md；
- 隔离 reviews；
- 禁止 transcript 正常恢复；
- 上线 Hot Card；
- 建 token/cost 基线。
```

退出标准：

```text
verified_without_verdict_count = 0
full_tool_output_in_context_rate = 0
review_default_disclosure_count = 0
resume_without_transcript_success_rate ≥ 80%
```

## 31～60 天：Context 与连续性

```text
- working-set 和 section/symbol retrieval；
- Context Capsule/Receipt；
- soft/hard watermark；
- handoff/resume；
- checkpoint/effect reconciliation；
- Claude Preview 稳定复用；
- OpenCode Prune 与单一 Writer；
- 30 tick 非线性增长测试。
```

退出标准：

```text
context_rebuild_success_rate ≥ 99%
resume_without_transcript_success_rate ≥ 95%
input_tokens_per_turn.p95 ≤ 24K
L5 dependency = 0
prune_before_summary_rate = 100%
```

## 61～90 天：增强、成本与归档

```text
- Flash/Opus 路由；
- Knowledge Patch；
- Oracle/Multi-Judge 按需启用；
- provider 熔断；
- 数据分类与本地路由；
- Memory Writeback；
- Archive 事务；
- Evidence Root；
- 成本和治理看板；
- Error DNA。
```

退出标准：

```text
token_$/verified_step 相比基线下降 ≥ 70%
single_state_writer_violation_count = 0
oracle_bypass_verify_count = 0
archive_integrity_pass_rate = 100%
secret_route_violation_count = 0
```

---

# 十五、SLO 与告警

## 15.1 核心 SLO

| SLO | 目标 |
|---|---:|
| 状态 CAS 成功率 | ≥99.9% |
| Context 重建成功率 | ≥99% |
| 无 transcript 恢复成功率 | ≥95% |
| Artifact 完整性通过率 | 100% |
| VerifyGate 越权次数 | 0 |
| Archive 完整性通过率 | 100% |
| 单一 Writer 冲突造成的数据丢失 | 0 |
| Review 默认泄露 | 0 |
| Secret 非授权外传 | 0 |

## 15.2 Context/成本 SLO

```text
Flash input median ≤8K
Reasoning input median ≤16K
全局 input P95 ≤24K
full_document_load_rate <2%
unused_context_ratio <20%
Claude prompt_cache_hit_rate ≥70%，目标≥85%（可观测时）
Claude L5_share ≈0
OpenCode prune_before_summary_rate =100%
compaction_trigger_frequency <0.2/session（初始目标）
token_$/verified_step 较基线下降≥70%
```

## 15.3 告警分级

### P0

```text
- VERIFIED 无 verdict；
- Archive hash 不一致；
- Secret 非授权路由；
- 多 Writer 导致状态覆盖；
- 未确认外部副作用被重放；
- Hook fail-open 执行高风险动作。
```

### P1

```text
- resume 依赖 transcript；
- Artifact 缺失；
- Review 进入执行 Capsule；
- Oracle 绕过 VerifyGate；
- OpenCode summary 成为状态源；
- Claude L5 连续触发。
```

### P2

```text
- cache hit rate 明显下降；
- full document load rate 超标；
- compaction 频率异常；
- token $/verified step 上升；
- stale normative 文档被引用；
- Handoff 频繁失效。
```

---

# 十六、灾难恢复

## 16.1 备份范围

```text
Tier 0：state、manifest、plan、verdict、evidence
Tier 1：Artifact、docs、ADR/Contract、archive
Tier 2：audit、Claude transcript、OpenCode SQLite
Tier 3：cache、generated index（可重建）
```

## 16.2 建议目标

```text
Tier 0/1：RPO ≤5 分钟，RTO ≤30 分钟
Tier 2：按组织审计政策
Tier 3：不设强 RPO，允许重建
```

## 16.3 恢复流程

```text
1. 停止所有 State Writer；
2. 恢复最近一致快照；
3. 校验 transaction journal；
4. 重放已提交的 append-only evidence/audit；
5. 校验 Artifact 和 Evidence Root；
6. 重建 docs/INDEX 与 archive index；
7. 对账外部副作用；
8. 重新生成 handoff 和 Capsule；
9. 任务最多恢复到 RUNNING/BLOCKED；
10. 重新运行 VerifyGate 后才恢复 VERIFIED。
```

禁止从灾难恢复直接设置 `VERIFIED`，除非原 verdict、证据和完整性链全部可验证。

## 16.4 平台差异

### Claude Code

```text
- transcript 可辅助审计，但不重建状态；
- checkpoint 可恢复文件，不恢复外部副作用；
- cache 丢失只影响成本，不影响真相；
- L5 摘要不得成为灾备源。
```

### OpenCode

```text
- SQLite 可恢复审计历史和 hidden 标记；
- SQLite 丢失不应导致任务状态丢失；
- Prune 非物理删除有利于离线调查；
- 多会话恢复前必须重建 writer lease。
```

---

# 十七、端到端验收矩阵

| ID | 场景 | 必须结果 |
|---|---|---|
| E2E-01 | L1 单文件修复 | Flash、窄 Context、Verify、Archive |
| E2E-02 | L2 跨模块设计 | Opus 隔离、Patch、执行轨落地 |
| E2E-03 | 30 tick 长任务 | Context 不线性增长 |
| E2E-04 | Claude 接近 L5 | handoff + 新会话，不依赖 L5 |
| E2E-05 | OpenCode Prune | hidden 可审计，先 Prune 后 Summary |
| E2E-06 | 双 Writer | 第二 writer 被拒绝 |
| E2E-07 | Oracle ACCEPT + 测试失败 | 仍 REJECTED |
| E2E-08 | Artifact 篡改 | Verify/Resume/Archive 全部阻断 |
| E2E-09 | 外部 action 状态 UNKNOWN | 禁止重放，进入 BLOCKED |
| E2E-10 | Secret 数据 | 只路由允许的本地/私有模型 |
| E2E-11 | Context 超 hard | 不删除 Contract，拆 step/切会话 |
| E2E-12 | Review 高相关 | 默认仍不披露 |
| E2E-13 | token.json 旧完成标记 | 无 verdict 则重新验证 |
| E2E-14 | Archive 中途失败 | 无半归档和假 ARCHIVED |
| E2E-15 | 灾难恢复 | 最多恢复 RUNNING，再 Verify |
| E2E-16 | Provider 熔断 | 重编译 Capsule，不绕过 Gate |
| E2E-17 | 模型切换 Opus→Flash | D4 降级为切片 |
| E2E-18 | Memory Writeback 失败 | ARCHIVING/BLOCKED |
| E2E-19 | Tombstone 定位 | 可找到 archive 和 Evidence Root |
| E2E-20 | 成本审计 | 可计算 $/verified step |

---

# 十八、发布门禁

## Gate G-Release-1：状态真相

```text
- 只有一个 active state source；
- token.json 不再参与运行；
- CAS 和非法转换测试通过。
```

## Gate G-Release-2：证据完成

```text
- 无 evidence 不得 VERIFIED；
- Oracle 不得旁路；
- Artifact hash 校验通过。
```

## Gate G-Release-3：Context 稳定

```text
- 第 30 轮输入不超过第 5 轮的 1.5 倍；
- transcript 默认不注入；
- Review 默认拒绝；
- full tool output rate 为 0。
```

## Gate G-Release-4：双栈连续性

```text
Claude：Preview 稳定、L5 非恢复源；
OpenCode：Prune 优先、单一 Writer、SQLite 仅审计。
```

## Gate G-Release-5：Archive

```text
- Final Report 可追溯；
- Evidence Root 可重算；
- Archive 事务可恢复；
- Tombstone 可定位；
- retention 已确定。
```

任一 Gate 失败，不得宣称 CarrorOS 完成生产化。

---

# 十九、最终架构全览图

```text
┌──────────────────────────────────────────────────────────────┐
│                        USER / OPERATOR                       │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Control Plane                                                │
│ CLI · IntakeGate · PlanBuilder · Router · Budget · Policy   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Context Plane                                                │
│ Document Index · Working Set · DisclosureGate · Capsule     │
│ Artifact Preview · Receipt · Compact · Handoff · Resume     │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Execution Plane                                              │
│ Single State Writer · PreActionGate · Checkpoint · Executor │
│ Claude subagent / OpenCode sessions · Provider Fallback     │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Verification Plane                                           │
│ Artifact · Evidence Ledger · VerifyGate · Oracle Review     │
│ Multi-Judge · Residual Risk · Memory Writeback              │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Archive / Audit Plane                                        │
│ Final Report · Evidence Root · Tombstone · Retention        │
│ Claude transcript · OpenCode SQLite · Cost / SLO Dashboard  │
└──────────────────────────────────────────────────────────────┘
```

持久真相关系：

```text
Project Truth      docs/ADR/Contract
Task Truth         manifest/state/plan
Execution Truth    evidence/Artifact
Completion Truth   VerifyGate verdict
Continuity         handoff/checkpoint
Audit Truth        audit/transcript/SQLite
Archive Truth      archive manifest + Evidence Root + tombstone
```

---

# 二十、全系统不可违反的不变量

```text
INV-01  state.json 是唯一任务运行状态源。
INV-02  Context 是可丢弃缓存，不是长期记忆。
INV-03  Transcript 和 SQLite 是审计，不是恢复状态源。
INV-04  每个 tick 只执行一个受 Gate 约束的 action。
INV-05  denied 优先于 allowed。
INV-06  工具完整输出先进入 Artifact。
INV-07  同一 Artifact Preview 按 hash 原样复用。
INV-08  只有 VerifyGate 可以产生 VERIFIED。
INV-09  Oracle、Summary、Handoff、Review 不能替代 Evidence。
INV-10  Compact 后必须从持久状态重建。
INV-11  外部副作用未知时禁止自动重放。
INV-12  Claude L5 是有损兜底，不是 Memory Plane。
INV-13  OpenCode Prune 优先于有损 Summary。
INV-14  多 Agent 只有一个 State Writer。
INV-15  高阶模型不获得跳过 Context 治理的特权。
INV-16  Review 永远默认 advisory/denied。
INV-17  Archive 只能从 VERIFIED 进入。
INV-18  归档必须具备可重算的完整性根。
INV-19  成本按 verified step 归因。
INV-20  隐私和安全策略优先于成本与速度。
```

---

# 二十一、Sovereign Verdict

## 21.1 最终裁决

CarrorOS 的正确定位不是“给 Agent 塞更多上下文”，而是建立一套主权明确的治理操作系统：

```text
文档拥有长期知识主权；
state 拥有运行状态主权；
PreActionGate 拥有行动授权主权；
Artifact/Evidence 拥有执行事实主权；
VerifyGate 拥有完成裁决主权；
Archive 拥有最终封存主权。
```

模型不拥有任何事实主权。模型只拥有受预算、scope、权限和来源约束的推理能力。

## 21.2 对 Claude Code 的最终裁决

```text
- 利用其 Stable Prefix、Prompt Cache、subagent 和 checkpoint；
- 采用 cheapest-first 的 CC-L1→CC-L5 压缩路径；
- 工具结果落盘和 Preview 稳定复用属于常规路径；
- L3/L4 是有损降级；
- L5 AutoCompact 是有损不可逆兜底；
- CarrorOS 对 L5 的记忆依赖必须为 0；
- transcript 只作审计和极端调查。
```

## 21.3 对 OpenCode 的最终裁决

```text
- 利用多会话、SQLite、BYOK、本地模型和可 Hook 源码；
- execute/retrieve/review/govern 必须隔离；
- 单一 State Writer 不可破坏；
- Prune(hidden) 是非物理删除，可审计回溯；
- 有损 Summary 只能在 Prune 后使用；
- SQLite 是审计链，不是 state；
- OpenCode 是 CarrorOS 做深度治理定制的主实验场。
```

## 21.4 对模型路由的最终裁决

```text
- DeepSeek V4 Flash：原子、窄 scope、确定性验证；
- Opus 4.8：高风险、跨模块、架构综合、隔离审查；
- Flash 失败应有界升级；
- Opus 不得通过大 Context 掩盖信息架构缺陷；
- Oracle 不得取代 VerifyGate；
- Multi-Judge 不得用多数票覆盖 critical evidence。
```

## 21.5 对成本治理的最终裁决

最终优化目标不是：

```text
最少 token / 调用
```

而是：

```text
最低 token $ / verified step
+ 可恢复性
+ 可审计性
+ 安全边界不退化
```

必须持续观测：

```text
cache hit rate
compaction 触发频率
Claude L5 占比
OpenCode prune-before-summary rate
token $/session
token $/verified step
resume_without_transcript_success_rate
full_document_load_rate
unused_context_ratio
```

## 21.6 最终 Sovereign Verdict

```text
VERDICT: ACCEPT WITH IMPLEMENTATION GATES

CarrorOS 的最终架构成立。

成立条件：
1. 先统一状态和证据真相源；
2. 再实施 Context 编译和连续性；
3. 再接入 Claude/OpenCode 平台机制；
4. 最后启用 Oracle、多 Agent 和成本优化；
5. 未通过发布门禁前，不宣称生产级完成。

最终成功定义：
- 第 30 轮 Context 不线性增长；
- 删除 transcript 后任务仍可恢复；
- 所有完成声明都有 VerifyGate verdict；
- 所有长工具输出都有 Artifact；
- Claude 不依赖 L5；
- OpenCode 始终先 Prune 后 Summary；
- 多 Agent 不发生状态写冲突；
- Archive 可由 Evidence Root 独立校验；
- token $/verified step 相比旧系统显著下降。
```

---

# 二十二、最终交付清单

```text
[ ] Slim CLAUDE.md
[ ] Slim AGENTS.md
[ ] state/manifest/plan Schema
[ ] CAS Task Store
[ ] PreActionGate
[ ] Artifact/Evidence Store
[ ] VerifyGate
[ ] Document Index
[ ] Working Set
[ ] Context Capsule + Receipt
[ ] Handoff + Resume
[ ] Checkpoint + External Effect Reconciliation
[ ] Claude Code adapter + cache metrics
[ ] OpenCode adapter + single writer + prune audit
[ ] Flash/Opus route policy
[ ] Knowledge Patch
[ ] Optional Oracle/Multi-Judge
[ ] Cost/SLO dashboard
[ ] Memory Writeback
[ ] Archive transaction
[ ] Final Report
[ ] Evidence Root
[ ] Tombstone
[ ] 30-tick、灾备、双栈端到端测试
```

至此，CarrorOS 最终整合重构方案 **8/8 完成**。
