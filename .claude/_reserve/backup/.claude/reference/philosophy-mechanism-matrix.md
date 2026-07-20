# 哲学-机制 完整追溯矩阵

> 生成: 2026-05-17 — 全量审计 7 条哲学 + 8 条铁律的一致性贯彻
> 更新: 2026-06-07 — feature-registry 哲学字段已覆盖 69/69 条目 (100%)
> 审计范围: 69 hooks + 24 skills + 28 scripts + 8 iron rules
> 
> 本文件是 **权威双向追溯矩阵**。正向（哲学→机制）和逆向（机制→哲学）均在本文档维护。
> AGENTS.md 和 philosophy.md 中的缩写版（~20 行）指向本文件。

---

## Part A: 正向追溯（哲学 → 机制）

### Philosophy #4 (最高优先级): 没通过验证等于没做

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `completion-gate.sh` | Hook | `.claude/hooks/completion-gate.sh` | 证据质量评分(E3)+E5 RCA硬阻断 | ✅ [已验证: .claude/scripts/harness-smoke-test.sh R34] |
| `pre-completion-gate.sh` | Hook | `.claude/hooks/pre-completion-gate.sh` | PreToolUse拦截无证据completed | ✅ |
| `posttool-completion-audit.sh` | Hook | `.claude/hooks/posttool-completion-audit.sh` | PostToolUse独立验证证据质量 | ✅ |
| `posttool-anti-pattern-detect.sh` | Hook | `.claude/hooks/posttool-anti-pattern-detect.sh` | A2虚假完成检测 | ✅ |
| `stop-drain.sh` | Hook | `.claude/hooks/stop-drain.sh` | Stop时兜底扫描补写错误记录 | ✅ |
| `harness-smoke-test.sh` | 脚本 | `.claude/scripts/harness-smoke-test.sh` | 回归验证(123/126动态计数) | ✅ |
| `audit-hooks.sh` | 脚本 | `.claude/scripts/audit-hooks.sh` | 三方一致性审计 | ✅ |
| `hook-production-verify.sh` | 脚本 | `.claude/scripts/hook-production-verify.sh` | 生产级端到端验证 | ✅ |
| `validate-skill.sh` | 脚本 | `.claude/scripts/validate-skill.sh` | Skill原子化合规校验(11项) | ✅ |
| `auto-score.sh` | 脚本 | `.claude/scripts/auto-score.sh` | 子维度独立客观评分+--calibrated校准 | ✅ |
| `score-self-check.sh` | 脚本 | `.claude/scripts/score-self-check.sh` | 评分方法论自检 | ✅ |
| `doc-sync-check.sh` | 脚本 | `.claude/scripts/doc-sync-check.sh` | 文档-代码一致性验证 | ✅ |
| Oracle 终审 | 节点 | AGENTS.md §Oracle | 独立agent源码级验证，不自证 | ✅ |
| Meta-Oracle | 节点 | AGENTS.md §Meta-Oracle | 最后守门员G1-G4触发 | ✅ |
| `lx-code-review` | Skill | `.claude/skills/lx-code-review/` | 代码审查 | ✅ |
| `lx-validate-skill` | Skill | `.claude/skills/lx-validate-skill/` | Skill验收(11条规则) | ✅ |
| `lx-root-cause-analysis` | Skill | `.claude/skills/lx-root-cause-analysis/` | 5-Why证据链 | ✅ |
| `lx-test-gen` | Skill | `.claude/skills/lx-test-gen/` | 测试代码生成 | ✅ |
| `lx-pre-commit` | Skill | `.claude/skills/lx-pre-commit/` | 提交前质量门禁 | ✅ |
| `lx-pre-push` | Skill | `.claude/skills/lx-pre-push/` | 推送前深度门禁 | ✅ |
| `lx-sync` | Skill | `.claude/skills/lx-sync/` | 变更后一致性检查 | ✅ |
| `feature-probe.sh` | 工具 | `.claude/scripts/feature-probe.sh` | L1-L4证据链完整性诊断 | ✅ |

**物化充足度**: ✅ 充分 — 10+ 直接机制，含 3 层防御纵深(PreToolUse截断→PostToolUse验证→Stop兜底)

---

