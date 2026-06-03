# lx-race — 蜂群协调层

## 原子化声明

| 节点 | 路径 | 用途 |
|------|------|------|
| report_generator | `../../nodes/report_generator.md` | 聚合报告生成 |
| behavior_rules | `../../nodes/behavior_rules.md` | 派发/收集阶段行为约束 |

| 脚本 | 用途 |
|------|------|
| `scripts/race_manager.sh` | 状态引擎：register/status/report |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/coordination-flow.md` | coordination flow 阶段 |
| `references/cross-platform-arch.md` | cross platform arch 阶段 |
| `references/worker-protocol.md` | worker protocol 阶段 |

> 降级升级: @../references/oma/degradation-escalation.md
> 裁决链: @../references/oma/decision-chain.md
> 执行工作流: @../references/oma/execution-workflow.md

## 状态机

```
need_input → [register → dispatch → collect → report] → done
```

## 降级策略

> 降级升级: `@../references/oma/degradation-escalation.md`
> 裁决链: `@../references/oma/decision-chain.md`
> 执行工作流: `@../references/oma/execution-workflow.md`
> 链式承接: `@../references/oma/skill-chaining.md`

| 场景 | 主路径 | 降级 |
|------|--------|------|
| 无子任务 | register | 报告退出 |
| Task() API 不可用 | Task 派发 | run_in_background |
| 后台不可用 | run_in_background | 顺序执行 |
| 脚本缺失 | 脚本执行 | 提示重新安装 |
| 全部失败 | 聚合报告 | 不阻断父任务 |

## 跨平台架构 → `@references/cross-platform-arch.md`

核心哲学：Race 不做调度（复用平台 Task API），不做写锁（复用 OMA Lock），只做**状态跟踪 + 冲突协调**。

## 协调流程 → `@references/coordination-flow.md`

1. **Register** — `race_manager.sh register` 创建 `.omc/race/<parent>/` 状态树
2. **Dispatch** — 路径 A: Task()（Claude Code）/ 路径 B: run_in_background（5 平台）
3. **Collect** — `race_manager.sh status --all` 轮询
4. **Report** — `race_manager.sh report` 聚合所有 result.json

## Worker 协议 → `@references/worker-protocol.md`

环境变量 `RACE_PARENT_ID` / `RACE_SUBTASK_ID` / `RACE_SUBTASK_PATH`。
完成契约：写入 `$RACE_SUBTASK_PATH/result.json`（status + output）。

## 限制

- 不做调度引擎、不做写锁、不新增 Hook
- 复用 `owner.json` + `result.json` 格式
- 子任务独立可验收，避免依赖链
