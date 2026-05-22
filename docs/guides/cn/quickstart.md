# 快速开始

> **在 2 分钟内见证一个 Gate 生效。**

## 前置条件

Carror OS 支持 **macOS / Linux / Windows (WSL & Git Bash)**。

| 平台 | 终端 |
|------|------|
| macOS | Terminal.app / iTerm |
| Linux | 任意终端 |
| Windows | Git Bash（推荐）或 WSL |

> **Windows 用户**：安装 [Git for Windows](https://git-scm.com/download/win) 即可获得 Git Bash。安装脚本会自动通过 `winget` → `choco` → `scoop` 补全缺失依赖。

## 1. 安装

```bash
# 基础版（零学习成本，静默守护）
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- base

# 增强版（完整武器库）
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- enhanced
```

> 脚本会自动安装 python3（如系统未安装），覆盖 brew / apt / yum / dnf / pacman / apk / winget / choco / scoop 共 9 种包管理器。

## 2. 启动 Claude Code

```bash
claude
```

## 3. 验证安装

```
/lx-status
```

你应该会看到带有绿色状态指示器的健康看板。

## 4. 触发一个 Gate

告诉 AI：

```
这个功能我已经改好了，应该没问题了，标记完成吧
```

预期结果 — Carror OS 拦截菜单：

```
⛔ Carror OS: 检测到未经验证的完成声明。
```

如果你看到这个菜单，说明 Carror OS 正在工作。AI 无法用言辞绕过它。

## 下一步

[十分钟入门](./first-10-minutes.md) — 所有核心功能的引导式体验。
