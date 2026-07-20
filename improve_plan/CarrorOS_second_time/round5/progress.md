# Round5 评分+3轮ROI迭代 — progress.md

> 模式: /lx-goal 自主执行 | 口径: 整合器自评+文件级证据,**不动 scorecard.md 官方分,不 commit**(owner 裁决 2026-07-20)
> 基线: R6 收口 1921/2220=8.65, 24项全≥8, UX 7.57

## 计划

| 步骤 | 内容 | 状态 | 证据 |
|---|---|---|---|
| T1 | 基线重评(24+7+7,文件级证据) | ✅ 完成(8.42) | baseline.md |
| T2 | 迭代1: 双源统一 | ✅ 完成(8.42→8.53) | iter1.md |
| T3 | 迭代2: lx-goal 参数守卫 | ✅ 完成(UX 7.43→7.57) | iter2.md |
| T4 | 迭代3: 注入新鲜度守卫 | ✅ 完成(8.53→8.59) | iter3.md |
| T5 | 收口: 累计delta+变更清单+退出报告 | ✅ 完成 | summary.md |

## ROI 候选池(实际效能口径,随证据更新)

| # | 候选 | 实际效能论点 | 状态 |
|---|---|---|---|
| P1 | hook 相对路径 cwd 脆弱 → $CLAUDE_PROJECT_DIR 锚定 | cwd 变更时门禁 file-not-found=fail-open,野外静默失保护 | 待证据 |
| P2 | lx-goal.py 未知参数当 goal 激活(本次实证 --help 建锁) | 误激活污染状态机,需人工清理 | 已实证(本会话) |
| P3 | session-handoff 陈旧(2026-07-18 0/6 任务仍在 SessionStart 注入) | 恢复导航误导,浪费上下文 | 待证据 |
| P4 | R6-B token 轮换 | blocked_human(owner 认领,AI 禁代劳) | 不动 |

## 执行日志

- 2026-07-20 09:2x Phase 0 完成: owner 裁决=独立报告+不 commit;清理 --help 误激活残留+PreCompact 陈旧锁
- T1 证据收集: 3 个并行 Explore(hooks接线/lx-goal+handoff/测试盘点)
- 基线回归(自跑,全 rc=0): watermark 25/25;oracle-gate 31/31;verify-gate 20/20;goal-mode 12/12;launcher ALL PASS;pkg_c ALL_PKG_C_TESTS_PASSED → R6 声称的拦截链在当前树全部成立
- **新发现 F4 双源漂移(E6/C8 类,R6 后新生)**:
  1. context_watermark.py: .claude 副本=40/70(7/5 旧) vs .omc 副本=50/70/80(7/20 新,commit 476a08b 只改了 .omc) — 离线入口口径分裂
  2. lib/error_dna.py: .claude 副本有 R4 K1 噪声过滤(7/20) vs .omc 副本无(7/13) — K1 对 .omc 侧消费者失效
  3. lib/flywheel.py: .omc 副本较新(7/15,归一化分组)但 **untracked+gitignored**;.claude 副本旧(7/13)且被 stop-flywheel.py 实际 import — Stop 飞轮跑旧逻辑,git status 干净无感
  4. kernel.md(冻结,AI 禁改)仍写 40/50/70 水位 vs 运行链 50/70/80 → blocked_human 候选
- **新发现 F5**: .claude/scripts/.omc/state/ 嵌套 state 被 commit 进库(oracle verdicts test_debug) — C8 噪声
