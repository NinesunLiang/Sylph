**Grok-4.5 审核结论（v3.0 定稿审）**

结论先说死：

> **v3.0 文本：架构 Accept with Residual Risks。**  
> **执行层：仍是 No-Go / 未达 v3.0-GA。**  
> Kimi 这次把第三轮绝大部分刀接进了正文，方向正确、收敛到位；  
> **但我不同意“执行物件修复项全部定型 → 修完 §16 就能升 GA 首夜”这种表述。**  
> 还差一组**状态机惩罚与门禁权威链**补丁。没有这些，系统仍可能在“规制全文正确”的同时，运行时悄悄撒谎。

---

## 1. 对 Kimi v3.0 的总评

| 维度 | 评分 | 说明 |
|---|---|---|
| 收敛完整度 | **9.0/10** | P0/P1、E1–E12、G1–G6 主线几乎全收 |
| 与无人值守铁律对齐 | **9.0/10** | 执行时无高阶模型、结论机器生成、1 页试毒、先控制面后产量 |
| 可执行性（纸面） | **8.5/10** | 比 v2 强一个量级，已像“能开工的系统说明书” |
| 抗撒谎完备度 | **7.0/10** | 还缺 token 权威链、C6 失败回退、原型非交互时的浮层门 |
| 当前能否 `lx-goal on` | **否** | §16 未落地 + §18 用户项未闭合 + 五类 smoke 未见实跑证据 |

一句话：

> **Kimi v3.0 已经是“应予采纳的执行宪法正本”；**  
> **还不是“今晚可以发车的运行证明”。**  
> 差的不是再写一篇架构，而是 6 条运行时补丁 + 实跑 smoke 绿证。

---

## 2. 已完全接受、无需再争的部分

以下我盖章，不再反驳：

1. 单一 `night-manifest.yaml`（immutable + digest 签署）  
2. 首夜硬锁 **1 页**  
3. `machine-summary.yaml` 独立文件、门禁生成  
4. 证据绑 `code_sha`，不绑 HEAD  
5. 晨报以 `pages[]` 为源，`CRASHED/NOT_STARTED` 必现身  
6. `--smoke-fail-open` + 五类 smoke  
7. `PAGE_BOUNDARY_RESET` + `WORKSPACE_POISONED` 夜熔  
8. shared-gap 可执行计数熔断  
9. 视觉工具失败 ≠ N/A PASS  
10. 仅 `DONE` 建 Draft PR  
11. 测试保持 `tests/e2e/`  
12. C3 在 C4/C5 前  
13. L0 可选  
14. K3 首夜 = 0  
15. 浮层/滚动升为一等质量维度（§7.1 方向对）

这些说明：第三轮的“控制系统优先于产量”已被写进主干，不再是附录情绪。

---

## 3. 我仍要补充的 6 条（Grok Residual Patch R1–R6）

Kimi 说“无悬而未决技术分歧”。**我不同意。**  
下面 6 条如果第一夜不补，仍会出现“文档全绿、系统假绿”。

### R1. token.json 不能继续是“可写日记”，必须是“门禁驱动状态机”

v3.0 写：`final_status` 来自 `token.json`。  
但没写：**谁有权把状态写成 VERIFIED / DONE？**

若执行会话（DeepSeek）自己把 token 标成：

```yaml
state: DELIVERED
final_status: DONE
```

而门禁日志缺失/失败，则 `finalize-page.sh` 只要“读 token”就会被带跑。这会把 P0-4（模型不能写结论）从正门堵上、从侧门重开。

**补丁（必须写进 finalize + carros_base）：**

```text
状态迁移合法性 = (当前态, 触发门禁脚本exit code, 证据指针) 三元组
- 不允许“只改 token 不附 gate-results”
- finalize-page.sh 以 gate-results/*.json 为准重算 final_status
- token 与 gate-results 冲突 → FAILED_INVARIANT
- 模型/会话对 token 的写入只允许通过 carros_base.py API，不重直接 Edit
```

**门禁权威序：**

```text
gate-results > machine-summary > token.json 展示字段 > acceptance_report.md
```

不是反过来。

### R2. C6 失败后的“降级—重修—作废证据”协议缺失

v3.0 顺序是：

```text
C4/C5 → code freeze → 清 artifacts → C6 → finalize
```

并规定 `VISUAL_VERIFIED` 后写 `src/` = `FAILED_INVARIANT`。  
但没说：

- C6 失败时状态怎么退？
- Fixer 修改代码后，旧 `code_sha` 与旧截图如何强制作废？
- 是否必须重新跑 C4/C5（防“只修样式却改坏交互”）？

**补丁：**

