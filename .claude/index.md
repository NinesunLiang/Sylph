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
| hooks/ | `@.claude/hooks/index.md` | CC 治理 Hook 脚本（34个，按触发点分类） |
| nodes/ | `@.claude/nodes/README.md` | 最小公共节点（12个，按功能/频率分类） |
| schemas/ | `@.claude/schemas/README.md` | 公共接口定义（atomic/contract/input/output） |
| references/ | `@.claude/references/index.md` | 公共资源文档（adr/design-docs/templates/race） |
| scripts/ | `@.claude/scripts/index.md` | 治理工具脚本（40+，按功能分 6 组 + lib/ 子模块） |
| rules/ | `@.claude/rules/index.md` | 语言与工具行为规则（2个） |
| profiles/ | `@.claude/profiles/index.md` | 项目语言 profile（6种语言，各含独立 harness.yaml） |
| skills/ | `@.claude/skills/index.md` | AI agent skills（按 category 分组） |
| workflows/ | `@.claude/workflows/index.md` | 工作流定义（2个）+ 基础设施 hook（4个） |

### `.omc/` — 运行时任务状态

| 房间 | 入口 | 功能 |
|------|------|------|
| tokens/ | `@.omc/tokens/index.md` | 运行时令牌（78个，按日期分目录） |
| tasks/ | `@.omc/tasks/index.md` | 任务文档系统（534个文件，按日期/任务组织） |
| state/ | `@.omc/state/index.md` | 运行时状态（lifecycle/hud/error-dna/snapshots） |
| archive/ | `@.omc/archive/index.md` | 归档任务快照（19个） |
| audit/ | `@.omc/audit/index.md` | 审计日志 JSONL（按日分片） |
| knowledge/ | `@.omc/knowledge/index.md` | 升华管道数据 |
| plans/ | `@.omc/plans/index.md` | 历史计划文档 |
| metrics/ | `@.omc/metrics/index.md` | 基准测试报告 |

## 路由规则
**默认 L1。** 当条件满足任意 L2 触发点时 → L2。

| 层级 | 路由 | 说明 |
|------|------|------|
| L1 | 默认路径 | 日常开发、单文件修复、文档更新 |
| L2 | 跨系统 / 不可逆 / 安全权限 / 发布 / 长时间无人 | 启用 Oracle + 水位 + 降级 |

## 工作流路由

| 场景 | 路径 | 入口 |
|------|------|------|
| 状态管理 | `kernel.md` → 管理内核 | 冻结 / 飞轮 / 降级 |
| 完整生命周期 | `.claude/scripts/carros_base.py` | init→tick→verify→archive |
| L1 快速任务 | `carros_base.py` | init→verify→archive |
| L2 复杂任务 | `carros_base.py` + 条件 Oracle | 含水位+Oracle+降级 |

## Hook 路由

| 触发点 | 注册位置 | 说明 |
|--------|----------|------|
| 统一门禁 | `.claude/settings.json` → `hooks.PreToolUse` | pretool-gate.py（G1-G6），每工具调用前自动执行 |
| Hook 调度 | `.claude/hooks/hook-launcher.py` | 从 settings.json 按名启动具体 hook |

## 脚本快速索引

| 脚本 | 用途 |
|------|------|
| `carros_base.py` | 主入口（init/status/tick/verify/archive/lint） |
| `omc_lint.py` | 7 项代码规范检查 |
| `verify_gate.py` | 完成验证门禁 |
| `lib/tool_store.py` | 工具结果落盘（Phase 0 S4） |
| `lib/error_dna.py` | Error DNA 自动生成与 Retry Gate（Phase 1） |
| `lib/oracle_gate_light.py` | Oracle 条件接入（Phase 1，同级模型） |
| `lib/water_level.py` | 三段式水位运行时（Phase 1，已接入） |
| `lib/phase3_oracle.py` | 双审判官独立 Context 裁决（Phase 3） |

> 完整脚本列表见 `.claude/scripts/` 目录。docs/carros/reviews/ 为审核参考材料，默认禁止入模。

## 架构决策记录

`.claude/references/adr/INDEX.md` — 架构决策索引（手动管理）。

