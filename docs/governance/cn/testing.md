# Carror OS v6.1.9 测试指南

> **版本**：v6.1.9 | **日期**：2026-05-13
> **HARNESS 实测总分**：127.2 / 130
> **测试结果**：BDD 10 PASS / 0 FAIL / 2 SKIP + L1\~L4 继承
---
## v6.1.8 新增内容
| 新增 | 验证命令|
|:---|:---|
| plan-gate 自动检测 rpe/ | `mkdir -p rpe/test && echo '## Step 1' > rpe/test/executor.md && echo '{"tool_input":{"file_path":"rpe/test/plan.md"}}' | bash .claude/hooks/plan-gate.sh; echo $?` → 2|
|bdd-harness-test.sh | `bash .claude/hooks/bdd-harness-test.sh` → 10P/0F/2S |
---
## BDD 场景测试
```bash
# 运行全部场景bash .claude/hooks/bdd-harness-test.sh
# 运行单个场景bash .claude/hooks/bdd-harness-test.sh scenario_H_plan_gate_auto
# 列出所有场景bash .claude/hooks/bdd-harness-test.sh --list
```
**10 个 BDD 场景**：

| ID | 场景 | 类型|
|:---|------|:----:|
|A | AI 无证据声称完成 → 阻断 | 自动|
|B | AI 提供有效证据 → 放行 | 自动|
|C | 范围外文件编辑预警 | SKIP（需路径）|
|D | 第20轮写文件 → 铁律注入 | 自动|
|E | 漂移词「顺手」→ 预警升级 | 自动|
|F | AI 执行 git push → 阻断 | 自动|
|G | 用户纠正信号 → 写教训提醒 | 自动|
|H | rpe/ 存在 → plan-gate 自动启用 | 自动（v6.1.3）|
|I | 无 rpe/ → plan-gate fail-open | 自动（v6.1.3）|
|J | 真实 AI 对话验证 | SKIP（需 API） |
---
## plan-gate 自动检测验证
```bash
# 场景 H：有 rpe/ 时自动阻断mkdir -p .omc/state rpe/my-featcat > rpe/my-feat/executor.md << 'EOF'## Step 1 — 实现EOFINPUT='{"tool_input":{"file_path":"rpe/my-feat/plan.md","new_content":"test"}}'echo "$INPUT" | bash .claude/hooks/plan-gate.sh; echo "exit: $?"# 期望: exit: 2（Research Gate BLOCKED）
# 场景 I：无 rpe/ 时 fail-openrm -rf rpe/echo "$INPUT" | bash .claude/hooks/plan-gate.sh; echo "exit: $?"# 期望: exit: 0（放行）
```
---
## 继承 v5.3.0 的全量测试
见 v5.3.0 TESTING.md，L1\~L4 测试结果：**98 PASS / 0 FAIL / 0 SOFT**
---
**Carror OS — AI Native Developer Operating System。**
## 平台兼容性验证
```bash
# 安装后确认两个文件都存在ls -la AGENTS.md CLAUDE.md
# 确认 CLAUDE.md 使用 @-include 跳板格式head -1 CLAUDE.md # 期望: @AGENTS.md
# 确认 AGENTS.md 含治理内容grep "Project 宪法|铁律|VERIFIED" AGENTS.md | wc -l # 期望 ≥5
# OpenCode 平台：直接读 AGENTS.md（无需 CLAUDE.md）# Claude Code 平台：读 CLAUDE.md → @AGENTS.md 展开 → 加载治理内容
```
**平台支持矩阵**：

| 平台 | 启动文件 | hooks 治理 | skill 能力|
|------|---------|-----------|-----------|
|Claude Code | CLAUDE.md（@AGENTS.md）| ✅ 30 hooks | ✅|
|Codex CLI | `.codex/hooks.json`（自动生成）| ✅ 11 hooks | ❌ |
|Gemini CLI | `.gemini/settings.json`（自动生成）| ✅ 11 hooks | ❌ |
|Qwen Code | `settings.json`（自动生成）| ✅ 11 hooks | ❌ |
|Cursor | `.cursor/hooks.json`（自动生成）| ✅ 2 hooks | ❌ |
|OpenCode | AGENTS.md（原生）| ✅ 5 hooks（插件）| ✅|
|CLAUDE.md 兼容 IDE | CLAUDE.md（@AGENTS.md）| ❌ | ✅ |
