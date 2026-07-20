# 迭代 1 — F2 hook 命令全量 $CLAUDE_PROJECT_DIR 锚定

> 2026-07-20 | 选取理由(实际效能): settings.json 10 条命令全相对路径;从子目录启动 Claude Code 时 hook spawn 失败,pretool-gate 等门禁**静默失效(fail-open)**——CarrorOS 守护承诺的破洞,且野外无任何告警

## 施工内容

| 动作 | 文件 | 说明 |
|---|---|---|
| 锚定 ×10 | `.claude/settings.json` | 9 hook 事件 + statusLine,`.claude/hooks/...` → `$CLAUDE_PROJECT_DIR/.claude/hooks/...`(官方 hook 环境变量,shell 执行期展开) |

未动 env 块(含敏感字段);hook-launcher 参数仍为短名(launcher 内部 $0 自锚定解析)。

## 验证证据

1. **JSON 校验+计数**: python json.load 通过;anchored=10 relative=0
2. **行为对照**(cwd=/tmp 模拟子目录启动):
   - 旧形式: `bash: .claude/hooks/hook-launcher.sh: No such file or directory`(spawn 失败=门禁缺位)
   - 新形式: `{"continue": true, "message": "PreToolGate: ALLOW tool=read"}`(门禁真实执行)
3. **回归六套件**: watermark 25 / oracle 31 / verify 20 / goal-mode 12 / launcher / pkg_c —— 全 PASS(watermark 活体态 stash+还原)

## 分数变化(自评口径)

| 项 | 前 | 后 | 说明 |
|---|---|---|---|
| 24 项总加权 | 8.65 | **8.65(不变)** | 评分表无对应格子——这正是"实际效能>评分"的典型:堵住的是评分看不见的静默失效洞 |
| C5 工具生命周期 | 9 | 9 | 已满分,锚定属加固 |

实际效能账: 门禁从"cwd 碰巧正确才工作"变为"任何启动目录都工作";fail-open 静默失保护类风险归零(对 9 hook+statusLine 全链)。
