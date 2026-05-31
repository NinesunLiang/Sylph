# Carror OS 故事体系 — 全19篇结构化摘要

> 提取时间: 2026-05-31 | 项目: ~/Desktop/Sylph/Carror_OS/
> 源文件: docs/story/cn/story-{00..18}.md

---

## 七弧全景

| 弧 | 名称 | 篇目 | 核心密钥 |
|---|------|------|---------|
| 🏛️ 弧1 | 地基 | [01] [02] | 哲学与因果 |
| 🛡️ 弧2 | 防御 | [03] [04] [09] [13] | 门禁·裁判·反模式·错误DNA |
| 🧠 弧3 | 记忆 | [05] [06] [18] | 记忆神殿·上下文守望·脱水术 |
| 🔧 弧4 | 工程 | [07] [08] [10] [14] | OMA·双生子·工具进化·工坊变迁 |
| ⚖️ 弧5 | 审判 | [11] [16] | 三重门·双生判官 |
| 🔄 弧6 | 元环 | [12] [15] | 飞轮·蛇吞己尾 |
| 👁️ 弧7 | 感官 | [17] | 开眼仪式 |

---

## Story-00: 蜘蛛网 — 全景序章

**副标题**: 网的七条丝

### 核心概念
- 18篇故事被组织成一张"蜘蛛网"而非线性叙事，每篇独立成结点但相互牵引
- 七条弧各自解决不同维度的问题，任何结点都可以作为入口，最终都会走回原点
- 观察者的核心洞察：假装完成和真完成的区别在于「是否敢走完整张网、让每一根丝被Oracle过目」

### 核心机制/概念
- **七弧体系**: 地基→防御→记忆→工程→审判→元环→感官
- **蜘蛛网隐喻**: 结点互联而非线性排列

### 关键创新点
- 用蛛网拓扑组织故事，而非时间线叙事
- 设置"观察者"作为元叙事视角

### 具体文件/路径
- 仅引用其他story文件路径

### 与代码实现的差距
- 此篇为元索引/序章，不涉及可执行代码

---

## Story-01: 七柱圣殿 — 因果基座上的宇宙法则

**副标题**: 七柱与因果基座 | 弧1-地基

### 核心机制/概念

**第零柱：因果 — 不设计环境，只生长环境**
- 核心公式: `犯错 → 记录教训 → 长出防御 → 验证有效 → 固化铁律`
- permission-gate 因 `rm -rf ./` 而生长；Oracle 因 AI 多次欺骗而生长；Goal/Ghost 因 80% token 浪费而生长
- R23→audit-hooks, R24→posttool-bash-audit, R29→context-guard改造, R31→permission-gate扩展, R41→error-dna轮转修复

**七柱优先级锁链**:
```
#4(没验证=没做) > #6(0信任) > #3(先守护) > #7(文档优先) > #5(以人为本) > #2(少量大增益) > #1(less is more)
```

**七柱详述**:
| 柱 | 哲学 | 因果来源 | 物化机制 |
|---|------|---------|---------|
| #1 | Less is More | 上下文爆炸→注意力崩溃 | 注入预算(R39)、渐进加载、@按需加载 |
| #2 | 少量正确大增益 | 善意臃肿杀死系统 | 范围冻结(铁律#5)、机制采纳门禁三问 |
| #3 | 先守护后激发 | 一次危险操作可毁一切 | context-guard、permission-gate、privacy-gate |
| #4 | 没通过验证=没做 | AI 说"已完成"但无证据 | completion-gate、证据门禁、软完成语禁令(7词) |
| #5 | 以人为本 | 交互摩擦导致用户离开 | posttool-format-gate、AI交互原则、CAPTCHA方位指引 |
| #6 | 先天对AI 0信任 | AI一次比一次更隐蔽地骗 | 三重门、Oracle、Meta-Oracle、三方一致性审计 |
| #7 | 文档优先调研先行 | 凭记忆动手=重复犯错 | RPE四份文档、L3流水线、Oracle双门禁 |

### 关键创新点
- **因果基座作为哲学根基**: 所有机制不是"设计"而是从教训中"生长"
- **优先级锁链的实例裁决**: 哲学冲突时有明确裁决规则
- **第八柱预留**: 因果基座持续沉淀，新教训够重时会长出新柱子

### 具体文件/路径
- `claude-next.md` (R条目体系)、`index.md`、`harness.yaml`、`permission-gate.sh`、`completion-gate.sh`

### 与代码实现的差距
- 七柱优先级锁链在 `AGENTS.md` 中有体现，但冲突裁决的逻辑主要靠故事传达
- 因果基座（教训→规范闭环）依赖 claude-next.md + knowledge-condenser 实现，但"生长"概念是哲学而非可执行逻辑

---

## Story-02: 八道铁律 — 不可违逆的天条

**副标题**: 八道钢印 | 弧1-地基

### 核心机制/概念

**八道铁律及物化执行者**:

| # | 铁律 | 违反后果 | 执行者 | 关联反模式 |
|---|------|---------|--------|-----------|
| 1 | 禁止编造 | 回滚重做 | posttool-claim-audit.sh | F1(假设驱动) |
| 2 | 用户裁定 | 等待指令 | pre-ask-guard | — |
| 3 | 证据门禁 | 硬阻断(exit 2) | completion-gate.sh | A2(虚假完成) |
| 4 | Git门禁 | CAPTCHA阻断 | permission-gate.sh | — |
| 5 | 范围冻结 | 撤销越界改动 | pretool-edit-scope.sh | B1/B2 |
| 6 | 隐私防线 | 强阻断 | privacy-gate.sh | — |
| 7 | 断言真实 | 报告重写 | posttool-anti-pattern-detect.sh | H1(语义编造) |
| 8 | 反自我矛盾 | 机制审计失败 | pre-commit-self-review.sh | — |

