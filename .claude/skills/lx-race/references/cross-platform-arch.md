# 跨平台架构

```
                    ┌──────────────────────────────┐
                    │     lx-race (协调层)           │
                    │  注册→派发→收集→报告             │
                    └──────┬───────────────┬───────┘
                           │               │
              Claude Code 路径        其他 5 平台路径
              Task()/TeamCreate     run_in_background
              原生子 Agent 派发       顺序/后台执行
                           │               │
                           └───────┬───────┘
                                   ▼
                         race_manager.sh
                       (bash + 文件 I/O)
                        全平台统一状态层
                                   │
                                   ▼
                              OMA Lock
                        (pretool-write-lock.sh)
```

## 平台支持矩阵

| 平台 | 子 Agent | race_manager.sh | OMA Lock | 备注 |
|------|:-------:|:---------------:|:--------:|------|
| Claude Code | ✅ Task() | ✅ bash | ✅ Hook | 原生子 Agent |
| OpenCode | ❌ | ✅ bash | ✅ AGENTS.md | 退化为后台/顺序 |
| Codex CLI | ❌ | ✅ bash | ✅ AGENTS.md | 退化为后台/顺序 |
| Gemini CLI | ❌ | ✅ bash | ⚠️ 有限 Hook | 事件模型最弱 |
| Qwen Code | ❌ | ✅ bash | ✅ AGENTS.md | 二级平台最强 |
| Cursor | ❌ | ✅ bash | ⚠️ 仅 Prompt | 仅 2 Hook |

## 核心哲学

Race 不做调度，只做**状态跟踪 + 冲突协调**：
- 调度 → 复用平台原生 Task() API
- 写锁 → 复用 OMA Lock
- 状态 → `race_manager.sh`（全平台通用）
