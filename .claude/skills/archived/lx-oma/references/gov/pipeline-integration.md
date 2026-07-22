# Pipeline 集成

> 本 skill **只读** `state/pipeline.yaml`。pipeline 写入由 `lx-oma-orch` 统一管理。

## 治理报告输出

每次命令执行后输出 `governance-report.yaml` 供 orch 消费：

```yaml
# → .omc/state/gov-latest-report.yaml
command: init|reconcile|propagate|status|audit
result: success|failure|no_changes|conflict
sub_prd: "<target>"
changes:
  - type: L1|L2|L3
    description: "<变更>"
    file: "<path>"
oracle_gate:
  action: create|update|skip
  verdict: approved|pending|rejected
features_updated:
  - id: "<feature-id>"
    status: "<new-status>"
```

## 命令 → orch 动作映射

| 命令 | orch 动作 |
|------|----------|
| init → success | stages.gov = initialized, auto-register features |
| reconcile → no_changes | stages.gov = completed |
| reconcile → success | 等待 propagate |
| reconcile → conflict | 等待人工 resolve |
| propagate → success | 更新对应 feature stage |
| status/audit | 只读，无操作 |

## 人工审核报告

```
=== 治理审核 ===
[ ] L1 变更全部自动归并？ [ ] L2 变更需确认？
[ ] L3 冲突已 resolve？ [ ] drift audit 符合预期？
报告：.omc/state/gov-latest-report.yaml
确认：/lx-oma-orch gate og-NNN approve
```
