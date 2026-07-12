# CarrorOS 资产清单 — Skills + Hooks

> 生成时间：2026-07-05

> 用途：基于「重构3」round3 架构方向，筛选保留高价值资产，剔除低价值资产

> Skills: 27 | Hooks: 77


---

## Skills（27 个）


### lx-code-review
- **描述**: Review & fix Go code: 8 categories, 39 rules covering error handling, concurrency, interface design, performance, robustness, observability.
- **引用文件**: auto-fix-templates.md, body.md, checklists, knowledge, rules-catalog.md
- **脚本**: subagent_reviewer.py


### lx-dogfood
- **描述**: 主动投喂狗粮 — 事故发生时趁热记录，处理完毕时提炼教训，让 Carror OS 和你意念通达
- **引用文件**: body.md, feed-protocol.md, structure-ecosystem.md


### lx-ghost
- **描述**: 幽灵模式 — 方向驱动的自主探索。Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告。
- **引用文件**: body.md, ghost-oracle-audit.md, ghost-phase0.md, ghost-polling.md
- **脚本**: lx-ghost.sh


### lx-goal
- **描述**: 目标模式 — 一次前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。入口：`/lx-goal` 或 `/executor`
- **引用文件**: autonomous-execution.md, body.md, exit-report.md, phase0-activation.md
- **脚本**: __pycache__, lx-goal.py, lx-goal.sh


### lx-learner
- **描述**: 从对话中提取可重复工作流并生成 lx-* skill。检测模式 → 提议提取 → 生成技能 → 附带来源文档。
- **引用文件**: body.md, pattern_detection_guide.md, phase-detect.md, phase-document.md, phase-propose.md...
- **脚本**: extract_pattern.py


### lx-oma-gov
- **描述**: OMA PRD 治理 — reconcile/propagate 增量同步、冲突裁决、漂移检测
- **引用文件**: body.md, commands-audit.md, commands-reconcile.md, directory-structure.md, pipeline-integration.md


### lx-oma-hier
- **描述**: 分层 PRD 拆解 — 将超大型 PRD 按功能域 MECE 拆分为多个 Sub PRD（黑盒/接口契约/Mock 数据/内部闭环），再委托 lx-oma-split 拆解为特性级 RPE。
- **引用文件**: body.md, error-codes.md, observability.md, pipeline.md, sub-prd-template.md...


### lx-oma-orch
- **描述**: Pipeline Orchestrator — 4-skill 管线编排（状态查看/阶段推进/Oracle 门禁/并行开发管理）
- **引用文件**: advance-flow.md, body.md, dev-management.md, error-codes.md, interface-contract.md...


### lx-oma-split
- **描述**: 一人成军司令部 — 将需求拆解为正交 feature 分支（prd/{sub_prd}/{feature}）
- **引用文件**: body.md, delivery-report.md, interface-verification.md, mece-checklist.md, scaffolding-template.md


### lx-oracle
- **描述**: Oracle 独立第三方审核 — 环境自适应路由: 有 Agent 时物理隔离 spawn, 无 Agent 时本地 prompt。裁决留痕 oracle-verdicts.md。
- **引用文件**: body.md


### lx-oracle-v2
- **描述**: DEPRECATED — 已合并到 lx-oracle v2.0。请使用 /lx-oracle。支撑脚本保留。
- **引用文件**: body.md, oracle-protocol.md
- **脚本**: oracle-spawn.sh


### lx-pre-commit
- **描述**: 提交前质量门禁：项目类型检测 → 编译 → 测试 → 代码审查。操作层由 scripts/ 脚本执行，AI 负责结果解读和路由决策。
- **引用文件**: body.md, checklists
- **脚本**: detect_project.py, run_checks.py


### lx-pre-push
- **描述**: 推送前深度门禁：commit message 规范校验（骨架驱动，通用）→ 测试覆盖 → 安全扫描 → 判定。
- **引用文件**: ank-commit-rules.md, body.md, commit-convention-guide.md
- **脚本**: commit_convention.py, get_changed_files.py, validate_commits.py


### lx-purify
- **描述**: 思想纯度审计 — 哲学→铁律→现状三层全量审计，逐对象双法官审核，改完即验。
- **引用文件**: audit-cheatsheet.md, body.md


### lx-race
- **描述**: 蜂群协调层 — 快速并行处理简单同构任务。goal/ghost 自动路由至此。
- **引用文件**: body.md, coordination-flow.md, cross-platform-arch.md, worker-protocol.md


