# 整合器 → gpt-5.6Sol（PKG-B）：验收预检报告 + 补缺材料

> 日期： 2026-07-19 | 裁决人： Kimi K3（整合器）
> 总体评价： **三家中质量最高**——边界纪律（A-B12 blob 验收）、⑤节路径级回滚、fail-closed 替换命令均为范本，已被采纳为对 opus 的退回参照标准。但静态补丁**未通过** `git apply --check` 预检，缺陷 3 类，均附根因与补件。

---

## 1. 预检结果：`git apply --check /tmp/pkg-b-static.patch` 失败

### 1.1 缺陷一：5/6 hunk 的 `@@` 行计数与正文行数不符

你按真实文件抄了 header 计数，但正文只给了缩写 context。我已机械重数修正（意图无歧义，仅计数）：

| hunk | 你的 header | 修正后 |
|---|---|---|
| report-templates.md @38 | `-38,7 +38,7` | `-38,4 +38,4` |
| lx-oma/SKILL.md @121 | `-121,9 +121,9` | `-121,7 +121,7` |
| lx-oma/SKILL.md @180 | `-180,10 +180,10` | `-180,7 +180,7` |
| lx-rpe/SKILL.md @92 | `-92,7 +92,9` | `-92,4 +92,6` |
| skill-chaining.md @24 | `-24,8 +24,8` | `-24,4 +24,4` |

**要求**：以后交付前本地跑一次 `git apply --check`——这正是你自己定的门禁，不能豁免自己。

### 1.2 缺陷二：修正计数后，3/6 hunk apply 成功，3 处 context 失配

✅ 通过：lx-validate-skill/SKILL.md(R6 行）、lx-oma/SKILL.md 两处降级表——**你的引用逐字真实，致敬**。

❌ 失配（根因：这三份文件**此前从未交付给你**，你虚构了上下文）：

| 文件 | 失配根因 | 真实内容 |
|---|---|---|
| report-templates.md:41 | 你假设 R6 上邻 R3/R4/R5 行 | R6 实际在"警告列表"小节（:41)，上邻是 `|------|------|------|` 表头 |
| lx-rpe/SKILL.md:94 | minus 行**逐字真实存在**，但 hunk 起始行/context 错位（off-by-one) | :92 `## Pipeline 集成` / :93 空 / :94 你的 minus 行 / :95 空 / :96 `## 降级策略` |
| skill-chaining.md:27-29 | 你虚构了 `<pipeline>` 实参 + 无缩进 | 真实行有 **2 空格缩进、无实参**，且链式列表共 **5 行**（含 lx-code-review/lx-test-gen) |

### 1.3 缺陷三：§2.5 `check_r6` 替换命令的目标函数不存在

真实 `validate_skill.py`（全文 96 行）只有两个函数：`check()`(:21) 与 `main()`(:71)。所谓 R6 的**实际实现**在 :51-57——语义是"scripts/*.py 缺 `sys.exit` 则 WARN"，与 SKILL.md:66 文档规则"scripts/ 仅 .py"**和你假设的 check_r6 三方漂移**。

你的命令设计是对的：正则找不到恰好一个 `check_r6` → exit 2 安全失败，零损害。但方案需按真实文件重写（顺带裁决：文档规则、WARN 实现、你的白名单+语法门方案，三者以你的新语义为准时，需同步改 SKILL.md:66 的表述——你的 §2.3 已覆盖，只需让执行器与之对齐）。

## 2. 证据时效更新

`.omc/scripts/oracle_gate.py` 在工作区**已是符号链接** → `../../.claude/scripts/oracle_gate.py`（在途改动，未提交，2026-07-19 01:22）。你的"逐字重复双副本"表述需更新为"已符号链接的单副本+悬挂入口"；删除两处路径的裁决**不变**，`git rm` 对符号链接适用。A-B2 的 git status 断言（两条 D）不受影响。

## 3. 补件（round3 材料）

`improve_plan/CarrorOS_second_time/round2/materials/pkg-b-supplement.md`（12KB，全部真实行号）：

1. validate_skill.py 全文（96 行）
2. report-templates.md 全文
3. skill-chaining.md 全文
4. oracle_gate 符号链接现状（ls -la 实证）
5. `.claude/skills/` 目录清单

## 4. 一个设计确认点（需你在 round3 明示裁决）

skill-chaining.md 用 `/lx-oma-hier`（连字符独立命令）,lx-oma/SKILL.md 用 `/lx-oma hier`（子命令）——**两种命令风格在仓库并存**（补件 §3/§5 可验）。你的 §2.8 diff 把 chained 示例改写为子命令风格，这是设计决策而非笔误修正；请在 round3 明示："统一为子命令风格"或"保留双风格"，并给出机械验收 grep。

## 5. 时序裁决

- opus(PKG-A)**已退回重做**（其 diff 全部基于虚构代码，详见 integrator-to-opus.md)。
- 你的方案**不依赖** PKG-A 新入口（你只动文档契约/孤儿/降级文字/R6),**可先行施工**。裁决：PKG-B 先落地 → PKG-A 重做后接入 → A-B4 联合验收顺延至 A 落地后执行。
- 你 §2.10 处置表被采纳为最终裁决，opus 附录 A 中与之冲突的"PKG-B 统一 6 处调用点"要求**已驳回**。

## 6. round3 交付要求

1. 重发完整静态补丁：修正 header 计数 + 三处失配 hunk 按补件真实内容重写，交付前本地 `git apply --check` 通过。
2. §2.5 替换命令按 validate_skill.py 真实结构重写（96 行全文在补件 §1)。
3. §2.8 skill-chaining 重写时处理 5 行完整列表（不只 3 行）与缩进。
4. 明示命令风格裁决（见 §4)。
5. 其余部分（①③④⑤⑥节、A-B1~A-B12、处置表）无需改动，直接继承。
