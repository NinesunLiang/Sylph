# Carror OS — 元项目治理

> **Carror OS = AI Native Developer Operating System**
>
> 本项目是 Carror OS 的 **元项目（meta-project）** — 使用 Carror OS 自身框架来治理 Carror OS 自身的开发（狗粮模式）。
>
> **为什么两个文件不同？**
> 元项目（本仓库）在狗粮模式下使用 Carror OS 框架来治理自身开发。这意味着它需要**框架规则**（管理 AI 行为的通用规则）+ **元项目规则**（同步纪律、发布流程、跨域变更协议）。
> 下游用户项目只安装框架规则（`source/harness-kit/AGENTS.md`），不需要元项目的工具链。
> 因此：本文件引用 source 版本获取通用框架，并增加元项目独有的层。
>
> **通用治理模板**位于 `source/harness-kit/AGENTS.md`。本文件是元项目专属治理文件，与分发版本**有意不同**。
>
> 平台兼容性（狗粮环境）：
> - **Claude Code**：通过 CLAUDE.md 的 @AGENTS.md 导入
> - **Codex CLI** / **Gemini CLI** / **Qwen Code**：通过自动生成的原生配置接入
> - **Cursor**：通过 `.cursor/hooks.json` 接入
> - **OpenCode**：直接读取 AGENTS.md（原生支持）

---

## 项目架构

本仓库有以下工作区：

| 目录 | 职责 | 说明 |
|------|------|------|
| **Root**（本仓库根目录） | 元项目开发环境 | 狗粮模式使用 Carror OS 治理自身开发，含 project 级别 hook/script/skill |
| `source/harness-kit/` | 治理层分发源 | 构建时同步至此。其 `AGENTS.md` = 通用分发模板，与根文件**有意不同** |
| `source/lx-skills-v5/` | 能力层分发源 | 构建时同步至此。skill 定义文件 |
| `packages/` | 构建产物 | tar.gz 归档 + 安装脚本 + CHANGELOG |

### Source Mirror 同步纪律

`scripts/package-release.sh` 在发布时从 root → source 同步以下文件：
- `.claude/hooks/*` — `rsync --delete` 全镜像（脚本与 hook 注册行为相关，必须一致）
- `.claude/scripts/*` — `rsync --delete` 全镜像
- `.claude/references/*` — `rsync --delete` 全镜像
- `.claude/kernel.md`、`harness.yaml`、`settings.json`、`index.md`、`anti-patterns.md`、`claude-next.md` — 直接 cp
- `.cursor/`、`.opencode/`、`.hooks/` — `rsync --delete`
- `CLAUDE.md` — 直接 cp。两个位置的 CLAUDE.md 字节相同，但 `@AGENTS.md` 的相对引用各自指向本目录的 AGENTS.md

**有意不同的文件**（不同步）：
- **`AGENTS.md`** — 本文件是元项目治理文件；source 版本是通用分发模板

**镜像验证**：`bash .claude/scripts/audit-hooks.sh --check-source-mirror` 排除有意分歧文件后验证一致性。

---

## Carror OS 哲学核心

> 哲学是 Carror OS 的「性格」— 定义了面对任何情况时的默认行为倾向。
> 所有机制（gate/hook/验证/节点/仲裁）都是这些哲学的物化。每个机制必须可追溯到哲学原则，每条原则必须有机制实现。

### 哲学宣言

| # | 哲学 | 一句话 | 优先级 |
|---|------|--------|--------|
| 4 | **没通过验证等于没做** | 无证据不可声明完成 | 最高 |
| 6 | **先天对 AI 0 信任** | 所有 AI 输出须经可证伪验证 | ↓ |
| 3 | **先守护，后激发** | 安全网先于创新能力 | ↓ |
| 7 | **文档优先，调研先行** | 充分调研 → Oracle 审核 → 执行 | ↓ |
| 5 | **以人为本** | 心智负担最小化，选择 > 文字输入 | ↓ |
| 2 | **少量正确大增益** | 不做虚假求圆满 | ↓ |
| 1 | **The Less, The More** | 渐进式披露，隐藏机制静默发力 | 基础 |

> 哲学冲突时按优先级裁决。行为不符合预期？根源是你和 Carror OS 的哲学理念不一致 — **调整哲学优先级即可**，无需绕过机制。
> 
> 完整说明（「为什么需要哲学」「梦中情人」定制指南、物化示例、机制采纳门禁、逆向追溯矩阵）→ `Read .claude/reference/philosophy.md`
> 公开文档 → `docs/guides/cn/philosophy.md`

