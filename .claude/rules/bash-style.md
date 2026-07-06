# Bash Style Rules（Carror OS 专用）

适用于：所有 bash / sh / install.sh / hook / release 脚本

## Rule 1：禁止使用 `&&` 串联关键命令
❌ cmd1 && cmd2 && cmd3
✅ 分行写，或显式判断返回值

## Rule 2：所有脚本必须 `set -euo pipefail`
❌ 没有
✅ 脚本第一行之后立刻写

## Rule 3：路径永远加引号
❌ bash source/harness/xxx.sh
✅ bash "source/harness/xxx.sh"

## Rule 4：禁止 `$(cat <<EOF)` 写 git commit
❌ git commit -m "$(cat <<EOF"
✅ git commit -m "summary" -m "body"

## Rule 5：禁止裸 curl 下载二进制
❌ curl | bash
✅ 下载 → 校验 → 再执行

## Rule 6：命令失败时必须有人类可读提示
❌ exit 1
✅ echo "ERROR: xxx failed" >&2 && exit 1

## Rule 7：多行命令用 heredoc，不用 -c
❌ python3 -c "..."
✅ python3 - << 'PY'

## Rule 8：不假设 GNU 工具一定存在
❌ sed -i
✅ sed -i.bak