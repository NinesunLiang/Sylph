# skills/ — AI Agent Skills

> 扁平布局：10 个 `lx-*` skill，每个是独立 SKILL.md（含 YAML frontmatter）。
> 完整清单与说明见 `SKILLS.md`；路由触发词见各 SKILL.md 的 `triggers`。

## Skill 清单（10 个）

| skill | 用途 | 触发词 |
|-------|------|--------|
| `lx-goal` | 目标模式：一次澄清→全自动执行→退出报告 | `/lx-goal`, `/executor` |
| `lx-ghost` | 方向驱动探索（开放目标） | `/lx-ghost` |
| `lx-oracle` | Oracle 质量门禁（static/runtime/duo 双审） | `/lx-oracle`, `双法官` |
| `lx-stepwise` | 卡片推进器：当前卡未闭环不进下一张 | `/lx-stepwise`, `逐步推进` |
| `lx-task-spec` | 统一任务驱动（light/standard/deep 三模式） | `/lx-task-spec` |
| `lx-rpe` | RPE 系统性特性开发（9 步闭环） | `/lx-rpe`, `feature dev` |
| `lx-pre-commit` | 提交前轻量检查 | `/lx-pre-commit` |
| `lx-pre-push` | 推送前安全检查 | `/lx-pre-push` |
| `lx-root-cause-analysis` | 五问根因分析 | `/lx-root-cause-analysis` |
| `lx-codebase-design` | 深模块设计哲学 | `/lx-codebase-design` |

## Skill 管理

- 新增 skill：按 `SKILLS.md` 约定创建 `lx-{name}/SKILL.md`（含 frontmatter）。
- Skill 设计指南：`.claude/references/skill-atomization-guide.md`
- 归档 skill：移入 `archived/`（git 可恢复）。
