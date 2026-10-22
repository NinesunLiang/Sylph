# 0020. 哲学单一真相源迁移：裁决链归 AGENTS.md + 审计还债批次

**日期**: 2026-10-23
**来源**: 用户指令「过一遍全文（主要是 .claude/ 下）看是否存在与哲学体系不符合的地方」+ 人类裁决（agentic-ui 选项交互两次）

## 上下文

按核心哲学优先级链 `少即是多 > 验证 > 零信任 > 守护 > 文档 > 人本 > 增益`（冲突时机械裁决）对 `.claude/` 全文审计，发现 12 处文档与哲学体系漂移，其中 1 处是架构级张力：

- **裁决链原文存在 3 处**：`philosophy.md`（自称唯一真相源，7 条）+ `AGENTS.md §灵魂`（7 条，每次会话自动加载）+ `adr/0006`（1 行链式表述）。`philosophy.md` 自称唯一真相源，但 `AGENTS.md` 实际持有同等 7 条——违反「同一份原文只在一处」的单链原则。
- 其余 11 处为计数/幽灵引用/时点快照漂移（门数、节点数、ADR 数、已删文件墓碑等）。

## 决策

**人类裁决（2026-10-23，agentic-ui 选项交互）**：

1. **裁决链（7 条灵魂）唯一真相源 = `AGENTS.md §灵魂`**。`philosophy.md` 降为「裁决链指针 + 落地实体映射 + 禁止事项」，不再复述 7 条原文。
   - 权衡：`AGENTS.md` 每次会话自动加载，操作定义留此处 = 零额外读文件（少即是多）；`philosophy.md` 保留落地实体映射（可 grep 校验）+ 4 条禁止事项，职责单一。
   - 同步：`references/index.md`、`ai_self_decision.md`、`adr/0006` 三处对 philosophy.md 的「唯一真相源」引用改为指向 AGENTS.md。
2. **冻结文件 diff 全部批准**：`AGENTS.md`（8 行命名收敛）+ `.claude/index.md`（7 行计数/幽灵引用修数）。`kernel.md` 审计无漂移未动。

## 改动清单（14 改 + 2 新归档，净删 156 行）

| 文件 | 改动 |
|------|------|
| `philosophy.md` | 33→27 行：7 条原文删除降为指针；落地实体映射改表格（修 2 处不存在 ref）；禁止事项保留 |
| `AGENTS.md` | 灵魂 7 条命名对齐正式命名；标题声明「裁决链唯一真相源」 |
| `.claude/index.md` | nodes 13/rules 3/tokens 不写死；删 7 幽灵 `.omc/*/index.md`；删 2 墓碑；ADR 14 |
| `invariants.md` | 标题 12→16；INV-14 标 2026-10-16 收敛 L1=L2=14 道 |
| `hooks/index.md` | 删 2 幽灵 hook 行；对齐 settings.json 实际 12 注册 |
| `pretool-gate.py` | docstring 7 门枚举→指针 `_GATE_CORE` |
| `harness.yaml` | 删 44 行死配置注释块→2 行 provenance 注 |
| `references/index.md` | 文档表补 4 行；ADR 表→指向 INDEX.md；philosophy 行改指向 |
| `ai_self_decision.md` | 重写：修断句；决策链指向 AGENTS.md |
| `governance-philosophy.md` | 22 门表标「2026-08-30 时点快照」 |
| `feature-registry.yaml` | 头部幽灵 hook/门数→指向 settings.json + `_GATE_CORE` |
| `nodes/README.md` | 重写：表头修复；10 通用 + a/b/orchestrator；删 generator 节 |
| `jev_rules.yaml` | 5 条规则原文与 AGENTS 新命名逐字对齐 |
| `adr/0006` | 链式表述加「原文唯一真相源 = AGENTS.md」标注 |
| 新 `archived/hooks-retired-20261023.md` | 墓碑迁出（5 删除 + 2 退休 + 2 幽灵） |
| 新 `archived/nodes-retired-20261023.md` | 墓碑迁出（8 删除 + generator 物理删除记录） |

## 回归证据

- `.claude/scripts/` + `.claude/hooks/` + `pretool_gates/` 全套：**901 passed**
- `omc_lint.py`：0 errors / 5 warnings（既有，与本批无关）
- 自定义审计脚本 `philosophy_audit_verify.py`：ALL CHECKS PASSED（~40 项）

## 后果

- **正面**：裁决链单链原则成立；改链只改一处（AGENTS.md），改落地实体只改一处（philosophy.md），职责不交叉。
- **风险**：`AGENTS.md` 为冻结文件，未来改裁决链须人类裁决（禁止事项①已写入 philosophy.md）。
- **回滚**：全部改动在 git 工作区，`git checkout -- <files>` 可整体回滚；无不可逆操作。

## 遗留（记录不修）

- 7+ skill 文件引用已删 `nodes/generator.md`（历史链接，待各 skill 维护者清理，不属本批范围）。
- `UI_README.md:491` 仍引用已删 `oracle_terminal.md`；`schemas/registry.yaml` 有 8 节点墓碑注释——低优先级，候选后续批次。
