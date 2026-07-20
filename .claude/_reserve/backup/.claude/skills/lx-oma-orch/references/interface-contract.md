# 跨 Skill 接口契约

> orch 协调 4 个下游 skill，通过 pipeline.yaml 或中间文件交换数据。

## 接口矩阵

| skill | 调用方 | 读取来源 | 写入目标 | 写入格式 | 读取方式 |
|-------|--------|---------|---------|---------|---------|
| lx-oma-hier | orch (advance) | sub-prds/domain-{id}.md | state/pipeline.yaml | `sub_prds[].{id, path, status: hier_done}` | orch 读取 status 后推进 |
| lx-oma-split | orch (advance) | sub-prds/domain-{id}.md + pipeline.yaml features[] | state/pipeline.yaml | `features[].{id, path, stage: oma_created}`, `sub_prds[].status=oma_done` | orch 读取后生成 og gate |
| lx-oma-gov | orch (advance) | prd/{sub_prd}/{feature}/prd.md + master-prd.md | `.omc/state/gov-latest-report.yaml` | governance report | orch 读取 report → 更新 pipeline.yaml |
| lx-rpe | 手动或 orch (run) | prd/{sub_prd}/{feature}/prd.md | state/progress.md (per feature) | tasks 进度状态 | orch 读取 state/progress.md 更新 pipeline |

## 数据流

```
orch advance →
  hier: 调 lx-oma-hier → hier 写 pipeline.yaml → orch 确认 → 等待 gate
  oma:  调 lx-oma-split → split 写 pipeline.yaml → orch 确认 → 等待 gate
  gov:  调 lx-oma-gov → gov 写 gov-latest-report.yaml → orch 读 report 更新 pipeline
  rpe:  调 lx-rpe → rpe 写 progress.md → orch 汇总 → 等待 gate
```

## 接口版本锁定

| 接口 | 版本 | 变更影响范围 |
|------|------|-------------|
| pipeline.yaml stages | v1 (keys: {hier,oma,gov,rpe,dev}) | 所有 4 个 skill 读，orch 写 |
| pipeline.yaml sub_prds[] | v1 (keys: {id, path, status, oracle, features[]}) | hier/split 写，orch 读 |
| pipeline.yaml oracle_gates[] | v1 (keys: {id, from_stage, to_stage, status}) | orch 写/读 |
| pipeline.yaml features[] | v1 (keys: {id, path, stage, oracle}) | split 写，orch 读 |
| gov-latest-report.yaml | v1 | gov 写，orch 读 |

> v1 接口不兼容变更必须创建 v2 新 key，旧 key 保留至少 1 个迭代周期。
