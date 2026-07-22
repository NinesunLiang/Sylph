# 投喂执行协议

## 主路径：一条命令投喂

AI 执行 5 步：
1. 捕获当前 git diff 作为上下文快照
2. 结合用户描述 + 修复状态，提炼 1-3 条结构化教训
3. 写入 YAML → `.omc/state/dogfood/dogfood-{date}-{slug}.yaml`
4. 教训追加到 `.claude/claude-next.md`：
   ```markdown
   ### 🐶 [DG-XX] {教训标题} (@{用户})
   @{日期} hits:1
   触发条件：{场景}
   正确行为：{怎么做}
   证据：{来源}
   ```
5. 输出总结：教训 + 狗粮编号 + "下次 AI 会记得"

## list — 查看历史

1. 列出 `.omc/state/dogfood/` 下所有记录
2. 每项：日期、标题、教训条数
3. 统计：累计狗粮数、累计教训数

## 可选：两步投递

| 命令 | 语义 |
|------|------|
| `/lx-dogfood incident "感受"` | 事故中趁热记录原始描述 |
| `/lx-dogfood close "修复+教训"` | 处理后关闭，关联之前 incident |
