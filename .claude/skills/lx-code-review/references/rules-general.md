# 通用代码审查规则（语言无关）

> 适用于所有语言。语言专项规则见 `rules-{lang}.md`。
> 每条规则包含唯一 ID、严重级别、类别，支持按 ID 屏蔽/按严重级筛选。

## 规则元数据格式

```yaml
id: generic.<category>.<descriptive-name>
severity: critical | high | medium | low
category: security | correctness | maintainability | performance | style
languages: [*]  # * 表示全语言适用
autofix: safe | review | suggest
confidence: high | medium | low
```

## 安全类（security）

### `generic.security.hardcoded-secret` 🔴 CRITICAL
- 密码/ApiKey/Token 硬编码在代码中
- 内网IP/域名直接写在配置或代码里
- 数据库连接串明文
- 自动修复等级: suggest（仅标记，不自动改）

### `generic.security.weak-crypto` 🔴 CRITICAL
- `Math.random()` 用于安全场景（密码/Token/会话ID）
- 自定义加密算法代替标准库
- 自动修复等级: suggest

### `generic.security.log-leak` 🟡 HIGH
- 日志输出 Token/密码/完整请求体
- 错误堆栈直接暴露给用户
- 自动修复等级: review

## 正确性类（correctness）

### `generic.correctness.missing-error-handling` 🟡 HIGH
- 外部调用（HTTP/DB/文件/网络）未处理异常
- 错误被 `catch {}` 或 `// ignore` 静默吞掉
- 自动修复等级: review

### `generic.correctness.null-safety` 🟡 HIGH
- 函数返回可能为空但调用方未防御
- 连续链式调用无空值保护
- 自动修复等级: review

## 可维护性类（maintainability）

### `generic.maintainability.long-function` 🟠 MEDIUM
- 函数超过 200 行
- 函数职责不单一（做了IO/业务/日志混合）
- 自动修复等级: suggest

### `generic.maintainability.duplicate-code` 🟠 MEDIUM
- 超过 10 行相似代码块
- 可提取公共函数/工具类
- 自动修复等级: suggest

### `generic.maintainability.stale-comment` 🟠 MEDIUM
- 过时注释误导
- 明显复制粘贴留错
- 自动修复等级: safe

## 性能类（performance）

### `generic.performance.inefficient-query` 🟢 LOW
- N+1 查询模式
- 循环内数据库调用
- 自动修复等级: suggest

## Auto-fixer 安全分级说明

| 等级 | 行为 | 示例 |
|------|------|------|
| **safe** | 自动落盘，无需确认 | 格式化、import清理、过时注释删除 |
| **review** | 生成 patch，等人工确认 | 错误处理补充、空值防御 |
| **suggest** | 仅输出建议文本，不生成代码 | 硬编码密钥、函数过长拆解 |
