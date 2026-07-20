# Round5 基线重评(baseline) — 整合器自评口径

> 日期: 2026-07-20 | 评分人: Kimi K3(整合器自评,**未经三模型终审**,不动 scorecard.md 官方分)
> 基线参照: R6 收口 1921/2220=8.65 | 方法: 文件级证据+六套回归现跑

## 0. 回归健康(现跑证据,全 rc=0)

| 套件 | 结果 | 日志 |
|---|---|---|
| test-context-watermark.py | 25/25 PASS | /tmp/r5_test-context-watermark.log |
| test-oracle-gate.py | 31/31 PASS | /tmp/r5_test-oracle-gate.log |
| test-verify-gate.py | 20/20 PASS | /tmp/r5_test-verify-gate.log |
| test-goal-mode-gate.py | 12/12 PASS | /tmp/r5_test-goal-mode-gate.log |
| test-hook-launcher.sh | ALL PASS | /tmp/r5_launcher.log |
| test_pkg_c_lifecycle.py | ALL_PKG_C_TESTS_PASSED | /tmp/r5_pkgc.log |

→ R6 声称的拦截链(verify/oracle/watermark/goal-mode/launcher/lifecycle)在当前树全部成立。扣分不来自机制失效,来自 **R6 后新生漂移**(下列 F 项)。

## 1. 新发现清单(本轮扣分依据)

| # | 发现 | 证据 | 打击面 |
|---|---|---|---|
| F1 | watermark 双源分裂: `.claude/scripts/context_watermark.py`=40/70(7/5) vs `.omc/scripts/context_watermark.py`=50/70/80(7/20,commit 476a08b 只改 .omc) | 两文件 diff;476a08b --stat | E6/C8 |
| F2 | error_dna 双源分裂: `.claude/scripts/lib/error_dna.py` 有 R4 K1 噪声过滤(7/20) vs `.omc/scripts/lib/error_dna.py` 无(7/13) → K1 对 .omc 侧消费者失效 | diff 18 行;K1 quarantine 块只在 .claude 侧 | E6/学习笔记 |
| F3 | flywheel 双源分裂: `.omc/scripts/lib/flywheel.py` 较新(7/15,归一化分组)但 **untracked+被 .gitignore:2 忽略**;`.claude/scripts/lib/flywheel.py` 旧(7/13)且被 stop-flywheel.py:25,41 实际 import → Stop 飞轮跑旧逻辑,git status 无感 | git check-ignore;diff 67 行 | E6/C8/学习笔记 |
| F4 | kernel.md(冻结,AI 禁改)水位表仍 40/50/70 vs 运行链 50/70/80 | kernel.md:13-17 vs pretool-gate.py:1039/1049 | E6 → blocked_human |
| F5 | session-start.py 注入无 staleness 校验;`.omc/session-handoff.md` 内容停 2026-07-18(task=skill-hook-adaptive-opt 0/6),每次启动照注 | session-start.py:74-80;handoff 头部 | C2/E8 |
| F6 | handoff 头部自称"AGENTS.md 已 @ 引用本文件"——grep AGENTS.md/CLAUDE.md/index.md/settings.json 零命中,声称不实 | grep 四文件 | E6 |
| F7 | lx-goal.py:782-789 未知 argv 当 goal 激活(`--help` 实证建锁),无 usage 守卫 | lx-goal.py:782-789;本会话事故 | C9/UX 可预测 |
| F8 | token 目录日期格式双存: `.omc/tokens/2026-07-18/` 与 `.omc/tokens/20260718/` 并存 | ls .omc/tokens/ | C4 |
| F9 | `.claude/scripts/.omc/state/` 嵌套 state 被 commit 进库(oracle verdicts test_debug) | git ls-files | C8 |
| F10 | settings.json 9 条 hook+statusLine 全相对路径,6 条直跑 python3 无 $CLAUDE_PROJECT_DIR 锚定(launcher 包装的 2 条关键 hook 自锚定,安全) | settings.json:27-122;hook-launcher.sh:9-10,40 | 已知边界(round4 §6.1) |

## 2. C 维度评分(权重/基线R6/本轮/依据)

| C | 指标 | 权重 | R6 | 本轮 | 依据 |
|---|------|------|----|------|------|
| C1 | 指令清晰度 | 15 | 9 | **9** | kernel/AGENTS/index 精炼;水位口径分裂计入 E6 不在此 |
| C2 | 上下文完整度 | 15 | 9 | **8** | F5: 注入链真实但无新旧校验,2 日陈旧 handoff+过期 token 摘要照注 |
| C3 | 流程结构化 | 15 | 9 | **9** | verify/oracle/watermark/goal-mode 四链回归全绿 |
| C4 | 输出规范化 | 10 | 8 | **8** | F8: token 日期目录双格式并存(audit 已统一,token 目录未) |
| C5 | 工具生命周期 | 10 | 9 | **9** | 9 事件+statusLine 全注册(settings.json:27-122);launcher fail-closed |
| C6 | 知识密度 | 10 | 9 | **9** | error-dna quarantine+flywheel 结构在;分裂计入 E6 |
| C7 | 关联编排 | 10 | 9 | **9** | goal/ghost 互斥、skill 路由、launcher 白名单均在 |
| C8 | 可维护性 | 10 | 8 | **7** | F1/F2/F3 三处双源漂移+F3 untracked+F9 嵌套 state |
| C9 | 错误恢复 | 10 | 9 | **9** | launcher fail-closed、precompact fail-closed、watermark stale 1800s fail-open 设计在 |

