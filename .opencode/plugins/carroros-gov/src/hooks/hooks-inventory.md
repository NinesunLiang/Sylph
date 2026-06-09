# Carror OS Hooks 目录摸底清单

> 生成: 2026-06-07
> 范围: `.claude/hooks/` + `.claude/workflow-standard/hooks/`
> 用途: 全平台 Python 化进度追踪

---

## 图例

| 标记 | 含义 |
|------|------|
| ✅ 已 Python 化 | .py 文件已存在且在 settings.json 中注册 |
| ❌ 仅 .sh 需移植 | 仅 .sh 文件，无 .py 孪生，需手工移植 |
| 📎 辅助脚本 | 被 source/import 引用，非直接注册的 hook |
| ⚠️ 废弃残留 | settings.json 不引用，其他脚本也不调用 |
| 🔷 工作流标准 | workflow-standard/hooks/ 下的注册脚本 |

---

## 1️⃣ Hook 分类摸底总表

### 1.1 ✅ 已 Python 化（.py 注册，.sh 孪生已删）

共 **17 个** .py 文件已在 settings.json 中注册，对应 .sh 孪生已清理：

| .py Hook | 行数 | 注册位置 |
|----------|------|----------|
| `context-guard.py` | 228 | PreToolUse:Edit\|Write |
| `edit-guard.py` | 125 | PreToolUse:Edit\|Write |
| `fuzzy-block.py` | 99 | PreToolUse:.* |
| `harness_lib.py` | 270 | 📎 共享库(被 import) |
| `lsp-suggest.py` | 132 | PreToolUse:Grep |
| `meta-oracle-trigger.py` | 414 | PostToolUse:.* |
| `permission-gate.py` | 651 | PreToolUse:Bash |
| `posttool-output-compressor.py` | 281 | ⚠️ 未注册(游离) |
| `pre-ask-guard.py` | 205 | PreToolUse:AskUserQuestion |
| `pre-completion-gate.py` | 130 | PreToolUse:TaskUpdate |
| `pretool-edit-scope.py` | 436 | PreToolUse:Edit\|Write |
| `pretool-oracle-gate.py` | 277 | PreToolUse:Edit\|Write |
| `pretool-plan-gate.py` | 296 | PreToolUse:Edit\|Write\|Bash |
| `pretool-retry-check.py` | 326 | PreToolUse:Bash |
| `pretool-sensitive-edit.py` | 303 | PreToolUse:Edit\|Write\|Bash |
| `privacy-gate.py` | 145 | PreToolUse:Bash\|Read\|Grep |
| `subagent-guard.py` | 178 | PreToolUse:Task |

> **注**: `posttool-output-compressor.py` 虽已 .py 化但未在 settings.json 注册，为游离态。
> `harness_lib.py` 是共享库，被其他 .py hooks `from harness_lib import ...` 引用。

---

### 1.2 ❌ 仅 .sh 需移植（无 .py 孪生，在 settings.json 中注册）

共 **25 个** .sh hook 需移植到 Python：

