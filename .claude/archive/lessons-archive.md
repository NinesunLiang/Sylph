# lessons-archive.md — 已归档教训

> 从 claude-next.md 归档的已修复/已关闭/不相关条目。
> 保留一行摘要 + 原始行号引用，便于追溯。
> 归档日期: 2026-05-15

---

## 已修复条目 (13)

| # | 条目 | 修复日期 | 摘要 |
|---|------|---------|------|
| R22 | PostToolUse 不派发失败事件 | 2026-05-13 | settings.json 需同时注册 PostToolUse + PostToolUseFailure |
| R23 | harness.yaml hooks_enabled 不等于实际注册 | 2026-05-13 | 三方一致性审计 (disk + settings.json + harness.yaml) |
| R24 | Bash unquoted glob 被 cwd 文件污染 | 2026-05-13 | `for x in $VAR` 前需 `set -f` 禁用 glob 展开 |
| R29 | context-guard matcher 放宽防自锁 | 2026-05-07 | matcher 从 `.*` 改为 `Edit\|Write`，避免无法自恢复 |
| R30 | AI 评估环境前必须先检查 | 2026-05-13 | score-self-check.sh 基于实际配置而非文档默认值 |
| R31 | gh CLI 写操作是 permission-gate 防御盲区 | 2026-05-13 | 新增 gh_write_regex 覆盖 release/pr/issue/secret 等 |
| R32 | install.sh 合并应降级标题层级 | 2026-05-13 | sed 降级 `#` → `##`，保留用户一级标题 |
| R33 | compact-detect.sh 必须注入知识 | 2026-05-12 | compact 后注入 index.md 铁律 + AGENTS.md 纲要 |
| R34 | 说"系统没这问题"前必须逐文件验证 | 2026-05-13 | pre-commit-self-review.sh 交叉验证 |
| R36 | hook 合并/废弃需三方同步 | 2026-05-13 | 同时更新 settings.json + harness.yaml + smoke tests |
| R41 | Error DNA JSONL 轮转数据丢失 | 2026-05-13 | 移位循环修复 `range(archive_count-1, 0, -1)` |
| DF-01 | turn-counter 模糊检测 false positive | 2026-05-14 | 方向限定词检测：`从.{1,8}(上\|角度\|层面)` 等 |
| DF-02 | completion-gate 自主模式 stderr 噪音 | 2026-05-14 | 改为写入日志文件，不输出 stderr |

## 已关闭条目 (2)

| # | 条目 | 关闭原因 |
|---|------|---------|
| 2026-05-10 | 用户纠正: scope gate 修复被中断 | 纠正内容跨会话丢失，已关闭 |
| 2026-05-11 | 用户纠正: agent-found issues 修复被中断 | 纠正内容跨会话丢失，已关闭 |

## 已升华 Seed 条目 (5)

> 来源：外部收录（其他用户 claude-next.md 互操作）。核心精神已融入 kernel.md §禁止行为。
> 条目本身与 Carror OS 项目无关（TypeScript/React 专用），移除以减少注入噪音。

| # | 条目 | hits | 原始行号 |
|---|------|------|---------|
| seed:typescript | 禁止 any 类型逃逸 | 3 | claude-next.md:480 |
| seed:typescript | useEffect 依赖数组必须完整 | 3 | claude-next.md:488 |
| seed:typescript | API 响应必须定义完整类型 | 2 | claude-next.md:496 |
| seed:general | 修改接口前必须查引用 | 4 | claude-next.md:504 |
| seed:general | 长对话中禁止依赖记忆引用文件内容 | 5 | claude-next.md:512 |
