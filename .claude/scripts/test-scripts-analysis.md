# 10 个小测试脚本覆盖分析报告

## 比对基准

| 主脚本 | 行数 | 职责 |
|--------|------|------|
| `capability-matrix-test.sh` | 1177 | 18 维度能力矩阵全量测试（hook 存在性、配置注册、语法、冒烟测试、功能注册、飞轮、三源、错误 DNA、Oracle、哲学追溯、铁律执行、技能可用性、缺陷跟踪、集成测试、跨平台、上下文压缩、Handoff、OC 插件） |
| `harness-smoke-test.sh` | 2179 | 真实 Claude Code JSON schema 下 hook 冒烟测试（context-guard、privacy-gate、error-dna、permission-gate、edit-guard、lsp、claim-audit、completion-gate、subagent-guard 等 40+ 测试用例） |

**关键发现**: 两个主脚本均未 `source` 或调用任何这 10 个小脚本。它们是完全独立的测试套件。

---

## 逐脚本分析

### 1. tier1-runtime-test.sh (114 行)

**内容**: 18 项原子机制运行验证 — 直接 bash 调用测试 completion-gate、permission-gate、privacy-gate、blast-radius、error-dna、intent-tracker、lsp-suggest、context-compressor 等 hook。

**覆盖判断**: 🔴 **基本完全覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ✓ 所有 hook 均有对应测试，且使用更严格的真实 Claude Code schema |
| `capability-matrix-test.sh` | ✓ D11(铁律运行时) + D14(集成测试) 也覆盖了大部分 |

**独有逻辑**: 使用简化 stdin 格式（无 `hook_event_name` 字段），是过时的测试风格。

**建议**: 🗑️ **可安全删除**。内容已被 `harness-smoke-test.sh` 完全覆盖且更严格。

---

### 2. tier2-runtime-test.sh (120 行)

**内容**: 8 对机制"配对协同"验证（completion-gate + posttool-completion-audit、permission-gate + privacy-gate、scope + tracker、error-dna + retry-budget、lsp + pre-edit-lsp、Oracle + Meta-Oracle、blast-radius + permission-gate、package-release DG-100）。

**覆盖判断**: 🟡 **部分覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ⚠️ 测试单个 hook，不测试配对协作 |
| `capability-matrix-test.sh` | ⚠️ D14 测试了部分 hook 组合但非完整配对 |

**独有逻辑**: ✅ **配对验证（pair verification）概念是独有的** — 测试两个 hook 在真实工作流中如何协作。这不是单一 hook 测试能覆盖的。

**建议**: 📌 **保留**。配对验证是独特且有价值的测试维度。

---

### 3. tier3-runtime-test.sh (138 行)

**内容**: 5 条链式机制管道验证（编辑管道、错误管道、打包管道、审查管道、会话管道）+ 问题发现（E6 contradiction、error-dna 空、retry-budget 稀疏）。

**覆盖判断**: 🟡 **部分覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ⚠️ 测试单个 hook，不测试跨 hook 管道 |
| `capability-matrix-test.sh` | ⚠️ D14 集成测试不涉及管道链 |

**独有逻辑**: ✅ **管道/链式验证 + 问题分析是独有的**。特别是 "Issues Found" 部分对 E6 矛盾检测、error-dna 管道、retry-budget 稀疏度的运行时数据分析，两个主脚本均不包含。

**建议**: 📌 **保留**。管道验证和运行时数据分析有独特价值。

---

### 4. tier4-e2e-test.sh (120 行)

**内容**: 3 个端到端全场景验证（Bug修复全流程 7 阶段、安装包发布 4 门禁、对照实验 10 维度能力比较）。

**覆盖判断**: 🟡 **部分覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ⚠️ 不涉及场景编排 |
| `capability-matrix-test.sh` | ⚠️ D1 检查 hook 存在性但不测试端到端流程 |

**独有逻辑**: ✅ **端到端场景验证是独特的**。7 阶段 Bug 修复流程、4 门禁发布流程是完整工作流测试。"对照实验"部分（10 维度 Group A vs Group B 对比）比较特殊但不是标准测试。

**建议**: 📌 **保留**。场景测试提供了单个 hook 测试无法提供的回归价值。

---

### 5. core-mechanism-test.sh (91 行)

