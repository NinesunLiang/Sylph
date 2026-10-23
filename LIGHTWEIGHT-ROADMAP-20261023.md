# 轻量化路线图（CarrorOS_dev 口径）

> 日期：2026-10-23 | 分支：`CarrorOS_dev` | 原则：只砍有证据的死重，不砍安全与测试；每次砍完跑全量回归；预算只降不升。
> 口径（用户裁决 F）：**目标只算非测试代码，≤25k 行**。

## 1. 当前实测（2026-10-23，CarrorOS_dev）

| 指标 | 实测 | 说明 |
|---|---|---|
| `.claude/` Python 总行数 | 53,084 | 含测试 |
| 非测试 Python | **36,124** | scripts 25,453 + hooks 7,581 + workflows 0 + skills 3,090 |
| `.claude/` Markdown | 32,719 | 含 references/archived（ADR0017 保留） |
| 已迁出治理域 | 7,566 py | `capabilities/frontend-overnight/`（C 档） |
| 回归 | **911 passed / 0 failed** | `.claude/scripts/ + .claude/hooks/` |
| lx-goal 自身测试 | 90 passed / 16 failed | **既有红灯**，D 档前置项（见迁移方案） |
| 距目标 25k | **-11,124** | |

## 2. 本轮在 CarrorOS_dev 实际落地

- **C 档**：`frontend-overnight` 迁出到 `capabilities/`（7,566 py），`night-deny` 从 settings.json 解绑（注册 hook 12→11），ADR0019。
- **B 档**：`ui_autopilot` 三个零引用模块在目标分支本就不存在，无行数变化（不重复删除）。
- **棘轮**：`test_line_budget.py` 按目标实测重标：scripts 25,650 / hooks 7,650 / workflows 100 / skills 3,150（合计 36,550）。
- **文档**：目标分支既有裁决优先——kernel/哲学/gate-contract/README/harness 保持原样（14 门、oracle 退役观察区）；只更新 workflows 行与 night-deny 说明。
- **产品更新**：`feat:pure` 的 `apps/photo_coach_v2`（485 文件）已迁入（commit 2f9474d）。

## 3. 死代码盘点（目标分支，本轮实测）

- 零引用：**1 个 / 185 行**（`jev_calibrate.py`，JEV 域，待 JEV 裁决）。
- 弱引用（仅测试/内部）：`claude_audit_jev.py`、`gov_score.py`、`consolidate.py`、`self_evolve.py`、`gate_roi_report.py` 等。
- `self_evolve.py` 是自迭代 cron 入口，zombie README 明确保留；`observe.py/consolidate.py` 属同管线。
- 结论：**目标分支已无“成规模的安全删除空间”**，再往下必须动子系统（D 档）或产品域（C 已完成）。

## 4. 防回胖

- `test_line_budget.py`：超 36,550 即红；目标常量 `TARGET_NON_TEST_LINES = 25000`。
- 下调节奏：完成 D 档后把 scripts/skills 预算同步下调。

## 5. 待办

1. **D 档**（lx-goal 1,855 行并入 carros_base）：方案已出，前置 = 电池基线 + 16 个既有红灯先稳定。
2. **JEV**：`jev_calibrate.py` 零引用等，随 JEV 去留一并裁决。
3. **分支/发布**：`CarrorOS_dev` 领先 `origin/feature_jev_version` 36 个提交，未 push。
4. **电池**：用户在 Claude Code 侧执行中（本会话不跑）。
