# D 档迁移方案：lx-goal 生命周期并入 carros_base

> 状态：**方案（未动代码）** | 日期：2026-10-23 | 用户裁决：「要谨慎，核心能力」
> 前置：先在 Claude Code 侧跑一轮 OFF/ON 电池，拿到 lx-goal 涉及探针的基线；本方案不先于基线执行。

## 1. 现状证据（2026-10-23 实读）

| 事实 | 证据 |
|---|---|
| `lx-goal.py` 1,855 行 / 62 个函数（CarrorOS_dev 实测） | `wc -l`、`grep -c '^def '` |
| 已委托 carros_base 的部分 | `lx-goal.py:438` 起调 `carros_base.py init`；`:116` `from carros_base import _save_token` |
| 仍自持的生命周期 | `cmd_phase0_done`(838) / `cmd_plan_done`(1163) / `cmd_verify_step`(1589) / `cmd_task_done`(1627) / `cmd_clear`(1837) / `cmd_checklist_verify`(1947) / `cmd_done`(2071) |
| 重复实现 | token 保存（`_save_task_token` 与 carros_base `_save_token` 双入口）、verify（`_verify_goal_step` vs `verify_gate.verify_step`）、done/archive（`cmd_done` vs `carros_base archive`） |
| 测试资产 | lx-goal 90 passed / 16 failed（**目标分支既有红灯**，D0 必须先定位）；全仓 911 passed |

## 2. 目标

- 生命周期**单一实现**：token 读写/CAS、verify、archive 只在 `carros_base.py` + `carros_lib/`。
- `lx-goal` 退化为「目标语义层」：goal 字段、轮次预算、事件流、退出报告；
  目标 ≤600 行（从 1,855 起，净减约 1,250 行，计入 F 档 25k 缺口）。
- **行为零变化**：CLI 命令名、token 字段、事件格式、报告格式全部保持。

## 3. 分阶段（每阶段独立 commit + 可回滚 + 测试全绿）

| 阶段 | 动作 | 验收 | 回滚 |
|---|---|---|---|
| D0 | 先让 16 个既有红灯归零/归因，再把 token 字段、事件、CLI 输出拍成 characterization 测试 | 116 测试全绿 | 无代码改动 |
| D1 | 抽 `carros_lib/token_store.py`：把 carros_base `_save_token`/`_load_token`/CAS 原样搬过去，两边 import | 1,003 + 116 全绿；无逻辑变化 | `git revert` |
| D2 | lx-goal 的 `_save_task_token` 改调 token_store；删除本地副本 | 同上；CAS 冲突测试通过 | 同上 |
| D3 | `cmd_verify_step` 改为：goal 包装器 → `verify_gate.verify_step` | verify 相关 30+ 测试全绿 | 同上 |
| D4 | `cmd_done`/`cmd_clear` 改为调 carros_base archive/状态机；goal 元数据走扩展字段 | 归档/清理测试 + 端到端 goal 测试全绿 | 同上 |
| D5 | 删除死代码，更新 SKILL.md/文档；跑 OFF/ON 电池对比 | 116 + 1,003 全绿；电池无回归 | 分支保留 |

## 4. 风险与控制

| 风险 | 控制 |
|---|---|
| CAS 语义差异（goal 用 expected_revision，CLI 无开关） | D1 先统一 `_save_token` 签名与测试，D2 再切换；保留 legacy 分支测试 |
| goal 事件流与快照膨胀（R2 已知线性增长） | 迁移时顺带加「事件数上限 + 老事件归档」开关，单独测试 |
| hooks 读 token 字段（night-deny / claim-audit） | D0 characterization 覆盖字段读取；字段只增不改 |
| CLI 契约破坏（用户/工作流脚本依赖命令名） | 命令名与输出格式冻结，D5 才允许改文档措辞 |
| 迁移期双写不一致 | 每阶段只改一侧；禁止「新旧并行写到同一 token」 |

## 5. 不做什么

- 不重写 verify 规则解析（只搬调用点）。
- 不改 token schema 版本（v1.0 保持），只加可选字段。
- 不在电池基线之前合并（用户先跑 OFF/ON）。
