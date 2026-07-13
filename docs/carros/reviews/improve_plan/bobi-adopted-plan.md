# 波比 · CarrorOS 最终采用方案

> 本方案吸收 Grok 4.5 / Opus 4.8 / GPT-5.6 Sol 三家 improve_plan 的核心思想。
> 每项设计标注来源：`[G]` = Grok, `[O]` = Opus, `[G5]` = GPT-5.6 Sol, `[B]` = 波比。

---

## 总体路线

```text
Phase 0 (3~4天)       Phase 0.5 (~1周)       Phase 1 (1~2周)        Phase 2 (~2周)         Phase 3 (按需)
Token Slim             文档基建                L2 治理                飞轮+无人               双审判官
┌──────────────┐      ┌──────────────┐       ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ 需求 1        │  →  │ 需求 2,3     │  →   │ 需求 5,6,8,9  │  →   │ 需求 4,7     │  →   │ 需求 10      │
│ Context Boom  │      │ Compact+文档  │      │ L1/L2+U型+自  │      │ 飞轮+无人     │      │ 双审判官      │
│              │      │              │      │ 闭环+Oracle   │      │              │      │              │
└──────┘      └──────┘       └──────┘       └──────┘       └──────┘
  不可动的 CC 引擎 ≈ 16K fixed
```

---

## Phase 0 — Token Slim（需求 1）

**来源**：核心设计 `[B]`，细节深化 `[O][G5]`，压缩策略 `[G]`

### 核心思想
改造注入逻辑，不改工作流。把可控部分从 19K 压到 8K。

```text
改造前：16K(CC固定) + 19K(可控) = 35K median
改造后：16K(CC固定) + 8K(可控)  = 24K median
                              ↓
                       可控部分压 58%
```

### S1：基线测量 `[B]`

抓 3~5 条真实会话，按以下维度拆账：

| 维度 | 含义 |
|------|------|
| system_tokens | CLAUDE.md + AGENTS.md + hook 注入 |
| hot_card_tokens | 当前 status --full（替代 Hot Card 后对比）|
| file_read_tokens | 每轮 Read 文件的内容 |
| tool_result_tokens | 工具输出全文回灌 |
| history_tokens | 对话历史累积 |
| fixed_overhead | CC tool engine ≈ 16K |

```bash
# 交付
.omc/metrics/r0_baseline/
  session_01.json ... session_05.json
  SUMMARY.md
```

### S2：CLAUDE.md Slim `[O][G5]`

