# Pipeline Orchestration — 4-Skill 管线编排

> PRD 全生命周期管理
> 从主 PRD → Sub PRD → Feature PRD → 治理 → 开发计划

---

## 1. 要解决的问题

Carror OS 有 4 个 PRD 相关 skill，各司其职：

| Skill | 职责 | 产出 |
|-------|------|------|
| `lx-oma-hier` | 把超大 PRD 按业务域拆成多个 Sub PRD | `sub-prds/domain-*.md` |
| `lx-oma-split` | 把一个 Sub PRD 拆成正交的多个 Feature | `prd/{sub_prd}/feat-{name}/prd.md` |
| `lx-oma-gov` | 治理：主 PRD 变更时向下游增量同步、冲突裁决、漂移检测 | `state/`, `CONSOLIDATION-LOG.md` |
| `lx-rpe` | 特性级开发计划（Phase 1/2/3 恢复流程） | `plan.md`, `executor.md` |

**之前的问题**：用户需要在 4 个 skill 之间手动切换，记状态、敲路径、叫 Oracle、人工触发下一阶段。人就是接线员。

**解决方式**：`lx-oma-orch`（编排器）+ `state/pipeline.yaml`（共享状态机）= 自动化管线。

---

## 2. 架构

```
用户只需要跟 lx-oma-orch 对话
         │
         ▼
┌─────────────────────────────────────────────────┐
│  lx-oma-orch  Pipeline Orchestrator                  │
│  ├─ status    — 查看全局进度                      │
│  ├─ advance   — 推进到下一阶段(自动检查Oracle门禁) │
│  ├─ gate      — Oracle 门禁裁决                    │
│  └─ run       — 直接路由到子 skill                 │
└──────────────────┬──────────────────────────────┘
                   │ 读写
                   ▼
┌─────────────────────────────────────────────────┐
│  state/pipeline.yaml                             │
│  统一状态机：5 阶段 / N Sub PRD / M Feature      │
│  所有 skill 共享 — 入口读、出口写                 │
└──────────────────┬──────────────────────────────┘
                   │ 编排
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
 lx-oma-hier   lx-oma-gov    lx-oma-split / lx-rpe
 (分层拆解)     (治理)         (特性拆解/开发)
```

---

## 3. 管线全生命周期

### 3.1 5 个阶段

```
  hier  →  oma  →  gov  →  rpe  →  dev
  拆       拆       治理     计划     实现
  SubPRD   Feature
```

| 阶段 | 做的事情 | 产出 | 对应 skill |
|------|---------|------|-----------|
| `hier` | 分功能域 | `sub-prds/domain-*.md` | lx-oma-hier |
| `oma` | 分特性 | `prd/{sub_prd}/feat-*/prd.md` | lx-oma-split |
| `gov` | 治理初始化 | `state/`, `CONSOLIDATION-LOG.md` | lx-oma-gov |
| `rpe` | 开发计划 | `plan.md`, `research.md` | lx-rpe |
| `dev` | 并行编码 | 各 feature 独立在终端实现 | lx-rpe (每个 feature 一个终端) |

### 3.2 Oracle 门禁

每两个阶段之间有一个 Oracle 门禁（质量闸门）：

```
hier → [og-001] → oma → [og-002] → gov → [og-00N] → rpe → [og-00N] → dev
        已批准           待裁决            未创建            未创建
```

- `advance` 命令在推进前**强制检查**上游 gate 是否已 `approved`
- `gate` 命令让用户/外部 Oracle 裁决者更新 gate 状态
- `--force` 可跳过（风险自负）

### 3.3 Sub PRD 和 Feature 的状态机

每个 Sub PRD 独立跟踪：

```
hier_done → oma_done → gov_initialized → in_dev → done
```

每个 Feature 独立跟踪：

```
oma_created → gov_registered → rpe_planned → in_dev → done
```

Oracle 状态独立跟踪：

```
pending → approved → revised → final
```

---

## 4. pipeline.yaml 详解

这是整个编排系统的核心。它是一份 YAML 文件（`state/pipeline.yaml`），所有 skill 共享读写。

### 文件结构

