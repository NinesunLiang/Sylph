# T02 — 静默守护

> 📍 它在做什么 | [← T01](tutorial-01.md) | 下一篇：[T03 亲手配置](tutorial-03.md) →

大多数时候你不会感觉到 Carror OS 的存在。你感觉到的是：

- AI 更不容易"假完成"了
- 敏感信息不会轻易被读进去
- 规则不会在长对话里漂移
- 新会话不需要反复重讲上下文

## 5 分钟看到第一个门禁

```bash
# 1. 安装（30秒）
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- base

# 2. 启动 Claude Code
claude

# 3. 对 AI 说这句话
# "这个功能我改好了，应该没问题了，标记完成吧"
```

**如果看到 `⛔ 检测到未经验证的完成声明`** → Carror OS 正在工作。AI 无法用言辞绕过它。

## 日常你被守护的地方

| 场景 | 守护机制 | 表现 |
|------|---------|------|
| AI 说"做完了"但没有证据 | completion-gate | 硬阻断，要求出示 VERIFIED |
| AI 想读 .env 文件 | privacy-gate | 硬阻断——绝对禁阅 |
| AI 想 rm -rf | permission-gate | CAPTCHA 验证码，人类批准 |
| AI 改文件但没读过 | edit-guard | 拦截——先读后写 |
| 对话超过 90% token | context-guard | 只让读不让写 |

---

← [T01 设计理由](tutorial-01.md) | 下一篇：[T03 亲手配置](tutorial-03.md) →
📖 深入：[Hook 配置指南](hook-configuration.md)
