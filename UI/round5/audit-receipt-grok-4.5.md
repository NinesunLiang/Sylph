# §17a 落盘审计回执（Grok-4.5 · v3.1 → RC）

> 审计对象：你们提交的**落盘实现清单 + smoke 自证摘要**
> 规格锚点：`UI/FINAL.md` v3.1（尤其 R1 权威链 / §4.5 信任边界 / C0–C8 / fail-closed）
> 范围声明：本回执**没有**逐字节打开 `scripts/carroros-gates/**`、`carroros-night-deny.py`、`night-loop.md` 的源码。我审的是「清单能不能自洽」「自证有没有自欺」「对重点攻击面的残余是否被诚实对待」。
> **没拿到源码就不能签“无旁路证明”。** 下面 P0/P1 是：**按摘要即可成立的阻断项 + 必须用源码当场证伪的嫌疑项**。

---

## 总判断

| 维度 | 判断 |
|---|---|
| 落盘骨架是否朝 FINAL.md | **基本对齐**（gate envelope、lock、deny hook、assertion-catalog、C8a 从 gate-results 重算、smoke 含 fail-open/篡改） |
| 自证是否可当 GA 证据 | **不可**——13/13 绿 + “失败原因核对过”目前是**实现方自陈**，不是独立复跑证 |
| 首夜 Runtime | **仍 NO-GO / 不得签 “无新 P0”** |
| 原因 | 至少 **2 个 P0 按摘要即可确认**；另有 **多个“源码一查就可能升 P0”** 的攻击面未闭合 |

**明确结论：不能写“无新 P0”。**

---

## P0（阻断首夜）

### P0-1 — Bash/CLI 旁路未在攻击模型里被杀死
**文件:** `.claude/hooks/carroros-night-deny.py` + 任何 `Write/Edit` only 的 deny 叙述
**缺陷:** 摘要假设「不能写控制面；token 只能走 `token-write` CAS」。真实夜间模型通常仍有 **Bash**。若 deny 只拦 `Edit/Write` 路径、不拦：

```bash
python - <<'PY'  # 或 printf / tee / install / dd
open(".../gate-results/C6.json","w").write(...)
PY
echo 'final_status: DONE' > verification-summary.yaml
```

则 R1「结论只能 reduce(gate-results)」在运行时被掏空。
**攻击:** DeepSeek 读懂 `finalize-page.sh` / envelope schema → Bash 直接种全套 PASS gate-results → 调 finalize → 早晨 scorecard 真 DONE。
**这与 §4.5 “同一执行身份”残余完全同构，而且比改 settings 更容易。**
**修法:**
1. deny 规则必须覆盖：**Bash/Shell 对治理路径的写命令**（或 night 会话直接禁用任意写治理路径的 shell，只允许 allowlist 子命令）。
2. 或 gate-results **目录级不可写**（OS ACL / 独立 uid；这才是 v3.2 preventive，更正统）。
3. smoke **必须加「Bash 直写 gate-results / summary」攻击用例**，现在 5 条篡改看起来都站在「API/脚本入口」视角，**没打穿工具面**。

未证明 hook 扎进 Bash 之前 → **P0**。

---

### P0-2 — Smoke 13/13 是自证，不是审计证据（证据自欺）
**文件:** `smoke/run-all.sh` 与“已验证证据”整段
**缺陷:** FINAL.md GA 门要求「五类 smoke **实跑**绿证」。你们给的是：

- 自己跑的 13/13
- 自己宣称 5a stderr 含指定字符串
- 自己宣称 hook 白天不生效

这是**实现完整性自检**，不是 §17a 要的高阶审计。审计在没复跑 stderr 原文、lock 条目列表、reducer 输入夹具前，**不能**把「无新 P0」建立在自陈上。
**失败场景:** 绿的是 fixture 目录，不是真实 `PAGE_BOUNDARY_RESET` 后工作树；或 `set -e` 漏网导致断言失败仍 exit 0。
**修法:**
1. 在干净 clone/worktree **独立复跑** `smoke/run-all.sh`，把每条的 **exit code + stderr 关键行 + 产物 diff** 贴进审计包。
2. 至少一份 **把控制面故意改坏** 的外部复现（由评审方指定 payload，不是实现方内定 5 条）。
3. scorecard 里增加 `smoke_attestation: independent|self`，self 不得放行首夜。