### lx-root-cause-analysis
- **描述**: Trace recurring Go bugs via Five Whys: evidence chains → confidence scoring → immunity defense.
- **引用文件**: anti-patterns.md, body.md, checklists, confidence-scoring.md, go-root-cause-patterns.md...


### lx-rpe
- **描述**: RPE 系统性特性开发 — 9 步闭环：TDD → code-review → security → acceptance → graded rollback
- **引用文件**: _archive, batch-accept-template.md, body.md, commit-convention.md, frontend-coding-rules.md...
- **脚本**: build_and_test.py, extract_ac.py, git_commit.py, update_progress.py


### lx-skillify
- **描述**: 将自然语言描述转化为生产级 lx-* skill。6 阶段管道。
- **引用文件**: body.md, phases-clarify-analyze-generate.md, phases-create-validate-register-report.md, reference_skill_selector.md, skill_generation_prompts.md
- **脚本**: skillify_generator.py, verify_and_register.py


### lx-status
- **描述**: Carror OS 健康面板 v3.0：Token 节省、任务通过率、拦截的错误、升华的知识点 + ROI 量化面板。底部追加 audit dashboard 摘要（5 源聚合）。
- **引用文件**: body.md


### lx-stepwise
- **描述**: 逐步攻坚模式 — 高难度 bug 单步推进，每步需验证，不可跳过。与 lx-race 互补（race 并行快处理，stepwise 串行深攻坚）。
- **引用文件**: body.md


### lx-sync
- **描述**: 变更后一致性检查：frontmatter↔registry 漂移、source mirror 同步、harness_version 对齐、重复 key、引用完整性。修完任何治理文件后调用。
- **引用文件**: body.md
- **脚本**: sync_check.py


### lx-task-spec
- **描述**: 任务驱动机制：lx-todo 升级目标，处理需精确 AC 但不需要完整 PRD 的中等复杂任务。3 问引导 → 规划 → 执行 → 验收。
- **引用文件**: ac-template.md, body.md, execution-modes.md, guided-interaction.md


### lx-test-gen
- **描述**: Language-agnostic test code generator. Auto-detects project language (Go/TS/Python/etc.), routes to appropriate test patterns: table-driven, mocks, HTTP handlers, benchmarks, fuzz, property-based.
- **引用文件**: body.md


### lx-todo
- **描述**: 轻量开发模式：捕获 → 分拣 → 执行 → 验证 → 关闭。5 步单终端闭环，≤3 文件变更。
- **引用文件**: body.md, execution-types.md, queue-format.md, steps-capture-triage.md, steps-close-review.md...
- **脚本**: todo_queue.py


### lx-validate-skill
- **描述**: 验收新 skill 是否遵循原子化架构规则。检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等 11 项规则。
- **引用文件**: body.md, report-templates.md
- **脚本**: carror_dashboard.py, check_progressive_disclosure.py, skill_trace_report.py, validate_skill.py


### lx-varlock
- **描述**: 隐私脱敏代理管理器。处理包含敏感信息（密码、API Key、Token）的文件读写或命令执行，确保明文绝不泄露在 AI 上下文中。
- **引用文件**: body.md
- **脚本**: varlock.py


### update-carror-os
- **描述**: Carror OS 安装/更新技能，自动保护 AGENTS.md 不被安装脚本污染。备份 → 安装 → 恢复 → 验证 4 步闭环。
- **引用文件**: body.md


---

## Hooks（77 个）

| 文件名 | 语言 | 大小 | 行数 | 阻塞？ | 关键函数 | 描述 |
|--------|------|------|------|--------|----------|------|
| agentic-ui.py | python | 3.3KB | 108L | ⚠ | banner, separator, status, breakdown, table | agentic-ui.py — 共享库（非 Hook） — Agentic UI 标准化输出函数

Role: 提供统一的菜单/确认/CAPTCHA/状态输出，替代各 hook 中分散的纯文本 stderr

This is a utility module; functions are primarily accessed via harness_lib.py.
Exports addition |
| auto-snapshot.py | python | 24.3KB | 670L | ⚠ | _get_mtime, _read_turns, _get_branch, _git_diff_names, _strip_surr | auto-snapshot.py — Stop / PostToolUse:Edit|Write — 会话结束时自动保存状态快照（分支/轮次/未提交文件）
Role: 会话结束时自动保存状态快照（分支/轮次/未提交文件）

