---
name: lx-oma
description: OMA Pipeline — hierarchically decompose, split into features, govern, orchestrate
version: v2.0.0
harness_version: ">=6.3.0"
status: stable
argument-hint: >
  hier <path> [output_dir] | split <path> [--pipeline <id>] |
  gov init|reconcile|resolve|propagate|status|audit [path] |
  orch status|advance|gate|run|dev
when_to_use: PRD 全生命周期 — 拆解、拆分、治理、编排
triggers: ["/lx-oma", "oma", "pipeline", "/lx-oma-hier", "/lx-oma-split", "/lx-oma-gov", "/lx-oma-orch", "分层拆解", "prd 拆分", "拆解需求", "一人成军拆解", "oma治理", "reconcile", "propagate", "漂移检测", "管线状态", "orchestrate"]
role: "OMA — Pipeline lifecycle (hier → split → gov → rpe)"
execution_mode: stepwise
---

# lx-oma OMA Pipeline — Unified Skill

> 合并自 lx-oma-hier v1.3.2 · lx-oma-split v1.2.1 · lx-oma-gov v1.2.1 · lx-oma-orch v1.2.2
> 向后兼容：原 `/lx-oma-hier` `/lx-oma-split` `/lx-oma-gov` `/lx-oma-orch` 仍可触发

## Subcommand 分发

```
/lx-oma hier <path> [output_dir]           → L1 分层拆解（原 lx-oma-hier）
/lx-oma split <path> [--pipeline <id>]     → L2 特性拆解（原 lx-oma-split）
/lx-oma gov <subcommand> [args...]         → 治理操作（原 lx-oma-gov）
/lx-oma orch <subcommand> [args...]        → 管线编排（原 lx-oma-orch）
```

> **注意：** `execution_mode: stepwise` 为根级声明。split 子命令内部使用 `race` 模式 — AI 自主拆解 + 脚手架构建后交还人工审核门禁。

## 共享 OMA 基础设施

| 文件 | 路径 | 用途 |
|------|------|------|
| 降级升级策略 | `@../references/oma/degradation-escalation.md` | 降级路径 |
| 裁决链 | `@../references/oma/decision-chain.md` | 决策记录 |
| 执行工作流 | `@../references/oma/execution-workflow.md` | 通用执行规范 |
| 链式承接 | `@../references/oma/skill-chaining.md` | 技能间委托 |
| 可观测性 | `@../references/oma/observability.md` | 遥测规范 |
| Pipeline 契约 | `@../references/oma/pipeline-contract.md` | 集成契约 |
| 错误码体系 | `@../references/oma/error-codes.md` | 共享错误码 |
| 方向指南 | `@../references/oma/direction-guide.md` | 方向指导 |

### 原子化节点

| 节点 | 路径 | 用途 |
|------|------|------|
| explore | `../../nodes/explore.md` | 文件/目录读取 |
| verifier | `../../nodes/verifier.md` | 质量验证 |
| oracle | `../../nodes/oracle_terminal.md` | 阶段转移门禁裁决 |
| mode_selector | `../../nodes/mode_selector.md` | 执行模式路由 |

### Schema

| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |
| error_codes | `../../schemas/atomic/error_codes.yaml` | 错误码共享体系 |

---

## hier — L1 分层 PRD 拆解（原 lx-oma-hier）

### references/（按需加载）

| 文件 | 加载时机 |
|------|---------|
| `references/hier/sub-prd-template.md` | sub prd 模板 |
| `references/hier/verification-gate.md` | verification gate |

### 状态机

```
need_input → [reading → analyzing → generating → verifying] → done
```

### 任务目标

将超大型 PRD 按功能域 MECE 拆分为 N 个 Sub PRD，确保功能正交、黑盒边界、可独立闭环、可独立交付。
> Sub PRD 模板 → `@references/hier/sub-prd-template.md` · 全生命周期管线 → `@../references/oma/pipeline-contract.md`

### 参数处理

入参 `<path>` + 可选 `[output_dir]`。模式：`--pipeline` 编排模式 / 无参数 手动模式。
输出路径: kernel.md 约定 → 用户显式 → 默认 `sub-prds/`。
文件直接读、目录读所有 `.md`、图片描述结构。

### MECE 功能域拆解

