# Research: Enhance → Base 全量差异分析

> **分析日期**: 2026-07-21
> **Base 版本**: v7.0.1 (`.claude/`)
> **Enhance 版本**: 冻结于 `.claude/_reserve/backup/`
> **分析方法**: 全量文件遍历 + 逐项对比 + 内容级 diff

---

## 1. 执行摘要

| 维度 | Base | Enhance | 差异 | 同步率 |
|------|------|---------|------|--------|
| Skills（活跃） | 14 | 22 | +8 (6 已合并, 2 新) | 93% 功能覆盖 |
| Skills（归档） | 3 | 0 (活跃) | +3 (有意归档) | — |
| Hooks | ~18 文件 | ~86 文件 | +68 | 21% |
| Scripts | ~49 文件 | ~137 文件 | +88 | 36% |
| Nodes | 14 活跃 | 16 活跃 + 6 decision/judgment | 完全同步 | 100% |
| Schemas | 12 | 12 | 完全同步 | 100% |
| Task System | 完整 | 完整 | 完全同步 | 100% |
| Profiles | ✅ | ✅ | 完全同步 | 100% |
| Workflow Standard | ✅ | ✅ (active) | 完全同步 | 100% |
| Signals | ✅ | ✅ | 完全同步 | 100% |
| Feature Registry | ✅ | ✅ (identical diff) | 完全同步 | 100% |
| 跨平台适配器 | 部分 (代码存在) | 完整 (6 平台) | 代码存在但未激活 | 75% |
| Decision/Judgment 节点 | ✅ | ✅ (identical diff) | 完全同步 | 100% |

**核心结论**: 基础设施层面 (nodes/schemas/task_sys/profiles/signals/registry) 已完全同步。真正差距集中在 **Hooks** (18 vs 86) 和 **Scripts** (49 vs 137)，以及少量 **Skills**。

---

## 2. Skills 差异详表

### 2.1 增强版专属（Base 缺失）

| # | 技能 | 功能 | ROI | 复杂度 | 建议 | 理由 |
|---|------|------|-----|--------|------|------|
| S1 | **update-carror-os** | 安装/升级 4 步闭环 (备份→安装→恢复→验证)，保护 AGENTS.md | 🔴 高 | 中 | ✅ **P0 迁移** | 运维必须技能 |
| S2 | **lx-status** | 健康面板 v3.0：Token 节省/任务通过率/ROI 仪表盘 | 🟡 中 | 简单 | ✅ **P1 迁移** | 用户已确认完整迁移 |
| S3 | **lx-test-gen** | 语言无关测试代码生成器 (Go/TS/Python 等) | 🟡 中 | 中 | ⏸ **P3 评估** | 需确认与 RPE TDD 步骤不重叠 |
| S4 | **lx-oracle-v2** | 已废弃 (自标记：合并到 lx-oracle v2.0) | ⚫ 零 | N/A | ❌ **Skip** | 已废弃，不可用 |
| S5 | **lx-oma-gov** | OMA PRD 治理 (已合并到 lx-oma subcommand:gov) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-oma 功能更优 |
| S6 | **lx-oma-hier** | PRD 分层拆解 (已合并到 lx-oma subcommand:hier) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-oma 功能更优 |
| S7 | **lx-oma-orch** | 管线编排 (已合并到 lx-oma subcommand:orch) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-oma 功能更优 |
| S8 | **lx-oma-split** | 特性拆解 (已合并到 lx-oma subcommand:split) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-oma 功能更优 |
| S9 | **lx-pre-commit** | 提交前门禁 (已合并到 lx-git-check subcommand:commit) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-git-check 功能更优 |
| S10 | **lx-pre-push** | 推送前门禁 (已合并到 lx-git-check subcommand:push) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-git-check 功能更优 |
| S11 | **lx-todo** | 轻量开发 (已合并到 lx-task-spec mode:light) | ⚫ 低 | N/A | ❌ **Skip** | Base lx-task-spec 功能等效 |

### 2.2 归档技能评估

