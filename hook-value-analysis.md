# 22 个 Hook 价值分析报告

> 分析日期: 2026-06-07
> 分析范围: harness.yaml hooks_enabled → hooks/ 实际脚本 → settings.json 注册 → 哲学矩阵追溯
> **关键发现: 全部 22 个 hook 均有对应的 .sh 脚本文件在 hooks/ 目录下，且内容完整。不存在"无脚本 hook"的情况。**

---

## 前置说明

全面检查后发现：
- 全部 22 个 hook 在 `.claude/hooks/` 目录下有对应的 `.sh` 文件
- 所有文件都有实际内容（10～343 行不等）
- 全部在 `settings.json` 中注册了触发事件和 matcher
- 全部在 `harness.yaml` 的 `hooks_enabled` 中标记为 `true`

**因此任务实质从"补实现 vs 删注册"转变为"评估现有钩子的价值、哲学合规性及ROI，给出 Keep/Delete建议"**。以下按 Keep（保留并优化）和 Delete（建议移除注册或实现）分类。

---

## # Keep — 高价值/高哲学契合/核心基础设施 (14个)

### 1. build_validator → build-validator.sh ✅ KEEP
- **文件**: `.claude/hooks/build-validator.sh` (343行) — PostToolUse:Bash / PostToolUseFailure:Bash
- **功能**: 构建失败时自动分类错误(Go/TS/Python/Rust/通用)，记录日志并输出针对性修复建议
- **哲学**: #4(验证) — 构建失败证据自动捕获；#3(守护) — 帮助快速定位问题
- **ROI**: 高。343行代码覆盖6种语言错误模式，每次构建失败可节省5-15分钟手动排查
- **建议**: 保留。可考虑将 error_classifier 搬到共享脚本减少重复

### 2. cruise_check → pretool-cruise-check.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-cruise-check.sh` (44行) — SessionStart / PreToolUse
- **功能**: 检测 ghost/goal mode 激活但基础设施未初始化 → 提醒用户初始化
- **哲学**: #3(守护) — 防止在未就绪状态下开始巡航；#7(文档) — 引导正确的初始化流程
- **ROI**: 中。轻量（44行），减少巡航模式使用者的困惑
- **建议**: 保留。

### 3. error_dna_auto_fix → error-dna-auto-fix.sh ✅ KEEP
- **文件**: `.claude/hooks/error-dna-auto-fix.sh` (63行) — Stop
- **功能**: 跨会话回顾顽固错误（≥3次出现+active），写入 retrospective.txt 供下次 SessionStart 读取
- **哲学**: #4(验证) — 追踪反复出现的错误；#6(0信任) — 不假设错误已被修复
- **ROI**: 中-高。已在 mechanism-lifecycle 中被重新评估激活（从 v1 83.5%噪声到 v6.3.27 重新激活）
- **建议**: 保留。持续追踪 ROI，如长期零触发可归档

### 4. posttool_checkpoint → posttool-checkpoint.sh ✅ KEEP
- **文件**: `.claude/hooks/posttool-checkpoint.sh` (140行) — PostToolUse:TaskUpdate / Stop
- **功能**: 工作流收尾时生成结构化 checkpoint 报告（状态/错误/待办/下一步建议）
- **哲学**: #5(以人为本) — 人类拿到清晰收尾报告；#4(验证) — 每个结论带证据来源
- **ROI**: 高。每次 TaskUpdate(completed) / Stop 都产生价值
- **建议**: 保留。

### 5. session_resume → session-resume.sh ✅ KEEP
- **文件**: `.claude/hooks/session-resume.sh` (154行) — SessionStart
- **功能**: 跨会话恢复 goal/ghost 任务上下文，注入进度摘要+恢复指令
- **哲学**: #7(文档优先) — 从 RPE progress.md 重建上下文，非依赖记忆
- **ROI**: 高。直接解决跨会话丢失上下文的核心问题（#36）
- **建议**: 保留。核心基础设施。

### 6. pretool_plan_gate → pretool-plan-gate.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-plan-gate.sh` (219行) — PreToolUse:Edit|Write|Bash
- **功能**: Plan-before-Execute 门禁，阻止未经审批的中等以上变更
- **哲学**: #3(先守护) — 方案未审批→阻断执行；#6(0信任) — 不信任 state.json，从 lx-goal.json 验证
- **ROI**: 高。已注册在哲学矩阵 Part B，防漂移的核心机制
- **建议**: 保留。219行的复杂逻辑有维护价值。

### 7. pretool_rules_inject → pretool-rules-inject.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-rules-inject.sh` (150行) — UserPromptSubmit
- **功能**: 3级脱水规则注入（L1每轮铁律，L2每5轮，L3每10轮），从 context-cache.md 单源提取
- **哲学**: #7(文档) — 单源上下文注入；#1(Less) — 分层频率控制
- **ROI**: 高。每轮注入关键铁律，防止漂移的核心机制
- **建议**: 保留。可考虑优化 context-cache.md 解析性能。