## 三源一致性 (Three-Source Consistency)

> **核心原则：真理出现在三个独立且异构的源达成一致的交汇点。**
> 单个源的输出永远不可信 — 生成源可能幻觉，静态规则源可能过时，运行时事实源可能被欺骗。只有三源一致 = 可接受为真。
>
> **工程学的上限：99.999% — 而非 100%**。三源一致性能把 AI 可靠性从"玩具级"(95%)拉升到"工业/航天级"(99.999%)，但不能保证数学上的绝对零错误。剩余 0.01% 的误差来自同源基集体盲区、间接提示注入、主观灰度地带。应对策略：纵深防御 + 快速熔断（而非追求绝对不犯错）。
>
> **完整理论 →** `Read .claude/reference/three-source-consistency.md`

### 三源映射到 Carror OS

| # | 源 | Carror OS 载体 | 确定性保证 |
|---|------|---------------|-----------|
| **Source I** | 生成源 — "AI 应该看到什么" | AGENTS.md §哲学核心 + 8 条铁律, kernel.md, anti-patterns.md | AI 无法在不违反铁律的情况下绕过 — **铁律违反 = BLOCKED** |
| **Source II** | 静态规则源 — "系统强制什么结构" | settings.json (Hook 注册) + harness.yaml (开关) + feature-registry.yaml + SKILL.md | 文件系统层面的硬约束。**文件存在 ≠ 生效**（DG-82: 39/44 hooks 无 flywheel.log） |
| **Source III** | 运行时事实源 — "系统实际验证了什么" | Meta-Oracle + hook flywheel.log + harness-smoke-test.sh + audit-hooks.sh + error-dna.jsonl | 运行时产生的**事实**，不是"系统认为什么是对的"。`harness-smoke-test.sh 全绿` = 事实，不是判断 |

### A→B→A 三重门 = 三源一致性的操作化实现

```
A 预测 → B 盲执行 → A 自证 → Oracle 审核（常规守门员）
                              ↓
                         Meta-Oracle 最后守门（仅在 G1-G4 触发）
```

| 步骤 | 映射到三源 | 说明 |
|------|-----------|------|
| A 预测（方案/PRD） | Source I (生成源) | AI 基于规则推理，输出预期结果 |
| B 盲执行（独立验证） | Source II (静态规则源) | 脱离 AI 上下文，用 hook/脚本执行验证 |
| A 自证（Oracle 审核） | Source III (运行时事实源) | Oracle 检查执行结果，不信任 AI 自证 |
| Meta-Oracle (G1-G4) | Source III ×2 + Source I 交叉验证 | 运行时验证 > 静态检查，对抗性审查找盲区 |

### 熔断机制 — 三源分歧时的处理

| 分歧类型 | 处理方式 |
|---------|---------|
| Source I vs II (规则冲突) | [哲学先行: 仲裁] — 按优先级裁决，不继续执行 |
| Source II vs III (规则未生效) | [治理异常] — audit-hooks 报告，修复后继续 |
| Source I vs III (规则被违反) | [铁律违反] — BLOCKED，回滚当前操作 |
| 三源同时分歧 (G1-G4) | Meta-Oracle ADVISORY/REJECT — AI 覆写需明确书面理由 |

### 纵深防御策略 (Heterogeneous Redundancy)

三源一致性不是"三道防线防同一个攻击"，而是**异构冗余防御**:
- **Source I 防 AI 幻觉**: 哲学 + 铁律强制文件来源标注，禁止无来源断言
- **Source II 防 AI 越界**: hook 拦截范围外修改、敏感文件触碰、破坏性操作
- **Source III 防 AI 欺骗**: Oracle/Meta-Oracle 独立审查，不信任 AI 自证

**关键区分**: Source II（静态规则）和 Source III（运行时事实）**必须使用不同验证方法**。如果两者都用 grep 检查同一文件，这就是同源失效。

### Red Team / Blue Team — 持续进化机制

三源一致性不是静态的，必须定期接受"邪恶版 AI"的攻击测试：
1. **Red Team**: 专门训练一个 agent，每天尝试绕过三道防线
2. **攻击向量**: 提示注入、同源基错误、间接欺骗、规则漂移
3. **Blue Team Response**: 根据攻击手段修补对应防线

