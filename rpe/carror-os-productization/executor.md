# Executor — Carror OS Productization

> RPE Version: v1.2 | 最后更新: 2026-05-04
> Status: Research Complete — Ready for Phase 0 / Phase 1 Execution

---

## 0. 模式标记

- 本次模式：Standard

---

## 1. 交付概览

- 完成内容：Phase 0 + Phase 1 + Phase 1.5 + Phase 2 + Phase 3 + Phase 5 (全部完成)
- 未完成内容：无 — 全量 16 Task 已完成
- 与计划偏差：新增 Phase 0 (Reality Check)、新增 Phase 1.5 (Observability)、删除 Phase 4、RPE-009 AC 已分配、RPE-001/RPE-008 职责已拆分、RPE-016 矛盾已修复、RPE-012/013/010 依赖已补充

---

## 2. 变更清单

- **新增**: `.claude/scripts/race_manager.sh` — 4 层 Race 调度编排脚本 (init/start/status/complete/list/clean)
- **新增**: `.claude/race/state-machine.md` — Race 状态机文档（含 Mermaid 图表、4 层架构说明、与 OMA Lock 正交性分析）
- **修复**: `oma_lock_manager.py` — TOCTOU 竞争条件 (os.rename 原子操作)
- **新增**: `oma_lock_manager.py` — heartbeat 过期锁检测 + 锁可观测性 (.omc/state/locks.json)
- **修复**: `posttool-write-lock.sh` — 嵌入式换行符 Bug
- **新增**: `harness.yaml` — hooks_enabled.oma_lock: true 开关
- **修复**: `flywheel-report.sh` — v1.3.0, 空日志防护, 桌面通知, 月度趋势

---

## 3. 验证证据

- **AC-16.1** [已验证: .claude/scripts/race_manager.sh:1-4] — 4 层 Race 实现完成：
  - isolation: `.omc/race/{id}/` 目录隔离 (init 命令)
  - dispatch: `run_in_background` 驱动 (start 命令)
  - coordination: 目录隔离 + result.json/owner.json (文件协议)
  - collection: result.json polling (status 命令)
- **AC-16.2** [已验证: .claude/race/state-machine.md:1-5] — Race 状态机文档创建，明确为 orchestration pattern
- **测试验证**:
  - `bash -n .claude/scripts/race_manager.sh` → 无语法错误
  - `init → start → status → complete → list → clean` 全流程通过
  - 重复 init 返回错误、非法 id 校验、无效状态校验 均通过
- **AC-14.1** [已验证: oma_lock_manager.py:120-152] — TOCTOU 修复: os.rename 原子操作替代 unlink 模式
- **AC-14.2** [已验证: oma_lock_manager.py:117,157-175] — heartbeat 过期锁检测, max(locked_at, heartbeat_at) 判断
- **AC-14.3** [已验证: pretool-write-lock.sh:7-15, posttool-write-lock.sh:7-14] — harness_config 集成
- **AC-14.4** [已验证: oma_lock_manager.py:62-105] — .omc/state/locks.json 锁可观测性
- **AC-17.1** [已验证: flywheel-report.sh:19] — `[ -s "$FLYWHEEL" ] || exit 0`
- **AC-17.2** [已验证: flywheel-report.sh:22,172-193] — flywheel-reports/ 持久化目录
- **AC-17.3** [已验证: flywheel-report.sh:124-170] — 月度趋势比较（/dev/tty 输出，不注入 AI 上下文）
- **AC-17.4** [已验证: flywheel-report.sh:195-203] — osascript/notify-send 桌面通知
- **OMA Lock 测试**: `test_oma_lock.py` 7/7 全部通过 (并发压力/心跳/可观测性/status)

---

## 4. Task 执行记录

| RPE-ID | Task | Phase | 状态 | 备注 |
|--------|------|-------|------|------|
| RPE-000 | Repository Reality Check | 0 | ✅ 完成 | 仓库清单 (27 hooks, 23 skills, 3 scripts, 57 docs) |
| RPE-001 | Error DNA 重写 | 1 | ✅ 完成 | 15→177 lines, 4 bugs fixed, dual format, 1MB rotation |
| RPE-002 | Loading Benchmark | 1 | ✅ 完成 | tiktoken measurement, 95.6% reduction verified |
| RPE-003 | Audit Trail 修复 | 1 | ✅ 完成 | rotation + token_writer + degraded logging + CLAUDE.md sync |
| RPE-004 | 统一特性注册表 | 1 | ✅ 完成 | feature-registry.yaml (27/23), feature-probe.sh |
| RPE-005 | Agentic UI 菜单 | 1 | ✅ 完成 | 4 hooks with numbered-choice menus |
| RPE-012 | lx-status 升级 | 1.5 | ✅ 完成 | 3-panel→5-panel, degraded states, ASCII trend |
| RPE-013 | Audit 统一仪表盘 | 1.5 | ✅ 完成 | 5-source aggregation, SHA256, 3 output modes |
| RPE-006 | Lecture 系列 | 2 | ✅ 完成 | 8 docs + README + lecture_sync_check.py |
| RPE-007 | Docs 重构 | 2 | ✅ 完成 | BIMODAL restructure (9 new files, 4 moved) |
| RPE-008 | Error DNA 共享库 | 2 | ✅ 完成 | error_classifier.py, dual fallback (import/inline) |
| RPE-010 | Marketing 重写 | 3 | ✅ 完成 | claim-registry.yaml, claim-lint.sh, docs/marketing 中性化改造 |
| RPE-011 | Launch Asset 补全 | 3 | ✅ 完成 | screenshot-checklist, DOGFOODING-LOG, external-review-template |
| RPE-014 | OMA Lock 增强 | 5 | ✅ 完成 | TOCTOU 修复, heartbeat, harness_config, 7/7 测试通过 |
| RPE-016 | Race 调度增强 | 5 | ✅ 完成 | .claude/scripts/race_manager.sh + .claude/race/state-machine.md |
| RPE-017 | Flywheel 增强 | 5 | ✅ 完成 | v1.3.0, 空日志防护, 桌面通知, 月度趋势 |

