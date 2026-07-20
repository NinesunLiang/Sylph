# Skill 原子化规则校验器

## 原子化声明

### scripts/
| 脚本 | 用途 |
|------|------|
| `scripts/validate_skill.py` | 11 项合规性验证 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/report-templates.md` | 报告输出/链路追踪/渐进式披露阶段 |

### 通用节点: report_generator, behavior_rules, interactive_prompt
### Schema: verdict.yaml
### 状态机: need_clarification → scan → validate → report → done
### 私有节点: 无。校验逻辑由脚本执行。

---

## 执行流程

### Step 0: 入口检查

```bash
test -f .claude/scripts/validate-skill.sh && echo "script=yes" || echo "script=no"
```

脚本缺失 → 输出引导信息，提示创建校验脚本。

### Step 1: 执行校验
运行校验脚本：

```bash
# 校验单个 skill
bash .claude/scripts/validate-skill.sh lx-{name}

# 校验所有 skill
bash .claude/scripts/validate-skill.sh
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
|R11 | 无私有 schemas | 无 `skills/lx-*/schemas/` 目录 |

### Step 3: 输出报告

见 @references/report-templates.md（校验报告模板：通过/错误/警告三种格式）。

## 错误恢复

- 脚本执行失败 → 手动执行 `bash .claude/scripts/validate-skill.sh`
- skill 不存在 → 提示可用 skill 列表

## 中止条件

- 无 `.claude/scripts/validate-skill.sh` → "校验脚本缺失"
- 无 lx-* skills → "无 skill 可校验"

## 执行

```bash
python3 .claude/skills/lx-validate-skill/scripts/validate_skill.py \
  --skill {skill_name} --skills-dir .claude/skills
```
读取 JSON：`passed=true` → 合规；`violations` → 报告违规。

## 链路追踪 & 渐进式披露

见 @references/report-templates.md（skill_trace_report.py + check_progressive_disclosure.py）。

## 降级策略
