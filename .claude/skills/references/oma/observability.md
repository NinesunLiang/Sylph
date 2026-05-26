# 可观测性契约

> OMA 全系列统一遥测规范。数据写入 `.omc/state/oma-telemetry.yaml`。
> 引用：`@references/oma/observability.md`

## 通用采集点

| 采集点 | 触发条件 | 字段 |
|--------|---------|------|
| skill_invoked | skill 被调用 | `{skill, command, timestamp, duration_ms}` |
| skill_completed | 正常完成 | `{skill, command, result, evidence_count}` |
| skill_error | 错误码触发 | `{skill, error_code, command, context}` |
| gate_verdict | Oracle gate 裁决 | `{gate_id, verdict, reason, timestamp}` |

## 数据格式

```yaml
# .omc/state/oma-telemetry.yaml — 追加模式
- timestamp: "2026-05-09T14:00:00+08:00"
  skill: "lx-oma-hier"
  command: "sub-prds/domain-dashboard.md"
  event: skill_invoked
  duration_ms: 120000
  result: completed
```

## 环境前置检查

- `.omc/state/` 存在 → 正常写入
- 不存在 → 静默跳过，报告末尾注明

## 存储

- 追加模式，单文件
- 超过 500 行 → 归档 `archive/oma-telemetry-{date}.yaml`

## Skill 特定采集点

### hier
- `hier_started` — `{input_path, expected_domains[]}`
- `hier_completed` — `{output_dir, sub_prd_count, quality_score}`
- `hier_entity_found` — `{entity_name, domain_assignment}`
- `hier_gate_passed` — `{orthogonal_count, dependency_resolution}`

### split
- `split_started` — `{input_path, sub_prd_id, feature_count}`
- `split_completed` — `{feature_count, scaffolding_files, coverage_pct}`
- `split_interface_verified` — `{total_interfaces, assigned, unassigned}`
- `split_scaffolding_done` — `{directories_created, files_created}`

### gov
- `gov_reconcile_started` — `{target_path, feature_count}`
- `gov_reconcile_completed` — `{changes_count, L1, L2, L3}`
- `gov_propagate_dryrun` — `{changes_previewed}`
- `gov_propagate_executed` — `{features_updated[], chg_ids[]}`
- `gov_audit_passed` — `{drift_count, severity_distribution}`
- `gov_conflict_resolved` — `{conflict_id, verdict, time_to_resolve_h}`
