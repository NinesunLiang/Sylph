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

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md


# lx-dogfood — 主动投喂狗粮

> **踩坑了？一句话投喂，Carror OS 越用越聪明。**

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #7 | 文档优先 | 每次事故结构化记录，不依赖记忆 |
| #4 | 没验证=没做 | 投喂时验证教训已入 claude-next.md |
| #5 | 以人为本 | **一句话投喂**——处理完问题顺手喂，不打断心流 |

---

## 触发条件

**自然语言触发词**（无需 `/lx-dogfood` 前缀，直接说这些词即可激活）：
`狗粮` `投喂` `喂狗粮` `意念通达` `记录教训` `踩坑记录` `喂经验` `记住这个教训` `dogfood` `dog food`

| 输入 | 语义 | 行为 |
|------|------|------|
| `/lx-dogfood "问题经过 + 怎么修的"` 或 `"投喂狗粮" + 描述` | **处理完毕，顺手喂**（主路径） | 记录 → 提炼教训 → 入 claude-next.md → 一条命令收工 |
| `/lx-dogfood list` 或 `"看看狗粮"` | 查看历史 | 展示所有狗粮记录摘要 |

> **一句话就够了。** 不需要先 incident 再 close——那是旧版的两步模式（已降级为可选高级用法）。
> 处理完问题，说一句 `/lx-dogfood "刚才 X 出了问题，根因是 Y，修了 Z，教训是..."`，剩下的 AI 做。

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

AI 执行：
1. 列出 `.omc/state/dogfood/` 下所有记录
2. 每项显示：日期、标题、教训条数
3. 底部统计：累计狗粮数、累计教训数

### 可选：两步投喂（趁热记录 + 事后关闭）

> 仅当你希望在事故发生时先记录原始感受，等修复完毕后再补充教训时才用。

| 输入 | 语义 |
|------|------|
| `/lx-dogfood incident "当时的感受"` | 事故中趁热记录原始描述 |
| `/lx-dogfood close "怎么修的 + 教训"` | 处理完毕后关闭，关联之前的 incident |

---

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

## 与已有机制的联动

| 机制 | 联动 |
|------|------|
| claude-next.md | 教训自动追加，带 @作者署名 + hits 计数 |
| SessionStart 注入 | 下次会话 AI 自动读到本次教训 |
| inject-project-knowledge | 高频教训（hits≥3）在每轮注入 |
| knowledge-condenser | 稳定教训升华为 kernel.md 正式规范 |
| MEMORY.md | 项目级记忆，跨会话持久化 |

---

## 设计原则

1. **用户的话不加工** — incident 描述原样保留，不美化、不删减
2. **趁热记录** — incident 在事故发生时立即记录，不等到事后回忆
3. **提炼而非归档** — close 时主动提炼教训，不是死板的"关闭 issue"
4. **署名权** — 每条教训标注 `@{用户}`，让狗粮有归属感
5. **意念通达** — 下次 AI 醒来时，会读到这些教训，不需要你再说第二遍
6. **私域积累，社域交流** — claude-next.md 是你的私有财产。分享是人的行为：觉得某条教训有价值，带上原文去论坛/GitHub Discussions 发帖讨论。维护者从中挑选高价值内容升华为 SEED 模板或铁律机制，下次 release 时所有人自动获得

---

## 完整生态循环

```
你的机器（私域）                    社区（社域）                      Carror OS 项目
─────────────                    ──────────                       ──────────────
/lx-dogfood incident             →
  事故趁热记录                     
                               
/lx-dogfood close                →  有感而发 → 论坛发帖            → 发现高价值内容
  提炼教训                           带上 claude-next.md 原文         挑选、审核
  ↓                                   加上自己的故事                  
  claude-next.md 积累               ← 社区讨论、共鸣                → 升华为 SEED 模板
  越用越聪明                                                         或 kernel.md 铁律
                                                                     或新 hook 机制
                                                                      ↓
                              ← ← ←  下次 release 所有人自动获得  ← ←
```

| 环节 | 谁 | 在哪 | 做什么 |
|------|----|------|------|
| **积累** | 你 | 你的机器 | `/lx-dogfood` → claude-next.md |
| **交流** | 你 + 社区 | 论坛/GitHub Discussions | 分享故事、讨论心得 |
| **升华** | Carror OS 维护者 | 元项目 | 挑选 → 审核 → 编码为 SEED/铁律/hook |
| **分发** | 所有人 | install.sh | 下次安装自动获得集体智慧种子 |

> 不是 `/lx-dogfood share` 命令——交流不需要工具，需要人的温度。把你的教训带上原文，去论坛写一段经历，比任何自动化都更有价值。

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 主路径失败 | 手动记录到 claude-next.md |
| YAML 写入失败 | 降级为纯 markdown 记录 |

