---
name: lx-oma-orch

description: Pipeline Orchestrator — 4-skill 管线编排（状态查看/阶段推进/Oracle 门禁/并行开发管理）

version: v1.2.0
harness_version: "6.1.9"
model: sonnet
argument-hint: "status | advance [--force] | gate <og-id> approve|reject [--reason \"...\"] | run <target> | dev list | dev mark <feature-id> <status>"
when_to_use: |
  当需要查看 PRD 全生命周期管线进度时；
  当需要推进到下一阶段（检查 Oracle 门禁后自动调用对应 skill）时；
  当需要裁决 Oracle 门禁时；
  当需要直接路由到指定子 skill 时；
  当需要管理并行开发进度时

triggers:
  - "/lx-oma-orch"
  - "pipeline"
  - "管线状态"
  - "orchestrate"
role: "Pipeline orchestrator — 4-skill lifecycle orchestration with Oracle gates"
execution_mode: stepwise
---

# lx-oma-orch Pipeline Orchestrator

**触发语**: `/lx-oma-orch`, `pipeline`, `管线状态`, `orchestrate`

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| oracle | `../../nodes/oracle_terminal.md` | 阶段转移门禁裁决 |
| mode_selector | `../../nodes/mode_selector.md` | 根据 skill frontmatter 确定执行模式，挂载对应门禁 |

### 本 skill 参考文档

| 文件 | 用途 |
|------|------|
| `state/pipeline.yaml` | 统一状态机 — 所有 skill 的共享状态 |
| `.claude/skills/lx-oma-hier/SKILL.md` | Level 1 分层拆解 |
| `.claude/skills/lx-oma-split/SKILL.md` | Level 2 特性拆解 |
| `.claude/skills/lx-oma-gov/SKILL.md` | 治理 reconcile/propagate |

### 状态机

```
idle
  → [status] → done
  → [advance] → checking_oracle_gate
      → [gate blocked] → awaiting_decision
          → [approve/reject] → (advance or abort)
      → [gate passed] → calling_skill
          → [skill done] → update_pipeline → done
          → [skill failed] → done (error)
      → [rpe→dev boundary] → launch_parallel_dev → done
  → [gate <id> approve|reject] → update_pipeline → done
  → [run <target>] → route_to_skill → done
  → [dev list] → done
  → [dev mark <id> <status>] → update_pipeline → done
      → [all features dev_done] → set stages.dev = completed → done
```

---

## 命令

### 1. status — 管线全景图

读取 `state/pipeline.yaml`，输出管线状态面板：

```
Pipeline Status
═══════════════════════════════════════════════════════════
  hier: ✅ completed     oma:  ✅ completed
  gov:  🟡 initialized   rpe:  ✅ completed
  dev:  ⬜ pending (parallel mode)
═══════════════════════════════════════════════════════════

Oracle Gates:
  og-001 (hier→oma): ✅ approved  "2 Major + 5 Minor — 全部修复"
  og-002 (oma→gov):  ⬜ pending (routing gate — 不阻塞 dev)
  og-003 (rpe→dev):  ⬜ pending (routing gate — 不阻塞 dev)

Sub PRDs:
  alert-engine       │ oma_done        │ 4 features │ oracle: revised
  notification       │ hier_done       │ 0 features │ oracle: approved
  dashboard          │ hier_done       │ 0 features │ oracle: approved
  tradingview        │ hier_done       │ 0 features │ oracle: approved
  user-preferences   │ hier_done       │ 0 features │ oracle: approved

═══ Parallel Dev — Ready Features ═══
  feat-alert-crud            🟢 rpe_planned  │ oracle: revised
  feat-price-evaluation      🟢 rpe_planned  │ oracle: pending
  feat-advanced-evaluation   🟢 rpe_planned  │ oracle: pending
  feat-trigger-history       🟢 rpe_planned  │ oracle: pending
──────────────────────────────────
  4 features ready · OMA file lock active · open N terminals

Next actions:
  /lx-oma-orch advance                → 检查下一阶段
  /lx-oma-orch gate og-002 approve    → 裁决 gate
  /lx-oma-orch dev list               → 并行开发面板
```

### 2. advance — 推进到下一阶段

读取 pipeline.yaml，找到下一个可推进的阶段：

