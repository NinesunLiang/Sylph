# CarrorOS LSP 安装指南 — AI 语义眼睛

> CarrorOS 启动时自动探测您的平台和 LSP 状态（`ecosystem-probe`）。  
> 本指南帮助您完成一次性安装，让 AI 获得 IDE 级别的代码理解能力。

---

## 为什么需要 LSP？

| 无 LSP（默认） | 有 LSP |
|---|---|
| AI 用 grep 搜代码 — 慢、不准、匹配注释 | AI 用语义导航 — 50ms 精确跳转定义 |
| 改完代码等 pytest 跑完才知道有没有错 | 改完立即看到类型错误（diagnostics） |
| 重构 API 签名时手动找所有调用点 | findReferences 一键全量，不漏一个 |
| 大项目 grep 扫几千行 → 5000+ tokens | LSP 精确返回 ~500 tokens |

**安装一次，永久生效。**

---

## 1. Claude Code 用户

### 1.1 安装语言服务器

```bash
# Python（必装 — SWE-bench 主要语言）
pip install pyright

# TypeScript / JavaScript（可选）
npm install -g typescript-language-server typescript

# Go（可选）
go install golang.org/x/tools/gopls@latest
```

### 1.2 安装 Claude Code LSP 插件

在 Claude Code 会话中运行：

```
/plugin install pyright-lsp@claude-plugins-official
```

### 1.3 验证

```
/status
```

应显示：`LSP servers: pyright`（或其他已安装的语言服务器）

---

## 2. OpenCode 用户

OpenCode **内置 40+ LSP 服务器**，只需启用。

### 2.1 启用 LSP

在项目根目录创建 `.opencode.json`：

```json
{
  "lsp": true
}
```

### 2.2 设置环境变量

```bash
export OPENCODE_EXPERIMENTAL=true
```

### 2.3 验证

启动 OpenCode，打开 `.py` 文件 — LSP 服务器自动启动。

---

## 3. Codex CLI 用户

Codex CLI **无原生 LSP**，通过 Serena MCP 桥接。

### 3.1 安装 Serena

```bash
pip install serena-agent
```

### 3.2 配置 Codex MCP

编辑 `~/.codex/config.toml`：

```toml
[mcps.serena]
command = "uvx"
args = ["--from", "serena-agent", "serena", "start", "--context", "codex"]
```

### 3.3 重启 Codex

```bash
codex
```

---

## 验证 LSP 是否生效

在 AI 会话中测试：

```
"帮我找到 calculate_score 函数的定义"
```

- **有 LSP**: AI 直接用 goToDefinition 精确定位，<100ms
- **无 LSP**: AI 用 grep 全文搜索，30-60s，可能返回错误位置

---

## 常见问题

**Q: pip install pyright 报错？**
```bash
# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyright
```

**Q: Claude Code 插件安装后不生效？**
- 确认 Claude Code 版本 ≥ v2.0.74
- 尝试 `npx tweakcc --apply`（社区补丁）
- 查看日志：`claude --debug`

**Q: OpenCode LSP 不启动？**
- 确认 `.opencode.json` 中 `lsp: true`
- 确认 `OPENCODE_EXPERIMENTAL=true` 环境变量已设置

**Q: Codex + Serena 工具调用失败但实际成功？**
- 已知 Codex UI bug，忽略错误提示，检查实际效果
