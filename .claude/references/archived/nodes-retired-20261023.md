# 节点归档：gate_checker / orchestrator / 已删除节点（2026-10-23 从 nodes/README.md 迁出）

> 回滚能力由 git 历史提供；本归档仅作删除依据留痕（少即是多：活跃文档不留墓碑）。

## 低频/参考节点（从"按功能分类"迁出，文件仍在 nodes/ 目录）

| 节点 | 引用率 | 用途 |
|------|--------|------|
| [gate_checker.md](../../nodes/gate_checker.md) | 2/19 | Gate 判定（安全/推送门禁） |
| [orchestrator.md](../../nodes/orchestrator.md) | 0（参考） | 通用状态机参考实现 |

## 已删除节点（8 个）

| 原节点 | 删除理由 |
|--------|---------|
| `plan_node.md` | 0 引用，规划逻辑内联到 skill |
| `a0_clarifier.md` | 0 引用，澄清合并到 interactive_prompt |
| `spec_generator.md` | 0 引用，generator.md 已覆盖 |
| `fallback_exploration.md` | 0 引用，降级触发在 execute_node 中 |
| `fallback_framework.md` | 0 引用，同上 |
| `judge.md` | 0 引用，verdict schema 已定义判定结构 |
| `mode_selector.md` | 0 skill 引用，已删除 |
| `oracle_terminal.md` | 0 skill 引用，已迁移到 scripts/oracle_agent.py |
| `generator.md` | 2026-10-23 物理删除：与 spec_generator 同职能，无独立消费者；历史链接残留于部分 skill 文档 |
