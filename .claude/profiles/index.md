# profiles/ — 项目语言 Profile

> 每种语言一个子目录，各含独立的 `harness.yaml` 和 `settings.json` 配置。
> 用于在不同语言项目下使用 CarrorOS 治理。

| Profile | 用途 |
|---------|------|
| `base/` | 基础默认配置 |
| `enhanced/` | Enhance 模式附加配置 |
| `go/` | Go 语言项目配置 |
| `python/` | Python 语言项目配置 |
| `rust/` | Rust 语言项目配置 |
| `node/` | Node.js 语言项目配置 |

## 使用方式

在项目根目录创建对应语言 profile 的软链接，或复制配置到项目 `.claude/`。