1. 检查当前阶段上游的 Oracle gate 是否已 `approved`
2. 若未裁决 → **提示人工审核**：输出审核清单并等待 `/lx-oma-orch gate <og-id> approve|reject`
3. 若已裁决 → 调用对应 skill 执行
4. **skill 完成后**：
   - lx-oma-hier / lx-oma-split：直接更新 pipeline.yaml（它们不写 pipeline）
   - **lx-oma-gov：读取 `.omc/state/gov-latest-report.yaml`** 治理报告 → 根据 report 结果更新 pipeline.yaml
   - **已完成规划的 feautre**：读取 state/progress.md 获取各 feature 完成状态
5. **人工确认阶段转换**：每次 advance 后输出转换结果供人工确认，不自动进入下一阶段

**gov 阶段报告消费流程**：

```
lx-oma-orch advance (gov 阶段)
  → 调 lx-oma-gov reconcile
  → lx-oma-gov 输出 .omc/state/gov-latest-report.yaml
  → lx-oma-orch 读取报告:
      result: no_changes → 更新 stages.gov = completed
      result: success   → 等待 propagate 后更新
      result: conflict  → 标记 oracle_gate = pending (L3 待裁决)
  → 输出审核清单 → 等待人工确认
  → 人工确认后更新 pipeline.yaml
```

**阶段推进顺序**：

```
hier → [og-001] → oma → [og-002] → gov → [og-00N] → rpe ──→ dev (parallel)
  (调 lx-oma-hier)   (调 lx-oma-split)  (调 lx-oma-gov)      (不调 skill)
```

**rpe → dev 边界特殊行为**：

当 `advance` 检测到当前阶段为 rpe（即 feature 方案已完成）且 dev 在 pending 状态时，**不调用任何子 skill**，改为输出并行开发启动面板：

```
═══ DEV MODE — 并行开发就绪 ═══

以下 4 个 feature 已完成方案，可并发开发。进入对应目录开始开发：

  cd prd/alert-engine/feat-alert-crud && /lx-rpe .
  cd prd/alert-engine/feat-price-evaluation && /lx-rpe .
  cd prd/alert-engine/feat-advanced-evaluation && /lx-rpe .
  cd prd/alert-engine/feat-trigger-history && /lx-rpe .

各 feature 在独立目录下，OMA 文件锁（pretool-write-lock.sh）已激活，
不同终端写不同目录不冲突。每个终端独立推进 9 步主循环。

完成后运行 /lx-oma-orch dev mark <feature-id> dev_done 标记完成。
```

设置 `stages.dev = running`（不标记 completed — 等各 feature 独立完成后由用户或脚本手动更新）。

`--force` 跳过 Oracle gate 检查（风险自负）。

### 2.5 模式门禁路由（advance 附带）

当调用子 skill 时，读取该 skill 的 `execution_mode` frontmatter 字段，自动挂载模式对应门禁：

| execution_mode | 路由行为 | 成功门槛 |
|---------------|---------|---------|
| **race** | 注册为 Race 子任务，用 `race_manager.sh` 跟踪 | 聚合报告 N/M 通过 |
| **stepwise** | 执行 Stepwise 阶段流程（entry gate → 执行 → exit gate） | 所有 exit criteria 通过 |
| direct/无 | 直接调用，不挂载额外门禁 | skill 自行返回 |

对应门禁参考 `@../../nodes/mode_selector.md`。

### 3. gate — Oracle 门禁裁决

`/lx-oma-orch gate <og-id> approve|reject [--reason "..."]`

- `approve`：门禁通过，允许阶段推进。更新 pipeline.yaml 对应 `oracle_gates[].status = approved`
- `reject`：门禁拒绝，阻止阶段推进。更新 `oracle_gates[].status = rejected`
- 影响：推进到下一阶段时检查所有上游 gate 必须为 approved

### 4. run — 直接路由到指定 skill

`/lx-oma-orch run <sub_prd> [--feature <id>]`

绕过阶段检查，直接调用子 skill：

| 目标 | 路由 | 示例 |
|------|------|------|
| Sub PRD 拆解 | lx-oma-hier | `/lx-oma-orch run notification` → 调用 lx-oma-hier 拆解 notification |
| Feature 拆解 | lx-oma-split | `/lx-oma-orch run alert-engine` → 调用 lx-oma-split 拆解 alert-engine |
| 治理 | lx-oma-gov | `/lx-oma-orch run --gov reconcile` |

路由通过 `state/pipeline.yaml` 中的 `sub_prds[].path` 和 `features[].path` 解析路径，无需手敲。

### 5. dev — 并行开发管理

#### 5.1 dev list — 并行开发面板

列出所有 `stage: rpe_planned` 或 `stage: in_dev` 的 feature：

