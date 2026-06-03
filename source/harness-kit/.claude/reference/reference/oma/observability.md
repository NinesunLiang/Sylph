# 可观测性契约

> OMA 全系列 skill 共享的遥测规范。各 skill 的特定采集点在其自身的 `references/observability.md` 中定义。

## 通用采集点

所有 OMA skill 必须记录：

| 采集点 | 触发条件 | 记录字段 |
|--------|---------|---------|
| skill_invoked | skill 被调用 | `{skill_name, input_path, mode}` |
| skill_completed | skill 正常完成 | `{skill_name, output, duration_ms}` |
| skill_error | skill 执行出错 | `{skill_name, error_code, stack}` |
| gate_verdict | Oracle 门禁裁决 | `{gate_id, verdict, reason}` |

## 各 Skill 特定采集点

| Skill | 采集点 | 定义位置 |
|-------|--------|---------|
| lx-oma-hier | hier_started/completed/entity_found/gate_passed | `skills/lx-oma-hier/references/observability.md` |
| lx-oma-orch | advance/skill_route/dev_mark | `skills/lx-oma-orch/references/observability.md` |
| lx-oma-split | split_started/completed/interface_verified | `skills/lx-oma-split/SKILL.md#可观测性` |
| lx-oma-gov | reconcile/propagate/audit | `skills/lx-oma-gov/SKILL.md` |

## 记录格式

```json
{"ts": "ISO8601", "skill": "lx-oma-xxx", "event": "skill_completed", "fields": {...}}
```
