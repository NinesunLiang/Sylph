# 波比 · CarrorOS 最终采用方案（v2 — 经三模型评审 + Boss 裁定）

> 本方案吸收 Grok 4.5 / Opus 4.8 / GPT-5.6 Sol 三家 improve_plan 核心设计，
> 经过三家评审意见修正，并经 Boss 三条裁定封口。

---

## Boss 裁定（三条，不可推翻）

| # | 裁定 | 影响 |
|:-:|------|------|
| ① | **token.json 为唯一状态源**，不迁 state.json | 命名钉死，不留双写歧义 |
| ② | **Claude Code 优先**，OpenCode 后续兼容 | Phase 0~1 只考虑 CC 路径 |
| ③ | **仅适配中低阶模型**（deepseek-v4-flash/pro / qwen3.7-plus 等） | Oracle 也用同级别模型，不做高阶路由 |

---

## 总体路线（10 条需求全覆盖）

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

**核心思想**：改造注入逻辑，不改工作流。可控部分从 ~19K 压到 ~8K。

```
改造前：~35K total = ~16K(CC固定) + ~19K(可控)
改造后：~24K total = ~16K(CC固定) + ~8K(可控)
                                    ↓
                             可控部分压 58%
```

### S1：基线测量

抓 3~5 条真实会话，按以下维度拆账：

| 维度 | 含义 |
|------|------|
| system_tokens | CLAUDE.md + AGENTS.md + hook 注入 |
| hot_card_tokens | 当前 status --full |
| file_read_tokens | 每轮 Read 文件的内容 |
| tool_result_tokens | 工具输出全文回灌 |
| history_tokens | 对话历史累积 |
| fixed_overhead | CC tool engine ≈ 16K（实测确认） |

```bash
# 交付
.omc/metrics/r0_baseline/
  session_01~05.json
  SUMMARY.md
```

**验收**：至少 5 条会话、30+ turn、覆盖 read_only / one_file_edit / edit_and_test / long_tool_output 场景。

### S2：CLAUDE.md Slim

目标：**≤100 行 / ≤6K chars**，砍掉审核长文、多视角方案、R1-R3 全文。

**禁令**：禁止阅读或粘贴 `docs/carros/reviews/**`；禁止整份 architecture 进对话。

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
python3 .claude/scripts/carros_base.py status --task-id <id>

## 回合
1. 只执行 `tick` 给出的一个 action
2. 每轮最多读 2 个 allowed 文件；大文件用 offset/limit
3. 工具长输出只看预览；全文在 artifacts/
4. 不复述 plan；不写长方案论文

## Budget
- soft/hard 见 token.budget；软水位写 handoff
- 不依赖 L5 AutoCompact（有损不可逆）

## Scope
- 只动 allowed_paths；secrets / .env / reviews 永不读

## 关于 Oracle
- L1 / Phase 0 禁调用 Oracle
- L2 高风险流程可条件使用（Phase 1+）
```

**验收**：≤100 行 / ≤6K chars / 禁词检测（无 "Meta-Oracle" / "完整改造方案" / "Opus 4.8 视角"）。

### S3：Hot Card — status 默认输出

采用 Opus 的 Hot Card 格式，**替代当前 `status --full`**。

```python
# .claude/scripts/lib/hot_card.py
HOT_MAX_CHARS = 4500

def render_hot_card(token: dict, step: dict, last_events: list) -> str:
    """
    输出模板（字段顺序固定，禁止 dict 无序拼接）：
    # CarrorOS Hot Card
    task: <id> | level: L1 | step: S1
    ticks: <n> | turns: <n> | verified: [..]
    budget: soft=<a> hard=<b> pct=<x>
    scope.allowed: [...] | scope.denied: [...]
    step.intent: <≤160 chars>
    step.files: [...] | step.verify: [...]
    last3:
    - <event short>
    next: python3 .claude/scripts/carros_base.py tick --task-id <id>
    """
```

**Hot Card 约束**：
- 是 token.json + plan step + evidence 的**派生视图**，不可独立编辑
- 同一输入状态 → 完全相同输出（确定性）
- HARD limit：chars ≤ 4500、token 估计 ≤ 1500
- **字段顺序写死为 tuple，禁止 dict 无序拼接**

**验收**：`status` 默认输出 ≤ 4.5K chars、含 "Hot Card" 标记、字段顺序固定。

### S4：工具结果落盘 + 稳定预览

**核心机制**：工具长输出 → 全文无损落盘 `artifacts/`，模型只见稳定预览。

```python
# .claude/scripts/lib/tool_store.py
TOOL_PREVIEW_CHARS = 2000

