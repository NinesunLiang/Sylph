---
name: lx-oma-hier

description: 分层 PRD 拆解 — 将超大型 PRD 按功能域 MECE 拆分为多个 Sub PRD（黑盒/接口契约/Mock 数据/内部闭环），再委托 lx-oma-split 拆解为特性级 RPE。

version: v1.3.0
harness_version: "6.2.0"
status: stable
model: sonnet
argument-hint: "<path> [output_dir]"
when_to_use: |
  当需要将超大型 PRD（单文件或目录）按功能域 MECE 拆分为多个独立的 Sub PRD，
  每个 Sub PRD 定义接口契约、Mock 数据、黑盒边界、依赖关系和验收条件，
  并可进一步委托 lx-oma-split 拆解为特性级 RPE。

triggers:
  - "/lx-oma-hier"
  - "分层拆解"
  - "prd 拆分"
role: "PRD hierarchical decomposer — master PRD to Sub PRDs (Level 1)"
execution_mode: stepwise
---

# lx-oma-hier 分层 PRD 拆解大脑

**触发语**: `/lx-oma-hier`, `分层拆解`, `prd 拆分`

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| explore | `../../nodes/explore.md` | 读取 PRD 文件/目录，识别核心业务实体 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |

### 状态机
need_input → [reading → analyzing → generating → verifying] → done

### 私有节点
本 skill 无私有节点。

## 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 输入路径不存在 | 报错 | 提示用户补充路径 |
| 输入为空文件 | 报错 | 输出"PRD 内容为空，无法拆解" |
| 读取的 PRD 内容过少（<200 字） | 按已有内容拆解 | 告知用户内容不足，建议补充后重新执行 |
| 输出目录已存在 | 覆盖写入 | 询问用户是否覆盖或指定新目录 |
| lx-oma-split 不可用（Level 2） | 委托调用 | 告知用户手动执行 `/lx-oma-split` 拆解 |
| Sub PRD 生成的字段不完整 | 自动补充 | 标记缺失字段为用户待办 |

## 1. 任务目标

将超大型 PRD 文档（或目录）按功能域 MECE 拆分为 **N 个 Sub PRD**，确保：
- **功能正交**：域间职责无重叠
- **黑盒边界**：域间只通过接口契约通信
- **可独立闭环**：每个域绑 Mock 数据可独立验证
- **可交付**：每个 Sub PRD 可独立进入开发

每个 Sub PRD 包含「功能边界、接口契约、非功能契约、Mock 数据、数据实体归属、依赖关系、父需求追溯、验收条件」完整字段。

完成后，可委托 `lx-oma-split` 对每个 Sub PRD 继续拆解为特性级 RPE。

## 2. 参数处理（Input）

入参是一条路径（`<path>`），由调用者附在触发语后（如 `/lx-oma-hier docs/prd-v3/` 或 `/lx-oma-hier master-prd.md`）。

### 2.1 执行模式检测

首先检测是否传入 `--pipeline` 参数：
- **编排模式**（含 `--pipeline`）：强制执行 §8 Pipeline 集成（写入 pipeline.yaml、telemetry）
- **手动模式**（无 `--pipeline`）：跳过 pipeline.yaml 写入，telemetry 按环境可用性决定，并在报告注明模式

### 2.2 输出路径优先级

输出目录按以下优先级确定：

1. **kernel.md 约定路径**：搜索项目 `.claude/kernel.md` 中 `OMA 路径约定` 节 → 若有约定则优先遵循（如 `main_prds/{sub_prd}/prd.md`）
2. **用户显式指定**：第二个参数 `<output_dir>` 指定的路径
3. **默认路径**：`sub-prds/`（输入的同级目录）

> 路径确定后必须向用户显式报告（"输出到：{路径}"），输出目录已存在时询问是否覆盖或指定新路径。

### 2.3 输入读取

1. 使用 Glob/Read 检查该路径。
2. 如果是文件，直接读取内容。
3. 如果是目录，读取该目录下所有 `.md` 文件内容作为上下文。
4. 如果有图片（`.png/.jpg/.svg` 等），在 `Read` 读取时描述其内容结构。
5. 如果未提供路径，向用户询问目标。

## 3. MECE 功能域拆解（Level 1）

运用顶级系统架构师思维，将主 PRD 拆解为 **N 个功能域（通常 3-8 个）**：

### 3.1 拆解方法论

1. **识别核心业务实体**：从 PRD 中提取主体概念（如：用户、订单、支付、商品、通知...）。**在生成任何文档前，必须显式输出实体归属表**，格式：
   ```markdown
   ## 核心业务实体识别
   | 实体名 | 候选归属域 | 归属理由 |
   |--------|-----------|---------|
   | {实体} | {域} | {引用 PRD 原文章节} |
   ```
   > 实体识别输出后，再检查实体冲突（同一实体被多个域候选），确认无冲突后再进入下一步。

