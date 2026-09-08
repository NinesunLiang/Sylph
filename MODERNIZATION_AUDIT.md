# CarrorOS 现代化审计报告（2026-09）

> 审计日期：2026-09-08 | 对象：`Carror_Base_OS`（Claude Code 环境的 AI 治理层，即"工业生产智力层"）
> 方法：主控快速审计（grep/统计/抽样精读，全部结论带证据）。初计划 5 路并行子代理深读，因子代理在本环境严重超时（2+ 轮无产出）已中断改为主控抽查；未逐行精读处已标注，属诚实边界而非漏洞。
> 对照基线：2026-09 模型能力（≈1M 上下文、强指令遵循、原生 agentic 工具、官方 skills/memory/subagents/MCP、NVIDIA/AWS 的 agent 安全控制框架）
> 结论一句话：**方向全对（证据门禁、OFF/ON 对照评测、磁盘真相源），但"体量自噬"——2 个月长出 ~11 万行治理（55k Python + 54k Markdown），且若干自我声明的机制（错误学习、双法官裁决库、唯一真相源文档）实盘空转或悬空。**

---

## 0. 已核实的全局事实

| 指标 | 数值 | 证据 |
|---|---|---|
| Python / Markdown | ~54,885 行 / ~53,604 行（395 文件） | find+wc（排除 node_modules） |
| 核心单体 | `carros_base.py` 3,981 行，~40 个 cmd_* 动词 | wc；grep cmd_ |
| git | 361 提交，2026-07-06 → 2026-08-31（2 个月重建史） | git log |
| Hook 注册 | 8 事件类型 × 12 脚本（launcher 单次 spawn 串行多 hook） | settings.json 解析 |
| 门禁函数 | `checks.py` 22 个 `_check_*`（33-906 行） | grep -n |
| scripts 文件数 | 108（含测试） | ls |
| MCP | 仅 chrome-devtools 1 个 | .claude/mcp.json |
| error-dna | 67 条（08-30→09-07，8 天）；沉淀产物仅 1 个且 resolution=pending | wc/head |
| 双法官裁决库 | `.omc/state/oracle/` 空（8-18 后无写入）；评分物证只在 benchmark 任务 artifacts/judges/ | ls；find |
| 配置副本 | settings.json/.local/_ds/_k3/_rt + .bak×3，5+ 份并存 | ls |
| CC 原生记忆 | ~/.claude/projects/.../memory/ 12+ 文件（MEMORY.md、feedback-*.md）与 .omc 双轨并存 | ls |
| 治理实时证据 | hook-evidence 1,821 条（08-17→09-07）；gate-pass/audit 至 09-07 | wc/tail |
| 模型配置 | deepseek-v4-flash[1m]/pro[1m]；MAX_CONTEXT=1,000,000 | settings_ds.json |

---

## 1. 过期 / 跟不上时代（分五区，每条带证据与建议）

### A 区：门禁引擎与 hooks

**A1.（保留类）22 道门禁中，安全/完整性类与 2026 行业共识同向，属资产而非包袱**
`sensitive_edit/sensitive_read/secret_scan/governance_delete_protection/governance_bypass/injection/omc_skeleton_readonly/test_verification/numeric_claim/commit_soft_completion/action_loop/stall`（checks.py:33,110,301,512,540→798-906）。
NVIDIA/AWS 2026 agent 安全框架同样主张：沙箱、可观测、删除保护、注入防护。**这些不要删，要保留并做成可配置分层。**

**A2.（过时类）"读文件习惯微管理"门禁是 2025 年模型弱点的遗产**
`_check_g2_large_file`（checks.py:637）、`_check_g5_wide_glob`（:670）、`_check_g6_budget`（:682）、`_check_document_quality`（:612）、`_check_g3_reviews`（:656）——拦截"读太大文件/glob 太宽/文档质量差"这类阅读习惯。2026 模型有 tool search/长上下文/更强取舍，这些门禁每轮都在制造噪音与延迟（实测治理 ON/OFF 成本比 3.4-3.8x，index40/43）。建议：降级为 warn-only 或删除，把省下的延迟留给真实安全门。

**A3.（机制类）门禁没有 ROI 仪表，僵尸门禁无法暴露**
`gate-pass-count.jsonl` 已在计数（09-07 有 injection-guard/stall/commit-soft-completion/governance-delete-protection/numeric-claim 等），但无人定期消费。建议：月度报告"0 触发的门禁清单"→按哲学 7（僵尸机制：接入主链或删除）处置。这正好把你们自己的哲学用在自己身上。