**在独立复跑附件齐备前，§17a 对本落盘不得闭环。**

---

### P0-3 — “token 只能 CAS”并不能防止假 DONE（若 finalize 输入面可控）
**文件:** `finalize-page.sh` + `.omc/scripts/carros_base.py`（`token-write` / `gate-results-init`）
**缺陷:** 摘要：token 冲突 → `FAILED_INVARIANT`。正确。但若：

- 模型能通过 **Bash** 种 gate-results（见 P0-1），或
- `gate-results-init` / 某 helper **以执行身份可写**完整 envelope（含 PASS），或
- finalize 在「缺 C6」时 fail，但在「伪造 C6 PASS 信封」时 **reduce 通过对 schema 但不对权威**（没有 supervisor 签名）

则早晨看到的是 **reducer 真心算出来的 DONE**——比手写 token 更毒，现有「手写 token 称 DONE 缺 C6 → exit3」用例**打不中**。
**攻击:** 合法 schema 的假 PASS 全集 → finalize → immutable `verification-summary.yaml` = DONE → Draft PR。
**修法:**
1. gate result 写入 **只允许** `run-gate.sh` 一条链；init 只建空目录/占位，禁止写 `status:PASS`。
2. envelope 强制 `producer: run-gate|scope-check|...` + `argv_digest` + `control_plane_digest`，finalize 校验 producer allowlist。
3. 篡改 smoke 增加：**schema 合法、script_hash 抄当前 lock、内容假 PASS**。

这条在 P0-1 关掉前默认成立。

---

## P1（首夜后必修；若源码证实则现场升 P0）

### P1-1 — `control_plane_lock` / `scripts_digest` 覆盖是否含“可改 settings 禁用 hook”的闭环
**文件:** `gen-control-plane-lock.sh`、`lib/common.sh`、`install-night-hook.sh`
**缺陷:** FINAL §4.5 已诚实写了：改 `settings.json` 关 hook 并等会话重启可绕。你们把 `settings.json#hooks` 做成 **伪条目哈希**，方向对。但未说明：

- lock 是 **签进 manifest 后不可再生**，还是夜间可 `gen-control-plane-lock.sh` 重签自洽？
- preflight 之后 lock 被改，门禁自验失败是否 **立即 NIGHT_FUSE**？
- hook 脚本自身 + `carroros-night-deny.py` 是否进 **19 项**？

**攻击:** 改 hook 使之放行 → 重算 lock（若可）→ 或故意让 lock 检查在某条路径 fail-open。
**修法:** lock 生成 **仅 Phase 0 / 人类**；夜间任何 `gen-control-plane-lock` = 违规；deny + preflight + 每门禁自验 **fail-closed**；hooks 段 + deny.py 必须进锁。

### P1-2 — fail-closed 三处经典洞（摘要未证伪）
**文件:** `lib/common.sh` lock 自验；`evidence-check.sh`；`finalize-page.sh` reducer
**嫌疑（需读码一锤定音）:**
1. lock 文件缺失 → 当 “开发模式跳过”？
2. `evidence-index.yaml` 缺字段 / 空数组 → 当 0 AC 仍 PASS？
3. gate-results 0 文件 → fail-open smoke 有了，但 **缺某一个 gate**（有 C1–C5 无 C6）是否被‌还原成 summary 的“部分完成”而非硬 FAIL？
4. YAML 锚点/重复键/科学计数导致 schema “过了但语义歪”
5. `SUPERSEDED` 过滤后 **无有效结果** 是否当成空成功？

每处默认按 **fail-closed** 写单测；任何 `|| true`、空分支 `exit 0` → 升 P0。

