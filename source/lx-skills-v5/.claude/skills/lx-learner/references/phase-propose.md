# Phase 1: 提议提取 (PROPOSE)

加载 `@../../nodes/interactive_prompt.md` + `@../../nodes/explore.md`。

## Step 1.1: 查重

探索 `.claude/skills/` 检查是否已有类似技能。若存在 → 警告用户。

## Step 1.2: 展示证据

使用 AskUserQuestion：

```
🔍 检测到重复模式：[类型]

证据：
1. [描述 + 上下文引用]
2. [描述 + 上下文引用]
3. [描述 + 上下文引用]

该操作在本次对话中出现了 {N} 次。

提取为可重用 skill？
```

选项：
- **"是，提取 lx-{suggested_name}"** → 继续 Phase 2
- **"修改方案"** → 用户自定义技能名称/范围 → 继续 Phase 2
- **"不，忽略"** → 退出

## 输出格式

```json
{
  "proposed_name": "lx-dockerfile-review",
  "scope": "Dockerfile 安全漏洞和最佳实践审查",
  "triggers": ["审查 dockerfile", "dockerfile check"],
  "confirmed": true
}
```
