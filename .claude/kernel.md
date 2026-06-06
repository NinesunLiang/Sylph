# 数字资产管理内核（压缩版）

> 知识进化引擎 — 运行时事件→铁律生长管道
> 资产路径: .omc/state/ + ~/.claude/ — kernel.md 是管理员

## 资产地图

| 资产 | 用途 | 守卫 |
|:---|:---|:---|
| flywheel.log | 全hook事件流 | flywheel_report SessionStart |
| error-dna.jsonl | E2验证码伪造 | 归档轮转 >1MB |
| governance-audit.jsonl | E1治理绕过 | 无自动清理 |
| error-signals.jsonl | 普通Bash错误 | 7天/512KB清空 |
| retry-budget.json | signature重试计数 | 3轮上限 |
| escape-patches.json | E1/E2自动修复建议 | 30d过期 |
| claude-next.md | 用户纠正→DG教训(58条) | >40条告警 |

## 管道: 事件→教训→规则→铁律

**Phase1 采集**: 每个hook → flywheel_event → flywheel.log | error-dna.sh拦截PostToolUse:Bash+Failure → 隐私脱敏/签名/分类/E1E2逃逸检测

**Phase2 感知**: flywheel-report.sh(SessionStart) P0≥5次+未ack→报告+通知 | error-dna高频扫描 signature≥5→session告警 | 逃逸E1/E2→即时写入additionalContext

**Phase3 记录**: pretool-user-correction(UserPromptSubmit)检测纠正信号→DG-[N]骨架到claude-next.md | Agent补充根因后hits+1

**Phase4 升华**: knowledge-condenser.sh(Stop)扫描hits≥2→阈值(hits5+age10d→kernel, hits3+age7d→kernel, hits3+age5d→建议) | >40条→清理告警

**Phase5 生长**: 极稳定kernel规则→候选铁律→Boss仲裁

## Compact 记忆恢复

- **Before**: stop-drain.sh→extract-compact-memory.py→todo-queue.md(最近20询问+任务摘要)
- **After**: context-compressor.sh→context-cache.md(铁律/反模式/架构压缩) | inject-project-knowledge.sh→todo-queue.md+session-handoff.md(Feature/进度/决策)+session-dump.json摘要

## E1/E2 逃逸

- **E1**: Bash含治理文件路径(harness.yaml, settings.json, kernel.md, anti-patterns.md, index.md, claude-next.md, AGENTS.md等)→governance-audit.jsonl→自动补丁
- **E2**: Bash含CAPTCHA标记(sensitive-approved/permission-required等)→error-dna.jsonl→自动补丁

## 运行模式

- **无人**: goal/ghost/rpe → L4权限/风险→记录跳过 | **有人**: ToDo/Task-spec/标准 → L4穿透到人
- Skill body.md强制执行: PreToolUse:Skill自动注入, PostToolUse:Skill审计合规