| # | .sh Hook | 行数 | 复杂度 | 注册位置(Event:Matcher) | 备注 |
|---|----------|------|--------|------------------------|------|
| 1 | `auto-snapshot.sh` | 532 | 🔴 复杂 | Stop / PostToolUse:Edit\|Write | 多函数+jq+跨平台mtime |
| 2 | `build-validator.sh` | 343 | 🔴 复杂 | PostToolUse:Bash / PostToolUseFailure:Bash | jq/json处理,多函数 |
| 3 | `completion-gate.sh` | 438 | 🔴 复杂 | PostToolUse:TaskUpdate | source agentic-ui.sh, jq+python |
| 4 | `context-compressor.sh` | 108 | 🟡 中等 | SessionStart | 文件拼接+缓存逻辑 |
| 5 | `cross-platform-smoke-test.sh` | 59 | 🟢 简单 | SessionStart | 纯检测逻辑 |
| 6 | `ecosystem-probe.sh` | 197 | 🟡 中等 | SessionStart | 多平台检测 |
| 7 | `error-dna-auto-fix.sh` | 63 | 🟢 简单 | Stop | python heredoc调用 |
| 8 | `error-dna.sh` | 538 | 🔴 复杂 | PostToolUse:Bash / PostToolUseFailure:Bash | jq+多函数+高频告警 |
| 9 | `flywheel-report.sh` | 159 | 🟡 中等 | SessionStart | 文件读取+日期窗口 |
| 10 | `inject-project-knowledge.sh` | 84 | 🟢 简单 | SessionStart | 文件存在检查+cat |
| 11 | `intent-tracker.sh` | 202 | 🟡 中等 | PostToolUse:Edit\|Write | python heredoc+文件追踪 |
| 12 | `knowledge-condenser.sh` | 211 | 🟡 中等 | Stop | python heredoc+sublimation |
| 13 | `lsp-gate.sh` | 31 | 🟢 简单 | SessionStart | 纯检测+echo |
| 14 | `oracle-gate.sh` | 33 | 🟢 简单 | SessionStart | command检测 |
| 15 | `phase-state-tracker.sh` | 162 | 🟡 中等 | PostToolUse:TaskUpdate\|Edit\|Write | Git检测+状态机 |
| 16 | `posttool-anti-pattern-detect.sh` | 129 | 🟡 中等 | PostToolUse:TaskUpdate\|Edit\|Write | 语义检测 |
| 17 | `posttool-bash-audit.sh` | 298 | 🟡 中等 | PostToolUse:Bash / PostToolUseFailure:Bash | jq+命令审计 |
| 18 | `posttool-checkpoint.sh` | 140 | 🟡 中等 | PostToolUse:TaskUpdate / Stop | python heredoc |
| 19 | `posttool-claim-audit.sh` | 218 | 🟡 中等 | PostToolUse:Edit\|Write | 断言检测 |
| 20 | `posttool-completion-audit.sh` | 137 | 🟡 中等 | PostToolUse:TaskUpdate | python heredoc+证据检查 |
| 21 | `posttool-edit-quality.sh` | 214 | 🟡 中等 | PostToolUse:Edit\|Write | jq+质量检查 |
| 22 | `posttool-format-gate.sh` | 73 | 🟢 简单 | PostToolUse:TaskUpdate\|Edit\|Write | 格式检查 |
| 23 | `posttool-handoff-writer.sh` | 154 | 🟡 中等 | PostToolUse:TaskUpdate | python heredoc |
| 24 | `posttool-read-cite.sh` | 66 | 🟢 简单 | PostToolUse:Read | jq/python fallback+echo |
| 25 | `pretool-approve-detect.sh` | 84 | 🟢 简单 | UserPromptSubmit:.* | 文件名匹配+文件操作 |

---

### 1.3 ❌ 仅 .sh 需移植（无 .py 孪生，在 settings.json 中注册）— 续

