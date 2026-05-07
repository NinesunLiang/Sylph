# First 10 Minutes — 快速体验 Carror OS

> **目标**：10 分钟内看到第一个 Gate 生效。
>
> 你不需要理解所有概念。跟着走一遍，就会明白 Carror OS 在做什么。

---

## 0. 前提

- 你使用 **Claude Code**（或 OpenCode / Codex CLI）
- 你的终端可以运行 `curl` 或 `git clone`

---

## 1. 安装（30 秒）

进入你想被 Carror OS 接管的项目目录，一行命令：

```bash
curl -fsSL https://raw.githubusercontent.com/anomalyco/carror-os/main/install.sh | bash -s -- base
```

安装完成后，你的项目下会多出 `AGENTS.md` 和 `.claude/` 目录。

---

## 2. 检查是否安装成功（30 秒）

启动 Claude Code：

```bash
claude
```

输入指令：

```
/lx-status
```

你会看到一个健康面板。如果看到绿色状态，说明 Carror OS 正在静默守护你。

---

## 3. 第一个 Gate：触发假完成拦截（3 分钟）

这是最核心的 aha moment。

在 Claude Code 中，对 AI 说：

```
这个功能我已经改好了，应该没问题了，标记完成吧
```

**期望结果**：

```
⛔ Carror OS: 检测到未经验证的完成声明。
    "应该没问题了" 是软完成语，不符合证据门禁。

   请选择:
   1. 运行测试重试
   2. 强制覆盖（需说明理由）
   3. 压缩上下文后继续
```

如果看到以上菜单 — **恭喜，Carror OS 正在工作**。
这意味着 AI 不能再说一句"应该好了"就糊弄过去。它必须提供真实验证证据。

---

## 4. 第二个 Gate：拦截危险命令（2 分钟）

继续对 AI 说：

```
请帮我删除 /tmp/test 目录
```

**期望结果**：

```
⛔ Carror OS: 检测到危险操作。
   rm -rf 已被物理阻断。

   请选择:
   1. 写入标记文件继续
   2. 取消操作
```

---

## 5. 查看审计记录（1 分钟）

输入：

```
/lx-status
```

你会看到面板上记录了刚才被拦截的操作。所有 AI 行为都被追踪。

---

## 6. 快速了解你在用什么

| 概念 | 一句话 |
|------|--------|
| **Gate（门禁）** | AI 做危险/虚假操作前物理拦截，不是"建议不做"，是"做不了" |
| **Context（上下文）** | AI 在长对话中会"变笨"，Carror OS 在 80% 时物理熔断防止毁坏代码 |
| **Audit（审计）** | AI 做了什么全被记录，可回溯、可复查 |
| **Workflow（工作流）** | 从零散指令升级为有纪律的 RPE 开发流程 |

---

## 7. 下一步

你已经体验了 Carror OS 的核心能力。接下来：

| 场景 | 路径 |
|------|------|
| 直接开始用 | 保持 Base 安装，AI 写代码时 Gate 们在后台静默守护你 |
| 想了解更多特性 | 阅读 [全特性参考](../governance/features.md) |
| 想跑完整验收测试 | 进入 [AI 事故防御验证](../tests/ai-incident-defense-verification.md) |
| 只想用安全门禁 | Harness Only — 现有 Base 安装已包含 |
| 想要主动工作流 | 升级到 Enhanced — `bash install.sh enhanced` |
| 不确定选哪个 | 先 Base 用一周，感觉需要更多再升级 |

---

**现在让 AI 写代码。出问题时，Carror OS 会拦住。**
