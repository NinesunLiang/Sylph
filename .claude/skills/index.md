# skills/ — AI Agent Skills

> 按 category 子目录分组的 AI agent 技能文件。
> 每个 skill 是一个独立的 SKILL.md（含 YAML frontmatter），agent 在需要时加载。

## Skill 分类

| category | 目录 | 说明 |
|----------|------|------|
| `apple/` | macOS 相关 | iMessage, Reminders, Notes, FindMy |
| `carroros/` | CarrorOS 治理 | Oracle, Gate, Hook, Benchmark 等 |
| `creative/` | 创意内容 | ASCII, SVG, Excalidraw, Manim |
| `data-science/` | 数据科学 | Jupyter, 数据分析 |
| `devops/` | 运维 | 代理, 基准测试, 模型路由 |
| `github/` | GitHub 工作流 | PR, Issue, Code Review |
| `media/` | 媒体 | YouTube, GIF, 音乐生成 |
| `mlops/` | ML Ops | LLM 评估, 微调, 推理 |
| `social/` | 社交 | 军师联盟 |
| `software-development/` | 软件开发 | TDD, 调试, 文档, 架构 |

## Skill 管理

- 新增 skill：`skill_manage(action='create', ...)`
- 查看当前 skill 列表：通过 skills_list 工具
- Skill 设计指南：`.claude/references/skill-atomization-guide.md`
