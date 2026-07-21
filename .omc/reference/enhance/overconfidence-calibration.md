# 过度自信防线 (E7)

> L2 Enhance Gate: verify_gate 校准回溯 + overturn 追踪
> 检测决策前后矛盾：此前 BLOCKED/REJECTED/WARN 的 step 突然 VERIFIED

## 检测条件

| 条件 | 行为 |
|------|------|
| 某 step 此前有 BLOCKED/REJECTED/WARN 记录，当前 VERIFIED | 写 `calibration_overturn` 记录 + stderr 告警 |
| VERIFIED + overturn | 要求人工回溯验证断言有效性 |
| 纯 VERIFIED（无 overturn） | 正常记录 `calibration_assertion` + 置信度 |

## E7 硬化（v7.2+）

### 变更摘要

| 项 | 旧行为 | 新行为 |
|----|--------|--------|
| calibration 日志 | 仅简单记录 VERIFIED + assertion | **+ confidence(置信度) + overturn 检测** |
| 置信度 | 无 | 规则匹配率: matched / (matched + missing) |
| 决策历史扫描 | 无 | 扫描 `.omc/audit/*.jsonl` 该 step 所有历史决策 |
| overturn 记录 | 无 | 新事件类型 `calibration_overturn` |
| stderr 告警 | 无 | overturn 触发 `⚠️ [E7:calibration_overturn]` |

### calibration 日志格式

正常断言:
```json
{
  "event_type": "calibration_assertion",
  "timestamp": "...",
  "step": "S1",
  "decision": "VERIFIED",
  "matched_rules": ["command match: echo ok exit=0"],
  "confidence": 1.0,
  "assertion": "step S1 全部规则通过（置信度=1.0）"
}
```

Overturn 记录:
```json
{
  "event_type": "calibration_overturn",
  "timestamp": "...",
  "step": "S1",
  "decision": "VERIFIED",
  "overturn": true,
  "previous_decisions": ["BLOCKED", "WARN"],
  "assertion": "step S1 overturn alert: 此前 2 次非通过(BLOCKED,WARN)→VERIFIED",
  "confidence": 0.8,
  "matched_rules": ["..."],
  "missing_rules": ["..."]
}
```

### overturn 检测流程

```
1. verify_gate VERIFIED 判定后
2.   读取 .omc/audit/*.jsonl
3.   筛选 event_type=verify_decision + step=当前step
4.   ├─ decision∈{BLOCKED,REJECTED,WARN} → 加入 _prev_decisions
5.   └─ 全部扫完
6.   if _prev_decisions 非空:
7.     写入 calibration_overturn 记录
8.     输出 stderr 告警
9.   else:
10.    写入 calibration_assertion 记录
```

## 集成点

- `.claude/scripts/verify_gate.py` — main() 中 E7 校准段
- `.omc/state/calibration-log.jsonl` — calibration 日志文件
- `.omc/audit/*.jsonl` — 历史决策源

## 配置

无配置文件。overturn 只要发现 ≥1 条历史非通过决策即触发（阈值=1）。
