# lx-oma-gov 补丁规范 v1

> 状态：Patch v1（基于 Oracle 评审 2026-05-08）
> 来源：Oracle 架构评审报告，全部建议已逐条评估
> 适用于：在 spec-v0 基础上追加的修复与补充，不替换 spec-v0，以本文件为准

---

## 评估决策记录

| Oracle 建议 | 决定 | 理由 |
|-------------|------|------|
| 越层读写权限明确化 | ✅ 接受 | 设计本意如此，补充说明 |
| 补充 CHG-* 和 CONFLICT-* ID | ✅ 接受 | 幂等性和裁决追溯的核心锚点 |
| 状态机补充 awaiting_human / error | ✅ 接受 | 缺失导致 L3 挂起后语义空洞 |
| 传播令牌机制 | ⬇️ 降级接受 | 原理接受，用 snapshot ID 字段代替"令牌"概念，降低实现复杂度 |
| AI-人工裁决操作路径完整定义 | ✅ 接受 | 最重要缺口，必须补 |
| propagate 幂等性（CHG-ID 写入 sync-notes.md） | ✅ 接受 | 标准幂等设计 |
| L2→L3 自动升级覆盖规则 | ✅ 接受 | 防止伪装成 L2 的 L3 变更 |
| L3 采用非阻塞 + 显式挂起模式 | ✅ 接受 | 实用性更强，不卡死 L1/L2 |
| 漂移检测四类量化规则 | ✅ 接受 | 可执行的检测规则 |
| 并发写入 + .lock 文件 | ✅ 接受 | 简化实现，文档工具足够用 |
| propagate dry-run 纳入 MVP | ✅ 接受 | 低成本、防 v2 债务 |
| 减法操作：deprecated 标签机制 | ✅ 接受 | 真实场景，防 ID 孤立 |
| ingest 输入格式分级（三条路径） | ✅ 接受 | 可操作的降级策略 |
| feature 目录最小有效结构定义 | ✅ 接受 | 明确 mothership 与 lx-rpe-split 的分工 |

**驳回**：无。

---

# 1. 对象 ID 体系补充

## 原有 ID 类型（spec-v0 第 4 节）

- `REQ-NNN`
- `DEC-NNN`
- `TERM-NNN`
- `RISK-NNN`
- `PHASE-NN`
- `FEAT-name`

## 新增 ID 类型

### 变更记录 ID：CHG-YYYYMMDD-NNN

格式：`CHG-20260508-001`

- **创建时机**：`reconcile` 识别出一条有效变更（已通过判定，不是候选）时分配
- **作用**：
  - `propagate` 以 CHG-ID 为单位执行，防止重复追加
  - feature/sync-notes.md 中每条追加记录必须绑定 CHG-ID
  - 重新执行 propagate 时先检查目标文件是否已有该 CHG-ID，存在则跳过
- **关闭条件**：所有目标 feature 均已完成传播
- **归档规则**：传播完成后在 `CONSOLIDATION-LOG.md` 中标记 `propagation_status: done`

### 冲突记录 ID：CONFLICT-NNN

格式：`CONFLICT-001`

- **创建时机**：`reconcile` 识别到 L3 高风险冲突时分配
- **作用**：
  - Owner 通过命令引用 CONFLICT-ID 完成裁决
  - CONSOLIDATION-LOG.md 中 L3 挂起条目必须有 CONFLICT-ID
  - `status` 命令展示当前 open CONFLICT 数量
- **关闭条件**：Owner 裁决（accept/reject/deferred）
- **归档规则**：裁决完成后状态更新为 `resolved`，历史保留不删除

---

# 2. 状态机扩展

## 原状态机（spec-v0）

```
need_init → initialized → loading_inputs → comparing_deltas
→ reconciling_master → propagating_features → done
```

## 扩展后状态机

