# 执行模式

## stepwise（逐步）

```
规划 → 子任务1 → 验证 → 子任务2 → 验证 → ... → 最终验收
```

- 每个子任务完成后立即验证
- 验证失败修复后重新验证
- 适合：有依赖关系、复杂架构变更

## race（并行 — 后端 lx-race）

```
规划 → [lx-race 注册] → 并行派发 → 收集 → 合并 → 最终验收
```

- 规划阶段识别独立子任务
- `race_manager.sh register` 注册子任务
- 并行派发（Claude Code: Task() / 其他: run_in_background）
- OMA Lock 自动防护并发冲突
- `race_manager.sh report` 聚合结果
- 适合：多文件独立变更、无依赖批量修复
