# Context Watermark 三段式水位检测

> owner 规格(2026-07-20 裁决): <50% 安全 / ≥50% 提醒 compact / ≥70% 只读 / ≥80% 强制
> 实测: 每轮尾读 transcript usage;执行: PreToolUse 门

## 四级水位

| 水位 | 范围 | 行为 |
|------|------|------|
| 🟢 SAFE | 0-50% | 无操作 |
| 🟡 REMIND | 50-70% | 每 5 轮注入 `🟡 W: 63% — 建议 /compact 释放上下文` |
| 🟠 READONLY | 70-80% | 注入警告 + pretool-gate 阻断写工具(Write/Edit/MultiEdit/NotebookEdit) |
| 🔴 FORCE | 80%+ | pretool-gate 阻断**全部**工具,立即运行 /compact |

## 实测方法(limit 从 settings.json 模型名自动推断)

- 数据源: hook payload 的 `transcript_path`,尾读 512KB 找最近一次 assistant `usage`
- `used = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`
  (每轮 cache_read 重放几乎全部历史 → 最后一次 usage ≈ 当前上下文总量)
- limit 自动推断: env.ANTHROPIC_MODEL 含 "1m" → 1M,否则 200K
- 覆盖: `CARROROS_CONTEXT_LIMIT=<N>` 环境变量

## 集成点(真实链路)

1. **实测** `.claude/hooks/pretool-user-approve.py`(UserPromptSubmit,每轮):
   算水位 → 写 `.omc/state/context-watermark.json` + 同步 token `session.context_watermark`
2. **执行** `.claude/hooks/pretool-gate.py`(PreToolUse,watermark 门排第一):
   读 state 文件;≥80 全阻断 / ≥70 阻断写工具;state 过期(>1800s)fail-open
3. **决策** `.claude/scripts/context_engine.py compact_decision`(L2_ENHANCE):
   ≥80 COMPACT_NOW / ≥50 COMPACT_SOON / 否则 CONTINUE
4. **离线调试** `.omc/scripts/context_watermark.py --used N [--limit N]`:
   同规格独立计算器,退出码 0/1/2 = SAFE·REMIND/READONLY·FORCE

## 调用方式(离线)

```bash
python3 .omc/scripts/context_watermark.py --used 85000
```

返回 JSON:
```json
{"used": 85000, "limit": 1000000, "pct": 50.0, "level": "REMIND", "action": "inject_warning", ...}
```

退出码: 0=SAFE, 1=REMIND(≥50), 2=READONLY/FORCE(≥70)。
