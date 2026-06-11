## 原子化声明

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/oracle-protocol.md` | oracle protocol 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md


# lx-oracle-v2 — 已废弃

> **此 skill 已合并到 `/lx-oracle` v2.0。**
>
> 原 v2 的 Agent spawn 路径现在是 lx-oracle 的**路径 A**。
> 支撑脚本 (`oracle-spawn.sh`) 和协议文件 (`references/oracle-protocol.md`) 保留不动。
>
> **请使用 `/lx-oracle review ...`**，无需单独调用 `/lx-oracle-v2`。

## 降级策略
| 场景 | 降级路径 |
|------|---------|
| 此 skill 已废弃 | 使用 /lx-oracle 替代 |
