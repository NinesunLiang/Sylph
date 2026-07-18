# §17a 复审回执（Grok-4.5 · 对“P0 处理响应”）

> 对：**`UI/round5` 实现方对 audit-receipt-grok-4.5 的逐条处置**
> 前提：响应文本 + 宣称的 hook v2 / producer 校验 / 43/43 independent smoke / NO-GO 12 项；**本回合仍未在本会话内逐字节打开那 10 份源码**，因此下面是 **“按处置是否足以销案/降级”的复审**，不是新一轮盲口“零 P0 盖章”。
> 一句话总判断先给：

| 项 | 结论 |
|---|---|
| P0-1 / P0-2 / P0-3（原工具面与自证类） | **原 P0 可降级为“已修 · 待源码 spot-check 销案”**；不再单独阻断，前提是你们宣称的机制为真 |
| P1-2 / P1-3 / P1-5 | **可销案（Closed with residual）**，见下表 |
| 是否还存在 **新的/残留 P0** | **没有新的实现级硬 P0**；剩 **1 个规格级残余条件（S1 子进程写面）** —— 它在 FINAL §4.5 下应记为 **残余风险 + Owner 签署**，**不应再写成“未修的 P0”去阻塞 v3.1 首夜**，除非你们希望把 preventive ACL 提前 |
| 能否写「无新 P0」过 §17a | **有条件可以**：在下列闭合清单打勾后，§17a 可记 **“无新阻断性 P0；S1 detective residual 已记录且 Owner 承责”** |
| Runtime | **仍不是 GA**；最多 **Conditional GO for single_page_single_night**，不是睡眠无监督 Full GO |

---

## 1. 三处原 P0 的复审

### P0-1 Bash/CLI 旁路 → **Accept fix（降级，不保留 P0）**

处置正确，而且比我原排查更深一层（`run-gate -- true`、`ln`、realpath、白天工具夜禁）。

**白名单默认拒绝** 是正确模式；类 6 的 24 用例形状也对。

**诚实残余你们自己写对了**：hook 只封工具面，**同 uid 子进程（playwright `fs.writeFileSync` 伪信封）不可拦**。
这不是“没修完的 P0-1”，而是 **FINAL §4.5 S1 已知残余**。我 **不要求首夜前置 v3.2 ACL** 才能过 §17a（与规格一致）；但必须同时满足：

1. signoff 里 `residual_risk_accepted_by` + `scope: single_page_single_night` + `auto_renew: false`（你们称 P1-8 已硬拦 —— 好）；
2. 晨审强制看：越界/异常 test 写文件、suspicious_gate_invocation、producer_mismatch；
3. night-loop **禁止列表**已含“子进程写控制面”（你们已写）。

→ **P0-1: CLOSED as mitigated (tool-surface)；残留并入 S1 residual，非阻断 P0。**

---

### P0-2 自证当证据 → **Accept partial（大幅降级）**

独立 rsync + `SMOKE_RUNNER=independent` + 日志 + `smoke_attestation` 字段，**正面回应了我“自证≠审计”**；首跑 41/43 抓到缺 `.git` 的环境假设，这恰恰证明 independent 有价值。

仍非“外部 auditor 亲手改 payload 再跑”，但 **§17a 接受标准可降为**：

- 独立目录复跑日志在袋（你们已有路径）；
- attestation≠self 才允许记绿；
- **评审方再指定 1–2 payload 当场跑**（你们已邀请 —— 见下文我给）后，本条销案。

→ **P0-2: OPEN only as “pending reviewer payload” 手续项，不再当架构 P0。手续完成即 CLOSED。**

---

### P0-3 合法假 PASS → **Accept fix（降级）**

`producer` 枚举 + `argv_digest` + finalize gate_id 映射 + digest 一致性 + 晨报 suspicious 计数 —— 这正是“比白名单更硬”的权威链补强；5f/5g 形状正确。

结合 P0-1，**“老实人 finalize 吃假 PASS”主路径已抬高伪造成本**到：同 uid 子进程写合法 producer/digest 信封。那属于 S1，不是未封的 P0-3。算法上：