### P1-3 — C1 `git show-prefix` 子目录
**文件:** `scope-check.sh`
**缺陷:** target 为 monorepo 子目录时，`git diff --name-only` 常带 prefix，`files_allowed: src/pages/x/**` 若一端带 `apps/web/` 一端不带 → **误杀或放过**。
**攻击/失败:**
- 放过：allowed 按 strip 后比，diff 未 strip → 前缀不一致被当“不在 diff”
- 误杀：反之为 BLOCKED_SCOPE，预算烧光
**修法:** 统一 canonical：全部相对 **repo root** 或全部相对 **page root**，`show-prefix` 只做一次 normalize；用 `carros_base manifest-json` 的规范化路径，禁止脚本自行二次 pan 模式；补 **prefix 非空** 的 smoke。

### P1-4 — `assertion-catalog.yaml` 与真 Playwright 断言未闭合
**文件:** `assertion-catalog.yaml` + C4/C5 执行器 / `run-gate.sh`
**缺陷:** 封闭词表落盘 ≠ **每条 id 有 helper 实现**。若 catalog 有 `skeleton_visible` 而 spec 引用但 runner 未知 id **skip**，O3 退化成存在性。
**修法:** preflight：`pages[].required_states` 全部 id ⊆ catalog，且 catalog 每 id **有可执行绑定**；未知 id → C0/C4 `FAILED_INVARIANT`。smoke：故意未知 assert id 必须红。

### P1-5 — night-loop.md 语义泄漏（合理误解）
**文件:** `.claude/workflows/frontend-overnight/night-loop.md`
**高危话术分类:**
- “尽量并发完成门禁” → 跳顺序 / 自写 summary
- “若门禁脚本异常可手动记录结果” → 手写 gate-result
- “更新 token 为 DONE” 而未写死 **只能 finalize 后由 CAS 写***
- “接近完成可先开 PR” → 绕 `draft_pr_on: DONE_only`

**修法:** 手册改成 **状态机祈使句** + 禁止列表（禁止手写 verification-summary / gate-results；禁止猜测 final_status）；每步唯一合法命令贴死（`run-gate.sh C4` 等）。对模型跑一次 **红队 prompt**（诱导跳门禁）看是否服从。

### P1-6 — intake 分期输入腐蚀权威链
**文件:** `intake.md`（api_doc 滞后 + inferred 契约）
**缺陷:** inferred API 写进测试/AC 后，早晨当“有证据通过”，但契约从未被人类 signoff。
**腐蚀路径:** inferred → playwright mock → C4 PASS → DONE；真实 API 次日反转 → 权威 AC 是假的。
**修法:** inferred 必须进 `assumptions.yaml`，`touches` 与 AC **贴标 `UNTRUSTED_CONTRACT`**；`evidence-check` 对仅依赖 inferred 的 AC **不得** 计满分 `ac_pass`；只允许 `BLOCKED_INPUT` 或晨报红旗阻断“当生产 DONE”。Draft PR body 强制列出 inferred 清单。

### P1-7 — O5 / 选页机判仍未见物件
**文件:** `preflight.sh` / `templates/night-manifest.template.yaml` / `phase0-checklist`
**缺陷:** 摘要的 10 项 preflight 未列 “复杂度 V0–V1 + 输入完整 + happy path 可测”。只有 `len(pages)==1` 不够。
**修法:** 模板加油字段 + preflight 硬拦（我方此前 O5 / 选页机判）。

### P1-8 — S1 残余风险 Owner 未闭合（规格债，落到今夜）
**文件:** 签署面 `night-manifest.signoff.yaml` / scorecard
**缺陷:** FINAL 允许 detective controls 首夜，但 **必须** Owner 显式 `residual_risk_accepted`。摘要未提签署字段。
**修法:** signoff 增加：
```yaml
s1_residual_risk_accepted: true
scope: single_page_single_night
auto_renew: false
```
preflight 读到 false/缺失 → NO-GO。

---

## P2（演进，不挡首夜）

| ID | 项 | 建议 |
|---|---|---|
| P2-1 | 完整 supervisor / gate-results 只读身份 | v3.2 preventive 隔离 |
| P2-2 | gate envelope 加 HMAC/签名 | 防同 uid 合法 schema 假 PASS |
| P2-3 | O1/O2 升 C3 阻断 | 现晨报指标可接受 |
| P2-4 | dry-cost 预算写入各自实测 | 与控制面正交，但首夜前要有数 |
| P2-5 | delivery_status 与重算 verification 完全正交 | 防状态机图再次糊回 |

