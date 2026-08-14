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