| # | 技能 | Base 状态 | ROI | 建议 | 理由 |
|---|------|-----------|-----|------|------|
| A1 | **lx-purify** | 已归档 | 🟢 低 | ⏸ **P2 评估** | 低频思想审计。若无常规使用场景，保持归档 |
| A2 | **lx-sync** | 已归档 | 🟢 低 | ⏸ **P2 评估** | 变更后一致性检查。需确认与 lx-validate-skill R1-R11 不重叠 |
| A3 | **lx-race** | 已归档 | 🟢 低 | ❌ **Skip** | 并行模式已被 lx-goal 原生并行 Task 吸收 |

### 2.3 Base 架构优势 (Enhance 缺失)

| 技能 | 相对 Enhance 的优势 |
|------|-------------------|
| **lx-learn** | 统一 lx-learner + lx-skillify，新增 EDIT/MERGE/OPTIMIZE 三种模式 |
| **lx-git-check** | 合并 pre-commit + pre-push，自动项目类型检测 |
| **lx-oma** | 合并 hier/split/gov/orch 四技能，完全向后兼容 |

---

## 3. Hooks 差异详表

### 3.1 架构关键差异

| 特性 | Base | Enhance |
|------|------|---------|
| Hook 注册模式 | `hook-launcher.py` 统一分发 | 单个 hook 直接注册 settings.json |
| 核心门禁 | `pretool-gate.py` 单体 (7 功能合一) | 独立文件 (每功能一文件) |
| 共享库 | 无 | `harness_core.py` + `harness_lib.py` |

### 3.2 P0 必须迁移 (高 ROI + 核心安全/治理)

| # | Hook | 类别 | 事件 | 复杂度 | 理由 |
|---|------|------|------|--------|------|
| H1 | **permission-gate.py** | 安全 | PreToolUse:Bash | 高 (651行) | 阻断不安全 Bash 命令。Base pretool-gate 有内联版本但不够全面 |
| H2 | **privacy-gate.py** | 安全 | PreToolUse:Bash/Read/Grep | 中 | DLP 门禁：阻止凭据泄露 (.env/.pem/keys/tokens) |
| H3 | **context-guard.py** | 上下文 | PreToolUse:Edit/Write | 中 | 防止上下文溢出 (80-90% 水位阻断写入) |
| H4 | **pretool-blast-radius.py** | 安全 | PreToolUse:Bash | 低 | 检测 `rm -rf`/`git checkout .` 等破坏性命令 |
| H5 | **posttool-claim-audit.py** | 治理 | PostToolUse:Edit/Write | 中 | 铁律 #1：禁止编造代码事实，检测无 source 的数字断言 |
| H6 | **completion-gate.py** | 治理 | PostToolUse:TaskUpdate | 高 (438行) | 强制性证据文件 → VERIFIED 关键词 → TaskUpdate(completed) |
| H7 | **pre-completion-gate.py** | 治理 | PreToolUse:TaskUpdate | 中 | 提前阻止无证据的 TaskUpdate(completed) |
| H8 | **error-dna.py** | 可观测 | PostToolUse:Bash | 中 | Bash 错误捕获 → error-dna.jsonl 分类+频率追踪 |
| H9 | **error-dna-auto-fix.py** | 可观测 | Stop | 低 | 跨会话错误回顾，修复>1次的高频错误提升 |
| H10 | **token_writer.py** | 上下文 | PostToolUse:* + SessionStart | 中 | Token 使用追踪索引，为 context-guard 提供计算基础 |
| H11 | **turn-counter.py** | UX | UserPromptSubmit | 中 | 会话轮次追踪 + 漂移防护 |
| H12 | **session-resume.py** | 基础设施 | SessionStart | 中 | /compact 后任务状态恢复，扫描 token 目录 |

### 3.3 P1 迁移 (高 ROI + 质量/UX)

