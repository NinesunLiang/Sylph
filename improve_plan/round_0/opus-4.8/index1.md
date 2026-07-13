# CarrorOS Opus-4.8 完整方案（1/10）

我现在给出我的完整版本，区别于 GPT Sol 的补充方案。我会在 10 轮内完成。

---

## 第 1 轮：核心立场与架构决策

### 一、我与 GPT Sol 的根本差异

GPT Sol 采取了**渐进兼容**策略：
- 保留现有 8/8 架构主体
- 增量补强 4 个修正 + 3 个补强
- 尽量不破坏已有设计

我（Opus-4.8）采取**重新审视**策略：
- 从你的 10 项原始需求出发
- 质疑 8/8 方案中是否存在过度设计
- 提出更简洁、更务实的替代方案
- 明确哪些是 MVP 必需，哪些是未来扩展

### 二、我的核心判断

基于对你 10 项需求的深度理解，我认为当前 8/8 方案存在 **3 个战略性问题**：

#### 问题 1：过度形式化导致实施门槛过高

8/8 方案定义了：
- 15+ Schema
- 4 层状态机
- 双栈平台适配
- 5 级压缩流水线
- Oracle/Multi-Judge/Meta-Oracle
- Archive 事务与 Evidence Root
- 完整的 MCP/Provider/Fallback 治理

**这对于一个刚启动的 CarrorOS MVP 来说过重。**

你的核心诉求是：
1. 解决 Context Boom（✓ 必需）
2. 抗 Compact 风暴（✓ 必需）
3. 简单交接（✓ 必需）
4. 飞轮学习（△ 可后置）
5. L1/L2 分级（✓ 必需）

我建议先做 **Minimum Viable Governance**，再迭代到完整治理。

#### 问题 2：token.json vs state.json 的历史包袱未明确处理

GPT Sol 建议：
> 可以保留 token.json 作为 state source，或者迁移到 state.json

我认为：
> 必须立即决定，不能两者共存，否则会导致后续所有 Schema 和工具链的双重维护。

**我的裁决：保留 token.json，但正式将其定义为 TaskState 的持久化格式。**

理由：
- 你已经有大量基于 token.json 的工具
- 改名不改变协议本质
- 避免大规模数据迁移风险

但必须增加：
- `schema_version`
- CAS 版本控制
- 明确的字段语义定义

#### 问题 3：双审判官的调用成本被低估

8/8 方案定义了：
- Oracle：主审
- Mate Oracle：副审
- Multi-Judge：多模型投票
- Meta-Oracle：聚合裁决

这在高风险场景是有价值的，但你的需求 10 说的是：
> 在五步法的执行方案审核和校验结果的审核或者其他决策点辅助决定

关键词是"**辅助**"，不是"**必需**"。

我建议：
- L1：不启用 Oracle
- L2 方案审核：单一 Oracle（Flash 能力不足时）
- L2 结果验证：单一 Oracle（residual risk 高时）
- Mate Oracle：仅用于关键架构决策和争议裁决
- Multi-Judge：仅用于跨组织/高合规场景

不要让"双审判官"变成每个 step 都要调用的标配。

---

### 三、我的架构决策

基于上述判断，我给出的 CarrorOS 架构分为 **3 个阶段**：

#### Phase 0：MVP（0～30 天）

**目标**：先止血，证明核心机制可行

```text
核心能力：
✓ token.json 作为唯一状态源
✓ 渐进式披露（D0～D3）
✓ Artifact + Preview 稳定化
✓ handoff.md 简单交接
✓ Hot Tail 每轮刷新
✓ L1 快速工作流
✓ 基础 VerifyGate
✓ 简单 Resume

不包括：
✗ Oracle/Multi-Judge
✗ Archive 事务
✗ Evidence Root
✗ 飞轮升华
✗ OpenCode 适配
✗ Provider 熔断
```

**关键指标**：
- Context 不再线性增长
- 删除 transcript 后可恢复
- handoff 后新会话可继续

#### Phase 1：L2 与长任务（31～60 天）

**目标**：支持复杂任务和无人模式

```text
新增能力：
✓ L2 工作流
✓ Checkpoint + 外部副作用对账
✓ 无人模式 Autonomy Contract
✓ 单一 Oracle（条件触发）
✓ Error DNA 基础版
✓ 模型路由（Flash/Opus）
✓ D4/D5 隔离
```

#### Phase 2：飞轮与多栈（61～90 天）

**目标**：系统自我成长和跨平台

```text
新增能力：
✓ Learning Promotion Pipeline
✓ Mate Oracle（争议场景）
✓ OpenCode 适配
✓ Archive 与 Evidence Root
✓ Provider Fallback
✓ 成本看板
```

---

## 第 2 轮预告

接下来 9 轮我将输出：

```text
Round 2: MVP 核心状态模型（token.json 正式 Schema）
Round 3: 渐进式披露与 Hot Tail 实现
Round 4: handoff.md 与 Resume 协议
Round 5: L1 快速工作流与 VerifyGate MVP
Round 6: L2 工作流与条件 Oracle
Round 7: 无人模式 Autonomy Contract
Round 8: 飞轮升华流水线
Round 9: 实施路线图与验收门
Round 10: 最终裁决与关键分歧总结
```

**核心原则**：
1. 先简单可用，再完整严谨
2. 磁盘记忆优先，Context 最小化
3. 状态文档化，恢复确定性
4. 能力分级，按需启用
5. 飞轮后置，避免过早优化

---

准备好了吗？我现在开始第 2 轮。