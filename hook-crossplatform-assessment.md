# Carror OS 全平台 Python 化 — Hook 调用生态摸底报告

> 生成: 2026-06-07  
> 项目路径: ~/Desktop/Sylph/Carror_OS  
> 版本: 6.6.0 (root VERSION.json) / 6.6.2 (source/harness-kit VERSION.json)  
> 工具: 终端调查 + 全文搜索 + 文件读取

---

## 1️⃣ @carroros/gov (OpenCode npm plugin) 当前状态

### 1.1 目录和版本

| 项目 | 值 |
|------|-----|
| 路径 | `packages/carroros-gov/` ✅ 存在 |
| package.json | `name: "@carroros/gov"`, `version: "1.0.0"` |
| 类型 | ES module (`"type": "module"`) |
| 入口 | `src/index.ts` |
| 依赖 | `effect ^4.0.0`, `zod ^3.24.0` |
| 对等依赖 | `@opencode-ai/plugin` |
| engines.opencode | `>=1.16.0` |
| dist/ | ❌ **不存在** — 未编译构建，仅源码 |
| tsconfig | ES2022 → NodeNext 模块 |

### 1.2 已实现 Hooks (5 个注册事件)

| Hook 事件 | 处理器 | 对应 CC .sh/.py 功能 |
|-----------|--------|---------------------|
| `experimental.chat.system.transform` | `systemTransform` → 注入 AGENTS.compact.md | ✅ 对应 AGENTS.md |
| `tool.execute.before` | `compositeBefore` = privacyGate + oraclePreReview | ✅ 对应 privacy-gate.py + oracle-gate.sh |
| `tool.execute.after` | `metaOraclePostReview` = anti-pattern detect | ✅ 对应 meta-oracle-trigger.py + detect.ts |
| `permission.ask` | `permissionAsk` → 权限映射 | ✅ 对应 permission-gate.py |
| `experimental.session.compacting` | `compactHandler` → handoff.py 调用 | ✅ 对应 handoff.py |

### 1.3 能力缺口 vs CC 实际 hooks

**缺失的治理能力（CarrorOS CC 有但 OC plugin 未实现）：**

| 缺失功能 | CC 实现 | OC 差距 | 影响 |
|----------|---------|---------|------|
| **Workflow 五阶状态机** | workflow-standard/hooks/ 4个 + settings.json 注册 | ❌ 完全缺失 | OpenCode 上无法使用 workflow gate/checkpoint |
| **SessionStart hooks (8个)** | context-compressor, ecosystem-probe, flywheel-report, lsp-gate, oracle-gate, session-resume, sessionstart-gate-check, cross-platform-smoke-test 等 | ❌ 完全缺失 | 启动时初始化全部靠 CC hook |
| **PostToolUse 审查 (15+ .sh)** | posttool-bash-audit, posttool-claim-audit, posttool-edit-quality, posttool-anti-pattern-detect, posttool-completion-audit 等 | ❌ 部分缺失 | 仅有 tool.execute.after 一个入口 |
| **Stop 事件 (4个)** | auto-snapshot, knowledge-condenser, stop-drain, skill-flywheel, error-dna-auto-fix | ❌ 完全缺失 | 会话结束时无清理 |
| **UserPromptSubmit 事件 (4个)** | pretool-approve-detect, pretool-rules-inject, pretool-user-correction, thinking-gate | ❌ 完全缺失 | 用户输入预处理缺失 |
| **PreToolUse:Bash 子集** | pretool-terminal-safety, pretool-blast-radius, pretool-git-gate 等 | ❌ 部分缺失 | Bash 安全门禁不全 |
| **PreToolUse:Edit\|Write 子集** | pretool-scope-gate, pretool-b1-detect, pretool-sensitive-file-guard, pretool-skill-version-guard, pretool-purify-gate, pretool-write-lock 等 | ❌ 完全缺失 | 文件编辑安全门禁全缺 |
| **Token/频率追踪** | token_writer, turn-counter, permission-frequency-tracker, read-tracker | ❌ 完全缺失 | 无使用量审计 |
| **Error DNA 与飞轮** | error-dna, error-dna-auto-fix, flywheel-report, skill-flywheel | ❌ 完全缺失 | 无错误自愈+反馈循环 |
| **Skill 合规** | posttool-skill-compliance, skill-usage-tracker, pretool-skill-body-enforce | ❌ 完全缺失 | 无 skill 合约执行 |