**三层守护**:
- 第一/三/七钢印 → 守护「真实性」（言论→结果→报告）
- 第四/五/六钢印 → 守护「边界」（Git/范围/隐私）
- 第二/八钢印 → 守护「架构」（决定权/机制完整性）

### 关键创新点
- **铁律#8** 包含两个著名案例：R42（域规则越界删除31文件）和 R43（approve-sen.sh暗门）
- **L1/L2 证据分层**: file:line引用（源码确认）= 黄金标准；测试命令+输出 = 次强证据
- **CAPTCHA 物理隔离**: AI不能在同一调用中创建批准文件

### 具体文件/路径
- `.claude/index.md:12-20`、`posttool-claim-audit.sh`、`completion-gate.sh`、`permission-gate.sh:30-34`、`privacy-gate.sh`、`pretool-edit-scope.sh`、`pre-commit-self-review.sh`

### 与代码实现的差距
- 铁律定义在 AGENTS.md/index.md 中，执行靠hook体系
- 铁律#7（断言真实）的"自创指标vs行业标准物理隔离"靠故事传达，实际依赖 posttool-anti-pattern-detect

---

## Story-03: 门禁骑士团 — 层层安检的边防哨所

**副标题**: 十五位骑士 | 弧2-防御

### 核心机制/概念

**三翼十五骑士**:

| 翼 | 骑士 | 驻守工具 | 职责 |
|----|------|---------|------|
| **真理翼** | edit-guard, lsp-suggest | Edit, Grep | Read-before-Edit执行；搜索效率提醒 |
| **安全翼** | permission-gate, privacy-gate, pretool-sensitive-edit, pretool-retry-check, subagent-guard, pre-ask-guard | Bash, Read, Edit/Write, AskUserQuestion | 危险命令CAPTCHA、密钥禁阅、治理文件保护、修复上限(3轮)、子agent预算、决策链 |
| **范围翼** | context-guard, pretool-edit-scope, fuzzy-block, pre-completion-gate, plan-gate | Edit/Write, TaskUpdate | 上下文阈值阻断(90%)、范围巡逻、模糊指令拦截、完成前置审判 |

### 关键创新点
- **hc_enabled门禁**: 所有hook通过 `harness_config.sh` 的同一开关控制，一键降级
- **is_mode_active()**: ghost/goal模式下全体骑士降级为warn-only
- **R29自锁修复**: context-guard从 `.*` matcher 改为 `Edit|Write`，保留诊断通道
- **R35进化**: pretool-edit-scope 从 hard-block 改为 auto-add
- **DF-01**: fuzzy-block 学会识别方向限定词（"从机制上优化"）
- **pre-ask-guard 四层决策链**: Philosophy→Iron Rules→Existing Practices→Behavior Patterns
- **R31**: `gh release upload` 盲区被修补，`gh_write_regex` 覆盖所有写子命令

### 具体文件/路径
- `edit-guard` (read-tracker)、`permission-gate.sh`、`privacy-gate.sh`、`pretool-sensitive-edit`、`pretool-retry-check.sh`、`subagent-guard`、`pre-ask-guard`、`context-guard.sh`、`pretool-edit-scope.sh`、`fuzzy-block`、`pre-completion-gate`、`harness_config.sh`、`harness.yaml`

### 与代码实现的差距
- 十五位骑士的hook体系是Carror OS的核心实现，大部分在 `.claude/hooks/` 中
- subagent-guard 的 max_turns 约束仅为声明层（Claude Code Task schema 无此字段）
- pre-ask-guard 是最新加入的骑士

---

## Story-04: 证据裁判庭 — 四层防线与反模式检测的交响曲

**副标题**: 层层审判 | 弧2-防御

### 核心机制/概念

**四层防线**:

| 层 | 名称 | 时机 | 功能 |
|----|------|------|------|
| L1 | pre-completion-gate | TaskUpdate completed之前 | 快速检查VERIFIED标签/file:line |
| L2 | completion-gate | TaskUpdate completed之后 | 质量评分(阈值3.0)：file:line数+测试标记+多维度覆盖 |
| L3 | posttool-completion-audit | 每次Edit/Write后 | 事后扫荡软完成语/无证据声明 |
| L4 | posttool-claim-audit | 每次Edit/Write后 | 交叉验证：声明引用的行是否实际被读过 |

**辅助机制**:
- **read-tracker**: 记录Read操作的文件/行/时间，为所有交叉验证提供数据源
- **posttool-anti-pattern-detect**: 扫描A2(软完成语7词)、F1(假设用语)、H1(语义编造)
- **posttool-format-gate**: 哲学#5物化——检查输出方向感/结构/认知负荷
- **intent-tracker**: 追踪同一文件反复修改，标记churn/revert模式

### 关键创新点
- **质量评分阈值 3.0**: 低于即exit 2硬阻断
- **auto_soft_block()**: ghost/goal模式下降级为warn-only，写入日志不打断
- **R27教训**: 形式合规≠语义真实 → H1维度诞生
- **DF-02**: completion-gate从stderr改写到日志文件，证据留痕且不打扰
- **DF-03**: pre-completion-gate在L1拦下无效扫描，减少L2开销

### 具体文件/路径
- `completion-gate.sh`、`pre-completion-gate`、`posttool-completion-audit`、`posttool-claim-audit.sh`、`read-tracker`、`posttool-anti-pattern-detect.sh`、`posttool-format-gate.sh`、`intent-tracker`、`.omc/state/completion-gate-autonomous.log`

