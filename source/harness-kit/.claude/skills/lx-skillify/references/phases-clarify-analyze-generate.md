# Phase 0-2: 澄清 → 分析 → 生成

## Phase 0: CLARIFY

一次问清 4 问：
- Q1: 这个 skill 要做什么？
- Q2: 触发词？
- Q3: 输出格式？
- Q4: 需要脚本还是纯 AI？

输出 `skill_spec`:
```json
{"name": "lx-{name}", "description": "...", "triggers": [...], "scope": "...", "needs_scripts": false, "output_type": "report|fix|verify|generate"}
```

## Phase 1: ANALYZE

1. 读 `.claude/skills/TEMPLATE.md`
2. 探索 skills/ 找 1-2 个最相似参考技能
3. 读参考技能 SKILL.md
4. 列出 `.claude/nodes/` 全部节点（19个）
5. 列出 `.claude/schemas/atomic/` 全部 Schema（9个）

节点选择规则：

| 技能类型 | 必选节点 | 可选 |
|---------|---------|------|
| 审查类 | behavior_rules, scanner, report_generator | auto_fixer, verifier |
| 生成类 | behavior_rules, generator, report_generator | context_collector |
| 门禁类 | behavior_rules, gate_checker, report_generator | scanner |
| 工作流类 | behavior_rules, context_collector, report_generator | interactive_prompt |

输出 `analysis_result`（target_name, skill_type, reference_skills, selected_nodes/schemas）。

## Phase 2: GENERATE

加载 `@../../nodes/generator.md`。

生成规则（按序）：
1. Frontmatter — 所有必填字段
2. 原子化声明 — 5 个子表，引用真实路径
3. 状态机 — 按类型选择
4. 私有节点 + 边界声明
5. 执行流程 — Step 0..N
6. 降级策略 + 错误恢复

约束：≤300 行，引用必须解析到真实文件。
