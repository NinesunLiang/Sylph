# Context Composition — 每轮饲喂模板

## 顺序（固定，前缀稳定）

```text
[1] Slim System (CLAUDE.md + AGENTS.md)   ≤ 2.0K tokens  ← cache 友好
[2] Hot Card                                ≤ 1.5K tokens
[3] 当前文件切片 ≤2 文件                    ≤ 2.5K tokens
[4] 最近 ≤2 条工具预览                     ≤ 1.0K tokens
[5] 用户本轮指令                            ≤ 1.0K tokens
───────────────────────────────────────────────
可控合计                                    ≤ 8.0K tokens
CC 固定                                     ≈ 16K
───────────────────────────────────────────────
总 median                                   ≤ 24K
```

## 规则

- [1] 和 [2] 字段顺序永不变（前缀稳定，cache 友好）
- reviews/ 文档、完整 plan、Oracle 输出：**禁止注入**
- 文件切片 > 2 个 → PreTool G1 阻断
- 工具输出 > 200 行无分页 → PreTool G2 阻断
- 超过 soft budget → 写 handoff，非 L5 AutoCompact

## 参考文献

- Hot Card 实现: `.claude/scripts/lib/hot_card.py`
- 工具落盘: `.claude/scripts/lib/tool_store.py`
- 门禁: `.claude/hooks/pretool-gate.py`
