# Plan: Enhance → Base 选择性特性迁移

> **关联文档**: `research.md`（差异清单 + ROI 矩阵）
> **版本**: v1.2 (Oracle Re-review 修订)
> **日期**: 2026-07-21
> **修订**: 修复 C1 (hook 激活架构) + C2 (harness.yaml 格式) + C3 (P0/P1 hook 重复: posttool-bash-audit/posttool-checkpoint/terminal-safety)

---

## 1. 迁移策略

### 1.1 原则

| # | 原则 | 含义 |
|---|------|------|
| 1 | **Base 架构优先** | 已合并/简化的不倒退 (lx-oma/lx-git-check/lx-learn 保持) |
| 2 | **安全韧性 → 治理 → 可观测性 → 功能增强** | 按此优先级排序 |
| 3 | **文件级复制 + 双轨注册** | Hook 文件复制到 `.claude/hooks/`；settings.json 新增 PostToolUse/SessionStart/Stop 事件类型；PreToolUse 安全 hook 逻辑集成到 pretool-gate.py |
| 4 | **软锚点安全** | 迁移后的 hook 在 `harness.yaml` 的 `hooks_enabled:` 下默认设为 `false`，人工确认后再开启 |
| 5 | **不迁移过时/废弃/已吸收的** | lx-oracle-v2, lx-race, 拆分版 OMA/git/todo |

### 1.2 settings.json Hook 激活策略 (修复 C1)

**问题**: Base settings.json 仅注册 PreToolUse + UserPromptSubmit 两个事件 (2 entries)。迁移的 hook 需要 PostToolUse、SessionStart、Stop 等事件类型才能执行。

**方案**: 采用**双轨策略**：
- **PreToolUse 安全 hook** (permission-gate, privacy-gate, blast-radius, context-guard): 逻辑集成到现有 `pretool-gate.py` (1257行单体门禁)，保持 `hook-launcher.py` 分发模式。这避免重复检查 (如 pretool-gate 的 action-gate 段与独立 permission-gate.py 同时检查 Bash 命令)。
- **PostToolUse/SessionStart/Stop hook** (claim-audit, error-dna, token_writer, session-resume, completion-gate 等): settings.json 新增对应事件类型条目 + 直接注册。Base 完全缺少这些事件层，必须通过 settings.json 添加。
- **harness.yaml 格式**: 使用现有 `hooks_enabled: { hook_name: true/false }` 扁平布尔格式 (修复 C2)。

### 1.3 执行顺序理由

```
P0 (前置依赖) → P0 (安全hook) → P0 (治理hook) → P0 (可观测hook) → P0 (断链修复)
    ↓
P1 (Oracle/评分脚本) → P1 (自主模式脚本) → P1 (OMA脚本) → P1 (新Skills) → P1 (剩余hook/settings注册)
    ↓
P2 (评估项：人工决策)
    ↓
P3 (延后项：跳过记录)
```

**关键约束**：`harness_core.py` + `harness_lib.py` 必须在所有 hook 之前迁移（所有 hook 的 import 依赖）。

---

## 2. P0 执行计划（必须迁移 — 10 步骤）

### 步骤 0：前置依赖 — Hook 共享库

**操作**:
1. 从 enhance 复制 `harness_core.py` → base `.claude/hooks/harness_core.py`
2. 从 enhance 复制 `harness_lib.py` → base `.claude/hooks/harness_lib.py`
3. 从 enhance 复制 `agentic-ui.py` → base `.claude/hooks/agentic-ui.py`
4. 从 enhance 复制 `read-tracker.py` → base `.claude/hooks/read-tracker.py`

**验证**: `python3 -c "import sys; sys.path.insert(0, '.claude/hooks'); from harness_lib import *"` 无 ImportError

**AC**: 4 个文件存在且 Python 可导入

### 步骤 1：断链修复 — Skill 验证脚本

**操作**:
1. 复制 `validate_skill_refs.py` → `.claude/scripts/`
2. 复制 `validate-skill.py` → `.claude/scripts/`
3. 复制 `validate-skill.sh` → `.claude/scripts/`

**验证**: `python3 .claude/scripts/validate_skill_refs.py` 执行成功，输出 JSON

