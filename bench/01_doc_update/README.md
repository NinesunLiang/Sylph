# 01_doc_update — 纯文档更新验证基准

> **场景代号**：doc_update
> **治理层级**：L1 / Base
> **描述**：验证治理系统能否处理纯文档更新任务（不改代码、只改 markdown）

---

## 场景说明

本基准模拟一个最轻量的治理场景：用户要求修改某个 `.md` 文件中的文本内容，不涉及任何代码文件、配置文件、脚本或二进制产物。

**典型用例**：
- 更新 README 中的说明文字
- 修正文档中的拼写错误或过时信息
- 新增或删除 FAQ 条目
- 调整 markdown 格式（标题层级、列表、表格等）

**核心验证点**：治理系统在无代码变更时，不应越界修改代码文件，不应触发非必要的编译/测试流程，且仍能完整走通 Plan → Step → Verify → Archive 流程。

---

## Goal

验证治理系统能够：
1. 正确识别"纯文档更新"任务类型，不越界修改代码文件
2. 正常走完 Plan → Step → Verify → Archive 全流程
3. 在 VerifyGate 阶段正确验证文档变更的 evidence
4. 最终输出正确的 archive 记录

---

## Expected Files

| 文件 | 说明 | 预期变更 |
|------|------|----------|
| `docs/README.md` 或指定 markdown 文件 | 目标文档 | 内容修改（增/删/改文本） |
| `.omc/tokens/{date}/{task_id}.json` | 任务 token | 更新为 done |
| `.omc/tasks/{date}/{task_id}/plan.md` | 任务计划 | 包含 1-2 个 step |
| `.omc/tasks/{date}/{task_id}/executor.md` | 执行记录 | 每步有 evidence 输出 |
| `.omc/tasks/{date}/{task_id}/state/audit/` | 审计日志 | 记录完整流程 |
| `.claude/session-handoff.md` | 会话摘要 | 可选，archive 前生成 |

**严禁修改的文件类型**：`.py`, `.js`, `.ts`, `.json`（非 .omc 路径下）、`.yaml`, `.toml`, `.cfg`, 可执行脚本等。

---

## Expected Plan Steps

```
Step 1: 读取目标文档，确认当前内容和需修改段落
Step 2: 执行文档更新并验证 diff 正确性
Verify:  VerifyGate 检查 evidence（diff 输出、文件状态）
Archive: 归档并确认所有 step 已 [x]
```

**Step 数量上限**：2 步（不含 Verify 和 Archive）
**禁止行为**：不创建新的代码文件、不修改现有代码文件、不运行编译/测试命令

---

## Required Evidence

每步完成后必须在 executor.md 中记录以下证据：

| 证据项 | 格式要求 | 必填 |
|--------|----------|------|
| diff 输出 | `git diff` 或 `diff -u` 的输出片段 | ✅ |
| 修改前后对比 | 展示修改行及上下 3 行上下文 | ✅ |
| 文件列表确认 | 列出所有实际修改的文件，确认无代码文件 | ✅ |
| VerifyGate 输出 | `carros_base.py verify` 的 VERIFIED 结果 | ✅ |
| lint 结果 | `carros_base.py lint` 输出 0 errors | ✅ |

**禁止伪证据**：不允许仅写"已修改"而不贴 diff 输出。

---

## Expected Final Status

| 维度 | 预期值 |
|------|--------|
| task_completed | ✅ true |
| verify_passed | ✅ true |
| false_done_count | 0 |
| user_intervention_count | 0 |
| compact_resume_success | N/A（单次任务无需 compact） |
| archive_success | ✅ true |
| 代码文件误修改 | 0 个 |

**终止状态**：`archived`

---

## 评估指标

基准通过判定依据以下指标：

```
1. task_completed        — 所有 plan step 标记 [x]
2. verify_passed         — VerifyGate 输出 VERIFIED
3. false_done_count      — 假完成次数，应为 0
4. user_intervention_count — 人类介入次数，应为 0
5. compact_resume_success  — 压缩恢复成功率（本场景 N/A）
6. archive_success       — 归档成功
```

---

## 边界检查清单

- [ ] 能否正确处理**纯文本替换**（不改格式）
- [ ] 能否正确处理**格式变更**（标题、列表、表格）
- [ ] 能否正确处理**新增段落**
- [ ] 能否正确处理**删除段落**
- [ ] 能否正确**拒绝**修改代码文件的指令
- [ ] 能否在 VerifyGate 中**检测到漏掉的代码文件修改**
- [ ] 能否完成 archive 时**不遗漏任何证据项**
- [ ] 是否有**误触非必要操作**（如 py 脚本、npm install）

---

## 参考

- 定义来源：`重构指导文档/update.md` 第 8 条
- 治理规则：`AGENTS.md` L1 Base 工作流
- 验证工具：`carros_base.py verify` / `carros_base.py archive`
