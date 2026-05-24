# Carror OS — Pre-Launch Refinement Plan

**目标发布日**: 2026-06-01  
**当前状态**: v1.0 — 喂狗粮 + 优化阶段 (2026-05 ~ 2026-06)  
**目标评分**: 9.5/10 (发布前), 断档领先

---

## 背景

Carror OS OMA (On My Command) 是一套 AI Agent 治理体系，包含三个核心模块：

| 模块 | 职责 | 当前状态 |
|------|------|----------|
| lx-oma-gov (governance) | 文档治理 — PRD 变更同步到 sub-PRD、sub-PRD 回写 feature | ✅ 规范完备，基础设施缺 |
| lx-oma-orch (orchestrator) | Pipeline 编排 — 阶段推进调度 (plan→exec→verify) | ⚠️ Schema v1.0 已创建，未验证 |
| Hooks 防护层 | Context Guard, Privacy Gate, Edit Guard, Subagent Guard 等 8 gates | ✅ 生产级，27+ 次触发验证 |

**当前综合评分: 8/10** — 防御层到位，治理有规范，执行层在补。

---

## P0 — 发布前必须完成的三件事

### 1. Pipeline Orchestrator 跑通 (v0 → v1)

**目标**: pipeline.yaml 从"schema"变成"实际运行的编排引擎"。

#### 验收标准
- [ ] `lx-oma-orch status` 能读取 pipeline.yaml 输出当前阶段
- [ ] `lx-oma-orch advance <stage>` 能推进到下一阶段并写验证证据
- [ ] `lx-oma-orch gate <stage>` 能触发 gate check（软/硬）
- [ ] `lx-oma-orch dev` 能在开发阶段跳过 gate（人工授权）

#### 实现要点
- pipeline.yaml 已有 v1.0 schema (2,482 bytes)，但 `features/`, `snapshots/master/` 目录为空
- 需要实现 `reconcile()` / `propagate()` — gov 模块调用的核心函数
- **the less the more**: 先实现 `status` + `advance`，gate/dev/run 后续迭代

#### 里程碑
- M1: pipeline.yaml schema v2 (stages + current_stage + tasks) — 5月10日
- M2: `status` / `advance` CLI 命令实现 — 5月17日
- M3: gate check + dev override — 5月24日

---

### 2. Human-in-the-Loop Gate (L3 裁决)

**目标**: governance-spec.md 里规划的 `awaiting_human_decision` 状态机真正落地。

#### 验收标准
- [ ] 检测到 L3 冲突 → 进入 `awaiting_human_decision` 状态
- [ ] Owner 执行裁决命令（approve/reject/modify）
- [ ] 决策写入 CONSOLIDATION-LOG.md (Entry status = awaiting_human → approved/rejected)
- [ ] human-acceptance-checklist 能跑完一轮完整流程

#### 实现要点
- governance-spec.md 第 2 节已定义 `awaiting_human_decision` 状态机（Oracle 评审 v1 patch 已接受）
- human-acceptance-checklist-20260505.md 已有 52/52 验证项（hooks 生产级验收）
- **关键缺口**: 没有"从检测到冲突到人工裁决"的自动化路径

#### 里程碑
- M1: L3 检测 + awaiting_human_decision 状态写入 — 5月12日
- M2: human-acceptance-checklist 自动化 runner — 5月19日
- M3: CONSOLIDATION-LOG.md 自动更新 — 5月26日

---

### 3. 运行数据收集与可视化 (Flywheel)

**目标**: hooks 拦截统计、context-guard 触发次数 — 用数据证明 OMA 的价值。

#### 验收标准
- [ ] `~/.claude/flywheel.log` 记录 hooks 拦截事件（context-guard, privacy-gate, edit-guard）
- [ ] `.omc/state/error-dna.jsonl` 能按签名聚合（去重后统计真实错误类型）
- [ ] 每周生成一份 "OMA Shield Report"（拦截次数、top error types）

#### 实现要点
- flywheel.log 已有部分记录（context_guard_triggered, subagent_high_usage）
- error-dna.jsonl 有 256KB / 100+ 条，但 stop-drain.sh timestamp=0 无法追溯 session
- **关键缺口**: context-guard 阻断被 hook error handler 吞掉，没落盘到 flywheel.log
- **context-monitor.py fallback**: token-tracking-index.json 不存在，context-guard 在"盲测"

