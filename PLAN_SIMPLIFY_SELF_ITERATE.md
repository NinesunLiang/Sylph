# CarrorOS 简化 + 自迭代 总设计（草案 v0.1，待人类评审）

> 配套审计：MODERNIZATION_AUDIT.md（2026-09-08，全部证据在案）
> 性质：**设计文档，不是执行令**。本文档评审通过后，才按 D 章阶段逐项执行（每项有独立验收与回滚）。
> 目标读者：人类 owner（拍板）+ 后续执行 AI（照章办事）。
> 一句话：**把 11 万行治理减到必要的量，然后装上"用一次进化一次"的飞轮，并用"每轮必须删 ≥1 个僵尸"的规则防止它再胖回去。**

---

## A. 双目标与反目标

**目标 1 — 大量简化，保留必要**
把"治理体量"降到可维护的 1/4~1/5，同时不丢失任何一条安全底线与证据链。

**目标 2 — 真正的自我迭代（越用越好用）**
每次真实使用（任务归档）都是系统的进化样本：错误 → 聚类 → 提案 → 人类采纳 → 测试锁死 → 下一轮验证变好。进化必须**可度量、可回滚、有人类裁决点**。

**反目标（防止过度设计的红线）**
- 不为"简化"推倒重写一切——现有 80+ 回归测试是重构安全网，**测试资产不减反增**
- 不引入新语言/新框架/数据库（JSONL + Python 够用）
- 不做自研 Web 控制台（CLI + Markdown 提案流先跑通）
- 不把"自动进化"做成无人类监督的自我修改（裁决权永远在人）
- 不做"每年一次大重构"——用 C4 防膨胀规则把简化变成日常

---

## B. 简化设计

### B0. 量化目标（现状 → 目标）

| 指标 | 现状（实测） | 目标 | 依据 |
|---|---|---|---|
| Python 治理代码 | ~55k 行 | **≤15k 行** | MODERNIZATION_AUDIT §0 |
| Markdown（活跃） | ~54k 行 / 395 份 | **≤10k 行活跃**（证据/ADR 转归档不计） | 同上 |
| carros_base.py | 3,981 行 / ~40 动词 | **≤1,200 行 / ≤15 动词** | B2 |
| 门禁数 | 22 道 | **10 道**（6 硬 + 3 契约 + 1 L2 专用） | B1 |
| Hook 注册脚本 | 12 | **≤8** | B1/B2 |
| scripts 目录 | 108 文件 | **≤50**（含测试） | B2/B4 |
| 每次任务文档仪式 | 六件套 | **三件套**（token/plan/executor） | B2 |
| settings 配置 | 5+ 份 + .bak×3 | **1 真相 + N env 差量** | B3 |

### B1. 门禁三级分类（22 → 10）

**G1 安全硬门（保留并集中，6 道，任何模型时代都不可省）**
| 现门禁 | 去向 | 理由 |
|---|---|---|
| sensitive_edit / sensitive_read | **合并 1 道** | 敏感路径读写，机械硬拦 |
| secret_scan | 保留 | 泄密防线 |
| governance_delete_protection（含 doc_reference_before_delete） | **合并 1 道** | 治理资产/被引用文件删除保护 |
| injection | 保留 + 扩展 | 边界从文本扩展至 MCP/web/多模态返回 |
| omc_skeleton_readonly / governance_bypass | 保留 | 状态机骨架保护 + 绕过检测 |

**G2 行为契约门（改造：事前拦 → 契约 + 事后审计，3 道）**
| 现门禁 | 去向 | 理由 |
|---|---|---|
| verify_gate / numeric_claim / commit_soft_completion | **合并 1 道 completion-integrity** | 同一目标（防虚假完成），一次判定 |
| action_loop / stall | **合并 1 道 progress-monitor** | 防死循环/卡死，统一为轮次/时间预算 |
| test_verification | 保留 | "跑测试才放行"价值已被 index40 实证 |

