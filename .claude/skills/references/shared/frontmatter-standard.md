# 标准 Frontmatter 字段

> 所有 lx-* skill 的 frontmatter 规范。

## 必填字段

| 字段 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `name` | string | `lx-code-review` | 技能名，`lx-` 前缀 |
| `version` | semver | `v1.0.0` | 语义版本 |
| `description` | string | `"审查代码..."` | 一句话描述，<120 字符 |
| `when_to_use` | string | `"Use when..."` | 触发条件 |
| `argument-hint` | string | `"[描述]"` | 参数提示 |
| `harness_version` | string | `">=6.3.0"` | 最低兼容 harness 版本（>=格式，不重复当前版本号） |
| `status` | enum | `draft\|stable\|mature` | 成熟度 |
| `role` | string | `"Code reviewer..."` | 角色描述 |
| `execution_mode` | enum | `stepwise\|race` | 执行模式 |
| `triggers` | string[] | `["/lx-xxx"]` | 触发词 |

## 可选字段

| 字段 | 说明 |
|------|------|
| `complexity` | `beginner\|intermediate\|advanced` |
| `paths` | 限制作用域的文件 glob |
| `disable-model-invocation` | 禁止自动调用 |
