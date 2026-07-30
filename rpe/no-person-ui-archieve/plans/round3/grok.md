**Grok 4.5 审核：搜索空间 + Token 边界 + 6h 宿主可靠性视角**

材料状态：
- ✅ `GAP-FIX-REPORT.md` 可读（部分截断）
- ❌ `orchestrator.py` **404**
- ❌ 无任何 dry-run artifacts / gate-results / measurements / checkpoint

因此本审核是 **契约级 + 风险消解级** 审核，不是代码级终审。

---

## 一句话判决

```yaml
verdict: NO-GO for real 6h overnight
allowed: dry-run only (≤30min, supervised, token write必禁)
confidence: high (报告已暴露多个结构性缺口，不需要看到全量代码也能判定)
```

报告标题写 **「13/13 Critical Gaps Fixed」**，但正文只列出 10 项（1–9, 12）。  
这在自动化验收里不是“文档小瑕疵”，而是 **契约生成器本身不可信**。  
如果报告都做不到数量自洽，没人该相信它把 C1–C8a 做成了 fail-closed。

---

## 我关注的另一套维度（与 GPT/Opus 不同）

| 维度 | 问题 | 当前状态 |
|------|------|----------|
| **Search Space** | 任务生成、文件范围、重复修复是否被硬约束 | 半封闭 |
| **Token Freeze** | source/generated 是否在任何 phase 都写不进去 | 部分声称，未闭合 |
| **Host Reliability** | Session 断连、配额、超时后能否继续 6h | 几乎未证 |
| **Observation Integrity** | 测量与评分是否可伪造、可旁路 | 高风险 |
| **Rollback Atomicity** | Gate fail 后系统是否回到“可继续”的状态 | 未证 |
| **Budget Law** | 时间/Token/模型调用是否有不可突破的宪法 | 弱 |

GPT 更看运行链，Opus 更看契约强制。  
我这边更看：**这个系统会不会在无人值守时“有序地跑偏到一个很远的错误吸引子”。**

---

## P0 级发现

### G-P0-1：报告自洽性崩溃 → 任何“13/13”断言先作废

```yaml
claimed: 13/13 Critical Gaps Fixed
documented_in_body: GAP 1,2,3,4,5,6,7,8,9,12  # 10 items
missing_ids: GAP 10, 11, 13
```

**Grok 处理方式**：  
先把 status 改成：

```text
Status: 10/13 documented, 3 undocumented, code evidence missing
```

在补齐 GAP 10/11/13 或修正编号前，**禁止进入任何 overnight 路径**。  
这不是吹毛求疵——无人系统的第一原则是：**自己产出的声明必须可机读校验。**

---

### G-P0-2：Gate Chain 声称“完整”，但没有证明是“唯一 accept 入口”

报告写：

> GAP 2 … Full C1–C8a implementation with `control_plane_lock`  
> Impact: Complete gate-result envelope protocol

我真正要看的不是函数写了没，而是这两条不变量：

```python
# Invariant A: accept 的唯一合法来源
assert accepted_patch implies sourced_from(_run_gates)

# Invariant B: 失败默认拒绝
assert missing_gate or timeout or exception => REJECT + ROLLBACK
```

目前报告 **一个不变量都没给出可运行证明**。

风险形态（搜素空间爆炸的典型入口）：

1. tick 里某个模型直接产出 `accept: true`
2. 外部 resume 注入伪造 `gate_results.json`
3. C6/C7 失败却被当 warn
4. Gate 脚本缺失被 skip
5. worktree 未隔离，fail 后脏状态继续向后推进

**没有 worktree + atomic rollback + sole accept path，C1–C8a 只是装饰器。**

---

### G-P0-3：测量生产者缺口是“评分欺诈”温床

报告声称：

> Playwright-based … ScoringEngine computes **D1–D7** from real browser measurements

但 UIF-99 不是只有 bbox/color。至少有：