| # | Hook | 类别 | 事件 | 复杂度 | 理由 |
|---|------|------|------|--------|------|
| H13 | **pre-ask-guard.py** | UX | PreToolUse:AskUserQuestion | 中 | 从项目文档自动回答，减少人类中断 |
| H14 | **pretool-approve-detect.py** | 安全 | UserPromptSubmit | 中 | 完整的 /approve CAPTCHA token 流 |
| H15 | **posttool-bash-audit.py** | 可观测 | PostToolUse:Bash | 中 | Bash 权限上下文审计 + 逃逸检测 |
| H16 | **posttool-checkpoint.py** | UX | PostToolUse:TaskUpdate + Stop | 高 | 结构化会话摘要 (决策/todo/方向指引) |
| H17 | **pretool-write-lock.py (pre)** | 并发 | PreToolUse:Edit/Write | 中 | OMA 写前并发锁获取 |
| H18 | **pretool-write-lock.py (post)** | 并发 | PostToolUse:Edit/Write | 低 | OMA 写后锁释放 |
| H19 | **thinking-gate.py** | 治理 | UserPromptSubmit | 低 | 检测 thinking/reasoning 内容泄露 |
| H20 | **pretool-terminal-safety.py** | 安全 | PreToolUse:Bash | 低 | 硬阻断 >2000 字符命令，执行 bash-style 规则 |

### 3.4 P2 考虑 (中 ROI)

| # | Hook | 类别 | 理由 |
|---|------|------|------|
| H21 | **edit-guard.py** | 质量 | 写前检查是否已读，不需要复杂逻辑 |
| H22 | **meta-oracle-trigger.py** | 治理 | G1-G4 门检测 (414行)，双审核心但复杂 |
| H23 | **pretool-purify-gate.py** | 治理 | 编辑治理文件时注入哲学纯度提醒 |
| H24 | **skill-usage-tracker.py** | 可观测 | 非侵入性技能使用频率追踪 |
| H25 | **pretool-scope-gate.py** | 治理 | current-scope.txt 文件范围执行 |

### 3.5 Skip (低 ROI/已覆盖/过重)

共跳过 42 个低 ROI hook (完整列表见 executor.md 执行记录)：
- LSP 相关: lsp-gate, lsp-suggest, pre-edit-lsp-check
- 低影响: sessionstart-gate-check, build-validator, inject-project-knowledge, knowledge-condenser
- 与已选重叠: posttool-anti-pattern-detect (与 claim-audit 重叠), posttool-format-gate, posttool-output-compressor
- 存根/废弃: plan-gate.py (5行空存根)

### 3.6 迁移前置依赖

| 依赖 | 被依赖方 | 说明 |
|------|---------|------|
| `harness_core.py` | 核心库 | 高频函数 (line_count, b64encode 等) |
| `harness_lib.py` | 扩展库 | 所有 hook 的导入源 |
| `agentic-ui.py` | 工具模块 | 多 hook 使用的 UI 工具 |
| `read-tracker.py` | 读取追踪 | edit-guard 依赖 |

---

## 4. Scripts 差异详表

### 4.1 P1 迁移 (ROI 评分/可观测性 — 用户已确认完整迁移)

| # | 脚本 | 功能 | 复杂度 | 依赖 |
|---|------|------|--------|------|
| SC1 | **roi-score.py** | 核心 ROI 评分引擎 (0-100 分/组件) | 中 | roi-data.json |
| SC2 | **roi-collector.py** | 从 flywheel.log/error-dna/git 提取收益/成本指标 | 中 | flywheel.log, error-dna.jsonl |
| SC3 | **roi-evaluate.py** | 对所有机制做 Evidence/Impact/Philosophy 评估 + 淘汰建议 | 低 | 无 (独立) |
| SC4 | **score-ux.py** | UX 5 维度独立评分 (UX1-UX5) | 低 | 无 |
| SC5 | **auto-score.sh** | Meta-Oracle 4 维评分 (C/E/G/UX) shell 包装器 | 中 | meta-oracle-scorer.py |
| SC6 | **roi-dashboard.py** | ROI 面板渲染 (lx-status 调用) | 低 | roi-scores.json |

### 4.2 P1 迁移 (Oracle/Meta-Oracle — 双审系统核心)

