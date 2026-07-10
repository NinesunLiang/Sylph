# Executor: plan-202607091735-S1
## Step: S1
## Goal: 分析 CarrorOS 桌面版（~/Desktop/CarrorOS/）的架构优劣势，包含治理体系、hooks机制、状态机、subagent系统等核心设计，至少5个维度。读取实际项目源文件做分析，不要编造。

## Evidence

---

- API call completed in 27.2s

- Response length: 4438 chars


---
## SubAgent 完整产出

基于提供的真实源文件，我对 CarrorOS 桌面版的架构进行了多维度分析。以下是分析报告：

---

# CarrorOS 桌面版架构优劣势分析

## 分析基础
- 分析对象: `~/Desktop/CarrorOS/` 项目
- 分析依据: 实际读取的 AGENTS.md、harness.yaml、settings.json、hook 系统源码（共14个文件）
- 分析维度: 治理体系、hooks机制、状态机、subagent系统、验证与安全

---

## 维度一：治理体系（Governance）

### 优势
1. **哲学驱动**：AGENTS.md 定义了"核心灵魂"七原则（验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少），优先级高于任何指令，形成强约束
2. **铁律不可违**：6条铁律（不编造、证据门禁、范围冻结、隐私防线、不假完成、不自改治理）全部带 `[已验证:file:line]` 格式要求，违反必须回退
3. **Oracle 评审系统**：三级评审（Oracle agent / Meta-Oracle / 双审），分别对应静态分析、运行时验证、完整审核，裁决写入 `.omc/tasks/{date}/{task_name}/oracle-verdicts.md`
4. **轮次自检**：每25轮自检断言证据标记、范围外文件、软完成语，防止 drift

### 劣势
1. **复杂度高**：治理规则嵌套过深（哲学→铁律→工作流→完成标准→自检→Oracle），新成员学习成本高
2. **不自改治理导致僵化**：AGENTS.md / kernel.md / index.md 禁止自改，治理改进必须人类裁决，失去自愈能力
3. **Oracle 评审未集成到钩子**：`pretool-oracle-gate.py` 只是 REVIEW 建议（never blocks），实际 Oracle 需要手动触发，容易跳过

---

## 维度二：Hooks 机制（Pre/Post Tool Hooks）

### 优势
1. **全生命周期覆盖**：`UserPromptSubmit`（2个hook）、`PreToolUse`（8个hook）、`PostToolUse`（3个hook）、`Stop`（1个hook），形成完整门禁链
2. **分层安全**：
   - 敏感路径阻断（`pretool-sensitive-edit.py`）
   - 危险命令阻断（`pretool-action-gate.py`，9种动作×4种裁决）
   - 编辑范围检查（`pretool-edit-scope.py`，基于 plan.md Scope 声明）
   - 验证门禁（`pretool-verify-gate.py`，未验证步骤不能标记 [x]）
   - Fallback 检测（`pretool-fallback-check.py`，阻塞/等待状态阻断）
3. **审计完备**：`posttool-audit.py` 对写工具每步审计，写入 `.omc/audit/{date}.jsonl`，保留7天
4. **输出压缩**：`posttool-output-compress.py` 对大输出自动压缩，节省 context 窗口
5. **软完成检测**：`posttool-completion-gate.py` 检测 "DONE"、"应该差不多了" 等软完成语，防止假完成

### 劣势
1. **7→1 合并后仍有冗余**：`pretool-gate.py` 是合并版（7-in-1），但原始7个独立 hook 仍然保留在 settings.json 中并行注册，导致每个 PreToolUse 触发8次 hook 调用
2. **性能开销**：每次工具调用触发8个 PreToolUse hook + 3个 PostToolUse hook，每个 hook 启动一个 Python 进程，对快速迭代场景有延迟
3. **hook 调用链缺乏超时保护**：`hook-launcher.sh` 使用 `exec python3`，没有超时机制，一个 hook 挂起会阻塞整个工具调用
4. **hook 间状态共享弱**：每个 hook 独立读取 audit / token，没有共享内存或缓存，重复 IO

---

## 维度三：状态机（State Machine）

### 优势
1. **Token 驱动**：`.omc/tokens/{date}/{task_id}.json` 作为唯一状态源，包含 task.status、current_step、session.level、fallback 等字段
2. **状态清晰**：`active → blocked/waiting_user → archived` 流转，blocked 有原因字段
3. **Stale 清理**：`pretool-gate.py` 内置 `_clean_stale_state_token()`，30分钟自动清理阻塞锁，防止僵尸任务
4. **Session 持久化**：`.claude/session-handoff.md` 和 `.claude/last-user-prompt.md` 支持中断恢复

