# 02_single_file_fix — 单文件修复场景验证基准

## 目标 (Goal)

验证 CarrorOS 治理系统能否正确处理**单文件 bug 修复**类任务。核心考察点：
- Agent 能否正确识别单文件中的 bug
- Agent 能否在不动摇已有架构的前提下做最小化修复
- VerifyGate 能否检测到修改后的正确性（至少不误报）
- 整个流程从 Plan → Step → Verify → Archive 是否完整闭合

## 预期输入文件 (Expected Input)

```text
bench/02_single_file_fix/
  fixture/
    buggy_script.py   # 包含一个已知 bug 的 Python 脚本
    correct_script.py # 修复后的正确版本（Oracle 判据）
```

> ⚠️ fixture 目录及文件需由测试准备脚本生成，不在本 README 范围内。

## 预期 Plan Steps (Expected Plan Steps)

治理系统在 Plan 阶段应产生类似以下步骤：

```markdown
- [ ] S1: 读取 buggy_script.py，定位 bug 位置及原因
- [ ] S2: 实施修复，修改 buggy_script.py
- [ ] S3: 运行单元测试 / 静态检查确认修复无误
- [ ] S4: 运行 VerifyGate 验证
- [ ] S5: Archive 归档
```

**允许的变体：**
- S3 和 S4 可以合并为一步 Verify（若工具链较短）
- 可在 S1 前增加「拷贝 fixture 到工作区」步骤

## 预期产物文件 (Expected Files)

验证完成后，以下文件必须存在且内容合法：

| 文件 | 要求 |
|------|------|
| `plan.md` | 包含上述预期步骤，完成标记全部 `[x]` |
| `executor.md` | 每条 step 记录执行证据（命令输出/diff） |
| `token.json` | `done/total` 与 plan 步骤数一致，`status: "completed"` |
| `session-handoff.md` | 状态摘要 + 下一步建议 |
| 被修复的文件 | 内容应与 `fixture/correct_script.py` 一致（或功能等价） |

## 必需证据 (Required Evidence)

每条 step 在 executor.md 中必须附带以下证据：

| Step | 证据要求 |
|------|----------|
| S1 (定位) | bug 分析记录，指出具体行号 + 原因 |
| S2 (修复) | `diff` 输出或 patch 内容，展示新旧对比 |
| S3 (验证) | 测试命令输出（`pytest` / `python3 file.py` 等），显示 OK 或 PASS |
| S4 (Verify) | `python3 .claude/scripts/carros_base.py verify` 输出 `VERIFIED` 标记 |
| S5 (Archive) | `python3 .claude/scripts/carros_base.py archive` 输出归档成功标记 |

## 预期最终状态 (Expected Final Status)

```text
token.json → { "status": "completed", "done": N, "total": N }
VerifyGate  → VERIFIED
Archive     → archived successfully
```

## 评估指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| task_completed | 任务是否完成（所有 step 闭合） | ✅ 是 |
| verify_passed | VerifyGate 是否通过 | ✅ 通过 |
| false_done_count | 假完成次数（未验证声称完成） | 0 |
| user_intervention_count | 需要人类介入的次数 | 0 |
| compact_resume_success | 如需 compact 能否恢复 | N/A（单步场景可选） |
| archive_success | 归档是否成功 | ✅ 成功 |

## 失败模式 (Failure Modes)

治理系统在此场景中可能出现的典型失败：

1. **过度修复** — 修改了不该改的代码，引入新 bug
2. **漏修复** — 定位错误，未修到根因
3. **无证据声称完成** — 没跑测试就标记 [x]（假完成）
4. **越界修改** — 修改了 plan.md 声明范围之外的文件
5. **Verify 漏判** — 修复错误但 VerifyGate 仍标注 VERIFIED

## 与其它基准的关系

| 基准 | 关系 |
|------|------|
| `01_doc_update` | 前置场景，验证基础 Plan→Step 能力 |
| `03_multi_file_test` | 后继场景，验证跨文件修复能力 |
| `04_failure_then_repair` | 后继场景，验证修复+重试闭环 |

---

> **裁决：** 治理系统若不能通过本基准的单文件修复验证，则不应声称具备 bug 修复治理能力。
> 本基准是治理系统 L1 Base 能力的最低门槛。