**AC**: lx-learner SKILL.md:93-94 的引用路径不再断链

### 步骤 2：PreToolUse 安全 Hook — 集成到 pretool-gate.py

**策略**: Base 的 pretool-gate.py 已有 7 段内联逻辑 (sensitive-edit, fallback-check, action-gate, plan-gate, edit-scope, verify-gate, oracle-gate)。将 enhance 的高 ROI PreToolUse 安全 hook **作为新段集成**到 pretool-gate.py 的执行链中，保持单体门禁架构。

**操作**:
1. 复制 `permission-gate.py` → `.claude/hooks/permission-gate.py` (保留独立文件作为参考)
2. 在 `pretool-gate.py` 的执行链中新增第 8 段 `permission-gate-ext` — 从 enhance permission-gate.py 提取核心危险命令检测逻辑 (rm -rf, DROP TABLE, git push --force 等)
3. 在 `harness.yaml` 的 `hooks_enabled:` 下确认 `permission_gate: true` 已存在 (base feature-registry 已注册)

**验证**: `python3 -m py_compile .claude/hooks/permission-gate.py`

**AC**: 文件存在 + 语法通过

### 步骤 3：PreToolUse 安全 Hook — privacy-gate.py + blast-radius + terminal-safety

**策略**: 同样集成到 pretool-gate.py 执行链。Privacy-gate 的 DLP 逻辑 (检测 .env/.pem/keys/tokens 访问) 和 blast-radius (检测 rm -rf/git checkout .) 作为新段添加。

**操作**:
1. 复制 `privacy-gate.py`, `pretool-blast-radius.py`, `pretool-terminal-safety.py` → `.claude/hooks/`
2. 在 `pretool-gate.py` 中集成 DLP 检测段 + 破坏性命令段 + 终端安全段
3. 在 `harness.yaml` 的 `hooks_enabled:` 下确认 `privacy_gate: true`, `blast_radius: true`, `terminal_safety: true` (base feature-registry 已注册)

**验证**: `python3 -m py_compile` 每个文件

**AC**: 3 个文件存在 + 语法通过

### 步骤 4：上下文 Hook — context-guard.py

**策略**: 上下文水位检测在 base feature-registry 已注册但实现文件缺失。作为独立 PreToolUse hook 注册到 pretool-gate.py 执行链。

**操作**:
1. 复制 `context-guard.py` → `.claude/hooks/`
2. 在 `pretool-gate.py` 集成上下文水位段 (50% 警告, 80% 硬阻断)
3. 在 `harness.yaml` 的 `hooks_enabled:` 下确认 `context_guard: true`

**验证**: `python3 -m py_compile .claude/hooks/context-guard.py`

**AC**: 文件存在 + 语法通过

### 步骤 5：上下文 Hook — token_writer.py + turn-counter.py

**策略**: token_writer 和 turn-counter 是 PostToolUse/UserPromptSubmit 事件类型 hook，base 完全缺少这些事件层 — 需要 settings.json 新增注册。

**操作**:
1. 复制 `token_writer.py`, `turn-counter.py` → `.claude/hooks/`
2. 在 settings.json 新增 PostToolUse 事件类型，注册 token_writer
3. 在 settings.json UserPromptSubmit 事件中追加 turn-counter
4. 在 `harness.yaml` 的 `hooks_enabled:` 下设置 `token_writer: false`, `turn_counter: false` (软锚点)

**验证**: `python3 -m py_compile` 每个文件

**AC**: 2 个文件存在 + 语法通过

### 步骤 6：PostToolUse 治理 Hook — completion-gate.py + pre-completion-gate.py + posttool-claim-audit.py

**策略**: 这些都是 PostToolUse 事件 hook — 通过 settings.json 新增事件注册激活。

**操作**:
1. 复制 `completion-gate.py`, `pre-completion-gate.py`, `posttool-claim-audit.py` → `.claude/hooks/`
2. 在 settings.json 的 PostToolUse 事件中注册 completion-gate (matcher: TaskUpdate) 和 claim-audit (matcher: Edit|Write)
3. pre-completion-gate 注册到 PreToolUse 事件 (matcher: TaskUpdate)
4. 在 `harness.yaml` 的 `hooks_enabled:` 下设置 `completion_gate: false`, `pre_completion_gate: false`, `claim_audit: false` (软锚点)

