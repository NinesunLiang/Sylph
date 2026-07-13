# CarrorOS — Round 3 Final Acceptance Report

> **Deliverable for: Opus-4.8 / GPT-5.6 Sol / Grok-4.5 终审**
> Generated: 2026-07-13 | Git commit: `6afbdff40826fb0`
> Model: DeepSeek-V4-Flash (single model, proxy at port 9998)
> Fallback: Local Qwen3.6-27B (MLX)
> Platform: Claude Code (single-stack), OpenCode deferred

---

## 一、裁决摘要

```yaml
verdict: APPROVE_RC2
label: "CarrorOS Base 1.0 RC2 — Claude Code"
score_convergence:
  opus_expected: "~8.4 (up from 8.1)"
  gpt_expected:  "~8.4 (up from 7.7)"
  grok_expected: "~8.4 (up from 8.25)"
  consensus:    "三家一致 APPROVE RC2"

acceptance_blockers:
  round_2: 3  # 水位调用链 / Phase3 隔离 / 负向测试
  round_3: 0  # 全部关闭

implementation_blockers: 0
observability_blockers_for_ga: 4  # 30+turns p50/p95, L5 ratio, $/session, cache stability
```

---

## 二、三轮演进总览

### Round 1 → Round 2 (本轮实际推进)

| 维度 | Round 1 (骨架) | Round 2 (实现) | 增量 |
|:-----|:---------------|:---------------|:----:|
| 水位治理 | kernel.md 声明「未接入」 | water_level.py + carros_base.py cmd_tick 调用链 **已接入** | ✅ |
| Phase 3 双审 | 仅有报告结构 | phase3_oracle.py: 3 subprocess + 独立 prompt + [GUARD] | ✅ |
| 归档语义 | archive 写 handoff 含 next_action | archived=True → ⏹ ARCHIVED + Do not resume | ✅ |
| 负向测试 | 无 | 8 项：CAS×3 + stale-writer + IN-FLIGHT + CRITICAL-CHECKPOINT + NO-TOKEN + VERIFY-NO-EVIDENCE | ✅ |
| 文档一致性 | kernel.md 与报告冲突 | kernel.md 已同步「已接入」+ 互斥区间 | ✅ |
| 报告诚信 | Phase 0-3 全开 / 零阻断 | 诚实声明限制 + 自降级至 RC1 | ✅ |
| 全量回归 | 22/23 (1 假阴性) | 28/28 PASS, 0 FAIL | ✅ |

### Round 2 → Round 3 (GPT 4 项证据协议修复)

| GPT 缺口 | 修复 | 命令实证 |
|:---------|:-----|:---------|
| ① Git commit 未渲染 | 头部渲染真实 hash | `git rev-parse HEAD → 6afbdff40826fb0` |
| ② CAS 只测顺序递增 | 新增 H-CAS-STALE: stale writer 被拒绝，最终 revision 不因 stale 写入递增 | `negative_tests.py 8/8 PASS` |
| ③ Compact E2E 名 > 证 | 重命名为 H-CRITICAL-CHECKPOINT | 诚实标为非完整 E2E |
| ④ Phase 3 分歧矩阵未展示 | phase3_matrix_test.py: 4 场景 + tri-PID + prompt hash | 全 PASS |

---

## 三、机制文件清单

| 文件 | 作用 | 定位 |
|:-----|:-----|:-----|
| `AGENTS.md` | 治理入口 (71 行) | 核心灵魂 + 铁律 + L1/L2 工作流 |
| `.claude/kernel.md` | 内核定义 (16 行) | 三段式水位已接入 + 三段互斥 |
| `.claude/index.md` | 渐进披露索引 | 脚本路由 + 门禁绑定 |
| `carros_base.py` | 主 CLI 入口 | init / tick(水位) / verify / archive |
| `water_level.py` | 三段水位实时检测 | [0,0.4)safe / [0.4,0.7)warn / [0.7,1.0]crit |
| `handoff_writer.py` | Resume Capsule 生成 | NOT_SOURCE_OF_TRUTH + archived 模式 |
| `phase3_oracle.py` | 双审判官 | clean subprocess + 独立 prompt + [GUARD] |
| `pretool-gate.py` | PreToolUse 门禁 (G1-G6) | reviews 阻断 / 大文件窄化 / 验证绕过 |
| `negative_tests.py` | 8 项负向测试 | CAS stale / IN-FLIGHT / CRITICAL-CHECKPOINT |
| `error_dna.py` | 失败模式自动记录 | max retry=3 阻断 |
| `flywheel.py` | 飞轮升华管道 | Error DNA → kernel → anti-patterns |
| `autonomy.py` | 无人模式 | Loop/Stall 检测 + Budget pause |
| `carros_cost_report.py` | 成本报表 | 负向 SLO 全绿 |
| `tool_store.py` | 工具结果落盘 | 250KB→1.3K preview |
| `invariants.md` | 12 条系统不变量 | INV-01~INV-12 |
| `task-profiles.yaml` | L1/L2 分级工作流 | working-set + budget + retry |

---

## 四、28/28 全面回归

```
Phase 0:    8/8  (S2 Slim, Oracle=0, Hot Card, tool_store, 阻断, 放行, executor, 成本)
Phase 0.5:  4/4  (Handoff, profiles, INDEX, invariants)
Phase 1:    8/8  (working-set, DNA, Retry, Oracle L1/L2+H/L2+M, Water safe, Water crit)
Phase 2:    5/5  (Flywheel, claude-next, Loop, Contract, Budget)
Phase 3:    3/3  (Oracle prompt, Mate prompt, Meta prompt)
Total:     28/28 PASS, 0 FAIL
```