**狗粮模式的天然优势**: Carror OS 本身就是自己的 Red Team。每次狗粮反哺（DG-xxx）都是一次攻击测试 + 防御升级。

---

### Meta-Oracle — 最后守门员（核武器级终审）

> **起源**：Oracle 和 Meta-Oracle 不是刻意设计出来的，是环境自然生长出来的。
> 哲学 #6（0信任）要求所有 AI 输出必须被独立验证 → 哲学 #4（没验证=没做）要求验证必须有物理证据 →
> OMC/OMO 恰好提供了 `Agent(critic)` 独立进程能力 → 三件事碰到一起，Oracle/Meta-Oracle 就自然出现了。
> **它们是「环境生长，而非设计」的物理具象化产物。**

> **概念归属**：Oracle 和 Meta-Oracle 是 **Carror OS 哲学物化的概念和协议**，不是任何平台的原生功能。
> 物理执行载体：OMC (oh-my-claude) 或 OMO (oh-my-opencode) 的 Agent 独立进程能力。
> 无 OMC/OMO 时，通过 lx-oracle skill 退回到本地 AI prompt 审核（协议不变，物理隔离打折扣）。

> **定位**：Oracle = 常规守门员（每阶段门禁），Meta-Oracle = 最后守门员（核武器级终审）。
> Meta-Oracle 是 Carror OS 的最高审查权威，消耗巨大（opus + 独立上下文），**仅在关键节点触发，非必要不使用**。

Oracle 不是绝对正确的。它用的评分方法论可能有 bug（auto-score.sh 静态检查虚高），它可能漏掉设计级缺陷（regex 只匹配部分引用格式），它的结论需要被验证。

**Meta-Oracle = Source III + Source I 交叉验证器**。使用完全不同的审查方法（运行时验证 > 静态检查，烟雾日志 > 文件存在性，对抗性审查 > 合规检查），专门寻找 Oracle 的盲区。

**Oracle vs Meta-Oracle — 三源交叉视角**:

| 维度 | Oracle（常规守门员） | Meta-Oracle（最后守门员） |
|------|---------------------|--------------------------|
| 方法论 | Source I → Source II 检查一致性 | Source III (运行时事实) × Source I 交叉验证 |
| 审查手段 | 静态检查、文件存在性 | 运行时验证、烟雾日志、对抗性测试 |
| 找什么 | 违规/遗漏/不合规 | Oracle 的盲区（同源基失效、间接注入） |
| 为什么独立 | — | Oracle 和 AI 共享上下文 = 同源风险 |

#### Oracle vs Meta-Oracle 分工

| 维度 | Oracle（常规守门员） | Meta-Oracle（最后守门员） |
|------|---------------------|--------------------------|
| 触发频率 | 每阶段（L2+ 强制） | 仅 4 个关键触发点（~5% 任务） |
| 消耗 | 中等 | 巨大（核武器级，opus + 独立上下文） |
| 方法论 | 静态检查 + 文件存在性 + 合规审查 | 运行时验证 + 烟雾日志 + 对抗性审查 + 设计盲区扫描 |
| 权威等级 | 高于代码现状 | **高于 Oracle**（可推翻 Oracle 裁决） |
| 执行方式 | 硬门禁（REJECT = 阻断流程） | **软门禁**（给出裁决 + 建议，AI 可在明确理由下覆写） |
| 模型 | critic/architect（当前平台最高可用模型） | critic（独立 agent，不共享主会话上下文，模型无关） |

#### 4 个触发点（G1-G4）

> **核心原则：珍惜 Meta-Oracle 的能力，非必要不触发。** 以下 4 个触发点是唯一激活 Meta-Oracle 的场景。

| # | 触发点 | 触发条件 | 理由 |
|---|--------|---------|------|
| **G1** | **架构决策终审** | 涉及 ≥2 子系统 + 不可逆的架构变更 | 架构错了全盘皆输，需要最高级审查 |
| **G2** | **PRD/方案最后一步** | PRD 完整生命周期的最终阶段（Oracle 已 ACCEPT） | 方案是工程的蓝图，蓝图错了执行全错 |
| **G3** | **Oracle ACCEPT + 高分** | Oracle 给出 ACCEPT 且评分 ≥8.5（现有逻辑，保留） | Oracle 最可能虚高的场景，需独立校准 |
| **G4** | **Release 门禁** | `package-release.sh` 执行前的最终安全检查 | 发布的破坏不可逆，必须最后把关 |