```
need_init
  → initialized
    → loading_inputs
      → comparing_deltas
          → [no effective changes] → done（快速路径，记录"无差异"）
          → reconciling_master
              → [L3 冲突] → awaiting_human_decision
                  → [Owner 裁决完成] → reconciling_master（恢复继续）
              → [无 L3 阻塞，或 L3 全部非阻塞处理] → propagating_features（dry-run）
                  → [用户确认] → propagating_features（写入）
                      → done
  → error（任意状态均可转入）
      → [repair 或 reset 命令] → (回到上一个稳定状态快照)
```

### 状态说明

| 状态 | 触发条件 | 退出条件 |
|------|---------|---------|
| `awaiting_human_decision` | 识别到 L3 冲突 | Owner 执行裁决命令 |
| `error` | 文件损坏/ID 冲突/外部中断 | 执行 `repair` 或 `reset` |
| `done`（快速路径） | comparing_deltas 结果无有效变更 | 自动，记录"无差异" |

### L3 的非阻塞行为

**选择：非阻塞 + 显式挂起**（不停止 L1/L2 处理）

- L3 冲突写入 `state/pending-decisions.md`，打 `BLOCKED` 标签
- 分配 CONFLICT-ID
- 其余 L1/L2 变更**继续**处理
- `status` 命令始终展示 open CONFLICT 数量
- `propagate` 执行时检查是否有 BLOCKED L3 影响当前传播范围：
  - 有影响 → 警告并列出（但不阻塞，除非用户配置 `strict_mode: true`）
  - 无影响 → 正常执行

---

# 3. 读写权限规范（补充 spec-v0 第 3 节）

## 越层访问规则

| 操作类型 | 越层访问 | 允许/禁止 |
|---------|---------|---------|
| 跨层**读取**（如 reconcile 读 feature/prd.md） | 允许 | ✅ |
| 跨层**写入**（如直接覆盖 feature/plan.md） | 禁止 | ❌ |
| 跨层**追加**（如 propagate 向 feature/prd.md 追加） | 允许（须绑定 CHG-ID） | ✅ |

**每条命令的读写范围**：

| 命令 | 读取层 | 写入层 |
|------|--------|--------|
| `init` | 无 | Master 层 + state/ |
| `ingest` | PRD-INBOX | source-prds/ + PRD-INBOX + CONSOLIDATION-LOG（候选区） |
| `reconcile` | Master 层 + Feature 层（只读） | Master 层 + CONSOLIDATION-LOG + state/ + snapshots/ |
| `propagate` | Master 层 + state/ | Feature 层（追加） + state/ + reports/ |
| `audit` | 所有层 | reports/audit/ |
| `status` | state/ | 无 |

---

# 4. L3 裁决操作路径

## 完整裁决工作流

```
1. reconcile 识别 L3 冲突
    → 分配 CONFLICT-NNN
    → 写入 CONSOLIDATION-LOG.md（Entry 状态 = awaiting_human）
    → 写入 state/pending-decisions.md（BLOCKED 标签）
    → 输出裁决提示给用户（格式化，含冲突内容、影响范围、建议选项）
    → 继续处理其他 L1/L2 变更（非阻塞）

2. Owner 查看 pending decisions
    → 运行: lx-oma-gov status
    → 查看 open CONFLICT 列表
    → 运行: lx-oma-gov resolve CONFLICT-NNN

3. 裁决命令格式
    lx-oma-gov resolve <CONFLICT-ID> <verdict> [--reason "说明"]

    verdict 选项（A — 推荐 ✓）：
    - accept          完整接受变更并合并到 master — 新资料可靠时
    - accept-partial  部分接受（需配合 --targets）— 仅部分内容有效时
    - reject          驳回，不进入 master — 现有定义仍为最优时
    - defer           暂缓，保留 pending — 信息不足以裁决时

4. 系统更新
    → 更新 CONSOLIDATION-LOG.md 对应 Entry（写入 adjudicated_by / adjudicated_at / verdict / reason）
    → 从 state/pending-decisions.md 移除该 CONFLICT（或标记 resolved）
    → 若 verdict = accept / accept-partial：继续 reconcile 流程，归并到 master
    → 若 verdict = reject：标记 Entry 为 rejected，不归并
    → 若 verdict = defer：保留 BLOCKED 状态，等待下次 reconcile 或手动处理
```

