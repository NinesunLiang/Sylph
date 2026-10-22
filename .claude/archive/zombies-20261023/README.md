# 归档：零引用脚本（2026-10-23）

按人类裁决「清理只保留和 AI 治理相关的」执行：非治理域的零引用脚本移出
`.claude/scripts/`，不删除（可随时 `git mv` 回原位）。

| 文件 | 原用途 | 为何归档 |
|---|---|---|
| `db_adapter.py` | Hermes 会话读取 + Obsidian 记忆宫殿适配器 | 个人数据管道，非治理域 |
| `lightweight_memory_tidy.py` | memory/user 压缩（char 限额裁剪） | 记忆整理，非治理域 |
| `notify_qq_pending.py` | QQ Bot 待确认通知 | 通知通道，非治理域 |

**保留**：`self_evolve.py`（自迭代流水线 cron 入口）—— 属 AI 治理/自迭代域。

## 恢复

```bash
git mv .claude/archive/zombies-20261023/<file>.py .claude/scripts/
```

## 背景

这 3 个文件在 2026-10-22 已由快照 commit 纳管（`3060bab`），但**纳管 ≠ 被引用**：
`zombie_scan` 判定它们零引用（代码/配置/文档均无提及）。归档后它们离开
`.claude/scripts` 扫描范围，归档防膨胀闸（C4）不再因它们 BLOCK。