**结论: OC plugin 仅覆盖约 10-15% 的 CC hook 功能。** 核心缺失在工作流状态机、SessionStart 初始化链、PostToolUse 审计集群和事件处理。

---

## 2️⃣ workflow-standard/hooks/ 现状

### 2.1 文件清单

| 文件 | 行数 | 注册位置 | 说明 |
|------|------|----------|------|
| `checkpoint` | 45 | PostToolUse:TaskUpdate | 工作流 checkpoint 自动推进 |
| `pretool-workflow-gate` | 62 | PreToolUse:Edit\|Write\|Bash | 工作流阶段门禁 |
| `session-inject` | 64 | SessionStart | 会话启动注入工作流上下文 |
| `state-recovery` | 79 | SessionStart | 状态腐蚀恢复 + Gate 超时检测 |

**特点:**
- 全部是 bash shebang 脚本且 **无文件后缀**（裸名）
- 全部 `source` 了 `harness_config.sh`
- **必须 Python 化** — Claude Code / OpenCode 跨平台都需要
- 相对简单（45-79行），可优先移植

### 2.2 与旧工作流 hooks 的关系

旧工作流 `.claude/hooks/` 下还有 4 个废弃游离脚本：
- `sessionstart-workflow-inject.sh`, `workflow-state-recovery.sh`, `posttool-workflow-checkpoint.sh`, `pretool-workflow-gate.sh`
- 这 4 个未被 settings.json 注册，workflow-standard/hooks/ 下的 4 个是它们的替代实现

---

## 3️⃣ source/harness-kit/ hooks 打包

### 3.1 hooks 分发机制

`scripts/package-release.sh` 的 Step 1 显示：
```bash
rsync -a --delete .claude/hooks/       "$HARNESS_SRC/.claude/hooks/"
rsync -a --delete .claude/scripts/     "$HARNESS_SRC/.claude/scripts/"
```

这意味着 **hooks 是跟随项目整体 rsync 到 source/ 的**，而不是独立打包。

### 3.2 source/harness-kit/.claude/hooks/ 内容

source/harness-kit 下已有完整 hooks 镜像（约 80+ 文件），包括：
- 所有 .sh hook
- 部分 .py hook（如 pretool-oracle-gate.py, pretool-edit-scope.py, pre-ask-guard.py 等）
- `harness_config.sh`（共享库核心）
- `agentic-ui.sh`（共享库辅助）

**关键发现：** source/harness-kit 中的 `.claude/settings.json` 在 rsync 时被 `sed` 替换了绝对路径 → `__PROJECT_ROOT__` 占位符，这是一个跨平台标记。

### 3.3 发布脚本对 hooks 的处理

`package-release.sh` 的 `verify_package()` 函数对每个 tar 包中的文件做 **sha256 完整性校验**：
```bash
tar_sha=$(tar -xzf "$tar_file" -O "$f" 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
src_sha=$(shasum -a 256 "$src_dir/$f" 2>/dev/null | cut -d' ' -f1)
```

这意味着 **Python 化后，所有编译/复制到 source 的文件必须与 root 完全一致**，否则打包会失败。

---

## 4️⃣ 核心依赖库分析：harness_config.sh + harness_lib.py

### 4.1 harness_config.sh (805 行) — 最核心的共享库

