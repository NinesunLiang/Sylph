# Context Watermark 三段式水位检测

> L2 Enhance 核心: 0-40% 安全 / 40-70% 警戒 / 70%+ 临界
> 调用 `.omc/scripts/context_watermark.py`

## 三级水位

| 水位 | 范围 | 行为 |
|------|------|------|
| 🟢 安全 | 0-40% | 无操作 |
| 🟡 警戒 | 40-70% | tool 调用后注入一行警告 `🟡 W: 63%`，建议 compact |
| 🔴 临界 | 70%+ | tool 调用后强制注入警告 + 禁止 L2 复杂操作 |

## Token 计数策略

1. **优先**: tiktoken（离线本地，零延迟）
2. **回退**: char_count / 4（兜底）
3. **校准源**: API response 的 `input_tokens`（每次请求后校准）

## 调用方式

```bash
python3 .omc/scripts/context_watermark.py [--used <N>] [--limit <N>]
```

返回 JSON:
```json
{"used": 85000, "limit": 200000, "pct": 42.5, "level": "WARNING", "remark": "40-70%"}
```

## 集成点

- `completion-gate.py` 在每次 tool call 后注入水位
- `pretool-action-gate.py` 在 70%+ 时阻断 L2 复杂操作
