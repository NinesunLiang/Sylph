# scripts/ — 治理工具脚本

> 可执行的 Python 治理脚本，按功能分为核心引擎和 lib 子模块。
> `carros_base.py` 是主入口。

## 核心引擎

| 脚本 | 用途 |
|------|------|
| `carros_base.py` | 主入口 CLI — `init/status/tick/verify/archive/lint/bench` |
| `pre_action_gate.py` | 前置动作门禁 |
| `oracle_agent.py` | 统一 Oracle（review/status/bypass） |
| `meta_oracle.py` | Meta-Oracle 二阶评审 |

## 任务/工作流

| 脚本 | 用途 |
|------|------|
| `task_state_tracker.py` | 任务状态追踪 |
| `task_planner.py` | 任务规划器 |
| `goal_state_machine.py` | Goal 状态机 |
| `sub_agent_executor.py` | SubAgent 执行器 |
| `sub_agent_manager.py` | SubAgent 管理器 |
| `sub_agent_recovery.py` | SubAgent 恢复 |

## 测试/验证

| 脚本 | 用途 |
|------|------|
| `verify_gate.py` | 完成验证门禁 |
| `negative_tests.py` | 负面测试 |
| `phase3_matrix_test.py` | Phase 3 矩阵测试 |
| `ga_behavioral_validation.py` | GA 行为验证 |

## 辅助工具

| 脚本 | 用途 |
|------|------|
| `context_engine.py` | 上下文引擎（handoff/prompt-ring/决策） |
| `capture_evidence.py` | 证据捕获 |
| `intake_gate.py` | 准入门禁 |
| `output_compress.py` | 输出压缩 |
| `plan_builder.py` | 计划构建器 |
| `temp-bypass.py` | 临时绕过 |
| `executor_ledger.py` | 执行分类账 |
| `clarify_engine.py` | 澄清引擎 |
| `omc_lint.py` | 代码规范检查 |
| `init-omc.sh` | 项目初始化脚本 |

## lib/ 子模块

| 模块 | 用途 |
|------|------|
| `tool_store.py` | 工具结果落盘 |
| `error_dna.py` | Error DNA 自动生成与 Retry Gate |
| `oracle_gate_light.py` | Oracle 条件接入 |
| `phase3_oracle.py` | 双审判官独立 Context 裁决 |
| `flywheel.py` | 飞轮引擎 |
| `handoff_writer.py` | Resume Capsule 生成器 |
| `autonomy.py` | Loop 硬化与自动 handoff |
| `hot_card.py` | Hot Card 阈值卡片 |
| `task_ssot.py` | 任务 SSOT |
| `ga_observability_*.py` | GA 可观测性指标 |