**G3 阅读习惯微管理（删除，5 道）**
g2_large_file / g5_wide_glob / g6_budget / document_quality / g3_reviews
→ 2026 模型自带取舍能力；删除后省下的延迟留给 G1。若担心，先降 warn-only 观察 2 周再删（由 gate-pass 计数证明 0 触发）。

> oracle_gate、action_gate 归入 L2 专用（不占日常 10 道）。全部 22→10 的映射以 checks.py 现有函数为基准（checks.py:33-906）。

### B2. 状态机与 carros_base 瘦身

1. **六件套 → 三件套**：token.json（状态）+ plan.md（契约）+ executor.md（证据，末尾含 handoff 段）。删除/并入：handoff.md（并入 executor）、evidence.jsonl（并入 EV 块）、working-set.yaml（L2 才允许保留，L1 不再生成）。
2. **carros_base.py 3,981 行拆分**：按现有 lib/ 目录收尾，拆成 `core(状态机) / docs(文档生成) / gates(门禁调用) / report(报告)` 四模块；命令从 ~40 收敛到 15：`init/status/tick/verify/archive/resume/lint/report/oracle/clarify/auto/prune/help`（其余先归档到 `retired/` 而不是删除——3 个月无人调用再物理删除，符合"僵尸机制"规则）。
3. **水位/U 型注入瘦身**（kernel.md:33-47）：删 40%/70% 软层（1M 窗口下是噪音），保留 80% 硬停；8KB 外部截断改为交给模型摘要；`<EXTERNAL_DATA>` 标签机制保留（注入面反而扩大）。
4. **PreCompact / stop-flywheel**：保留但合并入口，压缩为 1 个脚本 2 个动作。

### B3. 文档与配置

| 项 | 动作 | 验收 |
|---|---|---|
| README.md | 重写为 CarrorOS 一页说明（当前是 simpleX 宪法，错位） | 5 分钟内可答"这是什么" |
| philosophy.md | 重建 ≤30 行纯声明，删 7 个悬空引用与自写脚手架 | 全仓 md 实体引用 lint 0 悬空 |
| 文档三层结构 | 常驻 CLAUDE.md ≤200 行 + skills 按需 + archive 归档；395 份活跃文档折叠 | 活跃 md ≤10k 行 |
| omc_lint | 新增"md 引用实体存在性"检查 | lint 0 error |
| settings*.json | settings.json 唯一 hooks 真相源；_ds/_k3/_rt 只保留 env 差量；.bak 清理 | 配置 diff 门禁上线 |

// 注意：REAMDE.md是项目说明书（可以是任何一个项目），给CarrorOS治理的对象用的，被AGENTS.md引入；
// 注意：AGENTS.md为治理层的主要入口，不是CLAUDE.md
// settings*.json 暂时不要动，这个项目是给别的项目上管理的，所以实际上settings.json只应该包含hook相关的信息，其他的信息每个公司都不一样；

### B4. 技能与脚本瘦身

- lx-goal.py 1,619 行 + 测试 1,072 行：**skill 只留提示层**（SKILL.md），逻辑按模块移入 `.claude/scripts/lib/`（用现有测试护着移，不重写）。
- frontend-overnight 的 ui_autopilot（1,745 行）：本次不动（独立产品域），只做登记。
- scripts 108 → ≤50：以"被引用/被测试"为准批量归档到 retired/。

### B5. 保留清单（不许砍，动它们需人类裁决）

证据门禁文化 · 磁盘真相源三件套 · L1/L2 分级与"直达" · OFF/ON 评测法 · 盲评/双法官（降频不删） · 冻结规则与人类裁决 · 先守护后变更 · 80+ 回归测试 · error-dna 采集器 · gate-pass/hook-evidence/audit 数据管线 · skills 的 frontmatter 格式。

---

## C. 自迭代飞轮设计（真正的"越用越好用"）

