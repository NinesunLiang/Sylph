# 交叉验收测试方案

> 测试目标：验证 completion-gate 的 A→B→A 交叉验收提醒是否按设计工作
> 生成终端：A
> 验收终端：B（另开终端，换模型执行）

---

## 测试用例

### TC-1：代码任务不触发提醒

| 项 | 值 |
|---|------|
| 前置 | evidence 文件存在且内容不含关键词 |
| 证据内容 | `测试通过，go test ./... → PASS (12/12)，VERIFIED` |
| 操作 | 标记 TaskUpdate status=completed |
| 期望 | exit 0，无额外输出 |
| 注意 | 此处"无额外输出"仅指 completion-gate 的 stderr，不含其他 hook 的并发输出 |

### TC-2：报告任务触发提醒

| 项 | 值 |
|---|------|
| 前置 | evidence 文件存在且内容含「报告/方案/验收/通过率」等关键词 |
| 证据内容 | `通过率报告完成，合规映射一致，VERIFIED` |
| 操作 | 标记 TaskUpdate status=completed |
| 期望 | exit 0，打印交叉验收提醒框 |

### TC-3：方案类任务触发提醒

| 项 | 值 |
|---|------|
| 前置 | evidence 含「方案/计划/design/proposal」关键词，且 ≥20 字符 |
| 证据内容 | `安全审计方案已完成并验证, VERIFIED`（22 字符） |
| 操作 | 标记 TaskUpdate status=completed |
| 期望 | exit 0，打印交叉验收提醒框 |

### TC-4：无 evidence 文件时阻断

| 项 | 值 |
|---|------|
| 前置 | evidence 文件不存在；feature-registry.yaml 存在（`feature-registry.yaml:134-139` 定义 evidence_level: L3） |
| 操作 | 标记 TaskUpdate status=completed |
| 期望 | exit 2，打印阻断表格（含"预期证据级别 L3"） |

### TC-5：evidence 过短时阻断

| 项 | 值 |
|---|------|
| 前置 | evidence 文件存在但内容 < 20 字符 |
| 证据内容 | `done` |
| 操作 | 标记 TaskUpdate status=completed |
| 期望 | exit 2，打印内容过短提示 |

---

## 验收标准

- [ ] TC-1：代码任务静默通过，无提醒
- [ ] TC-2：报告任务打印提醒框
- [ ] TC-3：方案任务打印提醒框
- [ ] TC-4：无 evidence 时阻断任务
- [ ] TC-5：evidence 过短时阻断任务
- [ ] 所有 exit code 符合预期

---

## 验收方法

在 B 终端执行以下命令（替换 `{path}` 为实际路径）：

```bash
# TC-1
echo '测试通过，go test all green, VERIFIED' > {path}/.omc/state/.completion-evidence-$(date +%Y%m%d)
echo '{"tool_input": {"status": "completed"}}' | bash {path}/.claude/hooks/completion-gate.sh 2>&1
echo "exit: $?"

# TC-2
echo '通过率报告完成，合规映射一致, VERIFIED' > {path}/.omc/state/.completion-evidence-$(date +%Y%m%d)
echo '{"tool_input": {"status": "completed"}}' | bash {path}/.claude/hooks/completion-gate.sh 2>&1
echo "exit: $?"

# TC-3
echo '安全审计方案已完成并验证, VERIFIED' > {path}/.omc/state/.completion-evidence-$(date +%Y%m%d)
echo '{"tool_input": {"status": "completed"}}' | bash {path}/.claude/hooks/completion-gate.sh 2>&1
echo "exit: $?"

# TC-4
rm -f {path}/.omc/state/.completion-evidence-$(date +%Y%m%d)
echo '{"tool_input": {"status": "completed"}}' | bash {path}/.claude/hooks/completion-gate.sh 2>&1
echo "exit: $?"

# TC-5
echo 'done' > {path}/.omc/state/.completion-evidence-$(date +%Y%m%d)
echo '{"tool_input": {"status": "completed"}}' | bash {path}/.claude/hooks/completion-gate.sh 2>&1
echo "exit: $?"
```

---

## 测试环境

| 项 | 值 | 来源 |
|---|------|------|
| 项目 | Carror OS | `VERSION.json:1` |
| 版本 | v6.1.8 | `VERSION.json:3` |
| Hook | `.claude/hooks/completion-gate.sh` | 文件存在 |
| 配置文件 | `.claude/harness.yaml`（completion_gate.enabled=true） | `harness.yaml:59-63 + :103` |
| 特征注册表 | `.claude/feature-registry.yaml`（completion-gate evidence_level: L3） | `feature-registry.yaml:134-139` |
| 测试日期 | 2026-05-05 | 文档生成时间 |
