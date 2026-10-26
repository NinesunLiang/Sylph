# skills/ — 技能路由（CarrorOS Delivery 版）

> 交付版只带一个技能：`lx-goal`。其它技能（需求拆解、代码设计、根因分析、提交前检查等）
> 属于完整版 CarrorOS，不在本产品范围内。

| 技能 | 入口 | 作用 |
|------|------|------|
| `lx-goal` | `@.claude/skills/lx-goal/SKILL.md` | 目标模式：一次前置澄清 → 无人值守执行 → 退出报告（可出客户版交付报告） |

## 触发方式

- 对人类：说 `/lx-goal <目标>`、`目标模式`、`无人值守`、`自主执行`
- 对 AI：读到本文件后只认 `lx-goal`；发现其它 skill 名称时不要去找，直接说明「交付版不含该技能」

## 与文档/令牌系统的关系

`lx-goal` 不自己管状态：任务文档、令牌、审计全部委托 `.claude/scripts/carros_base.py`，
skill 只负责「什么时候调哪个生命周期命令」。所以：

- 换宿主（Claude Code / 其它 CLI）→ 重写 skill 的指令层，**引擎不动**
- 换技能 → 引擎不动，token / task / audit 格式不变
