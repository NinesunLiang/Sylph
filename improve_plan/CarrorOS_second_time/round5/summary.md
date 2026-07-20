# Round5 总结 — 评分 + 3 轮 ROI 迭代

> 2026-07-20 | 口径: 整合器自评+文件级证据,未经三模型终审 | owner 裁决: 不动 scorecard.md、不 commit
> 过程文件: baseline.md(基线) / iter1.md / iter2.md / iter3.md / progress.md

## 一、总分变化(自评口径)

| 维度 | R6 官方 | 本轮基线 | 迭代1 后 | 迭代2 后 | 迭代3 后 | 基线→终态 Δ |
|---|---|---|---|---|---|---|
| C1-C9 加权 | 8.81 | 8.57 | 8.67 | 8.67 | **8.81** | +0.24 |
| E1-E8 加权 | 8.53 | 8.29 | 8.41 | 8.41 | **8.41** | +0.12 |
| 治理均分 | 8.29 | 8.14 | 8.29 | 8.29 | **8.29** | +0.14 |
| **24 项总加权** | **8.65** | **8.42** | 8.53 | 8.53 | **1908/2220 = 8.59** | **+0.17** |
| 24 项最低分 | 8.0 | 7.0 | 8.0 | 8.0 | **8.0** | +1.0 |
| UX 均分(独立) | 7.57 | 7.43 | 7.43 | 7.57 | **7.71** | +0.29 |

> 注: 终态 8.59 仍低于 R6 官方 8.65——差值=E6 8→9 所需的 kernel.md 水位表更新(冻结文档,人类专属)+内置安全 R6-B 回执(owner 认领中)。机制类缺口已全部闭合。

## 二、逐项分数账(仅列变动项)

| 项 | 基线 | 终态 | 拉动轮 | 证据 |
|---|---|---|---|---|
| C8 可维护性 | 7 | 8 | 迭代1 | 三处双源愈合(symlink 单源);F9 嵌套 state 残留→人类 |
| E6 自我矛盾 | 7 | 8 | 迭代1 | F1/F2/F3 消除;kernel.md(冻结)+幽灵@(代码已修待自愈)挡 9 |
| 学习笔记积累 | 7 | 8 | 迭代1 | K1 过滤全侧生效;飞轮新逻辑(去重+task_dir bug 修复)全侧运行 |
| C2 上下文完整度 | 8 | 9 | 迭代3 | 注入新鲜度校验: STALE 横幅+token 年龄 |
| UX 行为可预测 | 7 | 8 | 迭代2 | --help 误激活消除+lib 分裂脑消除 |
| UX 心智负担减轻 | 7 | 8 | 迭代3 | 幻影任务 STALE 标注,不再裸注误导 |

未变动: C1 9 / C3 9 / C4 8 / C5 9 / C6 9 / C7 9 / C9 9;E1 8 / E2 9 / E3 9 / E4 8 / E5 8 / E7 8 / E8 9;治理 9/8/8/8/8/9(内置安全 8=owner 裁决维持);UX 8/7/8/7/8。

## 三、三轮迭代施工清单(实际效能口径)

| 轮 | 选题 | 实际效能 | 验证 |
|---|---|---|---|
| 1 | 双源统一(watermark/error_dna/flywheel 三处 symlink+flywheel 新版合并) | 离线水位入口不再说谎(40/70→50/70/80);Stop 飞轮跑新逻辑(修 run_flywheel task_dir 参数遮蔽 bug);K1 噪声过滤对 .omc 侧生效;漂移从"git 无感"变"单源可感" | 行为 5 项+六套回归全绿 |
| 2 | lx-goal.py 参数守卫 | `--help`/未知 dash 参数不再误激活建锁(本日实证事故);usage 自描述 | 4 路径行为+goal-mode 12/12 |
| 3 | session-start 新鲜度守卫+handoff 路径文档修正 | 陈旧 handoff 注入带 STALE 横幅;token 摘要带年龄;路径文档对齐现实 | live 注入实测+六套回归全绿 |

每轮均跑: watermark 25/25、oracle 31/31、verify 20/20、goal-mode 12/12、launcher、pkg_c —— 三轮 18 次套件执行全 rc=0。

## 四、未 commit 变更清单(owner 一键提交)

**本轮施工(7 项,建议一个 commit)**:
- `.claude/scripts/lib/flywheel.py`(新版合并)
- `.claude/scripts/context_watermark.py`(file→symlink → .omc 副本)
- `.claude/hooks/session-start.py`(staleness 守卫)
- `.claude/references/omc-path-conventions.md`(handoff 路径修正)
- `.claude/skills/lx-goal/scripts/lx-goal.py`(参数守卫)
- `improve_plan/CarrorOS_second_time/round5/`(本轮报告 5 文件,新增目录)
- 不可见但已生效: `.omc/scripts/lib/{flywheel,error_dna}.py` → symlink(gitignored 目录,提交不涉及)

**系统运行自更新(非施工,随会话产生)**:
- `.claude/.prompt-ring-state.json`(计数 55→58)
- `.claude/references/anti-patterns.md`(飞轮升华 3 条: unknown×155/unknown_recurring×124/timeout×16——子代理 Stop 触发;其中 unknown 类低信噪,迭代1 的新飞轮逻辑后续会改善分类)
- 仓根 `state/session-handoff.md`(本会话被 context_engine 刷新)

## 五、需人类介入项

| # | 项 | 类型 | 建议 |
|---|---|---|---|
| 1 | kernel.md 水位表 40/50/70 → 50/70/80 | 冻结文档(铁律6 AI 禁改) | 人类编辑 3 行;改完 E6 可评 9 |
| 2 | 仓根 `state/session-handoff.md` 孤儿文件 | rm 硬边界 | 确认无引用后删除(本会话 grep 零代码引用) |
| 3 | `.claude/scripts/.omc/` 嵌套 state 在库 | git rm 硬边界 | `git rm -r .claude/scripts/.omc`(test_debug 残留) |
| 4 | `.omc/tokens/` 日期双格式(2026-07-18/ vs 20260718/) | 迁移裁决 | 统一为 dash 格式并迁移旧目录;或容忍 |
| 5 | fallback_matrix 死模块(check_trigger 零调用+idle 路径错) | 架构裁决 | 归档或接线;idle 应指 `.omc/state/last-user-prompt.md` |
| 6 | R6-B token 轮换回执 | owner 已认领(不 nag,仅备忘) | 按 round4 模板补脱敏回执 |
| 7 | 本轮改动 commit | git 写硬边界 | 见第四节清单;提交后 scorecard 可并账 |

## 六、ROI 池剩余(backlog)

- P4 settings.json 6 条直跑 hook `$CLAUDE_PROJECT_DIR` 锚定(条件性风险,launcher 已保关键门)
- P6 token 日期格式统一(见人类清单 #4)
- kernel.md 更新后建议复审 E6 8→9 与总分 8.59→~8.65 并账