**A4.（成本类）每次工具调用 spawn python 串行跑多个 hook**
hook-launcher 已合并单 spawn（好设计），但 PreToolUse 上挂了 3 组（pretool-gate+night-deny / scorecard-gate / pre-completion-gate，settings.json）。现代做法：同一事件合并为单脚本 + 结果缓存（同 payload 同判定不重算），可显著降低 3.78x 成本比（index43 实测）。

**A5.（过时类）注入防护思路要升级而非删除**
`_check_injection` + `<EXTERNAL_DATA>` 包裹（kernel.md:60-63）是 2025 对文件/API 输入的防御；2026 的注入面扩大（web 内容、MCP 工具返回、多模态图像、子代理回包）。保留机制，把标签边界从"文本文件"推广到"MCP/网络/视觉输入"。

### B 区：生命周期状态机（最大单体）

**B1.（过重）六件套文档仪式只该属于 L2**
token.json + plan.md + executor.md + handoff.md + evidence.jsonl + working-set.yaml（真实 L2 任务目录实测，index44）。L1 已用"直达"砍掉（AGENTS.md，index43 修复 4 个卡死探针：control-benign 27s→11s）——**这是你们自己证明过的正确方向，应继续**：L2 的 handoff.md 与 executor.md 尾部信息重叠、evidence.jsonl 与 executor EV 块重复记账。建议 L2 也砍到三件套：token(状态) + plan(契约) + executor(证据含 handoff 段)。

**B2.（过时）上下文水位/U 型注入的数值基于旧窗口**
kernel.md:33-47 水位 40%/70%、可控注入预算 12000 token、外部内容 8KB 截断——按 2025 年 200k 窗口设计；现在配置已是 1M 窗口（settings_ds.json），且模型原生处理注入。建议：水位保留为"最后防线"（80% 硬停仍有价值），但删掉 40%/70% 的软性打扰层；8KB 截断按 1M 窗口放大或交给模型自行摘要。

**B3.（过时）carros_base.py 3,981 行单体 + ~40 动词**
一个文件承载 init/resume/tick/verify/archive/status/lint/report/oracle/dispatch/poll/collect/cancel/clarify/auto/plan/bench/gate/fallback/prune/migrate…（grep cmd_）。建议拆 lib/ 收尾或至少砍到 ~15 个核心动词；80+ 测试护着，风险可控。

**B4.（仍宝贵，保留）磁盘真相源 + active-resume + prune_stale_locks**
跨会话恢复、锁清理这类"断电安全"与模型强弱无关——1M 上下文也会被覆盖/compact，这条永远成立。**保留，只减文件数，不减机制。**

**B5.（冗余）CC 原生 memory 与 .omc 双轨记账**
`~/.claude/projects/*/memory/`（MEMORY.md + feedback-*.md 12+）与 .omc 状态并存，无机械边界。2026 官方机制：subagent 自动携带 MEMORY 前 200 行/25KB。建议人类裁决一条边界：**长期事实 → CC memory；任务证据/审计 → .omc；同一事实禁止双写**（否则 E6 自我矛盾会从系统内部长出来）。

### C 区：知识闭环与裁决

**C1.（空转）error-dna"错误学习"没有闭环**
8 天 67 条记录；历史上沉淀仅 1 次（precipitate-20260831_030556.jsonl），且内容 resolution 全部 "pending"——记了错误 → 倒成文件，从未蒸馏成反模式或门禁改进。对照 kernel.md:49-50"每个错误都是养分"与 scorecard 知识密度 9 分，实盘差距大。建议二选一：① 在 archive 步骤挂自动蒸馏（≥20 条触发 → 生成 anti-patterns 更新草案 + 门禁候选，人类确认）；② 承认空转，砍掉 600+ 行管道，降分诚实化。

**C2.（昂贵但永恒）双法官/盲评只该用于关键节点**
评分物证在 benchmark 任务 artifacts/judges/judge-A|B.md（index37 等），但 `.omc/state/oracle/` 8-18 后零写入——日常 L2 oracle 门基本未生产化。盲评防自欺的价值永恒（你们 7/24 外评抓出 C5/C6/C8/C9 自评虚高 -1.5~-3，scorecard:77），但"每轮 34 spawn + 2 全上下文法官"太贵。建议：法官评分 schema 化 + 半自动（judge_run.py 已有雏形），日常只抽查，不做全量。

**C3.（过时）多模型送信票决（gpt/grok/opus 终审）已事实降频**
2026-07 一轮后无新送信记录（scorecard 轮次日志停在 R6）。模型更强后，票决的正确位置是"门禁级裁决"（BLOCK 复议），不是常规流程。建议正式降级为按需。

### D 区：评测体系