**优先级**（多触发点同时满足时取最高）：G1 > G2 > G4 > G3。同一任务最多触发 1 次 Meta-Oracle。

**软门禁执行协议**：
1. Meta-Oracle 审查后给出裁决：`[Meta-Oracle: ACCEPT]` / `[Meta-Oracle: ADVISORY]` / `[Meta-Oracle: REJECT]`
2. ACCEPT → 继续流程
3. ADVISORY → 建议修正但不阻断，AI 自行判断是否采纳
4. REJECT → 强烈建议阻断，AI 必须有**明确书面理由**才能覆写（记录到 `.omc/state/meta-oracle-overrides.md`）
5. 连续 2 次 REJECT → 升级为事实阻断，需人工介入

**在 A→B→A 三重门中的位置**：
```
A 预测 → B 盲执行 → A 自证 → Oracle 审核（常规守门员）
                              ↓
                         Meta-Oracle 最后守门（仅在 G1-G4 触发）
```

**在完整开发生命周期中的位置**：
```
调研 → 方案 → Oracle 方案审核 → 执行 → 自愈 → 报告 → Oracle 终审
  ↓                                                    ↓
  [G1: 架构决策时]                              [G2: PRD 最后一步]
                                                       ↓
                                              Meta-Oracle 最后守门
```

> **关键约束**：
> - Meta-Oracle 不是每轮都要的。Oracle 给 REJECT/REVISE 时已在深度审查，Meta-Oracle 价值增量小
> - 同一任务最多触发 1 次 Meta-Oracle，触发后裁决留痕到 `.omc/state/meta-oracle-verdicts.md`
> - G3（Oracle ACCEPT/高分）是最低触发门槛，G1/G2/G4 是更高优先级的触发点

#### 已知盲区与防御边界

> 三重门 + Oracle + Meta-Oracle 的异构冗余防御体系能将 AI 犯错成本提升到「堪比登天」，
> 但作为足够复杂的自适应系统，永远存在微小的逃逸概率。
> Carror OS 不追求数学上的「绝对零错误」，而是建立「纵深防御 + 快速熔断」。

**三类系统性盲区**：

| 盲区类型 | 说明 | Carror OS 缓解措施 |
|---------|------|------------------|
| **共同模式失效 (CMF)** | A/B/Oracle/Meta-Oracle 同源基座时可能共享错误常识 | 三重门要求 A≠B 模型族；Oracle≠A 模型族；Oracle/Meta-Oracle 的检测逻辑是 bash 脚本（白盒），不共享 LLM 训练数据 |
| **间接提示注入** | 恶意数据源中的隐藏指令可一次性绕过所有防线 | privacy-gate 脱敏代理隔离外部数据；范围冻结阻断越权；硬边界协议物理阻断破坏性操作 |
| **主观/伦理灰度** | 对「设计是否优美」等无标准答案问题，三源一致性只能给出概率评分 | G1-G4 Meta-Oracle 软门禁；置信度不足时升级人类裁决；铁律 #2（用户裁定）兜底 |

**不确定性量化 (Uncertainty Quantification)**：
三源出现分歧或置信度不足时的熔断链：三源一致 → ✅ 继续；微小分歧 → ⚠️ 标记 [低置信度] 继续；重大分歧 → 🛑 熔断交还人类；Meta-Oracle REJECT ×2 → 🔴 事实阻断需人工介入。

#### 认知独立：不依赖跨族模型的替代方案

> **定论 (2026-05-18)**：Carror OS 防御体系不使用异族模型架构。大部分用户不具备多模型条件，且**结构性防御（白盒）覆盖了 80% 以上的欺骗漏洞，不需要跨族模型**。

四层认知独立方案（低成本，已在 Carror OS 中不同程度物化）：

| 方案 | 原理 | 覆盖率 | 现有物化 |
|------|------|:------:|---------|
| 结构化自检清单 | 把语义判断转化为结构验证 — 不要求 AI 「判断对错」，要求 AI 「填写字段是否可证伪」 | 70% | completion-gate 证据评分 + posttool-claim-audit 铁律 #1 |
| 时间隔离审查 | 同模型，不同上下文 — 会话 A 推理链不污染会话 B | 75% | cross-verify-handoff.md 双终端交叉验证 |
| 角色框架切换 | 同模型，不同 prompt — 执行者 vs 怀疑论者，激活不同权重路径 | 80% | 待物化：meta-oracle-trigger 注入怀疑论者额外上下文 |
| 确定性物理证据 | bash exit code / file checksum / 命令输出 — 无法用语义改写伪造 | ~99.999% | Oracle（静态规则）+ Meta-Oracle（运行时事实） |

