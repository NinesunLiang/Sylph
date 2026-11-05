# 内部独立审核（按需）

底层入口仍为 `.claude/scripts/oracle_agent.py`，不另设 skill。
- static：静态检查范围、计划、危险路径和证据。
- runtime：运行时验证；duo：静态与运行时互补审核。
- runtime/duo 之前必须有同 task-id 的静态 ACCEPT/ADVISORY；沿用底层检查。
- 高风险改动按既有策略审核，普通任务按需；不把模型赞同当作测试通过。
- REJECT 按原因修复再审；不可用明确标 UNVERIFIED，不伪造通过。
- 模型审核不授予人类权限；交互风险用 ask，Goal 未授权风险记录并跳过。
