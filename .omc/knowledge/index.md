# knowledge/ — 升华管道数据

> 飞轮升华引擎的输出产物。
> `sublimation-log.jsonl` 记录升华事件，`claude-next.md` 为待验证的涌现知识。

| 文件 | 用途 |
|------|------|
| `sublimation-log.jsonl` | 升华事件日志（每次升华追加一行 JSON） |
| `claude-next.md` | 涌现知识待验证队列（人工审阅后升入 anti-patterns.md） |

## 管道流程

```
Error DNA → 升华引擎 → sublimation-log.jsonl
                      → claude-next.md (待审)
                      → anti-patterns.md (审后)
                      → kernel.md (审后+升华)
```
