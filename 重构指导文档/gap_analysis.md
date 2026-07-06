# Gap Analysis — 重构指导文档 vs 磁盘状态
> 用于精确执行，不做额外设计

## 一、来自 总结.md 的要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 1 | session-handoff.md 完整（四件套缺一） | ✅ carros_base.py 已写（init/verify/archive 自动写） | 已修复 |
| 2 | 7 个 bench README 填充 | ✅ 各有目标/预期文件/验证/证据/终态 | 已修复 |
| 3 | carros_base.py `--step` 参数 | ✅ 已有（L464-469 读取步骤列表） | 已修复？需确认 |
| 4 | omc_lint.py 第 4 项 audit jsonl 转正检查 | ✅ L126-144 已检查 json 可解析+完整性 | 已修复？需确认 |

## 二、来自 update.md 的要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 5 | Hook 输出 ≤2 行 | 6 个 hooks 已精简（每步 1 行 json） | ✅ 已查 |
| 6 | 文档与代码路径对齐 | AGENTS.md 引用路径需确认 | ⏳ |
| 7 | index.md 路由系统可调用 | index.md 44 行，引用 SUBAGENT.md 和 enhance/ | ⏳ |
| 8 | bench 最高优先级完成 | 7 个 README 已写 | ✅ |
| 9 | L1 完全闭环 | init→verify→archive 全链路通过 | ✅ |
| 10 | L1 从 AGENTS.md 引用 core 工具 | AGENTS.md 路由表引用 kernel/index/enhance | ⏳ |

## 三、来自 总结.md 和 data.md 的 L2 要求

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 11 | oracle-spec.md 从 stub 变可调用 | 36 行静态描述，无可执行函数 | ❌ 需补 |
| 12 | context-watermark.md 从 stub 变可检测 | 3 级水位描述，无实现 | ❌ 需补 |
| 13 | fallback-matrix.md 从 stub 变可执行 | 降级逻辑描述，无实现 | ❌ 需补 |

## 四、来自 AGENTS.md 和总结.md 的工作流文档

| # | 要求 | 现状 | 状态 |
|---|------|------|------|
| 14 | 工作流文档（plan.md 2.0） | 无单独工作流文档 | ⏳ |
| 15 | L2 有完整技能和双法官规格 | 只在 AGENTS.md 中提及，无独立技能文档 | ⏳ |
