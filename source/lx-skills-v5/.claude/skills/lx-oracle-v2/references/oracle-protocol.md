# Oracle Protocol — 双协议定义

> 本文件是 Carror OS Oracle 审核机制的权威协议规范。
> 上游源: `.claude/nodes/oracle_terminal.md` (Oracle-V 两阶段) + `~/.claude/skills/lx-oracle/SKILL.md` (Oracle-D 判决，用户级 skill)
> 使用者: `lx-oracle-v2` skill → Agent(critic) 独立上下文注入

---

## 协议选择矩阵

| 场景 | 协议 | 调用方 |
|------|------|--------|
| 危险操作裁决 (rm -rf / git push --force) | Oracle-D | lx-goal / lx-ghost 决策链 |
| 架构决策审核 (重构方案 / 跨子系统变更) | Oracle-D | lx-goal / lx-ghost / lx-oma-orch |
| 方向漂移检测 (当前工作是否在目标范围内) | Oracle-D | lx-goal / lx-ghost |
| 硬边界预检 (操作是否触碰硬边界) | Oracle-D | permission-gate 升级 |
| 真阻断判断 (核心路径是否真的被堵死) | Oracle-D | AI 自主判断升级 |
| PRD/方案事前审核 (A 的测试方案公证) | Oracle-V (阶段1) | lx-ghost Phase 0.5 / RPE 验证 |
| 执行后终审 (A 预测 vs B 事实 vs A 自证) | Oracle-V (阶段2) | lx-ghost / lx-oma-orch |
| Meta-Oracle 升级前预审 | Oracle-V (阶段2) | meta-oracle-trigger |

---

## Oracle-D: Decision Protocol (单阶段判决)

### 裁决范围

| 类型 | 裁决 | 示例 |
|------|------|------|
| **危险操作** | approved / rejected | `git push --force` 是否安全 |
| **架构决策** | approved / rejected | 重构方案是否符合 Philosophy |
| **方向漂移** | confirmed / diverted | 当前工作是否在目标范围内 |
| **硬边界预检** | safe / blocked | 操作是否触碰硬边界 |
| **真阻断判断** | blocked / workaround | 核心路径是否真的被堵死 |

### 审核原则

1. **Philosophy 不可违背** — 即使技术上可行，违反 Philosophy 的操作必须 rejected
2. **Iron Rules 不可绕过** — AI 试图 workaround 时，Oracle 必须 rejected 并要求直面问题
3. **0 信任** — 不假设调用方已做尽职调查，独立验证所有前提
4. **裁决留痕** — 每条裁决必须附带理由，不可仅输出 approved/rejected

### 输出格式

```yaml
oracle_d:
  status: approved | rejected | escalated
  reasoning: string
  risk_level: P0 | P1 | P2
  evidence:
    - source: "path:line"
      finding: string
  recommendation: string | null  # escalated 时: 建议 Level 3 人类裁决
```

---

## Oracle-V: Verification Protocol (两阶段验证)

> 来源: `.claude/nodes/oracle_terminal.md`。专家公证人 / 两阶段验证官。
> 输入：A 的预测 + 测试方案，或 A 的自证 + B 的事实报告。
> 输出：公证意见 / 终审判定。

### 选型标准

| 维度 | 最低要求 | 推荐 |
|------|---------|------|
| 模型层级 | sonnet-class | opus-class |
| 与 A 不同族 | 必须 | 强烈要求 |
| 领域知识 | 通用 | 专业领域匹配 |
| 三端关系 | A≠B, Oracle≠A | A/B/Oracle 全部不同族 |

> Oracle-V 模式下，Agent(critic, opus) 天然满足"与 A 不同模型族"要求 (critic vs 主会话模型)。

### 阶段 1 — 事前公证（Pre-execution Notarization）

**输入**：A 的测试方案 + 可证伪预测

**检查项**：
- 预测是否可证伪？（有明确的 falsification_threshold）
- 测试步骤是否可执行？（有具体命令/路径）
- 成功/失败场景是否无歧义？
- 测试方案是否覆盖关键路径，而非绕过核心逻辑？

**输出**：
```yaml
oracle_v_stage1:
  status: approved | rejected | needs_clarification
  reasoning: string
  min_evidence_check:
    passed: true | false
    detail: "每条 evidence 的 machine fields (path/size/sha256/exit_code) 数，不足 3 的列出"
  clarifications: string[] | null  # 仅 needs_clarification 时
  approved_plan:
    - step_id: string
      description: string
      command: string | null
      verification_method: string
  note: "预测已审阅，已与测试方案剥离，不传递给 B"
```

