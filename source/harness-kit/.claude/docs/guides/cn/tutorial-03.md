# T03 — 亲手配置

> 📍 我能调什么 | [← T02](tutorial-02.md) | 下一篇：[T04 武器目录](tutorial-04.md) →

## Hook 开关

所有门禁都在 `.claude/harness.yaml` 中控制。关掉一个门禁只需要改一行：

```yaml
hooks_enabled:
  completion_gate: true   # 改 false = 不再拦假完成
  permission_gate: true   # 改 false = 不再拦危险命令
  privacy_gate: true      # 改 false = 取消 .env 保护
  context_guard: true     # 改 false = 取消上下文上限
```

**三方一致性**：开关（harness.yaml）↔ 脚本（hooks/*.sh）↔ 注册（settings.json）必须一致。任一缺失 hook 不生效。

## LSP — 给 AI 装上眼睛

一次安装，永久生效。AI 从"grep 摸黑"变"语义导航"：

```bash
# Python（必装）
pip install pyright

# Claude Code 插件
# 在 Claude Code 中运行: /plugin install pyright-lsp

# OpenCode: 在 opencode.json 中加 {"lsp": true}
```

| 无 LSP | 有 LSP |
|--------|--------|
| grep 搜代码——慢、不准、匹配注释 | LSP 语义导航——50ms 精确跳转 |
| 改完等 CI 才知道有没有错 | 改完立即看到类型错误 |
| 重构签名时手动找所有调用点 | findReferences 一键全量 |

---

← [T02 静默守护](tutorial-02.md) | 下一篇：[T04 武器目录](tutorial-04.md) →
📖 深入：[Hook 配置指南](hook-configuration.md) | [LSP 安装指南](lsp-setup.md)