**验证**: `python3 -m py_compile` 每个文件

**AC**: 3 个文件存在 + 语法通过

### 步骤 7：PostToolUse 可观测 Hook — error-dna.py + posttool-bash-audit.py + posttool-checkpoint.py

**策略**: PostToolUse + Stop 事件 hook — 通过 settings.json 新增注册。

**操作**:
1. 复制 `error-dna.py`, `error-dna-auto-fix.py`, `posttool-bash-audit.py`, `posttool-checkpoint.py` → `.claude/hooks/`
2. 在 settings.json PostToolUse 事件中注册 error-dna + bash-audit (matcher: Bash)
3. 在 settings.json PostToolUse 事件中注册 checkpoint (matcher: TaskUpdate)
4. 在 settings.json 新增 Stop 事件类型，注册 error-dna-auto-fix
5. 在 settings.json 新增 SessionStart 事件类型，注册 session-resume + error-dna-auto-fix
6. 在 `harness.yaml` 的 `hooks_enabled:` 下设置相应条目为 `false`

**验证**: `python3 -m py_compile` 每个文件

**AC**: 4 个文件存在 + 语法通过

### 步骤 8：基础设施 Hook — session-resume.py

**策略**: SessionStart 事件 hook — 在步骤 7 中一并注册到 settings.json 新增的 SessionStart 事件。

**操作**:
1. 复制 `session-resume.py` → `.claude/hooks/`
2. 在 `harness.yaml` 的 `hooks_enabled:` 下设置 `session_resume: false`

**AC**: 文件存在 + 语法通过

### 步骤 9：技能 — update-carror-os

**操作**:
1. 复制 enhance `skills/update-carror-os/` (SKILL.md + scripts/ + references/) → base `.claude/skills/update-carror-os/`
2. 检查 SKILL.md 路径引用是否适配 base 目录结构
3. 在 `SKILLS.md` 和 `skill-dependencies.yaml` 中注册
4. 检查 `scripts/package-release.sh` 引用路径是否存在 (Oracle M2 反馈)

**AC**: `update-carror-os/SKILL.md` 节点/Schema 引用无断链

---

## 3. P1 执行计划（增强功能迁移 — 7 步骤）

### 步骤 12：ROI 评分脚本套件

**操作**:
1. 复制 `roi-score.py`, `roi-collector.py`, `roi-evaluate.py`, `roi-dashboard.py`, `score-ux.py` → `.claude/scripts/`
2. 复制 `auto-score.sh` → `.claude/scripts/`
3. 复制 `score-delta.py`, `score-self-check.sh`, `roi-rules-inject.py` → `.claude/scripts/`

**AC**: 脚本可独立执行 (python3 语法检查通过)

### 步骤 13：Oracle/Meta-Oracle 脚本

**操作**:
1. 复制 `meta-oracle-scorer.py` → `.claude/scripts/`
2. 复制 `meta-oracle-agent-spawn.py` + `meta-oracle-agent-spawn.sh` → `.claude/scripts/`
3. 复制 `oracle-meta-handoff.py` → `.claude/scripts/`

**AC**: 脚本存在，无 ImportError

### 步骤 14：自主模式脚本

**操作**:
1. 复制 `lx-goal.py` + `lx-goal.sh` → base `.claude/skills/lx-goal/scripts/`
2. 复制 `lx-ghost.py` + `lx-ghost.sh` → base `.claude/skills/lx-ghost/scripts/`
3. 复制 `lx-plan.py` → `.claude/scripts/`

**AC**: lx-goal/lx-ghost 的 SKILL.md 引用的脚本路径不再断链

### 步骤 15：OMA 治理/编排脚本

**操作**:
1. 复制 `lx-oma-gov-human-check.py`, `lx-oma-gov-propagate.py`, `lx-oma-gov-resolve.py` → `.claude/scripts/`
2. 复制 `lx-orch-advance.py`, `lx-orch-gate.py`, `lx-orch-status.py` → `.claude/scripts/`

