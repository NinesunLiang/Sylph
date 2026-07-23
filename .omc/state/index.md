# state/ — 运行时状态文件

> 由 hook 和脚本自动读写。大部分文件不在 git 跟踪中。
> 删除后 hook 会在下次运行时重新生成。

## 系统状态

| 文件 | 来源 | 用途 |
|------|------|------|
| `lifecycle.json` | lifecycle_ssot | 生命周期 SSOT（goal/ghost 模式+计数器） |
| `handoff.json` | lifecycle_ssot | Handoff 计数器（written/claimed/items） |
| `workflow-state.json` | workflow hooks | 工作流状态恢复 |
| `hud-state.json` | agentic-ui | HUD 菜单状态 |
| `hud-stdin-cache.json` | agentic-ui | HUD 输入缓存 |

## 门禁/安全

| 文件 | 用途 |
|------|------|
| `hook-evidence.jsonl` | hook 证据记录 |
| `retry-budget.json` | 重试次数/预算跟踪 |
| `claim-audit-cold-warned` | Cold start claim 警告标记 |
| `.completion-evidence-*` | 完成门禁证据缓存 |
| `context-watermark.json` | 上下文水位状态 |

## 错误/审计

| 文件 | 用途 |
|------|------|
| `error-dna.jsonl` | Error DNA 记录（持续沉淀） |
| `error-signals.jsonl` | 错误信号 |
| `governance-audit.jsonl` | 治理审计记录 |

## Oracle 相关

| 文件/目录 | 用途 |
|-----------|------|
| `meta-oracle-overrides.md` | Meta-Oracle 手工覆写记录 |
| `meta-oracle-verdicts/` | Meta-Oracle 裁决缓存 |
| `oracle-verdicts/` | Oracle 裁决缓存 |

## 快照

| 目录 | 用途 |
|------|------|
| `snapshots/` | PreCompact 快照（压缩前保存状态） |
| `tokens/` | Token 运行时缓存 |

## 其他

| 文件 | 用途 |
|------|------|
| `last-user-prompt.md` | 最近用户 prompt |
| `compact-write.log` | Compact 写入日志 |
| `calibration-log.jsonl` | 校准日志 |
| `.harness-cache` | Harness 开关缓存 |