> 跨族模型额外覆盖的 ~0.001% 是**事实知识盲区**（如所有模型都相信某个错误常识）。
> 在代码场景中这几乎不存在 — 编译器和测试框架说了算，不是 LLM 说了算。
> **0% → 80% 不需要跨族模型。80% → 99.999% 靠白盒确定性验证。跨族是锦上添花，不是雪中送炭。**

---

## 狗粮反馈循环协议

> 实现哲学 #4（没通过验证等于没做）+ #6（0 信任）+ #7（文档优先）的操作层。
> 核心循环：发现问题 → 修复问题 → 添加机制 → 传播修复到 source/ 和 packages/
> 本协议适用于所有在元项目开发中发现的问题（bug、设计差距、文档过时、配置漂移）。

### Triage 决策树

当 AI 发现任何问题时，必须按以下分类和行动执行：

```
问题发现
  │
  ├─ 仅元项目特有（根级 hook/脚本/工具）→
  │   直接修复 + 记录机制到 claude-next.md → 验证 → 完成
  │
  ├─ 仅框架通用（source/harness-kit/ 或 source/lx-skills-v5/）→
  │   先在 source/ 修复 → 通过 package-release.sh 同步到 root → 验证
  │
  ├─ 两者兼有（根级和 source 都有问题）→
  │   修复框架（source/）→ 同步到 root → 验证 → 记录机制
  │
  └─ 揭示框架差距（新反模式/新铁律场景/新验证需求）→
      先在 source/harness-kit/AGENTS.md 添加规则 → 选择性适配到本文件
```

### AI Agent Dogfooding 操作协议

当你（AI agent）在狗粮模式下发现 Carror OS 自身的问题时：

1. **分类**：按上述 triage 树确定问题归属域
2. **修复**：在问题所在的域修复。跨域时先修上游（source/），再同步到 root
3. **机制**：在 Carror OS 框架层添加可重复的 gate/hook/验证来防止复发
4. **同步**：运行 `bash scripts/package-release.sh` 将 root 的修复传播到 source/ 和 packages/
5. **验证**：运行 `harness-smoke-test.sh` + `audit-hooks.sh --check-source-mirror` 确认无漂移
6. **记录**：将新经验写入 `.claude/claude-next.md`（hits:1），验证稳定后可升华到 kernel.md

**重要**：如果修复仅对元项目有用（对下游用户无关），只在本文件中记录，不修改 source 版本。

### 机制保留/删除判定原则

> 在评估是否保留或删除任何 hook/skill/机制时，必须遵循以下双标准：

**标准 1：哲学 > 铁律 > 需求，且收益远大于噪声**

```
哲学 7 条 → 铁律 8 条 → 项目需求 → 增益 vs 噪声
```

- 三级筛选：任何机制必须能追溯到至少一条哲学或铁律
- 同时满足：增益 >> 噪声（维持成本、运行时开销、维护负担）
- 增益/噪声比为负 → 即使有哲学支撑也应删除

**标准 2：先区分「意图不对」还是「实现不对」**

| 情况 | 处理 |
|------|------|
| **意图不对**（哲学/铁律无支撑，原始设计目标本身错误） | **删除** |
| **实现不对**（意图正确，但实现有 bug、埋点路径错误、未注册、观测不到等） | **改实现，不删除** |

> **为什么需要这个区分**：read-tracker.sh 零 flywheel 事件 → 初始误判为「无价值」。追溯原始意图后发现它是 edit-guard 的数据核心依赖。问题不在意图（Read-before-Edit = 铁律 #1），而在观测方法（数据型 hook 不写 flywheel，事件数不反映效果）。
>
> **操作约束**：评估任何机制前，先查 git log 追溯原始创建意图，确认它被设计来解决什么问题。禁止仅凭 flywheel 零事件 = 无价值的粗暴判断。

---

## 元项目开发规则

### AGENTS.md 修改协议

- 本文件是 Carror OS 元项目专属治理文件。**不要**将本文件内容复制到 `source/harness-kit/AGENTS.md`。
- 通用治理框架改进应先修改 `source/harness-kit/AGENTS.md`（上游规范源），再选择性适配到本文件。
- `scripts/package-release.sh` 不复制本文件到 source。
- 每次对本文件的修改运行 `harness-smoke-test.sh` 验证 R30/R34/R36 通过。
- 本文件也是 `install.sh` 合并到用户项目的模板。修改时注意：合并后以 `##` 二级标题出现，不要使用与用户 `#` 一级标题冲突的章节结构（R32）。