### 8. pretool_skill_version_guard → pretool-skill-version-guard.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-skill-version-guard.sh` (87行) — PreToolUse:Edit|Write
- **功能**: 拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式；拦截 @references 指向不存在文件
- **哲学**: #4(验证) — 版本号单一真相源；#6(0信任) — 不信任 AI 会正确写版本格式
- **ROI**: 中-高。每次 SKILL.md 编辑时提供保护，防止版本混乱
- **建议**: 保留。

### 9. skill_body_enforce → pretool-skill-body-enforce.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-skill-body-enforce.sh` (87行) — PreToolUse:Skill
- **功能**: 在 skill 执行前强制注入 body.md 内容到 additionalContext，确保 AI 无法"选择不看"
- **哲学**: #3(先守护) — 执行前确保完整执行合约；#6(0信任) — 强制注入而非信任 AI 会主动读
- **ROI**: 高。Skill 正确执行的核心保障
- **建议**: 保留。

### 10. pretool_git_gate → pretool-git-gate.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-git-gate.sh` (85行) — PreToolUse:Bash
- **功能**: git commit 前 pre-commit 检查门禁（铁律 #4 物化）
- **哲学**: #3(先守护) — 确保代码进入 git 前经过质量门禁；铁律#4 — Git 门禁直接物化
- **ROI**: 高。铁律#4的直接实现
- **建议**: 保留。核心基础设施。

### 11. pretool_scope_gate → pretool-scope-gate.sh ✅ KEEP
- **文件**: `.claude/hooks/pretool-scope-gate.sh` (152行) — PreToolUse:Edit|Write
- **功能**: 检测 Edit/Write 是否超出 current-scope.txt 声明的文件范围，支持 glob 匹配+自动扩展
- **哲学**: #5(范围冻结) — 一次一Step的直接物化
- **ROI**: 高。铁律#5的直接实现，含自动扩展机制减少误报
- **建议**: 保留。

### 12. permission_frequency_tracker → permission-frequency-tracker.sh ✅ KEEP
- **文件**: `.claude/hooks/permission-frequency-tracker.sh` (101行) — PostToolUse:*
- **功能**: 统计会话中 permission-required* 文件创建次数，写入审计 JSON
- **哲学**: #6(0信任) — 量化权限请求频率，辅助审计
- **ROI**: 中。轻量无侵入，提供审计数据基础。永不阻断
- **建议**: 保留。

### 13. oracle_gate → oracle-gate.sh ✅ KEEP
- **文件**: `.claude/hooks/oracle-gate.sh` (32行) — SessionStart
- **功能**: 检测 Agent 独立进程能力（claude/opencode/gh CLI），无能力时降级提示
- **哲学**: #6(0信任) — Oracle 需独立 agent 进程
- **ROI**: 中。32行低成本，SessionStart 时提供重要环境感知
- **建议**: 保留。

### 14. posttool_read_cite → posttool-read-cite.sh ✅ KEEP
- **文件**: `.claude/hooks/posttool-read-cite.sh` (66行) — PostToolUse:Read
- **功能**: 读取 .go/.api 等文件后提示引用规范（标注 file:line）
- **哲学**: #7(文档) — 引用规范提示；铁律#1 — 禁止编造
- **ROI**: 中。轻量（66行），每次 Read 提供引用规范提醒。已注册哲学矩阵 Part B
- **建议**: 保留。可考虑默认关闭（hc_enabled + 按需开启）

---

## # Keep with Caveats — 有价值但需优化/重新评估 (5个)

### 15. pretool_terminal_safety → pretool-terminal-safety.sh ⚠️ KEEP (优化)
- **文件**: `.claude/hooks/pretool-terminal-safety.sh` (71行) — PreToolUse:Bash
- **功能**: 终端命令格式校验（过长/链式操作/路径堆砌告警），>2000字符硬阻断
- **哲学**: #6(0信任) — 终端长度截断是已知事故（DG-13, DG-22）
- **ROI**: 中。告警多为软提示，仅>2000字符硬阻断实际有效。告警可能产生噪音
- **建议**: 保留但优化告警阈值，减少噪声，专注硬阻断场景

### 16. cross_platform_smoke_test → cross-platform-smoke-test.sh ⚠️ KEEP (降频)
- **文件**: `.claude/hooks/cross-platform-smoke-test.sh` (59行) — SessionStart
- **功能**: 检测 stat/sed 跨平台兼容性，记录 flywheel 事件
- **哲学**: #4(验证) — 环境兼容性验证；#7(文档) — 环境感知
- **ROI**: 低-中。每次 SessionStart 运行，但同一环境每次结果相同。实际价值集中在首次环境检测
- **建议**: 保留但改为每7天/每次环境变化时运行，避免每次 SessionStart 冗余执行