def store_tool_result(task_id: str, content: bytes, meta: dict) -> dict:
    """
    全文 → .omc/tasks/<date>/<id>/artifacts/tool_<seq>.log
    returns: { artifact_path, exit_code, bytes, preview }
    """
    
def build_preview(content: bytes, exit_code: int) -> dict:
    """
    内容寻址 preview（GPT-5.6 建议）：
    同一 content → 同一 body 前缀
    路径不进入 cache-sensitive 前缀
    """
    digest = sha256(content).hexdigest()
    return {
        "artifact_path": f".omc/artifacts/sha256/{digest[:2]}/{digest}.log",
        "exit_code": exit_code,
        "bytes": len(content),
        "preview": f"""[tool_result stored]
digest: {digest[:12]}
exit_code: {exit_code}
bytes: {len(content)}

{utf8_slice(content, 1200)}
{tail_error_lines(content, 600) if len(content) > 1800 else ''}
{'...[TRUNCATED]' if len(content) > 2000 else ''}"""
    }
```

**模板字节级稳定**：同一 content 多次 store → preview body 完全相同。

**验收**：100KB 日志落盘 > 10KB、preview ≤ 2.2K chars、同内容 body 前缀一致。

### S5：PreTool 读盘门禁

```python
# .claude/hooks/pretool-gate.py（唯一 PreTool 入口）
# 规则（各模型共识）：
G1 单 tick >2 文件                    → BLOCK
G2 无 offset/limit 且 >200 行        → BLOCK
G3 docs/carros/reviews/**            → BLOCK
G4 .env / secrets/ / *credential*     → BLOCK
G5 glob "**/*" 无类型收窄            → BLOCK
G6 估算本轮已读 + 新文件超预算       → CHECKPOINT_FIRST
```

**返回值结构化**（GPT-5.6 建议）：

```yaml
decision: ALLOW | DENY | NARROW | CHECKPOINT_FIRST
reason_code: G1_FILE_COUNT
suggested_request:  # DENY 时给出修正建议
  path: src/auth.ts
  offset: 120
  limit: 80
```

**验收**：`python3 pretool-gate.py --self-test` → 6 条规则全绿。

### S6：饲喂模板固化

每轮 Context composition 顺序固定：

```text
[1] Slim System (CLAUDE.md + AGENTS.md)   ≤ 2.0K tokens  ← 前缀稳定，cache 友好
[2] Hot Card                                ≤ 1.5K tokens
[3] 当前文件切片 ≤2 文件                    ≤ 2.5K tokens
[4] 最近 ≤2 条工具预览                     ≤ 1.0K tokens
[5] 用户本轮指令                            ≤ 1.0K tokens
───────────────────────────────────────────────
可控合计                                    ≤ 8.0K tokens
CC 固定                                     ≈ 16K
───────────────────────────────────────────────
总 median                                   ≤ 24K
```

同时交付 `.claude/prompts/executor_micro.txt`（≤15 行 / ≤800 chars）。

### S7：成本报表

**统一目标/SLO/硬上限口径**（GPT-5.6 要求）：

```yaml
context_budget:
  controllable:
    target_median_tokens: 8000   # 目标
    slo_p50_tokens: 9000         # 服务等级
    hard_p50_tokens: 12000       # 红线（超过即 FAIL）
    hard_p95_tokens: 16000
  total:
    target_median_tokens: 24000
    hard_p95_tokens: 48000
```

**负向 SLO**（Grok 要求）：

```yaml
negative_slo:
  - tool_full_in_context_rate > 0.05              → FAIL
  - l5_as_memory == 1                              → FAIL
  - controllable_median > 12000                    → FAIL
  - total_p95 > 48000                              → FAIL
  - cache_hit_rate < 60%（可观测时）              → FAIL（CC 路径）
  - same_content_same_preview == false             → FAIL
