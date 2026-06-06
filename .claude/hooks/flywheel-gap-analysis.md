# Flywheel 埋点缺口分析

## 分析范围
13 个 hook 源码中完全无 `flywheel_event()` 调用。评估是否值得补充。

## 分析规则
- `flywheel_event(hook, event, severity, detail)` 记录有意义的行为（阻断/告警/检测命中）
- **不**记录每次被动调用 → 避免 P3/L0 垃圾数据淹没 flywheel.log
- 记录阈值: 阻断(P0/P1) | 告警命中(P1/P2) | 重要成功事件(L0/L1)

---

## 1. inject-project-knowledge.sh
- **类型**: Injector | SessionStart
- **功能**: 注入 todo-queue.md / session-handoff.md / session-dump.json / handoff-v2.json 的记忆恢复
- **特征**: 只读检查文件存在性后 echo 到 stdout；无阻断/无告警/无检测命中
- **分析**: 纯粹的被动数据注入器。每次 SessionStart 都会运行，但"注入成功"不是有意义的业务事件。file-not-found 是正常状态（新项目无历史 handoff），不构成告警。
- **建议**: ❌ **Delete（不补充）** — passive injector，无业务语义事件可记录

## 2. lsp-gate.sh
- **类型**: Gate | SessionStart
- **功能**: 检测项目语言的 LSP 是否安装；缺失 → 注入提醒
- **特征**: 唯一的"动作点"是缺失 LSP 时注入 additionalContext 提醒
- **分析**: LSP 缺失是一个值得追踪的事件 — 反映开发者环境不完整，是 onboarding 质量指标
- **建议**: ✅ **Keep** — 在 `[ -n "$MISSING" ]` 分支加 `flywheel_event "lsp_gate" "lsp_missing" "P2" "$MISSING"`

## 3. oracle-gate.sh
- **类型**: Gate | SessionStart
- **功能**: 检测 Agent 独立进程能力（claude/opencode/gh CLI）
- **特征**: 无 Agent 能力 → 注入降级警告
- **分析**: Agent 不可用是重要的运维事件，影响 Oracle 审核质量。但对每个 SessionStart 都记录"可用"无意义。
- **建议**: ✅ **Keep** — 在 `! $CAN_AGENT` 分支加 `flywheel_event "oracle_gate" "agent_unavailable" "P2"`

## 4. posttool-output-compressor.sh
- **类型**: Monitor | PostToolUse
- **特征**: 此文件存在于 hooks/ 目录但 **settings.json 未注册**。实际注册的是 posttool-output-compressor.py（通过 settings.json 间接调用，但 settings 中实际无此 hook 条目）
- **功能**: 压缩 Read/Bash 输出以减少 token 消耗
- **分析**: 压缩是纯被动操作，每次 Read/Bash 都会触发。有"压缩后字符数"等指标但没有显著阻断/告警点。且此 hook 未激活。
- **建议**: ❌ **Delete（不补充）** — 未激活 + 操作本质是 passive 预处理

## 5. posttool-workflow-checkpoint.sh
- **类型**: Monitor | PostToolUse:TaskUpdate
- **特征**: `.claude/hooks/` 版本，但 **settings.json 注册的是 `workflow-standard/hooks/checkpoint`**，后者已有 flywheel_event
- **功能**: 检测 TaskUpdate 中的 [CHECKPOINT:xxx] 标记并推进 workflow-state.json
- **分析**: 此文件的已激活等价物（workflow-standard/hooks/checkpoint line 43）已有 `flywheel_event "workflow_checkpoint" "$CP" "L1" "checkpointed"`。此文件是遗留副本，不会被调用。
- **建议**: ❌ **Delete（不补充）** — 挂起的遗留文件，激活版已覆盖埋点

## 6. pretool-cruise-check.sh
- **类型**: Gate | SessionStart/PreToolUse
- **特征**: 注册在 settings.json UserPromptSubmit 下（line 507）
- **功能**: 检测 ghost/goal 巡航模式基础设施是否完整。若 `.cruising` 缺失 → 提醒创建；若 feature/ 缺失 → 自动创建
- **分析**: 巡航基础设施缺失是一个值得追踪的运维事件。自动创建 feature/ 目录是重要的行为。
- **建议**: ✅ **Keep** — 两个动作点:
  - `.cruising` 缺失告警 → `flywheel_event "cruise_check" "cruising_missing" "P2" "$MODE"`
  - 自动创建 feature/ 目录 → `flywheel_event "cruise_check" "feature_dir_created" "L1"`

## 7. pretool-python-bridge.sh
- **类型**: Bridge | UserPromptSubmit
- **特征**: 注册在 settings.json line 599，调用 `scripts/pretool-python-bridge.sh context-inject`
- **功能**: 桥接 CC hooks → Python 脚本，确保跨平台 python3 可用
- **分析**: 纯粹的调用桥接层。无业务逻辑、无阻断、无告警。python3 不可用场景是 exit 1（pipeline 错误）。
- **建议**: ❌ **Delete（不补充）** — 基础设施桥接，无业务语义事件

## 8. pretool-skill-version-guard.sh
- **类型**: Guard | PreToolUse:Edit|Write
- **特征**: 注册在 settings.json line 36
- **功能**: 拦截硬编码版本号写入 SKILL.md；检查 @references 指向的文件是否存在
- **分析**: **高价值埋点**。版本合规门禁有清晰的阻断/警告边界：
  - 硬编码版本阻断(P1) → 应记录
  - @references 指向不存在文件(P2) → 应记录
- **建议**: ✅ **Keep** — 两个动作点:
  - `exit 2` 阻断后 → `flywheel_event "skill_version_guard" "hardcoded_version_blocked" "P1"`
  - `BAD_REFS` 非空警告 → `flywheel_event "skill_version_guard" "ref_not_found" "P2"`