1. **识别核心业务实体** → 实体归属表（实体名/候选域/归属理由/原文引用）
2. **按职责聚类** → 围绕实体聚合功能
3. **正交性校验** → 域对检查职责重叠+数据交叉
4. **边界确认** → 每个域"管什么/不管什么"

#### MECE 校验摘要
- 正交性矩阵: 域对×重叠点×裁决（引用原文）
- 实体唯一 Own、接口耦合度(>10 警告)、孤儿接口检查、NFR 来源校验(无来源标注 `[内部自检]`)

#### 依赖分析
域间依赖图（A→B），区分服务依赖 vs 代码依赖，识别循环依赖，标注优先开发域。

### 输出目录结构

```
{output_dir}/
  INDEX.md              ← 层级关系树 + 依赖图 + 开发顺序
  domain-{name}.md      ← Sub PRD
```

### 校验与门禁

```bash
python3 .claude/scripts/verify_oma_mece.py {output_dir}/  # exit 0 → ✅
```

质量报告: verify_oma_mece.py exit_code + 模板字段8项 + 非功能契约一致性 + 父需求全覆盖。
G1 Meta-Oracle: ≥2子系统+不可逆变更时触发 → `@references/hier/verification-gate.md#meta-oracle-g1`

### 降级策略

| 场景 | 降级路径 |
|------|---------|
| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |
| Sub PRD 输出失败 | 保留中间产物，标注缺失项 |
| MECE 校验 3 轮未通过 | 标记需人工介入 |

---

## split — L2 特性拆解（原 lx-oma-split）

### references/（按需加载）

| 文件 | 加载时机 |
|------|---------|
| `references/split/mece-checklist.md` | MECE 拆解 |
| `references/split/scaffolding-template.md` | 脚手架构建 |
| `references/split/interface-verification.md` | 接口归属校验 |
| `references/split/delivery-report.md` | 战报交付 |

### 状态机

```
need_input → [reading → analyzing → scaffolding → verifying] → done
```

### 执行流程

#### 1. 参数处理
读取 `<path>`（文件→读内容，目录→读所有 .md）。未提供→询问用户。
从路径提取 `sub_prd_name`（如 `sub-prds/domain-auth.md` → `auth`）。

#### 2. MECE 正交拆解 → `@references/split/mece-checklist.md`
3-6 个 Feature，相互独立、完全穷尽。执行自检清单（正交性/完整性/独立性）。

#### 3. 脚手架构建 → `@references/split/scaffolding-template.md`
每个 Feature 自动生成 `prd/{sub_prd_name}/feat-XXX/{state,contracts,mocks}/prd.md`。

#### 4. 接口归属校验（阻断门禁） → `@references/split/interface-verification.md`
`verify_oma_interface_coverage.py` — 未归属接口必须修复后才放行。

#### 5. 战报交付 → `@references/split/delivery-report.md`
输出 feature 清单 + 并发启动指令（`/lx-rpe prd/...`）。

### Pipeline 集成

入口 `--pipeline <id>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。
> 完整契约 → `@../references/oma/pipeline-contract.md`

### 人工审核门禁

```
[ ] feature prd.md 完整？  [ ] 接口归属 exit 0？
[ ] 无 phantom 接口？      [ ] MECE 正交？
[ ] 所有目录已创建？
确认: /lx-oma orch gate og-NNN approve
```

### 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| Sub PRD <200 字 | 按已有内容拆解 | 告知内容不足 |
| 校验脚本不存在 | 自动化校验 | 降级手动校验 |
| hier 不可用 | 委托调用 | 手动 `/lx-oma hier` |

---

## gov — PRD 治理（原 lx-oma-gov）

### 专属文件

| 文件 | 用途 |
|------|------|
| `gov/governance-spec.md` | 完整规范（对象 ID/状态机/漂移规则） |
| `gov/HUMAN-IN-THE-LOOP-GATE.md` | awaiting_human_decision 状态机 |
| `gov/state/sync-state.md` | 同步状态跟踪 |

### references/（按需加载）

| 文件 | 加载时机 |
|------|---------|
| `references/gov/directory-structure.md` | init |
| `references/gov/commands-reconcile.md` | reconcile/verifier/resolve/propagate |
| `references/gov/commands-audit.md` | audit |
| `references/gov/pipeline-integration.md` | pipeline |

### 状态机

```
need_input
  → [init] → initialized
  → [reconcile] → reconciling
      → [no changes] → done
      → [L3 conflict] → awaiting_human_decision → [resolve] → reconciling
      → [changes ready] → verifying → propagating_dry_run
          → [confirmed] → propagating → done
  → [status] → done
  → [audit] → done
  → [error] → [repair → undone | reset → initialized]