```markdown
# CarrorOS Base · Slim Rail

## 真相
- 状态：`.omc/**` 文件。聊天不是真相。
- 完成：仅 `verify` 返回 VERIFIED。

## 命令
python3 .claude/scripts/carros_base.py init --task-id <id>
python3 .claude/scripts/carros_base.py tick --task-id <id>
python3 .claude/scripts/carros_base.py verify --task-id <id> --step <Sx>
python3 .claude/scripts/carros_base.py archive --task-id <id>
python3 .claude/scripts/carros_base.py status --task-id <id> --hot

## 回合
1. `status --hot`（禁止默认 full）
2. 只执行 `tick` 给出的一个 action
3. 每轮最多读 2 个 allowed 文件；大文件用 offset/limit
4. 工具长输出只看预览；全文在 artifacts/
5. 不复述 plan；不写长方案论文；不调用 Oracle

## Scope
- 只动 `allowed_paths`；永不读 secrets / .env / production 密钥

## 预算
- soft/hard 见 token.budget；软水位写 handoff（无损）
- 禁止依赖 L5 AutoCompact（有损不可逆）

## 禁止注入
- 禁止阅读或粘贴 `docs/carros/reviews/**`
- 禁止整份 architecture 进对话
```

**验收**：≤100 行 / ≤6K chars / 禁词检测通过。

### S3：Hot Card — status --hot `[O][B]`

采用 **Opus 的 Hot Card 格式**，替代当前 `status --full`。

```python
# .claude/scripts/lib/hot_card.py
HOT_MAX_CHARS = 4500

def render_hot_card(token: dict, step: dict, last_events: list) -> str:
    """
    输出模板（固定字段顺序）：
    # CarrorOS Hot Card
    task: <id> | level: L1 | step: S1
    ticks: <n> | turns: <n> | verified: [..]
    budget: soft=<a> hard=<b> pct=<x> l5=<bool>
    cost: in=<n> out=<n> oracle=<0>
    scope.allowed: [...] | scope.denied: [...]
    step.intent: <≤160 chars>
    step.files: [...] | step.verify: [...]
    last3:
    - <event short>
    constraints: one_action | no_full_plan | verify_only_done
    resume: python3 .claude/scripts/carros_base.py tick --task-id <id>
    """
```

**⚠️ 禁止**：在 Hot Card 中嵌入完整 plan、executor、audit 正文。

**验收**：`status --hot` 默认输出 ≤ 4.5K chars、含 "Hot Card" 标记。

### S4：工具结果落盘 + 稳定预览 `[O][G]`

**核心机制**：凡工具输出超过阈值 → 全文无损落盘 `artifacts/`，模型只见稳定预览。

```python
# .claude/scripts/lib/tool_store.py
TOOL_PREVIEW_CHARS = 2000

def store_tool_result(task_id: str, content: str | bytes, meta: dict) -> dict:
    """
    全文 → .omc/tasks/<date>/<id>/artifacts/tool_NNNN.log
    returns: { artifact_path, exit_code, bytes, preview }
    """
    
def build_preview(content: str, max_chars=2000) -> str:
    """模板必须字节级稳定（Grok 的 prompt cache 稳定要求）"""
    return f"""[tool_result stored]
path: {path}
exit_code: {code}
bytes: {n}

{content[:max_chars]}
{'...[TRUNCATED]' if len(content) > max_chars else ''}"""
```

**Grok 要求**：同一 content 多次 store → preview 字符串应相同。 `[G]`

**验收**：100KB 日志落盘 > 10KB、preview ≤ 2.2K chars、同内容 body 前缀一致。

### S5：PreTool 读盘门禁 `[O][G5]`

```python
# .claude/hooks/pretool-gate.py（唯一 PreTool 入口）
# 规则：
G1 单 tick >2 文件                    → BLOCK
G2 无 offset/limit 且 >200 行        → BLOCK
G3 docs/carros/reviews/**            → BLOCK
G4 .env / secrets/ / *credential*     → BLOCK
G5 glob "**/*" 无类型收窄            → BLOCK
G6 估算本轮已读 + 新文件超预算       → CHECKPOINT_FIRST
```

**验收**：`python3 pretool-gate.py --self-test` → 6 条规则全绿。

### S6：饲喂模板固化 `[G5]`

每轮 Context composition 顺序固定，前缀尽量稳定：

```text
[1] Slim System (CLAUDE.md + AGENTS.md)   ≤ 2.0K tokens  ← 前缀稳定，cache 友好
[2] Hot Card                                ≤ 1.5K tokens
[3] 当前文件切片 ≤2 文件                    ≤ 2.5K tokens
[4] 最近 ≤2 条工具预览                     ≤ 1.0K tokens
[5] 用户本轮指令                            ≤ 1.0K tokens
───────────────────────────────────────────────
可控合计                                    ≤ 8.0K tokens
CC 固定                                    16K
───────────────────────────────────────────────
总 median                                   ≤ 24K
```

同时交付 `docs/carros/runbooks/composition.md` 和 `.claude/prompts/executor_micro.txt`（≤15行）。

### S7：成本报表 `[O][B]`

```bash
python3 .claude/scripts/carros_cost_report.py --last 50
# 输出：
# samples: 42 turns
# median_in: 7400 (controllable) / 23400 (total)
# p95_in: 28000 (controllable) / 44000 (total)
# tool_full_in_context_rate: 0.02
# l5_rate: 0.00
# PASS_P0: yes/no
```

**红线**：`[G]` 负向 SLO 风格。
- tool_full_in_context_rate > 0.05 → FAIL
- l5_as_memory = 1 → FAIL
- median_in(p0) > 12000 → FAIL（可调控部分）
- cache_hit_rate < 60% → FAIL（如有数据）

### S8：回归验证 `[O][H1-H5 验收场景]`

| 场景 | 操作 | 轮数 |
|:----:|------|:----:|
| H1 | README 改一行标记 | 5~8 |
| H2 | 修 1 文件 + 跑 1 测试 | 5~8 |
| H3 | 只读解释 1 函数 | 5~6 |

**验收**：median ≤ 24K（含固定）、P95 ≤ 48K、可控 median ≤ 8K、smells 全灭。

---

## Phase 0.5 — 文档基建（需求 2, 3）

**来源**：核心设计 `[G5]`，Handoff 逻辑 `[O]`，负向 SLO `[G]`

### W1：Handoff.md 重构 + Resume Preflight `[O][B]`

现有 handoff.md 增强为恢复入口，增加 Resume Preflight 验证：

```markdown
# Resume Capsule
schema_version: carros.handoff.v2

