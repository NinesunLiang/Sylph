# 三源一致性 (Three-Source Consistency)

> **核心原则：真理出现在三个独立且异构的源达成一致的交汇点。**
> 单个源的输出永远不可信 — 生成源可能幻觉，静态规则源可能过时，运行时事实源可能被欺骗。只有三源一致 = 可接受为真。

---

## 为什么需要三源一致性？

### AI 犯错的成本模型

普通 AI 系统中，AI 出错的成本极低 — 只需调整几个 token 的概率。在**三源架构**下，AI 要成功输出一段错误的代码/结论，它必须同时骗过三个独立防线：

1. **生成源**的确定性规则约束
2. **静态规则源**的结构/语法扫描
3. **运行时事实源**的外部验证

这就好比一个小偷不仅要 bypass 指纹锁，还要躲过红外线，最后还要伪造一段监控录像。在这种高压下：

> **说实话的算力成本 < 编造一个天衣无缝的谎言**

AI 会自然选择"说实话"这条路。

### 工程学的上限：99.999% — 而非 100%

三源一致性能把 AI 可靠性从"玩具级"(95%)拉升到"工业/航天级"(99.999%)，但**不能保证数学上的绝对零错误**。剩余 0.01% 的误差来自：

| # | 失效模式 | 描述 |
|---|---------|------|
| 1 | **同源基集体盲区** (Common Mode Failure) | 所有源基于相同底层模型/训练数据，共享同一个错误常识。Mate-Oracle 也会认为"运行结果符合预期"（因为预期本身就是错的）。 |
| 2 | **间接提示注入** (Indirect Prompt Injection) | AI 在处理的数据源里被植入隐藏指令，三道防线同时被"毒数据"绕过。 |
| 3 | **主观灰度地带** (Subjective Ambiguity) | 对于没有标准答案的问题（公关稿语气、设计美感），三源本身无法给出绝对对错。 |

**应对策略：纵深防御 + 快速熔断（而非追求绝对不犯错）。**

---

## Carror OS 的三源映射

### Source I：生成源 — "AI 应该看到什么"

| 内容 | 载体 |
|------|------|
| 哲学宣言 (7条) + 优先级 | AGENTS.md §Carror OS 哲学核心 |
| 8条铁律 + 置信度标注要求 | AGENTS.md §8 条铁律, kernel.md |
| AI 行为约束 (16条反模式) | anti-patterns.md |
| 项目特定规则/铁律升华 | kernel.md, claude-next.md |

**确定性保证**: 这些规则在 AI 生成任何输出前已经注入上下文。AI 无法在不违反铁律的情况下绕过它们 — **铁律违反 = BLOCKED**。

**覆盖范围**: 所有 AI 输出（代码、报告、决策）。

---

### Source II：静态规则源 — "系统强制什么结构"