**内容**: 7 领域核心机制验证（脱水能力、LSP 能力、决策链、全自动化、OMA、审查体系、知识体系）。

**覆盖判断**: 🔴 **大部分覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `capability-matrix-test.sh` | ✓ D10(哲学追溯) + D12(技能可用性) + D9(Oracle) 覆盖了大部分 |
| `harness-smoke-test.sh` | ✓ LSP 测试已覆盖 |

**独有逻辑**: 脱水（mtime 触发的缓存刷新）和决策链哲学优先级验证部分独特，但核心机制测试已融入主脚本的更宽维度中。

**建议**: 🗑️ **可删除**，如果其独特部分（脱水刷新、哲学优先级）迁移到 capability-matrix-test.sh。否则可标记为到期。

---

### 6. deep-runtime-test.sh (133 行)

**内容**: 核心技能深度运行时验证 — LSP 深度验证（服务器安装状态、运行时行为、大写/小写行为）、决策链深度（哲学优先级、DG-91、claim-audit、反模式 F1）、OMA 深度验证（四件套完整性、MECE 验证、管道步骤）、自动化深度验证（goal/ghost、硬边界、三级裁决链、race mode、autopilot/ralph）。

**覆盖判断**: 🟡 **部分覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `capability-matrix-test.sh` | ✓ D12 检查技能存在性但不检查内容深度 |
| `harness-smoke-test.sh` | ✓ LSP 基本行为已覆盖 |

**独有逻辑**: ✅ **深度内容验证是独特的** — LSP 服务器安装检查、OMA MECE 正交验证、race mode/autopilot/ralph 技能测试、卡点分类处理矩阵、三级裁决链内容检查等。这些是检查技能文档内容而非 hook 存在性。

**建议**: 📌 **保留或合并到 capability-matrix-test.sh**。深度验证有独特价值，但可以考虑整合。

---

### 7. ed-red-team-test.sh (323 行)

**内容**: Error DNA 红队攻击模拟测试 — 11 种逃逸场景（E1 治理文件绕过 5 种方式、E2 CAPTCHA 伪造 3 种方式、E3 上下文规避、E4 证据编造、T2 路径逃逸 2 种方式、T6 编码逃逸、T7 API 逃逸）。直接向 error-dna.sh 和 posttool-bash-audit.sh 注入对抗性 payload。

**覆盖判断**: 🟢 **完全未被覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ❌ 仅测试 error-dna 正常行为，无红队对抗测试 |
| `capability-matrix-test.sh` | ❌ D8 仅检查 error-dna 管道健康，无攻击模拟 |

**独有逻辑**: ✅ **完全独特**。这是唯一测试逃逸检测引擎（error-dna 的 E1/E2 检测、posttool-bash-audit 的 E3/E4 检测）能否捕获 AI 对抗性逃逸的脚本。323 行中有大量复杂的事件模拟、上下文种子、断言逻辑。

**建议**: 🔒 **必须保留**。红队安全测试是不可替代的关键防线。

---

### 8. hook-production-verify.sh (228 行)

**内容**: 生产级 hook 端到端验证（A1-A4/E 场景）— privacy-gate 拦截 .env/sk-ant/ghp_、permission-gate 拦截 rm -rf/git commit、edit-guard Read-before-Edit、context-guard 95% 阈值、claim-audit 铁律#1、audit-hooks 对账、harness-smoke-test 回归。

**覆盖判断**: 🔴 **几乎完全覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ✓ **所有测试用例都已存在**，且使用相同的 Claude Code schema 格式 |
| `capability-matrix-test.sh` | ✓ D11(铁律运行时) 覆盖了相同场景 |

**独有逻辑**: 唯一的差异是使用了 `assert_exit` + `assert_stderr` 双断言模式 vs harness-smoke-test 的 `run_case` 单函数模式，但测试用例完全重叠。

**建议**: 🗑️ **可安全删除**。所有测试已被 `harness-smoke-test.sh` 完全覆盖。

---

### 9. cross-verify-b-terminal.sh (105 行)

**内容**: B 终端跨会话独立验证 — 三扇门 A→B→A 的 B 环节。运行 harness-smoke-test、audit-hooks、source-mirror 检查。输出 JSON 结果供 AI 读取（三源一致性中的 Source III：运行时事实）。

