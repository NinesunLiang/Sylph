# lx-validate-skill 报告模板

> 校验报告和链路追踪的输出格式模板。按需加载。

## 校验报告

### 全部通过

```
## Skill 原子化校验报告 ✅

### 校验范围
- Skill: {name}
- 规则数：11

### 结果：通过
- 错误：0
- 警告：0
```

### 有错误/警告

```
## Skill 原子化校验报告 ⚠️

### 校验范围
- Skill: {name}
- 规则数：11

### 结果：{N} 错误, {M} 警告

#### 错误列表
| 规则 | 问题 | 修复建议 |
|------|------|---------|
| R3 | 缺少原子化声明 | 添加 ## 原子化声明 区块 |
| ... | ... | ... |

#### 警告列表
| 规则 | 问题 | 建议 |
|------|------|------|
| R6 | scripts/ 含非 `.py`/`.sh` 文件，或脚本语法检查失败 | 删除非白名单脚本；对 `.py` 修复至 `python3 -m py_compile` 通过，对 `.sh` 修复至 `bash -n` 通过 |
| ... | ... | ... |
```

## 链路追踪

```bash
# 完整执行路径 + 错误路径 + Token 节省画像
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py

# 仅 Token 节省分析（JSON 输出）
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only

# 过滤指定特性
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --feature {feature_name}
```

读取三个数据源：
- `.omc/state/skill-trace.jsonl` ← update_progress.py 写入
- `.omc/state/error-dna.json` ← error-dna.sh 写入
- `.omc/state/read-tracker.txt` ← read-tracker.sh 写入

## 渐进式披露检查

```bash
python3 .claude/skills/lx-validate-skill/scripts/check_progressive_disclosure.py \
  --all --skills-dir .claude/skills
```

读取 JSON：`total_violations=0` → 合规；有 violations → 报告并建议修复。
