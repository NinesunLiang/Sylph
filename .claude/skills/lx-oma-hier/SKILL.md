---
name: lx-oma-hier
description: 分层 PRD 拆解 — 将超大型 PRD 按功能域 MECE 拆分为多个 Sub PRD（黑盒/接口契约/Mock 数据/内部闭环），再委托 lx-oma-split 拆解为特性级 RPE。
version: v1.3.2
harness_version: ">=6.3.0"
status: stable
argument-hint: "<path> [output_dir]"
when_to_use: |
  当需要将超大型 PRD 按功能域 MECE 拆分为多个独立的 Sub PRD，
  每个 Sub PRD 定义接口契约、Mock 数据、黑盒边界、依赖关系和验收条件，
  并可进一步委托 lx-oma-split 拆解为特性级 RPE。
triggers: ["/lx-oma-hier", "分层拆解", "prd 拆分"]
role: "PRD hierarchical decomposer — master PRD to Sub PRDs (Level 1)"
execution_mode: stepwise
---
# lx-oma-hier 分层 PRD 拆解大脑

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| explore | `../../nodes/explore.md` | 读取 PRD 文件/目录，识别核心业务实体 |

| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/error-codes.md` | error codes |
| `references/observability.md` | observability |
| `references/pipeline.md` | pipeline |
| `references/sub-prd-template.md` | sub prd template |
| `references/verification-gate.md` | verification gate |

> 共享能力: 降级升级 `@../references/oma/degradation-escalation.md` · 裁决链 `@../references/oma/decision-chain.md` · 执行工作流 `@../references/oma/execution-workflow.md` · 链式承接 `@../references/oma/skill-chaining.md`

状态机: `need_input → [reading → analyzing → generating → verifying] → done`

## 任务目标

将超大型 PRD 按功能域 MECE 拆分为 N 个 Sub PRD，确保功能正交、黑盒边界、可独立闭环、可独立交付。
> Sub PRD 模板 → `@references/sub-prd-template.md` · 全生命周期管线 → `@references/pipeline.md`

## 参数处理

入参 `<path>` + 可选 `[output_dir]`。模式：`--pipeline` 编排模式 / 无参数 手动模式。
输出路径: kernel.md 约定 → 用户显式 → 默认 `sub-prds/`。
文件直接读、目录读所有 `.md`、图片描述结构。

## MECE 功能域拆解

1. **识别核心业务实体** → 实体归属表（实体名/候选域/归属理由/原文引用）
2. **按职责聚类** → 围绕实体聚合功能
3. **正交性校验** → 域对检查职责重叠+数据交叉
4. **边界确认** → 每个域"管什么/不管什么"

### MECE 校验摘要
- 正交性矩阵: 域对×重叠点×裁决（引用原文）
- 实体唯一 Own、接口耦合度(>10 警告)、孤儿接口检查、NFR 来源校验(无来源标注 `[内部自检]`)

### 依赖分析
域间依赖图（A→B），区分服务依赖 vs 代码依赖，识别循环依赖，标注优先开发域。

## 输出目录结构

```
{output_dir}/
  INDEX.md              ← 层级关系树 + 依赖图 + 开发顺序
  domain-{name}.md      ← Sub PRD
```

## 校验与门禁

```bash
python3 .claude/scripts/verify_oma_mece.py {output_dir}/  # exit 0 → ✅
```

质量报告: verify_oma_mece.py exit_code + 模板字段8项 + 非功能契约一致性 + 父需求全覆盖。
G1 Meta-Oracle: ≥2子系统+不可逆变更时触发 → `@references/verification-gate.md#meta-oracle-g1`

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |
| Sub PRD 输出失败 | 保留中间产物，标注缺失项 |
| MECE 校验 3 轮未通过 | 标记需人工介入 |
