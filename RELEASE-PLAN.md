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