```
═══ Parallel Dev Dashboard ═══

Ready (rpe_planned):
  feat-alert-crud          🟢
  feat-price-evaluation    🟢

In Progress (in_dev):
  feat-advanced-evaluation 🔵  终端3  (started 2026-05-08)

Complete (dev_done):
  feat-trigger-history     ✅  (completed 2026-05-08)
```

各 feature 在独立目录下，进入目录即可继续开发。

#### 5.2 dev mark <feature-id> <status>

手动标记某个 feature 的 dev 进度（供用户调用）：

`/lx-oma-orch dev mark feat-alert-crud dev_done`

更新 `state/pipeline.yaml` 中对应 `features[].stage = dev_done`。

当所有 feature 标记为 `dev_done` 后，自动设置 `stages.dev = completed`。

---

## 与 Oracle 门禁的配合

本 skill 不自行判断 Oracle 裁决结果。它只做两件事：

1. **检查 pipeline.yaml 中的 gate status** — `approved` 或 `pending`
2. **通过 gate 命令让用户/外部裁决者更新 gate status**

裁决逻辑由外部 Oracle 节点（`oracle_terminal.md`）完成，本 skill 只负责编排和状态维护。

---

## Pipeline 更新契约

所有 skill 在完成工作后必须调用本 orchestrator（或直接写入 `state/pipeline.yaml`）以更新状态。写入格式：

```yaml
# 更新原则：
# - stages.{stage}: running → completed
# - sub_prds[].status: 推进到下一状态
# - features[].stage: 推进到下一状态
# - oracle_gates[].status: 新 gate → pending
```

使用原子写入：写 tmp 文件 → `os.rename(tmp, pipeline.yaml)`（参考 RPE-014 教训）。

---

## 可观测性契约

所有 OMA 系列 skill 共享以下可观测性规范，统一写入 `.omc/state/oma-telemetry.yaml`。

### 数据采集点

| 采集点 | 触发条件 | 记录字段 | 用途 |
|--------|---------|---------|------|
| skill_invoked | skill 被调用时 | `{skill, command, timestamp, duration_ms}` | 调用频次/耗时统计 |
| skill_completed | 命令正常完成 | `{skill, command, result, evidence_count}` | 成功率/证据完整性 |
| skill_error | 错误码触发 | `{skill, error_code, command, context}` | 错误模式分析 |
| gate_verdict | Oracle gate 裁决 | `{gate_id, verdict, reason, timestamp}` | 门禁吞吐/拒绝率 |

### 数据格式

```yaml
# .omc/state/oma-telemetry.yaml — 追加模式
telemetry:
  - timestamp: "2026-05-09T14:00:00+08:00"
    skill: "lx-oma-hier"
    command: "sub-prds/domain-dashboard.md"
    event: skill_invoked
    duration_ms: 120000
    result: completed
    error_code: null
    evidence_count: 7
```

### 读取方式

```bash
# 总调用次数
grep "event: skill_invoked" .omc/state/oma-telemetry.yaml | wc -l
# 成功率
grep "result: completed" .omc/state/oma-telemetry.yaml | wc -l
# 失败次数
grep "event: skill_error" .omc/state/oma-telemetry.yaml | wc -l
```

> **MVP 范围**: v1 仅规范数据格式和采集点定义，实际写入由各 skill 调用方（AI 执行时手动追加）。v2 计划实现自动化 hook 采集。
> **存储**: 单文件追加模式，每行一个事件。超过 500 行时归档到 `.omc/state/archive/oma-telemetry-{date}.yaml`。

## 跨 Skill 接口契约

本 orchestrator 协调 4 个下游 skill，每个 skill 通过约定的接口与 pipeline.yaml 或中间文件交换数据。

### 接口矩阵

| skill | 调用方 | 读取来源 | 写入目标 | 写入格式 | 读取方式 |
|-------|--------|---------|---------|---------|---------|
| lx-oma-hier | orch (advance) | sub-prds/domain-{id}.md | state/pipeline.yaml | `sub_prds[].{id, path, status: hier_done}` | orch 读取 status 后推进 |
| lx-oma-split | orch (advance) | sub-prds/domain-{id}.md + pipeline.yaml features[] | state/pipeline.yaml | `features[].{id, path, stage: oma_created}`, `sub_prds[].status=oma_done` | orch 读取后生成 og gate |
| lx-oma-gov | orch (advance) | prd/{sub_prd}/{feature}/prd.md + master-prd.md | `.omc/state/gov-latest-report.yaml` | governance report (§2.2) | orch 读取 report → 更新 pipeline.yaml |

### 数据流图