| 函数 | 功能 | 行数 | Python 版状态 |
|------|------|------|-------------|
| `hc_init()` | 标准路径变量初始化 | ~9 | ❌ 未实现 |
| `_resolve_python()` | 跨平台 Python 解析 (macOS/Linux/Windows) | ~38 | 不适用（Python 不需要） |
| `hc_get("key","default")` | 读 harness.yaml 配置值 | ~16 | ✅ `harness_lib.py` 有 |
| `hc_get_list("key","default")` | 读列表配置值 | ~16 | ✅ 有 |
| `hc_enabled("name")` | 检查 feature 是否启用 | ~28 | ✅ `harness_lib.py` 有 |
| `hc_hook_enabled("name")` | 仅检查 hooks_enabled | ~6 | ❌ 未实现 |
| `hc_skill_enabled("name")` | 仅检查 skills_enabled | ~6 | ❌ 未实现 |
| `hc_project_root()` | 返回项目根目录 | ~3 | ❌ 未实现硬编码类 |
| `hc_state_dir()` | 返回状态目录 | ~3 | ❌ 未实现 |
| `is_mode_active()` | 检测 Ghost/Goal/Normal 模式 | ~100 | ✅ 有 |
| `_hc_evidence()` / `_hc_write_evidence()` | 运行时证据追踪 | ~20 | ❌ 未实现 |
| `_hc_ensure_cache()` | YAML→键值缓存重建 | ~120 | ✅ 有 `_ensure_cache()` |
| `_parse_yaml_simple()` | 简单 YAML 解析器 | ~30 | ✅ 有 |
| Shell heredoc Python 内嵌 | 模式检测用 Python 内嵌 | ~300 | 不适用 |

### 4.2 harness_lib.py (270 行) — 已 Python 化

| 函数 | 与 shell 版对应 | 状态 |
|------|----------------|------|
| `_ensure_cache()` | `_hc_ensure_cache()` | ✅ 功能等价 |
| `hc_get(key, default="")` | `hc_get()` | ✅ 功能等价 |
| `hc_enabled(feature_name)` | `hc_enabled()` | ✅ 功能等价 |
| `is_mode_active(state_dir=None)` | `is_mode_active()` | ✅ 功能等价 |
| `flywheel_event(...)` | `flywheel_event()` | ✅ 功能等价 |
| `hc_emit_hook_json(...)` | 无 shell 对应 | ✅ 纯 Python 新增 |
| `agentic_menu(...)` | `agentic_menu()` (agentic-ui.sh) | ✅ 功能等价 |

**缺口:** `harness_lib.py` 缺少 `hc_hook_enabled()`, `hc_skill_enabled()`, `hc_project_root()`, `hc_state_dir()`, `hc_init()`, 证据追踪等函数。

### 4.3 agentic-ui.sh (177 行) — 次要共享库

被 `completion-gate.sh` 和 `pretool-git-gate.sh` 两个 hook 通过 `source` 引用。部分功能（`agentic_menu`）已被 `harness_lib.py` 覆盖。

---

## 5️⃣ 依赖关系图 — Shell Hook 调用树

### 5.1 一级依赖：谁 `source` 了 `harness_config.sh`

**54 个 .sh 文件 direct source harness_config.sh**（这是全平台 Python 化的最大耦合点）：

**`.claude/hooks/` (47 个):**
auto-snapshot, build-validator, completion-gate, context-compressor, cross-platform-smoke-test, ecosystem-probe, error-dna, error-dna-auto-fix, flywheel-report, inject-project-knowledge, intent-tracker, knowledge-condenser, lsp-gate, oracle-gate, phase-state-tracker, posttool-anti-pattern-detect, posttool-bash-audit, posttool-checkpoint, posttool-claim-audit, posttool-completion-audit, posttool-edit-quality, posttool-format-gate, posttool-handoff-writer, posttool-read-cite, posttool-skill-compliance, posttool-subagent-audit, posttool-template-check, posttool-write-cite, posttool-write-lock, pre-edit-lsp-check, pretool-approve-detect, pretool-b1-detect, pretool-blast-radius, pretool-cruise-check, pretool-git-gate, pretool-node-reference, pretool-purify-gate, pretool-rules-inject, pretool-scope-gate, pretool-sensitive-file-guard, pretool-skill-body-enforce, pretool-skill-version-guard, pretool-terminal-safety, pretool-user-correction, pretool-write-lock, read-tracker, session-resume, sessionstart-gate-check, sessionstart-workflow-inject, skill-flywheel, skill-usage-tracker, stop-drain, thinking-gate, token_writer, turn-counter, workflow-state-recovery, permission-frequency-tracker, posttool-output-compressor, agentic-ui