## 裁决提示输出格式

```md
## ⚠️ L3 冲突需要人工裁决

CONFLICT-ID: CONFLICT-001
Source File: source-prds/payment-v2.md
Risk Level: L3

### 冲突描述
新资料中对 REQ-021（支付失败重试次数）的定义与现有定义冲突：
- 现有定义：最多重试 3 次，间隔 10s
- 新资料：最多重试 5 次，间隔 30s

### 影响范围
- master-prd.md: REQ-021
- prd/{sub_prd}/feat-payment/prd.md
- decisions/DEC-004（依赖 REQ-021 的决策）

### 建议选项
A. accept — 推荐 ✓
   说明：接受新定义，更新 REQ-021 和 DEC-004
   适用场景：新资料更符合当前业务需求
B. reject
   说明：维持现有定义，驳回新资料
   适用场景：现有定义仍为最优，新资料理由不足
C. defer
   说明：暂缓处理，等待进一步确认
   适用场景：信息不足以做出裁决，需补充资料
D. 自定义操作
   → 输入其他裁决方式和理由
执行裁决: lx-oma-gov resolve CONFLICT-001 A|B|C|D [--reason "说明"]
```

## state/pending-decisions.md 格式

```md
# Pending Decisions

> 更新时机：每次 reconcile 产生新 L3 冲突时追加；裁决完成时移除或标记 resolved

## Open Conflicts

| CONFLICT-ID | Source | Risk | Affected Objects | Created At | Owner |
|-------------|--------|------|-----------------|------------|-------|
| CONFLICT-001 | payment-v2.md | L3 | REQ-021, DEC-004 | 2026-05-08 10:30 | - |

## Resolved Conflicts

| CONFLICT-ID | Verdict | Resolved At | Resolved By |
|-------------|---------|-------------|-------------|
| (empty) | | | |
```

---

# 5. propagate 幂等性规范

## 幂等保证机制

1. `reconcile` 产生有效变更时分配 `CHG-YYYYMMDD-NNN`
2. `propagate` 对每个目标 feature 执行前，先读取 `prd/{sub_prd}/feat-xxx/sync-notes.md`
3. 若 sync-notes.md 中已存在该 CHG-ID，跳过（不重复追加）
4. 若不存在，执行追加，并在 sync-notes.md 末尾写入记录

## sync-notes.md 追加记录格式

```md
## Sync Record CHG-20260508-001

- CHG-ID: CHG-20260508-001
- Propagated At: 2026-05-08 11:00
- Propagated By: lx-oma-gov
- Source Change: CONSOLIDATION-LOG.md Entry CL-014
- Sync Type: prd
- Content Added: REQ-021 重试次数更新引用
- Status: done
```

## 传播基准（降级版"传播令牌"）

- `reconcile` 完成时，在 `state/sync-state.md` 中写入：
  ```
  last_reconcile_snapshot: snapshots/master/master-prd-20260508-1100.md
  ```
- `propagate` 执行时读取此字段，以该快照为基准确定传播内容
- 若 `last_reconcile_snapshot` 为空，拒绝执行 propagate，提示"请先执行 reconcile"

---

# 6. 变更分级补充规则（L2→L3 自动升级）

## 升级覆盖规则（优先于类型判断）

**规则**：当一个被识别为 L1 或 L2 的候选变更，满足以下任一条件时，**自动升级为 L3**：

| 条件 | 示例 |
|------|------|
| 候选变更引用了已有对象 ID，且语义上**修改**（非仅引用或补充）了该对象 | 修改 REQ-021 的定义，而非新增一条 REQ |
| 候选变更与任何已有 `DEC-*` 存在逻辑矛盾（即使表面上看是"新增研究线索"） | 新研究结论否定了 DEC-004 的前提 |
| 候选变更修改了已有 `TERM-*` 的含义（非新增术语） | 修改"支付重试"的定义范围 |
| 候选变更影响了 `PHASE-*` 的边界或状态 | 说明某功能应移到下个 phase |