#### 里程碑
- M1: flywheel.log → weekly report generator — 5月12日
- M2: error-dna.jsonl 签名聚合 + session 追溯 — 5月19日
- M3: token-tracking-index.json 自动初始化 + context-monitor.py fallback — 5月26日

---

## P1 — 优化项（发布前争取完成）

### 4. Context Guard: Read/Grep/Write 同等阻断

**问题**: context-guard.sh R29 设计 (Edit/Write 阻断, Read/Grep/Bash 放行)。  
上下文爆炸时，读操作也在加速死亡。

**优化**: 高阈值 (≥95%) 时，Read/Grep/Bash 也阻断。低阈值 (80-95%) 时，仅 Edit/Write 阻断 + additionalContext。

**收益**: 防止上下文爆炸恶性循环（读 → 更满 → 更危险）

---

### 5. Edit Guard: Read-before-Edit 流程优化

**问题**: error-dna.jsonl 中大量 "File has not been read yet" — AI 跳过 Read 直接 Write。

**优化**: 
- PreToolUse:Edit → EditGuard.sh 检查 read-tracker.txt
- 如果未 Read → exit 2 + additionalContext "请先读取文件"
- read-tracker.txt 在 Read/Grep 后自动更新

**收益**: 减少"未读即写"错误，提升 edit-guard 实际拦截率

---

### 6. Governance 基础设施: features/ + snapshots/master/

**问题**: governance-spec.md 引用了 `features/`, `snapshots/master/` 等路径，实际不存在。  
reconcile() / propagate() 无基础设施。

**优化**:
- `mkdir -p features/ snapshots/master/`
- reconcile() 实现: diff PRD → apply to sub-PRDs
- propagate() 实现: sub-PRD 变更回写 feature PRD

**收益**: gov 从"规范"变成"可执行"

---

### 7. Stop-Drain.sh Timestamp Fix

**问题**: stop-drain.sh 捕获的错误 timestamp=0，无法追溯 session。  
session_id 在 error-dna.jsonl 中全是 `38603363-b3e7-4779-ab87-33ef171c4b27` (同一 session)。

**优化**:
- stop-drain.sh 从 transcript.jsonl 提取真实 session_id
- error-dna.jsonl entry 增加 `session_start` / `session_end`

**收益**: error-dna.jsonl 从"盲记"变成"可追溯"

---

### 8. Hook Audit: settings.json vs .codex/hooks.json 统一

**问题**: hooks 系统三套配置并存
- `.claude/settings.json` (Claude Code hooks — 30个)
- `.codex/hooks.json` (跨平台 Codex/OpenCode/Qwen Code — 19个)
- `.claude/harness.yaml` (启用/禁用控制)

**优化**: 
- 明确 .codex/hooks.json → Codex/OpenCode
- 明确 settings.json + harness.yaml → Claude Code (当前)
- CLAUDE.md hooks_and_context 只引用 settings.json

**收益**: 消除"配置三套、容易混乱"的 P4-1 问题

---

## P2 — 发布后迭代项

### 9. Subagent Guard: DEFAULT_MAX_TURNS=20 → exit 1 (警告)

**问题**: AI 不写 max_turns 走 DEFAULT_MAX_TURNS=20 → **放行**，"阻断"形同虚设。

### 10. Current-Scope.txt: edit-guard.sh 越界检测修复

**问题**: current-scope.txt 不存在 → edit-guard.sh (pretool-edit-scope) 的越界检测失效。

### 11. Verify-OMA-Interface-Coverage: sub-prds 覆盖不完整

**问题**: verify_oma_interface_coverage.py run exit code 1 — sub-prds/domain-*.md 孤立。

### 12. Pipeline.yaml: deprecated tasks cleanup

**问题**: pipeline.yaml 中有 `carror-os-productization`、`feat-alert-crud`、`race-enhancement` 等 tasks，但 features/ 目录为空。

---

## 评分预测 (2026-06-01)