| 维度 | 需要的 producer | 报告证据 |
|------|-----------------|----------|
| D1–D5 layout/type/color/spacing/fx | Playwright computed style | 有文件名，无产物 |
| **D6 token alignment** | AST/usage vs declaration catalog | **完全没说** |
| **D7 interaction coverage** | assertion catalog + runner | **完全没说** |
| C6 visual | region-masked screenshot diff | 只在架构图出现 |
| C5 overlay | z-index/stacking/context harness | 只在架构图出现 |

更致命：

- 若 prototype 是**静态 PNG**，Playwright **无法**对 gold 直接取 computed style
- 若走 OCR/CV 推断，必须披露误差模型与失败阈值
- 若 prototype 其实是可运行 HTML，报告必须说清 build path

否则 ScoringEngine 可以：

1. 用假 measurement 抬分  
2. 用残缺 D6/D7 默认 1.0  
3. 用全局截图 diff 代替 region golden  

这会把 overnight 优化目标改成 **“骗过分数”**，而不是 **“还原 UI”**。

**搜索空间结论**：  
当前系统没有证明 observation 是 hard、不可伪造的。  
一旦 observation soft，任务生成器就会在错误目标上疯狂探索。

---

### G-P0-4：6h 宿主模型把“会话内调度”伪装成“无人值守”

架构图：

```text
Host: Claude Code Main Session (DeepSeek V4 Pro)
  ├── lx-goal
  └── ScheduleWakeup (6h overnight run)
```

这正是最危险的“看起来能跑一晚”的结构。

**真实故障树：**

| 事件 | 无 supervisor 时结果 |
|------|----------------------|
| IDE/浏览器 tab 挂起 | 主 session 死，timer 一起死 |
| WebSocket 断 | 可能失 tick，也无 resume |
| DeepSeek 配额打满 | 若无硬降级策略，整晚空转或崩 |
| 单次模型调用 8–15min | 60s “periodic checkpoint” 不发生 |
| Playwright 卡死 | 进程僵尸，无心跳 |
| 机器睡眠/锁屏 | 整条链停 |

报告对以下事项**全无证据**：

- 独立 supervisor / watchdog 进程  
- session 外 cron/systemd 拉起  
- 断点自动 resume 的 owner  
- 模型超时 kill + requeue  
- 配额耗尽时的 **flash/kimi 强制降级 + audit 预算保留**

**Grok 判定**：  
当前是 **supervised long loop**，不是 **6h unattended system**。  
把前者卖成后者，overnight 一定会在你不在时机上死。

---

## P1 级发现

### G-P1-1：`time.monotonic()` “全面替换” 可能制造可恢复性 bug

报告把“全改 monotonic”当优点，这对 **单进程 duration** 正确，对 **跨崩溃契约** 常常错误。

不可恢复模式：

```python
deadline = time.monotonic() + remaining
checkpoint["deadline_mono"] = deadline
# crash → new process rereads mono baseline → remaining 变成乱数
```

正确预算宪法应该是：

```yaml
budget_law:
  wall_deadline: UTC datetime          # 可持久化
  spent_compute: float seconds         # 可累加
  mono_phase_guard: only in-process    # 不可入库
```

若 restore 依赖 monotonic 绝对值，**一恢复就可能立即 STOP 或永不 STOP**。  
两者都比“多丢 1 分钟进度”更致命。

---

### G-P1-2：60s checkpoint ≠ 最多损失 1 分钟

只要存在阻塞调用（大模型 / tsc / Playwright / visual diff），checkpoint 周期就是**理论下界**，不是损失上界。

更合理的表达：

```text
checkpoint policy:
  - every phase boundary
  - before/after apply
  - before/after each gate
  - after accept/reject
  - heartbeat every 60s IF event loop alive
loss_bound:
  - best case ≤ 60s
  - realistic = longest uninterruptible op
```

报告把 “Impact: Maximum 1min work loss” 写死，说明 **对长尾阻塞没有模型**。  
无人系统必须先建立 **阻塞上限与可中断语义**，再谈损失边界。

---

### G-P1-3：Token 冻结仍像“策略”不像“物理边界”

报告提到：

> Grok G-P0-2 fix (POLISH excludes tokens/source)

好，这说明你们听到了关键点。但还不够。

我要的是 **所有 phase 的写权限矩阵是硬失败**：