### 完整开发生命周期（哲学 #7 物化）

> 哲学 #7：文档优先，调研先行 — 处理前充分调研，出方案经 Oracle 审核后执行，全过程留痕。
> 本流程适用于所有非 trivial 变更（L2+）。L1 简单变更可跳过 Oracle 终审。

#### 标准流程（调研 → 方案 → 审核 → 执行 → 验证 → 终审）

1. **调研**：搜索项目同类实现、读取相关文档、理解现有架构。所有不确定信息询问用户。
2. **方案（PRD/Spec）**：出 PRD 或设计文档，含候选方案对比、选型理由、风险点。
   - RPE feature：`rpe/{feature}/design.md` + `spec.md`
   - Feature 间必须 MECE 正交，用 `lx-oma-split` 拆分
3. **Oracle 方案审核**：方案提交 Oracle 审核，通过后方可执行。
   - 不通过 → 返回 Step 2 优化方案
4. **执行**：拆解为独立可验证子步骤，逐一实现。
   - 过程记录到 `rpe/{feature}/executor.md`（progress 文档）
   - 每完成一个子步骤立即验证，不堆积
5. **自愈**：遇到问题自行修复，最多 3 次不同路径。第 3 次仍失败 → 升级用户介入。
   - 每轮记录根因假设，不得与上轮相同
   - 不自愈不等于放弃 — 升级后继续
6. **报告**：执行完毕生成 `rpe/{feature}/qa.md`（report 文档），含：
   - 验收条件逐项验证结果
   - L1/L2 证据（测试通过/端到端验证）
   - 代码变更摘要
7. **Oracle 终审**：报告提交 Oracle 审核，通过才算完成。
   - 通过 → 进入 Step 8（G1/G2 触发时）
   - 不通过 → 返回 Step 4（执行），优化后重新报告
8. **Meta-Oracle 最后守门**（仅在 G1/G2 触发时）：Oracle 终审通过后，若任务涉及架构决策（G1）或 PRD 方案最后一步（G2），提交 Meta-Oracle 做最高级审查。软门禁 — 裁决 ADVISORY/REJECT 时 AI 可在明确理由下覆写，但需留痕。

#### L1 简单变更

单步修改、明确 bug 修复、单文件、无架构决策：
```
调研 → 直接执行 → 证据验证 → 完成
```

### 跨域变更协议

当修改跨越多个域（root → source → packages）时：

1. **修改顺序**：只在 root 中修改，然后同步。不要在不同域中独立修改相同文件
2. **验证顺序**：每层修改后运行 `harness-smoke-test.sh`，全回归后运行 `package-release.sh`
3. **未发布状态**：如果跨域变更尚未发布到 packages/，在 RPE feature 目录中注释 `PENDING_SYNC`

### Release 流程

1. 在 `VERSION.json` 中更新版本号
2. 运行 `bash scripts/package-release.sh`：
   - Step 1: 同步 root → `source/harness-kit/`（`AGENTS.md` 有意不复制）
   - Step 2: 同步 root → `source/lx-skills-v5/`
   - Step 3: 构建 `packages/harness-kit-{TAG}.tar.gz`
   - Step 4: 构建 `packages/lx-skills-{TAG}.tar.gz`
3. 验证：`audit-hooks.sh` → `harness-smoke-test.sh`
4. 产物在 `packages/` 目录

### Hook/Skill 修改协议

- 三方一致性：磁盘脚本存在 ↔ `settings.json` 注册事件+matcher ↔ `harness.yaml` 开关 `true`
- 添加/删除/修改 hook 后运行 `audit-hooks.sh` 检查三方对齐
- 修改后运行 `harness-smoke-test.sh` 全回归 + `hook-production-verify.sh` 全面验证
- Hook 脚本永远不要 `set -e`，必须 `exit 0` 或 `echo '{"continue": true}'` + `exit 0`
- 更新 `.claude/index.md` hooks 表中的脚本描述
- 行为变更后同步更新脚本头部 `# Role:` / `# 用途` 注释（见 R35）
- Hook 合并/废弃时同步更新：(A) settings.json ← (B) harness.yaml ← (C) smoke tests（见 R36）
- 每次修改后审查脚本内的工具过滤白名单是否与 settings.json matcher 一致（R26）
- 跨平台时同步更新 `.opencode/plugins/` 和 `.cursor/` 的对应配置