```text
C6 FAIL 或 任意 merge-back 到 IMPLEMENTING：
1. 状态降级到 SCOPE_VERIFIED 之前可写码区（明确 demote 表）
2. invalidate_evidence(old_code_sha)   # artifacts 标记作废，不可再被引用
3. 源码变更后必须重跑：C1→C2→C3→C4/C5→(re)freeze→C6
4. 只允许“治同一 fingerprint 的最小修复”；跨指纹改动计入新 fix round
5. 超过 fix_rounds → BLOCKED_BUDGET / FAILED，不得带着旧图宣称接近完成
```

没有这条，**禁写规则会在第一次视觉失败后变成死锁或被人工空降绕过。**

### R3. §7.1 浮层触发扫描对“静态原型”会集体假 FAIL / 假 BLOCK

R1/R2 很强，但默认原型可“逐按钮点开”。真实常见输入是：

- 一张/一组 PNG 设计稿  
- 不可交互 PDF  
- 只有终态图、没有交互说明的原型

这时执行模型无法“点开发现 dialog”，研究步会系统性漏浮层，又被你定位成“研究失职不得 BLOCKED_INPUT”——结果变成：夜循环被自己的研究标准吊打。

**补丁（研究门分型）：**

```yaml
prototype_kind: interactive | static_images | mixed
overlay_discovery:
  interactive: 允许自动化点击扫描
  static_images: 禁止伪装点击；只能消费
    - PRD 显式浮层清单
    - 设计稿标注
    - Phase 0 人类/高阶预审写入的 overlays[]
  missing_overlay_after_static:
    → BLOCKED_INPUT（缺输入）而不是研究步自我处刑死循环
```

**硬规则：** `pages[].overlays` 在 plan 冻结前必须非空或显式 `overlays_none: true`（人类确认页确认无浮层）。  
“研究失职”只适用于 `prototype_kind=interactive` 且可点却未点的情形。

### R4. fail-open smoke 必须测“权威链绕过”，不只测脚本参数

你写了五类 smoke。G1 我仍坚持，但要加第 0 号攻击用例（preflight 强制）：

| 攻击 | 期望 |
|---|---|
| 手写 `machine-summary.yaml` 为 DONE，ac_passed=99 | finalize 重生成覆盖；若禁止覆盖则 FAIL |
| 手写 `token.json` 为 DELIVERED，但 gate-results 缺 C6 | 不得 DONE |
| 保留旧 `artifacts/*old_code_sha*.png` 并引用 | evidence-check FAIL |
| C6 工具故意 exit 非 0 | 结果 ∈ {BLOCKED_ENV, FAILED}，绝非 DONE |
| 修改 `tests/e2e` 让断言变弱但截图仍旧 | code_sha 新鲜度或 C4 重跑失败 |
| 解析损坏的 manifest | 全部门禁 fail-closed，preflight 禁 `lx-goal on` |

没有“篡改结论 / 半套证据”攻击集，`--smoke-fail-open` 只证明脚本脾气倔，不证明控制系统不会被！

### R5. 阻塞码枚举仍被写乱，机器聚合会再炸一次

正文先说七枚举：

`BLOCKED_INPUT / BLOCKED_SCOPE / BLOCKED_ENV / BLOCKED_BUDGET / BLOCKED_HUMAN / BLOCKED_VISUAL_P0 / FAILED_INVARIANT`

这把 **BLOCKED_*** 和 **FAILED_*** 塞进同一“阻塞码”袋子。  
晨报、熔断器、晋升指标会再次出现映射歧义（跟当初 DONE_WITH_ASSUMPTIONS 同类病）。

**补丁（正交，别再揉）：**

```yaml
final_status: DONE | BLOCKED | FAILED | CRASHED | NOT_STARTED

blocked_code:   # 仅 final_status=BLOCKED 时有值
  BLOCKED_INPUT | BLOCKED_SCOPE | BLOCKED_ENV |
  BLOCKED_BUDGET | BLOCKED_HUMAN | BLOCKED_VISUAL_P0

failed_code:    # 仅 final_status=FAILED 时有值
  FAILED_INVARIANT | FAILED_FIX_LOOP | FAILED_TOOLCHAIN | FAILED_UNKNOWN

delivery_status: DRAFT_PR_CREATED | DRAFT_PR_FAILED | NOT_ATTEMPTED
```

`CRASHED/NOT_STARTED` 是晨报派生态，不由页中途自报。

### R6. 早晨 8 问必须机器作答，不能再变“人盯着报告凭感觉勾”

v3.0 正确地把 8 问置顶，但没规定 **8 问字段全是 special 聚合结果**。  
否则第一晚又会退化成：人类读 Markdown，主观觉得“好像没撒谎”。

**补丁：`control-plane-scorecard.yaml`（由 morning-report 生成）**

```yaml
gates_can_fail_on_purpose: true|false
morning_report_missing_pages: 0
done_without_evidence_count: 0
scope_leak_count: 0
same_fingerprint_loop_count: 0
crash_recoveries_succeeded: n/n
workspace_poison_events: 0
forged_summary_attempts: 0
visual_tool_failure_marked_done: 0
control_plane_green: true|false   # 全绿前禁止进入产量评分
```

