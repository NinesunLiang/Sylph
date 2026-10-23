# Pipeline 集成契约

> OMA skill 通过 `state/pipeline.yaml` 与 orch 编排器集成。
> 引用：`@reference/oma/pipeline-contract.md`

## 管线阶段

```
hier → [og-001] → oma → [og-002] → gov → [og-00N] → rpe → dev (parallel)
```

## 入口（编排模式）

仅 `/lx-oma split` 可接收 `--pipeline <id>`。收到该参数时：

**硬约束**：
1. `<id>` 不存在、不可读或解析失败：返回 `BLOCKED`，不得降级为内存状态或人工声明。
2. `lx-rpe` 不得接收该参数；RPE 只接收 OMA 从磁盘状态解析出的 `BASE_DIR`。
3. pipeline 阶段推进必须先原子落盘，再向下游发出动作。

**解析步骤**：
1. 读 `state/pipeline.yaml`
2. 检查当前阶段状态
3. 使用 pipeline 中的 `path` 作为输入

## 出口

| Skill | 写入 pipeline |
|-------|-------------|
| hier | `sub_prds[].{id, path, status: hier_done}`, `stages.hier = completed` |
| split | `features[].{id, path, stage: oma_created}`, `stages.oma = completed` |
| gov | **不直接写** — 输出 `gov-latest-report.yaml`，orch 消费后更新 |

## 原子写入

写 tmp → `os.rename(tmp, pipeline.yaml)`（RPE-014 教训）

## 接口版本

| 接口 | v | 读写方 |
|------|:-:|--------|
| stages | v1 | 所有读，orch 写 |
| sub_prds[] | v1 | hier/split 写，orch 读 |
| oracle_gates[] | v1 | orch 写/读，其余只读 |
| features[] | v1 | split 写，orch 读 |
| gov-latest-report.yaml | v1 | gov 写，orch 读 |

> 向后兼容：不兼容变更创建 v2 key，旧 key 保留 1 迭代周期。
