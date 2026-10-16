# Anti-Patterns — 经验沉淀

_Updated: 2026-08-14 | 精简至代码引用项（K1-K3 / I1 / J1-J2），通用分类已移除_
_来源：.omc/knowledge/sublimation-log.jsonl + PostToolUse hook 实测触发_

> 本文件只保留**被 hook/代码引用或实测触发**的反模式。通用行为规范（不读 AGENTS、硬编码路径等）归入 `current-task-architecture.md` §3 铁律，不在此重复。

## 已识别模式

- **assertion_recurring** (step=RPE-C-S1, retry=2)
  - `RPE-C controlled recurring path expectation failure: expected .omc/scripts but observed stale .claude/scripts path; attempt to reload`

---

## I. 运行稳定性（Runtime Instability）

### I1 S1 步骤 30 秒超时熔断
- **现象**：step S1 反复 `TimeoutError: test timed out after 30s`（累计 16 次，2026-07-12~07-19，每 session 至少一次）
- **根因**：S1 步骤执行长时间挂起操作，默认 30s 超时不足
- **→ against**：
  1. 增大 S1 超时（30s→120s 或配置化）
  2. 或拆分 S1 为多个子步骤，单个不超 30s
  3. 或添加心跳/进度汇报区分"慢"与"死"

---

## J. 分类缺失（Classification Gap）

以下模式经升华管道检出（hits 超阈值）但原始错误数据泛化，无法直接提取可复用规则。

### J1 未分类错误膨胀（unknown, hits=155）
- **现象**：claude-next 中 `unknown` 以 "Test error"、"err2"、`[Bash] {command failed}` 泛化为主
- **→ against**：将 `[Bash] {stderr: command failed}` 映射为具体分类（如 `bash_command_failure`），为每个 error-dna 步骤注册已知失败签名

### J2 未分类循环膨胀（unknown_recurring, hits=124）
- **现象**：`unknown` 的循环版，以 "err3"、"err4" 占位符为主
- **→ against**：与 J1 同源解决；J1 修复后此模式自动消失

---

## K. 虚假数值断言（Pseudo-Integrity）

以下模式由 `posttool-claim-audit.py` 实测触发并引用（检测信号 = hook 输出格式）。

### K1 G1_PSEUDO_INTEGRITY：断言无来源
- **最后触发**：2026-08-14（仍活跃，本会话实测触发 warn）
- **描述**：AI 输出含未标注来源的数值断言（违反铁律#1），本分类触发最频繁
- **检测信号**：`⚠️ G1_PSEUDO_INTEGRITY: 数值断言(N 条)无来源`
- **触发条件**：Edit/Write 含无 `[来源:file:line]` 或 `[内部自检，非行业标准]` 标注的数值
- **→ against**：所有数值断言必须带来源标注；无法提供确切来源时标注 `[内部自检，非行业标准]` 并附推算依据。输出前自检（evidence_gate），而非被动等 hook 事后抓
- **严重度**：high，直接违反铁律#1，**仍应遵守**

### K2 E6_SELF_CONTRADICTION：编辑未收敛
- **最后触发**：**0 次**（`.omc/state/edit-churn-log.jsonl` 450 条 2026-08-14 数据，contradiction 全 false）
- **状态**：⚠️ **可能过期**——当前模型能力下已不再犯，保留为历史教训（低优先级）
- **描述**：同一文件短期连续 Edit 多次导致签名不一致（边写边改、方向摇摆）
- **检测信号**：`⚠️ E6_SELF_CONTRADICTION: [E6] EDIT_REPEAT: …编辑 N 次，N 个签名，可能未收敛`
- **触发条件**：同一文件被 Edit 连续修改 >=3 次且签名数 >= 编辑次数
- **→ against**：复杂内容（数值/多段/表格）优先用 Write 一次写出；Edit 仅用于精确单句修正
- **严重度**：medium（若未来模型退化重现，恢复高优先级）

### K3 E6_CONTENT_FLIP：前后内容方向摇摆
- **最后触发**：**0 次**（同上 edit-churn-log 数据）
- **状态**：⚠️ **可能过期**——当前模型能力下已不再犯，保留为历史教训（低优先级）
- **描述**：同一文件最近 3 次编辑 hash 各不相同、方向不一致（A→B→A 反复）
- **检测信号**：`⚠️ E6_SELF_CONTRADICTION: [E6] CONTENT_FLIP: …最近3次编辑hash均不同，方向摇摆`
- **触发条件**：同一文件 Edit >=3 次且最新 3 次 hash 二进制不一致
- **与 K2 边界**：K2 聚焦编辑**次数**（应 Write）；K3 聚焦编辑**方向**（应先打草稿）
- **→ against**：重大方向变更前先收敛方案（executor.md 打草稿），再 Edit 目标文件
- **严重度**：low（0 触发证据）

---

## L. AI 行为反模式（index37 教训，2026-08-30）

> 来源：index37-双法官盲评-CarrorOS-真实-AI-治理效能全量复测 task 实际报错分析。
> 这些不是机制 bug——是 AI 自身行为反模式。**疏导目标：AI 启动任务前先扫这些模式**。