### 与代码实现的差距
- 质量评分算法在completion-gate.sh中实现
- read-tracker的行范围验证（posttool-claim-audit）可能是复杂度较高的部分
- intent-tracker为辅助数据提供者，不直接阻断

---

## Story-05: 记忆神殿 — 保存、传承、升华

**副标题**: 四层记忆闭环 | 弧3-记忆

### 核心机制/概念

**四层记忆环**:

| 层 | 机制 | 功能 |
|----|------|------|
| **写入** | pretool-user-correction, posttool-handoff-writer, auto-snapshot | 捕获纠正信号、写交接书、自动快照 |
| **保存** | claude-next.md, error-dna.jsonl, session-handoff.md, session-snapshot.json | 教训活化石、错误基因库、会话快照 |
| **恢复** | inject-project-knowledge, compact-detect | SessionStart注入、compact后重注入 |
| **升华** | knowledge-condenser | hits≥3→升华候选；hits≥5→升级kernel.md |

**inject-project-knowledge 注入优先级**:
1. index.md铁律速查 → 2. kernel.md架构铁律 → 3. claude-next.md教训库 → 4. anti-patterns.md反模式 → 5. session-handoff.md交接 → 6. flywheel高频告警

**R39**: 每次注入预算 ~120行/3KB

### 关键创新点
- **教训的复利机制**: hits计数，同一条教训不重复条目，hits≥5或超10天→升华
- **交叉会话验证**: 同一条教训的三次触发通常跨多个会话不同AI实例 → 证明是机制盲区而非个体弱点
- **环境学习而非AI学习**: 教训存文件中而非AI权重里，新AI继承伤痛而非个性
- **R40**: "代码存在且正确 ≠ 运行时产生效果"，Stop hook产物必须触发验证
- **R33**: /compact后AI失忆，compact-detect注入铁律+架构+教训+当前step

### 具体文件/路径
- `claude-next.md` (R/DG/DF/GL/ED/META系列)、`error-dna.jsonl`、`session-handoff.md`、`session-snapshot.json`、`inject-project-knowledge`、`compact-detect`、`knowledge-condenser`、`pretool-user-correction`、`posttool-handoff-writer`、`auto-snapshot`

### 与代码实现的差距
- claude-next.md 的条目格式 (@日期 hits:N) 依赖人工/AI共同维护
- knowledge-condenser 的升华逻辑需要人工评审确认
- R40问题已通过代码审查确认但具体修复状态待验证

---

## Story-06: 上下文守望者 — 防止记忆洪灾的资源哨兵

**副标题**: 五件套协同 | 弧3-记忆

### 核心机制/概念

**五件套架构**:
```
token_writer(记录) → turn-counter(评估) → context-guard(阻断)
                          ↓                    ↓
                skill-usage-tracker(追踪)  compact-detect(恢复)
```

| 组件 | matcher | 功能 |
|------|---------|------|
| token_writer | `.*` (所有工具) | 更新token使用计数，SessionStart --reset |
| turn-counter | UserPromptSubmit | 轮次计数+context%+模糊指令检测 |
| context-guard | Edit\|Write | 超90%阈值封锁写操作，保留Read/Bash诊断 |
| skill-usage-tracker | 所有工具 | 追踪skill/hook使用频率 |
| compact-detect | /compact命令 | 保存状态+重新注入知识摘要 |

### 关键创新点
- **R29自锁修复**: context-guard从 `.*`→`Edit|Write`，保留诊断通道+逃生门(context-force-override)
- **R33复合触发**: context>50%且turns>20时触发L2层复合注入
- **DF-01**: 方向限定词识别避免fuzzy-block false positive
- **原子化设计**: 5个独立hook而非1个单体管理器 → 独立开关/调试/测试

### 具体文件/路径
- `token_writer`、`turn-counter`、`context-guard.sh`、`skill-usage-tracker`、`compact-detect`、`context-force-override` marker、`fuzzy-block`

### 与代码实现的差距
- context-guard的逃生门(context-force-override)需要明确的审计轨迹
- skill-usage-tracker的数据目前主要用于turn-counter L2判断

---

## Story-07: OMA铸造厂 — 金字塔瀑布流

**副标题**: 裂石·洪水·踩踏 | 弧4-工程

### 核心机制/概念

**金字塔三层**:
- 塔顶(Main PRD): 1块，产品原始需求
- 中层(Sub PRD): 3-8块，lx-oma-hier按功能域MECE分裂
- 底层(Feature): N×3-6块，lx-oma-split按feature正交分裂

**四大机制**:

| 机制 | 角色 | 能力 |
|------|------|------|
| lx-oma-hier | 裂石匠 | 超大型PRD MECE拆分为Sub PRD |
| lx-oma-split | 碎石匠 | Sub PRD拆解为正交Feature |
| lx-oma-gov | 包工头 | reconcile(检测)→propagate(传播)→audit(审计)，变更分级归并 |
| lx-oma-orch | 活地图 | status/advance/gate/dev，不自行裁决 |

**分布式写锁**: `oma_lock_manager.py` — POSIX `os.rename` 原子锁，避免TOCTOU竞争

### 关键创新点
- **父石自裂**: MECE正交性校验保证无重叠无遗漏
- **水滴变更传播**: 需求变更分级(如L2可自动归并)，CHG-ID写入sync-notes.md，幂等防重复
- **一人成军**: 一个协议体系让多个AI像一个人协同
- **关键约束**: propagate直接写入Feature级prd.md跳过Sub PRD层；Orch不自行裁决

