---

name: lx-validate-skill

version: v4.0.0

description: "验收新 skill 是否遵循原子化架构规则。检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等 11 项规则。"

complexity: beginner
when_to_use: "Use after creating a new skill. Trigger: 'validate skill', 'check skill', 'new skill review', 'skill audit'."

model: haiku

argument-hint: "[skill-name, default: all lx-* skills]"

paths:

 - ".claude/skills/lx-*/SKILL.md"

harness_version: ">=1.1.0"
role: "Skill atomization compliance validator — 11-rule architecture check"
execution_mode: stepwise

triggers:
  - "/lx-validate-skill"
---

# Skill 原子化规则校验器

## 原子化声明

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机|
|------|------|----------|
|`scripts/validate_skill.py` | Skill 三层结构合规性验证 | 验证执行阶段 |

> 本 skill 遵循 [skill-atomization-guide.md](../../skill-atomization-guide.md) 架构分层。

### 使用的通用节点
| 节点 | 路径 | 用途|
|------|------|------|
|report_generator | `../../nodes/report_generator.md` | 校验报告生成|
|behavior_rules | `../../nodes/behavior_rules.md` | 校验阶段行为约束 |
|interactive_prompt | `../../nodes/interactive_prompt.md` | 无参数时引导式问答 |

### 引用的通用 Schema
| Schema | 路径 | 用途|
|--------|------|------|
|verdict | `../../schemas/atomic/verdict.yaml` | 校验判定 |

### 引用的 task_sys 组件
| 组件 | 路径 | 用途|
|------|------|------|
|统一交付 Schema | `../../task_sys/unified_delivery_schema.md` | 输出格式统一 |

### 状态机
本 skill 使用**私有 scan→report 流程**，不引用 `orchestrator.md`。
**核心状态映射**: need_clarification → executing → [scan → validate → report] → done

### 私有节点
本 skill 无私有节点。校验逻辑由 `.claude/scripts/validate-skill.sh` 脚本执行。

---

## 执行流程

### Step 0: 入口检查

```bash
s
t
-f .claude/scripts/validate-skill.sh && echo "script=yes" || echo "script=no"
```

脚本缺失 → 输出引导信息，提示创建校验脚本。

### Step 1: 执行校验
运行校验脚本：

```bash
# 校验单个 skillbash .claude/scripts/validate-skill.sh lx-{name}

# 校验所有 skillbash .claude/scripts/validate-skill.sh
```

### Step 2: 解析结果
校验脚本输出 11 项检查结果：
| # | 规则 | 检查内容|
|---|------|---------|
|R1 | 文件存在 | SKILL.md 存在|
|R2 | frontmatter | YAML frontmatter 存在|
|R3 | 原子化声明 | `## 原子化声明` 区块存在|
|R4 | 节点表 | `### 使用的通用节点` 表存在|
|R5 | Schema 表 | `### 引用的通用 Schema` 表存在|
|R6 | 状态机 | `### 状态机` 声明存在|
|R7 | 私有节点 | `### 私有节点` 声明存在|
|R8 | 节点引用 | 至少引用 1 个 `@../../nodes/`|
|R9 | Schema 引用 | 至少引用 1 个 `schemas/atomic/`|
|R10 | 无私有 nodes | 无 `skills/lx-*/nodes/` 目录|
|R11 | 无私有 schemas | 无 `skills/lx-*/schemas/` 目录 |\|

### Step 3: 输出报告
**✅ 全部通过**：

```## Skill 原子化校验报告 ✅

### 校验范围- Skill: {name}- 规则数：11

### 结果：通过- 错误：0- 警告：0
```
**⚠️ 有错误/警告**：

```## Skill 原子化校验报告 ⚠️

### 校验范围- Skill: {name}- 规则数：11

### 结果：{N} 错误, {M} 警告

#### 错误列表| 规则 | 问题 | 修复建议 ||------|------|---------|| R3 | 缺少原子化声明 | 添加 ## 原子化声明 区块 || ... | ... | ... |

#### 警告列表| 规则 | 问题 | 建议 ||------|------|------|| R6 | 缺少状态机声明 | 添加 ### 状态机 声明 || ... | ... | ... |
```

## 错误恢复- 脚本执行失败 → 手动执行 `bash .claude/scripts/validate-skill.sh` 查看原始输出- skill 不存在 → 提示可用 skill 列表

## 中止条件- 无 `.claude/scripts/validate-skill.sh` → "校验脚本缺失"报告- 无 lx-* skills → "无 skill 可校验"报告

## 执行
路由命中校验请求时：

```bash
n
3 .claude/skills/lx-validate-skill/scripts/validate_skill.py \ --skill {skill_name} --skills-dir .claude/skills
bashpython3 .claude/skills/lx-validate-skill/scripts/validate_skill.py \ --skill {skill_name} --skills-dir .claude/skills

```
读取 JSON：`passed=true` → 合规；`violations` → 报告违规。

## 链路追踪报告
路由命中"查看执行路径" / "链路分析" / "token 节省" 时：

```bash
# 完整执行路径 + 错误路径 + Token 节省画像python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py
# 仅 Token 节省分析（JSON 输出）python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only
# 过滤指定特性python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --feature {feature_name}
```读取三个数据
源
：- `.omc/state/skill-trace.jsonl` ← update_progress.py 写入（路由路径）- `.omc/state/error-dna.json` ← error-dna.sh 写入（错误路径）- `.omc/state/read-tracker.txt` ← read-tracker.sh 写入（文件读取）

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|validate_skill.py 执行失败 | 脚本验证 | 手动检查 SKILL.md 是否含必填字段|
|skill 目录不存在 | 报错 | 提示用户确认路径|
|验证结果有警告 | 继续 | 列出警告，不阻断（violations 才阻断）|\|

## 渐进式披露检查
路由命中"检查渐进式披露"或"check progressive disclosure"时：

```bash
n
3 .claude/skills/lx-validate-skill/scripts/check_progressive_disclosure.py \ --all --skills-dir .claude/skills
bashpython3 .claude/skills/lx-validate-skill/scripts/check_progressive_disclosure.py \ --all --skills-dir .claude/skills
```
读取 JSON：`total_violations=0` → 合规；有 violations → 报告并建议修复。