### L1 PLAN_PHASE_FORMAT：plan.md Phase 头格式错
- **现象**：`❌ PlanGate 未通过: Plan must have at least 1 Phase (format: ## Phase N)`
- **根因**：AI 写 plan.md 时用了 "## Phase 1: 调研"——PlanGate 正则只接受严格 `## Phase 1`
- **触发条件**：AI 自创 plan 模板而非用 init 自动生成的模板
- **→ against**：
  1. 永远用 `carros_base.py init --task-id X --steps "..."` 自动生成 plan.md 模板
  2. 不要 Write 整个 plan.md——init 已经填好骨架
  3. 编辑时只改 step 内的 `scope`/`acceptance`/`verify` 字段，Phase 头保持严格
- **严重度**：medium（首次必踩，1 分钟可修）

### L2 WRITE_OVERSIZE：单次 Write 超 ~8192 tokens
- **现象**：`Error: content_truncated tool=write`
- **根因**：Claude Code Write 工具单次 content 字段上限 ~8192 tokens
- **触发条件**：AI 写大文件（battery.py、config.yaml 等）一次性 Write
- **→ against**：
  1. **分批 Write**：先 Write 文件头（前 30-50 行），Edit/append 后续
  2. **预估大小**：写之前粗略计算 token 数（`wc -m` 中文 1 字 ≈ 1.5 token，英文 1 字 ≈ 0.5 token）
  3. **超 500 行的文件**必须用 init/template + Edit 增量
- **严重度**：medium（机制限制无法绕过，只能改用法）

### L3 SIG_MISMATCH：调用函数传错参数
- **现象**：`TypeError: spawn_judge() takes 1 positional argument but 2 were given`
- **根因**：AI 凭"感觉"调用，未读取函数定义就传参
- **触发条件**：AI 调用非自己定义的函数时
- **→ against**：
  1. **调用前必读函数定义**（Grep + Read 函数签名）
  2. 遵循步骤交接契约：consumes 字段 = 函数签名要求
  3. **Read 是契约的来源**——不读就违约
- **严重度**：low（1 秒可修，但反映"不读源码"习惯）

### L4 EV_KEYPHRASE_MISS：EV 块缺 verify 关键短语
- **现象**：`❌ VerifyGate BLOCKED — evidence_missing`
- **根因**：AI 写 EV 块时没用 plan.verify 里的关键短语，VerifyGate 无法匹配
- **触发条件**：AI 写完 EV 块但没用 plan.verify 的原文短语
- **→ against**：
  1. **EV 块 assertion 字段必须逐字包含 plan.verify 关键短语**（已在 executor 模板注释）
  2. copy-paste plan.verify 关键短语到 EV 块，再补充实测
  3. 完成 EV 块前 Read 一下 plan.md 该 step 的 verify 字段
- **严重度**：low（机制正确，AI 偷懒）

### L5 SLEEP_OVERSIZE：单次 sleep 超沙箱超时
- **现象**：`Error: Exit code 143 / Command timed out after 2m 0s`
- **根因**：DSH 沙箱强制 60s / Claude Code Bash hook 默认 120s
- **触发条件**：AI 用 `sleep 110` 等待后台任务完成
- **→ against**：
  1. **分多个短 sleep**（`sleep 50 && sleep 50 && sleep 20`）
  2. **后台跑**：`run_in_background: true` + 后续查询时用 jobs 列表
  3. **轮询代替 sleep**：用循环查 status 直到 ready
- **严重度**：medium（沙箱机制无法绕，必须改用法）

### L6 PARTIAL_FIX：bug 修一半就停
- **现象**：错误修了一半，AI 继续往下走时报新错（"为什么不输入 prompt？"）
- **根因**：AI 修了 spawn_judge 签名但没继续往下调
- **触发条件**：bug 修复后 AI 没有继续
- **→ against**：
  1. **bug 修复后必须跑全流程验证**（不能修完就走）
  2. **每修一个错误，重新评估下一步入参**（steps 边界契约）
  3. **遵循"一镜到底"原则**：连续修复直到全流程通过
- **严重度**：high（破坏连贯性，浪费算力重复查错）

---

## 模式速查表

| 反模式 | 类型 | 对应机制 | 疏导 |
|---|---|---|---|
| L1 PLAN_PHASE_FORMAT | AI 行为 | PlanGate 严格 | init 自动模板 |
| L2 WRITE_OVERSIZE | 工具限制 | content_truncated | 分批 Write |
| L3 SIG_MISMATCH | AI 行为 | TypeError | Read 函数定义 |
| L4 EV_KEYPHRASE_MISS | AI 偷懒 | VerifyGate 严格 | 复用 plan.verify |
| L5 SLEEP_OVERSIZE | 沙箱限制 | timeout | 分批 sleep / 后台 |
| L6 PARTIAL_FIX | AI 行为 | 无 | bug 修完跑全流程 |

### governance_intervention（飞轮升华 2026-09-10）
- 来源：自动升华，hits=4（阈值≥3）
- 触发条件：反复出现的 `governance_intervention` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决

### redirect_recurring（飞轮升华 2026-09-10）
- 来源：自动升华，hits=4（阈值≥3）
- 触发条件：反复出现的 `redirect_recurring` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决

### blocked_recurring（飞轮升华 2026-09-10）
- 来源：自动升华，hits=3（阈值≥3）
- 触发条件：反复出现的 `blocked_recurring` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决