```text
phase\path                 tokens/source  tokens/generated  proposals  components
DISCOVERY                  RO             RO                 RW         RO
TOKENS                     RO             RO                 RW         RO
SHELL                      RO             RO                 RO         RW(shell)
REGIONS/ELEMENTS/...       RO             RO                 RO         RW(scoped)
POLISH                     DENY           DENY               RO         RW(visual only)
FINAL_AUDIT                RO             RO                 RO         RO
```

并且：

1. C1 在 patch 解析后、apply 前强制  
2. 路径归一化后匹配（防 `../`、symlink、case tricks）  
3. 违规 **不能** 进 C2  
4. 审计日志必须留下 denied paths

目前只对 POLISH 做了口头保证，**TOKENS 会不会直接改 source** 未闭合。  
Token 一旦在 overnight 被“顺手统一”，后面所有视觉修复都建立在被污染的地基上。

---

### G-P1-4：搜索空间没有“负反馈硬顶”

报告有：

- phase-scoped file patterns  
- dedup  
- EMA convergence  
- model router budget guards  

但缺最关键的 **负空间控制**：

```yaml
must_have:
  max_tasks_per_region: int
  max_retries_per_failure_signature: int
  ban_list_after_N: hash(failure) -> cooldown
  no_improve_stop: EMA plateau + variance threshold
  forbidden_rewrite_patterns:
    - whole-file regenerate
    - redesign tokens mid-run
    - global CSS nuke
```

否则 overnight 典型失败是：

1. 同一 Header spacing 反复改 40 次  
2. 分数在 0.82–0.86 震荡  
3. 模型开始换布局哲学  
4. region 范围慢慢膨胀到整页  
5. 最后用“大重构”碰运气

**收敛器存在 ≠ 搜索空间有界。**  
有界搜索需要 **显式禁区 + 失败签名冷却 + 单区预算**。

---

### G-P1-5：Region 提取从 “空” 到 “能 parse” 只完成 30%

GAP 1 把 `_manifest_regions()` 从 empty 修到能读 `manifest.routes[].modules[]`。  
这解决“发现不了 region”，不解决：

- region 稳定性（DOM 变更后 selector 是否仍成立）  
- region mask 精度（screenshot diff 用不用 mask）  
- gold 对齐（prototype region ↔ implementation region 是否 1:1）  
- partial page（只修 Header 时其它 region 的噪声）

没有 region mask 的 “page-level visual score”，会让本地正确修改被全局噪声否决，或错误修改被全局平均放过。  
这是 UI 还原自动化里经典的 **信用分配失败**。

---

## 我会怎样重写验收门槛（Grok 版 Gate）

在看到代码前，先把 “是否允许试跑” 订成机检规则：

### A. 文档 Gate（现在已 fail）

```text
[ ] claim_count == documented_gap_count
[ ] every GAP has: problem / files / test / residual_risk
[ ] no “Impact: ...” without artifact or unit test pointer
```

### B. 边界 Gate

```text
[ ] phase_rules single source of truth
[ ] TOKENS cannot write source/generated
[ ] POLISH cannot touch tokens/**
[ ] C1 runs before apply, fail closed
[ ] path normalization + symlink reject
```

### C. 观察 Gate

```text
[ ] at least 1 real measurement JSON with D1–D7 fields
[ ] D6 has declared/used/coverage
[ ] D7 has assertion catalog results
[ ] prototype measurement method explicitly declared
[ ] C6 uses region masks, not only full-page
```

### D. 接受 Gate

```text
[ ] sole accept path = _run_gates
[ ] missing/timeout/exception => reject
[ ] atomic worktree apply + rollback demo log
[ ] forge gate_results attempt is rejected
```

### E. 宿主 Gate（6h 的真正门槛）

```text
[ ] process owner != chat session
[ ] watchdog can kill and resume
[ ] quota exhaustion has forced degrade path
[ ] wall-clock deadline survives restart
[ ] mono values never used as durable deadline
```

**当前 A/B/C/D/E 全部未过。**

---

## 对照报告声称的修复：我的再评分