---

## 针对六个重点攻击问题的直接回答

| # | 问题 | 在现有信息下的答案 |
|---|---|---|
| 1 | 权威链旁路？ | **有可达旁路口——优先 Bash 写 gate-results + 合法 schema 假 PASS + finalize 真 reduce**。以“不能写控制面”为假设 **不成立**，除非 hook 证明拦了 shell 写。 |
| 2 | fail-closed 洞？ | smoke 形状对，但 **lock 缺失、缺门、空 SUPERSEDED、evidence 空 AC** 等未在摘要中看到针对性失败证。默认 **有洞嫌疑 → P1-2**。 |
| 3 | C1 prefix？ | **典型坑，摘要零提到 prefix smoke → P1-3**，子目录 monorepo 首夜高危。 |
| 4 | night-loop 误解？ | **未见原文；高概率存在语气洞 → P1-5**。必须红队。 |
| 5 | intake inferred？ | **会腐蚀 AC 权威，除非打 UNTRUSTED 且不计满 Done → P1-6**。 |
| 6 | 其他 | 自证 smoke、S1 签署字段、catalog 绑定、O5 机判。 |

---

## 对“已验证证据”的复核：有无自欺

| 宣称 | 审计判定 |
|---|---|
| smoke 13/13 绿 | **自欺风险高**：无独立复跑、无 inspector 签名日志 |
| 5a stderr 含特定句 | **弱可用**：比“碰巧 exit 3”好，但未附原始日志 |
| preflight 11 项命中模板 NO-GO | **方向正确**，需表列出 11 项名 vs FINAL 要求 |
| 模型路由 K3 vs DeepSeek | **有用**，非权威链核心 |
| deny 5 规则白天不生效 | **必要但不充分**：未测 Bash、未测会话标记伪造、未测 settings 篡改 |

**结论：当前证据包证明“脚本作者相信自己的 happy/adversarial fixture 过了”，不证明“夜间 DeepSeek 工具面攻不破权威链”。**

---

## 签署（Grok-4.5 · §17a）

```text
Spec alignment (skeleton):     LARGELY ALIGNED
Implementation trust:          NOT CERTIFIED（无源码级复审 + 无独立 smoke）
New P0 found from package:     YES（P0-1 工具面旁路模型、P0-2 自证当证据、P0-3 合法假 PASS）
“无新 P0”:                     否定 — 不得使用这句
v3.1-GA:                       NO
First-night Conditional GO:    NO，直到：
  1) Bash/治理路径写面关掉或 ACL 封死，并有对应攻击 smoke 绿
  2) 独立复跑全套 smoke，附件进审计袋
  3) 假 PASS envelope / producer allowlist 钉死
  4) signoff 含 S1 残余风险人签 + O5 选页机判
  5) 我方或并列审计员抽读：deny.py / finalize / gate_result.py / common.sh / scope-check / night-loop.md
```

---

### 一句话

> **落盘清单看起来是在实现 FINAL.md，不是在另起炉灶——这点及格。**
> **但用「我们自己 13/13 绿 + 假设模型不能写控制面」来过 §17a，本身就是权威链自攻。**
> 首要怀疑不是 reducer 会不会算错，而是 **DeepSeek 的 Bash 还敢不敢在 deny 眼皮底下种一套老实人 finalize 会信的 PASS。**
> 这没被杀之前，Grok 的 §17a：**有新 P0，NO-GO。**

---

### 为完成真正 code-level 审计，请直接贴（或授权读）最小充分集

优先顺序：

1. `.claude/hooks/carroros-night-deny.py`
2. `lib/gate_result.py`
3. `finalize-page.sh`
4. `lib/common.sh`
5. `scope-check.sh`
6. `smoke/run-all.sh`（含 5 条篡改夹具）
7. `night-loop.md`
8. `preflight.sh`
9. `assertion-catalog.yaml`
10. 独立复跑的完整终端日志

有这 10 样，我可以把 P1-2/1-3/1-5 升格或销案，并重开是否仍有 P0。