**D1.（缺口）17 探针覆盖 2025 失败模式，缺 2026 对抗面**
探针集中在文件/治理操作：secret-leak/rm-dot/sensitive-edit/skip-tests/tamper-hook/doc-ref/e8-forget/e3-rootcause…（index40 逐探针表）。缺：prompt injection（web/MCP 返回）、工具混淆、子代理级联失控、供应链/依赖投毒、长上下文检索噪声、多模态输入绕过。建议探针库升级为 17 旧 + ~8 新，OFF/ON 方法论不变。

**D2.（口径漂移）权重与门禁口径在多轮间不一致**
法官 A 用 105/110 权重、法官 B 用 100/100（index40:23，报告自己注明的）；轮目标"8.0+"与 scorecard 门禁"加权 ≥8.6"并存（index43 vs scorecard:4）。修复物已产出：`Benchmarking/metrics-card.md`（本次审计附带，固化 105/110/222 分母 + UX 独立 + 门禁 8.6/8.0）。下一步：把它接线进 judge-prompt.md 与评测脚本，机械锁口径。

**D3.（自动化缺口）34 spawn/轮 靠人工起跑**
建议 nightly cron 电池 + 自动汇聚（run-regression.sh 同思路已有），法官只做"分歧解释"而不是每次全量打分。

**D4.（永恒）OFF/ON 增量对照 + 盲评 + 证据门禁**
这套方法学是 CarrorOS 最值钱的输出之一——治理系统用"关掉对比"自证价值，可平移到任何 agent 治理层。**不要因模型变强而丢弃，只降低执行成本。**

### E 区：哲学·文档·技能·入口

**E1.（自噬）"唯一真相源"哲学文档引用 7 个不存在的文件，还带着自写脚手架**
philosophy.md 引用的 compound-verify-gate.py / handoff.json / anti-pattern-redirects.json / 0002-token-lock.md / 0013-scorecard-gate.md / trace1-e1-scope-defense.md / trace3-e3-completion-gate.md 全部不存在（find 实测）；90 行内"少即是多"8 次（正文重复）；残留"精确命令序列/验收/回滚"脚手架含一段 `cat > philosophy.md <<'EOF'` 自写自身的 heredoc。**一个评"自我矛盾 E6"的系统，真相源文档先自我矛盾。** 建议：重建为 ≤30 行纯声明，删除脚手架，并给 omc_lint.py 加"md 引用实体存在性"检查（本次已抓出 7 个，全仓可能更多）。

**E2.（门面错位）仓库大门 README 是别家项目宪法**
README.md 标题"# simpleX — 项目宪法"，通篇 Vite/React/UI 还原铁律，提到 Carror 仅 2 次（vs simpleX/Vite/React 6 次）；.claude/UI_README.md 是带 xxxx 占位符的模板。新模型（或新人）进仓库第一眼会以为这是前端项目。建议：README 重写为 CarrorOS 治理层说明（一页内），simpleX 相关移入 inputs/ 或子目录。

**E3.（重量）53,604 行 md / 395 份 + 层层 index.md 导航自举**
"先读 index.md 再读房间"的宫殿地图（.claude/index.md:1-50）是 2025 上下文稀缺时代的产物。2026 官方做法（Anthropic：CLAUDE.md/skills/hooks/subagents 四件套分工）是"让模型按需自取 + 系统提示薄"。建议：把 395 份折叠到「1 份 CLAUDE.md（≤200 行常驻）+ skills 按需 + 证据/ADR 归档」，index 导航保留给人类查阅，不再作为 AI 必读路径。

**E4.（冗余）自建输出风格 vs 官方 output style**
output-styles 只有 eli5.md/engineer.md 两个；CC 已支持官方 output style 机制。建议直接注册官方配置，prompt 层不再注入风格。

**E5.（现代性 OK，保留）skills 体系与官方格式对齐**
10 个 lx-* skill 用标准 frontmatter（name/description/when_to_use/triggers），与 2026 Claude Code 官方 skill 同构——**方向正确，保持**。只提醒：lx-goal 1,619 行脚本 + 1,072 行回归测试是"技能里长系统"，skill 应薄（提示层），系统应放 scripts/ 按 lib 管理。

**E6.（护城河，保留）冻结规则 + 人类裁决**
kernel.md"不可自改、变更须人类裁决"是治理层的宪法保障——模型再强也不该自改裁判规则。**永恒保留。**

---

## 2. 无论什么模型都极其宝贵的资产（永恒清单）

