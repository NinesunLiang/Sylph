# design-docs — 系统设计导航

> 活文档路由表。本目录不存放内容副本——所有设计规格指向已有单一真相源。
> 历史存档: `1.md`~`11.md`（第三轮迭代设计，2026-07-12 冻结，保留但不反映当前状态）

---

## 设计决策

| ADR | 决策 | 文件 |
|-----|------|------|
| 0001 | `.omc/` 作为 AI 唯一写入域 | `adr/0001-omc-ai-write-domain.md` |
| 0002 | Token + Lock 双层任务生命周期 | `adr/0002-token-lock-task-lifecycle.md` |
| 0003 | VerifyGate 证据等级 E3>E2>E1>E0 | `adr/0003-verifygate-evidence-hierarchy.md` |
| 0004 | Oracle 双模型对抗审核 | `adr/0004-oracle-dual-model-adversarial-review.md` |
| 0005 | Goal 模式自主执行 + skip-risk 安全阀 | `adr/0005-goal-mode-autonomous-execution.md` |
| 0012 | REDIRECT oracle 判决级别 + 反模式注入 | `adr/0012-redirect-verdict-level.md` |
| 0013 | Scorecard 自评审计门禁 | `adr/0013-scorecard-self-rating-audit-gate.md` |

> 自 2026-07-25 起，架构决策不再仅靠"不可撤销 + 非直觉 + 真权衡"。门禁、反模式等高频更迭项通过 `anti-patterns.md`（K 区）和 `redirect-mechanism.md` 记录演化，无 ADR 的决策视为"设计内调整"。

---

## 门禁体系

| 规格 | 描述 | 实现 |
|------|------|------|
| `redirect-mechanism.md` | REDIRECT 软打断：Gate 9 数值断言溯源 + Gate 10 引用溯源 + 三次上限升级 | `pretool-gate.py` |
| `ai_self_decision.md` | AI 自决边界：BLOCK/REDIRECT/WARN 三门决策说明 | `pretool-gate.py` |
| `gate-rules.yaml` | Gate 规则汇总 | `harness.yaml` (注册) |
| `oracle-spec.md` | Oracle 三层对抗审核 | `pretool-gate.py _check_oracle_gate()` |
| `design-docs/13-headless-lightweight-actions.md` | Headless 治理轻量化（安全的轻量化行动）：联合审判否决 headless 降级，改同构提速三件套（REVISED 待授权） | `hook-launcher.py`（runpy 同进程） |

**关键演进**: 2026-07-27 数值断言从 `WARN` 升级为 `REDIRECT`，新增文件引用溯源 Gate 10。三次同一违规自动升级为 `BLOCK`。（详见 `redirect-mechanism.md`）

---

## 评测框架

| 规格 | 描述 |
|------|------|
| `evaluation-framework.md` | 四层架构：Regression → Longitude → Latitude → Adversarial |
| `scorecard.md`（improve_plan/） | 纵向提分账本，R0-R6 完整轮次 + 三模型终审记录 |
| `improve_plan/CarrorOS_second_time/round7/` | 三模型(Opus/GPT/Grok)独立方案 |

**顶层设计**: `evaluation-framework.md` — C1-C9 能力激发、E1-E8 错误防护、长期治理 7 维、UX 7 维、合计 31 维度评分体系。总分 = 纵向追踪 ×0.6 + 独立审计 ×0.4。

---

## 反模式体系

| 规格 | 描述 |
|------|------|
| `anti-patterns.md` | 经验沉淀：E 区(闭环失败) / F 区(工具误用) / G 区(继承失效) / H 区(安全忽视) / I 区(运行稳定性) / J 区(分类缺失) / K 区(虚假数值断言) |
| `error-dna.jsonl`（.omc/） | 运行时错误追踪数据 |
| `edit-churn-log.jsonl`（.omc/） | 编辑抖动日志（供 E6 自洽检查） |

**K 区三模式（2026-07-27 新增）**:
- K1: G1_PSEUDO_INTEGRITY — 数值断言无来源
- K2: E6_EDIT_REPEAT — 同一文件连续高频编辑
- K3: E6_CONTENT_FLIP — 编辑方向前后摇摆

---

## 执行模式

| 模式 | 规格 | 触发 |
|------|------|------|
| Goal 模式 | `lx-goal/SKILL.md` + `autonomous-execution.md` | 用户说"自动驾驶" |
| L1 快速流程 | `AGENTS.md` L1 工作流 | 日常开发/单文件修复 |
| L2 完整流程 | L1 + 条件 Oracle 激活 | 跨模块/不可逆操作/安全权限 |

---

## 文件索引

```
.claude/
├── hooks/
│   └── pretool-gate.py           # 统一门禁（Gate 1-10，含 REDIRECT/trust_breach）
├── references/
│   ├── design-docs/INDEX.md      # ★ 本文件——设计导航
│   ├── adr/0001-0013/             # 架构决策记录
│   ├── redirect-mechanism.md      # REDIRECT 软打断规格（2026-07-27）
│   ├── evaluation-framework.md    # 评测框架（四层架构）
│   ├── anti-patterns.md           # 反模式库
│   ├── oracle-spec.md             # Oracle 规格
│   ├── ai_self_decision.md        # AI 自决边界
│   └── gate-rules.yaml            # Gate 规则汇总
├── skills/
│   └── lx-goal/                  # Goal 模式
└── scripts/
    └── carros_base.py             # 主入口
improve_plan/
├── CarrorOS_second_time/
│   ├── scorecard.md              # 纵向提分账本
│   └── round7/                   # 三模型终审方案
scripts/
├── run-regression.sh             # 回归地基
├── verify_contract.py            # 验证判决契约
tests/                              # 44 测试文件 + REDIRECT 测试套件