| 模块 | 现在 | P0完成后 (M3) |
|------|------|---------------|
| Hooks 代码质量 | 9/10 | 9/10 (已成熟) |
| lx-oma-gov 规范 | 7/10 → **9.5/10** (reconcile/propagate 可执行) |
| lx-oma-orch | 4/10 → **9/10** (pipeline.yaml 跑通) |
| 实际运行质量 | 7.5/10 → **9/10** (有数据背书) |
| **综合** | **8/10** → **9.5/10** 🚀 |

---

## 发布策略 (2026-06-01)

### Before Launch
- [ ] 三件事全部完成 (M3 milestone)
- [ ] run one full cycle: research → plan → execute → verify → review
- [ ] collect 30 days of flywheel.log data

### Launch Announcement
**标题**: "Carror OS: AI Agent Governance, Engineered"

**核心信息**:
1. **不是又一个 agent framework — 是治理体系** (gov + orch + hooks)
2. **8 gates 已拦截 X,XXX 次错误操作** (flywheel.log data)
3. **context-guard 保护了 Y,YYY token 的上下文爆炸** (data)
4. **human-in-the-loop gate — 人工验收闭环** (awaiting_human_decision)

### Promotion Channels
1. **GitHub** — open source, docs + examples
2. **Reddit / HN** — "How I built an AI agent governance system" (story-driven)
3. **Twitter/X** — hook screenshots, flywheel data visualization
4. **AI Dev communities** — Claude Code plugin ecosystem

---

*文档由 Hermes Agent 自动维护，随项目迭代更新。*
*最后更新: 2026-05-09*

---

## Audit Review — Hermes Agent 审计结论 (2026-05-09)

> **来源**: Agent 对 RELEASE-PLAN.md + HUMAN-IN-THE-LOOP-GATE.md 的独立审计  
> **目的**: 找出文档中的虚假信心、逻辑漏洞、优先级错误，确保 Boss 在同步前能看到不同视角

---

### 🔴 结论 1: 当前综合评分应改为 7/10 (不是 8)

**问题**: lx-oma-gov 和 lx-oma-orch 当前状态是"规范完备但无实现代码"。  
governance-spec.md 有 561 行、HUMAN-IN-THE-LOOP-GATE.md 有完整状态机定义，但 `reconcile()` / `propagate()` CLI 命令不存在。

**虚假信心**: "当前综合评分: 8/10" 给了用户错误预期。  
真实情况是防御层 (hooks) 有 7/10，治理层 (gov/orch) 只有 3-4/10（纸面规范）。

**修正**: 
```
当前综合评分: 7/10 — 防御层到位 (8-9)，治理有规范但无实现 (3-4)
```

---

### 🔴 结论 2: P0 三件事优先级应重新排序

**当前顺序**: 
1. Pipeline Orchestrator (最重)
2. Human-in-the-Loop Gate (中等)
3. Flywheel (最轻)

**我的判断 — 应改为**:
1. **Flywheel → P0-1 (5月12日 M1)** — 最快，2天内可出。已有 flywheel.log + error-dna.jsonl，只需整理成可读格式
2. **Human-in-the-Loop Gate → ~~P0-2~~ P1 v6.3 (5月26日 M3)** — 降级：不影响 MVP 双平台可用性目标，推迟至 v6.3 迭代
3. **Pipeline Orchestrator → P0-3 (5月24日 M3)** — 最重，需要 CLI + state machine

**理由**: 
- Flywheel 是其他两件事的"证据源" — 没有数据，gov/orch 的优化就是纸上谈兵
- Flywheel M3 (5月26日) 可以和其他两件事同时完成，但它的 M1/M2 (5月12日/19日) 必须先做
- "the less the more" 原则：Flywheel 先出数据 → 用数据驱动 gov/orch 的优化

---

### 🔴 结论 3: P1-5 Edit Guard "未读即写"硬阻断有技术争议

**当前方案**: 
```
PreToolUse:Edit → EditGuard.sh 检查 read-tracker.txt
如果未 Read → exit 2 + additionalContext "请先读取文件"
```

**问题**: 这会导致 AI **"卡死"**。  
AI 想 Write 一个刚创建的文件（Read 它不存在），被阻断说"请先 Read"，但它不知道要 Read 哪个文件。