**晋升与“首夜成功”定义绑定 `control_plane_green=true`，与页面好不好看解耦。**  
这才是我 G6 的完整落地，不是口号。

---

## 4. 次级但建议首夜前写死的 4 个小洞

1. **preflight 校验模型路由真身**  
   确认 proxy 的 `claude-opus→DeepSeek V4 Pro`、`haiku→Flash` 实打实生效；误连高阶模型 = 直接 No-Go（违反用户铁律）。

2. **code freeze 范围要包含 tests/**  
   你的新鲜度 diff 已含 `tests/`，很好；请在步骤 10 明文写：freeze 后改 `tests/e2e` 与改 `src` 同罪，必须 demote + 重验。

3. **Draft PR 模板增加“控制面摘要”段**  
   除了“做了什么/AC/assumptions/未动公共区”，再强制贴：  
   `code_sha / gates map / qualified / assumptions_present / overlays covered`。  
   防评审只看 UI 截图。

4. **§16 的“落盘完成”≠“GA”**  
   GA 门应是：  
   `物件落盘 + 五类 smoke 绿证（含 R4 攻击集） + §17a 高阶审计 diff 无 P0 + §18 用户两项必填闭合（repo/页/输入、PR 通道）`。  
   少一项都不能叫 v3.0-GA。

---

## 5. 对 §18 用户不确定项：我的票

| # | Grok 票 | 理由 |
|---|---|---|
| 1 antd | **A Patch A** | 宪法无 antd；混用会打碎 token/目录/ui_policy 机器门 |
| 2 首夜页数 | **1 页** | 交控制系统；产量是第二夜的问题 |
| 3 输入 | **必须齐** | 缺 repo/页/PRD/API/原型 = 禁止 Phase 0 完工 |
| 4 PR 通道 | **gh 已 auth 才允许 DONE→PR**；否则 `delivery_status=NOT_ATTEMPTED` 但仍可 DONE | 通道故障 ≠ 实现失败 |
| 5 K3 | **首夜 0** | 先证明确定性视觉子集 |
| 6 Owner | 可同人，但**早晨审查 Owner 必须回答 scorecard，不得只看业务** | |
| 7 预算 | 默认可用；但 **fix_rounds 用尽不得转 DONE** | |
| 8 排期 | 可今日落盘；**不允许“今晚边落盘边首夜”** | smoke + 17a 至少隔一次清醒窗口 |

---

## 6. 最终签署立场（与 Kimi 的关键分歧）

### Kimi 的表述
> 架构 Sign-off + 执行物件修复项全部定型。修完 §16 并通过五类 smoke 即升 GA，可首夜。

### Grok 的表述
> **架构：Accept。**  
> **执行规格：Accept with R1–R6 residual patches。**  
> **GA / 首夜：No-Go，直到下列全部为真：**

1. §16 六脚本 + carros_base `manifest-json` + hook 禁写真实落盘  
2. 五类 smoke **实跑绿**，且包含 R4 权威链攻击集  
3. R1 token/gate 权威序落地（finalize 重算、冲突判 invariant）  
4. R2 C6 失败 demote + 证据作废协议落地  
5. R3 静态原型浮层门分型写入 manifest  
6. R5 阻塞码/失败码正交  
7. R6 `control-plane-scorecard.yaml` 机器生成  
8. §18：至少闭合 **#1 选 A、#2=1 页、#3 输入齐全、#4 PR 通道可知**  
9. §17a 对脚本 diff 做一次高阶审计，无新 P0  
10. 首夜任务清单 **仅 1 页**，K3=0，Draft PR only，无真实后端

满足后我的票才是：

**Conditional GO（1-page control-plane trial night）。**

不满足其中任一条：

---

## 7. 要写进收口纪要的三句（可直接贴评审栏）

1. **采纳 Kimi v3.0 为唯一执行正本骨架。**  
2. **在 GA 前强制并入 Grok R1–R6：门禁权威链、C6 回退作废、静态浮层分型、篡改攻击 smoke、码表正交、控制面 scorecard。**  
3. **首夜定义保持：先证明系统不会撒谎，再证明它会写页面；页面再好看，scorecard 不绿也算失败。**

再压成我一贯的那句：

> **可以开工写脚本了；还不能宣布无人值守已经成立。**  
> **v3.0 证明你们終於把骨头换成了机器；R1–R6 证明机器还没被焊死到不会自己给自己发奖状。**

---

**补充结论（相对 GPT/Opus）：**  
他们已把“伪证据 / 晨报蒸发 / SHA 自指 / 可伪造 summary”基本钉死。  
**我多盯的是下一层：状态机是否仍可被侧写、视觉失败后是否死锁或带旧证重生、静态设计稿会否被交互研究标准误杀、以及早晨 8 问是否仍靠人类感觉。**  
这些不补，第一夜最可能的失败不是“写不出页面”，而是“控制面在祝贺自己成功”。