## Goal
<原始任务目标>

## Current State
- step: S2 | status: running | verified: [S1] | blocked: false

## Confirmed Decisions
- <关键决策>

## Changed Files
- <修改过的文件>

## Evidence
- E17: <证据概要> | artifact: artifacts/test-0017.log

## Next Action
<下一步动作>

## Required Reads
- <需要读取的文件/文档精确片段>

## Do Not Reload
- 全部旧 transcript
- docs/reviews/**
- 完整测试日志
```

**Resume Preflight 新增硬闸** `[G]`：检查外部副作用三界中是否有 `IN_FLIGHT`/`UNKNOWN` → BLOCKED，不得装成 CONTINUE。

### W2：文档系统四件套 `[G5][O]`

从当前"四件套"（token.json / plan.md / executor.md / session-handoff.md）升级为"分责七件套"：

```text
manifest.yaml       # 任务入口、等级、目标、索引          [G5]
state.json          # 唯一运行状态机（兼容旧 token.json） [O]
plan.md             # 完整计划；默认只披露 current step   [B]
working-set.yaml    # 当前 Context 的白名单与预算          [G5]
handoff.md          # 跨会话恢复入口                      [O]
evidence.jsonl      # 证据索引，不存完整日志               [G5]
artifacts/          # 完整工具结果、patch、测试报告         [O]
```

**目录约定**：

```text
.omc/tasks/<date>/<task-id>/
├── manifest.yaml
├── state.json           # 迁移期兼容旧 token.json
├── plan.md
├── working-set.yaml
├── handoff.md
├── evidence.jsonl
├── context/
│   ├── capsule.current.md
│   └── receipts.jsonl
└── artifacts/
    ├── tool_0001.log
    ├── tool_0002.log
    └── ...
```

### W3：docs/INDEX.yaml `[G5]`

给项目文档建立机器可读索引：

```yaml
# docs/INDEX.yaml
schema_version: carros.docs.v1

documents:
  - id: ARCH-CONTEXT
    path: docs/architecture/context-engine.md
    authority: normative
    status: active
    summary: CarrorOS 上下文编译、披露与恢复协议
    tags: [context, memory, compaction]
    headings:
      - id: progressive-disclosure
        title: 渐进式披露
        lines: [42, 118]
    estimated_tokens:
      full: 6400
      summary: 220
```

**原则**：Agent 默认先看 INDEX，不先看正文。 `[G5]`

### W4：系统不变量（12 条）`[G5→减到12条]`

```text
# 真相
INV-01  聊天不是任务状态源。状态在 `.omc/`。
INV-02  transcript 是审计记录，不是正常恢复入口。
INV-03  LLM Summary 是有损导航，不是真相源。
INV-04  完整工具输出 → artifacts；evidence 只存索引。

# 执行
INV-05  每个 tick 只执行一个可验证动作。
INV-06  只改 allowed_paths；denied_paths 优先级最高。
INV-07  只有 VerifyGate 可以把 step 标记为 VERIFIED。

# Context
INV-08  每轮 Context 从文件重建，不在旧 transcript 上追加。
INV-09  默认只读 Hot Card + 当前文件切片 + 最近工具预览。
INV-10  reviews/ 禁止默认入模。

# Compaction
INV-11  工具落盘 + 有界预览属于无损可回滚治理。
INV-12  禁止 L5 AutoCompact 当记忆。
```

---

## Phase 1 — L2 治理（需求 5, 6, 8, 9）

**来源**：核心设计 `[O]`，U 型注意力 `[G5]`，模型路由 `[G]`

### L2 工作流 `[O]`

L1 保持现有 `init → tick → verify → archive` 不变。L2 新增 `carros_enhance.py`：

```text
Research → Plan Review → Checkpoint → Execute → Verify → Oracle(条件) → Memory Writeback → Archive
```

**L2 准入条件**：
- 跨模块修改、公共 Contract 变化、安全权限、迁移、外部副作用
- 超时 &gt; soft budget、用户显式要求 L2

**L1→L2 不自动升级**，除非满足条件。 `[B]`

### U 型注意力模型 `[G5]`

```text
HEAD (≤2K, 稳定前缀)           ← 几乎不变，cache 友好
  Slim System + Hot Card 模板头
MIDDLE (可裁剪)                ← 历史工具预览、对话上下文
  Claude L1-L3 压缩 / OpenCode Prune
TAIL (每轮重生成)               ← 当前指令
  Hot Card 内容 + todo 列表 + 用户本轮指令
  GPT-5.6 要求：每 5 轮注入一次状态更新到 TAIL
```

**Grok 补充**：HEAD 必须锁死，禁止因 middle 切片变化而重排。 `[G]`

### 工作流自闭环 `[B][O]`

每步失败自动生成 Error DNA → 最多 retry 3 次 → 仍失败则 BLOCKED + 写状态。

```python
# Error DNA 格式
{
  "step": "S2",
  "error": "test failed: expected 1 call, got 3",
  "artifact": "artifacts/test-0017.log",
  "retry_count": 2,
  "suggestion": "check refreshToken in-flight promise"
}
```

### Oracle 条件接入（单审） `[O]`

| 场景 | Oracle | 预算 |
|:----:|:------:|:----:|
| L1 任务 | ❌ 不调 | $0 |
| L2 方案审核 | 🟡 residual risk 高时调 | < $0.05/次 |
| L2 结果验证 | 🟡 测试不稳定时调 | < $0.05/次 |
| 常规 L2 step | ❌ 不调 | $0 |

**Opus 原则**：Oracle 是辅助决策，不是每 step 标配。 `[O]`

### 模型路由 `[G]`

| 场景 | 模型 | 理由 |
|:----:|:----:|------|
| 搜索/测试/读文件摘要 | DeepSeek V4 Flash | 便宜、吞吐高 |
| L1 小修执行 | Flash | 风险可控 |
| L2 规划/架构/争议裁决 | Opus-4.8 / 高阶模型 | 长程一致性 |
| Oracle（条件触发） | 高阶模型，预算 < $0.05/次 | 绝非每 step |

### OpenCode 接入（session roles）`[G]`

```text
Session Roles:
  execute    → 唯一可以写 state.json
  retrieve   → 只读文档/代码，返回 Knowledge Patch
  review     → 只读审查，返回 Review Verdict
  govern     → 审计/成本/规则，只读状态

硬约束：
  只有 execute 或 govern 之一可以写 token（单一 State Writer）
  retrieve / review 只产出 Artifact，不得改 state
```

---

## Phase 2 — 飞轮 + 无人模式（需求 4, 7）

**来源**：飞轮 `[O]` + `[G5]`，无人模式 `[B]`，副作用三界 `[G]`

### 飞轮系统 `[O][G5]`

```text
Error DNA (每次)
    ↓
kernel.md 升华 (按条件触发)
    ↓
AGENTS.md 更新 / anti-patterns.md 沉淀
    ↓
claude-next 记录优化建议
```

**硬隔离** `[G]`：飞轮数据默认落 `.omc/knowledge/**`，进 Context 仅通过 D2 白名单 + token 预算。**禁止**飞轮数据默认塞进 HEAD / Hot Card。 `[G]`

### 无人模式 `[B][O]`

| 组件 | 内容 |
|------|------|
| Autonomy Contract | 权责范围、最大无人轮次、异常上报策略 |
| Loop 硬化 | 最大循环次数、状态漂移检测、自动 handoff |
| 可恢复性 | Phase 0.5 Handoff + Phase 1 VerifyGate + Phase 0.5 状态文档化 三层保障 |

### 外部副作用三界 `[G]`

```text
界 1 文件修改    ：Git / Claude Checkpoint → 无损可回滚
界 2 任务状态    ：state.json CAS 版本 → 可回退到 last VERIFIED
界 3 外部副作用  ：API/部署/DB → 状态机 PENDING → IN_FLIGHT → COMMITTED | FAILED
                  不可逆副作用 → 禁止自动回滚，只生成补偿清单
```

**Resume Preflight 硬闸**：任一 `IN_FLIGHT/UNKNOWN` → BLOCKED，不得装成 CONTINUE。 `[G]`

### 多 Agent 协同 `[G5]`

```text
主执行 Agent       → 只持有当前 Context Capsule
文档检索 Agent     → fresh context，只查询 docs/index
代码探索 Agent     → fresh context，只定位符号和依赖
审查 Agent         → fresh context，接收明确 patch + contract
验证 Agent         → fresh context，跑确定性验证
```

返回主会话的不是完整推理，是结构化 Knowledge Patch。 `[G5]`

---

## Phase 3 — 双审判官（需求 10）

**来源**：设计 `[O]`，成本控制 `[G]`，隔离 `[G5]`

### Oracle + Mate Oracle `[O]`

```text
Oracle Agent（主审）：
  - L2 方案审核
  - L2 结果验证
  - residual risk 高时

Mate Oracle（副审）：
  - 仅关键架构决策和争议裁决
  - 默认不激活

Meta Oracle（聚合）：
  - 接收 Oracle + Mate 的 verdict
  - 输出最终裁决
```

**触发条件** `[G]`：Oracle 调用 < L2 任务的 30%（防过度依赖）。

**预算** `[G]`：单次 Oracle 调用 < $0.05，Mate 仅在争议场景激活，Meta 仅在 Oracle 有分歧时。

---

## 10 条需求的全景映射

| # | 需求 | 在哪解决 | 核心来源 | 验收 |
|:-:|------|:--------:|:--------:|------|
| 1 | Context Boom | Phase 0 S1~S8 | `[B][O][G][G5]` | median ≤ 24K |
| 2 | Compact / Handoff | Phase 0.5 W1 | `[O][G]` | 删 transcript 可恢复 |
| 3 | 文档系统 | Phase 0.5 W2~W4 | `[G5][O]` | 七件套 + INDEX 可查询 |
| 4 | 飞轮 | Phase 2 | `[O][G5][G]` | 数据落盘不进 Context |
| 5 | L1/L2 分级 | Phase 1 | `[O]` | L2 可单独触发 |
| 6 | U 型注意力 | Phase 1 | `[G5][G]` | HEAD 锁死，TAIL 每 5 轮 |
| 7 | 无人模式 | Phase 2 | `[B][O]` | 30+ step 不间断 |
| 8 | 工作流自闭环 | Phase 1 | `[B][O]` | Error DNA + retry ≤ 3 |
| 9 | AI 自决定 + Oracle | Phase 1（单审） | `[O][G]` | Oracle < 任务 30% |
| 10 | 双审判官 | Phase 3 | `[O][G]` | 仅争议场景 |

---

## Claude Code 路径 vs OpenCode 路径

| 能力 | Claude Code | OpenCode |
|:----:|:-----------:|:--------:|
| 压缩阶梯 | L1 落盘 → L2 裁剪 → L3 微压缩 | Prune(hidden) → 摘要 Agent |
| L5 AutoCompact | 禁止当记忆 | 不适用（无 L5） |
| 审计 | .omc/metrics + 文件 | SQLite 原始会话 + .omc 文件 |
| 恢复 | state + handoff + state.json | 同左，+ SQLite 审计 |
| 多会话 | subagent（Phase 2） | Session Roles（Phase 1） |
| cache 稳定 | ⚠️ 必须锁死前缀 | 不适用 |
| Phase 1 接入 | ✅ 默认 | 🟡 新增 session roles |

---

## 修正后的量化目标

| 指标 | 修正目标 | 含义 |
|------|:--------:|------|
| median 总输入 | **≤ 24K** | 16K 固定 + 8K 可控 |
| P95 总输入 | **≤ 48K** | 16K 固定 + 32K 可控 |
| 可控 median | **≤ 8K** | System + Hot Card + 文件 + 预览 + 用户 |
| 可控 P95 | **≤ 32K** | 防读盘爆炸尖刺 |
| tool_full_in_context | **0%** | 全文回灌率归零 |
| reviews 入模率 | **0%** | 审核长文禁止注入 |
| cache_hit_rate | **≥ 70%** | Claude 前缀稳定 |

---

## 各模型贡献鸣谢

| 来源 | 核心贡献 |
|:----:|----------|
| **Grok 4.5** | 压缩优先级铁律、prompt cache 稳定性、场景路由、负向 SLO、飞轮 Context 隔离、外部副作用三界、OpenCode session roles |
| **Opus 4.8** | MVP 三阶段思想、Hot Card 格式与验收、token.json 唯一状态源、H1-H5 验收矩阵、Oracle 条件触发原则 |
| **GPT-5.6 Sol** | 四平面架构方向、Context Capsule 概念、Working Set 白名单、INDEX.yaml 文档索引、23 条不变量（本方案采纳 12 条）、每轮 Context 重建而非追加 |
| **波比** | 16K 固定开销的约束识别与目标修正、Phase 0 纯 Token Slim 定位、五段 Phase 划分、S1~S8 可执行计划、三模型分歧的仲裁与采纳、执行层面的路径验证 |
