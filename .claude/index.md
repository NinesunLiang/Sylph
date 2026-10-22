# index.md — 渐进式披露路由表

> 指向 `.claude/` 下的可复用资产和 `.omc/` 下的运行时任务

## 模块索引

## 模块路由 — 宫殿地图

> 一级路由：`.claude/index.md` = 宫殿地图（房间位置）
> 每个模块下的 `index.md` = 房间内地图（资源位置）

## AI 使用守则

> **不要全量加载** —— 先从本表判断需要哪个房间，再 `@.claude/{房间}/index.md`
> 加载房间内地图。看了地图后，按需 `@` 加载具体文件。
>
> **不要在不看地图的情况下直接猜文件路径** —— 每个房间的 index.md
> 就是你的导航图，先读地图再行动。
>
> **不要一次性遍历整个目录** —— 不知道路径时先看 index.md。

| 房间 | 入口 | 功能 |
|------|------|------|
| hooks/ | `@.claude/hooks/index.md` | CC 治理 Hook 脚本（按触发点分类；注册表以 settings.json 和 pretool-gate.py 为准） |
| nodes/ | `@.claude/nodes/README.md` | 最小公共节点（13 个节点文件：10 通用 + a/b terminal + orchestrator 路由） |
| schemas/ | `@.claude/schemas/README.md` | 公共接口定义（atomic/contract/output） |
| references/ | `@.claude/references/index.md` | 公共资源文档（adr/archived/design-docs/templates）；references 为唯一真源，大编号优先（ADR0017） |
| ~~error_rulers/~~ | 已随 error-dna 于 index48 移除（2026-09-10） | — |
| scripts/ | `@.claude/scripts/index.md` | 治理工具脚本（按功能分 6 组 + lib/ 子模块） |
| rules/ | `@.claude/rules/index.md` | 语言与工具行为规则（3个：bash-style / terminal-safety / external-knowledge） |
| skills/ | `@.claude/skills/index.md` | AI agent skills（10 个 lx-* 扁平布局） |
| workflows/ | `@.claude/workflows/index.md` | 工作流（front-stepwise 起源 + frontend-overnight UI 还原） |

### `.omc/` — 运行时任务状态

| 房间 | 入口 | 功能 |
|------|------|------|
| tokens/ | `.omc/tokens/`（运行时生成，无 index.md） | 运行时令牌（按日期分目录，数量随任务增减不写死） |
| tasks/ | `@.omc/tasks/index.md` | 任务文档系统 — 唯一入口 |
| state/ | `@.omc/state/index.md` | 运行时状态（lifecycle/hud/snapshots/oracle） |
| archive/ | `@.omc/archive/index.md` | 归档任务快照 |
| audit/ | `@.omc/audit/index.md` | 审计日志 JSONL（机器自决事件，按日分片） |
| decisions/ | `.omc/decisions/DECISIONS.md` | AI 治理决策日志（人类裁决，时间正序，append-only；不入库） |
| knowledge/ | `@.omc/knowledge/index.md` | 升华管道数据 |
| metrics/ | `@.omc/metrics/index.md` | 基准测试报告 |

## 路由规则

任务只有三条合法路径：

| 路径 | 适用情况 | 必做流程 |
|------|----------|----------|
| L1 simple | ≤3 个文件、单步、无跨模块依赖、可逆 | 读必要文件 → 实现 → 测试 → 报告；不创建任务文档 |
| L1 light | 需要留痕但不触发 L2 | `init --light` → 写 EV → light verify；不要求完整 Research/Oracle |
| L2 non-light | 跨模块、不可逆、安全/权限、发布、架构调整或长期无人 | `init --level L2` → research/plan → tick → TDD → VerifyGate=VERIFIED → archive |

安全、权限、架构和不可逆操作直接进入 L2；不能因为“改动文件少”降级。

## 工作流路由

| 场景 | 路径 | 入口 |
|------|------|------|
| 状态管理 | `kernel.md` → 管理内核 | 冻结 / 飞轮 / 降级 |
| L1 simple | 人工快速路径 | 不调用 carros_base 生命周期 |
| L1 light | `.claude/scripts/carros_base.py` | `init --light` → EV → verify |
| L2 non-light / goal | `.claude/scripts/carros_base.py` | `init --level L2` → tick→verify→archive |

## Hook 路由

| 触发点 | 注册位置 | 说明 |
|--------|----------|------|
| 统一门禁 | `.claude/settings.json` → `hooks.PreToolUse` | hook-launcher 合并 spawn（ADR0016）：pretool-gate.py（门禁集单一真源＝该文件 `_GATE_CORE`，14 道；oracle 退役观察区）+ carroros-night-deny.py + pretool-scorecard-gate.py（v2 路径预检）+ pre-completion-gate.py |
| Hook 调度 | `.claude/hooks/hook-launcher.py` | 从 settings.json 按名启动具体 hook；支持单次 spawn 串行执行多 hook |

## 脚本快速索引

| 脚本 | 用途 |
|------|------|
| `carros_base.py` | 主入口（init/status/tick/verify/archive/lint） |
| `omc_lint.py` | 7 项代码规范检查 |
| `verify_gate.py` | 完成验证门禁 |
| `lib/oracle_gate_light.py` | Oracle 条件接入（Phase 1，同级模型） |
| `lib/phase3_oracle.py` | 双审判官独立 Context 裁决（Phase 3） |

> 完整脚本列表见 `.claude/scripts/` 目录。docs/carros/reviews/ 为审核参考材料，默认禁止入模。

## 架构决策记录

`.claude/references/adr/INDEX.md` — 架构决策索引（单一真源，数量以 INDEX.md 为准；`references/index.md` 不再复述条目清单）。

