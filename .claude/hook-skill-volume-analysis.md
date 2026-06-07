# Carror OS Hook & Skill 体积分布摸底报告

> 生成日期: 2026-06-07 | 数据基线: `.claude/` 目录实时取样

---

## 1. 📊 总体概况

| 目录 | 文件数 | 总行数 | 说明 |
|------|--------|--------|------|
| `.claude/hooks/` | **96** (96 文件) | **16,172 行** | 含 13 个幽灵文件 |
| `.claude/scripts/` | **86** (86 文件) | **24,692 行** | 独立脚本层 |
| `.claude/skills/` | **198** (198 文件) | **13,721 行** | 含 body/scripts/references |
| **∑ .claude/** | **~5,021 文本文件** | **~55,000+ 行** | 完整治理体系 |

> 注: `.claude/` 下所有文本文件总行数约 11,916 行（不含 scripts/ 的 24,692 行和 skills/ 的 13,721 行，因部分文件计数口径不同）

---

## 2. 🪝 Hook 目录深度分析

### 2.1 注册状态

- **settings.json 注册的 hooks 脚本**: **83 个** (在 hooks/ 目录下的)
- **磁盘上的 hooks 文件**: **96 个** (不含 `__pycache__/` 和 `.omc/`)
- **幽灵 Hook** (磁盘上有但未注册): **13 个**

### 2.2 幽灵 Hook 清单

| 行数 | 文件 | 状态 |
|------|------|------|
| 805 | `harness_config.sh` | **完全未注册** (共享库, 被 source 引用——合理) |
| 270 | `harness_lib.py` | **完全未注册** (共享库) |
| 281 | `posttool-output-compressor.py` | **完全未注册** — 已迁移到 .sh 变体? |
| 74 | `posttool-output-compressor.sh` | **完全未注册** |
| 87 | `posttool-workflow-checkpoint.sh` | **完全未注册** — 被 workflow-standard 替代? |
| 19 | `pretool-python-bridge.sh` | **完全未注册** (位于 hooks/, 但 scripts/ 下有同名文件注册了) |
| 233 | `pretool-retry-check.sh` | 孪生文件，已注册 .py 变体 |
| 148 | `pretool-workflow-gate.sh` | **完全未注册** — 被 workflow-standard/hooks/ 替代 |
| 77 | `privacy-gate.sh` | 孪生文件，已注册 .py 变体 |
| 125 | `sessionstart-workflow-inject.sh` | **完全未注册** — 被 workflow-standard/hooks/ 替代 |
| 124 | `subagent-guard.sh` | 孪生文件，已注册 .py 变体 |
| 125 | `workflow-state-recovery.sh` | **完全未注册** — 被 workflow-standard/hooks/ 替代 |
| 133 | `flywheel-gap-analysis.md` | 文档文件，非可执行 **(无需注册)** |

**🔑 关键幽灵**: 805 行的 `harness_config.sh` 被所有 hook source 引用但自身非独立执行体，**安全**。真正可清理的废弃/冗余文件约 **6 个** (posttool-output-compressor.py/sh, posttool-workflow-checkpoint.sh, pretool-workflow-gate.sh, sessionstart-workflow-inject.sh, workflow-state-recovery.sh) = 约 **815 行** 可删除。

### 2.3 Hook 最大文件 TOP 10

| 排名 | 文件 | 行数 | 类型 | 备注 |
|------|------|------|------|------|
| #1 | `harness_config.sh` | **805** | 共享库 | 被所有 hook source，含大量 Bash 工具函数 |
| #2 | `permission-gate.py` | **651** | Python Gate | 危险性: 权限校验核心逻辑巨大 |
| #3 | `error-dna.sh` | **538** | Bash PostTool | 错误捕获+JSONL写入，含大量重复逻辑 |
| #4 | `auto-snapshot.sh` | **532** | Bash Stop | 快照+分支状态保存 |
| #5 | `completion-gate.sh` | **438** | Bash PostTool | 任务完成验证 |
| #6 | `pretool-edit-scope.py` | **436** | Python Gate | Scope 管理+锚点检测 |
| #7 | `meta-oracle-trigger.py` | **414** | Python PostTool | Meta-Oracle G1-G4 触发 |
| #8 | `turn-counter.sh` | **344** | Bash UserPrompt | 轮次统计+漂移检测 |
| #9 | `build-validator.sh` | **343** | Bash PostTool | 构建验证 |
| #10 | `pretool-retry-check.py` | **326** | Python Gate | 重试上限检测 |

### 2.4 孪生 Hook (py + sh 双版本) — 16 对

| 名称 | .sh 行数 | .py 行数 | 合计 | 冗余判定 |
|------|----------|----------|------|----------|
| permission-gate | 306 | 651 | **957** | 🟡 双活, .py 是主版本(说"转换自 .sh") |
| pretool-edit-scope | 235 | 436 | **671** | 🟡 双活, .py 是主版本 |
| pretool-oracle-gate | 226 | 277 | **503** | 🟡 双活 |
| pretool-retry-check | 233 | 326 | **559** | 🟡 双活 |
| pretool-sensitive-edit | 146 | 303 | **449** | 🟡 双活 |
| privacy-gate | 77 | 145 | **222** | 🟡 双活 |
| context-guard | 148 | 228 | **376** | 🟡 双活 |
| pre-ask-guard | 129 | 205 | **334** | 🟡 双活 |
| subagent-guard | 124 | 178 | **302** | 🟡 双活 |
| meta-oracle-trigger | 178 | 414 | **592** | 🟡 双活 (.py 注册, .sh 未注册但也在 settings 中) |
| edit-guard | 82 | 125 | **207** | 🟡 双活 |
| lsp-suggest | 83 | 132 | **215** | 🟡 双活 |
| fuzzy-block | 64 | 99 | **163** | 🟡 双活 |
| pre-completion-gate | 68 | 130 | **198** | 🟡 双活 |
| pretool-plan-gate | 219 | 296 | **515** | 🟡 双活 |
| posttool-output-compressor | 74 | 281 | **355** | 🔴 两者均未注册! |

**总冗余**: 16 对 × 2 = 32 个文件 = **~6,218 行**。如果能合并为单一语言版本，可释放约 **2,000-3,000 行**。

### 2.5 Crossover: hooks/ ↔ scripts/ 重叠

- `pretool-python-bridge.sh` 同时存在于 hooks/ 和 scripts/（hooks/ 下的 19 行未注册，scripts/ 下的 被注册）
- `token-tracking-real.json` 在 hooks/.omc/state/ 和 scripts/.omc/state/ 下有重复

---

## 3. 📚 Skills 目录分析

### 3.1 SKILL.md 分布

SKILL.md 是 skill 的"入口"——每个仅 13-32 行，**无超标项** (>150 行阈值)。

| Skill 名称 | SKILL.md 行数 | body.md 行数 | 合计(主文档) |
|------------|--------------|-------------|-------------|
| lx-dogfood | 32 | 83 | 115 |
| lx-validate-skill | 26 | 85 | 111 |
| lx-status | 24 | 63 | 87 |
| lx-varlock | 21 | 50 | 71 |
| lx-pre-push | 21 | 69 | 90 |
| lx-pre-commit | 21 | 60 | 81 |
| lx-stepwise | 20 | 64 | 84 |
| update-carror-os | 19 | 48 | 67 |
| lx-oracle | 17 | 86 | 103 |
| lx-learner | 17 | 100 | 117 |
| lx-sync | 16 | 70 | 86 |
| lx-skillify | 16 | 73 | 89 |
| lx-root-cause-analysis | 16 | 92 | 108 |
| lx-oma-hier | 16 | 73 | 89 |
| lx-code-review | 16 | 58 | 74 |
| lx-todo | 15 | 89 | 104 |
| lx-test-gen | 15 | 128 | **143** ⚠️ 接近阈值 |
| lx-rpe | 15 | 93 | 108 |
| lx-task-spec | 14 | 71 | 85 |
| lx-race | 14 | 66 | 80 |
| lx-oma-orch | 14 | 71 | 85 |
| lx-purify | 13 | **126** | **139** ⚠️ 接近阈值 |
| lx-oracle-v2 | 13 | 25 | 38 |
| lx-oma-split | 13 | 63 | 76 |
| lx-oma-gov | 13 | 71 | 84 |
| lx-goal | 13 | 52 | 65 |
| lx-ghost | 13 | 58 | 71 |
| TEMPLATE.md | - | - | (模板) |
| SKILLS.md | - | - | (索引) |

**结论**: ✅ **SKILL.md 全部合规** (< 50 行)，body.md 最大 128 行(lx-test-gen)、126 行(lx-purify)，**接近但未超过 150 行阈值**。无超标技能。

### 3.2 Skills 引用文件

- **body.md**: 27 个 skill × 各 1 个 = 27 个，共 **1,987 行**
- **共享引用 (skills/references/)**: 12 个文件，共 **613 行**（OMA 通用参考、共享标准等）
- **skill 内脚本**: **23 个** (.sh/.py)，最大的是 `lx-goal/scripts/lx-goal.sh` (734 行) 和 `lx-validate-skill/scripts/carror_dashboard.py` (707 行)
- **skill-dependencies.yaml**: 173 行的依赖图

### 3.3 Skills 总数据量

| 层级 | 行数 |
|------|------|
| SKILL.md (27个) | 463 |
| body.md (27个) | 1,987 |
| 共享引用 (12个) | 613 |
| 脚本 (23个) | ~4,500 |
| 其他引文/CHANGELOG 等 | ~6,000+ |
| **总计** | **~13,721** |

> Skills 的 body.md 是每次对话注入的关键上下文。按 skill-slimming 方法论， >150 行 × 27 = 4,050 行的冗余上限。当前 body.md 总和 **1,987 行**，低于阈值。

---

## 4. 🔄 上下文压缩机制

| 组件 | 位置 | 行数 | 状态 |
|------|------|------|------|
| `context-compressor.sh` | hooks/ | 108 | ✅ SessionStart 运行 |
| `compress-agent.py` | scripts/ | 107 | ✅ 存在, 生成 AGENTS.compact.md |
| `extract-compact-memory.py` | scripts/ | 248 | ✅ 存在, 用于 Stop 时生成 todo-queue |
| `AGENTS.compact.md` | .claude/ | 27 | ✅ 已生成 (1427 bytes) |
| `harness_config.sh` | hooks/ | 805 | ✅ 提供 hc_enabled 门禁 |
| `kernel.md` | .claude/ | **43** | ✅ 极简 |
| `index.md` | .claude/ | **52** | ✅ 极简 |

**评估**: ✅ Hot reload 机制完整。`harness_config.sh` 的 `hc_enabled` 门禁可用于每个 hook 的开关控制。context-compressor.sh 缓存到 .omc/state/context-cache.md。

---

## 5. 🔍 冗余/重复模式发现

### 5.1 可直接清理的废弃文件

| 文件 | 行数 | 原因 |
|------|------|------|
| `hooks/pretool-workflow-gate.sh` | 148 | 已被 `workflow-standard/hooks/pretool-workflow-gate` 替代 |
| `hooks/sessionstart-workflow-inject.sh` | 125 | 已被 `workflow-standard/hooks/session-inject` 替代 |
| `hooks/workflow-state-recovery.sh` | 125 | 已被 `workflow-standard/hooks/state-recovery` 替代 |
| `hooks/posttool-workflow-checkpoint.sh` | 87 | 已被 `workflow-standard/hooks/checkpoint` 替代 |
| `hooks/posttool-output-compressor.py` | 281 | 完全未注册，可能已弃用 |
| `hooks/posttool-output-compressor.sh` | 74 | 完全未注册，可能已弃用 |
| **小计可清理** | **~840 行** | |

### 5.2 .sh→.py 迁移后的冗余孪生文件 (建议只保留 .py)

以下 .sh 变体是 .py 迁移前的旧版本：

| .sh 文件 | 行数 | 对应 .py |
|----------|------|----------|
| `permission-gate.sh` | 306 | permission-gate.py (651, 是主版本) |
| `pretool-edit-scope.sh` | 235 | pretool-edit-scope.py (436) |
| `pretool-retry-check.sh` | 233 | pretool-retry-check.py (326) |
| `pretool-oracle-gate.sh` | 226 | pretool-oracle-gate.py (277) |
| `pretool-plan-gate.sh` | 219 | pretool-plan-gate.py (296) |
| `meta-oracle-trigger.sh` | 178 | meta-oracle-trigger.py (414) |
| `context-guard.sh` | 148 | context-guard.py (228) |
| `pretool-sensitive-edit.sh` | 146 | pretool-sensitive-edit.py (303) |
| `pre-ask-guard.sh` | 129 | pre-ask-guard.py (205) |
| `subagent-guard.sh` | 124 | subagent-guard.py (178) |
| `lsp-suggest.sh` | 83 | lsp-suggest.py (132) |
| `edit-guard.sh` | 82 | edit-guard.py (125) |
| `privacy-gate.sh` | 77 | privacy-gate.py (145) |
| `posttool-output-compressor.sh` | 74 | posttool-output-compressor.py (281) |
| `pre-completion-gate.sh` | 68 | pre-completion-gate.py (130) |
| `fuzzy-block.sh` | 64 | fuzzy-block.py (99) |
| **小计可清理** | **~2,392 行** | **前提**: 确认 .py 已完全覆盖 .sh 功能 |

### 5.3 脚本/ hook 跨目录重复

- `pretool-python-bridge.sh` 在 hooks/ 和 scripts/ 同时存在 (hooks/ 版本 19 行未注册)

### 5.4 body.md 无完全重复

27 个 body.md 均有不同的 MD5 哈希值——**无完全内容重复**。但部分 body.md 共享相似的结构模式（每个 skill 的 body.md 都包含 role/responsibilities/examples 等标准段）。

---

## 6. 🎯 优化潜力排名

| 排名 | 优化项 | 预估释放行数 | 影响度 | 难度 | 说明 |
|------|--------|-------------|--------|------|------|
| **#1** | **清理废弃 workflow 旧 hooks** (5 个文件) | **~840 行** | 🔴 高 | 🟢 低 | 已被 workflow-standard/ 替代，直接删除 |
| **#2** | **合并/删除 .sh 孪生文件** (16 个 .sh) | **~2,392 行** | 🔴 高 | 🟡 中 | 需确认 .py 全覆盖 .sh 功能，然后删 .sh |
| **#3** | **缩减超大 hook (Top 5)** | **~1,500 行** | 🟡 中 | 🔴 高 | permission-gate.py(651)、error-dna.sh(538)、auto-snapshot.sh(532) 等需要拆分或提取共享库 |
| **#4** | **瘦身 body.md >100 行** (4 个) | **~150 行** | 🟡 中 | 🟡 中 | lx-test-gen(128)、lx-purify(126)、lx-learner(100)、lx-todo(89) 可考虑提取到引用文件 |
| **#5** | **幽灵 hook 注册/清理** (非孪生部分) | **~815 行** (含废弃) | 🟡 中 | 🟢 低 | 6 个废弃文件已计入 #1 |
| **#6** | **合并 skills/ 脚本到 scripts/** | **~4,500 行** | 🟢 低 | 🔴 高 | 23 个 skill 内脚本共 ~4,500 行，但它们是 skill 自己的工具，迁移不一定合理 |
| **#7** | **harness_config.sh 瘦身** | **~200 行** | 🟢 低 | 🔴 高 | 805 行共享库，部分函数可能已不再使用 |

---

## 7. ✅ 建议立即操作

### P0 (立即做, 低风险)
1. **删除 5 个废弃 workflow hooks** → 释放 ~840 行
2. **注册或删除 posttool-output-compressor.py/sh** → 355 行幽灵
3. **清理 hooks/pretool-python-bridge.sh** → 19 行 (scripts/ 版本已注册)

### P1 (本周做, 中风险)
4. **permission-gate.sh → deprecate** (保留 .py) → 306 行
5. **pretool-retry-check.sh → deprecate** → 233 行
6. **pretool-oracle-gate.sh → deprecate** → 226 行

### P2 (规划中, 大工程量)
7. **error-dna.sh 瘦身**: 538 行，提取 shared 函数到 harness_config.sh
8. **auto-snapshot.sh 瘦身**: 532 行，抽取通用快照逻辑
9. **completion-gate.sh 瘦身**: 438 行

### 当前状态总结
- **SKILL.md**: ✅ 全部合规 (<50 行), 无 >150 行超标
- **body.md**: ✅ 全部 <150 行, 但 4 个 >100 行接近上限
- **Hot reload**: ✅ context-compressor.sh + compress-agent.py + extract-compact-memory.py 完整
- **kernel.md**: ✅ 仅 43 行, index.md: 52 行, 均极简
- **最大问题**: 16 对 py+sh 孪生 + 5 个废弃 workflow hook + ~2,300 行可清理冗余