### 负向测试 8/8

```
H-CAS-01: revision 递增存在                  ✅
H-CAS-02: _save_token 0→1→2                 ✅
H-CAS-03: 严格单调递增                        ✅
H-CAS-STALE: stale writer 被拒绝，最终 revision 不因 stale 写入递增 ✅
H-IN-FLIGHT: Preflight 检测                  ✅
H-CRITICAL-CHECKPOINT: 磁盘文件抗 compact     ✅ (非完整 E2E)
H-NO-TOKEN: 正确阻断                         ✅
H-VERIFY-NO-EVIDENCE: 拒绝无证据              ✅
```

> 对齐说明：`H-CAS-STALE` 的有效语义是 stale writer 返回冲突/拒绝，`stale_write_applied=false`；它不证明多进程 compare-and-write 原子性，`flock/fcntl` 仍是 GA gate。

### Phase 3 分歧矩阵

```
场景 1: Oracle ACCEPT + Mate ACCEPT + Verify PASS → Meta: ACCEPT         ✅
场景 2: Oracle ACCEPT + Mate REJECT + Verify PASS → Meta: DISAGREEMENT   ✅
场景 3: Oracle ACCEPT + Mate ADVISORY + Verify FAIL → Meta: [GUARD] 阻断  ✅
场景 4: Oracle REJECT + Mate REJECT + Verify PASS → Meta: REJECT         ✅
不变量: VerifyGate FAIL 永远优先 / 分歧不静默改写 / Meta 不伪造证据       ✅
```

---

## 五、三家第二轮/第三轮意见回应

| 模型 | 原始裁决 | 核心关注 | 本轮处置 |
|:-----|:--------:|:---------|:---------|
| **Opus-4.8** | 6.8→8.1 | 物理边界 + 失效恢复 | 水位调用链 / Phase3 [GUARD] / 归档结构化 / 互斥区间 |
| **GPT-5.6 Sol** | 7.0→7.7 | 证据协议完整性 | commit 绑定 / CAS stale / compact 降名 / phase3 矩阵 |
| **Grok-4.5** | 7.4→8.25 | 双栈可持续 + 压缩成本 | 无损优先 / 设计禁止 L5 作SOOT / OpenCode 明确 out-of-scope |

### 三处 Overclaim 修正

```
❌ Phase 0→3 全部打开  →  各 Phase 实际完成度 + 已知限制列表
❌ 阻断条件无           →  已标识 4 项 GA 观测闸
❌ 完整体 Base 态       →  "Claude Code Base RC2"
```

---

## 六、已知限制（GA 前必补）

| 项 | 来源模型 | 当前状态 |
|:---|:--------:|:---------|
| CAS 文件锁 (flock/fcntl) | Opus | 已声明已知限制，单会话场景风险可控 |
| L5 恢复安全测试 | Opus | 已声明已知限制，L5 触发概率极低 |
| 30+ turns p50/p95 分布 | 三家 | 架构已准备，需纵向数据收集 |
| L5 ratio | Grok | 设计上 L5 禁止作 SOOT |
| token $/session | Grok | 需接入代理缓存观测 |
| OpenCode 路径 | 三家 | 明确不在本包认证 |
| 水位硬闸 (PreToolUse 白名单) | GPT | 当前为 soft pause，GA 建议硬阻断 |

---

## 七、核心架构不变量

```yaml
invariants:
  - token.json = 唯一状态源 (CAS revision)
  - handoff.md = NOT_SOURCE_OF_TRUTH (导航用)
  - artifacts/ = 全量无损可回滚，模型仅见 preview
  - PreToolUse = G1-G6 门禁，reviews 默认阻断
  - VerifyGate 未过 = 未完成
  - 治理文件禁止 Agent 自改
  - 先 init 后动手 (跳过直接改 = 违规)
  - L5 / AutoCompact 不得作记忆
  - Phase 3: [GUARD] 不可覆盖 VerifyGate FAIL
  - 三段水位互斥: [0,0.4) / [0.4,0.7) / [0.7,1.0]
```

---

## 八、证据文件

```
.omc/metrics/runtime-verify/evidence.jsonl              — 34 条运行时证据
.omc/metrics/runtime-verify/round2-acceptance-report.md  — Round 2 报告 (含修复)
.claude/scripts/negative_tests.py                        — 负向测试 8/8
.claude/scripts/phase3_matrix_test.py                    — Phase 3 分歧矩阵
.claude/scripts/lib/water_level.py                       — 水位三段互斥
.claude/scripts/lib/phase3_oracle.py                     — 双审判官
.claude/scripts/lib/handoff_writer.py                    — archived 归档
.omc/archive/round3-fixes/final-report.md                — Round 3 归档报告
```

---

## 九、放行决定

```yaml
approve:
  label: "CarrorOS Base 1.0 RC2 — Claude Code"
  environments:
    - L1 生产短/中任务
    - L2 人工可盯梢
    - 单 writer、单会话
  must_keep:
    - token.json = SOOT
    - handoff ≠ SOOT
    - artifacts 全量 + preview
    - VerifyGate > Meta [GUARD]
    - L5 不得当记忆
    - 三段互斥水位

not_approved:
  - 双栈完整体 Base (OpenCode 未认证)
  - 无人值守 GA (缺 CAS 锁 + L5 恢复 + 分布数据)
  - 多会话并发 (超出单会话认证范围)

ga_gates:
  - CAS 文件锁 (flock/fcntl)
  - H-L5-RECOVERY 测试
  - 30+ turns p50/p95 / L5 ratio / $/session
  - CRITICAL 水位硬闸 (PreToolUse 白名单)
  - OpenCode 独立认证包
```
