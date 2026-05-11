---
name: lx-oma-split

description: 一人成军司令部 (One-Man Army) - 将需求拆解为正交的多个功能分支 (prd/{sub_prd}/{feature})，支持目录和单文件作为输入。

version: v1.2.0
harness_version: "6.1.9"
model: sonnet
argument-hint: "<path> [--pipeline <sub_prd_id>]"
when_to_use: |
  当 Sub PRD 已完成 hier 拆解，需要进一步拆解为可独立开发的 feature 级 RPE 时；
  当需要确保 feature 间 MECE 正交、接口完整归属时

triggers:
  - "/lx-oma-split"
  - "拆解需求"
  - "一人成军拆解"
role: "OMA commander — Sub PRD to feature decomposition (Level 2)"
execution_mode: race
---

# lx-oma-split 一人成军拆解大脑

**触发语**: `/lx-oma-split`, `拆解需求`, `一人成军拆解`

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| — | — | 本 skill 无外部节点依赖，拆解逻辑由 AI 自主执行 |

### 引用的通用 Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |

### 状态机

```
need_input → [reading → analyzing → scaffolding → verifying] → done
```

### 降级策略

| 场景 | 主路径 | 降级路径 |
|------|--------|---------|
| 输入路径不存在 | 报错 | 提示用户补充路径 |
| 输入为空文件 | 报错 | 输出"Sub PRD 内容为空，无法拆解" |
| 读取的 Sub PRD 内容过少（<200 字） | 按已有内容拆解 | 告知用户内容不足，建议补充后重新执行 |
| 输出目录已存在 | 覆盖写入 | 询问用户是否覆盖或指定新目录 |
| 接口校验脚本不存在 | 自动化校验 | 降级手动校验 |
| lx-oma-hier 不可用 | 委托调用 | 告知用户手动执行 `/lx-oma-hier` 拆解 |

## 1. 任务背景 (Context)你是”一人成军 (One-Man Army, OMA)”的战区总司令。开发者要求你读取一份需求文档（或一个目录下所有的文档），并将其拆解为多个**功能上绝对正交（MECE）**的子模块。后续，开发者会通过开启多个终端，分别为每个子模块运行独立的 `/lx-rpe prd/{sub_prd}/{feature}`，实现真正的并发协同开发。

输出遵循 OMA 文档体系：`prd/{sub_prd}/{feature}/{{prd.md, research.md, plan.md, ...}}`

## 2. 参数处理 (Input)你的入参是一条路径（\<path>），由开发者附在触发语后（如 `/lx-oma-split docs/` 或 `/lx-oma-split prd.md`）。
1. 使用 Bash 或 Read/Glob 工具检查该路径。
2. 如果是文件，直接读取内容。
3. 如果是目录，读取该目录下所有 .md 文件内容作为上下文。
4. 如果未提供路径，向用户询问目标。

## 3. 正交拆解原则 (MECE Analysis)请运用顶级架构师的思维，将需求拆解为 \$N\$ 个 Feature (通常 3-6 个)：

- **相互独立**：Feature 之间的职责必须清晰分离（例如：feat-db, feat-api, feat-ui），减少不同终端同时修改同一个核心文件的概率。
- **完全穷尽**：所有拆解后的 Feature 拼在一起，必须能完整实现原始 PRD。

**Feature 级 MECE 自检清单（每次拆解后执行）：**
```
正交性:
[ ] 每个 feature 的"负责"条目不与其他 feature 重叠
[ ] 没有两个 feature 同时 Own 同一实体
[ ] 接口在 feature 间无重复定义

完整性:
[ ] 所有 Sub PRD 接口已分配到某个 feature
[ ] 所有 Sub PRD 实体已分配到某个 feature
[ ] Sub PRD 中描述的每个功能场景至少被一个 feature 覆盖

独立性:
[ ] 每个 feature 可独立绑定 Mock 数据验证
[ ] feature 间依赖关系是 DAG（无循环依赖）
[ ] 依赖图中"被依赖"最多的 feature ≤3 个下游
```

## 4. 子 PRD 名称提取

从输入路径提取子 PRD 名称（sub_prd_name）：
- 若输入为 `sub-prds/domain-auth.md` → sub_prd_name = `auth`（取文件名 `domain-auth` 去掉 `domain-` 前缀的部分）
- 若输入为 `prd/auth/master.md` → sub_prd_name = `auth`（取路径倒数第二段）
- 若输入为 `docs/payment-v2.md` → sub_prd_name = `payment-v2`（取文件名去扩展名）
- 可直接指定：`/lx-oma-split prd/auth` → sub_prd_name = `auth`

## 5. 自动脚手架构建 (Scaffolding)