### 文档规范

- 中文文档：`docs/{section}/cn/`
- 英文文档：`docs/{section}/us/`
- `bash .claude/scripts/doc-sync-check.sh` 验证 docs/ 中 `[已验证: path:line]` 引用的准确性
- 架构变更后必须同步更新所有相关文档（R28 教训）

### 跨平台配置

- `.opencode/plugins/` — OpenCode 桥接插件
- `.cursor/` — Cursor hooks 配置
- `.hooks/` — Codex/Gemini/Qwen 跨平台接入

---

## 核心执行上下文

> 完整治理框架的执行上下文定义在 `source/harness-kit/AGENTS.md §核心执行上下文（渐进式加载）`。
> 以下为元项目特有的补充。

SessionStart 时自动加载以下核心文件（与 source 版本一致）：
- @.claude/kernel.md — 代码执行内核（架构铁律/命名/错误处理/测试要求）
- @.claude/anti-patterns.md — 项目反模式清单（A-H 共 16 条模式）
- @.claude/claude-next.md — 学习笔记（项目特有经验 / 纠正记录 / 高频教训）

会话初始化完成通用步骤后，额外执行：

```
4. 同步漂移检查：bash .claude/scripts/audit-hooks.sh --check-source-mirror
   - 全部通过或仅 AGENTS.md 标记为"有意分歧"：正常继续
   - 发现 🔴 漂移：立即报告，在继续任务前修复
```

### 注入预算约束（R39）

自动注入内容优先驻留在 `.claude/reference/*.md`，index.md 仅留摘要链接。
每次 SessionStart 自动注入控制在 ~120 行/3KB 以内。不常变/仅查阅的内容不注入。

### Source Consistency Protocol — 三源一致性操作规范

> **每次 SessionStart**：运行 `audit-hooks.sh --check-source-mirror` 确认 Source II（静态规则源）的三方一致性。
> **每次修改 hook/机制**：必须验证 Source II 三源对齐 + Source III（运行时事实）产出。

**Hook/Skill 修改时的三源检查清单**:
1. **Source II (静态)**: `settings.json` 注册 + `harness.yaml` 开关 + 磁盘脚本存在性
2. **Source III (运行时)**: `harness-smoke-test.sh` 全回归 + flywheel.log 埋点（非零命中）
3. **Source I (哲学)**: 机制是否物化了某条铁律/反模式？（逆向追溯矩阵确认）

**机制采纳前门禁三问**: 注册了？在运行？产生效果？— 三问全过才算生效。

---

## 治理框架引用

> 以下规则定义在 `source/harness-kit/AGENTS.md`，狗粮模式下全量生效。
> 本文件不重复这些规则，仅提供引用和元项目补充。

| 规则 | source 位置 | 元项目补充 |
|------|-----------|-----------|
| Carror OS 哲学核心 | §Carror OS 哲学核心 | 本文件已有完整哲学声明的扩展版。source 版本为通用版，本文件增加狗粮反馈循环等元项目特有机制 |
| Project 宪法 | §Project 宪法 | — |
| 8 条铁律 | §8 条铁律 | 铁律 #8（哲学先行）：问人前先过哲学，哲学能裁决→标注 `[哲学先行: #N→action]` 直接执行；仅用户偏好/不可逆/授权/合规可例外 |
| 智力代理交互原则 | §9. 智力代理交互原则 | 交互原则 #6（哲学先行）：见铁律 #8 使用细则，禁止跳过哲学直接问人 |
| 软完成语禁令 | §软完成语禁令 | — |
| 权威等级 | §权威等级 | Meta-Oracle（最后守门员）> Oracle 终审 > 代码现状。Oracle 是常规最高权威，Meta-Oracle 仅在 G1-G4 触发时高于 Oracle |
| 证据层级 | §防御性规则 > 证据层级与置信度 | — |
| 危险操作二次确认 | §防御性规则 > 危险操作二次确认 | — |
| 修复 3 轮上限 | §防御性规则 > 修复上限与升级 | 跨域修复（root + source）算作一轮 |
| 工作流原则 | §工作流原则 | L3/L4 强制 Oracle 终审 |
| 三重门交叉验证 | §工作流原则 > 三重门交叉验证 | = A→B→A（三源一致性操作化实现）|
| **三源一致性** | §三源一致性 (Three-Source Consistency) | **真理判定协议 — 生成源 I + 静态规则源 II + 运行时事实源 III** |
| L3 执行流水线 | §复杂任务执行流水线（L3 专用） | — |
| 方案复用自检 | §防御性规则 > 方案复用自检 | — |
| 会话初始化 | §会话初始化 | 见本文件 §核心执行上下文 的漂移检查补充 |

