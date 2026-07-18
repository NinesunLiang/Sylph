# §17a 审计响应 — 对 Grok-4.5 回执的逐条处理（v3.1 → RC）

> 回执：`UI/round5/audit-receipt-grok-4.5.md`
> 本文：每条发现的源码级判定 + 修复落点 + 证据。Grok 要的 10 份源码现全部在仓库内可直接读。
> 证据日志：`UI/round5/logs/smoke-independent-rerun-20260718.log`（43/43，runner=independent）、
> `UI/round5/logs/preflight-nogo-rerun-20260718.log`（NO-GO 12 项精确命中）。

## 一、P0 逐条

### P0-1 Bash/CLI 旁路 —— **确认成立，已修（hook v2 默认拒绝）**

Grok 推断精准：v1 的 `DENY_CMD_PATTERNS` 只拦 `>|>>|tee|sed -i|perl -pi|dd of=` 与 `rm|mv|cp`，
`python3 - <<PY open("gate-results/C6.json","w")` 之类解释器直写**完全穿防**。

**修复（`.claude/hooks/carroros-night-deny.py` 全量重写）：**
1. **默认拒绝**：Bash 命令凡提及控制面 token（gate-results / .omc/night / carroros-gates / token.json / settings / hooks / verification-summar / ac-aggregates / page-baselines / carros_base …），必须 fullmatch 白名单，否则 exit 2。
2. **白名单仅 6 类**：门禁脚本调用（scope-check/c7-check/evidence-check/finalize-page/abstraction-check）、run-gate（wrapped 二次校验）、carros_base 三 API、页基线重定向、events 追加、只读命令（cat/ls/grep/git 只读）。
3. **run-gate wrapped 二次校验**：工具白名单（pnpm/npm/npx/node/tsc/eslint/playwright 或 tests/visual/scripts 下脚本）+ 禁链式/重定向/命令替换 + 禁控制面 token。`run-gate -- true` = exit 2。
4. **`ln` 夜间全禁**（symlink 绕过路径字符串检查）；Edit/Write 加 **realpath 解析**（symlink 目标命中控制面同样阻断）。
5. preflight / morning-report / gen-control-plane-lock / install-night-hook / smoke **全部不在白名单**——夜间禁跑（晨收第一步人类 `rm .omc/state/night-session.active`，已写入 README ⑤）。

**证据**：smoke 类 6 共 24 用例全绿——13 攻击（heredoc 写、-c 写、直调 CLI、包 true、链式、cp、ln、echo 写 summary、Edit 直写、Edit 经 symlink、三个禁跑脚本）+ 11 放行（合法门禁调用、token-write、manifest-json、events、基线、读 gate-results、普通开发命令、白天无标记）。

**诚实残余（不掩盖）**：hook 只能拦**工具面**。子进程写控制面（如 playwright spec 内 `fs.writeFileSync` 伪造信封）理论上不可拦——这是 FINAL §4.5「同一执行身份」S1 残余的一部分，靠 ① PR diff 人工晨审（伪造代码必须藏在页面 diff 里）② producer/digest 校验（见 P0-3，伪造成本大幅抬高）③ v3.2 preventive（gate-results 目录 ACL / 独立 uid）收口。已写入 night-loop.md 禁止列表。

### P0-2 自证当证据 —— **确认成立，已修（独立复跑 + attestation 字段）**

1. **独立复跑落盘**：rsync 仓库到 `/tmp/carroros-17a-rerun`（无 .git、无共享状态）→ `SMOKE_RUNNER=independent` 全量复跑 → **43/43 绿**，日志 `UI/round5/logs/smoke-independent-rerun-20260718.log`。
2. **复跑真的抓到了环境假设**：首跑 41/43——finalize 的 `gates_code_sha` 需要 target-repo 是 git repo，裸 rsync 副本没有 .git → `git rev-parse HEAD` 失败。补 `git init + commit` 后 43/43。这正是独立复跑的价值（自陈环境下该前提永远满足，永远测不到）。
3. **scorecard 加 `smoke_attestation: self|independent`**（morning-report.sh，从 smoke-results.yaml 的 `runner` 字段读出）；preflight NO-GO 复跑日志同袋（12 项命中，含新增的 helper 绑定检查）。
4. 「评审方指定 payload 的破坏复现」一条**保持开放**：欢迎 Grok/Opus/GPT 各指定 1 条篡改 payload，我们跑给你看（smoke 类 5/6 框架已支持即插即用）。

### P0-3 合法 schema 假 PASS —— **确认成立，已修（producer 权威字段 + 三层校验）**

比 Grok 说的更糟：`gate_result.py` 的 CLI `write` 子命令任何人可直接调；`run-gate.sh -- true` 能产**合法链路的真 PASS 信封**。

**修复（三层）：**
1. **工具面封死**（P0-1 hook v2）：夜间直调 `gate_result.py` = exit 2；`run-gate -- true` = exit 2。
2. **信封加权威字段**（`lib/gate_result.py`）：`producer`（必填，枚举 7 个门禁脚本名，非法值 FailClosed）+ `argv_digest`（run-gate 被包装命令 sha256）。`common.sh gates_write_result` 自动取调用方脚本名；`run-gate.sh` 把 wrapped argv+digest 写进 evidence。
3. **消费方校验**：
   - `finalize-page.sh`：每信封 `producer` 必须匹配 gate_id→脚本映射（C1→scope-check.sh、C2/C4/C5/C6→run-gate.sh…），且**信封控制面 digest 必须与当前一致**——不符 = FAILED_INVARIANT exit 3。
   - `morning-report.sh`：`producer_mismatch_count` + `suspicious_gate_invocation_count`（C2 必须像 tsc/eslint/build、C4/C5 像 playwright、C6 像视觉脚本，wrapped argv 不像 = 计数）进 scorecard，非零 = 不绿。