2. **按职责聚类**：围绕每个实体，聚合其相关功能

3. **正交性校验**：每两个域之间检查——有没有功能重叠？有没有数据交叉？引用 PRD 原文章节作为证据

4. **边界确认**：明确每个域"管什么/不管什么"

### 3.2 MECE 校验（统一摘要表）

所有域生成后，统一输出 MECE 校验摘要表（不逐域输出 checkbox）：

**正交性矩阵**：对每两个域检查职责重叠，引用 PRD 原文章节作为证据
```markdown
| 域对 | 潜在重叠点 | 裁决 |
|------|-----------|------|
| D01 vs D02 | {检查项} | 不重叠 ✅（引用 PRD 原文 §X）|
```

**数据实体唯一 Own 验证**：确认无两个域同时声明"拥有"同一实体（同时检查表格行和散文描述）
```markdown
| 实体名 | Own 方 | 其他域声明 | 冲突状态 |
|--------|--------|-----------|---------|
```

**接口耦合度**：记录各域对外接口数，数量超标（>10）记录警告但标记为合理（业务复杂度决定）
```markdown
| 域 | 对外接口数 | 评估 |
|----|-----------|------|
```

**孤儿接口检查**：每个接口至少有一个已知调用方
**NFR 来源校验**：逐条确认 NFR 数字有主 PRD 章节来源；无来源则标注 `[内部自检，非行业标准]`

### 3.3 依赖分析

拆解完成后，绘制域间依赖图：
- A → B：A 依赖 B 的接口
- 区分**服务依赖**（运行时依赖对方服务） vs **代码依赖**（import/复用组件，不要求对方运行）
- INDEX.md 依赖表增加「依赖类型」列
- 识别循环依赖（需合并或重新切分）
- 标注无依赖的域（可优先开发）

## 4. Sub PRD 模板

每个功能域输出一篇标准 Sub PRD：

```markdown
# Sub PRD: [领域名称]

## 功能边界（黑盒）
- **负责**：本模块负责什么
- **不负责**：明确不属于本模块的职责（划清边界）

## 对外接口契约
> 本模块向外部暴露的所有接口

### 接口列表
| 接口名 | 方向 | 入参 | 出参 | 错误码 |
|--------|------|------|------|--------|
| `createXxx` | inbound | ... | ... | ... |

### 事件 / 消息（如有）
| 事件名 | 发布方 | 订阅方 | 载荷 |
|--------|--------|--------|------|

## 非功能契约
> 基于 Oracle Service Contract by Characteristic 规范

| 属性 | 约束值 | 优先级 | 来源（主 PRD 章节） |
|------|--------|--------|-------------------|
| 最大响应时间 | < 200ms (P95) | P0 | §非功能需求 |
| 可用性 | 99.9% | P0 | §非功能需求 |
| 最大并发 | 1000 req/s | P1 | §非功能需求 |

## Mock 数据
> 可独立测试本模块所需的 Mock 数据定义

```json
{
  "mock_input": {},
  "mock_output": {}
}
```

## 数据实体归属
> 本域管理的数据实体，遵循 Oracle ITSO 数据需求分解原则

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| User | 拥有 (Own) | CRUD | 用户基础信息 |
| Order | 读取 (Read) | R | 仅查询订单状态 |

- **拥有 (Own)**：本域是数据主控方，负责完整生命周期
- **读取 (Read)**：仅读取，不负责写入
- **写入 (Write)**：写入但不负责完整生命周期

## 依赖关系
- **依赖**：依赖的 Sub PRD（接口级）
- **被依赖**：哪些 Sub PRD 依赖本模块

## 父需求追溯
> 映射回主 PRD 的具体章节（IEEE 830 / Set-Based Design 可追溯性）

| 主 PRD 章节 | 覆盖的 Sub PRD 内容 |
|-------------|-------------------|
| §2.1 用户系统 | 全部 |
| §2.2 商品系统 | 仅「地址簿」部分 |

## 验收条件
- [ ] AC-1: ...
- [ ] AC-2: ...

## 技术约束
- 语言 / 框架 / 性能指标
```

## 5. 输出目录结构

```
{output_dir}/
  INDEX.md                ← 层级关系树 + 依赖图 + 开发顺序建议
  domain-{name1}.md       ← 第一个功能域
  domain-{name2}.md       ← 第二个功能域
  ...
```

### INDEX.md 格式样例