| # | 脚本 | 功能 | 复杂度 |
|---|------|------|--------|
| SC7 | **meta-oracle-agent-spawn.py** | 生成 Meta-Oracle Agent 跨模型审查 | 中 |
| SC8 | **meta-oracle-scorer.py** | C/E/G/UX 4 维评分引擎 (105/110/50/10 子维度) | 高 |
| SC9 | **oracle-meta-handoff.py** | Oracle→Meta-Oracle 交接文档生成器 | 中 |

### 4.3 P1 迁移 (OMA 治理/编排)

| # | 脚本 | 功能 | 复杂度 |
|---|------|------|--------|
| SC10 | **lx-oma-gov-human-check.py** | 人工验收 checklist 运行器 | 低 |
| SC11 | **lx-oma-gov-propagate.py** | reconcile 变更增量传播到 prd/ | 中 |
| SC12 | **lx-oma-gov-resolve.py** | L3 冲突裁决 (accept/reject/defer) | 低 |
| SC13 | **lx-orch-advance.py** | 管线阶段推进 (hier→oma→gov→rpe→dev) | 中 |
| SC14 | **lx-orch-gate.py** | Oracle 门禁 approve/reject + 结构化记录 | 低 |

### 4.4 P1 迁移 (自主模式脚本)

| # | 脚本 | 功能 | 说明 |
|---|------|------|------|
| SC15 | **lx-goal.py** | Goal 模式 (on/off/status/poll/report) | Base 仅有 SKILL.md 无脚本 |
| SC16 | **lx-ghost.py** | Ghost 模式 (方向驱动自主探索) | Base 仅有 SKILL.md 无脚本 |
| SC17 | **lx-plan.py** | 任务文档系统 auto-create/update | P0 基础设施 |

### 4.5 P0/P1 迁移 (断链修复 + 验证)

| # | 脚本 | 功能 | 断链位置 |
|---|------|------|---------|
| SC18 | **validate_skill_refs.py** | Skill 引用完整性校验 (147行) | lx-learner SKILL.md:93-94 |
| SC19 | **validate-skill.py** | Skill 验证 wrapper (22行) | lx-skillify 依赖 |
| SC20 | **validate-skill.sh** | validate-skill.py 的 shell wrapper (17行) | lx-learner SKILL.md:93 |

### 4.6 P2 辅助工具

| # | 脚本 | 功能 | 复杂度 | 建议 |
|---|------|------|--------|------|
| SC21 | **add-skill-frontmatter.py** | 批量添加 role+execution_mode 到 SKILL.md (118行) | 低 | 一次性工具，保留备用 |
| SC22 | **add-skill-triggers.py** | 批量添加 triggers 字段 (83行) | 低 | 一次性工具，保留备用 |
| SC23 | **harness-smoke-test.py** | Hook harness 快速烟雾测试 | 中 | P3 延后 |
| SC24 | **flywheel_analytics.py** | 飞行轮日志分析 | 中 | P3 延后 |

### 4.7 Skip 脚本

- Race 引擎: race_manager.py, race_swarm.py, race-tool.py, test_race.py (与归档决策一致)
- 重型测试: tier4-e2e-test.py, deep-runtime-test.py, harness-full-test.py
- Node.js 依赖: meta-oracle-capability-score.js
- 与已选重叠: oma_propagate.py (与 lx-oma-gov-propagate.py 重复)

---

## 5. 断链发现 (临界问题)

### 5.1 lx-learner VALIDATE 阶段断链 ⚠️

**位置**: `lx-learner/SKILL.md` 第 93-94 行
```bash
bash .claude/scripts/validate-skill.sh lx-{name}
python3 .claude/scripts/validate_skill_refs.py
```

**现状**: 两个脚本均不存在于 base 的 `.claude/scripts/` 目录
**影响**: lx-learner VALIDATE 阶段静默失败，新生成的 skill 未经引用完整性校验
**修复**: 迁移 validate_skill_refs.py + validate-skill.py + validate-skill.sh → P0

### 5.2 lx-goal/lx-ghost 模式脚本缺失

**位置**: `lx-goal/SKILL.md` 和 `lx-ghost/SKILL.md` 引用了 `lx-goal.py`/`lx-ghost.py`
**现状**: 这些脚本在 Base 中不存在，仅有 SKILL.md 定义
**影响**: 自主模式的物理锁约束 (`.omc/tokens/`) 和信号机制无法执行
**修复**: 迁移 lx-goal.py + lx-ghost.py + lx-plan.py → P1

