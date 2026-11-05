---
name: lx-pre-push
version: v3.0.0
description: "推送前深度检查 — 安全/边界/破坏性/依赖性，复用仓库自带能力，不依赖未安装的外部工具。纯指令调用，每次 push 前执行。"
when_to_use: "Use before git push. Deep gate: security, boundary, destructiveness, dependency. One check per push."
argument-hint: ""
harness_version: ">=6.3.0"
status: stable
role: "Pre-push deep gate — security, boundary, destructive, dependency. Repo-native, no external tools."
execution_mode: stepwise
triggers:
  - "/lx-pre-push"
---
# lx-pre-push — 推送前深度检查

> **硬闸强制**：仓库 Git `pre-push` 钩子会自动执行本检查，失败即阻断推送（`bash .claude/scripts/install_git_hooks.sh` 安装）。手动跑一次仍可用。生产的安全最后一道闸。

## 定位（index50 重建）

**深、复用仓库已有能力、不猜项目类型、不依赖外部工具。**

| 旧版问题 | 新版 |
|---|---|
| 安全扫描靠 `pip-audit`/`gosec`——**本仓均未安装**，而规则是「工具缺失 → 阻塞」→ **每次 push 恒卡死** | 复用仓库自带的密钥模式库（`pretool_gates/constants`），**零外部依赖** |
| 无「边界」检查 | **新增**：改动是否触碰禁止路径 |
| 「破坏性」只有敏感文件+二进制 | **新增**：被删文件是否仍被引用（悬空引用） |
| 无「依赖性」检查 | **新增**：改动文件**被谁引用**，暴露影响面 |
| 靠「项目类型」分支 | 按**改动内容**判定 |

## 执行

```bash
python3 ".claude/scripts/pre_push_check.py"
```

## 四项检查

| # | 检查 | 内容 | 失败行为 |
|---|---|---|---|
| 1 | **安全** | 改动内容是否含密钥/凭据（仓库自带模式库） | ❌ **阻断** |
| 2 | **边界** | 是否触碰禁止路径（`.env`/`secrets/`/`.ssh/`/`.aws/`/`docs/carros/reviews/`） | ❌ **阻断** |
| 3 | **破坏性** | 被删除的文件是否**仍被引用**（悬空引用） | ❌ **阻断** |
| 4 | **依赖性** | 被修改的文件**被谁引用**——影响面清单 | ✅ 仅暴露，供确认 |

## 关键实现细节（实跑教训）

- **比对基线用当前分支的 upstream**（`@{u}`）。本仓当前分支是 `release`，其 upstream 是
  `origin/release`，而 `origin/HEAD` 指向 `origin/main`——**拿后者比会得出 391 个「改动」，完全失真**。
- **测试夹具降级为警告**：`test_*.py` 里的 `sk-...` 是验证门禁用的夹具，不是真泄漏。
  业界密钥扫描器普遍排除测试夹具，此处同办；**非测试文件命中仍 🔴 阻断**。
- **引用识别要看「去扩展名」的形式**：代码里是 `from helper import x`，**不带 `.py`**。
  只搜文件名会漏判真实依赖。
- **扫描面用 `git ls-files`**，不用 `rglob`——后者会扫进 `node_modules/.git`，实测慢到超时。
- **历史也要查**：安全检查覆盖本地基线到 HEAD 的待推送提交，不能只看工作区最终内容。先提交后删除的凭据仍在历史中；输出只包含路径和提交编号，不回显凭据。超过扫描大小上限的历史内容明确报告未完成检查。
- **文件名使用 NUL 分隔**：中文、空格和换行不应导致检查漏项。

## 降级

| 场景 | 处理 |
|---|---|
| 无 upstream（首次推送） | 退化为与 `HEAD` 比较，不空转 |
| 密钥模式库不可用 | ❌ **阻断**（fail-closed，安全项不可降级） |
| 无待推送改动 | 直接通过 |
