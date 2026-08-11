# Current Task Architecture — 任务架构基线

> 版本: 2026-07-28
> 基于实际代码: carros_base.py / gatekeeper.py / kernel.md
> 本文件为事实基线。旧设计文档 (task-architecture/) 已精简/归档，差异见此文件。

---

## 1. 任务路径

```
.omc/tasks/{YYYYMMDD}/{task_name}/
              ↑  strftime("%Y%m%d")
├── plan.md           # 计划（含步骤清单）
├── executor.md       # 执行证据账簿（schema_version: v2）
├── research.md       # 调研笔记 / Phase 0 前置澄清（goal 模式）
├── sub_task/         # 子任务（子 agent 执行）
├── state/            # 运行时状态
│   └── audit/        # 审计日志
└── final-report.md   # cmd_report 产出
```

**Token 路径**: `.omc/tokens/{YYYYMMDD}/{task_name}.json`

**关键代码**: `carros_base.py L105-122` (`_init_task_paths`)
- 日期: `datetime.now(timezone.utc).strftime("%Y%m%d")` — ❌ NOT `YYYY-MM-DD`
- task_id: kebab-case slug — ❌ NOT `task-name`

---

## 2. 状态机（Token 级）

实际代码中没有形式化的状态机轮转。Token 结构定义在 `_default_token()`（L148-175）:

```
token.status  ∈ ["active", "archived"]
token.task.status ∈ ["active"]
token.task.blocked → None | str(reason)
token.task.current_step → str
token.stats → {done: N, total: M, tick: N}
```

**生命周期**: `_init_paths → init → tick/report → archive`
- `init` → token 创建，status=active
- `archive` → token 标记 archived，任务目录 mv 到 .omc/archive/
- 无 `recovered` 状态 — recovery 通过 token 字段 `recovery_ack`/`recovery_lock` 实现
- 无 `spec_review` 状态 — 代码中不存在
- 无 `fallback_exploring` 状态

**Goal 模式扩展**: lx-goal 在 token 注入 `mode: "goal"`，由 `goal_state_machine.py` 提供额外状态管理。

---

## 3. GateKeeper 裁决链

文件: `gatekeeper.py`（~705 行）

### 分层裁决链

```
GateContext → Step1 铁律检查 → Step2 协议A/B分流
           → Step3 哲学加权 → Step4 现状/ROI调节
           → GateDecision → 格式化输出
```

### 6 种裁决输出（GateDecision Enum）

| 输出 | 含义 | 协议 |
|:----|:-----|:----:|
| `ALLOW` | 允许 | C: AI 自决 |
| `ALLOW_WITH_CONSTRAINTS` | 带约束允许 | C: AI 自决 |
| `ASK_USER` | 等待用户决策 | A: 真阻断（危险/不可逆/越权/架构调整） |
| `REDIRECT` | 拦截+引导+auto-retry | B: 轻量拦截（可修正技术问题） |
| `BLOCK` | 阻断 | A/铁律命中 |
| `SKIP` | 跳过+记录 | 无人模式降级 |

### 8 条铁律
不可编造、证据门禁、范围冻结、隐私防御、先初始化后操作、值断溯源、治理不可改、不许绕过 gate。

### 7 条哲学（权重优先级）
`less_is_more > verify_first > zero_trust > guard_first > doc_first > human_first > gain_first`

### GateKeeper 接入点（5 个 gate）

```
pretool-gate (7门) → execute → completion-gate → verify-gate → claim-audit
    ↑                    ↑          ↑                  ↑            ↑
  协议 A/B            协议 C    协议 B               协议 B       协议 B
```

### 熔断开关
`GATEKEEPER_DISABLED=true` 环境变量 → 跳过所有 GateKeeper 裁决，直接返回 ALLOW。

---

## 4. 阈值（来源: kernel.md）

| 体系 | 区间 | 动作 |
|:----|:-----|:-----|
| **A. 可控预算水位** | [0,40%) | 正常执行 |
| | [40%,70%) | checkpoint 提示，禁止扩张，触发 handoff |
| | [70%,100%] | 暂停+写 handoff+请求 compact |
| **B. 上下文水位** | <50% | 正常执行 |
| | [50%,70%) | 提醒 compact |
| | [70%,80%) | 只读模式 |
| | ≥80% | 全阻强制 compact |

**与旧文档差异**: context_guard.md 阈值 `40/50/60/80` → 实际 `40/70/80`（A体系）和 `50/70/80`（B体系）。

---

## 5. 关键引用

| 组件 | 文件 | 行数 |
|:-----|:-----|:----:|
| 任务引擎 | `carros_base.py` | ~2521 行 |
| GateKeeper 裁决链 | `gatekeeper.py` | ~705 行 |
| 错误分类规则库 | `error_rulers.json` | 17 条规则 |
| Error DNA 分类 | `error-dna.py` | ~660 行 |
| 降级引擎 | `fallback_engine.py` | ~481 行 |
| 共享写锁 | `write_lock.py` | ~58 行 |
| 内核/阈值 | `kernel.md` | 冻结规则 |
| Phase 0 契约 | `goal-contract.md` | yaml 模板 |
| 门禁手册 | `runbook.md` | 5 场景应急 |
| 自治执行规则 | `autonomous-execution.md` | lx-goal 自治参考 |

---

## 附录: vs 旧设计文档差异矩阵

| 旧文件 | 实际差异 |
|:-------|:---------|
| orchestrator.md | 状态机含不存在状态 (spec_review)；无 GateKeeper 引用；缺 recovered 机制解释 |
| task_fs.md | 日期格式 YYYY-MM-DD ≠ YYYYMMDD；task_name ≠ task_id(slug) |
| context_guard.md | 阈值 40/50/60/80 ≠ kernel.md 的 40/70/80(A) / 50/70/80(B) |
| unified_delivery_schema.md | 含不存在状态 spec_review/fallback_exploring；无 GateKeeper 6 输出 |
| loading_matrix.md | 引用 12 个 nodes/ 文件（抽象层过高）；实际加载在 carros_base.py |
| mechanism_evals.md | M1-M4 用例从未运行 |