**更好的方案**: 
```
PreToolUse:Edit → EditGuard.sh 检查 read-tracker.txt  
如果未 Read → exit 0 + additionalContext "检测到 Write 操作，建议先 Read" (软提示)
```

**理由**: 
- AI 有时确实需要 Write 一个刚创建的文件（Read 它不存在）
- 硬阻断 (exit 2) = AI 必须重试，但重试时可能 Write 同一个文件 → 无限循环
- 软提示 (exit 0 + additionalContext) = AI 收到建议，可以选择是否遵守
- "软提示" 在无人值守模式下更安全 — 不会阻塞 AI，但会留下证据

---

### 🔴 结论 4: "发布策略" 部分过于营销化，应分离

**问题**: 
- "AI Agent Governance, Engineered" — marketing copy
- "8 gates 已拦截 X,XXX 次错误操作" — 需要数据，但当前 flywheel.log 不完整
- "context-guard 保护了 Y,YYY token" — 同上

**建议**: 
- RELEASE-PLAN.md → 纯技术文档，去掉营销内容
- LAUNCH-COPY.md (新文件) → marketing copy, release notes, promotion channels

---

### 🔴 结论 5: lx-oma-gov vs lx-oma-orch 的区别在文档中没有体现

**Boss 之前问过这个问题，但 RELEASE-PLAN.md 里没有回答。**

| 维度 | lx-oma-gov (governance) | lx-oma-orch (orchestrator) |
|------|------------------------|---------------------------|
| **职责** | PRD 文档治理 — reconcile/propagate | Pipeline 编排 — advance/gate |
| **核心命令** | init, ingest, reconcile, propagate, resolve, status | status, advance, gate, run, dev list/mark |
| **状态机** | need_input → reconciling → awaiting_human_decision → done | idle → checking_oracle_gate → calling_skill → update_pipeline → done |
| **依赖** | 独立（不依赖 orch） | 调用 gov.reconcile 作为子 skill |
| **触发方式** | keyword triggers: `/lx-oma-gov`, `reconcile`, `漂移检测` | keyword triggers: `/lx-oma-orch`, `pipeline`, `管线状态` |
| **当前实现** | 规范完备 (561行 spec)，无 CLI 命令 | Schema v1.0 (pipeline.yaml), 无 CLI 命令 |

**关系**: orch → gov.reconcile。orch 是上层调度器，gov 是下层执行者。

---

### 🔴 结论 6: "无人值守 Self-healing" 概念缺失

**Boss 刚才提出的关键问题**: 
> "无人值守模式时，真正做到无人、自助发现问题记录问题、解决问题，解决不了的换方式最多三次。还解决不了文档记录下来跳过。"

**RELEASE-PLAN.md 完全没有覆盖这个场景。**

**建议新增 P0.5**:
```markdown
### 13. Self-healing for Unattended Mode (P0.5)

**目标**: 无人值守时，系统自动发现问题 → 尝试修复（3次）→ 解决不了记录并跳过。

#### 三条规则:
1. **发现问题**: hook error handler → 自动归类到 flywheel.log + error-dna.jsonl
2. **尝试修复**: retry 最多 3 次（同一错误类型），每次换不同策略
   - attempt 1: retry original command
   - attempt 2: with additional context (read file first)  
   - attempt 3: alternative approach (different tool/path)
3. **记录并跳过**: 3次都失败 → 写入 `.omc/state/skipped-errors.md`，标记 `reason: self-healing exhausted (3/3)`

#### 无人值守触发条件:
- `unattended_mode=true` (环境变量或配置文件)
- 没有用户交互（no human-in-the-loop）
- hooks 自动执行，不阻塞 AI 主流程

#### 验收标准:
- [ ] error-dna.jsonl entry 有 attempt_count / last_attempt_reason
- [ ] skipped-errors.md 有自动写入的失败记录
- [ ] flywheel.log 能统计 "self-healing success rate"
```

---

### 🔴 结论 7: 文档中缺少 "交互体验" 审计

**问题**: RELEASE-PLAN.md 关注的是功能实现，但 Boss 问的 "交互是否都是 Agentic UI" 没有被回答。