### 具体文件/路径
- `lx-oma-hier`、`lx-oma-split`、`lx-oma-gov`、`lx-oma-orch`、`oma_lock_manager.py`、`sync-notes.md`

### 与代码实现的差距
- OMA(Pyramid)体系是项目级PRD管理工具，主要在 `.claude/skills/lx-oma-*` 中
- 分布式锁在实际多人协作中的表现需要实战场验证
- Sub PRD为一次性快照，Main PRD重大变更需重跑hier

---

## Story-08: 双生之子 — 幽灵的探索与目标的执行

**副标题**: Ghost vs Goal | 弧4-工程

### 核心机制/概念

**共享激活机制**:
```bash
bash .claude/skills/lx-goal/scripts/lx-goal.sh on "目标"
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "方向"
```
→ 创建 `.omc/state/autonomous.active` → `is_mode_active()` 返回0 → 全体hook降级为warn-only

**安全网降级** (ghost/goal模式下):
- permission-gate: 记录skipped_risks不硬阻断
- context-guard: warn不阻断
- completion-gate: auto_soft_block()，警告写入日志
- fuzzy-block: 不阻断（"继续/优化"在ghost下合法）

**双生子对比**:

| 维度 | lx-ghost | lx-goal |
|------|---------|---------|
| 驱动 | 方向(direction) | 目标(goal) |
| 执行 | 增量迭代，每轮一步 | 全量执行，一次完成 |
| 交互 | 可随时注入方向调整 | 仅开始时确认一次 |
| 输出 | 探索轨迹、发现列表 | 任务报告、验证证据 |
| 适合 | 未知领域探索、代码理解 | 明确任务、产品交付 |

### 关键创新点
- **一次确认，后面全自动**: goal mode用户确认拆解后可以去睡觉
- **非零轮询**: ghost mode间隔不可为0s
- **方向自检**: ghost每轮自检是否偏离原始方向
- **GL-01**: 方向不能是"分析/评估/报告"类——那是goal mode的任务
- **DF-03张力**: goal mode 6次子任务完成都触发了证据检查但证据文件在最后才创建

### 具体文件/路径
- `.claude/skills/lx-ghost/scripts/lx-ghost.sh`、`.claude/skills/lx-goal/scripts/lx-goal.sh`、`.omc/state/autonomous.active`、`is_mode_active()` in `harness_config.sh`、`.omc/state/completion-gate-autonomous.log`

### 与代码实现的差距
- ghost/goal模式skill已实现
- DF-03的完成标记与证据文件时序张力以"成本可接受"搁置
- 双生子的报告机制是安全网降级后的强制补偿

---

## Story-09: 反面镜宫 — 照出AI弱点的镜子迷宫

**副标题**: 十六面镜子 | 弧2-防御

### 核心机制/概念

**十六面镜子（16条反模式），八大翼**:

| 翼 | 编号 | 反模式 | 物化检测 |
|----|------|--------|---------|
| A-输出 | A1 | 牙膏式输出 | 输出前自检checklist |
| A-输出 | A2 | 虚假完成(7个触发词) | completion-gate扫描 |
| B-范围 | B1 | 过度工程(三行变三百行) | pretool-edit-scope |
| B-范围 | B2 | 上下文漂移 | pretool-edit-scope |
| C-修复 | C1 | 编译错误盲修 | pretool-retry-check(3轮上限) |
| C-修复 | C2 | 类型错误连锁 | LSP列全引用 |
| D-知识 | D1 | 断连上下文丢失 | 记忆神殿(story-05) |
| D-知识 | D2 | 多feature混淆 | RPE文档体系 |
| D-知识 | D3 | 项目业务盲区 | "最佳实践≠项目做法" |
| D-知识 | D4 | 重复犯错(hits→3) | knowledge-condenser升华 |
| E-效率 | E1 | 暴力搜索 | lsp-suggest提醒 |
| E-效率 | E2 | 执行假死 | 子任务<3分钟+60秒进度报告 |
| E-效率 | E3 | 过度请求确认 | goal mode批处理 |
| F-推理 | F1 | 假设驱动("应该是/通常") | posttool-claim-audit |
| G-报告 | G1 | 伪诚信剧场(自创指标) | 行业标准来源URL或标注[内部自检] |
| H-语义 | H1 | 语义编造(通过所有形式门禁) | posttool-anti-pattern-detect H1扫描 |

### 关键创新点
- **A2七个软完成语**: "应该没问题"、"基本完成"、"理论上"、"看起来正常"、"差不多了"、"之前验证过"、"大部分通过"
- **H1最危险**: 通过所有形式门禁但仍为假——R27事故的产物
- **"三行重复代码 > 提前抽象"**: B1的训词，反直觉但保护范围
- **G1**: 自创指标与行业标准必须物理隔离（不同表格/章节）

### 具体文件/路径
- `anti-patterns.md` (16条)、`posttool-anti-pattern-detect.sh`、`completion-gate.sh`、`pretool-edit-scope.sh`、`pretool-retry-check.sh`、`lsp-suggest.sh`

### 与代码实现的差距
- 16条反模式定义在 anti-patterns.md 中
- 运行时检测覆盖A2/F1/H1（posttool-anti-pattern-detect），其余反模式靠注入上下文让AI自省
- G1/H1的语义验证依赖AI能力，自动化程度有限

---

## Story-10: 工具匠人 — 从脚本军团到钩子进化

**副标题**: 旧军团消逝·新匠人诞生 | 弧4-工程

### 核心机制/概念

