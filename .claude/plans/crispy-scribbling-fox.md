# 计划：修复 lx-rpe Skill 不可用问题

## Context

用户尝试调用 `lx-rpe prd/notification/feat-notification-push`，但系统返回 "Unknown skill: lx-rpe"。

已确认：
- `lx-rpe` SKILL.md 存在于 `.claude/skills/lx-rpe/SKILL.md`
- `harness.yaml` 中 `skills_enabled.lx-rpe: true`（line 156）
- `feature-registry.yaml` 中 `lx-rpe` 已注册（line 275）
- 但系统-reminder 的可用技能列表中**不包含** `lx-rpe`（而同目录的 `lx-status`, `lx-code-review` 等均在列表中）

## 根因诊断（顺序执行）

### Step 1: 验证 SKILL.md frontmatter 格式
- 读取 `lx-rpe/SKILL.md` 与一个可正常工作的 skill（如 `lx-status/SKILL.md`）对比 frontmatter 格式
- 检查：yaml 分隔符、字段名、triggers、argument-hint 等是否一致
- 可能的问题：frontmatter 解析错误导致 skill 被静默跳过

### Step 2: 执行 lx-validate-skill 验证
- 运行 `/lx-validate-skill` 检查 `lx-rpe` skill 是否符合原子化架构规则

### Step 3: 检查 Skill 注册/发现机制
- 搜索 `.claude/` 下所有涉及 skill 注册/发现的配置（settings.json, 缓存文件等）
- 确认是否需要手动注册或刷新

### Step 4: 修复
- 根据诊断结果修复（frontmatter 修正、注册、或重新加载）

## 预期结果
- `lx-rpe` 出现在可用技能列表中
- 用户可调用 `/lx-rpe prd/notification/feat-notification-push`

## Verification
- 调用 Skill tool 的 `lx-rpe`，确认不再返回 "Unknown skill"
- 或用 `lx-validate-skill` 验证修复后的 skill 格式
