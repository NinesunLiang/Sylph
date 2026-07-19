# Round4 终审记票与收口对账（verdict-reconciliation）

> 日期： 2026-07-20 | 整合器： Kimi K3 | 对象： round4/gpt.md + grok.md + opus.md(R6 收口审）
> 前置： R6 施工收口报告 = round3/r6-closure.md;R5 记票 = round3/verdict-reconciliation.md

## 1. 票决汇总

| 议题 | GPT | Grok | Opus | 结果 |
|---|---|---|---|---|
| R6-A:E7 精确 BLOCK 化（7→8) | ACCEPT | YES | APPROVE | **3:0 成立** |
| R6-C:E2 8→9（机械选定冻结） | ACCEPT | YES（条件：复跑绿） | APPROVE | **3:0 成立** |
| 加权门禁 1920/2220=8.65 ≥8.6 | PASS | PASS | PASS | **3:0 达成** |
| 24 项全 ≥8（差内置安全） | FAIL pending R6-B | NOT YET | 待 R6-B | 0:3 卡点=token 人工轮换 |
| 开 R7(AI 扩项） | — | **NO**（除非复跑红/新 fail-open) | 不建议 | 不开 |
| 内置安全豁免/预记 8 分 | REJECT | REJECT(AI 伪造=否决） | 维持 7+blocked_human | 0:3 AI 侧不得刷分 |

**三家一致**:AI 可控范围工程完工（`R6_CONDITIONALLY_ACCEPTED_PENDING_HUMAN_SECURITY_CLOSURE` / Grok"8.65 工程封板" / Opus"AI 可控范围内终验标准已达成");AI 严禁代劳/伪造 token 闭环。

## 2. owner 裁决（2026-07-20，人的决策 > AI 决策）

> 用户原话：「忽略token这个，暂时视为通过；其他的按照他们的总结和处理优化」

- 内置安全 7→**8** 由 **owner 裁决**记为通过——这是人类独占裁决权的正当行使（终审三家均认可 token 闭环只能由人类完成；owner 即为该人类）。
- **诚实注记**:token 轮换的人工操作（Moonshot 控制台吊销+新 token 不入库+scan 对账+脱敏回执）仍由 owner 认领、**证据后补**;scorecard 以 owner 裁决记账，不作"AI 伪造回执"（三家禁令不触碰——本提分非 AI 伪造，是 owner 明示裁决）。
- 状态标签： GPT 禁用标签（FINAL_ACCEPTED/ALL_GATES_PASSED 等）的前提是"R6-B 未完成";owner 裁决视为通过后，采用 **ALL_GATES_MET (owner-adjudicated, R6-B receipt pending)**——既执行 owner 决策，又保留证据待补的事实。

## 3. 算术对账：Opus 1930 vs 报告 1921 → **1921 正确**

- Opus §4.1:「报告写 1921，我算 1930，差异 9 分需确认」——Opus 把内置安全按 E 项权重 10 计（+10)。
- GPT §5.2 已正确裁定：内置安全属**长期治理七项**（原始分计，权重 1),7→8 = **+1** → 1920+1=**1921**,1921/2220=8.6536→**8.65**。
- **裁决：以 1921 为准**（与 r6-closure.md §5 轨迹表一致）;Opus 的 1930 为权重口径误用，不影响门禁判定（两者均>8.6)。

## 4. Grok 条件兑现：七套回归复跑（2026-07-20，全 rc=0)

Grok 票：E2=9"有条件通过，缺复跑日志则分作废";"若复跑任一红，通过撤回"。现跑存证：

| 套件 | 结果 | 日志 |
|---|---|---|
| test-oracle-gate.py | 31/31 PASS rc=0 | ~~round4/evidence/oracle-gate-r6-rerun.log~~(2026-07-20 owner 指令清理，下表同） |
| test-verify-gate.py | 20/20 PASS rc=0 | ~~round4/evidence/verify-gate-r6-rerun.log~~ |
| apply-pkg-a.sh (A-A1..5) | 全绿 rc=0 | ~~round4/evidence/pkg-a-r6-rerun.log~~ |
| apply-pkg-b.sh (A-B2..12) | 全绿 rc=0 | ~~round4/evidence/pkg-b-r6-rerun.log~~ |
| run_pkg_c_acceptance.sh (V0..V6) | ALL_PKG_C_ACCEPTANCE_PASSED rc=0 | ~~round4/evidence/pkg-c-r6-rerun.log~~ |
| apply-pkg-r4.sh (A-1..8) | ALL R4 ACCEPTANCE PASSED rc=0 | ~~round4/evidence/pkg-r4-r6-rerun.log~~ |
| test-hook-launcher.sh | 3/3 PASS rc=0 | ~~round4/evidence/launcher-r6-rerun.log~~ |

> 日志存废声明： 七份复跑日志于 2026-07-20 复跑当日存在并已核对（rc 全 0，结论如上表）,owner 当日指令清理过程日志后删除（commit 3ba3d95 的 git 历史可恢复）。Grok 条件（决策时须有复跑存证）在决策时点已满足。

→ 条件通过转为正式通过；Grok 撤回条件不触发。

## 5. 非 token 事项处置（照三家总结）

| 来源 | 事项 | 处置 |
|---|---|---|
| Grok 收口令 2 | scorecard E7 记完结、E2=9 挂 31/31+20/20 日志路径 | ✅ 已挂（scorecard E 维度行+轮次日志） |
| Grok 收口令 4 | 禁开 R7 顺手改 CWD/observability | ✅ 不开 R7;hook 相对路径 cwd 脆弱点作为**已知边界**保留（见下） |
| Opus §八 | 正式发布+记录已知边界供后续轮次 | ✅ 本文件+scorecard 即发布记录；已知边界在下节存档 |
| Opus §1.4 / GPT §2.4 | docker `-e` 容器内注入、Gate7 L2 作用域、U13 hint 分层 | ✅ 三家均接受为已知边界/架构声明，维持风险登记 |
| GPT §7.3 | 禁用标签（R6-B 前） | ✅ owner 裁决后改用 ALL_GATES_MET (owner-adjudicated)，证据待补注记不删 |

## 6. 已知边界存档（后续轮次候选，非本轮施工）

1. **hook 相对路径 cwd 脆弱**(R5 观察项）:`python3 ".claude/hooks/posttool-gate.py"` 相对路径在 cwd 变更时 file-not-found；建议未来用 `$CLAUDE_PROJECT_DIR` 锚定。Grok 明示不强迫扩项。
2. **docker `-e SKIP_VERIFY=1` 容器内注入**:gate 在容器外；若未来出现容器挂载宿主 `.omc`/写宿主验证证据路径，必须重分类（GPT §2.4 条件）。
3. **L1 session 不走 oracle 门**：既有架构权衡，G5 回归守护；非永久豁免，仅非本轮阻断条件。
4. **R6-B 正式安全闭环**:owner 裁决视为通过，Moonshot 轮换+脱敏回执证据后补（owner 认领）。

## 7. 收口状态

```text
R6-A: ACCEPTED 3:0 (E7 7→8)
R6-C: ACCEPTED 3:0 (E2 8→9, rerun-green condition MET)
R6-B: OWNER-ADJUDICATED PASS (内置安全 7→8, receipt pending, owner-owned)
加权门禁: 1921/2220 = 8.65 ≥ 8.6  PASS
24 项全 ≥8: min = 8.0  PASS (owner-adjudicated)
状态: ALL_GATES_MET (owner-adjudicated, R6-B receipt pending)
R7: 不开（Grok 禁令 + 无红复跑 + 无新 fail-open)
```