```
orch advance (hier 阶段)
  → 调 lx-oma-hier
  → hier 写 pipeline.yaml: sub_prds[].status = hier_done, stages.hier = completed
  → orch 读取 pipeline.yaml 确认
  → 输出转换报告 → 等待人工 gate 裁决

orch advance (oma 阶段)
  → 调 lx-oma-split
  → split 写 pipeline.yaml: features[], stages.oma = completed, og-NNN = pending
  → orch 读取 pipeline.yaml 确认
  → 输出转换报告 → 等待人工 gate 裁决

orch advance (gov 阶段)
  → 调 lx-oma-gov
  → gov 写 .omc/state/gov-latest-report.yaml
  → orch 读取 report → 根据 result 更新 pipeline.yaml
  → 输出转换报告 → 等待人工 gate 裁决

orch advance (rpe 阶段)
  → rpe 阶段为并行开发准备阶段，不调子 skill
  → 输出并行开发启动面板（见 §2 rpe→dev 边界）
  → 设置 stages.dev = running
  → 等待各 feature 独立完成后用户标记 dev_done
```

### 接口版本锁定

| 接口 | 当前版本 | 变更影响范围 |
|------|---------|-------------|
| pipeline.yaml stages | v1 (keys: {hier,oma,gov,rpe,dev}) | 所有 4 个 skill 读，orch 写 |
| pipeline.yaml sub_prds[] | v1 (keys: {id, path, status, oracle, features[]}) | hier/split 写，orch 读 |
| pipeline.yaml oracle_gates[] | v1 (keys: {id, from_stage, to_stage, status}) | orch 写/读，其余 skill 只读 |
| pipeline.yaml features[] | v1 (keys: {id, path, stage, oracle}) | split 写，orch 读 |
| gov-latest-report.yaml | v1 (keys: {version, command, result, changes[], oracle_gate, features_updated[]}) | gov 写，orch 读 |

> **变更流程**：任何接口版本变更需同步更新本契约表，并在对应 skill 的 SKILL.md 中标注版本号。
> **向后兼容**：v1 接口不兼容变更必须创建 v2 新 key，旧 key 保留至少 1 个迭代周期。

---

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| pipeline.yaml 不存在 | 报错 | 提示运行 `/lx-oma-gov init` 创建 |
| 无可推进阶段 | 报告"管线已全部完成" | 退出 |
| Oracle gate 未裁决 | 提示先运行 gate 命令 | `--force` 跳过 |
| 子 skill 调用失败 | 报告错误 | 保留 pipeline.yaml 当前状态，不推进 |
| dev mark 的 feature-id 不存在 | 报错 | 列出当前已知 feature IDs |

## 错误码与超时规范

本 skill 遵循共享错误码体系 `.claude/schemas/atomic/error_codes.yaml`，前缀 `ORCH`。

| 错误码 | 场景 | 处理 |
|--------|------|------|
| ERR-ORCH-01 | status/advance/gate 缺少必要参数 | 提示命令格式 |
| ERR-ORCH-12 | pipeline.yaml 解析失败 | 检查 YAML 格式后重试 |
| ERR-ORCH-20 | advance 时当前阶段不允许推进 | 输出当前状态 + 正确路径 |
| ERR-ORCH-21 | gate 裁决时 og-id 不存在 | 列出当前 pending gates |
| ERR-ORCH-22 | dev mark 的 feature-id 不存在 | 列出已知 feature IDs |
| ERR-ORCH-30 | advance 调用子 skill 超时（>15 分钟） | 检查子 skill 是否卡死 |
| ERR-ORCH-32 | 并发编排写冲突（多实例同时写 pipeline） | 原子写入（tmp→rename） |
| ERR-ORCH-90 | 路由目标 skill 不存在 | 降级提示手动执行 |

**超时**: advance 操作默认 15 分钟（含子 skill 执行时间），gate 裁决瞬间完成。
**重试**: advance 失败最多 2 次，第 2 次失败后必须人工介入。

## 人工审核门禁

**每个 advance 步骤后，必须输出转换结果供人工确认**，不自动进入下一阶段：

```
=== 阶段转换报告 ===
从: {from_stage}
到: {to_stage}
Oracle Gate: {og-id} → {approved/rejected}

审核清单:
[ ] 上游 gate 状态符合预期？
[ ] 子 skill 执行结果正确？
[ ] 本次转换是否准备就绪？
[ ] 有无异常/漂移需要处理？

确认方法: /lx-oma-orch gate {og-id} approve
拒绝方法: /lx-oma-orch gate {og-id} reject --reason "..."
```

