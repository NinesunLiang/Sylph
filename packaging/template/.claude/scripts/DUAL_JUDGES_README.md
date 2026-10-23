# 双法官（Dual Judges）使用指南

> **用户视角**：你只需要知道两个名字 — **Oracle** 和 **Mate**。
> 内部模块命名（oracle_agent.py / meta_oracle.py / pretool-gate 等）是为了工程实现，用户不需要关心。

---

## 1. 一句话定义

**双法官 = Oracle（静态分析）+ Mate（运行时 TDD 冒烟）**，先后顺序，**被动响应**。

```
用户提交内容 → Oracle（静态，先）→ 决定跑不跑 Mate
                              ↓ ACCEPT/ADVISORY
                              Mate（运行时，后）→ 最终裁决
```

## 2. 何时会跑双法官

**双法官不会自动跑**。触发条件（满足任一）：

| 触发场景 | 谁在调 |
|---|---|
| 你说"**双法官过一遍**" / "**用 Oracle**" / "/lx-oracle review" | 你（用户主动） |
| L2 任务类型：架构变更 / 跨模块 / 不可逆 / 安全权限 / release / 长期无人 | L2 harness |

日常 L1 编辑（单文件、无跨模块影响）**不调双法官**——这是 API 成本 + 延迟成本的"成本门"。

## 3. 两个法官分别是什么

### 🔍 Oracle — 第一审（静态分析）

- **职责**：静态分析，不跑实际测试
- **哲学**：广度优先，bread-and-butter，速度快
- **依据**：Research 的依赖树 + 方案 + 不确定性
- **产出**：scope creep → REJECT；不完整 → ADVISORY；OK → ACCEPT
- **失败 → Mate 不跑**

### 🔬 Mate — 第二审（运行时 TDD 冒烟）

- **职责**：实际跑测试，模拟生产环境
- **哲学**：深度优先，更严格，更接近生产
- **依据**：Research 依赖树 vs 实际测试覆盖；mock vs production 数据
- **默认更严格**：不确定时默认 REJECT（vs Oracle 的 REJECT）
- **Oracle REJECT 时不跑**

## 4. 用户怎么用

```bash
# 1. 双法官级联（最常用）
# Oracle 先跑
python3 .claude/scripts/oracle_agent.py review \
  --mode static \
  --research .omc/tasks/{date}/{task}/research.md \
  --plan .omc/tasks/{date}/{task}/plan.md \
  --diff <your-diff.patch>

# 看完 Oracle 输出（ACCEPT/ADVISORY），再调 Mate
python3 .claude/scripts/oracle_agent.py review \
  --mode runtime \
  --research .omc/tasks/{date}/{task}/research.md \
  --executor .omc/tasks/{date}/{task}/executor.md \
  --logs <test-logs.txt>

# 2. 单跑 Oracle（不要 Mate）
python3 .claude/scripts/oracle_agent.py review --mode static --diff <diff>

# 3. 单跑 Mate（已经 Oracle 通过的情况）
python3 .claude/scripts/oracle_agent.py review --mode runtime --research X --logs Y

# 4. duo 模式（一键级联 + 合并 verdict）
python3 .claude/scripts/oracle_agent.py review --mode duo --research X --plan Y --diff Z --logs W
```

## 5. 输出格式（两个法官一致）

```
VERDICT: ACCEPT | REJECT | ADVISORY
Safety Risk: HIGH | MEDIUM | LOW
Architecture: 0-10
Evidence: 0-10
```

## 6. 常见误解

| 误解 | 真相 |
|---|---|
| "双法官 = pretool-gate + posttool-claim-audit" | ❌ 那是历史 ADR 里的另一套机制（Pre/Post 工具链）。**双法官 = Oracle + Mate**，是 lx-oracle 协议层。|
| "Meta-Oracle = Mate-Oracle" | ❌ **不同**。Meta-Oracle 是回顾性 G1-G4 评分模块（`meta_oracle.py`），Mate 是运行时 TDD 审计（`oracle_agent.py` 里的 ORACLE_MATE_PROMPT）。|
| "双法官会自动跑" | ❌ **被动响应**——只在用户主动要求或 L2 任务时触发。|
| "Mate 比 Oracle 宽松" | ❌ **Mate 更严格**——不确定时默认 REJECT，Oracle 不确定时也 REJECT 但 score 默认 7。|

## 7. 治理哲学：疏导 + 兜底

> **本节对应 `.claude/references/governance-philosophy.md` 完整文档**。这里只列用户需要知道的要点。

### 核心思想

不防错（防不过来），而是**疏导**（工作流步骤前置引导）+ **兜底**（防止 AI 不遵循引导）。

| 模式 | 描述 | 工作量 |
|---|---|---|
| 防错（禁用）| 预测所有 AI 错误并拦截 | 不可穷尽 |
| 疏导（首选）| step 前置引导（字段/模板/tooltip）| 低 |
| 兜底（辅助）| AI 不遵守时 REDIRECT/BLOCK | 中 |

### 22 个门实测分类

- **8 疏导为主**（36%）：doc_reference_before_delete / verify_gate / oracle_gate 等
- **11 疏导 + 兜底双层**（50%）：sensitive_edit / secret_scan / commit_soft_completion 等
- **3 纯兜底**（14%）：governance_bypass / injection / omc_skeleton_readonly（必要的安全攻击面）

### 用户视角的体现

| 你看到的 | 内部机制 |
|---|---|
| plan.md 的 consumes + produces 字段 | 步骤契约（路径锁定，AI 一直在正确路径）|
| handoff.md 的 "Last Step Produces" 段 | step 边界契约握手 |
| verify 时 PlanGate 严格 | 兜底（防 AI 写错）|
| 软完成语检测 warn | 兜底（防 AI 自夸）|
| delete 文档引用检测 | 疏导（删前提示怎么改）|

### 对用户的好处

- **不浪费算力**：AI 启动 step 前就知道需要什么，不在跑偏后矫正
- **不报 hook error**：所有 hook error 根因已修（commit 2907e42 / 6d3de8e / 952100c / 43ad497）
- **归档不再卡**：VERIFYING handoff 自动就绪（commit 43ad497）
- **步骤交接契约**：每个 step 边界显式握手

### 详细文档

完整治理哲学（22 门分类、加新门准则、不应加的"纯防错"模式）见：
`.claude/references/governance-philosophy.md`

---

## 8. 内部模块（无需用户感知）

| 用户视角 | 内部模块 | 角色 |
|---|---|---|
| Oracle | `oracle_agent.py` + `ORACLE_STATIC_PROMPT` | 第一审 |
| Mate | `oracle_agent.py` + `ORACLE_MATE_PROMPT` | 第二审 |
| (回顾评分) | `meta_oracle.py` | Meta-Oracle — G1-G4 历史评分，非双法官 |
| (辅助) | `lib/oracle_models.py` | 模型路由（按 role 选 sonnet/opus）|

**用户只需要记住 Oracle 和 Mate 两个名字**。其他内部细节（模块名、prompt 名、CLI 参数）按需查源码。

---

*最后更新: 2026-08-30 | 关联: `verdict.yaml` v3*