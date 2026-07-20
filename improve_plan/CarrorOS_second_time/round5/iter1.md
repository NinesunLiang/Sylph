# 迭代 1 — P1 双源统一(F1/F2/F3)

> 2026-07-20 | 选取理由: 实际效能最高——三处运行期行为分裂(离线水位说谎/K1 半失效/Stop 飞轮跑旧逻辑且参数被遮蔽),且 git status 无感

## 施工内容

| 动作 | 文件 | 说明 |
|---|---|---|
| 内容合并 | `.claude/scripts/lib/flywheel.py` | 采纳 .omc 新版(7/15): attempt=N 归一化去重、真实 count、`retry>=2 or count>=3` recurring、`run_flywheel` 尊重 task_dir 参数(旧版遮蔽参数全扫) |
| 符号链接 | `.omc/scripts/lib/flywheel.py` → `../../../.claude/scripts/lib/flywheel.py` | lib 源=tracked .claude |
| 符号链接 | `.omc/scripts/lib/error_dna.py` → `../../../.claude/scripts/lib/error_dna.py` | K1 噪声过滤(.claude 侧 7/20 新版)对 .omc 消费者生效 |
| 符号链接 | `.claude/scripts/context_watermark.py` → `../../.omc/scripts/context_watermark.py` | watermark 源=.omc(tracked 且 476a08b 更新的 50/70/80 版);先例=carros_base.py |
| 备份 | /tmp/r5_backup/{omc-flywheel,omc-error_dna,claude-flywheel}.py.bak | .omc lib 原 untracked 无 git 安全网,先备份 |

## 验证证据

1. **行为**: watermark 两路径同输出(60%→REMIND 50-70% 段);.omc 路径 error_dna K1 生效("t"→quarantined,正常错误不误杀);flywheel attempt 去重 3→1 组且 count=3+recurring;run_flywheel task_dir 尊重+落盘;两路径同 inode
2. **回归**: 六套全 rc=0(watermark 25/25、oracle 31/31、verify 20/20、goal-mode 12/12、launcher、pkg_c)
3. 消费方排查: `context_watermark` 无模块 import(纯 CLI);lib 消费方(stop-flywheel.py:41/posttool-gate.py:144/runtime_verify*.py)经 symlink 同源

## 分数变化(自评口径)

| 项 | 前 | 后 | 依据 |
|---|---|---|---|
| C8 可维护性 | 7 | **8** | 三处双源愈合,单一 tracked 源;F9 嵌套 state 残留(→人类清单)挡 9 |
| E6 自我矛盾 | 7 | **8** | F1/F2/F3 消除;F4 kernel.md(冻结)+F6 幽灵@残留挡 9 |
| 学习笔记积累 | 7 | **8** | K1 全侧生效+飞轮新逻辑全侧运行 |
| **C 加权** | 8.57 | **8.67** | +10 |
| **E 加权** | 8.29 | **8.41** | +13 |
| **治理均分** | 8.14 | **8.29** | +1 |
| **24 项总加权** | **8.42** | **1893/2220 = 8.53** | **+0.11** |
| 24 项最低分 | 7.0 | **8.0** | 回到门禁线 |
