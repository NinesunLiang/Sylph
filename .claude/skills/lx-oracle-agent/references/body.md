# lx-oracle-agent — Oracle Agent 静态分析审核

> 基于 **Oracle-D（Decision Protocol）** 协议的偏紧静态分析引擎。
> 方法论：静态检查（文件存在、注册完整、代码逻辑、scope 合规）。
> 倾向：偏紧 — 不确定时假设有问题。
> 优势：广度优先 — 全文件扫描。
> 不执行代码、不运行测试、不依赖运行时证据。

---

## 审核原则

1. **哲学不可违背** — 违反 **#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人本)>#2(增益)>#1(少)** 操作必须 REJECT
2. **铁律不可绕过** — AI 试图 workaround 时，Oracle 必须 REJECT 并要求直面问题
3. **0 信任** — 独立验证所有前提，不假设调用方已做尽职调查
4. **裁决留痕** — 每条裁决必须附带 file:line 证据，不可仅输出 verdict

## 裁决范围

| 类型 | 检查项 | 输出 |
|------|--------|------|
| **Scope 一致性** | executor 出现的文件是否都在 plan 声明范围内 | 列出越界文件 |
| **危险路径** | 是否引用 `.ssh/` `.env` `credentials` `/etc/` 等 | 列出命中模式 |
| **危险命令** | 是否包含 `rm -rf` `sudo` `chmod 777` `publish` `deploy` 等 | 列出命中模式 |
| **证据完整性** | file:line 引用是否指向实际存在的文件且行号合理 | 丢失/越界统计 |
| **治理文件豁免** | AGENTS.md / kernel.md / index.md / CLAUDE.md 允许 plan 外修改 | 豁免不告警 |

## 流程

### 1. 解析 task_id

```bash
python3 .claude/scripts/carros_base.py status
```

### 2. 执行 Oracle Agent 审核

```bash
python3 .claude/scripts/static_oracle_agent.py review \
  --task-id <task_id> \
  --plan .omc/tasks/<date>/<task_name>/plan.md \
  --executor .omc/tasks/<date>/<task_name>/executor.md
```

### 3. 读取裁决

```bash
cat .omc/state/static-oracle-verdicts/<task_id>/latest.json
```

### 4. 裁决判定

| 裁决 | 含义 | 操作 |
|------|------|------|
| ACCEPT | 结构一致、无危险模式 | 继续 |
| ADVISORY | 轻微越界或引用缺失 | 需确认后继续 |
| REJECT | 严重危险或大量越界 | 必须修正 |
| ESCALATE | 高风险但不确定 | 升级至 Meta-Oracle 或报 Boss |

## 输出格式（version 3 → 对齐 Oracle-D）

```json
{
  "version": 3,
  "agent": "static_oracle",
  "task_id": "20260707-xxx",
  "verdict": "ACCEPT|REJECT|ADVISORY|ESCALATE",
  "risk": "LOW|MEDIUM|HIGH",
  "score": 0.0-10.0,
  "checks": {
    "plan_files": ["..."],
    "executor_files": ["..."],
    "outside_plan_files": [],
    "dangerous_paths": [],
    "dangerous_commands": [],
    "file_line_refs": {
      "checked": 5,
      "missing": 0,
      "out_of_range": 0,
      "pass": true
    }
  },
  "reasons": ["说明1", "说明2"]
}
```