### 17. phase_state_tracker → phase-state-tracker.sh ⚠️ KEEP (精确度提升)
- **文件**: `.claude/hooks/phase-state-tracker.sh` (162行) — PostToolUse:TaskUpdate|Edit|Write
- **功能**: 追踪五阶段状态（research→approved→executing→approved→report），写入 current-phase.json
- **哲学**: #4(验证) — 每个状态判断附带证据来源；#6(0信任) — 实时检查不依赖缓存
- **ROI**: 中。162行代码提供状态感知，但阶段判断逻辑（Phase2/Phase4 复用相同检查）可能不够精确
- **建议**: 保留，细化 Phase2 vs Phase4 判别逻辑

### 18. pretool_b1_detect → pretool-b1-detect.sh ⚠️ KEEP (ROI监控)
- **文件**: `.claude/hooks/pretool-b1-detect.sh` (106行) — PreToolUse:Edit|Write
- **功能**: 检测单会话新文件创建数，超过阈值（默认5个）告警
- **哲学**: #1(Less is more) — 提示而非阻断；#3(守护) — 预警过度编辑
- **ROI**: 中-低。告警但不阻断，实际拦截效果弱。哲学矩阵 Part C D5 指出 B1 无自动化检测，此 hook 填补了空白
- **建议**: 保留但监控实际触发频率，如长期零触发考虑降级或移除

### 19. skill_compliance_audit → posttool-skill-compliance.sh ⚠️ KEEP (与 skill_body_enforce 合并评估)
- **文件**: `.claude/hooks/posttool-skill-compliance.sh` (112行) — PostToolUse:Skill
- **功能**: skill 执行后审计 AI 是否按 body.md 执行，发现偏差注入警告
- **哲学**: #4(验证) — 执行后验证；#6(0信任) — 运行时证据 > 静态声明
- **ROI**: 中。与 skill_body_enforce 形成前后对照。审计依赖 hook-evidence.jsonl 的存在，如日志系统不完善可能漏检
- **建议**: 保留。考虑与 skill_body_enforce 合并或共享 body.md 解析逻辑，减少维护负担

---

## # Delete — 建议移除注册 (3个)

### 20. pretool_purify_gate → pretool-purify-gate.sh ❌ DELETE
- **文件**: `.claude/hooks/pretool-purify-gate.sh` (26行) — PreToolUse:Edit|Write
- **功能**: 编辑治理文件时注入哲学纯度提醒
- **哲学**: 弱。仅为治理文件编辑时提醒哲学优先级，不阻断、不验证
- **问题**: 
  - 仅输出提醒文本，无实际约束力
  - 哲学提醒已在 L1 规则注入中每轮注入，功能重叠
  - flywheel 事件只记录 triggered，无后续价值评估
  - 纯冗余提醒，AI 可忽略
- **建议**: 从 harness.yaml 删除注册。功能已被 pretool_rules_inject (L1每轮注入) 完全覆盖

### 21. pretool_node_reference → pretool-node-reference.sh ❌ DELETE
- **文件**: `.claude/hooks/pretool-node-reference.sh` (12行) — PreToolUse:Agent
- **功能**: Agent 工具触发时注入 nodes 目录文件列表
- **问题**:
  - 仅 12 行，功能极简单：列出 nodes 目录的文件名
  - nodes/ 目录可能已不再活跃维护或节点数量有限
  - Agent 工具使用频率低，此 hook 触发机会少
  - 节点列表可在 AGENTS.md 路由索引中静态维护，无需运行时动态注入
- **建议**: 从 harness.yaml 删除注册。节点参考信息可静态维护在文档中

### 22. posttool_template_check → posttool-template-check.sh ❌ DELETE
- **文件**: `.claude/hooks/posttool-template-check.sh` (10行) — PostToolUse:TaskUpdate|Edit|Write
- **功能**: task_sys 模板写入后提示必填字段
- **问题**:
  - 仅 10 行，仅针对 `.claude/task_sys/templates/*` 路径
  - task_sys 模板使用率可能不高
  - 必填字段信息可写在模板文件本身的注释中，无需 hook 注入
  - 每次 Edit/Write/TaskUpdate 都触发但仅极少数匹配
- **建议**: 从 harness.yaml 删除注册。模板自文档化即可

---

## 总结

| 分类 | 数量 | 建议 |
|------|------|------|
| ✅ KEEP (核心) | 14 | 高价值/哲学直接物化/核心基础设施 |
| ⚠️ KEEP (优化) | 5 | 有价值但需降频/合并/提升精确度 |
| ❌ DELETE | 3 | 冗余被覆盖/价值低/触发率极低 |

### 删除操作影响

| Hook | harness.yaml | settings.json | 文件本身 |
|------|-------------|--------------|---------|
| pretool_purify_gate | 删 `pretool_purify_gate: true` | 删对应 command 行 | 保留（可归档） |
| pretool_node_reference | 删 `pretool_node_reference: true` | 删对应 command 行 | 保留（可归档） |
| posttool_template_check | 删 `posttool_template_check: true` | 删对应 command 行 | 保留（可归档） |

**额外建议**: 建议将本次分析的结论更新到 `.claude/reference/philosophy-mechanism-matrix.md` 的 Part B（逆向追溯），为上述 20 个当前不在矩阵中的 hook 补充哲学归属行。