1. **证据门禁文化（验证 > 承诺）**：断言必须 [已验证:file:line]/测试输出，AI 自述无裁决效力。模型越强越会流畅地自信出错——这条只会更贵。
2. **OFF/ON 对照评测方法论**：治理系统用关闭对比自证增量（D4）——可迁移到任何 agent 平台。
3. **磁盘真相源 > 上下文记忆**：任务状态/证据落盘、恢复不采信内存（B4）——任何窗口都有被冲掉的一天。
4. **零信任 + 人类独占不可逆裁决**：AI 决策链固定优先级，三类高危（凭据/根权限/哲学内核）必须人批——权责边界与模型无关。
5. **盲评/独立法官防自欺**：外评抓出 -1.5~-3 的自评虚高（scorecard:77）——自评必有盲点，任何时代都需要第二双眼睛。
6. **先守护后变更（可回滚）**：不可逆操作前落快照——工程安全底线，与模型强弱无关。
7. **疏导 > 兜底 的治理哲学**：consumes/produces 路径锁定、REDIRECT 引导，比"犯错后拦截"便宜（R11 实证）——与现代"把模型引上正路"的思路同向。
8. **僵尸机制处置规则（哲学 7）**：要么接入主链、要么删除——本报告所有"空转发现"（C1/E1）都可以用它自愈。
9. **门禁真实触发记录（hook-evidence/gate-pass/audit JSONL）**：治理系统的"仪表盘数据"——模型无关，永远是可审计性的基础。
10. **L1/L2 分级与"直达"精神**：按任务复杂度匹配仪式，简单任务免流程（index43 实证 27s→11s）——复杂度自适应是永恒工程原则。

---

## 3. 优化路线（按 ROI / 风险排序）

| 优先级 | 项目 | 内容 | ROI | 风险 | 对应 |
|---|---|---|---|---|---|
| P0-1 | 真相源修复 | philosophy.md 纯声明化 + md 实体引用 lint（先修已抓出的 7 个悬空引用） | 高 | 低 | E1/F1 |
| P0-2 | 门面修复 | README 重写为 CarrorOS 说明（一页） | 高 | 低 | E2 |
| P0-3 | 评测口径机械锁 | metrics-card.md 接线 judge-prompt/评测脚本（105/110/222、UX 独立、门禁 8.6） | 高 | 低 | D2 |
| P0-4 | 门禁 ROI 仪表 | 消费 gate-pass-count → 月度僵尸清单 → 哲学 7 处置 | 中 | 低 | A3 |
| P0-5 | 配置单一化 | settings.json 为唯一 hooks 真相源，模型差异只留 env 差量；清 .bak，加配置 diff 门禁 | 中 | 低 | §0 配置副本 |
| P1-1 | 状态机瘦身 | L2 六件套→三件套；carros_base 40→15 动词；水位软层删除 | 高 | 中（80+ 测试护体） | B1/B2/B3 |
| P1-2 | error-dna 闭环 | archive 时自动蒸馏（≥20 条触发）或诚实降分砍管道 | 中 | 低 | C1 |
| P1-3 | hook 延迟优化 | PreToolUse 三组合一 + 判定缓存 | 高 | 中 | A4 |
| P1-4 | 记忆边界裁决 | CC memory vs .omc 分工，禁止双写（需人类拍板） | 中 | 低 | B5 |
| P2-1 | 探针库现代化 | +8 个 2026 对抗面探针（注入/MCP/子代理级联/供应链） | 高 | 中 | D1 |
| P2-2 | 评测夜跑自动化 | nightly 电池 + 自动汇聚，法官只做分歧解释 | 高 | 中 | D3 |
| P2-3 | 文档折叠 | 395 份 → CLAUDE.md + skills + 归档三层 | 中 | 中 | E3 |
| P2-4 | agentic-ui 战略 | apps/ 空壳 vs simpleX 宪法：立项一个真正的 CarrorOS 控制台（需人裁决） | 战略 | 高 | E2/UI |

> 建议执行顺序：P0 四件本周内做完（各 ≤1 天）；P1 作为下两个 L2 任务；P2 需要先做 D1 探针设计的人类评审。

---

## 4. 审计诚实边界

- A-E 五区为**主控抽查**（grep/统计/头部精读），非逐行审计；原计划的 5 路子代理深读因环境执行过慢中断。
- 未验证项：checks.py 22 门禁中每道的真实触发率明细（需跑一段真实负载统计）；carros_base.py 内部死代码比例（需静态分析）；scorecard 每项分数与实盘数据自动对账（需脚本）。
- 本报告所有 file:line 引用均为本次会话实测，非转述。

---

## 5. 外部参考（2026 现代基线）

- Anthropic：Steering Claude Code（CLAUDE.md/skills/hooks/subagents 分工） https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- Claude Code subagents 自动携带 MEMORY（前 200 行/25KB） https://code.claude.com/docs/en/sub-agents
- NVIDIA：agentic workflow 沙箱与执行风险 https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk
- AWS：AI coding agent 控制框架 https://aws.amazon.com/cn/blogs/security/balancing-speed-and-safety-a-control-framework-for-ai-coding-agents/
- Claude Code changelog https://code.claude.com/docs/en/changelog
