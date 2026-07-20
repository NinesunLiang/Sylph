# advance 推进流程

## 检查 → 推进 → 更新

```
1. 读 pipeline.yaml，找当前阶段的 upstream Oracle gate
2. 若未裁决 → 提示人工: /lx-oma-orch gate <og-id> approve|reject
3. 若已 approved → 调用对应子 skill:
    hier → lx-oma-hier
    oma  → lx-oma-split
    gov  → lx-oma-gov
    其他 → 按 pipeline.yaml 路由
4. skill 完成 → 更新 pipeline.yaml
5. 人工确认阶段转换（非自动进入下一阶段）
```

## 阶段推进顺序

```
hier → [og-001] → oma → [og-002] → gov → [og-00N] → rpe → dev (parallel)
  (lx-oma-hier)    (lx-oma-split)  (lx-oma-gov)
```

`--force` 跳过 Oracle gate 检查。

## rpe → dev 边界

不调用子 skill，输出并行开发启动面板（列出 ready features + 终端命令）。

## 模式门禁路由

读取子 skill 的 `execution_mode` frontmatter：

| execution_mode | 路由行为 |
|---------------|---------|
| **race** | 注册为 Race 子任务 |
| **stepwise** | 执行 Stepwise 阶段流程 |
| direct/无 | 直接调用，无额外门禁 |

> 参考 `@../../nodes/mode_selector.md`