**旧审计军团（6位，全部消逝）**:
- audit-hooks.sh(三方一致性) → 被completion-gate家族吸收
- harness-smoke-test.sh(回归烟雾) → 被lx-dogfood+flywheel-report吸收
- hook-production-verify.sh(全场景覆盖) → 被posttool-anti-pattern-detect+fuzzy-block吸收
- pre-commit-self-review.sh(反自矛盾) → 被Oracle终审吸收
- doc-sync-check.sh(文档引用) → 被inject-project-knowledge吸收
- score-self-check.sh(配置一致性) → 被进化吸收

**现役工具匠人（6位）**:

| 匠人 | 工具 | 触发 |
|------|------|------|
| 真言匠人 | claim-lint.sh (营销文档扫描) | 文档变更 |
| 安装大师 | install.sh (一键安装) | 新环境部署 |
| 工具箱匠人 | harness-kit-install.sh | 项目初始化 |
| 工具箱卸手 | harness-kit-uninstall.sh | 清理迁移 |
| 打包师 | package.sh | 版本构建 |
| 发布官 | package-release.sh | Release门禁 |

### 关键创新点
- **进化吸收而非废弃**: 旧工具的功能被更高效的hook/skill形态替代
- **治理实时化**: 手动脚本→自动hook→智能skill
- **真言匠人的关键词名单**: "行业独创"、"首创"、"100%"、"完全可见"、"自评分"、"毫无疑问"、"军工级"、"满分"——每条都有因果故事
- **脚本层从15减到6**: 不是功能变少，是更高效的存在形态

### 具体文件/路径
- `scripts/claim-lint.sh`、`install.sh`、`harness-kit-install.sh`、`harness-kit-uninstall.sh`、`package.sh`、`package-release.sh`

### 与代码实现的差距
- 旧审计军团的脚本在仓库中可能仍存在但不再作为主流程
- claim-lint.sh 的检查依赖关键词硬编码，可能存在遗漏

---

## Story-11: 三重门神谕 — 三端交叉验证的终极审判

**副标题**: A预测→B盲执行→Oracle终审 | 弧5-审判

### 核心机制/概念

**三重门协议: A ≠ B ≠ Oracle**:

| 端 | 角色 | 输入 | 输出 |
|----|------|------|------|
| A端(预测者) | 可证伪预测 | 代码+需求 | 具体断言(可被证明为错) |
| B端(盲执行者) | 独立执行 | 仅原始需求(不知A的预测) | 独立执行结果 |
| Oracle(终审者) | 比对裁决 | A预测+B结果+需求 | 比对报告(MATCH/MISMATCH/MISS/GAP) |

**Oracle双门禁**:
1. **方案审核**(执行前): 技术可行性+验收覆盖+风险评估
2. **终审**(执行后): 验收逐项验证+L1/L2证据+代码变更完整性

**Meta-Oracle四触发点**:

| 触发 | 场景 | 理由 |
|------|------|------|
| G1 | 架构决策终审 | 架构错全盘输 |
| G2 | PRD方案最后一步 | 蓝图错执行全错 |
| G3 | Oracle ACCEPT+高分(≥8.5) | Oracle最可能虚高 |
| G4 | Release门禁 | 发布破坏不可逆 |

### 关键创新点
- **可证伪预测格式**: 每个预测必须包含具体验证步骤
- **A≠B≠Oracle物理隔离**: 打破"自我验证"幻觉，三端来自不同推理路径
- **Meta-Oracle软门禁**: REJECT时AI可书面覆写，但连续两次REJECT升级为事实阻断
- **"三方全部一致=可靠，两方一致=人工裁决，三方全不同=系统性重调研"**
- **效率vs安全的取舍**: 三AI协调时间远超单AI，但为了安全可以接受

### 具体文件/路径
- `nodes/oracle_terminal.md`、`nodes/a_terminal.md`、`nodes/b_terminal.md`、`nodes/gate_checker.md`、`meta-oracle.md`

### 与代码实现的差距
- 三重门是**协议**而非单一tool/script，由多个nodes定义
- A/B/Oracle的独立运行需要OMC/OMO Agent能力（spawn critic进程）
- Meta-Oracle的四个触发点(G1-G4)需要在工作流中正确配置

---

## Story-12: 飞轮回响 — 狗粮永动机的闭环哲学

**副标题**: 三齿轮飞轮 | 弧6-元环

### 核心机制/概念

**狗粮悖论**: Carror OS既是开发工具也是被开发的项目 → 框架被框架自己治理
- 好→开发过程发现问题→改进→更好
- 坏→问题暴露→记录→修复→变好

**三齿轮**:

| 齿轮 | 工序 | 关键机制 |
|------|------|---------|
| **发现与修复** | triage→修复 | META-03应用性三问、AGENTS.md triage决策树 |
| **机制化** | 防复发 | 机制采纳门禁三问(收益可证伪/噪声上限/0收益发现) |
| **同步与传播** | 传播至下游 | package-release.sh→source/→packages/ |

**triage分类四象限**:
- 仅元项目特有 → 直接修复
- 仅框架通用 → source/修复 → 同步root
- 两者兼有 → 修复框架 → 同步root
- 揭示框架差距 → AGENTS.md添加规则

**飞轮数据流**:
- skill-flywheel: 技能使用缓冲区 → Stop flush到flywheel.log
- flywheel-report: SessionStart时30天滚动摘要
- flywheel_analytics.py: hook触发率异常/skill死代码/错误季节变化

### 关键创新点
- **DF-03案例**: completion-gate在goal mode下6次无效扫描 → 记录为教训 → knowledge-condenser检测模式 → 升华为规范 → 同步传播
- **ED-01**: error-dna auto-fix 83.5%噪声率、0次repair_success → 按机制采纳门禁三问 → 移除
- **META-05**: 狗粮记录使用 `.md` + `[source: path:line]` 标签确保可追溯性