**执行逻辑**：
```
AI 初判类型 → 检查升级条件（优先执行）→ 满足任一条件则升级为 L3 → 进入人工裁决流程
```

## 修订后的分级定义（含升级规则）

| 级别 | 基础适用场景 | 升级条件（满足则强制升为 L3） |
|------|------------|--------------------------|
| L1 | 新术语新增、非冲突注释、元数据更新 | 修改了已有对象含义时升级 |
| L2 | 新研究线索、新边界说明、可选需求 | 与已有 REQ/DEC 语义冲突时升级 |
| L3 | 改核心需求、改 phase 边界、推翻决策 | 不降级 |

---

# 7. ingest 输入格式分级

## 三条处理路径

### Structured（结构化输入）
**识别条件**：文档中含有 `REQ-*`、`DEC-*`、`TERM-*`、`RISK-*` 等对象 ID 标记

**处理方式**：
- 直接进入候选变更识别流程
- AI 对每个带 ID 的对象做变更分析（新增 vs 修改）

### Semi-structured（半结构化输入）
**识别条件**：文档有清晰的 Markdown 标题层级，但无对象 ID

**处理方式**：
- AI 自动为识别到的需求/决策/术语生成候选 ID
- 输出候选 ID 映射提示，请用户确认后再进入 reconcile
- 未确认前，状态标记为 `pending_id_assignment`

### Unstructured（非结构化输入）
**识别条件**：纯文本、笔记、口述整理等，无结构

**处理方式**：
- 放入 `PRD-INBOX.md` 的 `## RAW` 区块
- 标注 `status: needs_structuring`
- **不**参与 reconcile，等待人工结构化后重新 ingest
- `audit` 命令会提示"有 RAW 条目待处理"

## PRD-INBOX.md RAW 区块格式

```md
## RAW (待人工结构化)

### RAW-001
- Ingested At: 2026-05-08 10:00
- Source File: source-prds/incoming/note-2026-05-08.md
- Status: needs_structuring
- Content Summary: 关于支付失败重试的口述讨论记录
```

---

# 8. feature 目录最小有效结构定义

## 必须存在的文件

| 文件 | 创建者 | 说明 |
|------|--------|------|
| `prd.md` | lx-rpe-split 或人工 | feature 范围、输入输出、黑盒边界、REQ/DEC 引用 |
| `sync-notes.md` | lx-oma-gov（init 时） | 记录母本向本 feature 的增量同步历史（含 CHG-ID） |

## 可选但建议存在的文件

| 文件 | 创建者 | 说明 |
|------|--------|------|
| `research.md` | lx-rpe 或人工 | 待验证问题、mock 假设、风险线索 |
| `plan.md` | lx-rpe 或人工 | 执行建议，供 lx-rpe 消费 |
| `mocks/` | 开发者 | 模拟数据 |
| `adapters/` | 开发者 | 替换层 |
| `contracts/` | 开发者 | 输入输出契约 |

## 文件职责分工（mothership vs lx-rpe-split）

| 文件 | mothership 做什么 | lx-rpe-split 做什么 | 开发者做什么 |
|------|-----------------|-------------------|------------|
| `prd.md` | 追加式传播 REQ/DEC 引用 | 创建初始版本（含黑盒边界） | 维护局部内容 |
| `sync-notes.md` | 创建并维护 | 不涉及 | 不应手动修改 |
| `research.md` | 追加研究线索 | 可创建初始结构 | 填充研究内容 |
| `plan.md` | 追加"建议变更项"区块 | 可创建初始结构 | 维护任务主体 |

## audit 时的 feature 结构完整性检查

```
检查项：
1. prd.md 是否存在？（必须）
2. sync-notes.md 是否存在？（必须）
3. prd.md 中是否有黑盒边界区块？（建议）
4. prd.md 引用的 REQ-*/DEC-* 是否在 master 中有效？（漂移检测）
```

