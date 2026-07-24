# CarrorOS 架构地图 — round7 评审参照

> 供机制设计时落地参照。路径以仓库根为基准。

## 一、Hook 链(`.claude/settings.json` 注册，全部 `$CLAUDE_PROJECT_DIR` 锚定)

| 事件 | 入口 | 职责 |
|---|---|---|
| PreToolUse | hook-launcher.sh → pretool-gate.py | 6 道闸：任务状态/plan 存在/编辑越界/VerifyGate/水位/明文密钥；关键门 fail-closed |
| PreToolUse | hook-launcher.sh → carroros-night-deny.py | 夜间危险命令拒绝 |
| UserPromptSubmit | pretool-user-approve.py | 实测水位(读 transcript usage) → 写 state + 回写 token;goal 模式检测 |
| PostToolUse | posttool-gate.py | 工具后检查 |
| SessionStart | session-start.py | 注入 token 摘要+handoff;staleness 守卫(超 24h 标 STALE) |
| Stop | stop-lifecycle-wrapper.sh | 飞轮学习/生命周期 |
| PreCompact | precompact-lifecycle.py | compact 前写 handoff |
| SubagentStop | subagent-stop-lifecycle.py | 子代理生命周期 |
| SessionEnd | session-end-lifecycle.py | 会话收尾 |
| statusLine | statusline-command.sh | 状态条 |

hook-launcher.sh: `$0` 自锚定切项目根；关键 hook 缺失 = fail-closed 阻断。

## 二、脚本树(单源：`.claude/scripts/`,`.omc/scripts/` 侧为 symlink 或运行时)

- `carros_base.py` — L1 工作流核心：init/status/tick/report/verify/archive/lint/bench
- `lib/` — water_level(可控预算水位 A)/flywheel(飞轮)/error_dna(失败分类)/autonomy/handoff_writer/hot_card/oracle_gate_light/phase3_oracle/tool_store
- `context_watermark.py` — 上下文水位 B(50/70/80，只读/全阻/强制 compact)
- `temp-bypass.py` — 60min 全门降级授权(自过期，人类执行)
- `archived/` — 死模块归档(如 fallback_matrix)
- `.claude/skills/lx-goal/scripts/lx-goal.py` — 目标驱动无人值守模式(物理锁/裁决链/退出报告)

## 三、状态机与存储

| 路径 | 内容 |
|---|---|
| `.omc/tokens/{YYYYMMDD}/{task}.json` | 任务物理锁；**选择器按 mtime 取最新**(已知缺陷，见 dossier 附录) |
| `.omc/tasks/{YYYYMMDD}/{task}/` | plan.md(scope 冻结)/executor.md(证据)/research.md/handoff.md |
| `.omc/state/` | token.json(全局指针)/context-watermark.json(活水位)/temp-bypass.json |
| `.omc/knowledge/` | 飞轮沉淀(claude-next.md 等) |
| `.claude/references/` | anti-patterns.md(自动升华)/omc-path-conventions.md/context-watermark.md |
| `.claude/audit`、`.omc/state/audit` | VerifyGate 双绑定审计 |

## 四、回归 battery(`scripts/run-regression.sh` 一键)

| 套件 | 用例 | 覆盖 |
|---|---|---|
| test-context-watermark.py | 25 | 水位 B 三段策略 |
| test-oracle-gate.py | 31 | oracle 对抗审核 |
| test-verify-gate.py | 20 | VerifyGate 双绑定 |
| test-goal-mode-gate.py | 12 | goal 模式降级/恢复 |
| test-hook-launcher.sh | — | launcher 自锚定/fail-closed |
| test_pkg_c_lifecycle.py | — | 生命周期 pkg |

注意：活体 state(temp-bypass/watermark ≥70%)会污染测试，脚本自带 stash+trap 还原。

## 五、冻结与人类专属

- 冻结文档(铁律 6): `AGENTS.md` / `.claude/kernel.md` / `.claude/index.md` — 变更须人类
- 官方分账： `improve_plan/CarrorOS_second_time/scorecard.md` — AI 不动，人类并账
- 历史轮次： round3(三模型)/round4(终审)/round5(8.42→8.59)/round6(8.65→8.70)
