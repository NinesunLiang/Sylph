# T06 — 深度治理

> 📍 怎么管大项目 | [← T05](tutorial-05.md) | 终章 →

**TL;DR**: OMA 管线拆需求 → 审判系统验质量 → 你的代码。下面展开。

## OMA 管线：一人成军

把 400 行 PRD 变成可执行的 feature 链路：

```
/lx-oma-hier  — 拆大 PRD 为 Sub PRD（按功能域 MECE 分裂）
  → /lx-oma-split — Sub PRD 拆为正交 Feature
    → /lx-oma-orch — 编排执行（状态/推进/门禁/并行管理）
      → /lx-oma-gov — 需求变更时增量同步、漂移检测
```

每一层压着下一层。子不认父 = 孤儿 = 被 gov audit 报漂移。

## 审判系统：Oracle 与 Meta-Oracle

### Oracle — 常规守门员
AI 说"做完了"之前，先过 Oracle 这一关。Oracle 是独立 spawn 的 critic agent——不共享上下文、不共享推理链。它只看物理证据：文件、exit code、sha256。

Oracle 的裁决只有三个词：`ACCEPT`、`REVISE`、`REJECT`。

### Meta-Oracle — 最后守门员
连 Oracle 都信不过的时候，Meta-Oracle 出手。只在四个关键点触发：架构决策 → PRD 方案终审 → Oracle 高分 ACCEPT → Release 门禁。

它的判决是软门禁——AI 可以在书面理由下覆写。但连续两次 REJECT → 事实阻断，必须人工介入。

---

## 全景

```
你的需求 → OMA 管线拆解 → lx-rpe 执行 → lx-code-review 审查
  → lx-pre-commit 门禁 → Oracle 审判 → 你的代码
                                   ↓
                            Meta-Oracle（只在关键时刻）
```

---

← [T05 自主执行](tutorial-05.md) | 终章 →
📖 深入：[Oracle vs Meta-Oracle 实战](oracle-meta-oracle-adversarial-review.md) | [OMA 铸造厂故事](../story/cn/story-07.md)
