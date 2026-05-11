<!-- PROJECT: Carror OS -->

<!-- DATE: 2026-05-07 -->

# 代码执行内核（kernel.md）

> >
> 由 bootstrap-harness 生成，请按项目实际情况填充各章节
> 本文件是 AI 执行内核 — 写代码前必读，冻结后不可随意扩展

## ⚖️ 宪法冻结声明
本文件作为 **AI 执行内核（Kernel）**：
- ✅ 不再新增行为铁律、Gate 类型
- ✅ 所有新经验默认进入 `.claude/claude-next.md`，验证稳定后可升华到此文件

---

## 架构铁律
<!-- 由 R17 审计填充 @2026-05-07 -->
- **双域架构**：harness-kit（内核层/治理） + lx-skills-v5（能力层/工程），严格按 domain 划分职责
- **Hook 不可失败**：所有 `hooks/*.sh` 禁止 `set -e`，必须 `exit 0` 或 `echo '{"continue": true}'` 结尾
- **hc_enabled 门禁**：每个 Hook 脚本必须通过 `hc_enabled "feature_name" || exit 0` 读取 yaml 开关
- **最大修复上限**：同一问题最多修 3 轮，超过则 BLOCKED 升级用户

## 命名强制规则
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Hook 脚本**：snake-case（`context-guard.sh`、`completion-gate.sh`），与 harness.yaml key 保持连字符一致
- **Python 脚本**：snake_case（`context_monitor.py`、`oma_lock_manager.py`）
- **Skill 目录**：`lx-` 前缀（`lx-rpe`、`lx-oma-split`），SKILL.md 主文件
- **YAML key**：snake_case（`hooks_enabled.completion_gate`），与脚本调用一致
- **版本号**：始终 `v6.1.9-stable` 格式，VERSION.json 无前缀 `6.1.9`

## 错误处理铁律
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Hook 永不阻塞**：任何失败必须 `exit 0` 或 `echo '{"continue": true}'` + `exit 0`
- **证据门禁优先**：错误修复后必须提供 VERIFIED 证据再标 completed
- **Error DNA 捕获**：Bash 错误自动记录至 `error-dna.jsonl`，使用 `error_classifier.py` 分类
- **修复 3 轮上限**：每轮记录根因假设，第 3 轮仍失败 → BLOCKED 升级

## 测试要求
<!-- 由 R17 审计填充 @2026-05-07 -->
- **Harness Smoke**：修改 hook 后必须通过 `harness-smoke-test.sh`（动态计数，全绿为 pass）
- **Hook 生产验证**：`hook-production-verify.sh`（动态计数，全绿为 pass）覆盖所有 gate 场景
- **OMA Lock 测试**：修改锁逻辑后必须运行 `test_oma_lock.py`
- **版本审计**：修改版本号后必须运行 `audit-hooks.sh` 确认三方对齐

## 禁止行为
<!-- 由 R17 审计填充 @2026-05-07 -->
- 禁止在 Hook 脚本中设置 `set -e`（会阻断工具调用）
- 禁止 `eval`（当前 0 处，保持零容忍）
- 禁止未引用 `file:line` 的技术断言（铁律 #1）
- 禁止在报告中混合自创指标与行业标准（铁律 #7）
- 禁止在 `for x in $VAR` 中使用未加引号变量（R24 教训）
