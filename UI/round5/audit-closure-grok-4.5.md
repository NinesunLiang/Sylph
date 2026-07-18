# §17a 闭环记录 — Grok-4.5 复审条件逐项兑现（v3.1 → Conditional GO 轨道）

> 复审回执：`UI/round5/audit-rereview-grok-4.5.md`
> 本文：Grok 开出的 Conditional GO 清单，逐项兑现证据。

## Conditional GO 清单（Grok §5）

| # | 条件 | 状态 | 证据 |
|---|---|---|---|
| 1 | Grok-A / Grok-B 当场绿 | ✅ **7/7 绿** | `UI/round5/logs/grok-ab-payloads-20260718.log`（驱动：`UI/round5/grok-ab-payloads.py`，fresh 编写非夹具复诵） |
| 2 | smoke_attestation=independent 入袋 | ✅ | `UI/round5/logs/smoke-independent-rerun-20260718.log`（43/43，runner=independent）；scorecard 字段已上线 |
| 3 | Owner 签署 S1 三件套 | ⬜ **用户动作**（Phase 0 B7） | preflight 已硬拦：`residual_risk_accepted_by` 非空 + `auto_renew=false` + `scope=single_page_single_night`，未签 = NO-GO |
| 4 | O5 五项机判 | ✅ 机制就位 | preflight.sh 第 3 项；NO-GO 复跑日志可复核 |
| 5 | 晨审 checklist 四项 | ✅ 已写入 README ⑤ | repo 根 diff 兜底 / 测试内写控制面嗅探 / scorecard 三零 / C4-C5 证据链抽查 |

## Grok-A/B 结果原文（7/7）

```
== Grok-A：夜标记开启，间接写 gate-results（hook 模拟 PreToolUse） ==
  ✓ Grok-A1 python pathlib 间接写: exit 2（命令触碰控制面且不在夜跑白名单）
  ✓ Grok-A2 node writeFileSync 间接写: exit 2（同上）
  ✓ Grok-A3 阻断后无伪造文件落盘: 0 文件
== Grok-A 兜底：裸伪造文件（即使越过 hook 落盘）finalize 不得吃 ==
  ✓ Grok-A4 裸伪造（缺权威字段）→ finalize: exit 3（FAILED_INVARIANT: gate-results 不可信）
== Grok-B：假 PASS 全集 + 真 digest + C1.producer 错配 ==
  ✓ Grok-B1 finalize 拒收: exit 3
  ✓ Grok-B2 stderr 含 producer 原因
  ✓ Grok-B3 不得写出 DONE: DONE=False
  stderr 原文: FAILED_INVARIANT: C1 信封 producer='finalize-page.sh'（期望 scope-check.sh）——非合法门禁链产物
```

要点：Grok-B 抄的是**当前真实 lock digest**（3f71142b…）——digest 一致性检查真的通过了，是 producer 映射把它拦下的；两条防线各自独立生效。

## 复审残余记账（已落 scorecard / 文档）

| 残余 | 落点 |
|---|---|
| `yaml_duplicate_key_policy: last_wins_known`（P1-2） | scorecard 静态字段 ✅ |
| `red_team_night_loop: due=after_first_trial`（P1-5） | scorecard 静态字段 ✅（首夜后必须红队实测，不得无限 defer） |
| C1 看不到 target 外 monorepo 改动（P1-3） | 晨审 checklist #1 repo 根 diff 兜底 ✅ |
| S1 子进程写控制面（playwright spec 内伪造） | FINAL §4.5 已声明残余；晨审 checklist #2 嗅探；v3.2 ACL 收口；**Owner 签署承责** |

## 结论状态

- **Grok 侧 §17a：无新阻断性实现 P0；S1 子进程残余已记录** —— 待 Owner 签署后其 Conditional GO 正式生效
- **GA：NO**（v3.2 预防式隔离 + §18 全闭合证据前不申报）
- **还缺**：Opus 4.8 / GPT-5.6 Sol 两家 §17a 回执（`audit-request.md` + 本袋全部修复/复验材料）