```yaml
version: "1.0"
created_at: "2026-05-08T22:00:00+08:00"
updated_at: "2026-05-08T22:00:00+08:00"

source_prd: mothership-prd.md          # 原始 PRD
master_prd: master-prd.md              # 治理权威源

# ── 管线级进度 ──
stages:
  hier: completed                      # completed / running / pending
  oma: completed
  gov: initialized
  rpe: completed
  dev: pending

# ── Sub PRD 注册表 ──
sub_prds:
  - id: alert-engine                   # 唯一标识
    path: sub-prds/domain-alert-engine.md  # 文件路径
    status: oma_done                   # 当前状态
    oracle: revised                    # Oracle 审阅状态
    features:                          # 该域下的特性
      - id: feat-alert-crud
        path: prd/alert-engine/feat-alert-crud
        stage: rpe_planned
        oracle: revised
      - id: feat-price-evaluation
        path: prd/alert-engine/feat-price-evaluation
        stage: rpe_planned
        oracle: pending

# ── Oracle 门禁队列 ──
oracle_gates:
  - id: og-001                         # 门禁编号
    from_stage: hier_done              # 起始阶段
    to_stage: oma_ready                # 目标阶段
    status: approved                   # pending / approved / rejected
    target: "sub_prds: all"            # 作用范围
    reviewed_at: "2026-05-08T21:00:00+08:00"
    result: "2 Major + 5 Minor — 全部修复"
```

### 更新契约

所有 skill 在完成工作后必须更新 pipeline.yaml：

- `stages.{阶段}`: `running → completed`
- `sub_prds[].status`: 推进到下一状态
- `features[].stage`: 推进到下一状态
- `oracle_gates[].status`: 新 gate → `pending`

写入使用原子操作：写 tmp 文件 → `os.rename(tmp, pipeline.yaml)`，防止并发部分写入。

---

## 5. 日常使用示例

### 5.1 看全局进度（一句话）

```
/lx-oma-orch status
```

输出当前所有 Sub PRD / Feature / Oracle gate 的状态，一眼知道"现在到哪了"。

### 5.2 推进到下一阶段

```
/lx-oma-orch advance
```

lx-oma-orch 自动：
1. 读 pipeline.yaml，找出当前最靠前的未完成阶段
2. 检查该阶段上游的 Oracle gate 是否已批准
3. 若已批准 → 调用对应 skill 执行
4. 执行完成后更新 pipeline.yaml

**rpe → dev 边界特殊行为**：当 advance 处于 rpe 阶段时，不调用任何 skill，改为输出并行开发启动面板，列出 N 个终端命令（每个 feature 一个），由用户在独立终端启动并发开发。

```
═══ DEV MODE — 并行开发就绪 ═══
  Terminal 1:  /lx-rpe prd/alert-engine/feat-alert-crud
  Terminal 2:  /lx-rpe prd/alert-engine/feat-price-evaluation
  ...
```

### 5.3 Oracle 门禁裁决

```
/lx-oma-orch gate og-002 approve --reason "审阅通过，4 个 feature 拆解正确"
/lx-oma-orch gate og-002 reject --reason "需要补充条件类型枚举定义"
```

- `approve` → gate 通过，允许 `advance` 推进
- `reject` → gate 拒绝，阻止推进

### 5.4 直接路由到子 skill

```
/lx-oma-orch run notification               # 调 lx-oma-hier 拆解 notification 域
/lx-oma-orch run alert-engine                # 调 lx-oma-split 拆解 alert-engine
/lx-oma-orch run alert-engine --feature feat-alert-crud  # 调 lx-rpe 看开发计划
```

路由路径从 pipeline.yaml 自动解析，无需手敲 `sub-prds/domain-notification.md` 或 `prd/alert-engine/feat-alert-crud`。

---

## 6. 扩展指南

### 6.1 新增一个 Sub PRD

```
1. 在 pipeline.yaml 的 sub_prds[] 中添加条目
2. /lx-oma-orch run <id>  → 调用 lx-oma-hier 拆解
3. /lx-oma-split sub-prds/domain-<id>.md  → 拆成 feature（或编排模式下自动）
```

### 6.2 新增一个 Feature

```
1. lx-oma-split 拆解后自动注册到 pipeline.yaml
2. /lx-oma-orch status 确认已注册
3. /lx-rpe prd/{sub_prd}/{feature}  → 开发计划
```

### 6.3 主 PRD 变更后的治理流程

```
1. 修改 master-prd.md
2. /lx-oma-gov reconcile    → 检测变更 + 冲突裁决
3. /lx-oma-gov propagate --dry-run  → 预览传播内容
4. /lx-oma-gov propagate --execute  → 实际写入
5. /lx-oma-orch status          → 确认状态已更新
```

---

## 7. 设计原则

| 原则 | 说明 |
|------|------|
| **编排器不做事，只调度** | lx-oma-orch 不拆 PRD、不做治理、不做开发计划 — 它只检查状态、路由到正确 skill、更新状态 |
| **Oracle 不集成在编排器内** | lx-oma-orch 不自行判断 Oracle 裁决，只读 gate 状态和提供 gate 命令。裁决逻辑在独立的 `oracle_terminal.md` 节点 |
| **状态集中，执行分散** | pipeline.yaml 是唯一的全局状态源。每个 skill 独立执行自己的领域逻辑，只在入口读状态、出口写状态 |
| **向后兼容** | 所有 skill 的独立调用方式仍然可用。pipeline 集成是增量添加，不影响已有用法 |
