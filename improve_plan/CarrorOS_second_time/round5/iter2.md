# 迭代 2 — P2 lx-goal.py 参数守卫(F7)

> 2026-07-20 | 选取理由: 本日实证事故——`--help` 被当 goal 激活建锁,需人工清理;修复成本极低,防复发

## 施工内容

`.claude/skills/lx-goal/scripts/lx-goal.py` main() 分发前置守卫(原 782-789):

| 输入 | 原行为 | 新行为 |
|---|---|---|
| 无参数 | cmd_status | cmd_status(不变) |
| `-h`/`--help`/`help` | **当 goal 激活建锁** | 打印 usage,exit 0 |
| 未知 `-` 开头参数(如 `-x`) | **当 goal 激活建锁** | stderr 报错+usage,exit 2,不激活 |
| 非子命令文本 | 当 goal 激活 | 不变(设计内简写) |

## 验证证据

1. `--help` → usage 全量输出,rc=0,`.omc/tokens/2026-07-20/` 无新锁(仅本任务合法锁)
2. `-x` → `ERROR: 未知参数 '-x'`+usage,rc=2,无激活
3. 无参数 → status 正常显示当前目标,rc=0
4. 当前 goal 会话未被扰动: `is-active` rc=0
5. 回归: test-goal-mode-gate.py 12/12 PASS rc=0;py_compile OK

## 分数变化(自评口径)

| 项 | 前 | 后 | 依据 |
|---|---|---|---|
| UX 行为可预测 | 7 | **8** | F7 误激活消除+iter1 lib 分裂脑消除→import/CLI 行为确定 |
| UX 均分 | 7.43 | **53/70 = 7.57** | +1 |
| 24 项总加权 | 8.53 | **8.53(不变)** | 守卫属预防面,C9/E4 已高分,不再重复计 |