| GAP | 报告自评 | Grok 再评分 | 理由 |
|-----|----------|-------------|------|
| 1 Region extract | Fixed | **Partial** | parse ≠ stable gold regions + masks |
| 2 Gate chain | Fixed | **Unverified/High risk** | 无 sole-path / fail-closed 证据 |
| 3 Measurement | Fixed | **Fail** | D6/D7 与 gold 来源未闭合 |
| 4 Time consistency | Fixed | **Likely regress** | 可能破坏跨进程 deadline |
| 5 Import org | Fixed | Pass (cosmetic) | 与无人运行无关 |
| 6 Line count | Fixed | Pass (local) | 有用，但不解决主风险 |
| 7 Convergence persist | Fixed | **Partial** | 序列化有了，时间/策略兼容未证 |
| 8 phase_rules | Fixed | **Partial** | POLISH 提到了，全相位矩阵未给出 |
| 9 Periodic ckpt | Fixed | **Overclaim** | 1min loss 不成立 |
| 12 Entry conditions | Fixed | Plausible | 需代码确认 |
| 10/11/13 | “Fixed” claim | **Missing** | 审计直接红灯 |

净结果：  
**真正可能站住的是局部工程卫生项；支撑 6h 无人 UI 还原的主脊柱仍未站立。**

---

## 与另两家视角的分歧点（明确写清）

### 相对 GPT（运行链）
我同意运行链未闭合；并额外强调：  
**即使链跑通，只要 observation 可被优化器玩弄，系统会“正确执行错误目标”。**

### 相对 Opus（契约强制）
我同意 fail-closed / 证据原子性；并额外强调：  
**宿主不可靠时，再完美契约也只是“有电才生效的法律”。**  
6h 的第一性原理是进程所有权，不是 phase 数量。

### Grok 特有否决项
1. 报告数量欺诈式不一致  
2. 搜索空间负反馈不足  
3. Token 边界未物理化  
4. Session 宿主冒充 unattended  
5. D6/D7 缺失导致 UIF-99 名存实亡  

---

## 最终裁决（Grok）

```yaml
identity: grok-4.5
review_mode: search_space + token_boundary + host_reliability
materials:
  report: partial
  orchestrator_py: 404
  artifacts: none

decision:
  production_overnight_6h: REJECT
  supervised_dry_run_30m: CONDITIONAL_ALLOW
  token_source_write: FORBIDDEN
  auto_phase_advance_past_TOKENS: FORBIDDEN

must_fix_before_any_unsupervised_run:
  - reconcile 13/13 vs documented 10 items
  - publish full phase write-permission matrix
  - prove sole accept path + atomic rollback
  - produce 1 real D1–D7 measurement artifact
  - separate host from chat session (watchdog/supervisor)
  - durable UTC budget law (no mono deadlines in checkpoints)
  - failure-signature cooldown + per-region task caps

if_only_one_thing_done_today:
  "Stop claiming 6h unattended. First make observation hard and host external."
```

---

## 你现在最该补给我的最小包（按优先级）

不要再补长报告。按这个顺序丢材料：

1. **`phase_rules.py` 全文**  
2. **`_run_gates()` + accept 调用点**（能证明唯一入口的片段即可）  
3. **1 份真实 `measurements/*.json`**（必须含 D6/D7 或明确标注 not implemented）  
4. **1 次 reject+rollback 日志**  
5. **checkpoint JSON 样例**（看 deadline 字段是 UTC 还是 mono）  
6. **GAP 10/11/13 原文** 或声明“编号作废，实为 10 项”

拿到 1–5 后，我可以直接给 **GO / NO-GO 终审**（仍会比 GPT/Opus 更苛刻地盯搜索空间和宿主）。

---

**结论再压一行：**

你们现在修的是 **workflow 拼图的可见缺口**；  
真正决定“能不能无人化高度还原 UI”的，是 **不可伪造的测量、不可越界的 token、不可被会话杀死的宿主、不可无限膨胀的搜索空间**。  

这四项里，报告只对第二项开了一个口子，其余三项基本还没进场。  

**所以：可以干 30 分钟受监督 dry-run，不可以进 6h overnight。**