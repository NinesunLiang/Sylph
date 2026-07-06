# Phase 0: 前置澄清窗口

> 唯一的人类交互窗口。激活后 AI 不再提问。引用：`@references/phase0-activation.md`

## Step 0.1: 解析目标

有完整目标描述 → 直接进入 Step 0.2。无参数 → 问一句话目标。

## Step 0.2: AI 主动扫描不确定项

**核心原则：一次问清，永不回头。** 所有可能需要人类决策的事项，必须在此窗口一次性列出。激活后 AI 不再提问。

| 维度 | 必须澄清的内容 |
|------|-------------|
| **范围边界** | 目标的确切边界是什么？哪些明确不在范围内？ |
| **硬边界预检** | 目标是否涉及 rm/git写/敏感文件/API Key？如是，预记录为硬边界跳过项 |
| **外部依赖** | 需要哪些外部服务/API/工具？是否有替代方案？ |
| **能力缺口** | AI 是否具备完成目标的所有能力？缺口如何降级？ |
| **风险点** | 最可能失败的环节是什么？各环节的降级策略？ |
| **执行顺序** | 子任务间的依赖关系？哪些可以并行？ |
| **验收条件** | 每个子任务的完成标准是什么？如何验证？ |
| **过期策略** | 预计耗时多久？超时后如何处理未完成项？ |

## Step 0.3: 输出执行计划 + 不确定项清单

展示：子任务列表（含验收条件、依赖）、所有 Q 项一次性列出、已识别风险及策略。回复 "开始" 激活。

## Step 0.4: 激活（物理执行，不可跳过）

人类确认"开始"后，AI 必须**立即执行激活脚本**（不先做任何其他操作）。这是硬步骤，不可跳过、不可手动替代。

```bash
python3 .claude/skills/lx-goal/scripts/lx-goal.py on "{目标描述}"
```

此命令创建两个信号文件：
- `.omc/state/tokens/lx-goal.json` — `is_mode_active()` 读取此文件判断是否为 goal 模式
- `.omc/state/tokens/autonomous.active` — hook 据此降级

**激活后验证**：
```bash
ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active
```

**为什么必须走脚本**：手动 `touch autonomous.active` 只创建一个文件，`is_mode_active()` 读取 `lx-goal.json` 而非 `autonomous.active`，半个系统仍在 normal mode（DG-46 教训）。

## 跨会话恢复（长目标）

激活时调用 CronCreate 注册轮询：
- cron: `*/10 * * * *`（每 10 分钟检查）
- prompt: `检查 lx-goal.json 状态，如果激活且未过期，继续执行下一个未完成的子任务`
- recurring: true