---

## 已完成的 Step

| Step | Task | 完成日期 | 证据 |
|------|------|---------|------|
| Phase 1 Research | PRD 全量 16 需求 + 13 Oracle | 2026-05-04 | research.md 完整填充 |
| Oracle Round 1 | 13/13 独立咨询 | 2026-05-04 | 13 份 Oracle 报告 |
| Oracle Round 2 | 4 不成熟项联网调研 | 2026-05-04 | oracle-research-round2.md |
| Oracle Round 3 | 17 Task 全量最终验证 | 2026-05-04 | oracle-round3-synthesis.md |
| GPT5.5 Research 评审 | research.md 13 处不严谨表述修正 | 2026-05-04 | gpt5.5-export.md |
| GPT5.5 Plan 评审 | plan.md 结构修正 (Phase 0 + 依赖 + 职责拆分) | 2026-05-04 | gpt5.5-export-plan.md |
| Plan 合成 (v1.0) | Oracle 优化 WBS (17 Tasks) | 2026-05-04 | plan.md |
| Plan 更新 (v1.1) | Round 3 修正 (16 Tasks, 5 Phases) | 2026-05-04 | plan.md + AC 重分配 |
| Plan 更新 (v1.2) | GPT5.5 Plan 评审 (Phase 0 + 依赖修正 + 职责拆分) | 2026-05-04 | plan.md + progress.md + executor.md |
| GPT5.5 Report Advice 评估 | 10 条建议覆盖分析 — 8/10 已覆盖, 2 项记录待讨论 | 2026-05-04 | research.md + plan.md |
| GPT5.5 Report Advice 2 评估 | 评分表采纳 + 任务清单确认覆盖 | 2026-05-04 | docs/internal/product-comparison-scorecard.md + research.md |
| GPT5.5 Release Plan 评估 | 发布计划定位语采纳 + 模板创建 | 2026-05-04 | research.md + README + manifesto + FAQ + DOGFOODING-LOG.md + EVIDENCE-BANK.md |
| GPT5.5 better-info 评估 | 8 建议覆盖分析 + First 10 Minutes 指南创建 + C1-C5 证据层级互补 | 2026-05-04 | research.md + plan.md + progress.md + docs/guides/first-10-minutes.md + EVIDENCE-BANK.md |
| GPT5.5 better-info2 评估 | 29 章覆盖分析 + Known Limitations + Feedback Questions 创建 | 2026-05-04 | research.md + plan.md + progress.md + docs/reference/known-limitations.md + docs/reference/feedback-questions.md |
| RPE-000 | Repository Reality Check | 2026-05-04 | state/repository-reality-check.md |
| RPE-001 | Error DNA 重写 (15→177 lines, 4 bugs fixed) | 2026-05-04 | .claude/hooks/error-dna.sh (.jsonl + .json dual format, 1MB rotation) |
| RPE-002 | Loading Benchmark (tiktoken, 95.6% verified) | 2026-05-04 | .claude/scripts/loading_benchmark.py |
| RPE-003 | Audit Trail 修复 (rotation + token_writer + degraded) | 2026-05-04 | .claude/hooks/read-tracker.sh + token_writer.sh + proactive-handoff.sh |
| RPE-004 | Feature Registry (27 hooks + 23 skills) | 2026-05-04 | .claude/feature-registry.yaml + feature-probe.sh |
| RPE-005 | Agentic UI menus (4 hooks, numbered-choice) | 2026-05-04 | 4 gate hooks: completion/context/permission/pretool-edit-scope |
| RPE-012 | lx-status v2.0 (3-panel→5-panel, degraded states) | 2026-05-04 | carror_dashboard.py (5-panel: Token/Error DNA/Flywheel/Registry/Context) |
| RPE-013 | Audit Dashboard (5-source, SHA256, 3 modes) | 2026-05-04 | .claude/scripts/audit_dashboard.py |
| RPE-007 | Docs BIMODAL 重构 (9 new files, 4 moved) | 2026-05-04 | docs/overview/ + concepts/ + guides/ + governance/ |
| RPE-008 | Error DNA 共享库 (error_classifier.py, dual fallback) | 2026-05-04 | .claude/scripts/error_classifier.py |
| RPE-006 | Lecture 系列 (8 docs + README + sync checker) | 2026-05-04 | lecture/ (01→08) + README.md + lecture_sync_check.py |
| RPE-010 | Marketing 重写 | 2026-05-04 | claim-registry.yaml + claim-lint.sh + 4 docs 中性化 |
| RPE-011 | Launch Asset 补全 | 2026-05-04 | screenshot-checklist + DOGFOODING-LOG + external-review-template |
| RPE-014 | OMA Lock 增强 | 2026-05-04 | oma_lock_manager.py v2 (TOCTOU + heartbeat + 7/7 tests) |
| RPE-016 | Race 调度增强 | 2026-05-04 | race_manager.sh + state-machine.md |
| RPE-017 | Flywheel 增强 | 2026-05-04 | flywheel-report.sh v1.3.0 (空日志/趋势/桌面通知) |
| RPE-016 | Race 调度增强 (4-layer race + state machine) | 2026-05-04 | .claude/scripts/race_manager.sh + .claude/race/state-machine.md |