## 9. pretool-workflow-gate.sh
- **类型**: Gate | PreToolUse:Edit|Write|Bash
- **特征**: `.claude/hooks/` 版本，但 **settings.json 注册的是 `workflow-standard/hooks/pretool-workflow-gate`**，后者无 flywheel_event
- **功能**: 阻断超越当前工作流阶段的编辑/写入/操作。多种阻断场景：
  - Stage=planning/gate1 → BLOCKED
  - Stage=executing 但文件不在约束矩阵 → BLOCKED
  - Stage=gate2/gate3 → PAUSED
- **分析**: **高价值埋点**。每个阻断点都是 P0/P1 级别的重要治理事件。workflow-standard 版本也无埋点。
- **建议**: ✅ **Keep（补充到激活版本）** — 应在 `workflow-standard/hooks/pretool-workflow-gate` 中补：
  - planning/gate1 阻断 → `flywheel_event "workflow_gate" "planning_block" "P0"`
  - 约束矩阵越界阻断 → `flywheel_event "workflow_gate" "constraint_block" "P0"`
  - gate2/gate3 暂停阻断 → `flywheel_event "workflow_gate" "gate_pause" "P1"`
- ⚠️ 此 `.claude/hooks/` 版本是旧的，应补充到 workflow-standard 版本

## 10. sessionstart-workflow-inject.sh
- **类型**: Injector | SessionStart
- **特征**: `.claude/hooks/` 版本，**settings.json 注册的是 `workflow-standard/hooks/session-inject`**，后者 line 63 已有 `flywheel_event "workflow_session" "injected" "L0" "stage=$STAGE"`
- **功能**: 检测活跃工作流并注入结构化上下文
- **分析**: 激活版本已有 flywheel_event。此文件是遗留副本。
- **建议**: ❌ **Delete（不补充）** — 挂起的遗留文件，激活版已覆盖埋点

## 11. thinking-gate.sh
- **类型**: Gate | UserPromptSubmit
- **特征**: 注册在 settings.json line 589，matcher: `.*`
- **功能**: 检测 thinking/reasoning 内容泄漏到用户消息中
- **分析**: **高价值埋点**。THINKING_LEAK 是该 hook 唯一的业务事件。当前 hook 已有 LEAK_TYPE 检测逻辑，且有 TO_FLYWAY_WELL_TAG 但实际只 echo 到 stderr 和 `~/.hermes/cron/output/thinking-leak-events.json`，没有调用 `flywheel_event()`。
- **建议**: ✅ **Keep** — 在 `[ -n "$LEAK_TYPE" ]` 分支补充:
  - `flywheel_event "thinking_gate" "leak_detected" "P1" "$LEAK_TYPE"`

## 12. workflow-state-recovery.sh
- **类型**: Monitor | SessionStart
- **特征**: `.claude/hooks/` 版本，**settings.json 注册的是 `workflow-standard/hooks/state-recovery`**，后者 line 37 和 78 已有 flywheel_event
- **功能**: 检测 workflow-state.json 损坏或 Gate 超时，自动恢复
- **分析**: 激活版本已有 flywheel_event（corruption=P0, gate_timeout_check=L1）。此文件是遗留副本。
- **建议**: ❌ **Delete（不补充）** — 挂起的遗留文件，激活版已覆盖埋点

---

## 汇总

| # | Hook | Active? | 已有埋点? | 建议 | 优先级 | 补充事件 |
|---|------|---------|-----------|------|--------|---------|
| 1 | inject-project-knowledge.sh | ✅ | ❌ | ❌ Delete | — | passive injector，无业务事件 |
| 2 | lsp-gate.sh | ✅ | ❌ | ✅ Keep | P2 | lsp_missing |
| 3 | oracle-gate.sh | ✅ | ❌ | ✅ Keep | P2 | agent_unavailable |
| 4 | posttool-output-compressor.sh | ❌ | ❌ | ❌ Delete | — | 未激活，passive 预处理 |
| 5 | posttool-workflow-checkpoint.sh | ❌ | ❌ | ❌ Delete | — | 已由 workflow-standard/hooks/checkpoint 覆盖 |
| 6 | pretool-cruise-check.sh | ✅ | ❌ | ✅ Keep | P2/L1 | cruising_missing, feature_dir_created |
| 7 | pretool-python-bridge.sh | ✅ | ❌ | ❌ Delete | — | 基础设施桥接，无业务事件 |
| 8 | pretool-skill-version-guard.sh | ✅ | ❌ | ✅ Keep | P1/P2 | hardcoded_version_blocked, ref_not_found |
| 9 | pretool-workflow-gate.sh | ❌(旧) | ❌ | ✅ Keep(补到激活版) | P0/P1 | planning_block, constraint_block, gate_pause |
| 10 | sessionstart-workflow-inject.sh | ❌(旧) | ❌ | ❌ Delete | — | 已由 workflow-standard/hooks/session-inject 覆盖(已有埋点) |
| 11 | thinking-gate.sh | ✅ | ❌ | ✅ Keep | P1 | leak_detected |
| 12 | workflow-state-recovery.sh | ❌(旧) | ❌ | ❌ Delete | — | 已由 workflow-standard/hooks/state-recovery 覆盖(已有埋点) |

### 总结
- **值得补充**: 5 个活跃 hook（#2, #3, #6, #8, #11）+ 1 个需补充到激活版本（#9）
- **不补充**: 4 个被动/桥接 hook（#1, #4, #7）+ 3 个 legacy 副本（#5, #10, #12）
- **关键发现**: #5, #10, #12 在 `workflow-standard/hooks/` 下已有激活版本，其中 #10 和 #12 已有 flywheel_event，激活版 #9 无埋点需补充