---

# 9. 漂移检测量化规则（spec-v0 第 19 节补充）

## 四类可执行检测规则

### 规则 1：ID 孤儿检测
- **检测**：扫描所有 feature/prd.md，提取引用的 `REQ-*/DEC-*/TERM-*/RISK-*`
- **比对**：与 master-prd.md / GLOSSARY.md / decisions.md 中的对象列表比对
- **报告**：引用了 master 中不存在的 ID → `DRIFT: orphan_reference`

### 规则 2：版本落后检测
- **检测**：读取 `state/sync-state.md` 中 `last_reconcile_snapshot`
- **比对**：读取 feature/sync-notes.md 中最后一条记录的 CHG-ID 时间戳
- **报告**：feature 的最后同步时间 < 最后一次 reconcile 时间 → `DRIFT: sync_behind`

### 规则 3：冲突定义检测
- **检测**：找出同一 REQ-ID 在多个 feature/prd.md 中的描述
- **比对**：与 master 中该 REQ 的权威定义比对
- **报告**：feature 中的描述与 master 不一致 → `DRIFT: definition_conflict`

### 规则 4：孤立变更检测
- **检测**：扫描 CONSOLIDATION-LOG.md 中所有 `status: pending / awaiting_human`
- **比对**：条目创建时间与当前时间之差
- **报告**：超过 7 天（可配置）未处理 → `DRIFT: stale_pending`

## 漂移检测报告格式

```md
## Audit Report — 2026-05-08
### Summary
- Total Features: 4
- Drift Detected: 2
- Audit Status: warning

### Drift Details

| Feature / Target | Drift Type | Severity | Suggested Action |
|-----------------|------------|----------|-----------------|
| FEAT-payment/prd.md | orphan_reference (REQ-022) | high | reconcile + propagate |
| FEAT-order/prd.md | sync_behind | medium | propagate |
| CONSOLIDATION-LOG CL-010 | stale_pending (12 days) | high | human review |
```

---

# 10. propagate dry-run 模式（纳入 MVP）

## MVP 中的 propagate 实现范围

| 功能 | MVP（v1） | v2 |
|------|----------|-----|
| `propagate --dry-run` | ✅ 实现 | - |
| `propagate`（实际写入） | ❌ 推迟 | ✅ |
| 幂等性检查（CHG-ID） | ✅ 实现（dry-run 时模拟） | - |
| propagation report 生成 | ✅ 实现（dry-run 输出） | - |

## dry-run 输出格式

```md
## Propagate Dry-Run Report — 2026-05-08 11:00

> 注意：这是预览模式，未实际写入任何文件。
> 执行实际传播请运行: lx-oma-gov propagate --execute

### Changes to be propagated

| CHG-ID | From | To | Sync Type | Content |
|--------|------|----|-----------|---------|
| CHG-20260508-001 | master-prd.md REQ-021 | FEAT-payment/prd.md | prd | 追加支付重试次数更新引用 |
| CHG-20260508-001 | master-prd.md REQ-021 | FEAT-billing/research.md | research | 追加待验证风险线索 |

### Pending Conflicts (not propagated)

| CONFLICT-ID | Affected Features | Status |
|-------------|------------------|--------|
| CONFLICT-001 | FEAT-payment | awaiting_human |

### Summary
- Total CHG to propagate: 1
- Total feature targets: 2
- Skipped (conflict pending): 1
```

---

# 11. 并发写入保护

## .lock 文件机制

- 写操作命令（init/ingest/reconcile/propagate）执行开始时在 `state/` 目录创建 `.lock` 文件
- `.lock` 文件内容：`{command, pid, started_at, timeout_at}`
- 超时时间：30 分钟（可通过 `config.yaml` 配置）
- 新命令执行前检查 `.lock` 文件：
  - 存在且未超时 → 拒绝执行，提示当前锁定状态
  - 存在且已超时 → 自动释放，继续执行，写入日志"已清除超时锁"
  - 不存在 → 正常执行