### C0. 现状缺口（为什么现在不是自迭代）

数据已有（error-dna 67 条 / gate-pass / audit / hook-evidence 1,821 条），但：
- 记了错误 → 从不蒸馏（沉淀仅 1 次且 resolution=pending）
- 门禁计数 → 无人消费（僵尸门禁无感知）
- 评测分数 → 每轮人工起跑、手工对账
- 文档/门禁漂移 → 靠审计撞见（philosophy.md 7 个悬空引用即是证据）

**缺的不是数据，是"蒸馏→采纳→验证"三环。**

### C1. 五组件架构

```
┌────────────── 使用（日常任务，照常跑）──────────────┐
│  任务归档 = 一次进化样本                               │
│  （error-dna / gate-pass / audit / hook-evidence）    │
└──────────────────────┬───────────────────────────────┘
                       ▼
  ① Distiller 蒸馏器（新增，archive 钩子 / nightly 双触发）
     规则聚类 + 模型归纳 → 进化提案 proposals（每条带证据计数）
     ┌──────────────┬──────────────────┬──────────────┐
     │ 反模式提案    │ 门禁僵尸提案      │ 文档漂移提案  │
     │ (错误模式+建议)│ (0触发/误伤统计)  │ (悬空引用等)  │
     └──────────────┴──────────────────┴──────────────┘
                       ▼
  ② Approver 采纳台（人类裁决，CLI 一键 accept/reject/defer）
     accept → 自动生成 TDD 红测试 → 实现 → 全量回归绿 → commit
     reject → 原因回写数据（下次蒸馏学习什么不该提）
                       ▼
  ③ Verifier 验证器（每轮 benchmark 或 nightly）
     探针子集自动跑 + scorecard 自动对账（分数 vs 实盘数据 Δ）
                       ▼
  ④ Anti-regrowth 防膨胀闸（归档必查）
     每轮必须：删 ≥1 僵尸 或 证明无僵尸（输出证据）
     否则归档报告不通过 —— "少即是多"的机械执行
                       ▼
  回到 ①（下一轮样本带着上一轮的改进继续）
```

### C2. 数据契约（proposal schema v1）

```json
{
  "id": "p-2026-09-08-001",
  "source": "distiller",
  "kind": "anti-pattern | gate-zombie | doc-drift | new-gate | delete-candidate",
  "evidence": {"count": 12, "refs": ["error-dna.jsonl:...", "gate-pass-count.jsonl:..."]},
  "suggestion": "一句话动作建议",
  "impact_estimate": "高/中/低",
  "status": "pending | accepted | rejected | deferred",
  "human_note": "",          // 裁决意见（reject 必填）
  "test_commit": ""          // 采纳后生成的 TDD 红测试 commit
}
```

### C3. 人类裁决点（机械分界，不烦人也不越权）

| 类别 | 谁决定 |
|---|---|
| 反模式采纳/驳回 | 人（可一键批量，逐条可查） |
| 新增门禁 / 门禁语义变更 | 人 + 先红测试 |
| 删除 >100 行代码 / 文档归档 | 人（diff 清单先审） |
| 哲学 / AGENTS.md / kernel.md / hooks 核心 | 人（冻结规则，不可自改） |
| 僵尸清单生成 | 机器自动，人只看结果 |

### C4. 防膨胀规则（本设计的灵魂）

> CarrorOS 长到 11 万行不是被谁设计出来的，是"只加不减"积累的。
> 规则：**任何任务归档前，执行方必须回答"本轮删了什么或证明了什么无僵尸"（证据形式），否则归档报告不通过。**
> 让"减法"和"加法"一样成为每日动作——这才是简化能持续的机械原因。

### C5. 越用越好用的度量（每轮自动记录，进 scorecard）

