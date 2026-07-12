# index.md — 渐进式披露路由表

> 指向 `.claude/` 下的可复用资产和 `.omc/` 下的运行时任务

## 路由规则
**默认 L1。** 当条件满足任意 L2 触发点时 → L2。

| 层级 | 路由 | 说明 |
|------|------|------|
| L1 | 默认路径 | 日常开发、单文件修复、文档更新 |
| L2 | 跨系统 / 不可逆 / 安全权限 / 发布 / 长时间无人 | 启用 Oracle + 水位 + 降级 |

## 工作流路由

| 场景 | 路径 | 入口 |
|------|------|------|
| 状态管理 | `@kernel.md` → 管理内核 | 冻结 / 飞轮 / 降级 |
| 完整生命周期 | `.claude/scripts/carros_base.py` | Plan→Step→Verify→Archive |
| L1 快速任务 | `.claude/scripts/intake_gate.py` + `.claude/scripts/verify_gate.py` | init→verify→archive |
| L2 复杂任务 | `.claude/scripts/carros_base.py` + `.claude/scripts/oracle_engine.py` | 含水位+Oracle+降级 |

## Hook 路由

| 触发点 | 位置 | 说明 |
|--------|------|------|
| 统一门禁（7 合一） | `.claude/hooks/pretool-gate.py` | sensitive-edit / fallback-check / action-gate / plan-gate / edit-scope / privacy-gate / completion-gate |
| 状态横幅 | `.claude/hooks/statusline-command.sh` | 状态回调 |

## Skill 路由

| 场景 | 路径 |
|------|------|
| 目标驱动执行 | `.claude/skills/lx-goal/SKILL.md` |
| Oracle 门禁 | `.claude/skills/lx-oracle/SKILL.md` |
| 多 agent 并行 | `.claude/skills/lx-race/SKILL.md` |
| 步骤式推进 | `.claude/skills/lx-stepwise/SKILL.md` |
| 任务队列管理 | `.claude/skills/lx-todo/SKILL.md` |
| 治理验证 | `.claude/skills/lx-validate-skill/SKILL.md` |
| 变量锁 | `.claude/skills/lx-varlock/SKILL.md` |
| CarrorOS 更新 | `.claude/skills/update-carror-os/SKILL.md` |

## Schema 路由

| Schema | 路径 |
|--------|------|
| Token 结构 | `.claude/schemas/token.schema.json` |
| 原子结构 | `.claude/schemas/atomic/`（context_summary / error_codes / finding / fix_record / gate_result / scan_report / scan_target / severity / verdict） |
| 合约 | `.claude/schemas/contract/state_transitions.yaml` |
| 输入 | `.claude/schemas/input/task_input.yaml` |
| 输出 | `.claude/schemas/output/`（acceptance_report / gov_report / review_report / task_spec） |
| 注册表 | `.claude/schemas/registry.yaml` |

## 脚本快速索引

| 脚本 | 用途 |
|------|------|
| `carros_base.py` | 主入口（init/status/tick/verify/archive/lint） |
| `omc_lint.py` | 7 项代码规范检查 |
| `verify_gate.py` | 完成验证门禁 |
| `plan_builder.py` | 计划生成 |
| `context_engine.py` | 上下文引擎 + compact_write |
| `output_compress.py` | 输出压缩 |
| `pre_action_gate.py` | 动作前门禁 |
| `task_state_tracker.py` | 任务状态追踪 |
| `executor_ledger.py` | 执行台账 |
| `intake_gate.py` | 入口门禁 |
| `honesty_audit.py` | 诚实审计 |
| `oracle_*.py`（6 文件） | Oracle 评审引擎 |
| `fallback_matrix.py` / `fallback_engine.py` | 降级矩阵 |
| `context_watermark.py` | 水位检测（骨架） |
| `statusline.py` | 状态栏生成 |
| `archive_engine.py` | 归档引擎 |
| `carros_utils.py` | 工具函数 |
| `carros_oracle_base.py` | Base 版 Oracle 适配 |

## Reference 路由

| 资产 | 路径 |
|------|------|
| SubAgent 派发 | `.claude/references/SUBAGENT.md` |
| 路径规范 | `.claude/references/omc-path-conventions.md` |
| Oracle 门禁规格 | `.claude/references/oracle-spec.md` |
| 水位检测 | `.claude/references/context-watermark.md` |
| 降级矩阵 | `.claude/references/fallback-matrix.md` |
| 违反范式处理 | `.claude/references/anti-patterns.md` |
