---

name: lx-pre-commit

version: v2.0.0

description: "提交前质量门禁：项目类型检测 → 编译 → 测试 → 代码审查。操作层由 scripts/ 脚本执行，AI 负责结果解读和路由决策。"

when_to_use: "Use when user says 'pre-commit', 'commit check', '提交前检查', or before git commit."

model: sonnet

argument-hint: "[--skip-review]"

harness_version: ">=1.1.0"
role: "Pre-commit quality gate — compile, test, lint, coverage check"
execution_mode: stepwise

triggers:
  - "/lx-pre-commit"
---

# lx-pre-commit — 提交前质量门禁

## 原子化声明

### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| behavior_rules | `../../nodes/behavior_rules.md` | 行为约束 |
| auto_fixer | `../../nodes/auto_fixer.md` | P0 自动修复 |

### scripts/（确定性执行层）
| 脚本 | 用途 | 调用时机 |
|------|------|---------|
| `scripts/detect_project.py` | 检测项目类型（go/node/python/rust）| Step 0 |
| `scripts/run_checks.py` | 运行编译+测试门禁序列 | Step 1 |

### references/（按需加载）
| 文件 | 加载时机 |
|------|---------|
| `references/checklists/danger-signals.md` | 发现异常时加载 |

---

## 执行流程

### Step 0 — 检测项目类型

```bash
n
3 .claude/skills/lx-pre-commit/scripts/detect_project.py
bashpython3 .claude/skills/lx-pre-commit/scripts/detect_project.py
```

读取 JSON → `type`（go/node/python/rust）+ `runner`（vitest/jest/npm）。未知类型 → 输出"无法识别项目类型，请手动指定" → 停止。

### Step 1 — 运行门禁检查

```bash
n
3 .claude/skills/lx-pre-commit/scripts/run_checks.py \ --type {type} --runner {runner}
bashpython3 .claude/skills/lx-pre-commit/scripts/run_checks.py \ --type {type} --runner {runner}
```
读取 JSON：- `blocked: false` → 门禁通过 → Step 2- `blocked: true` → 输出失败步骤 → **阻塞提交**，提示修复命令
**降级策略**：| 场景 | 降级 ||------|------|| 脚本执行失败 | 直接调用 `go build ./...` / `npm test`，手动判断 || 测试框架未检测到 | 询问用户确认测试命令 |

### Step 2 — 代码审查（自动调用）
按项目类型路由：- Go → `Invoke the Skill tool with skill: "lx-code-review"`- 前端 → `Invoke the Skill tool with skill: "lx-react-review"`
P0 问题：加载 `@../../nodes/auto_fixer.md` 修复 → 重跑 Step 1。P1+ 问题：列出，不阻塞提交。

### Step 3 — 输出概览

```✅ lx-pre-commit 通过 类型：{go/node} 编译：✅ 测试：N passed 代码审查：P0=0
✅ lx-pre-commit 通过 类型：{go/node} 编译：✅ 测试：N passed 代码审查：P0=0
```

---

## 降级策略
| 场景 | 主路径 | 降级路径|
|------|--------|---------|
|lx-code-review 不可用 | 调用 skill | 跳过代码审查，标注"[代码审查已跳过]"|
|测试命令超时（>120s）| 等待完成 | 超时后报告"测试超时"，建议手动运行 |


