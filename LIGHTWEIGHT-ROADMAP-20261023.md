# 轻量化路线图（阶段 2 已落地）

> 日期：2026-10-23 | 任务：lightweight-20261023（阶段 1）→ lightweight2-20261023（阶段 2）
> 原则：**只砍有证据的死重，不砍安全与测试**；每次砍完跑全量回归；预算只降不升。

## 1. 两阶段实测（累计）

| 指标 | 起点 | 阶段 1 后 | 阶段 2 后 | 累计 Δ |
|---|---|---|---|---|
| `.claude/` Python 总行数 | 66,865 | 65,941 | **56,828** | **-10,037（-15%）** |
| 非测试 Python 行数 | 45,238 | 44,249 | **35,192** | **-10,046** |
| `.claude/` Markdown 行数 | 36,747 | 36,653 | **34,772** | -1,975 |
| 回归测试 | 1001 passed | 1003 passed | **1003 passed / 0 failed** | +2 |

阶段 1：删 3 个零引用脚本 + 1 个归档脚本 + 生成物；清 17 个 `__pycache__`；装棘轮。
阶段 2（B/C）：删 `ui_autopilot` 3 个零引用模块（-924 行）；`frontend-overnight` 整体迁出 `.claude/workflows/` → `capabilities/frontend-overnight/`（-8,189 行 py + -1,932 行 md，git mv 保历史）；`carroros-night-deny.py` 从 settings.json 解绑（注册 hook 12→11，能力保留）；新增 ADR0019。

## 2. 目标口径（用户 2026-10-23 裁决 F）

**只算非测试代码，目标 ≤25k 行。** 当前 35,192 行，缺口 ≈10,192 行。
（旧口径把测试 21,550 行与产品工作流算进去，≤15k 在算术上不可达。）

## 3. 档位状态

| 档 | 动作 | 状态 | 可减 |
|---|---|---|---|
| **B** | 删 `ui_autopilot` 3 个零引用模块 | ✅ 完成 | -924 py |
| **C** | `frontend-overnight` 迁出治理域（保留能力） | ✅ 完成 | -8,189 py、-1,932 md |
| **D** | lx-goal 生命周期并入 carros_base | 📋 迁移方案已出（artifacts/LX_GOAL_MERGE_PLAN.md），**未动代码** | 目标 ~2,000 |
| **E** | `references/archived/`（19,887 md） | ❌ 不建议（ADR0017 裁决归档不删） | — |

## 4. 已装的防回胖机制

- `test_line_budget.py`：scripts 22100 / hooks 7700 / workflows 100 / skills 5650
  （合计 35,550；超限即红）。
- 下调节奏：每完成一档削减，把预算下调到实测值 + 0.4%，并同步本文件。
- 目标常量 `TARGET_NON_TEST_LINES = 25000` 已写入测试文件，作为下一里程碑。

## 5. 冻结域文档漂移（已修，用户 2026-10-23 授权「删除错误过时的」）

- `.claude/kernel.md` Gate 模式：改为**实测值**「11 个 hook 脚本 / L1 16 道门 / L2 18 道门」，
  删除不存在/过时的 hook 名（bash-audit 等）与「13 注册 hook」错误计数；Oracle 改为
  「不挂 hook，经 carros_base oracle 显式调用」。
- `.claude/index.md`：hooks 行（15 顶层 py / 11 注册）、rules（3 个）、tokens（94 个）、
  workflows 行（frontend-overnight 已迁出）、门禁数（16/18）。

## 6. 仍未解决（需人类裁决）

1. **评测尺子**：index46 是 2026-09-10 的；用户已在 Claude Code 侧跑新一轮 OFF/ON 电池（本会话未跑、不碰）。
2. **JEV 孤儿**：7 个 JEV 脚本仅在 `.omc/worktrees/task-isolated-goal-7de94ace/`，主干无；合回 or 弃置待裁。
3. **分支拓扑**：`main` 停 2026-07-12、`release` 停 09-13；治理最新代码在 `photo-coach-v2-rebuild`，稳定发布线待定。
