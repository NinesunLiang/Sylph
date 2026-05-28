.claude/docs/story/cn/story-21.md
# Story 21: context-cache 分层脱水注入

> v6.3.8 · Carror OS — 哲学#1(The Less,The More)+#7(文档优先)

## 问题

AGENTS.md 148KB 直接注入AI上下文, token消耗巨大。多源维护导致漂移。

## 解决方案

context-compressor.sh → context-cache.md (27.2x压缩) → pretool-rules-inject.sh 三层分频注入。

| Layer | 内容 | 频率 | 行数 |
|-------|------|------|------|
| L1 | 铁律+哲学+软完成语 | 每轮 | ~15 |
| L2 | 操作约束+反模式+架构 | 每5轮 | ~25 |
| L3 | 教训+禁止项+TODO | 每10轮 | ~20 |

## 架构原则

AGENTS.md → context-compressor.sh → context-cache.md (单源)
CLAUDE.md → @AGENTS.md → @.omc/state/context-cache.md (桥接)