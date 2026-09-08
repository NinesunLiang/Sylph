# 15 — carros_base.py 单体拆分施工图（PLAN_SIMPLIFY B2，A 方向）

> 状态：已批准方向（人类 2026-09-08 选 A：拆单体）。本图是施工依据，**每个模块迁移独立 commit + 全量 pytest 绿 + 人审 diff 后落地**。
> 目标：carros_base.py 3,981 行 → **≤1,200 行**；动词收敛 → **≤15**；行为 100% 不变（514 回归测试是安全网）。

## 现状（实测）

- 单文件 3,968 行（含注释/长 docstring），~21 动词，21 个大 cmd_* 函数互相经模块级全局（TOKEN_PATH/PLAN_PATH/TASK_DIR/helpers）耦合。
- 死链 `_run_dual_judge` 已删（2026-09-08，commit b598ff7）。

## 拆分原则

1. **只搬逻辑，不动行为**：任何迁移 = 原样搬 + import 回接 + 全量 514 测试绿 + `help`/主流程手测一次。
2. **避免循环 import**：先抽**无全局依赖的纯函数/常量**到 `lib/`（它们不 import carros_base），carros_base 之后 import 它们。cmd_* 动词保留在 carros_base（只变瘦：把被调用的逻辑体挪走），或后续整体迁入 `lib/carros_verbs/` 时通过参数传状态、不 import carros_base。
3. **回滚 = revert 单 commit**（每模块一 commit，互不掺）。
4. **不顺手改**：不在迁移里修 bug/加功能；冻结文件不碰。

## 四模块划分（目标结构）

| 模块 | 内容（从 carros_base 迁出） | 预计行 | 耦合 |
|---|---|---|---|
| `lib.carros_core` | 状态机/文件路径/全局解析纯函数（token 定位、task_dir、plan/executor 解析、sha/时间工具、`_ev_field` 等） | ~500 | 低（先迁） |
| `lib.carros_report` | final-report 生成、report/status 输出、bench 场景文案与汇总 | ~600 | 中（依赖 core+数据） |
| `lib.carros_docs` | init 文档骨架（research/plan/executor 模板、working-set/三件套生成）、clarify 问题文案 | ~700 | 中 |
| `lib.carros_gates` | verify_gate/oracle/self-check/mechanism 自检调用封装 | ~700 | 高（最晚迁） |
| `carros_base.py`（瘦身主体） | import 上述 + 全局状态 + 命令分发 + 薄 cmd_* 壳 | ≤1200 | — |

## 迁移顺序（耦合低→高，每步独立 commit）

1. **M0 纯函数库**：搬无全局依赖的 helper（时间/路径/解析/文本）。验收：carros_base import 后全量绿，行数 −。
2. **M1 报告/输出**：`report`/`status` 文本与 final-report 生成逻辑。验收：`carros_base.py report` 输出与迁移前一致（对比）。
3. **M2 文档骨架**：init 模板/clarify 文案。
4. **M3 门禁封装**：verify/oracle/self-check。
5. **M4 动词收敛**：把实际未用/低频动词（cancel/migrate/collect/gate/manifest/auto 等）标 retired 移入 `retired/`（3 个月无人调用再物理删）。

## 验收里程碑

| 步 | 验收 |
|---|---|
| 每模块 | pytest（.claude/scripts + .claude/hooks）0 failed；`carros_base.py help` 正常；被迁功能手测一条等价 |
| M0 后 | 行数 ≥200 下降 |
| M4 后 | 动词 ≤15；carros_base ≤1200 行 |
| 全程 | 冻结文件零改动；每 commit 可单独 revert |

## 风险与回滚

- **风险**：import 环 / 全局状态错位 / 迁移时夹带行为变化。
- **缓解**：只搬纯函数先行；动词壳薄；每 commit 前 `git stash` + 迁移后立即全量测试；回滚 = revert 该 commit。
- **不做**：不在此重构期改状态机语义/加功能/动冻结文件。

## 参考

- PLAN_SIMPLIFY_SELF_ITERATE.md B2（六件套→三件套、carros 拆分、命令 40→15）
- MODERNIZATION_AUDIT.md（55k 治理代码现状证据）
