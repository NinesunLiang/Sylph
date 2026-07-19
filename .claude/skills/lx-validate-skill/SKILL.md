---
name: lx-validate-skill
version: v4.0.0
description: "验收新 skill 是否遵循原子化架构规则。检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等 11 项规则。"
complexity: beginner
when_to_use: "Use after creating a new skill. Trigger: 'validate skill', 'check skill', 'new skill review', 'skill audit'."
argument-hint: "[skill-name, default: all lx-* skills]"
paths:
  - ".claude/skills/lx-*/SKILL.md"
harness_version: ">=6.3.0"
status: draft
role: "Skill atomization compliance validator — 11-rule architecture check"
execution_mode: stepwise
triggers:
  - "/lx-validate-skill"
nodes:
  - scanner                  # 按规则集扫描 skill（R1-R11）
  - report_generator         # 生成合规报告
  - behavior_rules           # 自洽检查
schemas:
  - atomic/scan_report       # 扫描报告
  - atomic/verdict           # 最终判定
  - atomic/finding           # 合规问题发现
---
# lx-validate-skill — 原子化架构合规检查

## 原子化声明

### 通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| scanner | `../../nodes/scanner.md` | 按 R1-R11 规则集扫描 skill |
| report_generator | `../../nodes/report_generator.md` | 生成合规检查报告 |
| behavior_rules | `../../nodes/behavior_rules.md` | 自洽检查 |

### Schema
| Schema | 路径 | 用途 |
|--------|------|------|
| scan_report | `../../schemas/atomic/scan_report.yaml` | 扫描报告 |
| verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |
| finding | `../../schemas/atomic/finding.yaml` | 合规问题发现 |

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `scripts/validate_skill.py` | 核心校验：R1-R11 规则引擎 | 全流程 |
| `scripts/skill_trace_report.py` | skill 依赖追踪报告 | review 阶段 |
| `scripts/check_progressive_disclosure.py` | 渐进式披露合规检查 | review 阶段 |
| `scripts/carror_dashboard.py` | 系统健康面板 | 运行时 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/report-templates.md` | 生成合规报告时 |
---

表

| 编号 | 规则 | 检查方式 |
|:----|:-----|:---------|
| R1 | frontmatter 包含必填字段 | yaml 解析 |
| R2 | SKILL.md 包含 nodes 声明 | `grep '^nodes:' SKILL.md` |
| R3 | SKILL.md 内联完整（无 body_ref） | 无 body_ref: 行 |
| R4 | 无私有 nodes/ 目录 | `ls skills/lx-*/nodes/` |
| R5 | 无私有 schemas/ 目录 | `ls skills/lx-*/schemas/` |
| R6 | scripts/ 仅允许 `.py` 与 `.sh`；`.py` 必须通过 `python3 -m py_compile`，`.sh` 必须通过 `bash -n`；其他扩展名一律失败 | 扩展名白名单 + 逐文件语法检查 |
| R7 | frontmatter 有 description | yaml 校验 |
| R8 | 至少引用 1 个 `../../nodes/` | grep SKILL.md |
| R9 | 至少引用 1 个 `../../schemas/` | grep SKILL.md |
| R10 | 无私有 nodes | 同 R4 |
| R11 | 无私有 schemas | 同 R5 |

## 执行流程

```
1. 确定检查目标（指定 skill 或 all）
2. 逐 skill 扫描 R1-R11（scanner 节点单规则执行）
3. 输出合规报告（含每条规则的 PASS/FAIL）
4. 打印改善建议
```

## 调用方式

```bash
# 检查单个 skill
/lx-validate-skill lx-goal

# 检查所有 skill
/lx-validate-skill all

# 检查特定目录
python3 .claude/skills/lx-validate-skill/scripts/validate_skill.py --skills-dir .claude/skills
```
