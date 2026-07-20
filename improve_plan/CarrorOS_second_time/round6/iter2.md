# 迭代 2 — F1 lib 七对双源副本 symlink 统一

> 2026-07-20 | 选取理由(实际效能): round5 迭代1 愈合了 3 处**已分裂**双源,但 lib/ 下仍存 7 对**内容相同**的双源副本——完全相同的事故温床:任一侧未来被编辑即静默分裂,git 对 .omc 侧无感。消灭整个类别 > 等下次分裂再修

## 施工内容

| 动作 | 文件 | 说明 |
|---|---|---|
| 双源统一 ×7 | `.omc/scripts/lib/{autonomy,handoff_writer,hot_card,oracle_gate_light,phase3_oracle,tool_store,water_level}.py` | 逐文件 diff 确认相同 → mv 至 `/tmp/r6_backup/*.bak`(可逆,不用 rm) → symlink `../../../.claude/scripts/lib/X.py`(沿用 round5 flywheel/error_dna 既定模式,.claude 侧为 git 跟踪单源) |

## 验证证据

1. **逐文件前置 diff**: 7/7 内容相同才动;无 DRIFT SKIP
2. **导入测试**: `.omc/scripts` 路径下 `lib.*` 7/7 import 成功
3. **活体调用**: `water_level.get_water_detail()` 实测返回 `{level: safe, ratio: 0.191, controllable_tokens: 2286/12000}`(System A 检测链经 symlink 正常工作)
4. **回归六套件**: 全 PASS(watermark 活体态 stash+还原)
5. **复扫**: 全 lib 树双源对**清零**(扫描含 .claude/scripts/*.py 与 lib/*.py 双侧)

## 分数变化(自评口径)

| 项 | 前 | 后 | 依据 |
|---|---|---|---|
| C8 可维护性 | 8 | **9** | round5 挡 9 的两项均已闭合: 嵌套 state 出库(d2d8022)+双源类别全仓清零(本轮) |
| C 加权 | 8.81 | **935/1050 = 8.90** | +10 |
| **24 项总加权** | 8.65 | **1931/2220 = 8.70** | **+0.05** |

实际效能账: "编辑一侧、另一侧静默过期"的事故模式在脚本树内结构性消灭;未来任何 lib 改动单点生效,双侧消费者(.claude 入口与 .omc 运行时)永远同步。
