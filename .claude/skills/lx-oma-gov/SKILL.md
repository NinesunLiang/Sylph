---
name: lx-oma-gov

description: OMA PRD 治理 — 在 `prd/{sub_prd}/{feature}` 变更时通过 reconcile/propagate 机制增量同步，处理冲突裁决、漂移检测，保持 OMA 文档体系一致性

version: 1.2.0
harness_version: "6.1.8"
model: sonnet
argument-hint: "init [path] | reconcile [path] | resolve <CONFLICT-ID> <verdict> [--reason] | propagate --dry-run|--execute [path] | status | audit [path]"
when_to_use: |
  当主 PRD 发生变更需要向下游 feature 增量同步时；
  当需要检测 feature 与 master 之间的漂移时；
  当出现 PRD 冲突需要人工裁决时；
  当需要查看 PRD 治理状态时

triggers:
  - "/lx-oma-gov"
  - "oma治理"
  - "reconcile"
  - "propagate"
  - "漂移检测"
---

# lx-oma-gov OMA PRD 治理

**触发语**: `/lx-oma-gov`, `oma治理`, `reconcile`, `propagate`, `漂移检测`

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| explore | `../../nodes/explore.md` | 扫描 feature 目录，读取 PRD 文件 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | 冲突裁决判定 |

### 本 skill 参考文档

| 文件 | 用途 |
|------|------|
| `governance-spec.md` | 完整规范（对象 ID 体系、状态机、漂移检测规则等） |
| `HUMAN-IN-THE-LOOP-GATE.md` | awaiting_human_decision 状态机 + resolve/human-check runner 实现规范 |

### 状态机（会话级，单次调用）

```
need_input
  → [init] → initialized
  → [reconcile] → reconciling
      → [no changes] → done
      → [L3 conflict] → awaiting_human_decision
          → [resolve] → reconciling
      → [changes ready] → propagating_dry_run
          → [confirmed] → propagating → done
          → [cancelled] → done
  → [status] → done
  → [audit] → done
  → [error] → [repair → undone | reset → initialized]
  → [ingest] → initializing
  → [deprecate] → done
```

### 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 治理目录不存在 | 报错 | 提示先运行 init |
| reconcile 无变更 | 报告"无差异" | 快速路径 done |
| L3 冲突无人工裁决 | 挂起 + 生成裁决提示 | 非阻塞继续 L1/L2 |
| propagate 目标 feature 不存在 | 跳过并报告 | 列出缺失 feature |
| 锁文件超时 | 自动释放 | 记录清除日志 |

---

## 1. 目录结构约定

`lx-oma-gov` 治理 OMA 文档体系下的 feature 目录：

```
prd/{sub_prd}/{feature}/
  prd.md              ← feature PRD（治理目标）
  research.md         ← 技术调研
  plan.md             ← 实施计划
  executor.md         ← 执行记录
  state/              ← 状态追踪
    progress.md
  sync-notes.md       ← 同步记录（由 propagate 维护）
```

### init 创建的目录

```
./
  master-prd.md                 ← 主 PRD（权威源，init 询问是否创建）
  source-prds/                  ← 原始输入 PRD（ingest 前暂存）
  state/                        ← 治理状态
    sync-state.md               ← 最后 reconcile 快照
    pending-decisions.md        ← 待裁决队列
    feature-map.md              ← feature 注册表
  snapshots/                    ← 历史快照
  CONSOLIDATION-LOG.md          ← 变更日志
  PRD-INBOX.md                  ← 原始 PRD 收件箱
```

---

## 2. 命令

### 2.1 init — 初始化治理目录结构

在指定目录下创建 `state/`、`source-prds/`、`snapshots/`、`CONSOLIDATION-LOG.md`、`PRD-INBOX.md`。

**触发**：`/lx-oma-gov init [path]`

### 2.2 reconcile — 变更检测 + 冲突裁决

将主 PRD（`master-prd.md`）与各 `prd/{sub_prd}/{feature}/prd.md` 比对，识别变更级别：

| 级别 | 适用场景 | 处理方式 |
|------|---------|---------|
| L1 | 新术语、注释、元数据更新 | 自动归并 |
| L2 | 新研究线索、可选需求 | 自动归并 |
| L3 | 改核心需求、推翻决策、修改已有对象 | 挂起 pending-decisions |

**L2→L3 自动升级**：若变更修改了已有 `REQ-*`/`DEC-*`/`TERM-*` 或与已有决策矛盾，升级为 L3。

**产出**：
- 分配 `CHG-YYYYMMDD-NNN`（变更记录 ID）
- 分配 `CONFLICT-NNN`（L3 冲突 ID）
- 更新 `CONSOLIDATION-LOG.md`
- L3 挂起写入 `state/pending-decisions.md`