等效移植自 auto-snapshot.sh (532行):
- 保存 session-snapshot.json (含 timestamp/turns/branch/modi |
| completion-gate.py | python | 30.5KB | 704L | ⚠ | _get_fallback_level, _check_finish_length_detected, _manage_finish_length_streak, _is_autonomous, _auto_soft_block | completion-gate.py — PostToolUse:TaskUpdate — 强制 TaskUpdate 前提供结构化证据文件
Role: 强制 TaskUpdate 前提供结构化证据文件

等效移植自 completion-gate.sh (438行):
- 提取 status 字段，非 completed → 放行
- 自主/无人值守模式降级（检查 + warn，不阻断）
- 证 |
| context-compressor.py | python | 7.1KB | 183L | ⚠ | safe_stat_mtime, main | context-compressor.py — SessionStart — 渐进式披露：源文件精简版注入缓存
检测源文件 mtime → 拼接精简内容 → 缓存到 .omc/state/context-cache.md |
| cross-platform-smoke-test.py | python | 3.1KB | 93L | ⚠ | _run, main | cross-platform-smoke-test.py — SessionStart — 检测 stat 和 sed 的跨平台兼容性
Role: 检测 stat 和 sed 的跨平台兼容性，永不阻断 |
| distinct-concept-richner.py | python | 3.3KB | 97L | ⚠ | detect_concept_overlap, inject_distinction, write_signal, main | distinct-concept-richner.py — Richner hook: distinct概念丰富化

在AI生成内容中检测概念混淆/重叠, 自动注入区分策略。
哲学归属: #7(文档) → 确保概念边界清晰, 引用准确。

工作流:
  1. 检测输出中概念混用 (同义反复/范畴错误/层级混淆)
  2. 如发现混淆 → 注入区分说明 + 引用AGENTS.md路由表
  3. 记 |
| ecosystem-probe.py | python | 11.4KB | 310L |  | detect_omo_family, main | ecosystem-probe.py — SessionStart — 生态探针

Role: 检测运行平台（Claude Code / OpenCode）与 OMO 安装状态，输出软建议
永不阻断，exit 0。SessionStart 时注入平台能力信息，AI 据此调整行为策略。
有 OMO 时：hook 完整运行，gate/skill/context 全功能可用
无 OMO 时：无 hook |
| edit-guard.py | python | 3.9KB | 126L | ⚠ | main | edit-guard.py — PreToolUse:Edit — 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
Role: 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
对应 edit-guard.sh 的 Python 移植，保持完全相同的逻辑 |
| error-dna-aggregator.py | python | 5.8KB | 159L | ⚠ | main | error-dna-aggregator.py — Stop — 聚合 error-dna.jsonl → error-dna.json 含去重+升华+退化

Role: 跨会话错误聚合管道
- 去重: 按 signature 聚合 error-dna.jsonl，同一天内重复签名只 count++
- 升华: count >= 3 自动生成规则到 error-rules.md
- 退化: 7天未 |
| error-dna-auto-fix.py | python | 2.6KB | 81L | ⚠ | main | error-dna-auto-fix.py — Stop — 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
Role: 跨会话错误回顾，只输出 fix_count > 1 的条目 |
| error-dna.py | python | 20.1KB | 511L | ⚠ | main | error-dna.py — PostToolUse:Bash / PostToolUseFailure:Bash — 轻量错误捕获（Oracle 瘦身后 v2）
Role: 捕获 Bash 错误写入 error-dna.jsonl + governance-audit.jsonl + total-ops 计数器 + 高频告警

等效移植自 error-dna.sh (538行) |
| flywheel-report.py | python | 5.9KB | 181L |  | main | flywheel-report.py — SessionStart — 读取飞轮日志，生成 30 天频率摘要注入会话

Role: 读取飞轮日志，生成 30 天频率摘要注入会话 |
| harness_core.py | python | 11.4KB | 366L |  | _resolve_python_bin, _ensure_cache, _load_cache_file, _parse_cache_content, _write_cache | harness_core.py — 共享库核心（Python 版）
高频函数: hc_enabled, output_continue, read_input, flywheel_event, hc_get
用于频繁调用的 hook，减少 import 开销。

版本对照：harness_config.sh v6.6.4 → harness_core.py v1.0 |
| harness_lib.py | python | 16.5KB | 537L | ⚠ | hc_init, _resolve_python_bin, hc_get_list, hc_fail_closure, hc_hook_enabled | harness_lib.py — 共享库（Python 版）扩展部分
Core 函数已拆分到 harness_core.py。
向后兼容: from harness_lib import * 仍可导入所有函数。

版本对照：harness_config.sh v6.6.4 → harness_lib.py v1.0 |
| inject-project-knowledge.py | python | 3.8KB | 110L | ⚠ | safe_read_head, main | inject-project-knowledge.py — SessionStart — 注入紧凑记忆恢复文件
注入 todo-queue.md(最近询问+任务摘要) + session-handoff.md + session-dump.json + session-handoff-v2.json |
| intent-tracker.py | python | 8.9KB | 241L |  | main | intent-tracker.py — PostToolUse:Edit|Write — 跟踪文件级编辑统计 + revert 检测

Role: 跟踪编辑次数、检测内容回退（revert）、标记高频编辑（churn）

原理：
  PostToolUse 不暴露 AI 输出文本，无法直接检测语义矛盾（已知约束）。
  替代方案（均为文件级统计，非语义分析）：
  1. 跟踪每个文件在会话内的编辑 |
| knowledge-condenser.py | python | 8.7KB | 238L |  | main | knowledge-condenser.py — Stop — 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议

Role: 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
GS-003: 自动知识抽取 — 支持 [seed:*] 和 @YYYY-MM-DD 两种格式 |
| lsp-gate.py | python | 2.7KB | 91L | ⚠ | main | lsp-gate.py — SessionStart — 检测项目语言对应的 LSP 是否可用
Role: 确保基础设施就绪再开始工作 |
| lsp-suggest.py | python | 4.7KB | 133L |  | _extract_pattern, _has_regex_metacharacters, _is_exported_symbol_pattern, _is_pure_identifier, main | lsp-suggest.py — PreToolUse:Grep — 检测 Grep 搜索导出符号时建议改用 LSP 工具

Role: 检测 Grep 搜索导出符号时建议改用 LSP 工具
Replaces lsp-suggest.sh with pure Python3 (cross-platform). |
| meta-oracle-trigger.py | python | 14.1KB | 411L |  | _resolve_project_root, _is_feature_enabled, _read_stdin_json, _extract_combined_text, _emit_json | Meta-Oracle trigger hook — PostToolUse event, G1-G4 gate detection.

Replaces meta-oracle-trigger.sh with pure Python3, cross-platform
(macOS / Linux / Windows) and zero external dependencies.

4 trig |
| oracle-gate.py | python | 17.1KB | 501L |  | _timeout_handler, _timeout_wrapper, _load_consolidated_state, _save_consolidated_state, _cleanup_legacy_state_files | pretool-oracle-gate.py — Oracle review pre-gate (Python3 cross-platform)

Replaces pretool-oracle-gate.sh on Windows where bash is unavailable.
Block mechanism/governance file edits without 24h Oracle |
| permission-frequency-tracker.py | python | 3.4KB | 116L | ⚠ | main | permission-frequency-tracker.py — PostToolUse:* — 统计当前会话中 permission-required* 文件的创建次数
写入 .omc/state/permission-frequency.json
永不阻断 |
| permission-gate.py | python | 24.7KB | 599L | ⚠ | _hc_ensure_cache, _load_cache_file, _rebuild_cache, hc_get, hc_enabled | 确保 harness.yaml 缓存已加载，返回 True=可用 False=空/不可用 |
| phase-state-tracker.py | python | 5.4KB | 162L |  | check_accept_24h, main | phase-state-tracker.py — PostToolUse hook — 追踪当前任务所处的五阶段状态

Role: 检查 oracle-verdicts.md 24h 内是否有 ACCEPT → phase2_approved
      检查 git diff 是否有未提交修改 → phase3_executing
      写入 .omc/state/current-phas |
| plan-gate.py | python | 0.2KB | 6L | ⚠ | - | plan-gate: 计划门禁占位桩（已注册但暂未实现） |
| posttool-anti-pattern-detect.py | python | 5.5KB | 150L | ⚠ | extract_result, log_violation, main | posttool-anti-pattern-detect.py — PostToolUse:TaskUpdate|Edit|Write — 反模式自动检测

Role: 根据 .claude/anti-patterns.md 自动检测 A2/F1/H1 反模式输出
哲学 #6：先天对 AI 0 信任 — 自动化检测语义层面的反模式
哲学 #4：没通过验证等于没做 — A2 虚假完成硬阻断

阻断策 |
| posttool-bash-audit.py | python | 13.6KB | 332L | ⚠ | main | posttool-bash-audit.py — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计权限上下文，只提醒不阻断
Role: Bash 执行后审计权限上下文，只提醒不阻断
对应 posttool-bash-audit.sh 的 Python 移植 |
| posttool-checkpoint.py | python | 6.1KB | 169L |  | main | posttool-checkpoint.py — PostToolUse:TaskUpdate + Stop — 工作流闭环：所有工作流结束时输出结构化 checkpoint

Role: TaskUpdate(completed) / Stop 时自动生成过程摘要 + 决策记录 + 待处理 + 方向指引
覆盖: RPE / TODO / Task-Spec (TaskUpdate) + Goal |
| posttool-claim-audit.py | python | 11.7KB | 273L | ⚠ | main | posttool-claim-audit.py — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验
检测 AI 对文件内容的断言（file:line 引用 + 数值断言来源）是否基于真实读取
Role: 铁律 #1 enforce — AI 不能编造没读过的代码事实 + 不能写无来源的数值断言

等效移植自 posttool-claim-audit.sh (218 |
| posttool-completion-audit.py | python | 5.0KB | 153L |  | main | posttool-completion-audit.py — PostToolUse — 独立验证 evidence 质量（E3/E7 防御纵深）

Role: PostToolUse 独立验证证据文件质量，不依赖 completion-gate 的门禁逻辑

原理：
  completion-gate.sh 是 PreToolUse 门禁（阻断无证据的完成声明）。
  本 hook 是 Post |
| posttool-edit-quality.py | python | 8.5KB | 223L | ⚠ | _fnmatch, main | posttool-edit-quality.py — PostToolUse:Edit|Write — 编辑后自查代码风格、文档同步、方案复用检测
Role: 编辑后自查代码风格、文档同步、方案复用检测
对应 posttool-edit-quality.sh 的 Python 移植 |
| posttool-error-dna-shard.py | python | 2.7KB | 102L |  | main | error-dna-shard.py — PostToolUse — daily sharding for error-dna.jsonl

Periodically splits error-dna.jsonl by date into daily/{date}.jsonl.
Runs every 50th PostToolUse to avoid per-call overhead. |
| posttool-format-gate.py | python | 2.4KB | 81L | ⚠ | main | posttool-format-gate.py — PostToolUse:TaskUpdate — 以人为本输出格式门禁（哲学 #5 物化）
检查任务输出是否符合"以人为本"原则：有方向感、结构化、认知负担低 |
| posttool-handoff-writer.py | python | 7.2KB | 218L |  | main | posttool-handoff-writer.py — PostToolUse:TaskUpdate — 每次 Task 完成后写 handoff

Role: 每次 Task 完成后写 handoff（E8 上下文遗忘防御） |
| posttool-read-cite.py | python | 2.5KB | 90L | ⚠ | _fnmatch, main | posttool-read-cite.py — PostToolUse:Read [默认关闭] — 读取文件后提示引用规范
Role: 读取文件后提示引用规范
对应 posttool-read-cite.sh 的 Python 移植 |
| posttool-skill-compliance.py | python | 4.3KB | 137L | ⚠ | main | posttool-skill-compliance.py — PostToolUse:Skill — 执行合规审计
在 skill 执行后审计 AI 是否按 body.md 执行了，发现偏差则注入警告 |
| posttool-subagent-audit.py | python | 5.5KB | 157L | ⚠ | main | posttool-subagent-audit.py — PostToolUse:Task — 子 agent 执行后审计 content 用量，超限告警 |
| posttool-template-check.py | python | 1.8KB | 63L | ⚠ | main | posttool-template-check.py — PostToolUse — 模板文件写入后输出 schema 提醒
Role: 检测是否写入了 .claude/task_sys/templates/ 下的模板文件，输出 schema 提醒 |
| posttool-write-cite.py | python | 3.9KB | 114L | ⚠ | main | posttool-write-cite.py — PostToolUse:Write|Edit — 检测写入 claude-next.md 时验证教训格式 |
| posttool-write-lock.py | python | 2.3KB | 78L | ⚠ | main | posttool-write-lock.py — PostToolUse:Edit|Write — 写操作后释放 OMA 并发锁
Role: 写操作后释放 OMA 并发锁 |
| pre-ask-guard.py | python | 8.3KB | 214L | ⚠ | extract_questions, extract_keywords, search_decision_chain, main | pre-ask-guard.py — PreToolUse:AskUserQuestion — 两段式决策链评估

Role: 拦截 AskUserQuestion，检查决策链是否已有答案。能自主决策则阻断提问，降低人类心智负担。

决策链（两段式）：
  Phase 1 (快速扫描): AGENTS.md → kernel.md（高频匹配层，单次读取）
  Phase 2 (完整遍历): ant |
| pre-completion-gate.py | python | 4.0KB | 128L | ⚠ | main | pre-completion-gate.py — PreToolUse:TaskUpdate — 前置完成门禁，阻止无证据的 completed 调用
Role: 前置完成门禁，在 AI 调用 TaskUpdate(completed) 前阻止，减少浪费轮次
对应 pre-completion-gate.sh 的 Python 移植，保持完全相同的逻辑 |
| pre-edit-lsp-check.py | python | 7.0KB | 204L | ⚠ | safe_strip_ansi, run_diagnostic, main | pre-edit-lsp-check.py — PreToolUse:Edit — 编辑前强制诊断检查 (v2)
编辑代码文件前主动获取诊断结果，注入 AI 上下文
永不阻断 (exit 0) — 诊断注入不阻断编辑 |
| pretool-agents-merge.py | python | 9.1KB | 269L | ⚠ | read_file, write_file, is_standard_line, extract_user_content, _filter_standard_block | pretool-agents-merge.py — AGENTS.md 智能合并策略

触发: PostToolUse(Edit|Write) 作用于 AGENTS.md
也可由 install.sh / harness-kit-install.sh 在覆盖安装后手动调用。

流程:
  1. 读取当前 AGENTS.md（发布包标准版）
  2. 备份旧 AGENTS.md → .omc/sta |
| pretool-agents-merge.sh | bash | 1.6KB | 48L |  | - | !/bin/bash |
| pretool-approve-detect.py | python | 3.5KB | 95L | ⚠ | main | pretool-approve-detect.py — UserPromptSubmit — 检测 /approve <token> 或 /deny，自动写入/清除 CAPTCHA 批准文件
Role: 拦截用户聊天中的 /approve|/deny 指令，实现对话内批准流程
对应 pretool-approve-detect.sh 的 Python 移植 |
| pretool-b1-detect.py | python | 3.7KB | 121L | ⚠ | main | pretool-b1-detect.py — PreToolUse:Edit|Write — 检测单次编辑是否过度（新文件创建数告警）
统计本会话已创建的新文件数，超过5个时输出告警但不阻断。记录每次新文件创建到 new-files-log.jsonl |
| pretool-blast-radius.py | python | 3.5KB | 92L | ⚠ | main | pretool-blast-radius.py — PreToolUse:Bash — 全局破坏性命令拦截 (DG-101)
Role: 检测 git checkout . / rm -rf 等全量操作，提醒改用选择性路径 |
| pretool-compact-writer.py | python | 9.3KB | 275L |  | collect_query_history, collect_session_state, write_handoff, write_todo_queue, main | pretool-compact-writer.py — PreCompact — 在 /compact 前保存任务状态+最后20条用户query

Role: /compact 前收集当前会话状态、活跃任务、最近用户询问
      写入 session-handoff.md 和 todo-queue.md，
      确保 compact 后 inject-project-knowledge  |
| pretool-cruise-check.py | python | 2.6KB | 82L | ⚠ | main | pretool-cruise-check.py — SessionStart/PreToolUse — 巡航模式基础设施自检
Role: 检测 ghost/goal mode 激活但巡航基础设施未初始化 → 提醒 AI 创建 |
| pretool-edit-scope.py | python | 13.1KB | 437L | ⚠ | read_stdin, extract_file_path, check_completion_blocked, _safe_remove, warn_protected_file | pretool-edit-scope.py — PreToolUse:Edit|Write — Scope management + Rule anchor + completion-blocked reminder (DG-131)
Role: Scope file matching + auto-add + core file warning + long conversation rule  |
| pretool-git-gate.py | python | 3.6KB | 116L | ⚠ | get_file_mtime, main | pretool-git-gate.py — PreToolUse:Bash — Git 提交前 pre-commit 检查门禁（铁律 #4 物化）
检测 git commit 前是否有 pre-commit 检查。非 git commit 命令透传。 |
| pretool-level-gate.py | python | 4.6KB | 159L |  | _read_input, _check_hard_conditions, _check_soft_conditions, main | pretool-level-gate.py — L1/L2 二元路由判级门禁

拦截所有 PreToolUse 请求，检查是否需要升级到 L2。
硬条件命中 → 阻断 + 强制走 L2 入口
软条件 → 注入 context 提示 agent 可升级

输入：CC hook 标准 stdin (JSON)，含 tool_name, tool_input
输出：CC hook 标准继续/阻断信号

 |
| pretool-node-reference.py | python | 1.6KB | 62L | ⚠ | main | pretool-node-reference.py — PreToolUse — Agent 工具调用时注入可用 nodes 列表
Role: 检测 Agent 工具调用，注入 .claude/nodes/ 目录下可用 node 列表到上下文 |
| pretool-plan-gate.py | python | 11.9KB | 297L | ⚠ | main | ⛔ [Plan Gate] 目标模式活跃，但 Phase 0 未完成 (phase0_passed_at 缺失)。

    AI 必须先调用 phase0-done 完成计划阶段:
      lx-goal phase0-done

    这会验证 prd.md 已写入子任务/验收标准/风险点，
    然后将 phase0_passed_at 写入 lx-goal.json，解锁代码变更。 |
| pretool-purify-gate.py | python | 1.9KB | 68L | ⚠ | main | pretool-purify-gate.py — PreToolUse:Edit|Write — 编辑治理文件时注入哲学纯度提醒
Role: 编辑治理文件时注入哲学纯度提醒到 AI 上下文 (不阻断) |
| pretool-retry-check.py | python | 12.1KB | 327L | ⚠ | read_stdin, get_tool_name, get_command, check_budget_exceeded, check_near_limit | pretool-retry-check.py — PreToolUse — 阻断超过重试上限的 Bash 命令

Role: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令

原理：
  retry-budget.json 记录每个错误签名的重试次数。
  当某个签名超过 MAX_RETRIES（默认 3），后续 Bash 调用被阻断。
  避免 AI 在同一个错 |
| pretool-rules-inject.py | python | 5.7KB | 179L |  | parse_context_cache, main | pretool-rules-inject.py — UserPromptSubmit — 3级脱水分层注入

永不阻断 (exit 0)
Turn 0: L1+L2+L3 全量上车
Turn 1+: 自适应频率 (L1每轮, L2自适应, L3每10轮) |
| pretool-scope-gate.py | python | 5.1KB | 156L | ⚠ | read_scope_patterns, is_in_scope, main | pretool-scope-gate.py — PreToolUse:Edit|Write — 检测 Edit/Write 是否超出 current-scope.txt 声明的文件范围

哲学 #5(范围冻结): 一次一 Step，非核心 → TODO，越界 → 撤销
无 current-scope.txt 时透传。支持 glob 模式匹配。自主模式降级为记录。 |
| pretool-sensitive-edit.py | python | 8.8KB | 304L | ⚠ | extract_file_path, check_bash_tool, is_sensitive_file, check_captcha_approval, output_captcha_block | pretool-sensitive-edit.py — PreToolUse:Edit|Write|Bash — 治理文件编辑验证码门禁（哲学 #6 物化）

Role: 对 CLAUDE.md/AGENTS.md/harness.yaml/settings.json 等治理文件的 Edit/Write/Bash
      要求用户 CAPTCHA 确认
哲学 #6：先天对 AI 0 信任 —  |
| pretool-sensitive-file-guard.py | python | 3.2KB | 105L | ⚠ | _is_mode_active, main | pretool-sensitive-file-guard.py — PreToolUse:Edit|Write — 保护门禁文件不被 AI 直接写入
Role: 拦截 AI 通过 Edit/Write 工具直接写 permission-approved / permission-required 等门禁文件 |
| pretool-skill-body-enforce.py | python | 3.1KB | 106L | ⚠ | main | pretool-skill-body-enforce.py — PreToolUse:Skill — 强制执行合约注入
在 skill 执行前自动将 body.md 内容注入 additionalContext，
确保 AI 无法"选择不看"执行合约。 |
| pretool-skill-version-guard.py | python | 3.8KB | 108L | ⚠ | main | pretool-skill-version-guard.py — PreToolUse:Edit|Write — SKILL.md 版本格式 + 引用有效性门禁
拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式（指向 VERSION.json 单一真相源）
拦截 @references 指向不存在文件的写入 |
| pretool-terminal-safety.py | python | 3.6KB | 110L | ⚠ | main | pretool-terminal-safety.py — PreToolUse:Bash — 终端命令格式校验
永不阻断 (exit 0) 但超长命令(>2000字符)除外 — 告警+flywheel, >2000字符硬阻断 |
| pretool-user-correction.py | python | 6.0KB | 147L | ⚠ | main | pretool-user-correction.py — UserPromptSubmit — 检测用户纠正信号，强制记录到 claude-next.md |
| pretool-write-lock.py | python | 3.8KB | 114L |  | main | pretool-write-lock.py — PreToolUse:Edit|Write — 写操作前获取 OMA 并发锁，防止多终端冲突
Role: 写操作前获取 OMA 并发锁，防止多终端冲突。锁管理器异常时 fail-open（记录+放行），不硬阻断写入
对应 pretool-write-lock.sh 的 Python 移植 |
| privacy-gate.py | python | 4.9KB | 156L | ⚠ | _agentic_status_danger, _check_file_path, _check_command_for_tokens, main | privacy-gate.py — PreToolUse:Bash|Read|Grep — 防止隐私数据泄露（DLP 门禁）
Role: 防止隐私数据泄露（DLP 门禁）

等效移植自 privacy-gate.sh:
- 文件路径敏感匹配 (.env, .pem, .key, credentials, kubeconfig 等)
- 命令明文 Token 检测 (sk-, ghp_, Beare |
| read-tracker.py | python | 3.2KB | 108L | ⚠ | main | read-tracker.py — PostToolUse:Read — 记录已读文件路径供 edit-guard 检查 Read-before-Edit
Role: 记录已读文件路径供 edit-guard 检查 Read-before-Edit |
| score-archiver.py | python | 2.5KB | 86L | ⚠ | _extract_date, main | score-archiver.py — Stop — 归档评分报告到 .claude/data/score/daily/

迁移 .omc/state/auto-score-*.json → .claude/data/score/daily/{date}.json
仅归档最新的评分报告（按天去重），不删除源文件。 |
| sessionstart-gate-check.py | python | 3.0KB | 77L | ⚠ | main | sessionstart-gate-check.py — SessionStart — 门禁禁用状态通知
Role: 在会话启动时检查 harness.yaml 中显式禁用的门禁/功能并输出警告 |
| skill-flywheel.py | python | 3.3KB | 102L | ⚠ | main | skill-flywheel.py — Stop — 停止时更新 skill 使用频率，驱动飞轮优化（含时间戳追踪） |
| skill-usage-tracker.py | python | 2.7KB | 88L | ⚠ | main | skill-usage-tracker.py — UserPromptSubmit|PostToolUse:Skill — 记录 skill 调用频率
Role: 无侵入 skill 使用率追踪 — 双路径: UserPromptSubmit + PostToolUse:Skill |
| stop-drain.py | python | 11.5KB | 319L |  | sanitize, classify, main | stop-drain.py — Stop — Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）

Role: Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层） |
| subagent-guard.py | python | 5.7KB | 179L | ⚠ | extract_fields, is_dangerous_type, main | subagent-guard.py — PreToolUse:Task — 约束子 agent 用量，防账单雪崩（软约束+事后对账）

Role: 约束子 agent 用量，防账单雪崩（软约束+事后对账）

R25 产品策略:
- Task 工具 schema 没有 max_turns 字段，AI 无法在 tool_input 合法传入。
- 三级 fallback: (1) tool_input |
| thinking-gate.py | python | 3.4KB | 109L | ⚠ | main | thinking-gate.py — UserPromptSubmit — 检测 thinking 内容残留
Role: 检测用户消息中是否包含 thinking/reasoning 内容残留 |
| token_writer.py | python | 8.7KB | 271L | ⚠ | auto_limit, detect_context_limit, get_increment, get_effective_incr, main | token_writer.py — PostToolUse:.* / SessionStart — 写入 token 用量追踪索引供 context-guard 计算
Role: 写入 token 用量追踪索引供 context-guard 计算
对应 token_writer.sh 的 Python 移植 |
| turn-counter.py | python | 21.4KB | 465L | ⚠ | main | turn-counter.py — UserPromptSubmit — 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测
Role: 统计会话轮次，定时注入 Todo 队列防漂移 + 模糊指令检测
对应 turn-counter.sh 的 Python 移植 |