C 加权: **900/1050 = 8.57**(R6: 925=8.81)

## 3. E 维度评分

| E | 指标 | 权重 | R6 | 本轮 | 依据 |
|---|------|------|----|------|------|
| E1 | 目标漂移 | 20 | 8 | **8** | edit-scope/token-scope 双 BLOCK 在,回归绿 |
| E2 | 幻觉输出 | 20 | 9 | **9** | verify 20/20+claim-evidence 机械校验在 |
| E3 | 虚假完成 | 15 | 9 | **9** | cmd_verify→verify_gate→task-bound audit 链 20/20 |
| E4 | 惯性执行 | 12 | 8 | **8** | goal-mode 12/12,warn 门 audit 留痕 |
| E5 | 症状混淆 | 10 | 8 | **8** | oracle-escalation 重组保持 |
| E6 | 自我矛盾 | 13 | 9 | **7** | F1/F2/F3/F4/F6 五处活跃矛盾(双源×3+冻结文档水位+幽灵@声称) |
| E7 | 过度自信 | 10 | 8 | **8** | oracle 三层 31/31 |
| E8 | 上下文遗忘 | 10 | 9 | **9** | PreCompact fail-closed 快照+sha256 回读在;staleness 计入 C2 |

E 加权: **912/1100 = 8.29**(R6: 938=8.53)

## 4. 长期治理(7 项)

| 维度 | R6 | 本轮 | 依据 |
|------|----|------|------|
| 抗衰减防线 | 9 | **9** | PreCompact/Stop seal/SubagentStop 幂等在 |
| AI 赋能全流程自动化 | 8 | **8** | 保持 |
| 学习笔记积累 | 8 | **7** | F2/F3: error-dna K1 半失效+flywheel 旧逻辑在跑,学习环分裂 |
| 长期目标一致性 | 8 | **8** | 保持 |
| 功能标志分明 | 8 | **8** | registry 对齐保持;F6 小瑕疵不拉分 |
| 内置安全与洞察 | 8 | **8** | owner 裁决维持(R6-B 回执仍 pending,blocked_human) |
| Evaluation 评测框架 | 9 | **9** | benchmark/ 框架+六套回归现跑绿 |

治理: **57/70 = 8.14**(R6: 58=8.29)

## 5. UX(独立,不入门禁)

| 维度 | R6 | 本轮 | 依据 |
|------|----|------|------|
| 长期目标一致性 | 8 | **8** | — |
| 用户心智负担减轻 | 7 | **7** | F5 陈旧注入+F7 误激活残留需人工清理 |
| 交互现代化 | 7 | **7** | — |
| 用户掌控感 | 8 | **8** | — |
| ai 智能感 | 7 | **7** | — |
| 行为可预测 | 8 | **7** | F7(--help→激活)+F2/F3(import 结果取决于路径,行为不确定) |
| 人机权限分明 | 8 | **8** | verify 不自证保持 |

UX: **52/70 = 7.43**(R6: 53=7.57)

## 6. 总账

| 维度 | R6 | 本轮基线 | Δ |
|---|---|---|---|
| C1-C9 加权 | 8.81 | **8.57** | -0.24 |
| E1-E8 加权 | 8.53 | **8.29** | -0.24 |
| 治理均分 | 8.29 | **8.14** | -0.14 |
| **24 项总加权** | **8.65** | **1869/2220 = 8.42** | **-0.23** |
| 24 项最低分 | 8.0 | **7.0(C8/E6/学习笔记)** | -1.0 |
| UX 均分 | 7.57 | **7.43** | -0.14 |

> 结论: R6 机制全部存活(回归绿),但 R6 收口后 24h 内新生双源漂移×3+冻结文档失同步+注入无新旧校验。漂移主因=commit 476a08b 施工时只改了 .omc 侧, .claude 侧副本与 kernel.md 未同步——**双源物理复制的老病在新代码上复发**。

## 7. ROI 池(实际效能口径排序)

| 序 | 候选 | 实际效能论点 |  effort | 打击面 |
|---|---|---|---|---|
| P1 | 双源统一(watermark 符号链接化+error_dna 同步 K1+flywheel 并新版) | 离线水位入口不再说谎;Stop 飞轮跑新逻辑;K1 全侧生效;git 可感 | 中 | C8/E6/学习笔记 |
| P2 | lx-goal.py 未知参数守卫(-h/--help/未知 dash→usage+exit 2) | 防误激活污染状态机(本日实证) | 低 | C9/UX 可预测 |
| P3 | session-start staleness 守卫(handoff 超龄/无活 token→注记或跳过)+handoff 幽灵@声称修正 | 每会话省噪声、防误导恢复 | 低-中 | C2/E8/UX |
| P4 | settings.json 直跑 hook $CLAUDE_PROJECT_DIR 锚定 | 条件性风险(cwd≠root 才发作),launcher 已保关键门 | 低 | 已知边界 |
| P5 | kernel.md 水位表更新 | **冻结文档,AI 禁改** → blocked_human | — | E6 |
| P6 | token 日期格式统一 | 美观性,工具 glob 影响 | 低 | C4 |
| P7 | .claude/scripts/.omc 嵌套 state 出库 | git rm=硬边界 → 人执行 | — | C8 |

迭代计划: T2=P1, T3=P2, T4=P3(P4-P7 入 backlog/人类清单)