### Philosophy #6: 先天对AI 0信任

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `posttool-claim-audit.sh` | Hook | `.claude/hooks/posttool-claim-audit.sh` | 铁律#1强制校验(file:line/G1数值断言) | ✅ |
| `edit-guard.sh` | Hook | `.claude/hooks/edit-guard.sh` | Read-before-Edit门禁 | ✅ |
| `permission-gate.sh` | Hook | `.claude/hooks/permission-gate.sh` | CAPTCHA+危险命令拦截 | ✅ |
| `pretool-sensitive-edit.sh` | Hook | `.claude/hooks/pretool-sensitive-edit.sh` | 治理文件CAPTCHA门禁 | ✅ |
| `meta-oracle-trigger.sh` | Hook | `.claude/hooks/meta-oracle-trigger.sh` | G1-G4触发检测 | ✅ |
| `posttool-anti-pattern-detect.sh` | Hook | `.claude/hooks/posttool-anti-pattern-detect.sh` | F1假设驱动/H1语义作弊 | ✅ |
| `posttool-bash-audit.sh` | Hook | `.claude/hooks/posttool-bash-audit.sh` | Bash执行后审计+E3/E4逃逸检测 | ✅ |
| `intent-tracker.sh` | Hook | `.claude/hooks/intent-tracker.sh` | 编辑统计+revert检测(变动追踪) | ✅ |
| ~~`pretool-ask-guard.sh`~~ | Hook | `.claude/hooks/pretool-ask-guard.sh` | 已移除 (2026-05-17) → 铁律#8 + meta-oracle-trigger | ✅ |
| `read-tracker.sh` | Hook | `.claude/hooks/read-tracker.sh` | 记录已读文件供edit-guard检查 | ✅ |
| Oracle 终审 | 节点 | AGENTS.md §Oracle | 独立agent最高权威裁决 | ✅ |
| Meta-Oracle | 节点 | AGENTS.md §Meta-Oracle | 独立二审+运行时验证 | ✅ |
| `meta-oracle-review.sh` | 脚本 | `.claude/scripts/meta-oracle-review.sh` | G1-G4审查执行 | ✅ |
| `escape-patch-apply.sh` | 脚本 | `.claude/scripts/escape-patch-apply.sh` | 所有补丁需人工/Oracle审核 | ✅ |
| `lx-varlock` | Skill | `.claude/skills/lx-varlock/` | 隐私脱敏代理 | ✅ |
| `ed-red-team-test.sh` | 脚本 | `.claude/scripts/ed-red-team-test.sh` | 11场景红队验证 | ✅ |

**物化充足度**: ✅ 充分 — 与#4并列最高覆盖密度

---

### Philosophy #3: 先守护，后激发

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `context-guard.sh` | Hook | `.claude/hooks/context-guard.sh` | 上下文阈值阻断防记忆衰退 | ✅ |
| `privacy-gate.sh` | Hook | `.claude/hooks/privacy-gate.sh` | DLP门禁(.env/私钥) | ✅ |
| `permission-gate.sh` | Hook | `.claude/hooks/permission-gate.sh` | 危险命令二级确认 | ✅ |
| `pretool-sensitive-edit.sh` | Hook | `.claude/hooks/pretool-sensitive-edit.sh` | 治理文件CAPTCHA | ✅ |
| `harness_config.sh` | 共享库 | `.claude/hooks/harness_config.sh` | hc_enabled统一门禁 | ✅ |
| `error-dna.sh` | Hook | `.claude/hooks/error-dna.sh` | E1/E2逃逸检测+高频告警 | ✅ |
| `subagent-guard.sh` | Hook | `.claude/hooks/subagent-guard.sh` | 子agent用量防账单雪崩 | ✅ |
| `posttool-subagent-audit.sh` | Hook | `.claude/hooks/posttool-subagent-audit.sh` | 子agent执行后审计 | ✅ |
| `pretool-retry-check.sh` | Hook | `.claude/hooks/pretool-retry-check.sh` | E4诊断门禁+3轮上限 | ✅ |
| `pretool-write-lock.sh` | Hook | `.claude/hooks/pretool-write-lock.sh` | OMA并发写锁 | ✅ |
| `posttool-write-lock.sh` | Hook | `.claude/hooks/posttool-write-lock.sh` | OMA并发解锁 | ✅ |
| `is_mode_active()` | 模式检测 | 各hook内联 | ghost/goal降级保护 | ✅ |
| `ecosystem-probe.sh` | Hook | `.claude/hooks/ecosystem-probe.sh` | 平台探测+行为调整 | ✅ |
| `session-health-check.sh` | 脚本 | `.claude/scripts/session-health-check.sh` | 会话健康监控 | ✅ |
| `pre-commit-self-review.sh` | 脚本 | `.claude/scripts/pre-commit-self-review.sh` | 提交前自检 | ✅ |
| `lx-goal` | Skill | `.claude/skills/lx-goal/` | 硬边界协议+三级裁决链 | ✅ |
| `lx-ghost` | Skill | `.claude/skills/lx-ghost/` | 方向驱动+风险记录 | ✅ |
| `lx-stepwise` | Skill | `.claude/skills/lx-stepwise/` | 逐步攻坚，每步验证 | ✅ |

