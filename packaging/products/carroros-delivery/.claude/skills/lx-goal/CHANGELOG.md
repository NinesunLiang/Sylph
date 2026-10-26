# Changelog

## v1.7.0
- feat: `report --format client` —— 客户版「交付报告」
  - 输出 `state/goal-report-client.md`（`--out <路径>` 可指定位置），7 节全客户语言：
    结论 / 本次交付内容 / 怎么验证的 / 需要你决定的事 / 本次未做 / 需管理员权限执行 / 验收方式
  - 交付项显示 plan.md 的人类可读标题，不再只给 `S1/S2` 内部编号
  - **硬约束**：不得出现 `EV-` / `uncertified` / `skipped_risks` / `GateKeeper` /
    `plan.step.` / `**status**` / `**confidence**`（`test_client_report_format.py` 钉死）
  - 内部版 `goal-report.md` 仍是唯一机器真相源，默认行为不变
  - 用法：`lx-goal.py report --format client [--out <路径>]`

## v1.6.0
- feat: 每步结束打印「下一步入参契约」——事前告知，不靠事后报错
  - on → research 8 章节；phase0-done → plan 结构 + L2 TDD 判据
  - plan-done → EV 块写法；task-done → 进度/收尾三连
  - report → checklist + verdict；accept → done
- fix: L2 前置 TDD 门从 phase0-done 移到 plan-done（plan 判据此时才存在）
- fix: L2 收尾（done）强制跑后置 TDD；worktree 归档前必须合回
- change: 双法官（accept）改为可选增强，简单任务不强制
- fix: TDD 命令改为在项目根/worktree 执行（原在任务文档目录，必然误判）
- feat: 无人值守防中断——剩余不足 1 小时且有 step 成功推进时顺延 6 小时
- test: 生命周期测试改为 hermetic，不再在真实仓库创建 worktree

## v1.5.1
- fix: Phase0 改为逐卡片澄清循环
  - 每张卡只问一个问题
  - 用户回答后重新扫描剩余不确定项
  - 仅在没有新的用户决策项时进入计划确认
  - 删除与逐问规则冲突的批量 Q 清单要求

## v1.5.0
- feat: Phase0 融入 brainstorming/grill-me 理念
  - HARD-GATE: Phase0 未完成不得执行
  - 先探索再提问，能自答不问用户
  - 每次一个问题，逐分支推进
  - 非平凡任务提出 2-3 种方案
  - 自审计划（检查占位符/矛盾/模糊）
  - Anti-Pattern: "太简单不需要澄清"
- feat: 任务规模判断（含多子系统→拆解为子项目）

## v1.4.2
- fix: 引用路径修正（progress-template.md→exit-report.md）
- docs: 跨会话续跑 Step 3 补充"最后一步"判定说明

## v1.4.1
- feat: SubAgent 调度记录（assign/complete/fail/summary）
- feat: L1→L2 就地升级协议

## v1.4.0
- feat: 跨会话续跑
- feat: 退出报告 exit-report.md