→ **P0-3: CLOSED as mitigated。**

---

## 2. 你问的重点：P1-2 / P1-3 / P1-5 能否销案？

| ID | 复审判类 | 理由 | 残余（非 P0） |
|---|---|---|---|
| **P1-2 fail-closed 五连** | **销案 Closed** | 五支路径均给出期望行为 + smoke 锚（含 5h SUPERSEDED 滤空→BLOCKED）；YAML 重复键“后者胜”标注为已知解析语义、不进权威链 —— 可接受 | 建议在 scorecard 记 `yaml_duplicate_key_policy: last_wins_known`，防止以后有人当 bug 重开 |
| **P1-3 C1 prefix** | **销案 Closed with residual** | 补了 monorepo 子目录 smoke 类 7；逻辑声称 strip_prefix 本在 | **记名残余**：`git -C <subdir>` 看不到 target **之外** monorepo 改动 → **必须** 晨报/人审 repo 根 `git diff` 兜底（你们已写）。首夜单页 + files_allowed 窄时可接受 |
| **P1-5 night-loop 语义** | **销案 Closed with soft residual** | 禁止列表 + exit3=夜熔 + PR inferred 段 —— 我要的主干都有 | **红队 prompt 实测 defer 到首夜后**可接受，但要在 scorecard/open-questions 写死期限：`red_team_night_loop: due=after_first_trial`；**不得无限 defer** |

其余 P1（供记账）：

| ID | 判定 |
|---|---|
| P1-1 lock | 按描述 **Closed** |
| P1-4 catalog 绑定 | **Closed**（4b helper 全 id grep + NO-GO 复跑）—— 兑现了我 O3 深水区要求的方向 |
| P1-6 inferred | **Closed as deliberate product partial-accept**。反对“不得满分”与分期输入冲突合理；首夜 O5=complete 使路径默哀。**UNTRUSTED_CONTRACT + 晨报红旗 + PR 段**足够首夜 |
| P1-7 O5 | **Closed**（五项机判 + NO-GO 日志）—— 原 O5「只改成 len==1」担忧收口 |
| P1-8 S1 签署字段 | **机制 Closed**；**人类 Owner 真签名事件**仍是放行条件，不是脚本 bug |

P2 全部维持“演进，不挡首夜”——同意。

---

## 3. 重开：是否仍有 P0？

### 实现/工具面
在“响应描述为真”的前提下：

> **没有新的、未处理的实现级阻断 P0。**
> 原先三项 P0 **均已修到可接受的 detective + consensus 规格内**。

### 仍可被误解成 P0、但应按规格归到“条件” 的仅此一件

**S1：同执行身份子进程写 gate-results（playwright/node 内伪造 + 若 producer/digest 能抄当前值）**

- 技术上：**不可被 PreToolUse 消灭**（你们判断对）。
- 规格上：FINAL §4.5 已允许首夜 detective；**完整 supervisor/ACL = v3.2**。
- 审计立场：**不升级为首夜 P0**，但 **Conditional GO 的前置条件必须是 Owner 签名承责**，不是默认“已物理保证”。

若 Owner **拒绝**签残余风险 → 则运行时结论变 **NO-GO**，项目标签是 **产品风险否决**，不是“脚本还没写完的 P0”。

---

## 4. 我指定的 2 条复验 payload（请当场跑，贴 exit+stderr）

请不要用现成 24 条夹具复诵；要 fresh：

### Payload Grok-A — “伪装 run-gate 的间接写 + 合法 shape”
夜会话标记 **开启** 时执行（或由 hook 模拟 PreToolUse 输入）：

```bash
# 期望：exit 2（hook 默认拒）或永远到不了写盘
python3 -c 'import pathlib; p=pathlib.Path(".omc/night/demo/gate-results/C4.json"); p.parent.mkdir(parents=True, exist_ok=True); p.write_text("{\"status\":\"PASS\",\"producer\":\"run-gate.sh\"}\n")'
```

再试变异（若你们允许 `node`）：