| 内容 | 载体 |
|------|------|
| Hook 注册 (settings.json) | settings.json — PreToolUse/PostToolUse/Bash 等事件注册 |
| Hook 开关 (harness.yaml) | harness.yaml — hooks_enabled 字典，可单独关闭/开启每个 hook |
| Feature Registry (feature-registry.yaml) | feature-registry.yaml — hooks/skills/evidence_level 分类管理 |
| Skill 定义 (SKILL.md) | .claude/skills/*/SKILL.md — skill 触发条件和执行逻辑 |
| Source Mirror (同步纪律) | package-release.sh, audit-hooks.sh --check-source-mirror |

**确定性保证**: 这些是文件系统层面的硬约束。AI 可以"知道"铁律，但如果 hook 没注册 = 不执行。**文件存在 ≠ 生效**（DG-82: 39/44 hooks 无 flywheel.log）。

**覆盖范围**: 工具调用（Edit/Write/Bash）、会话生命周期、跨平台接入。

---

### Source III：运行时事实源 — "系统实际验证了什么"

| 内容 | 载体 |
|------|------|
| Oracle 审核 (静态检查) | Agent(opus, critic) — 文件存在性、合规审查 |
| Meta-Oracle (运行时验证) | Agent(opus, critic, 独立上下文) — smoke tests、烟雾日志、对抗性审查 |
| Hook 执行结果 (flywheel.log) | flywheel.log — intercept_count, error signatures |
| Smoke Test 回归 (harness-smoke-test.sh) | harness-smoke-test.sh — 全回归验证 |
| Audit Hooks (三方对账) | audit-hooks.sh — disk/registry/harness 一致性检查 |
| Error DNA (错误模式库) | .omc/state/error-dna.jsonl — 签名/次数/修复上下文 |

**确定性保证**: 这些是运行时产生的**事实**，不是"系统认为什么是对的"。`harness-smoke-test.sh 全绿` = 事实，不是判断。

**覆盖范围**: 验证、审查、回归测试、错误追踪。

---

## A→B→A 三重门 = 三源一致性的操作化实现

```
A 预测 → B 盲执行 → A 自证 → Oracle 审核（常规守门员）
                              ↓
                         Meta-Oracle 最后守门（仅在 G1-G4 触发）
```

这是三源一致性的**执行协议**:

| 步骤 | 映射到三源 | 说明 |
|------|-----------|------|
| A 预测（方案/PRD） | Source I (生成源) | AI 基于规则推理，输出预期结果 |
| B 盲执行（独立验证） | Source II (静态规则源) | 脱离 AI 上下文，用 hook/脚本执行验证 |
| A 自证（Oracle 审核） | Source III (运行时事实源) | Oracle 检查执行结果，不信任 AI 自证 |
| Meta-Oracle (G1-G4) | Source III ×2 + Source I 交叉 | 运行时验证 > 静态检查，对抗性审查找盲区 |

---

## 熔断机制 (Circuit Breaker)

当三源出现分歧时，不强行统一，而是触发熔断：

| 分歧类型 | 处理方式 |
|---------|---------|
| Source I vs II (规则冲突) | [哲学先行: 仲裁] — 按优先级裁决，不继续执行 |
| Source II vs III (规则未生效) | [治理异常] — audit-hooks 报告，修复后继续 |
| Source I vs III (规则被违反) | [铁律违反] — BLOCKED，回滚当前操作 |
| 三源同时分歧 (G1-G4) | Meta-Oracle ADVISORY/REJECT — AI 覆写需明确书面理由 |

---

## 纵深防御策略 (Defense in Depth)

三源一致性不是"三道防线防同一个攻击"，而是**异构冗余防御 (Heterogeneous Redundancy)**:

- **Source I 防 AI 幻觉**: 哲学 + 铁律强制文件来源标注，禁止无来源断言
- **Source II 防 AI 越界**: hook 拦截范围外修改、敏感文件触碰、破坏性操作
- **Source III 防 AI 欺骗**: Oracle/Meta-Oracle 独立审查，不信任 AI 自证

**关键区分**: Source II（静态规则）和 Source III（运行时事实）**必须使用不同验证方法**。如果两者都用 grep 检查同一文件，这就是同源失效。

---

## 红蓝对抗 (Red Teaming) — 持续进化机制

三源一致性不是静态的，必须定期接受"邪恶版 AI"的攻击测试：

1. **Red Team**: 专门训练一个 agent，每天尝试绕过三道防线
2. **攻击向量**: 提示注入、同源基错误、间接欺骗、规则漂移
3. **Blue Team Response**: 根据攻击手段修补对应防线

**狗粮模式的天然优势**: Carror OS 本身就是自己的 Red Team。每次狗粮反哺（DG-xxx）都是一次攻击测试 + 防御升级。

---

## 与已有机制的整合

| 旧概念 | 三源映射 | 说明 |
|--------|---------|------|
| Oracle/Meta-Oracle | Source I + III → II 验证 | 审核是源间交叉验证协议 |
| Hook/Skill/Harness | Source II (静态) + III (运行时) | 注册=静态，执行=事实 |
| 三方一致性 (hook/skill/registry) | Source II 内部一致性检查 | audit-hooks.sh 的核心职责 |
| A→B→A 三重门 | 三源一致性操作协议 | 执行层面的具体实现 |
| 狗粮反馈循环 | Red Team → Blue Team 进化闭环 | DG-xxx = 攻击日志 + 防御补丁 |

---

## Meta-Oracle 裁决标准（基于三源一致性）

Meta-Oracle 不是"更高级的 Oracle"，而是**独立的 Source III + Source I 交叉验证器**:

| 维度 | Oracle (常规守门员) | Meta-Oracle (最后守门员) |
|------|---------------------|--------------------------|
| 方法论 | Source I → Source II 检查一致性 | Source III (运行时事实) × Source I 交叉验证 |
| 审查手段 | 静态检查、文件存在性 | 运行时验证、烟雾日志、对抗性测试 |
| 找什么 | 违规/遗漏/不合规 | Oracle 的盲区（同源基失效、间接注入） |
| 为什么独立 | — | Oracle 和 AI 共享上下文 = 同源风险 |

---

## 引用来源

- **三源一致性概念**: 基于 OpenAI o1/o3 推理模型 + Anthropic Constitutional AI 的前沿安全架构
- **异构冗余防御**: 民航客机自动驾驶 (AI) + 飞行管理计算机 (Oracle) + 风洞数据模拟 (Mate-Oracle)
- **红蓝对抗**: 网络安全领域的攻击/防御持续进化模型