**物化充足度**: ✅ 充分 — 几乎所有hook都含防御组件

---

### Philosophy #7: 文档优先，调研先行

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `inject-project-knowledge.sh` | Hook | `.claude/hooks/inject-project-knowledge.sh` | SessionStart核心知识注入 | ✅ |
| `plan-gate.sh` | Hook | `.claude/hooks/plan-gate.sh` | 编辑前检查是否跳过规划 | ⚠️默认关闭 |
| `knowledge-condenser.sh` | Hook | `.claude/hooks/knowledge-condenser.sh` | 高频模式扫描+升华建议 | ✅ |
| `ecosystem-probe.sh` | Hook | `.claude/hooks/ecosystem-probe.sh` | 环境探测→策略调整 | ✅ |
| `pretool-user-correction.sh` | Hook | `.claude/hooks/pretool-user-correction.sh` | 用户纠正信号强制记录 | ✅ |
| `posttool-handoff-writer.sh` | Hook | `.claude/hooks/posttool-handoff-writer.sh` | 每次Task完成后写handoff | ✅ |
| `auto-snapshot.sh` | Hook | `.claude/hooks/auto-snapshot.sh` | 会话状态快照持久化 | ✅ |
| `lx-oma-hier` | Skill | `.claude/skills/lx-oma-hier/` | PRD分层拆解 | ✅ |
| `lx-oma-split` | Skill | `.claude/skills/lx-oma-split/` | Feature MECE正交拆解 | ✅ |
| `lx-oma-orch` | Skill | `.claude/skills/lx-oma-orch/` | 管线原子化编排 | ✅ |
| `lx-oma-gov` | Skill | `.claude/skills/lx-oma-gov/` | PRD治理+冲突裁决+漂移检测 | ✅ |
| `lx-rpe` | Skill | `.claude/skills/lx-rpe/` | RPE文档体系完整生命周期 | ✅ |
| `lx-task-spec` | Skill | `.claude/skills/lx-task-spec/` | 任务驱动+精确AC | ✅ |
| `lx-dogfood` | Skill | `.claude/skills/lx-dogfood/` | 狗粮记录+教训提炼 | ✅ |
| `doc-sync-check.sh` | 脚本 | `.claude/scripts/doc-sync-check.sh` | 文档代码一致性 | ✅ |
| `task-workspace.sh` | 脚本 | `.claude/scripts/task-workspace.sh` | 任务持久化工作区 | ✅ |
| `snapshot-helper.sh` | 脚本 | `.claude/scripts/snapshot-helper.sh` | 非git环境快照 | ✅ |
| `pipeline-step.sh` | 脚本 | `.claude/scripts/pipeline-step.sh` | Pipeline步骤追踪 | ✅ |
| `lx-oma-gov-propagate.sh` | 脚本 | `.claude/scripts/lx-oma-gov-propagate.sh` | PRD增量传播 | ✅ |

**物化充足度**: ✅ 充分 — 但plan-gate默认关闭降低实际覆盖率

---