---

## 6. ROI 优先级矩阵

### P0 (立即修复 — 安全韧性 + 断链)
| Item | 类型 | 理由 |
|------|------|------|
| update-carror-os | Skill | 运维必须 |
| permission-gate.py | Hook | 安全底线 |
| privacy-gate.py | Hook | DLP 零容忍 |
| context-guard.py | Hook | 上下文防溢出 |
| pretool-blast-radius.py | Hook | 破坏性命令保护 |
| posttool-claim-audit.py | Hook | 铁律 #1 执行 |
| completion-gate.py + pre-completion-gate.py | Hook | 防虚假完成 |
| error-dna.py + error-dna-auto-fix.py | Hook | 错误可观测性 |
| token_writer.py + turn-counter.py | Hook | 会话状态追踪 |
| session-resume.py | Hook | /compact 恢复 |
| validate_skill_refs.py + validate-skill.py + validate-skill.sh | Script | lx-learner 断链修复 |
| harness_core.py + harness_lib.py | Script | Hook 共享库 (前置依赖) |

### P1 (迁移增强功能)
| Item | 类型 | 理由 |
|------|------|------|
| lx-status + roi-* 脚本 | Skill + Scripts | 用户确认完整迁移 |
| meta-oracle-scorer.py + auto-score.sh | Scripts | 双轨评分方法论 |
| meta-oracle-agent-spawn.py + oracle-meta-handoff.py | Scripts | 双审系统 |
| lx-oma-gov-* + lx-orch-* 脚本 | Scripts | OMA 管线可执行化 |
| lx-goal.py + lx-ghost.py + lx-plan.py | Scripts | 自主模式可执行化 |
| pre-ask-guard.py | Hook | UX 优化 |
| thinking-gate.py | Hook | 隐私防泄露 |
| pretool-terminal-safety.py | Hook | 终端安全规则执行 |
| edit-guard.py | Hook | 写前读检查 |
| pretool-write-lock.py (pre+post) | Hook | 并发保护 |

### P2 (评估决定)
| Item | 类型 | 理由 |
|------|------|------|
| lx-purify | Skill | 低频审计，如无使用场景保持归档 |
| lx-sync | Skill | 与 lx-validate-skill 可能重叠 |
| lx-test-gen | Skill | 与 RPE TDD 步骤可能重叠 |

### P3 (延后/低优先级)
| Item | 类型 | 理由 |
|------|------|------|
| cross-platform adapters 激活 | Infra | 已确认仅需 Claude Code + OpenCode |
| harness-smoke-test.py | Script | 需要迁移 hook 后才能运行 |
| flywheel_analytics.py | Script | 依赖 flywheel.log 数据积累 |
| add-skill-frontmatter.py / add-skill-triggers.py | Script | 一次性批量工具 |

---

## 7. 样本文件索引

| 文件 | 路径(Enhance) | 行数 |
|------|---------------|------|
| permission-gate.py | `.claude/_reserve/backup/.claude/hooks/` | 651 |
| completion-gate.py | `.claude/_reserve/backup/.claude/hooks/` | 438 |
| context-guard.py | `.claude/_reserve/backup/.claude/hooks/` | ~200 |
| harness_core.py | `.claude/_reserve/backup/.claude/hooks/` | 共享库 |
| harness_lib.py | `.claude/_reserve/backup/.claude/hooks/` | 共享库 |
| validate_skill_refs.py | `.claude/_reserve/backup/.claude/scripts/` | 147 |
| meta-oracle-scorer.py | `.claude/_reserve/backup/.claude/scripts/` | 高(~500+) |
| lx-goal.py | `.claude/_reserve/backup/.claude/scripts/` | ~200 |
| update-carror-os SKILL.md | `.claude/_reserve/backup/.claude/skills/update-carror-os/` | — |
| lx-status SKILL.md | `.claude/_reserve/backup/.claude/skills/lx-status/` | — |