**AC**: 脚本存在

### 步骤 16：lx-status 技能 + ROI 脚本绑定

**操作**:
1. 复制 enhance `skills/lx-status/` → base `.claude/skills/lx-status/`
2. **修复 Oracle M1**: 将 SKILL.md 的 `execution_mode: race` 改为 `execution_mode: stepwise` (lx-race 已归档，'race' 模式无运行时)
3. 检查 SKILL.md 对 roi-dashboard.py 的引用路径
4. 在 `SKILLS.md` 中注册

**AC**: `/lx-status` 可触发，ROI 面板渲染链路完整，execution_mode 正确

### 步骤 17：P1 级 Hook 迁移

**策略**: P1 hook 分为三类 — PreToolUse hook (集成到 pretool-gate.py 或者独立 PreToolUse 注册)、UserPromptSubmit hook (追加到现有事件)、PostToolUse hook (追加到步骤 5-7 已创建的 PostToolUse 注册条目)。

**操作**:
1. **PreToolUse P1**: 复制 `edit-guard.py`, `pretool-purify-gate.py`, `pretool-write-lock.py` (pre 版本) → `.claude/hooks/`；在 `pretool-gate.py` 执行链中集成对应新段 (edit-guard-ext, purify-gate-ext, write-lock-ext)。**注**: `pretool-terminal-safety.py` 已在 step 3 (P0) 集成，不重复。
2. **PostToolUse P1**: 复制 `pretool-write-lock.py` (post 版本) → `.claude/hooks/`；追加到 settings.json 现有 PostToolUse 注册条目 (matcher: Edit|Write)。**注**: `posttool-bash-audit.py` 和 `posttool-checkpoint.py` 已在 step 7 (P0) 处理，不重复。
3. **UserPromptSubmit P1**: 复制 `pre-ask-guard.py`, `thinking-gate.py`, `pretool-approve-detect.py` → `.claude/hooks/`；追加到 settings.json 现有 UserPromptSubmit 注册条目
4. 在 `harness.yaml` 的 `hooks_enabled:` 下设置所有 P1 hook 为 `false`

**验证**: `python3 -m py_compile` 每个文件

**AC**: 所有 P1 hook 文件存在 + 语法通过

### 步骤 18：Settings 适配 — 迁移 Hook 注册

**策略**: 分三类处理：
1. **settings.json**: 新增 PostToolUse、SessionStart、Stop 事件类型条目 (步骤 5-7 中已操作)。PreToolUse 安全 hook 通过 hook-launcher.py → pretool-gate.py 分发，无需新增 settings.json 条目。
2. **harness.yaml**: 在 `hooks_enabled:` 下添加所有 P0+P1 hook 的布尔开关 (默认 `false`)
3. **feature-registry.yaml**: 添加所有新 hook 的注册条目

**操作**:
1. 在 `harness.yaml` 的 `hooks_enabled:` 下逐项添加:
   - `permission_gate: true`, `privacy_gate: true`, `blast_radius: true`, `terminal_safety: true`, `context_guard: true` (P0 安全hook，已在 base registry 注册)
   - `token_writer: false`, `turn_counter: false` (P0 上下文hook，软锚点)
   - `completion_gate: false`, `pre_completion_gate: false`, `claim_audit: false` (P0 治理hook，软锚点)
   - `error_dna: false`, `bash_audit: false`, `checkpoint: false` (P0 可观测hook，软锚点)
   - `session_resume: false` (P0 基础设施hook，软锚点)
   - `edit_guard: false`, `purify_gate: false`, `write_lock: false`, `pre_ask_guard: false`, `thinking_gate: false`, `approve_detect: false` (P1 hook，软锚点)
2. 在 `feature-registry.yaml` 添加所有新 hook 的注册条目
3. 不修改 `settings.json` 的 PreToolUse hook 注册模式 (保持 hook-launcher.py 分发)；仅新增 PostToolUse/SessionStart/Stop 事件条目

**AC**: `harness.yaml` 和 `feature-registry.yaml` 包含所有新 hook 条目；settings.json 包含新增事件类型

---