```markdown
# PRD 拆解索引

> 主 PRD：{来源路径}
> 拆解日期：{当前日期}

## 层级关系图

```
                    ┌──────────────┐
                    │  主 PRD       │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   domain-auth.md    domain-order.md   domain-payment.md
```

## 依赖关系

| 域 | 依赖 | 被依赖 | 建议开发顺序 |
|----|------|--------|-------------|
| auth | 无 | order, payment | 1 |
| order | auth | payment | 2 |
| payment | auth, order | 无 | 3 |

## 各域文件清单
- [domain-auth.md](domain-auth.md) — 认证权限
- [domain-order.md](domain-order.md) — 订单管理
- ...
```

## 6. PRD 全生命周期管线

本 skill 是 PRD 全生命周期的起点。完成拆解后，下游管线如下：

```
初始化路径（一次性，新项目启动）:

  lx-oma-hier    →     lx-oma-split       →     lx-rpe
  (主PRD→SubPRD)     (SubPRD→RPE)        (特性开发)

  用法:
    1. /lx-oma-hier docs/master-prd.md      # 拆出 Sub PRD
    2. /lx-oma-split sub-prds/domain-xxx.md       # 拆出 feature RPE
    3. /lx-rpe <feature-name>               # 启动特性开发

治理路径（长期，主 PRD 变更时）:

  lx-oma-gov      →   lx-oma-split / lx-rpe
  (reconcile/       (变更后重新拆解或直接开发)
   propagate/
   audit)

  用法:
    1. /lx-oma-gov reconcile                # 检测变更 + 冲突裁决
    2. /lx-oma-gov propagate --dry-run      # 预览传播内容
    3. /lx-oma-gov propagate --execute      # 实际写入 prd/{sub_prd}/{feature}
    4. /lx-oma-gov audit                    # 漂移检测
    5. /lx-oma-gov status                   # 治理面板
```

### 联动 lx-oma-split（Level 2）

完成 Sub PRD 拆解后，向用户报告：

```
# 📋 分层拆解完成

共拆分为 N 个功能域，详见 {output_dir}/

## 下一步

每个 Sub PRD 可独立进入特性级拆解。
运行以下命令分别拆解：

/lx-oma-split {output_dir}/domain-xxx.md
/lx-oma-split {output_dir}/domain-yyy.md
...
```

如果调用者要求"继续拆"，则逐一调用 `lx-oma-split` skill 对每个 Sub PRD 进行特性级拆解，产出 `prd/{sub_prd}/feat-X/` 目录。

**注意**：
- 不修改 `lx-oma-split` 原有代码
- 两阶段可独立执行（先拆 Sub PRD → 确认 → 再拆特性）
- Sub PRD 目录和 `prd/` 目录可共存，不冲突
- 长期治理使用 `lx-oma-gov`，见 `.claude/skills/lx-oma-gov/SKILL.md`

### 交付后的方向指引

输出报告后（无论是否继续拆），必须追加方向指引：

```
─── 方向指引 ───
📍 分层拆解完成。你现在位于 PRD 全生命周期的起点。

建议下一步:
  1. /lx-oma-split sub-prds/domain-{name}.md
     → 对某个 Sub PRD 进行特性级拆解（推荐先拆核心域）
  2. /lx-orch status
     → 查看 PRD 全景管线状态
  3. 继续拆分其余 Sub PRD
     → 重复 /lx-oma-hier，直到所有域拆分完成
  4. 自定义操作
     → 输入你想要的命令
  ─── 或直接输入你想要的命令 ───

注意事项:
  · 依赖链上游的域建议优先拆解（如 auth→order→payment）
  · 无依赖的域可并行推进
```

## 7. 拆解质量的自我校验

全部输出写入后，执行以下校验：

1. **文件清单完整性**：INDEX.md 中提到的每个文件都存在
2. **模板字段完整性**：每个 Sub PRD 包含「边界、接口契约、非功能契约、Mock、数据实体、依赖、父需求追溯、AC」
3. **正交性抽查**：随机选 2 个域，对照 PRD 原文确认无职责重叠
4. **依赖闭合性**：依赖图中所有被依赖的域都已拆出
5. **数据实体唯一性**：同一数据实体不被多个域同时「拥有（Own）」
6. **非功能契约一致性**：各域非功能约束之和 ≤ 主 PRD 全局非功能约束
7. **父需求全覆盖**：所有 Sub PRD 的父需求追溯条目拼起来完整覆盖主 PRD 各章节

校验结果写入输出目录末尾，格式：
```markdown
## 拆解质量报告
- 文件完整性：✅
- 模板字段（8 项）：✅
- 正交性抽查：✅
- 依赖闭合性：✅
- 数据实体唯一性：✅
- 非功能契约一致性：✅
- 父需求全覆盖：✅
```

