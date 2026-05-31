# lx-oma-split 一人成军拆解大脑

## 原子化声明

| Schema | 路径 | 用途 |
|--------|------|------|
| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |

> 本 skill 无外部节点依赖，拆解逻辑由 AI 自主执行。

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/mece-checklist.md` | MECE 拆解 |
| `references/scaffolding-template.md` | 脚手架构建 |
| `references/interface-verification.md` | 接口归属校验 |
| `references/delivery-report.md` | 战报交付 |

> 共享 OMA 能力 `@../references/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining · pipeline-contract · observability

## 状态机

```
need_input → [reading → analyzing → scaffolding → verifying] → done
```

## 执行流程

### 1. 参数处理
读取 `<path>`（文件→读内容，目录→读所有 .md）。未提供→询问用户。
从路径提取 `sub_prd_name`（如 `sub-prds/domain-auth.md` → `auth`）。

### 2. MECE 正交拆解 → `@references/mece-checklist.md`
3-6 个 Feature，相互独立、完全穷尽。执行自检清单（正交性/完整性/独立性）。

### 3. 脚手架构建 → `@references/scaffolding-template.md`
每个 Feature 自动生成 `prd/{sub_prd_name}/feat-XXX/{state,contracts,mocks}/prd.md`。

### 4. 接口归属校验（阻断门禁） → `@references/interface-verification.md`
`verify_oma_interface_coverage.py` — 未归属接口必须修复后才放行。

### 5. 战报交付 → `@references/delivery-report.md`
输出 feature 清单 + 并发启动指令（`/lx-rpe prd/...`）。

## Pipeline 集成

入口 `--pipeline <id>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。
> 完整契约 → `@../references/oma/pipeline-contract.md`

## 人工审核门禁
```
[ ] feature prd.md 完整？  [ ] 接口归属 exit 0？
[ ] 无 phantom 接口？      [ ] MECE 正交？
[ ] 所有目录已创建？
确认: /lx-oma-orch gate og-NNN approve
```

## 降级策略
| 场景 | 主路径 | 降级 |
|------|--------|------|
| Sub PRD <200 字 | 按已有内容拆解 | 告知内容不足 |
| 校验脚本不存在 | 自动化校验 | 降级手动校验 |
| hier 不可用 | 委托调用 | 手动 `/lx-oma-hier` |