## 4. P2 评估计划（需 AI 自决 / 人工决策）

| Item | 评估问题 | 决策条件 |
|------|---------|---------|
| lx-purify | 思想审计是否仍有使用场景？ | 若最近 30 天无使用需求 → 保持归档 |
| lx-sync | 变更后一致性检查与 lx-validate-skill R1-R11 是否重叠？ | 读取两者的检查项列表，若有 ≥50% 重叠 → 保持归档 |
| lx-test-gen | 测试生成与 RPE TDD 步骤是否重叠？ | 读取 lx-rpe SKILL.md Phase 3，若 TDD 步骤已覆盖语言无关测试生成 → Skip |

---

## 5. P3 延后项

| Item | 延后原因 | 触发条件 |
|------|---------|---------|
| Cross-platform 激活 | 当前仅用 Claude Code，代码已存在于 `.hooks/` | 添加 OpenCode 等第二平台时 |
| harness-smoke-test.py | 依赖 hook 迁移完成后才能运行 | P0/P1 全部完成后 |
| flywheel_analytics.py | 依赖 flywheel.log 数据积累 | flywheel.log ≥30 天数据时 |
| add-skill-frontmatter.py | 一次性批量工具 | 新增大批 skill 时 |
| add-skill-triggers.py | 一次性批量工具 | 新增大批 skill 时 |
| meta-oracle-trigger.py | 复杂 (414行)，需与现有 Oracle 门禁集成测试 | Oracle 脚本迁移完成后 |

---

## 6. 依赖拓扑

```
harness_core.py + harness_lib.py  ←── [前置依赖]
         │
         ├── P0 hooks (步骤2-8) ←── 所有依赖共享库
         │
         ├── P1 hooks (步骤17)
         │
validate_skill_refs.py  ←── [步骤1: 断链修复]
         │
         └── lx-learner VALIDATE 阶段恢复
         
lx-goal.py + lx-ghost.py  ←── [步骤14: 自主模式]
         │
         └── lx-goal/lx-ghost SKILL.md 断链修复

roi-* scripts  ←── [步骤12]
         │
         └── lx-status (步骤16) 依赖 roi-dashboard.py

update-carror-os  ←── [步骤9: 独立步骤]

scripts → harness.yaml → feature-registry.yaml  ←── [步骤18: 最终注册]
```

---

## 7. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Hook 共享库与 base Python 版本不兼容 | 低 | 中 | 语法检查 + 静态导入测试 |
| 复制的 hook 引用了 enhance 独有的 harness.yaml 键 | 中 | 低 | 只做文件复制，不激活 (enabled: false) |
| settings.json 新增事件类型注册冲突 | 中 | 中 | PostToolUse/SessionStart/Stop 为新增事件类型，与现有 PreToolUse/UserPromptSubmit 无冲突；保留 hook-launcher.py 分发模式兼容 |
| lx-status 对不存在的 roi-* 数据的依赖 | 低 | 低 | roi 脚本独立于 hook 运行，fallback 到 "no data" |
| 文件路径硬编码 | 中 | 中 | 每个迁移文件检查 `__file__` / `os.path` 相对路径 |

---

## 8. 回滚策略

**文件级回滚**：每个迁移的 hook/script/skill 是独立文件，回滚只需删除对应文件
**注册回滚**：harness.yaml/feature-registry.yaml/settings.json 的修改可通过 `git diff -- harness.yaml feature-registry.yaml settings.json` 查看并 revert
**验证方式**: 每个步骤完成后运行一次验证检查

---

## 9. 成功标准

- [x] 所有 P0 hook 文件存在于 `.claude/hooks/`
- [x] `validate_skill_refs.py` 可执行且输出有效 JSON
- [x] lx-learner VALIDATE 阶段不再断链
- [x] lx-goal.py + lx-ghost.py 存在且可导入
- [x] lx-status + ROI 脚本链路完整
- [x] update-carror-os skill 注册成功
- [x] harness.yaml 包含所有新 hook 的 enabled 开关
- [x] feature-registry.yaml 包含所有新 hook 条目
- [ ] `python3 .claude/scripts/validate_skill_refs.py` 返回 passed: true