**覆盖判断**: 🟡 **功能测试内容被覆盖，但架构角色独特**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ✓ B 终端中运行的就是 smoke test 自身 |
| `capability-matrix-test.sh` | ✓ D4 运行 smoke test，D7 运行 audit-hooks |

**独有逻辑**: ✅ **B 终端编排角色是独特的**。这不是测试什么（内容已被覆盖），而是如何测试（独立 bash 进程、不共享 AI 上下文、输出 JSON 供后续消费）。这是三源一致性架构的 "Source III" 环节。

**建议**: 📌 **保留脚本，但标记为"基础设施编排脚本，非测试用例"**。如果三源验证协议需要保留 B 终端环节，则保留。如果只关心测试覆盖，内容已在主脚本中。

---

### 10. test_race.sh (387 行)

**内容**: Race 蜂群协调层集成测试 — 12 个测试用例覆盖注册、状态聚合、报告、错误处理、清理、列表显示。测试 `race_manager.sh` 的完整生命周期。

**覆盖判断**: 🟢 **完全未被覆盖**

| 主脚本 | 覆盖情况 |
|--------|----------|
| `harness-smoke-test.sh` | ❌ 完全不涉及 race 系统 |
| `capability-matrix-test.sh` | ❌ 不涉及 race 系统 |

**独有逻辑**: ✅ **完全独特**。测试的是一个独立子系统（race_manager.sh），两个主脚本均不涉及。

**建议**: 🔒 **必须保留**。这是 race 蜂群系统的唯一测试套件。

---

## 汇总表

| # | 脚本名 | 行数 | 覆盖状态 | 独有价值 | 建议 |
|---|--------|------|----------|----------|------|
| 1 | `tier1-runtime-test.sh` | 114 | 🔴 完全覆盖 | 无（使用过时格式） | 🗑️ **删除** |
| 2 | `tier2-runtime-test.sh` | 120 | 🟡 部分覆盖 | ✅ 配对验证 | 📌 **保留** |
| 3 | `tier3-runtime-test.sh` | 138 | 🟡 部分覆盖 | ✅ 管道验证 + 问题分析 | 📌 **保留** |
| 4 | `tier4-e2e-test.sh` | 120 | 🟡 部分覆盖 | ✅ 端到端场景 | 📌 **保留** |
| 5 | `core-mechanism-test.sh` | 91 | 🔴 大部覆盖 | ⚠️ 脱水/决策链微量 | 🗑️ **可删（或迁移后删）** |
| 6 | `deep-runtime-test.sh` | 133 | 🟡 部分覆盖 | ✅ 深度内容验证 | 📌 **保留或合并** |
| 7 | `ed-red-team-test.sh` | 323 | 🟢 未覆盖 | ✅ 红队逃逸测试 | 🔒 **必须保留** |
| 8 | `hook-production-verify.sh` | 228 | 🔴 完全覆盖 | 无 | 🗑️ **删除** |
| 9 | `cross-verify-b-terminal.sh` | 105 | 🟡 内容覆盖 | ✅ B 终端编排角色 | 📌 **保留（基础设施）** |
| 10 | `test_race.sh` | 387 | 🟢 未覆盖 | ✅ race 子系统测试 | 🔒 **必须保留** |

## 可删除清单

### 明确可删除（内容已在主脚本中）：
1. **`tier1-runtime-test.sh`** — 所有 18 项 hook 测试已被 `harness-smoke-test.sh` 覆盖且更严格
2. **`hook-production-verify.sh`** — 所有 A1-A4/E 场景测试已被 `harness-smoke-test.sh` 覆盖
3. **`core-mechanism-test.sh`** — 大部被 `capability-matrix-test.sh` 覆盖；配合度/决策链/脱水测试可迁入后删除

### 不可删除（独有价值）：
4. **`ed-red-team-test.sh`** — 唯一红队对抗测试
5. **`test_race.sh`** — 唯一 race 子系统测试
6. **`tier2-runtime-test.sh`** — 配对验证独特
7. **`tier3-runtime-test.sh`** — 管道验证 + 数据分析独特
8. **`tier4-e2e-test.sh`** — 端到端场景验证独特
9. **`deep-runtime-test.sh`** — 深度内容验证独特
10. **`cross-verify-b-terminal.sh`** — B 终端编排架构角色独特
