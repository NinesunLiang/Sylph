---
name: lx-dogfood
version: v1.0.0
description: 主动投喂狗粮 — 事故发生时趁热记录，处理完毕时提炼教训，让 Carror OS 和你意念通达
category: workflow
type: workflow
execution_mode: stepwise
enabled_by_default: true
when_to_use: "Use when user experiences an incident, discovers a pitfall, or wants to record a lesson learned. Trigger: '狗粮', '投喂', 'dogfood', '记录教训', '记住这个教训'."
harness_version: ">=6.3.0"
status: stable
role: "Dogfood recorder — capture incidents hot, extract lessons"
evidence_level: L3
triggers:
  - "狗粮"
  - "投喂"
  - "喂狗粮"
  - "投喂狗粮"
  - "意念通达"
  - "趁热记录"
  - "记录教训"
  - "踩坑记录"
  - "喂经验"
  - "记住这个教训"
  - "dogfood"
  - "dog food"
  - "feed dogfood"
  - "dogfooding"
  - "incident report"
  - "eat your own dog food"
---

## 原子化声明

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/feed-protocol.md` | feed protocol 阶段 |
| `references/structure-ecosystem.md` | structure ecosystem 阶段 |

> 降级升级: @../reference/oma/degradation-escalation.md
> 裁决链: @../reference/oma/decision-chain.md
> 执行工作流: @../reference/oma/execution-workflow.md


# lx-dogfood — 主动投喂狗粮

> 踩坑了？一句话投喂，Carror OS 越用越聪明。哲学 #7(文档优先) + #4(没验证=没做) + #5(一句话不打断心流)。

## 触发

一句话激活：`狗粮` `投喂` `记录教训` `dogfood` 等（完整触发词见 frontmatter triggers）。
主路径：`/lx-dogfood "问题经过 + 怎么修的"` → 记录→提炼→入 claude-next.md。可选两步模式见 references/feed-protocol.md。

---

## 执行协议

### 投喂（主路径，一条命令）

AI 执行：
1. 捕获当前 git diff 作为上下文快照
2. 结合用户的描述 + 当前修复状态，提炼 1-3 条结构化教训
3. 写入 YAML → `.omc/state/dogfood/dogfood-{date}-{slug}.yaml`
4. 教训追加到 `.claude/claude-next.md`，格式：
   ```markdown
   ### 🐶 [DG-XX] {教训标题} (@{用户})

   @{日期} hits:1
   触发条件：{场景}
   正确行为：{怎么做}
   证据：{来源}
   ```
5. 输出总结：本次投喂的教训 + 狗粮编号 + "下次 AI 会记得这个教训"

### list — 查看历史

1. 列出 `.omc/state/dogfood/` 下所有记录，每项显示日期+标题+教训条数
2. 底部统计：累计狗粮数、累计教训数

## 狗粮记录结构

```yaml
# .omc/state/dogfood/dogfood-{date}-{slug}.yaml
meta:
  date: 2026-05-16
  author: {用户名}
  type: incident-report

incident:
  timestamp: {发生时间}
  description: "{原始描述}"

resolution:
  timestamp: {关闭时间}
  how_fixed: "{怎么修的}"
  lessons:
    - id: DG-XX
      title: "{教训标题}"
      trigger: "{触发条件}"
      correct_behavior: "{正确行为}"
      evidence: "{证据}"
```

---

## 联动机制

claude-next.md（教训追加）→ SessionStart 注入 → inject-project-knowledge（hits≥3 高频注入）→ kernel.md 升华。完整生态循环见 @references/structure-ecosystem.md。

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 主路径失败 | 手动记录到 claude-next.md |
| YAML 写入失败 | 降级为纯 markdown 记录 |