| # | .sh Hook | 行数 | 复杂度 | 注册位置(Event:Matcher) | 备注 |
|---|----------|------|--------|------------------------|------|
| 26 | `pretool-b1-detect.sh` | 106 | 🟡 中等 | PreToolUse:Edit\|Write | 文件计数+模式检测 |
| 27 | `pretool-blast-radius.sh` | 63 | 🟢 简单 | PreToolUse:Bash | 命令字符串匹配 |
| 28 | `pretool-cruise-check.sh` | 44 | 🟢 简单 | SessionStart | mode检测 |
| 29 | `pretool-git-gate.sh` | 85 | 🟢 简单 | PreToolUse:Bash | source agentic-ui.sh,命令检测 |
| 30 | `pretool-node-reference.sh` | 12 | 🟢 简单 | PreToolUse:Agent | python一行+echo |
| 31 | `pretool-purify-gate.sh` | 26 | 🟢 简单 | PreToolUse:Edit\|Write | case匹配+echo |
| 32 | `pretool-rules-inject.sh` | 150 | 🟡 中等 | UserPromptSubmit:.* | 分层注入逻辑 |
| 33 | `pretool-scope-gate.sh` | 152 | 🟡 中等 | PreToolUse:Edit\|Write | git+范围检查 |
| 34 | `pretool-sensitive-file-guard.sh` | 64 | 🟢 简单 | PreToolUse:Edit\|Write | 文件名匹配 |
| 35 | `pretool-skill-body-enforce.sh` | 87 | 🟢 简单 | PreToolUse:Skill | jq+文件读取 |
| 36 | `pretool-skill-version-guard.sh` | 88 | 🟢 简单 | PreToolUse:Edit\|Write | python heredoc |
| 37 | `pretool-terminal-safety.sh` | 71 | 🟢 简单 | PreToolUse:Bash | 命令校验 |
| 38 | `pretool-user-correction.sh` | 104 | 🟡 中等 | UserPromptSubmit | 信号词检测 |
| 39 | `pretool-write-lock.sh` | 79 | 🟢 简单 | PreToolUse:Edit\|Write | 锁文件检查 |
| 40 | `read-tracker.sh` | 62 | 🟢 简单 | PostToolUse:Read | 文件追踪 |
| 41 | `session-resume.sh` | 154 | 🟡 中等 | SessionStart | python heredoc+多模式 |
| 42 | `sessionstart-gate-check.sh` | 61 | 🟢 简单 | SessionStart | harness.yaml读取 |
| 43 | `skill-flywheel.sh` | 76 | 🟢 简单 | Stop | 文件追加 |
| 44 | `skill-usage-tracker.sh` | 44 | 🟢 简单 | PostToolUse:Skill / UserPromptSubmit | 日志追加 |
| 45 | `stop-drain.sh` | 231 | 🟡 中等 | Stop | jq+python heredoc+transcript扫描 |
| 46 | `thinking-gate.sh` | 62 | 🟢 简单 | UserPromptSubmit:.* | 文件检测+flywheel |
| 47 | `token_writer.sh` | 291 | 🟡 中等 | PostToolUse:.* / SessionStart | 多路径注册 |
| 48 | `turn-counter.sh` | 344 | 🔴 复杂 | UserPromptSubmit | jq+多文件状态追踪 |
| 49 | `posttool-skill-compliance.sh` | 112 | 🟡 中等 | PostToolUse:Skill | jq+skill合规检查 |
| 50 | `posttool-subagent-audit.sh` | 89 | 🟢 简单 | PostToolUse:Task\|Agent |
| 51 | `posttool-template-check.sh` | 10 | 🟢 简单 | PostToolUse:TaskUpdate\|Edit\|Write |
| 52 | `posttool-write-cite.sh` | 89 | 🟢 简单 | PostToolUse:Edit\|Write |
| 53 | `posttool-write-lock.sh` | 45 | 🟢 简单 | PostToolUse:Edit\|Write |
| 54 | `pre-edit-lsp-check.sh` | 90 | 🟢 简单 | PreToolUse:Edit | LSP诊断注入 |
| 55 | `permission-frequency-tracker.sh` | 101 | 🟡 中等 | PostToolUse:.* | 频率统计 |
| 56 | `posttool-edit-quality.sh` | 214 | 🟡 中等 | PostToolUse:Edit\|Write | **(已在1.2#21列出, 行数确认)** |
| 57 | `sessionstart-workflow-inject.sh` | 125 | 🟡 中等 | 未注册(游离) | 旧工作流hook |
| 58 | `workflow-state-recovery.sh` | 125 | 🟡 中等 | 未注册(游离) | 旧工作流hook |
| 59 | `posttool-workflow-checkpoint.sh` | 87 | 🟢 简单 | 未注册(游离) | 旧工作流hook |
| 60 | `pretool-workflow-gate.sh` | 148 | 🟡 中等 | 未注册(游离) | 旧工作流hook |

> **注**: `sessionstart-workflow-inject.sh`, `workflow-state-recovery.sh`, `posttool-workflow-checkpoint.sh`, `pretool-workflow-gate.sh` 这4个旧工作流hook在settings.json中未被直接注册，但检查是否被外部引用...

---

### 1.4 🔷 工作流标准 hooks（workflow-standard/hooks/）

| 文件 | 行数 | 复杂度 | 注册位置 | 备注 |
|------|------|--------|----------|------|
| `checkpoint` | 45 | 🟢 简单 | PostToolUse:TaskUpdate | 无后缀名，bash shebang |
| `pretool-workflow-gate` | 62 | 🟢 简单 | PreToolUse:Edit\|Write\|Bash | 无后缀名，bash shebang |
| `session-inject` | 64 | 🟢 简单 | SessionStart | 无后缀名，bash shebang |
| `state-recovery` | 79 | 🟢 简单 | SessionStart | 无后缀名，bash shebang |

这4个也需 Python 化，较简单，可优先处理。

---

### 1.5 📎 辅助脚本（被 source/import，非直接注册）

| 文件 | 行数 | 类型 | 引用者 |
|------|------|------|--------|
| `harness_config.sh` | 805 | 🟡 共享库(.sh) | 被几乎所有 .sh hook 通过 `source harness_config.sh` 引用 |
| `harness_lib.py` | 270 | ✅ 已 Python 化 | 被 .py hooks 通过 `from harness_lib import ...` 引用 |
| `agentic-ui.sh` | 177 | 🟡 共享库(.sh) | 被 `completion-gate.sh`, `pretool-git-gate.sh` source |

> **关键依赖**: `harness_config.sh` 是最核心的共享库(805行)，提供 hc_get/hc_enabled 等基础函数。
> 移植时需保留其功能，或由 Python 的 `harness_lib.py` 替代。
> `agentic-ui.sh` 提供 UI 输出函数，被 2 个 .sh hook source。

---

### 1.6 ⚠️ 废弃/游离（settings.json 未注册，未被 source/import）

| 文件 | 行数 | 说明 |
|------|------|------|
| `sessionstart-workflow-inject.sh` | 125 | 旧工作流系统，未被注册 |
| `workflow-state-recovery.sh` | 125 | 旧工作流系统，未被注册 |
| `posttool-workflow-checkpoint.sh` | 87 | 旧工作流系统，未被注册 |
| `pretool-workflow-gate.sh` | 148 | 旧工作流系统，未被注册 |
| `posttool-output-compressor.py` | 281 | .py 已写但未注册，游离态 |

> 这 4 个旧工作流 .sh 文件未被 settings.json 注册，且 `workflow-standard/hooks/` 下有替代实现。
> **建议**: 确认旧工作流已完全废弃后，可删除。

---

## 2️⃣ 复杂度分级统计

| 复杂度 | 数量 | 说明 |
|--------|------|------|
| 🔴 复杂(>150行,多函数/jq/json/subprocess) | **5** | auto-snapshot(532), build-validator(343), completion-gate(438), error-dna(538), turn-counter(344) |
| 🟡 中等(50-150行,含条件分支) | **23** | context-compressor, ecosystem-probe, flywheel-report, intent-tracker, knowledge-condenser, phase-state-tracker, posttool-anti-pattern-detect, posttool-bash-audit, posttool-checkpoint, posttool-claim-audit, posttool-completion-audit, posttool-edit-quality, posttool-handoff-writer, posttool-skill-compliance, pretool-b1-detect, pretool-rules-inject, pretool-scope-gate, pretool-user-correction, session-resume, stop-drain, token_writer, permission-frequency-tracker, harness_config(805共享库) |
| 🟢 简单(<50行,简单逻辑) | **28** | 剩余全部 |

---

## 3️⃣ settings.json 中已切 .py 但仍有 .sh 残留的对照

**此前已删除 16 个双激活 .sh 孪生文件**（对照 `twin-sh-analysis.md`），当前确认：

| 曾有的 .sh 孪生 | 对应 .py | 状态 |
|------------------|----------|------|
| ~~context-guard.sh~~ | `context-guard.py` | ✅ 已删 |
| ~~edit-guard.sh~~ | `edit-guard.py` | ✅ 已删 |
| ~~fuzzy-block.sh~~ | `fuzzy-block.py` | ✅ 已删 |
| ~~lsp-suggest.sh~~ | `lsp-suggest.py` | ✅ 已删 |
| ~~meta-oracle-trigger.sh~~ | `meta-oracle-trigger.py` | ✅ 已删 |
| ~~permission-gate.sh~~ | `permission-gate.py` | ✅ 已删 |
| ~~pre-ask-guard.sh~~ | `pre-ask-guard.py` | ✅ 已删 |
| ~~pre-completion-gate.sh~~ | `pre-completion-gate.py` | ✅ 已删 |
| ~~pretool-edit-scope.sh~~ | `pretool-edit-scope.py` | ✅ 已删 |
| ~~pretool-oracle-gate.sh~~ | `pretool-oracle-gate.py` | ✅ 已删 |
| ~~pretool-plan-gate.sh~~ | `pretool-plan-gate.py` | ✅ 已删 |
| ~~pretool-sensitive-edit.sh~~ | `pretool-sensitive-edit.py` | ✅ 已删 |
| ~~pretool-retry-check.sh~~ | `pretool-retry-check.py` | ✅ 已删 |
| ~~privacy-gate.sh~~ | `privacy-gate.py` | ✅ 已删 |
| ~~subagent-guard.sh~~ | `subagent-guard.py` | ✅ 已删 |
| ~~posttool-output-compressor.sh~~ | `posttool-output-compressor.py` | ✅ 已删（.py 未注册，游离态） |

**当前无残留的双激活文件** — 所有已 Python 化的 hook 的 .sh 孪生均已清除 ✅

---

## 4️⃣ 待移植优先级建议

### 🥇 P0 — 复杂 hook（5 个，预估 3-5 天）
| Hook | 难点 |
|------|------|
| `auto-snapshot.sh` (532行) | 跨平台 mtime + Git 分支检测 + 多函数 |
| `completion-gate.sh` (438行) | source agentic-ui.sh + jq + python heredoc 混合 |
| `error-dna.sh` (538行) | 多 JSON 文件操作 + 高频告警 + 归档轮转 |
| `turn-counter.sh` (344行) | jq + 多状态文件追踪 |
| `build-validator.sh` (343行) | jq 大量 JSON 解析 + 多函数 |

### 🥈 P1 — 中等 hook（23 个，预估 5-7 天）
含 context-compressor, ecosystem-probe, intent-tracker, knowledge-condenser, phase-state-tracker, posttool-bash-audit 等

### 🥉 P2 — 简单 hook（28 个，预估 3-4 天）
含 lsp-gate, oracle-gate, pretool-node-reference, posttool-template-check 等

### ⚡ 基础设施先修
- `harness_config.sh` (805行) → 需拆分为 Python 版 `harness_lib.py`（已有 270 行，需补全 hc_get/hc_enabled 等 bash 函数的等价实现）
- `agentic-ui.sh` (177行) → 需 Python 版输出函数

**总计**: ~60 个 .sh 文件待处理（含 4 工作流标准 hook），其中 5 复杂 + 23 中等 + 28 简单 + 4 工作流标准

---

## 5️⃣ 项目文件汇总

```
.claude/hooks/
├── *.py (17 个) — 已 Python 化，其中 16 注册 + 1 游离
├── *.sh (63 个) — 待摸底
│   ├── 56 个实际 hook/辅助脚本（含 4 废弃游离）
│   ├── 4 个废弃游离（旧工作流）
│   ├── 3 个辅助脚本（harness_config, agentic-ui, pretool-python-bridge）
│   └── 49 个需移植（在 settings.json 中注册）
├── .omc/ — 状态目录
├── __pycache__/ — Python 缓存
└── twin-sh-analysis.md — 此前孪生分析

.claude/workflow-standard/hooks/
├── checkpoint (45行)
├── pretool-workflow-gate (62行)
├── session-inject (64行)
└── state-recovery (79行)
```
