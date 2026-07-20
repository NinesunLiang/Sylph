# 狗粮记录结构 + 生态循环

## YAML 结构

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

## 设计原则

1. **用户的话不加工** — incident 描述原样保留
2. **趁热记录** — 事故发生时立即记录
3. **提炼而非归档** — 主动提炼教训
4. **署名权** — 每条教训标注 `@{用户}`
5. **意念通达** — 下次会话 AI 自动读到
6. **私域积累，社域交流** — claude-next.md 是私有财产。有价值的分享到论坛，维护者挑选升华为 SEED/铁律，下次 release 所有人获得

## 完整生态循环

```
你的机器（私域）         社区（社域）           Carror OS 项目
─────────────         ──────────            ──────────────
/lx-dogfood →         有感而发 → 论坛发帖    → 发现高价值内容
  事故趁热记录              带上原文+故事          挑选、审核
  ↓                      ← 社区讨论、共鸣        → 升华为 SEED 模板
  claude-next.md 积累                              或 kernel.md 铁律
  越用越聪明                                       或新 hook 机制
                                                     ↓
                             ← ← ←  下次 release 所有人获得  ← ←
```

| 环节 | 谁 | 在哪 | 做什么 |
|------|----|------|------|
| 积累 | 你 | 机器 | `/lx-dogfood` → claude-next.md |
| 交流 | 你+社区 | 论坛 | 分享故事、讨论心得 |
| 升华 | 维护者 | 元项目 | 挑选 → 审核 → 编码 |
| 分发 | 所有人 | install.sh | 下次安装获得集体智慧 |