```

```bash
# 命令
python3 .claude/scripts/carros_cost_report.py --last 50
# 输出：
# samples: 42 turns
# controllable_median: 7400 / total_median: 23400
# controllable_p95: 12000 / total_p95: 44000
# tool_full_in_context_rate: 0.02 | l5_rate: 0.00
# PASS_P0: yes/no
```

### S8：回归验证

**基线场景**（Opus H1-H3 + Grok/GPT 追加）：

| 场景 | 操作 | 轮数 | 验证目的 |
|:----:|------|:----:|:--------:|
| H1 | README 改一行 | 5~8 | 基础 Hot Card |
| H2 | 修 1 文件 + 跑 1 测试 | 5~8 | 工具落盘 + preview |
| H3 | 只读解释 1 函数 | 5~6 | 读盘门禁 |
| H4 | 100KB 测试日志生成 | 3~5 | 工具落盘反压 |
| H5 | 跨 2 文件 + 连续 12 轮 | 12 | 无线性增长 |

**验收**：
- median total ≤ 24K、P95 total ≤ 48K
- controllable median ≤ 8K
- smells 全灭（review_markdown_in_prompt / test_log_full_in_prompt / repeated_full_file_reads）
- same_content_same_preview == true
- hot_card_default == true
- pretool_self_test: all green

---

## Phase 0.5 — 文档基建（需求 2, 3）

### W1：Handoff.md 重构 + Resume Preflight

**Resume Capsule**（手写交接导航，非真相源）：

```markdown
## ⚠️ NOT SOURCE OF TRUTH
Resume engine MUST load token.json (CAS) first.
This handoff is navigation only. Do not parse current state from this file.

## Goal
<原始任务目标>

## Confirmed Decisions
- <关键决策>

## Next Action
<下一步动作>

## Required Reads
- <需要读取的文件/文档精确片段>

