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
| 状态管理 | `kernel.md` → 管理内核 | 冻结 / 飞轮 / 降级 |
| 完整生命周期 | `.claude/scripts/carros_base.py` | init→tick→verify→archive |
| L1 快速任务 | `carros_base.py` | init→verify→archive |
| L2 复杂任务 | `carros_base.py` + 条件 Oracle | 含水位+Oracle+降级 |

## Hook 路由

| 触发点 | 注册位置 | 说明 |
|--------|----------|------|
| 统一门禁 | `.claude/settings.json` → `hooks.PreToolUse` | pretool-gate.py（G1-G6），每工具调用前自动执行 |
| Hook 调度 | `.claude/hooks/hook-launcher.sh` | 从 settings.json 按名启动具体 hook |

## 脚本快速索引

| 脚本 | 用途 |
|------|------|
| `carros_base.py` | 主入口（init/status/tick/verify/archive/lint） |
| `omc_lint.py` | 7 项代码规范检查 |
| `verify_gate.py` | 完成验证门禁 |
| `tool_store.py` | 工具结果落盘（Phase 0 S4） |
| `error_dna.py` | Error DNA 自动生成与 Retry Gate（Phase 1） |
| `oracle_gate_light.py` | Oracle 条件接入（Phase 1，同级模型） |
| `water_level.py` | 三段式水位运行时（Phase 1，已接入） |
| `phase3_oracle.py` | 双审判官独立 Context 裁决（Phase 3） |

> 完整脚本列表见 `.claude/scripts/` 目录。docs/carros/reviews/ 为审核参考材料，默认禁止入模。
