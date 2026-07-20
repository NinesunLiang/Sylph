# Round6 评分+3轮ROI迭代 — progress.md

> 模式: /lx-goal 自主执行 | 口径: 独立报告,**不动 scorecard.md 官方分,迭代期不 commit,结束给清单**(常设裁决,沿用 round5 owner 拍板)
> 前置状态: round5 已收口并提交(d2d8022/1cd778c/ed2fa6a/81b6716),round5 终值 8.59(1908/2220),UX 7.71

## 计划

| 步骤 | 内容 | 状态 | 证据 |
|---|---|---|---|
| T1 | 基线重评: 8.65(1921/2220,E6 8→9),与 R6 官方并账;新发现 F1/F2/F3 | ✅ 完成 | baseline.md |
| T2 | 迭代1: F2 settings.json 10 条锚定,fail-open 洞闭合 | ✅ 完成(8.65 不变,效能账外) | iter1.md |
| T3 | 迭代2: lib 7 对双源统一,全树清零 | ✅ 完成(C8 8→9,8.70) | iter2.md |
| T4 | 迭代3: scripts/run-regression.sh 入库 | ✅ 完成(8.70 不变,效能账外) | iter3.md |
| T5 | 收口: summary+清单+退出报告 | ✅ 完成 | summary.md |

## ROI 候选池(实际效能口径,随证据更新)

| # | 候选 | 实际效能论点 | 状态 |
|---|---|---|---|
| P-A | hook 相对路径 cwd 脆弱性(round5 P1 遗留,"待证据") | 若证实 fail-open,野外静默失保护 | 待取证 |
| P-B | UX 最低维度(round5 终评 UX 7.71,查最低项) | 体验短板直接可见 | 待取证 |
| P-C | 新增双源漂移扫描(round5 后是否再生) | 防 8.65 回退 | 待取证 |
| P-D | tt-e2e 孤儿锁 3 个(.omc/tokens/20260720/) | 惰性噪声,微益 | 低优先 |
| P-E | R6-B token 轮换 | blocked_human(owner 专属,secrets 硬边界) | 不动 |

## 执行日志

- 2026-07-20 round6 激活,物理锁 .omc/tokens/20260720/round6-*_token.json
- 常设裁决沿用: 独立报告 + 迭代期不 commit(round5 owner 拍板,不重复问)