## Do Not Reload
- 全部旧 transcript
- docs/reviews/**
- 完整测试日志
```

**Resume Preflight 顺序钉死**（Grok 要求）：
1. token.json CAS load  ← 先读状态
2. plan 版本一致性检查
3. external_effects 三界检查（IN_FLIGHT/UNKNOWN → BLOCKED）
4. 再读 handoff 作导航  ← handoff 是导航，不是状态

### W2：文档系统轻量升级

从"当前几件套"过渡。**按任务等级实例化**（GPT-5.6 建议）：

```yaml
task_profiles:
  L1:
    required: [token.json, artifacts]
    derived: [hot_card]
    optional: [plan.md, handoff.md]
  L2:
    required: [token.json, plan.md, evidence.jsonl, artifacts]
    conditional: [handoff.md]
```

**目录约定**（不强制全部创建）：

```text
.omc/tasks/<date>/<task-id>/
├── token.json                          # 唯一状态源（Boss 裁定）
├── plan.md                             # 已有
├── handoff.md                          # W1 增强
├── evidence.jsonl                      # verify 绑定
└── artifacts/
    ├── tool_0001.log
    ├── tool_0002.log
    └── ...
```

### W3：docs/INDEX.yaml（轻量版）

给核心文档建立机器可读索引，**先看 INDEX 再看正文**：

```yaml
# docs/INDEX.yaml
documents:
  - id: ARCH-CONTEXT
    path: docs/architecture/context-engine.md
    summary: 上下文编译、披露与恢复协议
    headings:
      - id: progressive-disclosure
        lines: [42, 118]
    estimated_tokens:
      full: 6400
      summary: 220
```

**Token.json CAS 增强**：

```json
{
  "schema_version": "carros.token.v2",
  "revision": 7,
  "task": { "id": "...", "level": "L1", "current_step": "S1" },
  "progress": { "verified_steps": ["S1"], "ticks": 5 },
  "budget": { "turns": 5, "max_turns_soft": 12, "max_turns_hard": 18 },
  "scope": { "allowed_paths": [...] }
}
```

### W4：12 条系统不变量

```text
# 真相
INV-01  聊天不是任务状态源。状态在 token.json。
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

**⚠️ 注意**：因 Boss 裁定仅适配中低阶模型（deepseek-v4-flash/pro、qwen3.7-plus），
以下所有 Oracle、模型路由、架构审查均使用**同级模型**，不涉及 Opus/GPT/Grok 等高阶模型。

### L2 工作流

L1 保持现有 `init → tick → verify → archive` 不变。L2 新增：

```text
Plan Review → Execute → Verify → Oracle(条件) → Archive
```

**L2 准入条件**：跨模块修改、公共 Contract 变化、安全权限、用户显式要求 L2。
**L1→L2 不自动升级**，Boss 要在场。

### U 型注意力模型

```text
HEAD (≤2K, 稳定前缀)        ← 极少改动，cache 友好
  Slim System + 规则
MIDDLE (可裁剪)              ← 历史工具预览
  Claude L1-L3 压缩
TAIL (每轮重生成)            ← 当前指令
  Hot Card + todo + 用户指令
  每 5 轮注入一次状态更新到 TAIL
```

**HEAD 必须锁死**，禁止因 middle 切片变化而重排。

### 工作流自闭环

每步失败自动生成 Error DNA → 最多 retry 3 次 → 仍失败则 BLOCKED + 写状态。

```json
{
  "step": "S2",
  "error": "test failed: expected 1 call, got 3",
  "artifact": "artifacts/test-0017.log",
  "retry_count": 2
}
```

### Oracle 条件接入（单审，同级模型）

**Oracle 使用 deepseek-v4-flash 或同级别模型**，非高阶模型。

| 场景 | Oracle | 预算估计 |
|:----:|:------:|:--------:|
| L1 任务 | ❌ 不调 | $0 |
| L2 方案审核 | 🟡 residual risk 高时 | 同级模型成本 |
| L2 结果验证 | 🟡 不稳定时 | 同级模型成本 |
| 常规 L2 step | ❌ 不调 | $0 |

**Oracle 输出不进 VerifyGate**。VerifyGate 必须先满足确定性 Evidence；
Oracle 只判断 residual risk，不能把 FAIL 改成 VERIFIED。

---

## Phase 2 — 飞轮 + 无人模式（需求 4, 7）

### 飞轮系统

```text
Error DNA (每次)
    ↓
kernel.md 升华 (按条件触发)
    ↓
anti-patterns.md 沉淀
```

**飞轮数据默认落 `.omc/knowledge/**`，进 Context 需经白名单 + token 预算。**
**禁止飞轮数据默认塞进 HEAD / Hot Card。**

### 无人模式

| 组件 | 内容 |
|------|------|
| Autonomy Contract | 权责范围、最大无人轮次、异常上报策略 |
| Loop 硬化 | 最大循环次数、状态漂移检测、自动 handoff |
| 可恢复性 | Phase 0.5 Handoff + Phase 1 VerifyGate 保障 |

### 外部副作用三界

```text
界 1 文件修改    ：Git / Claude Checkpoint → 无损可回滚
界 2 任务状态    ：token.json CAS → 可回退到 last VERIFIED
界 3 外部副作用  ：API/部署/DB → 状态机，不可逆则禁止自动回滚
```

**Resume Preflight 硬闸**：任一 `IN_FLIGHT/UNKNOWN` → BLOCKED。

---

## Phase 3 — 双审判官（需求 10，按需）

**Oracle + Mate Oracle，均使用同级中低阶模型。**

| 角色 | 触发条件 |
|:----:|----------|
| Oracle（主审） | L2 高风险时，单次 |
| Mate Oracle（副审） | 仅争议裁决时激活 |
| Meta Oracle（聚合） | 仅在 Oracle 有分歧时调用 |

## 10 条需求的全景映射

| # | 需求 | Phase | 核心 |
|:-:|------|:-----:|------|
| 1 | Context Boom | 0 | S1~S8 |
| 2 | Compact / Handoff | 0.5 | W1 |
| 3 | 文档系统 | 0.5 | W2~W4 |
| 4 | 飞轮 | 2 | 落盘不进 Context |
| 5 | L1/L2 分级 | 1 | L2 工作流 |
| 6 | U 型注意力 | 1 | HEAD+TAIL |
| 7 | 无人模式 | 2 | Autonomy Contract |
| 8 | 工作流自闭环 | 1 | Error DNA |
| 9 | Oracle 辅助 | 1（单审） | 同级模型 |
| 10 | 双审判官 | 3 | 按需 |

---

## 修正后的量化目标

| 指标 | 目标 | 含义 |
|------|:----:|------|
| total median | **≤ 24K** | 16K 固定 + 8K 可控 |
| total P95 | **≤ 48K** | |
| controllable median | **≤ 8K** | target；SLO 9K；红线 12K |
| controllable P95 | **≤ 16K** | |
| tool_full_in_context | **0%** | 全文回灌归零 |
| reviews 入模率 | **0%** | 审核长文禁止 |
| cache_hit_rate | **≥ 60%** | CC 路径；不可观测则用 stable_prefix_hash 代理 |

## 各来源贡献

| 来源 | 核心贡献 |
|:----:|----------|
| **Grok 4.5** | 压缩铁律、cache 稳定性、负向 SLO、副作用三界、飞轮 Context 隔离 |
| **Opus 4.8** | MVP 三阶段、Hot Card 格式与验收、H1-H5 场景、Oracle 条件触发原则 |
| **GPT-5.6 Sol** | 内容寻址 Artifact、按等级实例化文件、测量口径统一、handoff 非真相源 |
| **Boss 裁定** | token.json 唯一源、CC 优先、仅中低阶模型 |
| **波比** | Phase 0 纯 Token Slim、S1~S8 可执行计划、16K 固定约束修正、评审意见落地 |