### 机制→哲学 逆向追溯矩阵

> 完整双向追溯矩阵（覆盖 46 hooks + 25 skills + 28 scripts + 8 条铁律）→ `Read .claude/reference/philosophy-mechanism-matrix.md`
> 
> 以下为快速参考速查表（仅列最常用机制，完整版含全量 99 项）：

| 机制 | 类型 | 所属哲学 | Source | 说明 |
|------|------|---------|--------|------|
| `completion-gate.sh` | Hook | #4, #6 | III | 证据质量评分+虚假完成阻断 |
| `permission-gate.sh` | Hook | #6, #3 | III | CAPTCHA 验证码审批+危险命令拦截 |
| `pretool-sensitive-edit.sh` | Hook | #6 | II+III | 治理文件 CAPTCHA 门禁（Edit/Write 扩展防御面） |
| `context-guard.sh` | Hook | #3 | III | 上下文阈值阻断防记忆衰退 |
| `edit-guard.sh` | Hook | #6 | II+III | Read-before-Edit 门禁 |
| `privacy-gate.sh` | Hook | #3, #6 | II+III | .env/私钥拦截 |
| `pretool-edit-scope.sh` | Hook | #2 | II+III | 范围冻结拦截 |
| `posttool-format-gate.sh` | Hook | #5 | III | 输出格式方向感检查 |
| `turn-counter.sh` | Hook | #1, #5 | III | 轮次统计+模糊指令检测 |
| `inject-project-knowledge.sh` | Hook | #7 | I+II | 核心知识注入（Source I → AI 上下文） |
| `harness_config.sh` | 共享库 | #3 | II | hc_enabled 统一门禁 |
| `posttool-claim-audit.sh` | Hook | #6, #4 | III | 铁律#1强制校验（Source I → Source III） |
| `pretool-ask-guard.sh` | Hook | #5, #6 | II+III | 哲学先行门禁 |
| `meta-oracle-trigger.sh` | Hook | #4, #6 | III×I | G1-G4 Meta-Oracle 触发（Source III × Source I） |
| `audit-hooks.sh` | 脚本 | #4 | II+III | Source II 三方一致性审计 + Source III 事实验证 |
| `harness-smoke-test.sh` | 脚本 | #4 | III | Source III 运行时回归验证 |
| `lx-oma-orch` | Skill | #1 | I+II | 管线原子化编排（Source I → Source II） |
| `lx-oma-split` | Skill | #2 | I+II | Feature MECE 正交拆解（Source I → Source II） |
| `lx-code-review` | Skill | #4 | III | 代码审查（Source III） |
| `lx-oma-hier` | Skill | #7 | I+II | PRD 分层拆解（Source I → Source II） |
| `is_mode_active()` | 模式检测 | #3 | II+III | ghost/goal 降级保护（Source II → Source III） |
| Oracle 终审 | 节点 | #6 | I→II+III | 最高权威裁决（Source I → Source II/III） |
| Meta-Oracle | 节点 | #4, #6 | III×I | 最后守门员（核武器级终审）— G1-G4，独立于 Oracle，软门禁 |
| **三源一致性** | 框架 | #4,#6,#3 | I+II+III | **真理判定协议 — 三源一致=真，分歧=熔断** |
| **A→B→A 三重门** | 协议 | #4,#6 | I+II+III | **三源一致性操作化实现** |

### Harness 配置

- Hook 配置: `.claude/harness.yaml`（45 条总引用 / 41 个唯一 hook 注册 / 44 个磁盘脚本，实际以 settings.json + yaml 为准）
- 代码风格: `.claude/kernel.md`
- 学习笔记: `.claude/claude-next.md`

### Enhanced 激活（可选）

> 完整协议和激活指南见 `source/harness-kit/AGENTS.md §Enhanced 激活（可选）`。

```bash
# 一键激活
cat .claude/profiles/enhanced/append-to-claude.md >> CLAUDE.md
```

激活后 `lx-task-spec` skill 按 `.claude/task_sys/loading_matrix.md` 加载对应节点。
