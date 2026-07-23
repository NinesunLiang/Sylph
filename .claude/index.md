# index.md — 渐进式披露路由表

> 指向 `.claude/` 下的可复用资产和 `.omc/` 下的运行时任务

## 模块索引

### `.claude/` — 公共可复用资产（删除即丢失治理能力）

| 目录 | 用途 | 内容结构 |
|------|------|---------|
| `hooks/` | CC 治理 hook 脚本 | 每个 hook 一个 `.py` 文件，配套 `harness_core.py` / `harness_lib.py` 共享库 |
| `nodes/` | 最小公共节点 | 每个节点一个 `.md`，按 `decisions/` `judgments/` 等子目录分类 |
| `schemas/` | 公共接口定义 | `atomic/`（基本类型） `contract/`（契约） `input/`（输入） `output/`（输出） |
| `references/` | 公共资源文档 | `adr/` `design-docs/` `templates/` `race/` 等子目录 |
| `scripts/` | 治理工具脚本 | 核心引擎（`carros_base.py` `oracle_engine.py` 等）+ `lib/` 子模块 |
| `rules/` | 语言/工具规则 | 每个规则一个 `.md`（如 `bash-style.md` `terminal-safety.md`） |
| `profiles/` | 项目语言 profile | 每种语言一个子目录（`python/` `go/` `rust/` `node/` `base/`），各含 `harness.yaml` |
| `skills/` | AI agent skills | 按 category 子目录分组（`carroros/` `devops/` `software-development/` 等） |
| `workflows/` | 工作流定义+基础设施 | 具体工作流（`front-stepwise/` `frontend-overnight/`）+ `hooks/` 通用基础设施 |

### `.omc/` — 运行时任务状态（删除不影响治理能力）

| 目录 | 用途 |
|------|------|
| `tokens/` | 运行时令牌（每任务一个 `.json`，含步骤状态） |
| `tasks/` | 运行时任务文档系统（`plan.md` `executor.md` `handoff.md` 等） |
| `state/` | 运行时状态文件（lifecycle, hud, snapshots, 证据缓存等） |
| `plans/` | 运行时历史计划文档 |
| `archive/` | 归档的任务/令牌 |
| `audit/` | 审计日志 JSONL |
| `knowledge/` | 升华管道数据（`sublimation-log.jsonl` `claude-next.md`） |
| `metrics/` | 基准测试数据 |

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