**`.claude/scripts/` (9 个):**
setup-terminal-safety, setup-rpe-task-layer, setup-client-fallback, setup-release-gate, ab-test-rules-inject, release, setup-session-recovery, setup-sync-governance-debt

**`.claude/workflow-standard/hooks/` (4 个):**
checkpoint, pretool-workflow-gate, session-inject, state-recovery

**`.claude/` settings.json 注册模式:** 所有 hooks 都通过 settings.json 的 `"hooks"` 数组注册，hook 路径相对于 `.claude/hooks/`。

### 5.2 二级依赖：谁 `source` 了 `agentic-ui.sh`

- `completion-gate.sh` (438行, 复杂)
- `pretool-git-gate.sh` (85行, 简单)

### 5.3 跨文件调用模式

除了 `source` 外，部分 hook 通过 `bash xxx.sh` 或 `python3 xxx.py` 调用其他脚本：
- `error-dna.sh` → `source scripts/issue-triage.sh` (子 shell)
- `completion-gate.sh` → `source scripts/issue-triage.sh`
- `posttool-claim-audit.sh` → `source scripts/issue-triage.sh`
- 多数 hook 通过 `$PYTHON_BIN -c "..."` 内嵌 Python 执行配置读取

### 5.4 叶子节点 vs 根节点

| 层级 | 分类 | 特征 | 例子 | 移植优先级 |
|------|------|------|------|-----------|
| **叶子** | 简单纯逻辑 | 不 source 其他脚本, 无复杂 JSON | `lsp-gate.sh`, `oracle-gate.sh`, `pretool-node-reference.sh`, `pretool-purify-gate.sh` | 🥇 可先移 |
| **中间** | 中等依赖 | source harness_config.sh, 含 Python heredoc | `posttool-format-gate.sh`, `pretool-terminal-safety.sh`, `skill-usage-tracker.sh` | 🥈 第二批 |
| **根节点** | 复杂多依赖 | source 多个脚本 + python heredoc + jq | `error-dna.sh`, `completion-gate.sh`, `turn-counter.sh`, `auto-snapshot.sh` | 🥉 最后移 |

---

## 6️⃣ .sh 脚本间互调分析

### 6.1 `source xxx.sh` 模式（46+ 处）

所有 `.sh` hook 互调都是通过 `source harness_config.sh`，少数通过 `source agentic-ui.sh`。**未发现 .sh hook 之间相互 source 的情况**——每个 hook 仅依赖共享库。

### 6.2 `bash xxx.sh` / `./xxx.sh` 模式

仅存在于 `package-release.sh` 中调用 `audit-hooks.sh`、`meta-oracle-review.sh`、`harness-smoke-test.sh` 等发布脚本（非 hooks）。

### 6.3 `python3 -c "..."` 内嵌模式（大量使用）

约 20 个 .sh hook 使用 heredoc 内嵌 Python 代码进行 JSON 操作。这是 Python 化的自然信号——内嵌 Python 代码应提升为纯 Python 文件。

---

## 7️⃣ 跨平台化影响总结

### 7.1 必须 Python 化的文件

| 类别 | 数量 | 优先级 |
|------|------|--------|
| `.sh` hooks (在 settings.json 注册) | ~49 个 | P0-P2 |
| `workflow-standard/hooks/` (4 个无后缀) | 4 个 | P0 |
| `harness_config.sh` (共享库, 805行) | 1 个 | **阻塞依赖** |
| `agentic-ui.sh` (共享库, 177行) | 1 个 | P1 |
| `harness_lib.py` 补全缺口 | ~30% 功能缺失 | **阻塞依赖** |
| `scripts/` 下 setup/ 脚本 (9 个 source) | 9 个 | P2（不影响 hooks） |

### 7.2 @carroros/gov 能力缺口