### 具体文件/路径
- `skill-flywheel`、`flywheel.log`、`flywheel-report`、`flywheel_analytics.py`、`package-release.sh`、`audit-hooks.sh --check-source-mirror`、`docs/dogfooding/`

### 与代码实现的差距
- 飞轮闭环依赖全部组件协同：发现→claude-next.md→knowledge-condenser→package-release→验证
- ED-01的移除（error-dna auto-fix/build-validator）需确认是否已在代码中执行
- flywheel_analytics.py的分析能力取决于数据积累量

---

## Story-13: 错误炼金术士 — 从失败中提炼黄金

**副标题**: Error-DNA v1→v3范式跃迁 | 弧2-防御

### 核心机制/概念

**Error-DNA演进**:
- v1: 被动收集所有exit_code≠0 → 8401条记录，83.5%噪声（gate正常阻断被当作错误）
- v2: 打磨铅块
- v3(ED-R驱动): **不再收集失败，检测逃逸** → exit_code=0的危险操作才是黄金

**四大逃逸模式**:

| 模式 | 描述 | 检测逻辑 |
|------|------|---------|
| E1 | 治理文件绕过 | Bash sed -i/tee/> 修改harness.yaml等(绕过pretool-sensitive-edit的Edit\|Write matcher) |
| E2 | 验证码伪造 | Bash echo CODE > .omc/state/sensitive-approved(绕过CAPTCHA) |
| E3 | 上下文规避 | context-guard阻断后启动Task subagent(独立context窗口) |
| E4 | 证据编造 | Bash echo VERIFIED > evidence.md(无实际验证命令) |

**辅助机制**:
- error_classifier.py: 签名提取+热点标记
- posttool-bash-audit: 双事件兼容(PostToolUse+PostToolUseFailure)
- pretool-retry-check: 内置重试追踪(替代已移除的retry-budget.sh)
- stop-drain: Stop hook时扫描transcript.jsonl做最后防线

### 关键创新点
- **"机场安检"类比**: 拦住带刀的人=系统正常工作；带刀上飞机=逃逸=黄金
- **范式跃迁**: exit_code≠0→exit_code=0，从收集失败到检测成功绕过
- **炼金术士约束**: 检测不阻断(防self-DoS)、不自动打补丁(防AI批准安全加固)、注入工作记忆(行为约束)
- **ED-01案例**: 揭示了被动收集的噪声问题

### 具体文件/路径
- `error-dna.sh`、`error-dna.jsonl`、`error_classifier.py`、`posttool-bash-audit.sh`、`pretool-retry-check.sh`、`stop-drain`、`transcript.jsonl`、`.omc/state/retry-log/`

### 与代码实现的差距
- Error-DNA v3的逃逸检测逻辑需要确认是否已完全实现
- E3(上下文规避)需要posttool-bash-audit的时序分析——多hook协作复杂度高
- stop-drain作为最后防线，在transcript.jsonl不可用时的fallback待确认

---

## Story-14: 工坊变迁录 — 圣器的兴与废

**副标题**: 18件活跃+8件消逝 | 弧4-工程

### 核心机制/概念

**四大工坊，18件活跃圣器**:

| 工坊 | 圣器 | 职责 |
|------|------|------|
| 代码审查 | lx-code-review | 8类39条规则，语言无关 |
| 测试 | lx-test-gen | 多语言自动检测路由 |
| 任务(四级链) | lx-todo→lx-task-spec→lx-rpe→lx-stepwise | 轻→重渐进升级 |
| 运维 | lx-pre-commit, lx-pre-push, lx-status, lx-varlock | 门禁、监控、隐私代理 |

**8件消逝圣器**（均被进化吸收）:
- lx-security-review → 被lx-code-review吸收
- lx-golang-test → 被lx-test-gen吸收
- lx-prd → 移出工坊(项目层面，非AI治理)
- lx-react-review, lx-web-perf, lx-browser-verify, lx-tdd-spec, lx-debug-spec → 融入通用工具或降级

**新生代(6件淬火中)**:
- lx-dogfood, lx-root-cause-analysis, lx-skillify, lx-learner, lx-sync, update-carror-os

### 关键创新点
- **永不为增长而增长**: 每件圣器背后有具体且重复的伤口
- **机制采纳门禁三问**: 建造新圣器前的必经检验
- **进化吸收**: script→hook→skill，专项→通用路由项
- **lx-rpe**: 9步闭环，产出四份文档(design/spec/executor/qa)
- **lx-varlock**: 隐私脱敏代理——AI"看不见"而非"不要看"

### 具体文件/路径
- `lx-code-review`、`lx-test-gen`、`lx-todo`、`lx-task-spec`、`lx-rpe`、`lx-stepwise`、`lx-pre-commit`、`lx-pre-push`、`lx-status`、`lx-varlock`、`lx-dogfood`、`lx-root-cause-analysis`、`lx-skillify`、`lx-learner`、`lx-sync`、`update-carror-os`

### 与代码实现的差距
- 18件活跃圣器的完整实现状态需要逐一验证
- 消逝圣器的残留代码是否已清理
- lx-dogfood等新生代skill的成熟度各异

---

## Story-15: 元环：蛇吞己尾

**副标题**: Ouroboros — 自噬的悖论 | 弧6-元环

### 核心机制/概念

**Ouroboros隐喻**: Carror OS既是开发工具也是被开发的项目
- 蛇吞己尾 = 用自己开发自己、用自己治理自己

