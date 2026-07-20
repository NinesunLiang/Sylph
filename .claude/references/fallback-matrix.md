<!-- ENHANCE-ONLY: 高级特性的降级矩阵 -->
# Fallback Matrix — L2→L1 降级策略

> L2 Enhance: 当 context 过高 / 模型异常 / 连续失败时，自动降级到 L1
> 降级矩阵配置: `fallback_matrix.yaml`

## 降级触发条件

| # | 条件 | 检测方式 | 阈值 | 降级动作 |
|---|------|---------|------|---------|
| 1 | Context 过满 | context_watermark | ≥80% | L2→L1 全降级 |
| 2 | 连续 3 步未 Verify | audit 检查 | 连续 3 tick 无 verify 事件 | 暂停复杂操作 |
| 3 | 3 次 Oracle 执行时间超过 30s | Oracle 响应时间 | 单次 >30s | 跳过 Oracle（ACCEPT 默认） |
| 4 | 模型返回格式异常（非 JSON） | parse error 计数 | 连续 3 次 | 降级 L2→L1 |
| 5 | 人类长时间无介入 | last_user_message | >3600s | 不降级，但限制 L2 操作范围 |

## 声明式降级矩阵 YAML

```yaml
fallbacks:
  - trigger: "context_full"
    condition: "context_pct >= 80"
    actions:
      - "watermark_to_compact"
      - "disable_oracle"
      - "demote_to_L1"
  - trigger: "oracle_slow_3x"
    condition: "oracle_rtt_3x_avg > 30000"
    actions:
      - "skip_oracle:ACCEPT"
      - "log_audit"
  - trigger: "no_verify_3_ticks"
    condition: "consecutive_no_verify >= 3"
    actions:
      - "pause_complex_ops"
      - "log_audit"
  - trigger: "parse_error_3x"
    condition: "consecutive_parse_errors >= 3"
    actions:
      - "demote_to_L1"
      - "reset_token_chain"
```

## 降级路径

- **L2→L1**: 关闭水位检测、关闭 Oracle、关闭飞轮。回到 L1 4 步工作流（Plan→Step→Verify→Archive）
- **L1→非活跃**: session-handoff 写入后停止

## 调用方式

```bash
python3 .omc/scripts/fallback_matrix.py [--check <触发点ID>]
```

返回 JSON:
```json
{"should_fallback": true, "action": "demote_to_L1", "reason": "context_pct=83% > 80%"}
```