## 8. Pipeline 集成

本 skill 与 `state/pipeline.yaml` 状态机配合，支持 `/lx-oma-orch` 编排。

### 入口检查

当调用者传入 `--pipeline <sub_prd_id>` 参数时（编排模式）：
1. 读取 `state/pipeline.yaml`
2. 检查该 sub_prd 的 `status` 是否为 `hier_done` 或更早
3. 若不是 `hier` 级状态 → 跳过（可能已被 lx-oma-split 拆解过）
4. 读取 sub_prd 的 `path` 作为输入路径

若未传入 `--pipeline` 参数（手动模式），按原有交互模式执行（手动指定路径）：
- 跳过 pipeline.yaml 写入
- 在报告中注明当前执行模式

### 出口写入

编排模式下，拆解完成后更新 `state/pipeline.yaml`：
- 为每个 Sub PRD 写入 `sub_prds[].{id, path, status: hier_done, oracle: pending, features: []}`
- 设置 `stages.hier = completed`
- 新增 Oracle gate 条目：`{id: og-NNN, from_stage: hier_done, to_stage: oma_ready, status: pending}`

## 9. 可观测性契约

本 skill 遵循 OMA 系列统一可观测性规范，详见 `lx-oma-orch/SKILL.md` §可观测性契约。

### 环境前置检查

写入 telemetry 前检查环境：
- `.omc/state/` 目录存在？ → 正常写入
- 目录不存在？ → **静默跳过**，在报告末尾注明"§9 遥测跳过（.omc/state/ 不存在）"

### 本 skill 特定采集点

| 采集点 | 触发条件 | 记录字段 | 用途 |
|--------|---------|---------|------|
| hier_started | 拆解开始时 | `{input_path, sub_prd_count, expected_domains[]}` | 拆解规模评估 |
| hier_completed | 拆解完成时 | `{output_dir, sub_prd_count, quality_score}` | 拆解质量追踪 |
| hier_entity_found | 核心实体识别 | `{entity_name, domain_assignment}` | 实体分布统计 |
| hier_gate_passed | MECE 校验通过 | `{orthogonal_count, dependency_resolution}` | 校验质量 |

> 数据写入 `.omc/state/oma-telemetry.yaml`，格式与 lx-oma-orch 保持一致。

## 10. 错误码与超时规范

本 skill 遵循共享错误码体系 `.claude/schemas/atomic/error_codes.yaml`，前缀 `HIER`。

| 错误码 | 场景 | 处理 |
|--------|------|------|
| ERR-HIER-01 | 缺少路径参数 | 提示输入路径 |
| ERR-HIER-03 | 输入路径不存在 | 报错阻断 |
| ERR-HIER-10 | PRD 文件读取失败 | 尝试 latin-1 回退 |
| ERR-HIER-23 | MECE 校验失败 | 修复后重新拆解 |
| ERR-HIER-30 | 拆解超时（>5 分钟） | 建议缩小 PRD 范围后重试 |
| ERR-HIER-31 | 超过最大重试次数（3 次） | 报告已尝试方案 + 失败证据 |
| ERR-HIER-90 | lx-oma-split 不可用 | 降级提示手动拆解 |

**超时**: 单次拆解操作默认 5 分钟。
**重试**: 校验失败最多重试 3 次，每轮必须不同假设。

## 11. 人工审核门禁

hier → oma 阶段转换前，**必须**执行人工审核。每次执行完成后（无论是否编排模式），必须输出审核清单：

```
## §11 人工审核门禁

> 以下清单由人工逐项确认后，方可执行 `/lx-oma-split`

[ ] 1. Sub PRD 边界正交（无职责重叠）？
        → {引用 MECE 摘要结果}

[ ] 2. 每个 Sub PRD 的接口契约可落地？
        → {引用接口检查结果}

[ ] 3. 数据实体唯一性满足（无两个域同时 Own 同一实体）？
        → {引用实体 Own 表结果}

[ ] 4. 依赖图无循环依赖？
        → {引用依赖分析结果}

[ ] 5. INDEX.md 中所有文件存在且路径正确？
        → {引用文件清单结果}

[ ] 6. §3.2 摘要中所有 ⚠️/❌ 冲突项已完成裁决？
        → {逐项说明}
```

### 待裁决项

如有未裁决的冲突（Oracle 发现的 FAIL/WARNING），列出待裁决项：

| 编号 | 问题 | 影响域 | 本次裁决 |
|------|------|--------|---------|
| OQ-NNN | {问题描述} | {域} | {✅已裁决 / ⏳待定} |

所有待裁决项清零后，执行 `/lx-oma-orch gate og-NNN approve` 推进到 oma 阶段。

