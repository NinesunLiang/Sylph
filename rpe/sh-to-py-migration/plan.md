# Plan: sh → py 轻量化迁移

## 总策略
每步：**改 → 验证 → commit → 下一步**，不跨步。

## Scope
- 允许：`.claude/skills/lx-*/` `.claude/profiles/` `.claude/scripts/` `.claude/hooks/` `.claude/workflow-standard/` `.claude/_reserve/backup/` `template/` `source/lx-skills-v5/` `source/harness-kit/`
- 不允许：`packages/` `.opencode/` `scripts/` (运维) `source/` (安装)

---

## 步骤

### S1 — 清理死代码 + 备份层
**内容**：删除零引用 .sh + `_reserve/backup/` 整目录
**文件清单**：
- `.claude/hooks/hook-launcher.sh`
- `.claude/hooks/statusline-command.sh`
- `.claude/hooks/stop-lifecycle-wrapper.sh`
- `.claude/hooks/tests/run_pkg_c_acceptance.sh`
- `.claude/workflow-standard/provision.sh`
- `.claude/workflow-standard/deprovision.sh`
- `.claude/_reserve/backup/` (整目录)
- `.claude/scripts/auto-score.sh`
- `.claude/scripts/meta-oracle-agent-spawn.sh`
- `.claude/scripts/score-self-check.sh`
- `.claude/scripts/provision-worktree-hooks.sh`

**AC**：
- 确认被删文件不在 settings.json / SKILL.md 引用链上
- `git status` 只显示 deleted
- commit

### S2 — 清理模板 + 源镜像
**内容**：删除 `template/` `source/lx-skills-v5/` `source/harness-kit/` 中的 .sh

**AC**：
- template/**/*.sh 全删 (4个)
- source/lx-skills-v5/**/*.sh 全删 (4个)
- source/harness-kit/**/*.sh 全删 (4个)
- commit

### S3 — 转 validate-skill.sh → .py (最小，热身)
**内容**：读取 `.claude/scripts/validate-skill.sh` (657B)，逐行对等转 Python，更新引用方
**引用方**：`lx-skillify/SKILL.md` `lx-learner/SKILL.md` `lx-validate-skill/SKILL.md`

**AC**：
- validate-skill.py 语法通过 (`python3 -m py_compile`)
- 功能等价（bash -n = python3 -m py_compile）
- 所有 SKILL.md 引用 .sh→.py
- 删 validate-skill.sh
- commit

### S4 — 转 lx-stepwise.sh → .py (最小二)
**内容**：读取 369B，逐行对等转 Python

**AC**：
- lx-stepwise.py 语法通过
- SKILL.md 引用更新
- 删 .sh
- commit

### S5 — 转 merge-profile.sh → .py
**内容**：读取 8KB，逐行对等转 Python
**引用方**：`source/install.sh` 中的引用

**AC**：
- merge-profile.py 逻辑等价
- source/install.sh 引用更新
- 删 .sh
- commit

### S6 — 转 lx-goal.sh → .py
**内容**：读取 15KB，逐行对等转 Python
**引用方**：`lx-goal/SKILL.md`

**AC**：
- lx-goal.py 功能等价
- SKILL.md 引用更新
- 删 .sh
- commit

### S7 — 转 lx-ghost.sh → .py (收官)
**内容**：读取 19KB，逐行对等转 Python
**引用方**：`lx-ghost/SKILL.md`

**AC**：
- lx-ghost.py 功能等价
- SKILL.md 引用更新
- 删 .sh
- commit

### S8 — 终验
**AC**：
- `find . -name "*.sh" -not -path "*/.git/*" -not -path "*/packages/*" -not -path "*/.opencode/*" -not -path "*/scripts/*" -not -path "*/install.sh" -not -path "*/source/install.sh"` 输出为空
- `python3 -m py_compile` 对所有新 .py 通过
