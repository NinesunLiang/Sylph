# Skill 链式承接 (Skill Chaining)

> 所有 OMA skill 的链式组合模式。引用：`@reference/oma/skill-chaining.md`

## 链式组合哲学

单个 skill = 原子操作。链式组合 = 原子 skill 按契约串联成完整流水线。

```
原子 skill A ──契约──→ 原子 skill B ──契约──→ 原子 skill C
```

每个 skill 只关心自己的输入/输出契约，不感知上下游实现。

## 主链：PRD 全生命周期

```
lx-oma-hier ──→ lx-oma-split ──→ lx-rpe ──→ lx-code-review ──→ lx-test-gen
 (主PRD→Sub)    (Sub→Feature)    (开发)      (审查)            (测试)
      │               │              │            │                │
      └── 输出: Sub PRD ──┘             │            │                │
               └── 输出: Feature RPE ───┘            │                │
                         └── 输出: 代码 ─────────────┘                │
                                   └── 输出: 审查报告 ────────────────┘

链式调用:
  1. /lx-oma-hier docs/master-prd.md --pipeline
  2. /lx-oma-split sub-prds/domain-auth.md --pipeline
  3. /lx-rpe prd/auth/feat-login --pipeline
  4. /lx-code-review
  5. /lx-test-gen
```

## 治理链：变更检测 & 传播

```
lx-oma-gov ──→ lx-oma-split ──→ lx-rpe
 (检测变更)     (重拆)          (重开发)

链式调用:
  1. /lx-oma-gov reconcile          # 检测主 PRD 变更
  2. /lx-oma-gov propagate --execute # 传播到 feature
  3. /lx-oma-split <changed>        # 重拆受影响的 feature
  4. /lx-rpe <feature>              # 重新开发
```

## 编排链：自动推进

```
lx-oma-orch auto
   ↓ 读 pipeline.yaml
   ├── hier_done? → 触发 split
   ├── oma_ready? → 触发 rpe
   ├── dev_done?  → 触发 code-review
   └── review_done? → 触发 test-gen

每个阶段有 Oracle gate，orch 自动推进。
```

## 审判链：双法官审核

```
Oracle Agent ──→ Meta-Oracle ──→ 人类
 (静态分析)       (运行时+对抗)    (最终裁决)

嵌入任意链式流程：
  hier → [Oracle → Meta-Oracle] → split → [Oracle] → rpe → [Oracle → Meta-Oracle] → 交付
```

## 组合规则

### 契约传递

上游输出 → 下游输入必须是结构化契约：

```
上游 SKILL.md:
  输出: `sub-prds/domain-{name}.md`

下游 SKILL.md:
  输入: `<sub_prd_path>`（Sub PRD markdown 文件）
```

### 独立可执行

链中任意 skill 可以独立调用，不依赖链上历史：

```
✅ /lx-oma-split sub-prds/domain-auth.md     # 独立执行
✅ /lx-rpe prd/auth/feat-login               # 独立执行
```

### 去重

如果两个 skill 的公共能力相同 → 提取到 `reference/oma/`：

| 公共能力 | 引用路径 |
|---------|---------|
| 裁决链 | `decision-chain.md` |
| 执行工作流 | `execution-workflow.md` |
| 降级升级 | `degradation-escalation.md` |
| Pipeline 契约 | `pipeline-contract.md` |
| 可观测性 | `observability.md` |
| 错误码 | `error-codes.md` |
| 方向指引 | `direction-guide.md` |

## 并发链：Race 模式

```
lx-race
  ├── Task A: lx-rpe feat-A        (并行)
  ├── Task B: lx-rpe feat-B        (并行)
  └── Task C: lx-rpe feat-C        (并行)
       ↓
  聚合报告 → lx-oma-orch 更新 pipeline
```

独立子任务（互不依赖）→ Race 并发。有依赖 → Stepwise 串行。
