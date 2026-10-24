# 0022. 人本门禁：只 ask 不 block，用户命令必须单行脚本

**日期**: 2026-10-24
**来源**: 用户「在 CarrorOS 的治理下永远不再出现多行脚本让用户到终端执行」+「CarrorOS 只能ask_user . 绝不block」；AskUserQuestion 选择「全部改成 ask」
**状态**: 已采纳（D-032 / D-033）

## 上下文

两个独立故障指向同一条设计缺陷：

1. **命令交付**：AI 多次把多行/超长命令交给用户粘贴，终端折行后 zsh 拆成多条执行。
   规则文件只有提示级约束（Rule 6「>120 字符」），连续三次失效。
2. **阻断语义**：UserPromptSubmit 钩子因 `git rev-parse --show-toplevel` 找到嵌套仓库、
   相对路径找不到 `hook-launcher.py`，Python 以退出码 2 结束；Claude Code 把退出码 2
   解释为**阻断**。用户看到的是「CarrorOS 不让我提问」，实际是基础设施坏了。

共同根因：**把「机器没看清」和「人类不许做」混成同一个出口**。

## 决策

1. **新增 Stop hook 门禁**：每轮结束前扫描 `last_assistant_message`；
   多行命令块 / 绝对路径 / 超过 60 显示列的命令 → `decision: block` 强制重写。
   唯一放行形态：单行 `bash .omc/scripts/<name>.sh`。
2. **交互模式一律 ask**：`_block` / `_redirect` / night-deny / hook 故障，
   全部输出 `permissionDecision: ask`，由人类在宿主里选择；不再 deny。
3. **仅 goal（无人）模式保留 deny**：没有人能回答 ask，保留 deny + 自纠引导防卡死。
4. **路径基准改用 `${CLAUDE_PROJECT_DIR}`**：官方变量指向会话启动时的项目根，
   不再依赖 `git rev-parse` 与当前 cwd。
5. **基础设施故障绝不阻断**：钩子找不到/崩溃/超时 → ask 或放行，永不产生退出码 2 的阻断。

## 后果

- 好处：人不会因为工具坏了被锁在门外；所有拦截都变成人类可见的选择。
- 代价：安全护栏从「硬拦」降为「问一句」；误点允许的风险转由人承担。
- 兜底：门禁违规留痕 `.omc/state/audit/<date>.jsonl`；`stop_hook_active` 与官方
  8 次续写上限防止 Stop hook 死循环。

## 改动清单

| 文件 | 改动 |
|---|---|
| `.claude/hooks/stop-user-command-gate.py` | 新增 Stop 门禁（fail-open） |
| `.claude/hooks/test_stop_user_command_gate.py` | 13 个契约测试 |
| `.claude/settings.json` | 注册 Stop；路径基准改 `${CLAUDE_PROJECT_DIR}` |
| `.claude/rules/terminal-safety.md` | Rule 6 收紧为单行/不折行/相对路径 |
| `.claude/hooks/index.md` | 登记 Stop 门禁 |
| `.claude/references/anti-patterns.md` | 新增 L7 |
| `.claude/hooks/hook-launcher.py` | 故障转 ask，不再 rc 2 |
| `.claude/hooks/pretool_gates/helpers.py` | `_block` / `_redirect` 交互模式改 ask |
| `.claude/hooks/carroros-night-deny.py` | 不改：夜跑即无人值守，ask 会卡死，属「无人模式保留 deny」例外 |
