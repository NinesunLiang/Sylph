# 数字资产管理内核（压缩版）

> 知识进化引擎 — 运行时事件→铁律生长管道
> 资产路径: .omc/state/ + ~/.claude/ — kernel.md 是管理员

## 架构铁律

> 完整铁律见 AGENTS.md §哲学铁律 — kernel.md 只维护增量。

- 知识管道：事件 → 计数 → 升华 → kernel.md
- 资产状态：运行时数据不可假造，不可写入 kernel.md
- 守护原则：Asset 守卫优先于功能
- **读不阻断：Read/Grep/非写Bash 永不阻断，仅敏感路径拦截**

## 资产地图

| 资产 | 用途 | 守卫 | 运行时路径 |
|:---|:---|:---|:---|
| flywheel.log | 全hook事件流 (CSV格式) | flywheel_report SessionStart | `~/.claude/flywheel.log` (HOME) |
| 蛇形命名(snake-case) | hook/script命名规范 | 一致性检查 | — |

## 架构铁律

执行前快速复核——8条核心铁律（完整版见 AGENTS.md）：
1. 禁止编造、2. 用户裁定、3. 证据门禁、4. Git门禁
5. 范围锁定、6. 隐私防线、7. 断言真实、8. 哲学先行

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
- **After**: context-compressor.sh→context-cache.md(铁律/反模式/架构压缩) | inject-project-knowledge [注: 此机制在 v7.x 评估 ROI 不足，已移除 — 见 clean-dead-code-20260721].sh→todo-queue.md+session-handoff.md(Feature/进度/决策)+session-dump.json摘要

## E1/E2 逃逸

- **E1**: Bash含治理文件路径(harness.yaml, settings.json, kernel.md, anti-patterns.md, index.md, claude-next.md, AGENTS.md等)→governance-audit.jsonl→自动补丁
- **E2**: Bash含CAPTCHA标记(sensitive-approved/permission-required等)→error-dna.jsonl→自动补丁

## 置信度管道

输出必须带置信度标记：
| 标记 | 含义 | 使用条件 |
|:---|:---|:---|
| [已验证:file:line] | 断言有源码/输出证据 | 引用具体文件+行号 |
| [已测试:命令+输出] | 实际运行验证过 | 附命令和结果摘要 |
| [推断,待确认] | 推理，未经证实 | 所有非验证断言 |

## 运行模式

- **无人**: goal/ghost/rpe → L4权限/风险→记录跳过 | **有人**: ToDo/Task-spec/标准 → L4穿透到人
- **模式选择**: L2+ 任务先过 `docs/technical/cn/execution-mode-matrix.md` 选 race / stepwise / direct
  - race（并行）: MECE 分解 ≥3 同构子任务 → `race-tool.py` 文档驱动
  - stepwise（串行）: 有依赖/根因不明/跨模块 → 每步验证
  - direct: 单文件小改 → 直接执行+证据门禁
- Skill body.md强制执行: PreToolUse:Skill自动注入, PostToolUse:Skill审计合规
