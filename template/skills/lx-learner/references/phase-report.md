# Phase 5: 报告 (REPORT)

加载 `@../../nodes/report_generator.md`。

```
## /learner 提取报告 ✅

### 检测到的模式
- 类型：{pattern_type}
- 重复次数：{N}
- 置信度：{high/medium}

### 创建的技能
- lx-{name}: .claude/skills/lx-{name}/
  - SKILL.md ({N} 行)
  - references/conversation_provenance.md

### 验证结果
- 结构检查：{通过/失败}（{N} 轮修复）
- 引用检查：{通过/失败}

### 注册
- feature-registry.yaml: 已更新
- skills-catalog.md: 已更新

### 下一步
1. 审查 SKILL.md — 确保提取的行为匹配你的意图
2. 审查来源文档 — 确认对话摘录准确
3. 手动 git add .claude/skills/lx-{name}/
4. 或用 /lx-{name} 立即测试
```
