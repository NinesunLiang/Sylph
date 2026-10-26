<!-- ENHANCE-ONLY: 高级终端安全规范 -->
# Terminal Safety Rules（终端命令输出规范）

适用范围：所有涉及 git / bash / python / gh / sed / awk / jq 的命令  
目标：100% 可复制、不炸、不隐式失败

## Rule 1：多行命令必须用 heredoc
- ✅ 使用：`python3 - << 'PY' ... PY`
- ❌ 禁止：`python3 -c "..."`

## Rule 2：Git 命令不合并
- ✅ 分开：git add / git commit / git push 各一行
- ❌ 禁止：`git add ... && git commit ... && git push`

## Rule 3：文件路径每行一个
- ✅ 多行 git add，每行一个路径
- ❌ 禁止同一行堆砌大量路径（尤其含 source/）

## Rule 4：commit message 禁止 `#`
- ✅ 用中文冒号/括号替代
- ❌ 禁止 `#` 任何位置（Git 会截断）

## Rule 5：脚本修改 JSON/YAML 必须幂等
- 不改则不写文件
- 可重复执行
- 不破坏未知字段

## Rule 6：给用户的命令必须单行、不折行、只调用临时脚本（2026-10-24 人类裁决）
- ✅ 唯一允许的形态：`bash .omc/scripts/<name>.sh`（相对路径，单行）
- ✅ 脚本用 Write 落盘到 `.omc/scripts/`，首行后立刻 `set -euo pipefail`
- ❌ 禁止多行命令块 / 带 `\` 续行 / 绝对路径 / 超过 60 显示列的命令
- ❌ 禁止把 `python3 -c "..."` 之类的长命令交给用户执行
- 强制：`.claude/hooks/stop-user-command-gate.py`（Stop hook）在每轮结束前扫描最终回复，
  违规即 block 并强制重写；不依赖 AI 自觉
- 工具侧沿用：单条 Bash 命令 > 30 字符必须脚本化