- 只读命令（status/audit）不获取锁

## .lock 文件格式

```json
{
  "command": "reconcile",
  "pid": 12345,
  "started_at": "2026-05-08T10:30:00Z",
  "timeout_at": "2026-05-08T11:00:00Z"
}
```

---

# 12. 减法操作：deprecated 机制

## 废弃规则

- `REQ-*`、`DEC-*`、`TERM-*`、`RISK-*`、`FEAT-*`、`PHASE-*` 均**不物理删除**
- 废弃时在对象定义处增加 `status: deprecated` 标签
- 保留历史快照于 `snapshots/` 目录

## feature 废弃流程

```
1. Owner 决定废弃 FEAT-xxx
2. 运行: lx-oma-gov deprecate FEAT-xxx [--reason "说明"]
3. 系统操作：
   - 在 prd/{sub_prd}/feat-xxx/prd.md 顶部插入 DEPRECATED 声明
   - 在 state/feature-map.md 中标记 FEAT-xxx status: deprecated
   - 在 PHASES.md 中更新对应 phase 的 feature 列表
   - 生成废弃快照: snapshots/prd/{sub_prd}/feat-xxx-deprecated-YYYYMMDD.md
4. audit 时识别所有引用 deprecated FEAT-xxx 的对象，输出警告
```

## REQ 废弃流程

```
1. 废弃的 REQ-* 在 master-prd.md 中标记 status: deprecated
2. audit 识别所有 feature/prd.md 中引用该 REQ 的条目
3. 输出: DRIFT: orphan_reference (REQ-NNN deprecated)
4. Owner 决定各 feature 如何处理（移除引用 / 接受新替代 REQ）
```

---

# 13. MVP 范围修订

## 修订后的 MVP 范围（v1）

| 命令 | v1 实现 | v2 实现 |
|------|---------|---------|
| `init` | ✅ 完整实现 | - |
| `ingest` | ✅ 完整实现（含三路径分级） | - |
| `reconcile` | ✅ 完整实现（含 L3 非阻塞挂起、CONFLICT-ID、CHG-ID 分配） | - |
| `propagate --dry-run` | ✅ 实现 | - |
| `propagate`（实际写入） | ❌ | ✅ |
| `status` | ✅ 完整实现（含 open CONFLICT 展示） | - |
| `audit` | ❌（基础漂移检测） | ✅（完整四类规则） |
| `resolve` | ✅ 实现（L3 裁决命令） | - |
| `deprecate` | ❌ | ✅ |

---

# 14. 结论

## 本补丁覆盖的阻塞点

| 阻塞点（Oracle 评审） | 修复位置 |
|---------------------|---------|
| L3 裁决操作路径缺失 | 第 4 节 |
| CHG-ID / CONFLICT-ID 缺失 | 第 1 节 |
| propagate 幂等性无保证 | 第 5 节 |
| propagate 推迟到 v2 制造债务 | 第 10 节、第 13 节 |
| 状态机 awaiting_human / error 缺失 | 第 2 节 |
| L2→L3 升级规则缺失 | 第 6 节 |
| 漂移检测无量化规则 | 第 9 节 |
| 并发写入无保护机制 | 第 11 节 |
| ingest 降级路径不明 | 第 7 节 |
| feature 目录分工不明 | 第 8 节 |
| 减法操作（废弃）未覆盖 | 第 12 节 |
| 越层读写权限不明 | 第 3 节 |

## 下一步

本补丁与 spec-v0 合并后，可以正式进入 `SKILL.md` 编写阶段。

编写优先级建议：
1. frontmatter（触发词、状态机定义）
2. Phase 0（init）+ Phase 1（ingest，含三路径）
3. Phase 2（reconcile，含 L3 非阻塞 + CONFLICT-ID + CHG-ID）
4. resolve 命令
5. propagate --dry-run
6. status 命令

---

> 本文件为 lx-oma-gov spec-v0 的补丁，两者共同构成 SKILL.md 编写的完整前置规范。