```bash
node -e 'require("fs").writeFileSync(".omc/night/demo/gate-results/C6.json", JSON.stringify({status:"PASS",producer:"run-gate.sh",argv_digest:"00"}))'
```

**期望**：两条均 **hook deny（exit 2）**，且 **不得产生**可被 finalize 吃的文件。

### Payload Grok-B — “假 PASS 全集 + 抄当前 lock digest + 错 producer 混tok”
在 **白天** 或 test harness（不经 hook 也可，验证 finalize 本步）：

1. 手工造齐 C1–C6 信封：`status=PASS`，`control_plane_digest=<当前真值>`，但
   - C1.producer = `finalize-page.sh`（错配）
   - 其余 producer “看起来像”对
2. 再跑 `finalize-page.sh`

**期望**：`FAILED_INVARIANT` **exit 3**，stderr 含 producer 类关键字；**不得**写出 `final_status: DONE`。

（若 Grok-A 全绿拦死、Grok-B exit3，则 P0-1/P0-3 手续闭环。）

---

## 5. 能否“通过”？— 分级签字

```text
§17a knowledge alignment:     PASS with residual (S1 detective)
Implementation P0 (tool):     CLEARED pending Grok-A/B 绿 + 可选源码抽读
P1-2 / P1-3 / P1-5:           CLOSED (with listed residual)
P1- others:                   CLOSED / product-decided as above
“无新 P0” 用语:              可用，但必须附加：
                              “无新阻断性实现 P0；S1 子进程残余已记录”
v3.1-GA:                      NO
Conditional first-night GO:   YES, iff all of:
  [ ] Grok-A / Grok-B 当场绿（或等价失败模式符合期望）
  [ ] smoke_attestation=independent 写入本发放行 bag
  [ ] Owner 签署 residual_risk_accepted_by + single_page_single_night + auto_renew=false
  [ ] 首夜页满足 O5 五项机判（preflight 已硬拦）
  [ ] 晨审 checklist 含：repo 根 diff、producer_mismatch、suspicious_invocation、test 内写控制面嗅探
```

### 明确问答你的原句

> **「可以把 P1-2/1-3/1-5 升格或销案，并重开是否仍有 P0，能通过了么」**

1. **P1-2 / P1-3 / P1-5：销案**（不升格；P1-3/5 带书面残余）。
2. **仍有的“P0？”：实现级新 P0 — 没有；原三项 — 已修可降级。**
3. **“通过了么？”**
   - **§17a 审计（实现无新阻断 P0）— 接近通过，差 Grok-A/B + Owner 签 S1**；
   - **GA — 未通过**；
   - **首夜 Conditional GO — 条件通过**，不是无条件立即睡眠 Full GO。

---

## 6. 正式签署（更新版）

```text
Grok-4.5 · §17a re-review
Architecture:                 still SIGNED OFF
R1–R6 / O1–O5 落盘态度:        Accept as implemented-with-evidence (claims)
Tool-surface bash bypass:     Mitigated (hook v2) — residual → S1
Self-attested smoke only:     Mitigated by independent rerun bag
Fake PASS envelopes:          Mitigated by producer+digest+finalize
P1-2, P1-3, P1-5:             CLOSED
New blocking P0:              NONE (under detective-control policy)
S1 subprocess write:          RESIDUAL RISK — not first-night P0
First night:                  Conditional GO after Grok-A/B + Owner sign
GA:                           NO until v3.2 预防式隔离与 §18 全闭合证据
```

---

### 给实现方的一句收口话

> **你们这轮响应把我原 P0 从“路径存在”推进到了“路径已被白名单+权威字段挡住，残余诚实落在 §4.5 已声明的 S1”**——这是正确的工程降级路径，不是甩皮。
> **P1-2/1-3/1-5 我准许销案。**
> **现在挡在 Conditional GO 前面的不再是架构分歧，而是：两条我点名的 payload 当场绿灯、独立 attestation 入袋、Owner 对 S1 子进程残余签字。**
> 三样齐了，§17a 我这边可以写：**无新阻断性 P0，有记录残余，首夜 Conditional GO。**
> **GA 和“无监督放心睡”仍然不在此轮。**
