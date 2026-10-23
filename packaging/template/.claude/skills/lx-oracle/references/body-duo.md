# lx-oracle — 双 Agent 审核模式（原 lx-oracle-review）

> 编排 **Oracle agent**（静态分析，偏紧）+ **Meta-Oracle**（运行时验证，偏松）
> 双上下文独立执行审核，互不影响。
> 适用于 verify/archive 前置门禁、架构终审、Release 发布。

---

## 裁决等级

| 等级 | 裁决链 | 含义 |
|------|--------|------|
| ✅ ACCEPT | Oracle agent ACCEPT + Meta-Oracle ACCEPT + Meta ≥ 8.0 | 全部通过 |
| ⚠ ADVISORY | 任一 ADVISORY 或 Meta 5.0-7.9 | 建议确认后继续 |
| ❌ REJECT | 任一 REJECT 或 Meta < 5.0 | 必须修正 |
| 🔺 ESCALATE | 任一 ESCALATE 或矛盾裁决 | 报 Boss |

## 完整流程

### 1. 解析 task_id

```bash
python3 .claude/scripts/carros_base.py status
```

### 2. 双 Agent 审核

用 `oracle_agent.py --mode duo` 同时调 Oracle Agent + Meta-Oracle + G1-G4 聚合：

```bash
python3 .claude/scripts/oracle_agent.py review \
  --task-id <task_id> \
  --mode duo \
  --plan .omc/tasks/<date>/<task_name>/plan.md \
  --executor .omc/tasks/<date>/<task_name>/executor.md \
  --token .omc/tokens/<date>/<task_name>.json \
  --audit-dir .omc/state/audit
```

### 3. 读取三份裁决

```bash
# Oracle agent 静态
cat .omc/state/static-oracle-verdicts/<task_id>/latest.json
# Meta-Oracle 运行时
cat .omc/state/runtime-oracle-verdicts/<task_id>/latest.json
# Meta-Oracle G1-G4 聚合
cat .omc/state/meta-oracle-verdicts/meta-<task_id>-*.json | jq .
```

### 4. 判定

- **ACCEPT**: Oracle agent ACCEPT + Meta-Oracle ACCEPT + Meta ≥ 8.0 且全部门禁 pass
- **ADVISORY**: 任一 ADVISORY 或 Meta ≥ 5.0
- **REJECT**: 任一 REJECT 或 Meta < 5.0
- **ESCALATE**: 得分矛盾（如 Oracle agent REJECT 但 Meta-Oracle ACCEPT）或任何 ESCALATE

## 独立执行（单 agent 审核）

如果只需 Oracle agent 或 Meta-Oracle 之一，可直接调单个模式：
- `static` — 只做 Oracle agent 静态分析（偏紧、广度优先）
- `runtime` — 只做 Meta-Oracle 运行时验证（偏松、深度优先）

## 输出目录

| Agent | 路径 |
|-------|------|
| Oracle agent | `.omc/state/static-oracle-verdicts/{task_id}/` |
| Meta-Oracle | `.omc/state/runtime-oracle-verdicts/{task_id}/` |
| Meta-Oracle G1-G4 | `.omc/state/meta-oracle-verdicts/` |
| Bypass | `.omc/state/oracle-bypass/` |