- M1 闭环完成数：本轮 error-dna → 提案 → 采纳 → 测试锁死的条数
- M2 转化率：错误条目 → 有效提案的比例（太低说明蒸馏器要调，太高说明门禁太松）
- M3 僵尸率：0 触发门禁占比（目标 ≤10%）
- M4 分数曲线：benchmark 汇聚分每轮 Δ（沿用现有 OFF/ON 双法官法）
- M5 **体重曲线**：活跃代码+文档行数（目标：简化后持平或下降——反向指标，防止再次膨胀）
> M5 进 scorecard 是"简化"能被治理层自己治理的关键设计。

### C6. MVP 范围（先让飞轮转起来，约 1-2 天）

1. distiller v1：archive 后触发（≥20 条新错误才跑），输出 proposals.md + proposals.jsonl
2. approver v1：CLI `carros propose list|accept|reject`
3. accept → 自动生成红测试 → 绿 → 回归（复用现有 run_regression.py）
4. 防膨胀闸 v1：归档 checklist 加"删≥1/证明无僵尸"一问（carros_base archive 内）
5. 不动：评测/探针/文档折叠（后续阶段）

---

## D. 执行阶段与验收

| 阶段 | 内容 | 验收标准 | 风险 | 回滚 |
|---|---|---|---|---|
| **Phase 0（本文档）** | 人类评审定稿 | owner 批注/签字 | — | — |
| **Phase 1（P0 低风险，各 ≤1 天）** | README 重写；philosophy 纯声明化 + 引用 lint；评测口径锁（metrics-card 接线 judge-prompt）；配置单一化；门禁僵尸仪表 | 每项独立 commit；pytest 0 failed；lint 0 error | 低 | 独立 commit 回退 |
| **Phase 2（飞轮 MVP，1-2 天）** | C6 的 5 件 | 一次真实任务归档跑通 采集→提案→采纳→红绿 | 中（新增钩子） | 钩子独立开关 |
| **Phase 3（大简化，分模块 2-3 周）** | B1 门禁归并（G2 先降 warn 2 周取证）；B2 状态机三件套 + carros_base 拆分；B3 文档折叠；B4 skill 瘦身 | 每模块：diff 清单人审 → TDD 红绿 → 全量回归 0 failed → 行数里程碑达成（55k→≤35k→≤20k→≤15k 逐级） | 中高（触碰核心） | 每模块独立 commit + .omc/state/restore 快照（已有机制） |
| **Phase 4（评测现代化，1-2 周）** | +8 个 2026 对抗面探针；nightly 电池；scorecard 自动对账 M1-M5 | 探针设计人审通过；nightly 连续 3 晚 0 崩溃 | 中 | 探针独立目录，可整体回退 |

**全程硬门槛**：任何阶段 pytest 不允许新增失败；冻结文件（AGENTS.md/kernel.md/index.md/hooks 核心/harness.yaml）的任何触碰必须先走人类裁决；本文档 D 表之外的"顺手改动"一律不做（防止范围蔓延）。

---

## E. 不做清单（明示边界，防过度设计）

1. 不推倒重写（保留 80+ 测试与磁盘格式兼容）
2. 不引入数据库/新框架/新语言
3. 不自研 Web 控制台（MVP 用 CLI + Markdown）
4. 不做"全自动自我修改"——裁决权永久在人
5. 本轮不动 frontend-overnight（独立产品域）与评测探针口径（Phase 4 才动）
6. 不动冻结文件（除非人类逐条裁决）

---

## F. 引用

- 审计证据：MODERNIZATION_AUDIT.md §0/§1/§2/§3
- 实测数据：error-dna.jsonl(67 条) · hook-evidence.jsonl(1,821 条) · gate-pass-count.jsonl · checks.py:33-906 · carros_base.py(3,981 行) · philosophy.md 悬空引用 7 处
- 现代基线（2026）：Anthropic Steering Claude Code / subagents MEMORY / NVIDIA & AWS agent 安全框架（URL 见审计报告 §5）