### 2.3 resolve — L3 人工裁决

当 reconcile 产出 L3 冲突时，用户运行此命令裁决。

**格式**：`/lx-oma-gov resolve <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason "说明"]`

**执行**：
- 更新 `CONSOLIDATION-LOG.md` 对应 Entry
- 从 `state/pending-decisions.md` 移除（或标记 resolved）
- accept → 继续归并；reject → 标记拒绝；defer → 保留

### 2.4 propagate — 增量传播

将 reconcile 产生的变更传播到各 `prd/{sub_prd}/{feature}/prd.md`。

**格式**：
- `/lx-oma-gov propagate --dry-run` → 预览变更内容，不写入
- `/lx-oma-gov propagate --execute` → 实际写入

**幂等保证**：每条传播记录写入 `sync-notes.md`，绑定 `CHG-ID`。重复执行跳过已有 ID。

> **MVP 范围**：v1 仅支持 `--dry-run`（预览模式），`--execute` 为 v2 计划。

### 2.5 status — 治理状态查看

**格式**：`/lx-oma-gov status`

**输出**：
- 当前治理状态（state machine 位置）
- Open CONFLICT 列表
- 各 feature 同步状态（up-to-date / behind）
- 待处理 pending decisions

### 2.6 audit — 漂移检测

四类检测规则：

| 规则 | 检测内容 | 严重度 |
|------|---------|--------|
| ID 孤儿检测 | feature 引用了 master 中不存在的 ID | high |
| 版本落后检测 | feature 最后同步 < 最后一次 reconcile | medium |
| 冲突定义检测 | feature 中定义与 master 不一致 | high |
| 孤立变更检测 | pending decision 超过 7 天未处理 | high |

> **MVP 范围**：v1 实现基础检测（ID 孤儿 + 版本落后），v2 扩展为完整四类规则（含冲突定义检测 + 孤立变更检测）。

### 2.7 参考规范能力（v2 计划）

以下能力在 `governance-spec.md` 中有完整规范，当前未作为独立命令实现，v2 计划：

| 命令 | 用途 | 规范位置 |
|------|------|---------|
| `ingest` | 输入 PRD 分级处理（结构化/半结构化/非结构化） | governance-spec.md §7 |
| `deprecate` | 废弃 feature / REQ，标记 deprecated 状态 | governance-spec.md §12 |
| `repair` / `reset` | 错误恢复：从 `error` 状态回到上一个稳定快照 | governance-spec.md §2 |

---

## 3. 与管线集成

`lx-oma-gov` 在 PRD 全生命周期中的位置：

```
初始化路径（一次性）:
  lx-oma-hier  →  lx-oma-split  →  lx-rpe
  (主PRD→SubPRD)  (SubPRD→RPE)  (特性开发)

治理路径（持续）:
  lx-oma-gov  →  lx-oma-split → lx-rpe
  (reconcile/propagate)  (re-split)  (开发)
              直接→ lx-rpe
              (小变更直接通知开发)
```

### 调用时机

| 触发条件 | 操作 |
|---------|------|
| 主 PRD 更新 | `/lx-oma-gov reconcile` → 检测变更 |
| reconcile 产出变更 | `/lx-oma-gov propagate --dry-run` → 预览 |
| 预览确认 | `/lx-oma-gov propagate --execute` |
| L3 冲突 | `/lx-oma-gov resolve CONFLICT-NNN <verdict>` |
| 定期检查 | `/lx-oma-gov audit` → 漂移报告 |
| 首次数治 | `/lx-oma-gov init` → 创建 state 目录 |
| 日常查看 | `/lx-oma-gov status` → 治理面板 |

---

## 4. 治理质量自检

执行命令后自动校验：

1. **CHG-ID 完整性**：每条变更记录有唯一 CHG-ID，且格式正确
2. **CONFLICT-ID 闭合性**：已裁决的 CONFLICT 标记 resolved，无遗漏
3. **幂等安全**：重复 propagate 不产生重复内容
4. **引用一致性**：propagate 后所有 feature 引用的 REQ/DEC 在 master 中存在
5. **同步状态**：所有活跃 feature 最后同步时间 ≥ 最后一次 reconcile 时间

---

## 5. Pipeline 集成

本 skill **只读** `state/pipeline.yaml` 用于获取编排上下文。所有 pipeline 状态写入由 `lx-oma-orch` 统一管理。

### 入口读取（编排模式）

当调用者传入 `--pipeline` 参数时，读取 pipeline.yaml 获取编排上下文：
1. 识别 `stages.gov` 的当前状态（pending / initialized / running）
2. 从 `oracle_gates[]` 中读取与 gov 相关的 gate 状态
3. 从 `sub_prds[]` 获取 feature 注册信息

