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