| 维度 | 当前覆盖 | 缺口严重性 |
|------|---------|-----------|
| governance rules injection | ✅ 实现 | - |
| privacy gate | ✅ 实现 | - |
| oracle pre-review | ✅ 部分实现（无 workflow 联动） | 中 |
| anti-pattern detection | ✅ 实现 | - |
| permission mapping | ✅ 部分实现 | 低 |
| compact handoff | ✅ 实现 | - |
| **Workflow state machine** | ❌ 完全缺失 | **高** |
| **SessionStart chain** | ❌ 完全缺失 | **高** |
| **PostToolUse audit cluster** | ❌ 完全缺失 | **高** |
| **Stop/cleanup hooks** | ❌ 完全缺失 | **中** |
| **UserPromptSubmit hooks** | ❌ 完全缺失 | **中** |

### 7.3 移植阻塞依赖链

```
harness_config.sh (805行, 被54+个脚本source)
  └── agentic-ui.sh (177行, 被2个脚本source)
       └── completion-gate.sh (438行)
       └── pretool-git-gate.sh (85行)
  └── 47个 .claude/hooks/ .sh 文件
  └── 9个 .claude/scripts/ 脚本
  └── 4个 workflow-standard/hooks/ 脚本
```

**结论：** `harness_config.sh` → `harness_lib.py` 的等价移植是整个 Python 化的 **阻塞依赖**。必须先完成共享库移植，才能逐步将 40+ 个 .sh hook 逐个 Python 化。

### 7.4 推荐移植顺序

**Phase 0 (基础设施):** `harness_lib.py` 补全 → 删除 `harness_config.sh`  
**Phase 1 (工作流标准):** 4 个 workflow-standard hooks → OC plugin 集成  
**Phase 2 (叶子节点):** ~20 个简单 hooks (< 50行) → 批量 Python 化  
**Phase 3 (中间节点):** ~20 个中等 hooks → 逐个人工审查  
**Phase 4 (根节点):** 5 个复杂 hooks (auto-snapshot, completion-gate, error-dna, turn-counter, build-validator)  
**Phase 5 (@carroros/gov 增强):** 补齐 OC plugin 缺失的能力（workflow 状态机、SessionStart 等）

---

## 8️⃣ 附件

### 8.1 核心文件路径清单

```
packages/carroros-gov/          → OC npm plugin (TypeScript, 5 hooks)
├── src/index.ts                → plugin 入口 (5事件注册)
├── src/system.ts               → chat.system.transform
├── src/privacy.ts              → tool.execute.before (privacy)
├── src/oracle.ts               → tool.execute.before (oracle)
├── src/oracle-post.ts          → tool.execute.after (meta-oracle)
├── src/detect.ts               → anti-pattern 检测引擎
├── src/permission.ts           → permission.ask
├── src/compact.ts              → experimental.session.compacting
└── src/rules/index.ts          → rules 加载器

.claude/hooks/                  → 全部 hook 实现 (63 .sh + 17 .py)
├── harness_config.sh           → 805行共享库 (被54+文件 source)
├── harness_lib.py              → 270行 Python 共享库 (已部分实现)
├── agentic-ui.sh               → 177行 UI 辅助库 (被2文件 source)
├── hooks-inventory.md          → Hook 摸底清单
├── *.sh (60+ 个)               → 需移植的 shell hooks
└── *.py (17 个)                → 已 Python 化 hooks

.claude/workflow-standard/hooks/ → 4个工作流标准 hook (无后缀, bash)
├── checkpoint                  → PostToolUse:TaskUpdate
├── pretool-workflow-gate       → PreToolUse:Edit|Write|Bash
├── session-inject              → SessionStart
└── state-recovery              → SessionStart

scripts/                        → 发布/安装脚本
├── package-release.sh          → 打包 harness-kit (rsync hooks)
├── *setup-*.sh (9 个)          → source harness_config.sh 的安装脚本
```

### 8.2 source/harness-kit/ hooks 同步机制

打包流程: `root .claude/hooks/` → `rsync --delete` → `source/harness-kit/.claude/hooks/` → tar.gz

这意味着 **Python 化只需在 root/.claude/hooks/ 修改**，source/ 自动通过打包流程同步。