```

### 命令

#### init → `@references/gov/directory-structure.md`
`/lx-oma gov init [path]` — 创建 state/ + source-prds/ + snapshots/ + 日志

#### reconcile / verifier / resolve / propagate → `@references/gov/commands-reconcile.md`
变更检测（L1/L2/L3 分级）→ verifier 质量门禁 → resolve 人工裁决 → propagate 增量传播

#### status — 治理状态面板
#### audit → `@references/gov/commands-audit.md`
四类漂移检测（ID 孤儿/版本落后/冲突定义/孤立变更）

### Pipeline 集成 → `@references/gov/pipeline-integration.md`
只读 pipeline.yaml。命令执行后输出 governance-report.yaml 供 orch 消费。

### 治理质量自检

1. CHG-ID 完整性：格式 `CHG-YYYYMMDD-NNN`
2. CHG 分类正确性：L3 必须涉及 REQ-/DEC-/TERM- 修改
3. CONFLICT-ID 闭合性：已裁决标记 resolved
4. 幂等安全：重复 propagate 不产生重复内容
5. 引用一致性：propagate 后所有引用在 master 中存在
6. 同步状态：活跃 feature 同步时间 ≥ 最后 reconcile

### 降级策略

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 治理目录不存在 | 报错 | 先运行 init |
| reconcile 无变更 | 报告"无差异" | fast path done |
| L3 冲突无裁决 | 挂起 + 提示 | 继续 L1/L2 |
| propagate 目标缺失 | 跳过 | 列出缺失 feature |
| 锁超时 | 自动释放 | 记录清除日志 |

---

## orch — Pipeline 编排器（原 lx-oma-orch）

### 子 skill 路由

| 目标 | 路由 |
|------|------|
| Sub PRD | lx-oma hier (self) |
| Feature | lx-oma split (self) |
| 治理 | lx-oma gov (self) |
| RPE | lx-rpe |

### references/（按需加载）

| 文件 | 加载时机 |
|------|---------|
| `references/orch/status-panel.md` | status |
| `references/orch/advance-flow.md` | advance |
| `references/orch/oracle-gate.md` | gate |
| `references/orch/dev-management.md` | dev |
| `references/orch/interface-contract.md` | 接口契约 |
| `references/orch/manual-review.md` | 人工审核 |

### 状态机

```
idle → [status] → done
     → [advance] → checking_oracle_gate
         → [blocked] → awaiting_decision → [approve/reject] → advance/abort
         → [passed] → calling_skill → update_pipeline → done
     → [gate <id> approve|reject] → update_pipeline → done
     → [run <target>] → route_to_skill → done
     → [dev list|mark] → done
```

### 命令

#### status — 管线全景 → `@references/orch/status-panel.md`
#### advance — 推进阶段 → `@references/orch/advance-flow.md`
检查→路由→执行→更新→人工确认。

#### gate — Oracle 门禁 → `@references/orch/oracle-gate.md`
`/lx-oma orch gate <og-id> approve|reject [--reason "..."]`

#### run — 直接路由（绕过阶段检查）
| 目标 | 路由 |
|------|------|
| Sub PRD | lx-oma hier |
| Feature | lx-oma split |
| 治理 | lx-oma gov |
| RPE | lx-rpe |

#### dev — 并行开发 → `@references/orch/dev-management.md`

### Pipeline 更新 → `@../references/oma/pipeline-contract.md`
原子写入（tmp→rename）+ 更新规则 + Oracle gate 创建。

### 降级策略

| 场景 | 降级路径 |
|------|---------|
| advance 失败 | 检查管线状态，手动修复 |
| gate 不可用 | 跳过 Oracle 门禁，标注 [无Oracle审核] |
| Pipeline 写入失败 | 降级为手动状态跟踪 |