### 阶段 2 — 事后终审（Post-execution Final Review）

**输入**：A 的原始预测 + B 的事实报告 + A 的自证

**检查项**：
- A 的预测与 B 的观测是否匹配？
- A 的自证是否诚实？是否有事后合理化（post-hoc rationalization）？
- A 对偏差的解释是否合理（根因 vs 借口）？

**输出**：
```yaml
oracle_v_stage2:
  overall: PASS | FAIL | INCONCLUSIVE
  reasoning: string
  predictions_total: int
  predictions_held: int
  predictions_failed: int
  honesty_assessment: string
  failed_items:
    - prediction_id: string
      issue: string
      evidence_ref: string
```

> **注意**：Oracle-V 不定义 `risk_level` 字段。Oracle-V 评估的是证据完整性和预测诚实度，而非操作风险等级。风险定级是 Oracle-D（决策链审核）的职责。两者分工明确：Oracle-D 判断「该不该做」，Oracle-V 判断「做没做对」。

### 硬规则

- Oracle 的事前批准是**绑定**的 — A 不得在知道 B 结果后修改预测
- 阶段 1 可以向 A 提问澄清，但**不得泄露预期的答案方向**，**最多 2 轮循环**，超过 → 自动 rejected
- 阶段 2 是单向评审：接收全部材料后一次性输出，不与 A 对话
- 终审报告中必须逐条引用证据（`file:line` 或命令输出）
- 阶段 1 以 **minimal_by_category**（详见 AGENTS.md #6 证据模板）为拒止底线：B 报告每条 evidence 必须 ≥3 个 machine fields (path/size/sha256/exit_code 中至少 3 个)，不足 → rejected

### 边界声明

| 不做的操作 | 原因 |
|-----------|------|
| 替代 B 执行测试 | Oracle 只审方案和结果，不执行 |
| 与 A 在阶段 2 对话 | 防止污染终审独立性 |
| 替 A 修改预测 | 预测是 A 的假设，Oracle 不替 A 思考 |

---

## 故障恢复与容错

> Oracle 协议不仅定义正常执行路径，还必须覆盖故障场景。以下为现实故障的降级协议。

### 内容截断

- `oracle-spawn.sh prepare` 将 target 内容截断到 50KB
- 截断后，Agent 收到的审核内容可能不完整
- **协议**：当 target 超过 50KB 时，Agent 必须在裁决的 `reasoning` 中标注 `[CONTENT_TRUNCATED: 原始 N 行, 截断至 50KB]`
- 裁决仍然有效，但置信度应降级，并建议在可能时进行完整审核

### Agent Spawn 超时

- Agent(critic, opus) 默认超时 120s
- **降级路径**：
  1. 超时 → 记录到 `.omc/state/pending-decisions.md`
  2. 降级放行（不阻塞主流程）
  3. `flywheel_event "oracle_spawn_timeout" "P1"`
  4. 在退出报告中标记 "Oracle 审核未完成（超时）"

### API 序列化失败

- 已知故障模式：lone surrogate (DG-87)、context overflow
- **降级路径**：
  1. Agent spawning 失败 → 降级为手动执行 Oracle 方法论
  2. 手动执行：AI 自行按协议逐项审核，但标注 `[MANUAL_FALLBACK: Agent spawn failed]`
  3. 裁决置信度降级，标记为需后续补审

### 裁决存储失败

- `oracle-spawn.sh record` 写入 `oracle-verdicts.md` 失败时
- **容错**：至少 echo 原始 agent 输出到 stdout，不静默丢弃

---

## Meta-Oracle 升级路径

> Oracle 的裁决不是最终的。当 Meta-Oracle 触发时 (G1-G4)，Oracle 的 ACCEPT/高分裁决需经 Meta-Oracle 独立验证。

**升级条件**：Oracle 给出 ACCEPT 且任务满足 G1-G4 任一触发条件时，自动升级至 Meta-Oracle。

**G1-G4 触发点**：
- G1: 架构决策终审 (≥2 子系统 + 不可逆变更)
- G2: PRD/方案最后一步 (Oracle 已 ACCEPT)
- G3: Oracle ACCEPT + ≥8.5 分
- G4: Release 门禁 (package-release.sh 执行前)

**Meta-Oracle 执行方式**：opus critic agent (独立上下文，不共享主会话)，运行时验证 > 静态检查。
