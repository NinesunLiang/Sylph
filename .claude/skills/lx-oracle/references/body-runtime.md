# lx-oracle — 运行时验证模式（原 lx-oracle-meta）

> 基于 **Oracle-V（Verification Protocol）** 协议的运行时验证引擎。
> 方法论：**运行时验证**（实弹测试、bash 执行、交叉验证）。
> 倾向：偏松 — 不确定时运行时确认。
> 优势：深度优先 — 针对性证伪。
> 依赖 Oracle Agent 的静态输出做二次判断。

---

## 裁决范围

| 类型 | 检查项 | 输出 |
|------|--------|------|
| **G1: Token 进度** | token 中 done/total 是否匹配 | done / total / pass |
| **G2: 失败模式** | executor/audit 是否有 FAIL/ERROR/Traceback/timed out | 列出命中模式 |
| **G3: 通过证据** | 是否有 PASS/OK/exit code 0/0 failed | 有/无 |
| **G4: 哲学一致性** | 是否有软完成语、无证据断言 | 列出命中项 |
| **审计事件** | audit 中是否有 verify 事件记录 | 有/无 |

## 流程

### 1. 解析 task_id

```bash
python3 .claude/scripts/carros_base.py status
```

### 2. 执行 Meta-Oracle 审核

```bash
# 方式 A：直接运行时验证
python3 .claude/scripts/runtime_oracle_agent.py review \
  --task-id <task_id> \
  --token .omc/tokens/<date>/<task_name>.json \
  --executor .omc/tasks/<date>/<task_name>/executor.md \
  --audit-dir .omc/state/audit

# 方式 B：G1-G4 完整评分
python3 .claude/scripts/meta_oracle.py score --task <task_id>
```

### 3. 读取裁决

```bash
# 运行时验证结果
cat .omc/state/runtime-oracle-verdicts/<task_id>/latest.json
# G1-G4 评分结果
cat .omc/state/meta-oracle-verdicts/meta-<task_id>-*.json | jq .
```

### 4. 裁决判定

| 裁决 | 含义 | 操作 |
|------|------|------|
| ACCEPT | token 完成 + 有通过证据 + 无失败 + 无软完成 + Meta ≥ 8.0 | 继续 |
| ADVISORY | 缺部分证据或 Meta 5.0-7.9 | 需确认后继续 |
| REJECT | 有失败证据或 Meta < 5.0 | 必须修正 |
| ESCALATE | 矛盾证据（token 完成但有失败标记） | 升级 |

## 输出格式（version 3 → 对齐 Oracle-V / Meta-Oracle）

```json
{
  "version": 3,
  "agent": "runtime_oracle",
  "task_id": "20260707-xxx",
  "verdict": "ACCEPT|REJECT|ADVISORY|ESCALATE",
  "risk": "LOW|MEDIUM|HIGH",
  "score": 0.0-10.0,
  "checks": {
    "token_progress": {"done": 3, "total": 3, "pass": true},
    "fail_hits": [],
    "pass_hits": ["PASS"],
    "soft_completion_hits": [],
    "has_verify_audit": true
  },
  "reasons": ["说明1", "说明2"]
}
```

Meta-Oracle G1-G4 评分输出（`meta_oracle.py score`）：

```json
{
  "task_id": "20260707-xxx",
  "final_score": 8.5,
  "verdict": "ACCEPT",
  "gates": {
    "G1": {"score": 8, "pass": true, "reasons": ["file:line 引用 5处"]},
    "G2": {"score": 10, "pass": true, "reasons": ["未发现范围外修改"]},
    "G3": {"score": 9, "pass": true, "reasons": ["有 VERIFIED 标记"]},
    "G4": {"score": 8, "pass": true, "reasons": ["哲学一致性检查通过"]}
  }
}
```