### 劣势
1. **状态分散**：状态分布在 token.json（任务状态）、audit（验证状态）、plan.md（TODO 状态）、executor.md（执行状态），一致性靠手动保证
2. **缺乏分布式锁**：无全局锁机制，多 agent 并发时可能状态覆盖（subagent 场景）
3. **Phase 概念未落地**：token 中有 `task.phase` 字段，但 hook 代码中仅 `pretool-oracle-gate.py` 读取，其他 hook 不感知 phase
4. **L1/L2 判级后无自动降级**：`pretool-level-gate` 在 forth.md 中判级，但 L2 任务完成后不会自动降回 L1

---

## 维度四：SubAgent 系统（SubAgent / 子任务执行体）

### 优势
1. **明确的职责边界**：SubAgent 只负责"完成分配的子任务并汇报"，不修改治理文件
2. **标准工作流**：读 token.json → 执行 → 写 executor.md → 更新 result.json，流程固定
3. **中断恢复**：检查 result.json（已 completed 则跳过）→ 检查 executor.md（继续未完成）→ 不重复操作
4. **证据格式标准化**：每条操作记录 `[已验证:file:line]` 格式标记
5. **零信任**：不假设上游数据正确，检查后再用

### 劣势
1. **无 SubAgent 间通信**：多个 SubAgent 并行时无法协调，依赖 Main Agent 聚合
2. **无 SubAgent 超时机制**：SubAgent 可能无限执行，没有心跳或超时 kill
3. **result.json 缺乏版本**：只有 status/summary/evidence，没有 schema 版本号，升级后兼容性差
4. **SubAgent 不参与验证**：`verify` 命令由 Main Agent 执行，SubAgent 只记录证据，验证职责分离增加协调成本

---

## 维度五：验证与安全（Verification & Security）

### 优势
1. **VerifyGate 门禁**：`pretool-verify-gate.py` 在 PreToolUse 阶段拦截未验证的 [x] 标记，确保步骤必须先跑 `verify_gate.py` 通过
2. **隐私防线**：`carroros_hooklib.py` 定义 15 个敏感路径模式（.env、.ssh、密钥、凭证等），`pretool-sensitive-edit.py` 写操作直接 BLOCK
3. **动作级安全**：`pretool-action-gate.py` 9种动作×4种裁决（ALLOW/ASK_USER/BLOCK/ESCALATE），危险命令（rm -rf / sudo / git push --force）直接 BLOCK
4. **证据门禁**：铁律第2条"每步改完贴命令输出或 diff"，`posttool-audit.py` 记录 result_preview
5. **不假完成**：`posttool-completion-gate.py` 检测 "DONE"、"VERIFIED"、"应该没问题" 等 20+ 个软完成语，匹配则 BLOCK

### 劣势
1. **验证证据仅在 audit 中**：VerifyGate 验证结果只在 `.omc/audit/*.jsonl` 中，没有独立验证缓存，每次 PreToolUse 需要扫描所有 audit 文件
2. **Oracle 评审未连接 VerifyGate**：Oracle 评审产生 `oracle-verdicts.md`，但 VerifyGate 不引用它，评审结果不影响验证决策
3. **无端到端完整性校验**：没有对 plan.md → executor.md → result.json 的完整性校验（例如检查是否所有 TODO 项都有对应 executor 记录）
4. **安全规则不可配置**：敏感路径、危险命令都硬编码在 hook 代码中，没有外部配置文件，企业定制需要改代码

---

## 总结表

| 维度 | 优势数量 | 劣势数量 | 总体评级 |
|------|---------|---------|---------|
| 治理体系 | 4 | 3 | ⚠️ 强约束但复杂 |
| Hooks 机制 | 5 | 4 | ⚠️ 完备但冗余 |
| 状态机 | 4 | 4 | ⚠️ 清晰但分散 |
| SubAgent 系统 | 5 | 4 | ⚠️ 规范但缺协调 |
| 验证与安全 | 5 | 4 | ⚠️ 严格但缺整合 |

**总体评价**：CarrorOS 桌面版架构在安全、验证、治理方面设计非常严谨（特别是铁律、VerifyGate、隐私防线），但存在 hooks 冗余、状态分散、SubAgent 协作弱等问题。核心矛盾是"严格治理 vs 执行效率"的平衡。
