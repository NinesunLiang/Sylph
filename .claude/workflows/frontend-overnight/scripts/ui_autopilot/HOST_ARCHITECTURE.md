# 6h Tick-Loop Host Architecture

> 解决三个模型的共同疑问：谁在 while-tick？断线后如何续跑？6h 无人值守如何实现？

## 宿主：Claude Code Goal Session

**不是**独立 Python 进程 daemon。**是** CC 主会话 + lx-goal + ScheduleWakeup 的组合拳。

```
lx-goal activated (6h TTL)
  └── CC main session (DeepSeek V4 Pro) as orchestrator
       └── while not (goal_met | budget_exhausted | human_decision):
            ├── orchestrator.py tick() → JSON directive
            ├── CC interprets directive
            ├── Agent(flash) spawns worker → execute → return result
            ├── (escalation) Kimi K3 visual diagnosis if needed
            ├── orchestrator.py tick(result) → update state
            ├── checkpoint every 60s (state_store.save_run_state)
            └── ScheduleWakeup(120s) for heartbeat/long-poll recovery
```

## 核心循环

```
SessionStart:
  if .omc/state/tokens/lx-goal.json exists:
    → read goal + plan_dir
    → load run-state.json (orchestrator state)
    → if run_status == "running":
        → resume from last checkpoint
        → orchestrator.tick() → continue

每个 tick:
  1. orchestrator.tick() 读取当前状态
  2. 输出 JSON directive: {phase, action, task, model}
  3. CC 主会话派发 Worker:
     - task phase=L1_SHELL → prompt 只含 shell layout 约束
     - task phase=L4_ELEMENT → prompt 必须含 token 约束
     - task escalate_to_kimi → 直接调 Kimi K3 做视觉诊断
  4. Worker 返回结果 → orchestrator.tick(result)
  5. 状态更新 → checkpoint → 下一 tick

跨会话续跑:
  新会话启动 → SessionStart hook 检测 lx-goal.json
  → 读 run-state.json
  → orchestrator.tick() 从上次 checkpoint 继续
  → 无需重新 Phase 0

断线恢复:
  CC session 崩溃/超时 → ScheduleWakeup 心跳丢失
  → 用户返回新会话 → SessionStart 自动恢复
  → 状态不丢（每 60s checkpoint 持久化）
```

## 退出条件（只三类）

1. GoalMet: UIF-99 ≥ 0.99 + 全门绿 + interaction coverage = 1.0
2. BudgetExhausted: 6h wall clock or API budget exhausted
3. HumanDecisionRequired: ≤3 问题最小决策包 → 退出报告

禁止: 静默 exit / 单次 patch 失败 exit / 对话窗口关闭 exit

## 启动命令

```bash
# 首次启动
/lx-goal "UI Autopilot v2: restore {page} from prototype.
  orchestrator=.claude/workflows/frontend-overnight/scripts/ui_autopilot/orchestrator.py
  manifest=.omc/ui-autopilot/{task_id}/goal-manifest.yaml
  6h autonomous, token-frozen, hierarchy gate L0→L6, UIF-99≥0.99" 6

# 恢复已中断的 run
python3 .claude/workflows/frontend-overnight/scripts/ui_autopilot/orchestrator.py \
  --task-id "{task_id}" --action status
# → 自动加载 run-state.json, 输出当前 phase/score/directive
```

## 与 lx-goal 的关系

- lx-goal 提供: 无人值守信号(.omc/state/tokens/autonomous.active)、卡点处理、退出报告
- orchestrator 提供: 状态机、相位门禁、收敛追踪、模型路由、任务生成
- CC session 提供: Agent 调度、文件 I/O、Kimi K3 调用

三者分工: lx-goal 管"能不能做"、orchestrator 管"做什么"、CC 管"怎么做"