拆解完成后，**你必须使用 Bash 工具** 在 `prd/{sub_prd_name}/` 下自动生成目录体系。对于每个拆解出来的 Feature (例如 `feat-user`, `feat-pay`)，执行：

```bash
mkdir -p prd/{sub_prd_name}/feat-XXX/{state,contracts,mocks}
cat > prd/{sub_prd_name}/feat-XXX/prd.md << 'EOF'
# Feature: {Feature 名称}

> 所属 Sub PRD：{Sub PRD 名称}
> 职责：{一句话描述}

## 功能边界（从 Sub PRD §功能边界 提炼）

- **负责**：
  - {从 Sub PRD 职责中提取属于本 Feature 的部分}
  - {逐条列出}

- **不负责**：
  - {明确不属于本 Feature 的职责（从 Sub PRD 不负责 + 其他 feature 的负责中提炼）}

## 对外接口（从 Sub PRD §对外接口契约 提炼）

| 接口 | 方向 | 入参 | 出参 |
|------|------|------|------|
| {接口名} | {inbound/outbound} | {入参} | {出参} |

### 事件（如适用）

| 事件名 | 方向 | 说明 | 载荷 |
|--------|------|------|------|
| {事件名} | {inbound/outbound} | {触发条件} | {载荷} |

## 非功能要求（从 Sub PRD §非功能契约 继承与本 Feature 相关的条目）

| 属性 | 约束值 | 优先级 |
|------|--------|--------|
| {指标} | {约束} | {P0/P1/P2} |

## 数据实体归属（从 Sub PRD §数据实体归属 切分）

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| {实体} | Own/Read/Write | {CRUD} | {说明} |

## 依赖关系（从 Sub PRD §依赖关系 继承）

- **依赖**：{本 Feature 依赖的其他模块/Feature}
- **被依赖**：{哪些模块/Feature 依赖本 Feature}

## Mock 数据（从 Sub PRD §Mock 数据 提炼本 Feature 相关的 mock）

```json
{
  "{场景名}": {
    "input": {},
    "output": {}
  }
}
```

## 验收条件（从 Sub PRD §验收条件 拆解出本 Feature 负责的 AC）

- [ ] AC-1: {描述}
- [ ] AC-2: {描述}

## 技术约束（从 Sub PRD §技术约束 继承与本 Feature 相关的约束）

- {约束 1}
- {约束 2}
EOF
```

## 5.5 接口归属完整性校验（通用型能力 — 阻断门禁）

拆解完成后、战报输出前，**必须**自动化执行以下校验。校验失败阻断拆解流程。

### 触发条件
无论编排模式还是手动模式，每次拆解后自动执行。

### 执行序列

```
1. 调用自动化校验脚本：
   python3 .claude/scripts/verify_oma_interface_coverage.py \
     sub-prds/domain-{sub_prd_name}.md

2. 解读脚本 exit code：
   ├─ exit 0 → ✅ 全部接口/事件有归属 → 继续战报输出
   └─ exit 1 → ❌ 存在未归属缺口 → 阻断，执行修复

3. 修复未归属接口（exit 1 时）：
   a. 分析该接口的数据流向和职责，确定归属 feature
   b. 追加到对应 feature 的 prd.md 接口表/事件表
   c. 重新执行校验脚本 → 确认 exit 0
   d. 不修复不得跳过
```

### 校验规则

| 检查项 | 通过标准 | 阻断条件 |
|--------|---------|---------|
| 所有接口有归属 | 命中率 100% | exit 1 — 阻断，必须修复 |
| 命名严格一致 | Sub PRD 名称 == feature 名称（大小写敏感） | exit 1 — 阻断，必须对齐 |
| 无 phantom 接口 | feature 不声明 Sub PRD 未定义的接口 | ⚠️ 警告不阻断（扩展接口需注明） |

### 完成标准
- ✅ 校验脚本 exit 0
- ✅ 所有未归属接口已分配到对应 feature
- ✅ 命名与 Sub PRD 完全对齐（大小写一致）

## 6. 战前动员 (Delivery)全部构建完毕后，输出一份战报给开发者：

```markdown
# ⚔️ 一人成军拆解完成

共拆分出 N 个正交功能分支：
1. **feat-xxx**：负责...
2. **feat-yyy**：负责...

## 🚀 并发开发

共拆分出 N 个正交功能分支，可独立进入开发。

每个 feature 目录在 `prd/{sub_prd_name}/feat-xxx/` 下，包含：
- `prd.md` — 该 feature 的需求子集
- `contracts/` — 接口契约定义
- `mocks/` — Mock 数据

直接进入对应目录开始开发即可。

底层的 OMA 文件锁 (Micro-OS Mutex) 已就绪，冲突将自动挂起排队，尽情享受最高密度的并发生产力！

```

### 交付后的方向指引

输出战报后，必须追加方向指引：

