# 迭代 3 — 回归脚本入库 scripts/run-regression.sh

> 2026-07-20 | 选取理由(实际效能): round5 实证痛点——手工 stash 舞蹈失败两轮才跑绿(首轮 bypass 干扰、次轮水位态干扰、脚本自身 rc 统计 bug)。该知识此前只存在于 /tmp 临时脚本,会话结束即蒸发。固化为库内脚本 = 未来每次施工一键验证

## 施工内容

| 动作 | 文件 | 说明 |
|---|---|---|
| 新增 | `scripts/run-regression.sh` | 六套件一键回归: temp-bypass+watermark 双 stash、trap EXIT 无条件还原、stash 残留防御(上次异常退出→人类可读报错并中止)、逐套日志 /tmp/carros-regression.*.log、pass/fail 计数+非零退出码 |

合规: `set -euo pipefail`、无 `&&` 串联、路径全引号、失败均有人类可读提示(bash-style 规则 1/2/3/6)。

## 验证证据

1. **自证运行**: `bash scripts/run-regression.sh` → 6 过 / 0 败,FINAL_EXIT=0
2. **还原验证**: watermark 活体态 stash 后 trap 还原成功(输出含 `[restore]`)
3. **幂等**: 可重复执行;stash 残留时拒绝运行并给出恢复指引(防御分支,代码审查级)

## 分数变化(自评口径)

| 项 | 前 | 后 | 说明 |
|---|---|---|---|
| 24 项总加权 | 8.70 | **8.70(不变)** | Evaluation 治理维已 9;此为流程加固,评分表外效能 |
| 治理 Evaluation | 9 | 9 | 六套件 battery 不变,变的是"一键可达性" |

实际效能账: 回归从"记得 stash 哪两个文件+手写 rc 统计"降为一条命令;验证门槛降低 → 未来每轮施工都更可能真跑验证(对抗 E3 虚假完成的 tooling 侧加固)。