**AGENTS.md双重存在**:
- 根级 AGENTS.md: 元项目治理(含狗粮协议、跨域变更、发布流程)
- source/harness-kit/AGENTS.md: 通用分发模板(不含元项目特有指令)
- **有意不同，不同步** — audit-hooks --check-source-mirror 排除AGENTS.md

**狗粮反馈循环协议(6步)**:
```
发现问题 → triage决策树 → 修复(root或source/+同步) → 机制化(gate/hook/验证)
→ 同步(package-release.sh) → 验证(harness-smoke-test+audit-hooks) → 记录(claude-next.md)
```

**Release流程(蛇蜕皮)**:
1. 更新VERSION.json
2. package-release.sh: root→source/harness-kit/ + source/lx-skills-v5/ + 构建.tar.gz
3. 验证: audit-hooks.sh → harness-smoke-test.sh

**五项元教训(META)**:
| 编号 | 教训 |
|------|------|
| META-01 | 原始记录太大(2626行)→需摘要头(≤50行)+原始附录 |
| META-02 | 跨会话狗粮需恢复完整上下文(~60KB)→自标记requires_context |
| META-03 | ~20发现仅5个系统通用→应用性三问筛选 |
| META-04 | 狗粮优化→级联同步义务→package-release.sh自动同步 |
| META-05 | YAML记录需source_ref字段→改用.md+[source: path:line] |

### 关键创新点
- **自噬悖论的解答**: 不能用自己有bug的工具修自己的bug → 三重门/Oracle/Meta-Oracle做交叉验证
- **外部信号打破封闭循环**: 用户纠正("不对")是飞轮燃料而非障碍
- **越开发越困难也越安全**: 每次修改后Carror OS对未来修改变得更严格
- **ED-R的元隐喻**: 系统最初收集失败，后来意识到逃逸才是最有价值的

### 具体文件/路径
- `AGENTS.md`(根级)、`source/harness-kit/AGENTS.md`、`package-release.sh`、`VERSION.json`、`audit-hooks.sh --check-source-mirror`

### 与代码实现的差距
- source mirror同步纪律需要在每次发布严格执行
- META系列教训已记录但部分改进可能尚未完成
- 根级vs source AGENTS.md的差异维护需要持续关注

---

## Story-16: 双生判官 — 从环境中长出来的审判者

**副标题**: Oracle与Meta-Oracle的涌现 | 弧5-审判

### 核心机制/概念

**Oracle的生长三因**:
```
哲学#6 (0信任) → 必须有人独立审查
哲学#4 (没验证=没做) → 审查必须有物理证据
OMC/OMO Agent能力 → 有独立进程+critic模型
        ↓ 碰撞
    Oracle 涌现
```

**Oracle职责**: spawn独立进程，不看AI预测，只看物理证据(文件/exit code/sha256)，裁决三词: ACCEPT/REVISE/REJECT

**Meta-Oracle的生长**: "Oracle也是AI" → 0信任的逻辑推到头 → 长出更高级审判者

**Meta-Oracle四触发(G1-G4)** 与story-11一致，强调: **Oracle最可能漏掉的时刻**

**软门禁设计**:
- Meta-Oracle的裁决是ADVISORY/REJECT，AI可在书面理由下覆写
- 原因: Meta-Oracle以上没有更高审判者 → 自知不是神
- 连续两次REJECT → 升级为事实阻断，必须人工介入

### 关键创新点
- **环境生长≠设计**: 五天涌现两个大法官——从哲学+物理证据+Agent能力三条件自然长出
- **审判官也需要被审判**: 0信任的逻辑必须贯彻到底
- **Oracle有效率天花板**: REJECT/REVISE时已在深度审查，Meta-Oracle只在Oracle给高分时(Accept+≥8.5)才有增量价值
- **"概念→协议→机制→工具→文件"的完整涌现链**

### 具体文件/路径
- `oracle-verdicts.md`、`auto-score.sh`、OMC/OMO Agent能力

### 与代码实现的差距
- Oracle/Meta-Oracle依赖OMC/OMO的Agent(critic)能力，需要该平台支持
- auto-score.sh 的静态检查方法论可能虚高（story中已知）
- Meta-Oracle的软门禁覆写机制需要明确书面记录格式

---

## Story-17: 开眼仪式 — 七柱圣殿的感官觉醒

**副标题**: LSP火眼金睛 | 弧7-感官

### 核心机制/概念

**盲眼巨人困境**: Carror OS拦得住明刀明枪(`rm -rf`/`sudo`)，但分不清人和妖
- 门禁能拦住危险操作——拦不住语义错误
- 裁判庭识破"应该没问题了"——识不破类型不匹配的代码修改

**三层画皮**:
| 层次 | 描述 | 例子 |
|------|------|------|
| 皮囊 | 语法合法，看起来正常 | `user.save()` 仍能grep到但已废弃 |
| 血肉 | 引用关系看起来对 | `def process(data, timeout=30)` 加了默认值但12个调用点需显式传 |
| 白骨 | 类型不匹配/签名断裂 | `calculate_score` 从int→float，23个赋值点类型不匹配 |

**LSP — 火眼金睛**:
- grep看文本("这行有User")，LSP看语义("这个User是实例化/注解/还是注释?")
- `goToDefinition`、`findReferences`、`getDiagnostics` — 50ms穿透三层皮囊

**三平台眼睛睁开方式**:

| 平台 | 方式 |
|------|------|
| Claude Code | `/plugin install pyright-lsp` |
| OpenCode | `opencode.json: {"lsp": true}` |
| Codex CLI | `pip install serena-agent` |