### 标准化治理报告输出

**本 skill 不直接修改 pipeline.yaml**。每次命令执行完毕后，输出一份机器可读的治理报告供 `lx-oma-orch` 消费：

```yaml
# governance-report.yaml — 输出到 .omc/state/gov-latest-report.yaml
# 由 lx-oma-orch 读取后更新 pipeline.yaml
version: "1.0"
command: init|reconcile|propagate|status|audit
result: success|failure|no_changes|conflict
sub_prd: "<target>"
changes:
  - type: L1|L2|L3
    description: "<变更描述>"
    file: "<path>"
oracle_gate:
  action: create|update|skip
  from_stage: "<from>"
  to_stage: "<to>"
  verdict: approved|pending|rejected  # L3 冲突时为 pending
features_updated:
  - id: "<feature-id>"
    status: "<new-status>"
```

### 命令与 report 映射

| 命令 | 产出报告 | orch 读取后的动作 |
|------|---------|-----------------|
| init | governance-report.yaml | 更新 stages.gov = initialized，auto-register features |
| reconcile（无变更） | result: no_changes | 更新 stages.gov = completed |
| reconcile（有变更） | result: success + changes[] | 等待 propagate 后更新 |
| reconcile（L3 冲突） | result: conflict + oracle_gate.verdict: pending | 等待人工 resolve |
| propagate | result: success + features_updated[] | 更新对应 feature stage |
| status / audit | 只读，不产出管道变更报告 | 无操作 |

### 人工审核报告生成

完成 reconcile 后，`lx-oma-gov` 必须生成人工审核清单供用户确认：

```
=== 治理审核清单 ===
[ ] 检测到的 L1 变更全部自动归并？
[ ] L2 变更是否需人工确认？
[ ] L3 冲突是否已 resolve？
[ ] drift audit 结果符合预期？
[ ] 治理报告路径：.omc/state/gov-latest-report.yaml
人工确认后，运行 /lx-oma-orch gate og-NNN approve 推进。
```

## 6. 可观测性契约

本 skill 遵循 OMA 系列统一可观测性规范，详见 `lx-oma-orch/SKILL.md` §可观测性契约。

### 本 skill 特定采集点

| 采集点 | 触发条件 | 记录字段 | 用途 |
|--------|---------|---------|------|
| gov_reconcile_started | reconcile 开始时 | `{target_path, feature_count}` | 治理规模评估 |
| gov_reconcile_completed | reconcile 完成时 | `{changes_count, L1, L2, L3, conflict_ids[]}` | 变更分布统计 |
| gov_propagate_dryrun | --dry-run 执行时 | `{changes_previewed}` | 预览频次 |
| gov_propagate_executed | --execute 执行时 | `{features_updated[], chg_ids[]}` | 传播效率 |
| gov_audit_passed | audit 通过时 | `{drift_count, severity_distribution}` | 漂移趋势 |
| gov_conflict_resolved | L3 冲突裁决 | `{conflict_id, verdict, time_to_resolve_h}` | 裁决效率 |

> 数据写入 `.omc/state/oma-telemetry.yaml`，格式与 lx-oma-orch 保持一致。

## 7. 错误码与超时规范

本 skill 遵循共享错误码体系 `.claude/schemas/atomic/error_codes.yaml`，前缀 `GOV`。

| 错误码 | 场景 | 处理 |
|--------|------|------|
| ERR-GOV-01 | init/reconcile 缺少参数 | 提示命令格式 |
| ERR-GOV-03 | master-prd.md 不存在 | 检查治理目录结构 |
| ERR-GOV-10 | governance-spec.md 读取失败 | 检查 skill 安装完整性 |
| ERR-GOV-12 | governance-report.yaml 写入失败 | 检查 .omc/state/ 路径 |
| ERR-GOV-20 | stages.gov 状态冲突 | 检查 pipeline.yaml 当前状态 |
| ERR-GOV-21 | L3 冲突未 resolve 尝试 propagate | 先调 resolve |
| ERR-GOV-23 | reconcile 检测到不一致但 --force 未传 | 修复后重试 |
| ERR-GOV-30 | reconcile 操作超时（>10 分钟） | 检查 feature 数量 |
| ERR-GOV-32 | 治理目录锁竞争 | 等待后重试 |
| ERR-GOV-90 | governance-spec.md 不存在 | 降级运行基础模式 |

**超时**: reconcile 默认 10 分钟，propagate 默认 3 分钟。
**重试**: reconcile 失败最多 3 次，每次重试前重新读取文件状态。

---

> 完整规范见 `governance-spec.md`（本 skill 目录下），含对象 ID 体系、状态机扩展、并发写入保护、deprecated 机制等细节。
