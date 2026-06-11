# Ghost Phase 0: 前置澄清 + 激活

> 唯一的人类交互窗口。激活后 AI 不再提问。

## Step 0.1: 方向自检

AI 检查方向适合性：
- "探索/扫描/修复/迭代" 等增量关键词 → ghost mode
- "分析/报告/评估/阅读" 等一次性关键词 → 建议 goal mode
- 区分不清 → 向人类说明理由，推荐模式

## Step 0.2: 扫描不确定项

**核心原则：一次问清，永不回头。**

扫描维度（必须全部覆盖）：

| 维度 | 必须澄清的内容 |
|------|-------------|
| 范围边界 | 探索范围？哪些明确不在范围内？ |
| 硬边界预检 | 是否涉及 rm/git写/敏感文件/API Key？ |
| 外部依赖 | 需要哪些外部服务/API/工具？ |
| 能力缺口 | AI 是否具备完成探索的能力？缺口如何降级？ |
| 风险点 | 最可能失败的环节？降级策略？ |
| 探索方向 | 具体探索目标和预期发现？ |
| 成功信号 | 如何判断方向已达成？ |
| 过期策略 | 预计耗时？超时后如何处理？ |

## Step 0.3: 输出探索计划

展示：探索方向、每轮操作粒度（一步一操作）、预计轮询间隔、已识别风险、Q 项。回复 "开始" 激活。

## Step 0.4: 激活

人类 + Oracle 双确认后激活。

```bash
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "方向" [间隔秒] [过期小时] [最小迭代数]
```

此命令创建 `.omc/state/tokens/lx-ghost.json` + `.omc/state/tokens/autonomous.active`。

**激活后验证**：
```bash
ls -la .omc/state/tokens/lx-ghost.json .omc/state/tokens/autonomous.active
```

**为什么必须走脚本**：手动 touch 一个文件 = 半个系统仍在 normal mode（DG-46 教训）。

## CronCreate 轮询

```bash
# cron: */N * * * *（N = 间隔分钟，≥1）
# prompt: "根据 lx-ghost.json 方向做一步探索，更新状态。方向: {方向描述}"
# recurring: true
```

告知用户 job ID + Oracle 裁决结果，可随时 CronDelete 停止。