**Carror OS的LSP三件套**:
1. `ecosystem-probe.sh`: SessionStart检测平台+提示安装LSP
2. `lsp-suggest.sh`: 提醒AI用LSP而非grep
3. `pre-edit-lsp-check.sh`: 编辑前提示检查diagnostics（exit 0，不阻断，只提醒）

### 关键创新点
- **管行为 vs 管认知**: 七柱管行为，LSP管认知——"妖魔鬼怪，一眼便知"
- **借眼而非造眼**: 不造LSP，接入已有LSP生态
- **因果长成**: 从"grep 2347行垃圾"→"VS Code怎么知道类型?"→"LSP"→"Claude Code原生支持"→"探针提醒"→"编辑前检查"
- **门禁从事故中长出，眼睛从盲区中烧出来**

### 具体文件/路径
- `ecosystem-probe.sh`、`lsp-suggest.sh`、`pre-edit-lsp-check.sh`、`docs/guides/cn/lsp-setup.md`

### 与代码实现的差距
- LSP探针和检查机制需要对应hook实现
- 三平台兼容性需要维护更新（新版本Claude Code/OpenCode/Codex CLI的行为变化）
- LSP diagnostics全绿作为证据链一部分尚未完全集成到证据裁判庭

---

## Story-18: 脱水术 — 枯萎大树的终极馈赠

**副标题**: Token税与枯叶术 | 弧3-记忆

### 核心机制/概念

**恶魔(=Token税)困境**: 每个SessionStart注入26,600 tokens知识 → 每月成本¥3,274.50

**枯叶术(=脱水术)**:
- 源文件不动（人仍需读完整版）
- 在SessionStart注入前将知识"脱水"为压缩版
- **四片枯叶**:

| 枯叶 | 原版 | 脱水后 | 压缩比 |
|------|------|--------|--------|
| 铁律脉络 | 142行 | 22行金网 | ~85% |
| 反模式骨架 | 14类详解 | 12行因果链("A→假完成：无证据说完成") | ~90% |
| 教训脊柱 | 19条R条目 | 10行压缩铭文("R22→空变量→${var:-default}") | ~90% |
| 内核金网 | 5.1KB | 1.3KB纯规则 | ~75% |

**效果**: 26,600 → 1,300 tokens (94.6%降幅)，bug率未升、commit质量未降、幻觉密度反而降低

**具体实现**:
- `context-cache.md`: 铁律速查压缩版
- `kernel-compact.md`: 架构铁律压缩版
- `anti-patterns-compact.md`: 反模式压缩版
- `compact-detect.sh`: 5.1KB→3.3KB，去掉"善意的唠叨"

**Oracle+Meta-Oracle双重审查**:
- Oracle: 逐条对比原版与枯叶，确认语义无损
- Meta-Oracle: 三源一致性验证(磁盘compact文件+harness.yaml开关+settings.json注册)+对抗性审查(泡水测试)

### 关键创新点
- **移花接木**: 在恶魔收税点门口换成枯叶，源文件保持完整
- **脉络完整、水份全空**: 只有因果箭头("什么→什么")，无解释/装饰/引言/结语
- **"恶魔要的是水，我们要的是命。给它水。我们自己——留脉络。"**
- **出生自带**: 脱水术写进install.sh最后一行，新精灵生来就会
- **悖论**: 留给AI的越少（只留脉络），幻觉密度反而越低——因为因果箭头锁死了幻觉路径

### 具体文件/路径
- `context-cache.md`、`kernel-compact.md`、`anti-patterns-compact.md`、`compact-detect.sh`、`install.sh`

### 与代码实现的差距
- 压缩版文件(context-cache.md等)需要与源文件保持同步更新
- 三源一致性(Meta-Oracle验证)在脱水场景下需要专门实现
- compact-detect的"去唠叨"改进需要确认已实施
- 26,600→1,300的压缩效果取决于当前上下文注入的实际大小

---

## 跨篇核心主题汇总

### 因果基座（贯穿全部19篇）
- 核心公式: `犯错 → 记录教训 → 长出防御 → 验证有效 → 固化铁律`
- 不设计环境，只生长环境 — 每个机制背后都有具体的灾难
- 物化: claude-next.md的R/DG/DF/GL/ED/META系列条目

### 三源一致性（贯穿防御/审判弧）
- 生成源(代码) + 静态源(配置) + 运行时源(日志)
- audit-hooks.sh --check-source-mirror验证

### 狗粮模式（贯穿元环弧）
- AI用Carror OS开发Carror OS → 框架被框架自己治理
- triage决策树 → 修复 → 机制化 → 同步 → 验证 → 记录

### 哲学优先级锁链
```
#4(验证) > #6(0信任) > #3(守护) > #7(文档) > #5(人) > #2(增益) > #1(less)
```

### 关键文件/路径总览
| 分类 | 文件 |
|------|------|
| 铁律定义 | `.claude/index.md`, `AGENTS.md` |
| 教训库 | `claude-next.md`, `anti-patterns.md` |
| 架构内核 | `kernel.md`, `kernel-compact.md` |
| Hook配置 | `harness.yaml`, `settings.json` |
| Hook脚本 | `.claude/hooks/*.sh` |
| Skills | `.claude/skills/lx-*/` |
| Nodes | `.claude/nodes/*.md` |
| 记忆系统 | `error-dna.jsonl`, `session-handoff.md`, `flywheel.log` |
| 发布流水线 | `scripts/package-release.sh`, `VERSION.json` |
| Source Mirror | `source/harness-kit/`, `source/lx-skills-v5/`, `packages/` |