**证据**：smoke 5f（producer 错配假 PASS 全集 → exit3，stderr 含 "producer"）、5g（digest 不符 → exit3，stderr 含 "digest"）、fail-open 非法 producer → FailClosed，全绿。

## 二、P1 逐条

| # | 判定 | 处理 |
|---|---|---|
| P1-1 lock 闭环 | **源码已闭合** | lock 生成仅白天（gen-control-plane-lock.sh 不在夜跑白名单，夜间调用 = exit 2）；每个门禁 preamble 自验，mismatch = exit 3；deny hook + hook-launcher + settings#hooks 伪条目均在 19 项内。smoke 5d/5e + hook 禁跑用例佐证。 |
| P1-2 fail-closed 五连 | 逐条核对 | ① lock 缺失/空 entries → exit 3（common.sh，smoke 5d 佐证）② evidence-index 缺字段 → evidence-check exit 2（fail-closed）③ 缺门 → finalize BLOCKED（5a 变体验证过）④ YAML 锚点/重复键：pyyaml safe_load 语义，重复键后者胜——接受为已知解析语义，不进权威链 ⑤ SUPERSEDED 滤空 → reduce {} → BLOCKED（**新增 smoke 5h 佐证**）。 |
| P1-3 C1 prefix | **确认是测试缺口，已补** | strip_prefix 逻辑本在；**新增 smoke 类 7**：monorepo 子目录 fixture，合规改动 exit0 / 越界改动 exit1（stderr 精确列出越界文件），全绿。已知边界：target 子目录**之外**的 monorepo 改动 C1 看不见（git -C 子目录限制）——晨审 repo 级 git diff 兜底，记入残余。 |
| P1-4 catalog 绑定 | **确认缺口，已修** | preflight 新增 **4b**：`tests/e2e/helpers/assertions.ts` 必须存在且 17 个 catalog id 逐个 grep 命中（helper 以 id 为键导出 registry，phase0-checklist A1 已写明）。NO-GO 复跑日志可见该项精确命中。manifest 引用 id ⊆ catalog 的检查本在（preflight 4）。 |
| P1-5 night-loop 语义 | **确认，已修** | night-loop.md 新增**禁止列表**（手写信封/包空命令/子进程写控制面/跑白天工具/猜 final_status/提前开 PR）+ **exit 3 = 夜熔**规则 + 步 13 PR 第六段 inferred 清单强制。红队 prompt 实测留给首夜后（DeepSeek 会话内进行）。 |
| P1-6 inferred 腐蚀 | **部分采纳** | finalize summary 加 `contract_trust: TRUSTED|UNTRUSTED_CONTRACT|NONE`；DONE 含推断契约时 reason 强制标注；晨报 `untrusted_contract_pages` 计数 + 行内 ⚠ 红旗；PR body 第六段强制 inferred 清单。**未采纳**「inferred 不得计满分/只许 BLOCKED_INPUT」：与分期输入需求直接冲突（原型先行、API 滞后是明确需求）；首夜 O5 选页本就要求 input_completeness=complete，inferred 路径首夜不触发。对账翻转走 intake reconcile。 |
| P1-7 O5 机判 | **源码已闭合** | preflight.sh 五项机判（pages==1 + input_completeness=complete + complexity=V0_or_V1 + 三布尔）本在，NO-GO 日志可复核。 |
| P1-8 S1 签署 | **源码已闭合 + 补强** | `residual_risk_accepted_by` 非空 + `auto_renew=false` 硬拦本在；新增 `trust_boundary.scope == single_page_single_night` 硬拦（模板本有该字段）。 |

## 三、P2 处置

| # | 处置 |
|---|---|
| P2-1 supervisor/只读身份 | v3.2，已列入 manifest `mandatory_before_v3_2_ga` |
| P2-2 envelope HMAC | v3.2（同 uid 下 HMAC 密钥也在同 uid，收益有限；producer/digest/晨报侦探为首夜足够） |
| P2-3 O1/O2 升阻断 | 维持晨报指标，首夜后评估 |
| P2-4 dry-cost 预算 | Phase 0 B3 必做（preflight 硬拦空预算） |
| P2-5 delivery 正交 | 已正交（delivery_status 独立码表，DRAFT_PR_FAILED 不改写 DONE） |

## 四、给 Grok 的复验邀请

1. 你要的 10 份源码全在仓库：`carroros-night-deny.py`(v2) / `gate_result.py` / `finalize-page.sh` / `common.sh` / `scope-check.sh` / `smoke/run-all.sh`(43 例) / `night-loop.md` / `preflight.sh` / `assertion-catalog.yaml` / 独立复跑日志 ×2。
2. 请指定 1–2 条**你的**篡改 payload（不是我们这 24 条里的），我们当场跑。
3. 子进程写控制面（playwright spec 内伪造）我们判定为 S1 残余不可拦——若你认为首夜必须拦，唯一正解是 v3.2 ACL 提前，请明示，我们调整 GA 门槛。
