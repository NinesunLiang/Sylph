# Headless Permissions Contract（可移植执行使能）

> 背景：index17 独立评估发现——ON spawn 会话能写文件完成任务，关键机制是 `.claude/settings.local.json` 的 `permissions.allow` 含 `Bash(python3 *)`。该文件 gitignored（机器本地），fresh 环境（新克隆/新机器）无此配置时，headless AI 所有写入被拦，退回「OFF 全拦」状态。
>
> 用户裁决（2026-08-13）：把权限契约写进项目正式文件，让任何环境都能用。

## 契约文件

`.claude/settings.permissions.json`（**已提交**）——可移植的 headless 执行使能白名单：

- `Bash(python3 *)`：核心使能。允许 python3 脚本/heredoc/-c 执行（headless 下唯一可靠的写文件与运行路径）。
- 少量只读工具（git status/diff/log、ls、pwd）：headless 下的常用只读操作。

> 安全网说明：允许 python3 广泛执行**不削弱安全**——dangerous 命令由 pretool-gate 的 secret-scan / governance-bypass / action 门禁拦截；contract 只负责「让 AI 能干活」，不做「危险命令判定」。

## 应用方式（fresh 环境一键）

```bash
python3 .claude/scripts/apply_permissions.py
```

脚本行为：
- 读取契约 `permissions.allow` → 与本地 `settings.local.json` 的 `permissions.allow` 做**并集**（去重、保留现有规则顺序、不覆盖未知字段）。
- **幂等**：无变化不写文件。
- 首次写入前自动备份 `settings.local.json.bak`。
- 支持 `--dry-run` 预览、`--target/--contract` 指定路径（测试用）。

## 为什么是独立契约文件而非直接提交 settings.json

- `.claude/settings.json` / `settings.local.json` 含机器特定配置（apiUrl / authToken / 本机工具链 allow），**gitignored 且含机密**，不可提交。
- 契约文件不含机密、结构最小，可安全提交；合并脚本把契约落到本地生效文件，保持「机器配置留本机、能力契约进项目」的边界。

## 与 inline python 软规则的关系（F2 例外条款）

AGENTS.md 的「临时脚本须用 Write/Edit 落盘、禁止 inline `python3 -c`」是**软规则**（无 hook 硬门禁，index17 实测 ON 会话 python3 -c/heredoc 均放行）。

**例外条款（2026-08-13 用户裁决 F2 还债）**：当 Write/Edit 与 Bash 直写（重定向/touch/tee）**均被权限系统拦截**，而 python3 是唯一可用的合法执行/写文件路径时，允许临时使用 python3 heredoc 或脚本落盘——**这属于例外，不构成违规**，无需在报告里自我批评偏离规则。AI 按决策链自决，并在报告中如实标注所用回退方式。

> **禁 inline python 的真实语义（用户 2026-08-13 澄清）**：「禁止 inline `python3 -c`」指的是**不要把需要人类在终端执行的临时 python 命令塞给人类**（终端宽度截断、不可审查、不可重跑）。**AI 在权限受限的 headless 环境中自己用 python3 写文件/执行，不属于被禁的 inline python**——这正是 F2 例外覆盖的合法回退。
>
> 判定边界：
> - ✅ 例外：AI 用 Bash(python3 *) 写文件/执行（权限受限时的合法回退）——不违规
> - ✅ 常规：AI 把临时脚本用 Write/Edit 落盘后执行——推荐路径
> - ❌ 被禁：AI 让人类在终端手动跑 `python3 -c "..."` 等内联命令——这才是「禁 inline python」的本意

## 决策记录（2026-08-13 用户裁决）

| # | 裁决 | 落地 |
|---|------|------|
| 1 | 权限契约写进项目正式文件，任何环境可用 | 本文件 + settings.permissions.json + apply_permissions.py |
| 2 | 规则冲突不设权限硬门禁 | 确认 inline python 为软规则，无 hook 门禁；不回退到硬门禁方案 |
| 3 | 环境约束（如 E1：headless 无交互权限）执行时默认由 AI 决策链自决 | headless/无交互权限类约束不再呈交人类逐次裁决；AI 按 CarrorOS 决策链（哲学/铁律/现状/ROI）自主处理，仅记录 |