```
─── 方向指引 ───
📍 拆解完成，{N} 个 feature 已就绪。

建议下一步:
  1. /lx-rpe prd/{sub_prd_name}/feat-{name}
     → 启动核心 feature 的 RPE 开发（建议先做依赖链上游的）
  2. 并行启动多个 /lx-rpe
     → 无依赖的 feature 可同时开始开发
  3. /lx-orch status
     → 查看管线全景，了解整体进度
  4. 自定义操作
     → 输入你想要的命令
  ─── 或直接输入你想要的命令 ───

推荐顺序:
  · 有依赖项的 feature → 优先启动（处于依赖链上游的）
  · 无依赖的 feature   → 可并行启动
  · 建议一次启动不超过 3 个 RPE 实例，避免上下文混
```

## 7. Pipeline 集成

本 skill 与 `state/pipeline.yaml` 状态机配合，支持 `/lx-oma-orch` 编排。

### 入口检查（编排模式）

当调用者传入 `--pipeline <sub_prd_id>` 参数时：
1. 读取 `state/pipeline.yaml`
2. 从 `sub_prds[]` 中按 `id` 匹配目标 sub_prd
3. 检查其 `status` 是否为 `hier_done`（只能对 hier 完成的 sub_prd 做 oma 拆解）
4. 使用 `path` 字段作为输入路径（如 `sub-prds/domain-alert-engine.md`）

若未传入 `--pipeline` 参数，按原有交互模式执行。

### 出口写入（编排/手动模式均执行）

拆解完成后，更新 `state/pipeline.yaml`：
- 为每个 feature 写入 `features[].{id, path, stage: oma_created, oracle: pending}`
- 设置 sub_prd 的 `status = oma_done`
- 设置 `stages.oma = completed`
- 若 pipeline 中已有 Oracle gate，将其 status 更新为 `approved`
- 生成新的 Oracle gate：`{id: og-NNN, from_stage: oma_done, to_stage: gov_initialized, status: pending}`

### 路径复用

`sub_prd_name` 提取规则（§4）保持不变。编排模式下，`sub_prd_name` 直接从 pipeline.yaml 的 sub_prd `id` 字段获取，无需从文件名推断。

## 8. 可观测性契约

本 skill 遵循 OMA 系列统一可观测性规范，详见 `lx-oma-orch/SKILL.md` §可观测性契约。

### 本 skill 特定采集点

| 采集点 | 触发条件 | 记录字段 | 用途 |
|--------|---------|---------|------|
| split_started | 拆解开始时 | `{input_path, sub_prd_id, feature_count}` | 拆解规模评估 |
| split_completed | 拆解完成时 | `{feature_count, scaffolding_files, coverage_pct}` | 拆解质量追踪 |
| split_interface_verified | 接口归属校验 | `{total_interfaces, assigned, unassigned, phantom}` | 接口覆盖率 |
| split_scaffolding_done | 脚手架生成完成 | `{directories_created, files_created}` | 产出度量 |

> 数据写入 `.omc/state/oma-telemetry.yaml`，格式与 lx-oma-orch 保持一致。

## 9. 错误码与超时规范

本 skill 遵循共享错误码体系 `.claude/schemas/atomic/error_codes.yaml`，前缀 `SPLIT`。

| 错误码 | 场景 | 处理 |
|--------|------|------|
| ERR-SPLIT-01 | 缺少路径参数 | 提示输入路径 |
| ERR-SPLIT-03 | 输入路径不存在 | 报错阻断 |
| ERR-SPLIT-10 | feature PRD 写入失败 | 检查权限后重试 |
| ERR-SPLIT-23 | 接口归属校验脚本 exit 1 | 修复未归属接口后重新校验 |
| ERR-SPLIT-30 | 拆解超时（>3 分钟） | 检查 Sub PRD 大小后重试 |
| ERR-SPLIT-31 | 超过最大重试次数（3 次） | 报告已尝试方案 + 失败证据 |
| ERR-SPLIT-90 | verify_oma_interface_coverage.py 不存在 | 降级手动校验 |

**超时**: 单次拆解默认 3 分钟（含脚手架生成）。校验脚本执行超时 30 秒。
**重试**: 校验失败最多重试 3 次，每轮必须不同接口归属假设。

## 10. 人工审核门禁

oma → gov 阶段转换前，**必须**执行人工审核：

```
审核清单：
[ ] 所有 feature 的 prd.md 是否完整（边界/接口/非功能/实体/AC）？
[ ] 接口归属校验脚本 exit 0？
[ ] 无 phantom 接口（扩展接口已注明）？
[ ] Feature 间职责正交（MECE）？
[ ] 所有 feature 目录已创建（prd/{sub_prd}/feat-*/）？
```

人工确认后，运行 `/lx-oma-orch gate og-NNN approve` 推进。

