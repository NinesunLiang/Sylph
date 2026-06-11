# 执行模式

## stepwise（逐步）

```
规划 → 子任务1 → 验证 → 子任务2 → 验证 → ... → 最终验收
```

- 每个子任务完成后立即验证
- 验证失败修复后重新验证
- 适合：有依赖关系、复杂架构变更

## race（并行 — 后端 lx-race, 工具 race-tool.py）

```
规划 → [race-tool.py init] → [dispatch] → 并行派发 → 收集 → 合并 → 最终验收
```

- 规划阶段识别独立子任务
- `race-tool.py init` / `dispatch` / `timeout-check` 管理并行生命周期
- **depends_on** 字段自动处理任务间依赖
- **timeout-check** 自动超时检测 + 自动重试
- **recover** 自动恢复崩溃的 main agent
- `.omc/race/` 已废弃（由 race_manager.sh 维护），全部迁移到 `race-tool.py` + `.omc/plan/{date}/`
- 适合：多文件独立变更、无依赖批量修复
