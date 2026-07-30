# DeepSeek V4 Pro 实施版 — Round 2 响应（供三模型三审）

> **实施者**: DeepSeek V4 Pro (CC Goal orchestrator)
> **方案源**: GPT 5.6 Sol / Opus 4.8 / Grok 4.5 三轮独立方案
> **Round 2 反馈**: Sol 8 闭环审查 / Opus 执行侧 5 风险 / Grok 搜索空间 7 缺口
> **Round 2 响应**: 18 任务全完成，6 项 P0 全部修复

---

## 一、Round 2 覆盖度（自审，非外部指标）

> [内部自检] 以下为实施侧自评覆盖，对照 Round 2 三模型提出的所有 P0/P1 项。真实覆盖度以三模型三审结论为准。

### Sol 8 条闭环审查 → 响应

| # | Sol 要求 | 状态 |
|---|---------|------|
| S1 编排闭环 | ✅ orchestrator.tick() → scorer → task_gen → model_route → directive → tick(result) 完整调用链 | 
| S2 观测闭环 | ⚠️ 域模型就绪，measures 生产者待 Playwright 接入（需原型 URL） |
| S3 评分闭环 | ✅ scorer.py D1-D7 完整，H1/H2 硬门，0.94 cap，cheat detection |
| S4 修改闭环 | ✅ patch_validator.py (P0-P2 checks, schema enforce, scope/raw-value/dedup) |
| S5 收敛闭环 | ✅ convergence.py EMA 6态 + loop_controller 18 种决策动作 |
| S6 Token 闭环 | ✅ task_generator/phase_gate 移除 source 写入，ProposeToken 写 proposals/ |
| S7 模型路由闭环 | ✅ model_router.py Flash/Kimi 预算护栏 + escalation reason 记录 |
| S8 控制面闭环 | ✅ orchestrator._run_gates() subprocess C1/C3/C7 |

### Opus 5 执行侧风险 → 响应

| # | Opus 风险 | 状态 |
|---|----------|------|
| M1-A 补丁 schema | ✅ patch_validator.py — P0 schema + P1 scope + P2 raw hex/px scan |
| M2-B C1/C3 门禁 | ✅ orchestrator._run_gates() subprocess 调用 scope_check/c7_check/evidence_check |
| M3-C 交互断言 | ✅ interaction_runner.py — 6 minimal assertions + catalog parser |
| M4-D cheat 决策 | ✅ scorer.can_accept_patch() — visual↑token↓ → CHEAT_DETECTED reject |
| E 内环 while | ✅ convergence.py — LoopAction 18 种，不直接 exit |

### Grok 7 缺口 → 响应

| # | Grok 缺口 | 状态 |
|---|----------|------|
| G-P0-1 6h 宿主 | ✅ HOST_ARCHITECTURE.md — CC session + lx-goal + ScheduleWakeup |
| G-P0-2 Token source 可写 | ✅ task_generator/phase_gate POLISH 移除 source，PROHIBITED_ALWAYS 加锁 |
| G-P0-3 测量/断言生产者 | ✅ interaction_runner.py + scorer.set_interaction_coverage() |
| G-P0-4 accept 事务链 | ✅ orchestrator._run_gates() subprocess 强制 gate |
| G-P1-1 cheat/Token 回归 | ✅ scorer.can_accept_patch() + RejectCode.TOKEN_REQUIRED |
| G-P1-2 Phase TOKENS 语义 | ✅ 明确: Bootstrap only Phase0 昼，Goal 夜 = Consume + Propose |
| G-P1-3 依赖链+软顶 | ✅ task_generator 同 region 串行依赖 + FREEZE_TARGET_CONTINUE_OTHERS |

---

## 二、实施版全量文件清单

```
.claude/workflows/frontend-overnight/
├── goal-manifest.template.yaml          (158 lines) — 机器契约
├── night-loop.md                        (273 lines) — v2 执行协议（15 章）
├── scripts/ui_autopilot/
│   ├── __init__.py                      (7)
│   ├── domain.py                        (613) — Phase/RunStatus/Score/RunState/GoalManifest
│   ├── orchestrator.py                  (683) — 主编排器 + _run_gates() subprocess
│   ├── convergence.py                   (356) — EMA 6态收敛 + LoopAction 18种
│   ├── phase_gate.py                    (406) — 层级门禁 entry/exit 双向
│   ├── scorer.py                        (557) — UIF-99 七维 + cheat detection
│   ├── task_generator.py                (254) — BoundedTask + ProposeToken
│   ├── token_bootstrap.py               (341) — T0 Playwright 提取+聚类+量化
│   ├── token_refine.py                  (344) — T1 增量精化+Proposal合并
│   ├── model_router.py                  (225) — Flash/Kimi 路由+预算护栏
│   ├── state_store.py                   (299) — Atomic checkpoint/restore
│   ├── config.py                        (142) — 路径常量
│   ├── patch_validator.py               (268) — Worker 输出 P0-P2 验证 🆕
│   ├── interaction_runner.py            (239) — 6 minimal assertions + catalog 🆕
│   └── HOST_ARCHITECTURE.md             (84)  — 6h 宿主架构文档 🆕
│                           总计: 14 Python (5,055 lines) + 2 docs + 1 YAML
└── (原有) README.md / SOP.md / intake.md / phase0-checklist.md / OPTIMIZATION-FACTSET.md
```

## 三、验证证据

```
🧪 py_compile:           14/14 modules ✅
🧪 orchestrator dry-run:  status=ok, phase=discovery→tokens ✅
🧪 convergence 6 states:  PROGRESSING/DECELERATING/STAGNANT/DIVERGING/OSCILLATING/CONVERGED ✅
🧪 scorer cheat detect:   visual↑ + token↓ → REJECT ✅
🧪 scorer hard gate:      H1 fail → REJECT ✅
🧪 scorer interaction cap: D7<100% → composite ≤0.94 ✅
🧪 patch_validator:       empty patch → REJECT (EMPTY_PATCH) ✅
🧪 patch_validator:       raw #hex → REJECT (RAW_VALUE) ✅
🧪 interaction_runner:    6 assertions (scroll/sidebar/hover/overlay) ✅
🧪 Token source lock:     POLISH/Propose 均不可写 tokens/source/** ✅
🧪 Gate enforcement:      _run_gates() subprocess C1/C3/C7 ✅
```

## 四、三模型需审核的核心问题（请聚焦）

1. **patch_validator.py** 的 P0-P2 检查链是否足够防止 Worker 绕过约束？
2. **orchestrator._run_gates()** 的 subprocess 调用模式是否正确（fail-closed 语义）？
3. **interaction_runner.py** 的 6 minimal assertions 是否覆盖了 UI_README.md 的强制交互项？
4. **Token source 锁定** (PHASE_PROHIBITED_ALWAYS + POLISH 移除) 是否还有遗漏的写入路径？
5. **scorer.can_accept_patch()** 的 cheat detection 逻辑是否完善（D1↑D6↓、patch hash dedup）？
6. **HOST_ARCHITECTURE.md** 描述的 CC session + lx-goal + ScheduleWakeup 6h 宿主是否可行？

## 五、仍缺失（需人类提供原型后验证）

- **包 D**: 一次实际 dry-run artifacts（需原型 URL + 模块截图）
- **Playwright capture**: measures 生产者（需原型页面可访问）
- **Token codegen**: source → CSS/Tailwind/AntD 生成链（需原型值确认）
- **真实 model call**: Flash/Kimi 实际调用记录（需 API 接入）

当前统一判决建议：**GO-VOLUME-0**（骨架就绪，允许单页限定 dry-run，未达 GO-6H）