**当前 hook 触发情况**:
- **PreToolUse hooks (9个)**: context-guard, edit-guard, privacy-gate, permission-gate 等 — **自动触发** ✅
- **PostToolUse hooks (12个)**: auto-snapshot, error-dna, build-validator 等 — **自动触发** ✅
- **SessionStart hooks (3个)**: inject-project-knowledge, flywheel-report — **自动触发** ✅
- **Skill triggers**: `/lx-oma-gov`, `reconcile` 等 — **需要用户输入** ❌
- **CLI commands**: `lx-oma-gov resolve`, `lx-oma-orch advance` — **需要用户输入** ❌

**问题**: 
1. Hooks 是 Agentic UI (自动触发) ✅
2. 但 gov/orch CLI 命令需要用户手动输入 `/lx-oma-gov reconcile` ❌
3. L3 冲突的 `resolve CONFLICT-ID accept/reject` 需要用户手动输入 ❌
4. propagate --execute (实际写入) 在 MVP 中是 "推迟到 v2" ❌

**结论**: "AI Agent Governance, Engineered" 的 claim 是成立的，但"Agentic UI"的程度被高估了。  
**真实情况**: 80% hooks 是自动的，20% CLI/gov/orch 需要用户手动输入。

**改进建议**: 
- L3 resolve → 自动尝试 accept/reject (基于风险评估)，只有高置信度冲突才 require human
- propagate → 自动 dry-run，用户只需 approve/reject (不需要手动输入 CHG-ID)

---

### 🟡 结论 8: P1-4 Stop-Drain.sh timestamp fix — 优先级争议

**当前**: P1-7 (中等优先级)  
**我的判断**: 应该升为 P0-3。

**理由**: 
- error-dna.jsonl (256KB, 100+ entries) 的 timestamp=0 → **完全无法追溯**
- session_id 全是同一个 `38603363-b3e7-4779-ab87-33ef171c4b27` — 说明所有错误都被归到了同一 session
- 如果 timestamp fix 不做，Flywheel (P0) 的数据就是"盲数据"
- **Flywheel + Stop-Drain timestamp = 缺一不可**

---

### 🟡 结论 9: "文档同步" 概念需要明确定义

**Boss 说**: "你持续深度探索，挖掘优化点和问题点...文档同步了"

**问题**: 什么是"文档同步"？
1. **Governance spec → implementation**? (已有 HUMAN-IN-THE-LOOP-GATE.md)
2. **Implementation → documentation**? (RELEASE-PLAN.md 更新)
3. **Documentation → user-facing docs**? (README, launch copy)

**建议**: 明确定义 sync 的 scope，避免"文档同步了"变成模糊承诺。

---

### 🟡 结论 10: Milestone dates are too aggressive

**当前**: M3 gate check + dev override — 5月24日  
**问题**: "gate check" 需要实现完整的 Oracle gate + approve/reject workflow。这不是一个命令能搞定的。

**建议**: 里程碑按依赖关系排期，不写死日期：
```markdown
#### 里程碑 (按依赖顺序)
- M1: pipeline.yaml schema v2 → status CLI (5月10日)
- M2: advance CLI + basic gate check → 7天 after M1
- M3: dev override + full cycle (research→plan→exec→verify) → 7 days after M2
```

---

## Summary — Agent 的建议排序

### 必须改 (MUST):
1. **评分改为 7/10** — 不要给虚假信心
2. **Flywheel → P0-1** — 最快出数据，驱动后续优化
3. **Edit Guard → soft-prompt** — 避免无人值守卡死
4. **Self-healing P0.5** — Boss 提出的关键需求

### 应该改 (SHOULD):
5. **P1-7 Stop-Drain timestamp → P0** — Flywheel 依赖
6. **P1 milestone dates → dependency-based** — 不写死日期
7. **lx-oma-gov vs orch 区别** — 在文档中明确

### 建议改 (COULD):
8. **发布策略分离到 LAUNCH-COPY.md** — 技术文档 vs marketing
9. **Agentic UI 审计结果** — 不要高估自动化程度

---

*这份审计结论由 Hermes Agent 独立生成，未经 Boss 审阅。*
*目的: 给 Boss 一个不同视角的审查结果，帮助他做最终决策。*