### Philosophy #5: 以人为本

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `posttool-format-gate.sh` | Hook | `.claude/hooks/posttool-format-gate.sh` | 输出格式方向感检查 | ✅ |
| `agentic-ui.sh` | 共享库 | `.claude/hooks/agentic-ui.sh` | 统一菜单/确认/CAPTCHA/状态 | ✅ |
| ~~`pretool-ask-guard.sh`~~ | Hook | `.claude/hooks/pretool-ask-guard.sh` | 已移除 (2026-05-17) → 铁律#8 + meta-oracle-trigger | ✅ |
| `fuzzy-block.sh` | Hook | `.claude/hooks/fuzzy-block.sh` | 模糊指令硬阻断 | ✅ |
| `pretool-user-correction.sh` | Hook | `.claude/hooks/pretool-user-correction.sh` | 用户纠正信号检测 | ✅ |
| `skill-usage-tracker.sh` | Hook | `.claude/hooks/skill-usage-tracker.sh` | 无侵入skill使用率追踪 | ✅ |
| `turn-counter.sh` | Hook | `.claude/hooks/turn-counter.sh` | 模糊指令检测(#5清晰度) | ✅ |
| `ecosystem-probe.sh` | Hook | `.claude/hooks/ecosystem-probe.sh` | 平台探测+软建议 | ✅ |
| `flywheel-report.sh` | Hook | `.claude/hooks/flywheel-report.sh` | 30天频率摘要注入会话 | ✅ |
| `lsp-suggest.sh` | Hook | `.claude/hooks/lsp-suggest.sh` | LSP工具推荐 | ✅ |
| `lx-status` | Skill | `.claude/skills/lx-status/` | 健康面板v3.0 | ✅ |
| `lx-todo` | Skill | `.claude/skills/lx-todo/` | 轻量todo工作流 | ✅ |
| `lx-oma-gov-resolve.sh` | 脚本 | `.claude/scripts/lx-oma-gov-resolve.sh` | L3冲突裁决人工参与 | ✅ |
| `lx-oma-gov-human-check.sh` | 脚本 | `.claude/scripts/lx-oma-gov-human-check.sh` | 人工验收清单 | ✅ |

**物化充足度**: ✅ 充分 — 已删除 proactive-handoff.sh (2026-05-19)

---

### Philosophy #2: 少量正确大增益

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `pretool-edit-scope.sh` | Hook | `.claude/hooks/pretool-edit-scope.sh` | 范围文件匹配+自动加入 | ✅ |
| `subagent-guard.sh` | Hook | `.claude/hooks/subagent-guard.sh` | 子agent用量约束 | ✅ |
| `posttool-subagent-audit.sh` | Hook | `.claude/hooks/posttool-subagent-audit.sh` | 资源用量超限告警 | ✅ |
| `pretool-retry-check.sh` | Hook | `.claude/hooks/pretool-retry-check.sh` | 3轮修复上限 | ✅ |
| `auto-scope.sh` | 脚本 | `.claude/scripts/auto-scope.sh` | 范围推导 | ✅ |
| `skill-flywheel.sh` | Hook | `.claude/hooks/skill-flywheel.sh` | 飞轮优化驱动 | ✅ |
| `knowledge-condenser.sh` | Hook | `.claude/hooks/knowledge-condenser.sh` | 模式升华建议 | ✅ |
| `lx-oma-split` | Skill | `.claude/skills/lx-oma-split/` | MECE正交Feature拆解 | ✅ |
| `lx-oma-hier` | Skill | `.claude/skills/lx-oma-hier/` | PRD分层拆解 | ✅ |
| `lx-task-spec` | Skill | `.claude/skills/lx-task-spec/` | 精确AC驱动分解 | ✅ |
| `lx-race` | Skill | `.claude/skills/lx-race/` | 并行处理同构任务 | ✅ |
| `lx-learner` | Skill | `.claude/skills/lx-learner/` | 从对话提取可重复工作流 | ✅ |
| `lx-skillify` | Skill | `.claude/skills/lx-skillify/` | 自然语言→生产级skill | ✅ |

**物化充足度**: ⚠️ 部分 — B1(过度工程)反模式仅有文档约定无hook检测
---

### Philosophy #1 (基础): The Less, The More

| 机制 | 类型 | 文件 | 物化方式 | 生效验证 |
|------|------|------|---------|---------|
| `turn-counter.sh` | Hook | `.claude/hooks/turn-counter.sh` | 轮次统计+Todo队列管理 | ✅ |
| `context-guard.sh` | Hook | `.claude/hooks/context-guard.sh` | 上下文阈值管理 | ✅ |
| `token_writer.sh` | Hook | `.claude/hooks/token_writer.sh` | Token用量追踪索引 | ✅ |
| `flywheel-report.sh` | Hook | `.claude/hooks/flywheel-report.sh` | 压缩30天摘要注入(非全量) | ✅ |
| `knowledge-condenser.sh` | Hook | `.claude/hooks/knowledge-condenser.sh` | 蒸馏升华建议 | ✅ |
| `auto-snapshot.sh` | Hook | `.claude/hooks/auto-snapshot.sh` | 压缩状态快照 | ✅ |
| `inject-project-knowledge.sh` | Hook | `.claude/hooks/inject-project-knowledge.sh` | R39注入预算控制 | ✅ |
| `skill-usage-tracker.sh` | Hook | `.claude/hooks/skill-usage-tracker.sh` | 无侵入追踪(零感知) | ✅ |
| `session_handoff` | 配置 | `.claude/harness.yaml:60-63` | max_adr_lines:10, max_todo_lines:10, max_lessons:3 | ✅ |
| `kernel.md 宪法冻结` | 规则 | `.claude/kernel.md:7-12` | 冻结后不可随意扩展 | ✅ |
| `lx-oma-orch` | Skill | `.claude/skills/lx-oma-orch/` | 管线原子化编排 | ✅ |
| `lx-goal/ghost` | Skill | `.claude/skills/lx-goal/`,`lx-ghost/` | 无人值守渐进执行 | ✅ |
| `proactive-handoff.sh` | Hook | ~~已删除 (2026-05-19)~~ | 上下文阈值交接(#5方向感) | ❌已删除 |

**物化充足度**: ✅ 充分 — 8+ 直接机制，R39注入预算主动控制

---

## Part B: 逆向追溯（机制 → 哲学）

### Hooks (43个 + 3个共享库/工具脚本)

| Hook | 哲学归属 | 铁律归属 | 生效 |
|------|---------|---------|------|
| `completion-gate.sh` | #4, #6 | #3(E) | ✅ |
| `pre-completion-gate.sh` | #4 | #3(E) | ✅ |
| `posttool-completion-audit.sh` | #4, #6 | #3(E) | ✅ |
| `context-guard.sh` | #3, #1 | — | ✅ |
| `permission-gate.sh` | #6, #3 | #1(A), #6(P) | ✅ |
| `privacy-gate.sh` | #3 | #6(P), #7(P) | ✅ |
| `edit-guard.sh` | #6 | #1(A) | ✅ |
| `pretool-sensitive-edit.sh` | #6, #3 | #1(A), #2(U) | ✅ |
| `pretool-edit-scope.sh` | #2 | #5(S) | ✅ |
| `posttool-format-gate.sh` | #5 | — | ✅ |
| `turn-counter.sh` | #1, #5 | — | ✅ |
| `inject-project-knowledge.sh` | #7, #1 | #8(P) | ✅ |
| `posttool-anti-pattern-detect.sh` | #6, #4 | #1(A), #3(E) | ✅ |
| `posttool-claim-audit.sh` | #6, #4 | #1(A), #7(T) | ✅ |
| `posttool-bash-audit.sh` | #6, #4 | #1(A) | ✅ |
| `posttool-subagent-audit.sh` | #2, #3 | — | ✅ |
| `subagent-guard.sh` | #2, #3 | #5(I) | ✅ |
| `pretool-retry-check.sh` | #3, #2 | #5(I) | ✅ |
| ~~`pretool-ask-guard.sh`~~ | #5, #6 | #8(P), #2(U) | 已移除 (2026-05-17) |
| `pretool-write-lock.sh` | #3 | — | ✅ |
| `posttool-write-lock.sh` | #3 | — | ✅ |
| `error-dna.sh` | #3, #6 | #1(A) | ✅ |
| `stop-drain.sh` | #4, #6 | #3(E) | ✅ |
| `fuzzy-block.sh` | #5, #4 | #2(U) | ✅ |
| `plan-gate.sh` | #7 | #5(S) | ⚠️默认关闭 |
| `meta-oracle-trigger.sh` | #4, #6 | #3(E), #8(P) | ✅ |
| `intent-tracker.sh` | #6 | — | ✅ |
| `token_writer.sh` | #1 | — | ✅ |
| `auto-snapshot.sh` | #7, #1 | #8(P) | ✅ |
| `skill-flywheel.sh` | #1, #2 | — | ✅ |
| `skill-usage-tracker.sh` | #5, #1 | — | ✅ |
| `ecosystem-probe.sh` | #7, #3 | #6(P) | ✅ |
| `flywheel-report.sh` | #1, #5 | — | ✅ |
| `knowledge-condenser.sh` | #1, #2, #7 | — | ✅ |
| `proactive-handoff.sh` | #1, #5, #7 | #8(P) | ❌已删除 |
| `read-tracker.sh` | #6 | #1(A) | ✅ |
| `pre-ask-guard.sh` | #5, #8 | #2(U) | ✅ — 问人前强制过决策链四层 |
| `pretool-user-correction.sh` | #5, #7 | #2(U) | ✅ |

| `posttool-write-cite.sh` | #7 | #1(A) | ✅ |
| `posttool-edit-quality.sh` | #6, #4 | — | ✅ |
| `posttool-handoff-writer.sh` | #7 | #3(E) | ✅ |
| `lsp-suggest.sh` | #2, #5 | — | ✅ |
| `feature-probe.sh` | #4, #7 | #3(E) | ✅(工具脚本) |
| `agentic-ui.sh` | #5 | — | ✅(共享库) |
| `harness_config.sh` | #3 | — | ✅(共享库) |

### Skills (24个)

| Skill | 哲学归属 | 铁律归属 |
|-------|---------|---------|
| `lx-goal` | #4, #2, #6, #3 | #2(U) |
| `lx-ghost` | #4, #3, #6 | — |
| `lx-pre-commit` | #3, #4 | #4(G) |
| `lx-pre-push` | #3, #4 | #4(G) |
| `lx-code-review` | #4, #6 | #1(A), #7(T) |
| `lx-rpe` | #7, #4 | #3(E), #8(P) |
| `lx-todo` | #2, #5 | #5(S) |
| `lx-root-cause-analysis` | #4, #7 | #7(T) |
| `lx-stepwise` | #3, #4 | #3(E) |
| `lx-race` | #2 | — |
| `lx-task-spec` | #2, #7 | #5(S) |
| `lx-test-gen` | #4 | — |
| `lx-validate-skill` | #4 | #3(E) |
| `lx-oma-split` | #2, #7 | #5(S) |
| `lx-oma-hier` | #7, #2 | #5(S) |
| `lx-oma-orch` | #7, #4 | #3(E) |
| `lx-oma-gov` | #7, #3 | — |
| `lx-status` | #5, #1 | — |
| `lx-sync` | #4, #7 | #8(I) |
| `lx-varlock` | #6 | #6(P) |
| `lx-dogfood` | #7, #4 | — |
| `lx-learner` | #2, #5 | — |
| `lx-skillify` | #2, #1 | — |
| `update-carror-os` | #3, #7 | — |

### Key Scripts (28个)

| Script | 哲学归属 | 铁律归属 |
|--------|---------|---------|
| `audit-hooks.sh` | #4 | #8(I) |
| `harness-smoke-test.sh` | #4 | — |
| `meta-oracle-review.sh` | #4, #6 | #3(E) |
| `pre-commit-self-review.sh` | #3, #6 | #8(I) |
| `auto-score.sh` | #4, #6 | #7(T) |
| `auto-scope.sh` | #2 | #5(S) |
| `hook-production-verify.sh` | #4 | — |
| `lx-goal.sh` | #3, #4, #6, #7 | #2(U) |
| `lx-ghost.sh` | #3, #4, #6 | — |
| `doc-sync-check.sh` | #7 | #1(A), #7(T) |
| `escape-patch-apply.sh` | #6 | — |
| `ed-red-team-test.sh` | #4, #6 | — |
| `retry-budget.sh` | #3 | #5(I) |
| `session-health-check.sh` | #3 | — |
| `score-self-check.sh` | #4, #6 | #7(T) |
| `pipeline-step.sh` | #7, #3 | — |
| `validate-skill.sh` | #4 | — |
| `race_manager.sh` | #2 | — |
| `snapshot-helper.sh` | #7, #4 | #4(G) |
| `lx-orch-gate.sh` | #4 | #3(E) |
| `lx-orch-advance.sh` | #7 | — |
| `lx-orch-status.sh` | #5 | — |
| `lx-oma-gov-resolve.sh` | #5 | — |
| `lx-oma-gov-propagate.sh` | #7 | — |
| `lx-oma-gov-human-check.sh` | #5 | #2(U) |
| `task-workspace.sh` | #7 | — |
| `test_race.sh` | #4 | — |
| `lx-unattended-toggle.sh` | — | —(已废弃) |

### Iron Rules Legend:
- A = AGENTS.md authoritative source
- I = index.md version only (may differ from AGENTS.md)
- P = present in both AGENTS.md and index.md
- U = 用户裁定 (#2 in AGENTS.md only)
- G = Git 门禁 (#4 AGENTS.md / #3 index.md)
- S = 范围冻结 (#5 AGENTS.md / #4 index.md)
- E = 证据门禁 (#3 AGENTS.md / #2 index.md)
- T = 断言真实 (#7 AGENTS.md only)
- P(phil) = 哲学先行 (#8 AGENTS.md only)

---

## Part C: 铁律→机制 正向追溯

### 铁律来源说明

> ⚠️ **CRITICAL发现**: index.md 和 source/harness-kit/AGENTS.md 的 8 条铁律编号不一致。
> 以下以 **AGENTS.md** 为权威源(source of truth)，并在差异处标注 index.md 版本。

| # (AGENTS.md) | 铁律 | index.md 对应 | 硬/软 | 物化机制 |
|---------------|------|-------------|-------|---------|
| 1 | **禁止编造** | #1(相同) | 硬 | posttool-claim-audit.sh, edit-guard.sh, posttool-anti-pattern-detect.sh, permission-gate.sh, pretool-sensitive-edit.sh |
| 2 | **用户裁定** | 缺失 | 硬 | pretool-sensitive-edit.sh(CAPTCHA), permission-gate.sh(CAPTCHA), lx-oma-gov-human-check.sh |
| 3 | **证据门禁** | #2 | 硬 | completion-gate.sh, pre-completion-gate.sh, posttool-completion-audit.sh, anti-pattern-detect(A2), stop-drain.sh |
| 4 | **Git门禁** | #3 | 软 | lx-pre-commit skill, lx-pre-push skill, snapshot-helper.sh |
| 5 | **范围冻结** | #4 | 软 | pretool-edit-scope.sh, plan-gate.sh(默认关闭), auto-scope.sh |
| 6 | **隐私防线** | #7 | 硬 | privacy-gate.sh, lx-varlock skill, ecosystem-probe.sh |
| 7 | **断言真实** | 缺失 | 硬 | posttool-claim-audit.sh(G1), posttool-anti-pattern-detect.sh(H1), auto-score.sh, doc-sync-check.sh |
| 8 | **哲学先行** | 缺失 | 硬+软 | posttool-handoff-writer.sh, meta-oracle-trigger.sh（pretool-ask-guard.sh 已于2026-05-17移除）|

**index.md 特有铁律**(AGENTS.md中不存在):
| # (index.md) | 铁律 | 对应AGENTS.md | 物化机制 |
|-------------|------|--------------|---------|
| 5 | 修复上限 | kernel.md §最大修复上限 | pretool-retry-check.sh, retry-budget.sh |
| 6 | 禁用词 | anti-patterns.md A2, G1 | posttool-anti-pattern-detect.sh, completion-gate.sh |
| 8 | 反自我矛盾 | kernel.md §禁止行为 | audit-hooks.sh, pre-commit-self-review.sh |

---

## Part D: 审计发现与建议

### D1: 关键发现

| # | 严重性 | 发现 | 建议 |
|---|--------|------|------|
| 1 | 🔴 CRITICAL | 铁律编号不一致 — index.md 与 AGENTS.md 定义不同的8条铁律 | 以 AGENTS.md 为权威源，同步 index.md |
| 2 | 🟡 MAJOR | 逆向追溯矩阵覆盖率仅 ~16% (16/99机制) | ✅ 本文档已修复 |
| 3 | 🟡 MAJOR | Skills 层无哲学声明 — SKILL.md 几乎从不提及哲学 | 建议：新增 skill 时在 SKILL.md 加哲学归属行 |
| 4 | ✅ RESOLVED | plan-gate.sh 默认关闭 (评估: 保持) + ~~proactive-handoff.sh~~ 已删除 (2026-05-19) |
| 5 | 🟢 MINOR | B1(过度工程)反模式仅有文档约定，无hook自动化检测 | 考虑在posttool-anti-pattern-detect.sh增加B1检测 |
| 6 | 🟢 MINOR | 交互原则(#5下属原则)无独立hook | 已由agentic-ui.sh+posttool-format-gate.sh覆盖，可接受 |

### D2: 哲学冲突裁决验证

> 完整验证：本次审计通过 3 个独立 agent 执行 6 场景冲突裁决验证。
> 结果：5/6 ✅PASS, 1/6 ⚠️PARTIAL(pretool-ask-guard模式匹配误报风险 — 该hook已于2026-05-17移除)。
> 验证数据来源：冲突裁决验证 agent (79 tool calls, 25 verification checks)

### D3: 无孤儿机制

审计确认: **所有 46 hooks + 25 skills + 28 scripts 均有合理的哲学归属。** 没有发现"有机制但哲学来源不明"的孤儿。
这验证了 `philosophy.md:42-43` 的声明: "每个机制必须可追溯到一个或多个哲学原则"。

### D4: 哲学物化评分

| 哲学 | 直接机制数 | 物化评分 | 备注 |
|------|----------|---------|------|
| #4 没验证=没做 | 22 | 9.5/10 | 最强物化，三层防御纵深 |
| #6 0信任 | 16 | 9.0/10 | 广泛覆盖 |
| #3 先守护 | 17 | 8.5/10 | 几乎所有hook含防御 |
| #7 文档优先 | 18 | 8.0/10 | plan-gate默认关闭扣分 |
| #5 以人为本 | 12 | 8.5/10 | proactive-handoff已删除，扣分项移除 |
| #2 少量大增益 | 13 | 7.5/10 | B1无自动化检测扣分 |
| #1 Less is More | 14 | 8.5/10 | R39注入预算主动控制 |

### D5: 验收条件逐项验证

- [x] 7条哲学每条有 >=1 个物化机制 — ✅ 最少13个(#2/#5), 最多22个(#4)
- [x] 所有主要机制有哲学归属 — ✅ 99个机制全部可追溯
- [x] 哲学冲突裁决测试 >=3个场景 — ✅ 6个场景验证
- [x] 完整矩阵文件存在且准确 — ✅ 本文档
- [ ] Oracle critic独立审核通过 — ⏳ 待执行
- [ ] harness-smoke-test.sh无回归 — ⏳ 待执行

### D6: 2026-06-07 同步验证 — feature-registry vs matrix 差异

**验证方式**: 逐行对比 `.claude/feature-registry.yaml`(69条目) 与 `.claude/reference/philosophy-mechanism-matrix.md` Part B Hooks 段。

| # | 严重性 | 发现 | 建议 |
|---|--------|------|------|
| 1 | 🟡 MAJOR | **27 个 registry hook 缺失于 matrix Part B** — 多数为 2026-06 新增：build-validator, context-compressor, error-dna-auto-fix, lsp-gate, meta-oracle-trigger-py, oma-lock, oracle-gate, posttool-checkpoint, posttool-read-cite, posttool-template-check, pre-edit-lsp-check, pretool-approve-detect, pretool-blast-radius, pretool-cruise-check, pretool-node-reference, pretool-oracle-gate/py, pretool-plan-gate, pretool-purify-gate, pretool-rules-inject, pretool-sensitive-file-guard, pretool-skill-version-guard, pretool-terminal-safety, session-resume, skill-body-enforce, skill-compliance-audit, thinking-gate | 将上述 27 条目补入 Part B Hooks 表 |
| 2 | 🟡 MAJOR | **30 处 philosophy 归属不一致** — 相同 hook 在 registry 和 matrix 中哲学字段不同 (详见表下方) | 逐一确认后统一两文件 |
| 3 | 🟢 MINOR | `plan-gate.sh` 存在于 matrix 但不在 registry (可能已被 `pretool-plan-gate` 替代) | 确认是否已更名，更新 matrix |
| 4 | 🟢 MINOR | Skills 段(24个) 和 Scripts 段(28个) 完全未出现在 feature-registry | 如需全量覆盖，考虑扩展 registry 范围 |

**philosophy 不一致明细**:
| Hook | registry | matrix |
|------|---------|-------|
| agentic-ui | #5, #7 | #5 |
| auto-snapshot | #3, #7 | #1, #7 |
| context-guard | #3 | #1, #3 |
| ecosystem-probe | #4, #7 | #3, #7 |
| edit-guard | #4, #6 | #6 |
| error-dna | #4, #6 | #3, #6 |
| flywheel-report | #1, #4 | #1, #5 |
| harness-config | #1, #3 | #3 |
| intent-tracker | #4, #6 | #6 |
| knowledge-condenser | #1, #4 | #1, #2, #7 |
| lsp-suggest | #5, #7 | #2, #5 |
| posttool-claim-audit | #1, #4, #6 | #4, #6 |
| posttool-edit-quality | #4, #5 | #4, #6 |
| posttool-format-gate | #5, #7 | #5 |
| posttool-handoff-writer | #5, #7 | #7 |
| posttool-subagent-audit | #4, #6 | #2, #3 |
| posttool-write-cite | #4, #7 | #7 |
| posttool-write-lock | #3, #6 | #3 |
| pre-ask-guard | #4, #5 | #5, #8 |
| pre-completion-gate | #4, #6 | #4 |
| pretool-edit-scope | #4, #6 | #2 |
| pretool-retry-check | #4, #6 | #2, #3 |
| pretool-user-correction | #4, #5 | #5, #7 |
| pretool-write-lock | #3, #6 | #3 |
| privacy-gate | #3, #6 | #3 |
| read-tracker | #1, #6 | #6 |
| skill-flywheel | #1, #7 | #1, #2 |
| skill-usage-tracker | #1, #4 | #1, #5 |
| subagent-guard | #3, #6 | #2, #3 |
| token-writer | #1, #4 | #1 |

---

## 维护约定

1. 新增机制时同步更新本文档 Part B 对应分类
2. 删除机制时移除本文档对应行
3. 哲学优先级变更时更新 Part A 物化充足度评估
4. 每季度对照 harness.yaml hooks_enabled 复审覆盖率
5. 新增 hook 时确保 feature-registry.yaml 和 matrix.md 同步更新
