# CarrorOS 前端无人值守 v2.0（第二轮整合定稿）

> v2.0 | 2026-07-18 | 作者：Kimi K3（在 CarrorOS 治理会话内产出）
> 输入：GPT-5.6 Sol《Autopilot v2.0》+ Grok 4.5《v1.1 补丁包 14 条 + Go/No-Go 清单》+ Opus 4.8《11 份落盘物件》
> 硬约束（用户拍板，不可评审推翻）：**执行时没有高阶模型。高阶模型只存在于规则制定与方案评审阶段。**
> 与 v1.0 的关系：v1.0 骨架（模型舰队 / J0 / 12 步夜循环 / C0–C8）**一字不改**，v2.0 是把三家补丁全部机器化后的版本。

---

## 0. 第二轮收敛判定

三家分歧已经消失，证据：

- Grok 判我的 v1.0 是"最接近今晚能跑的一版"，要求 14 个补丁 → Opus 把补丁全部写成了可落盘物件（含 Grok 截断的 acceptance_report 模板，由 Opus 补完）；
- GPT 判"无补丁 No-Go、小规模有条件 Go"，其 v2.0 的每个机器契约元素都能映射进 Grok 的补丁体系，无一冲突；
- 三家对首夜形态完全一致：≤3 页、串行、Patch A、Draft PR only、K3 关闭。

**只剩两个真实分歧，我作为整合者直接裁决（欢迎第三轮反驳）：**

| 分歧 | GPT 立场 | Grok 立场 | 我的裁决 |
|---|---|---|---|
| 首夜前是否要 L0 影子周（只分析不写码） | 成熟度从 L0 起 | P0 全绿即可真跑 | **L0 降为可选项**。Draft PR only 本身就是影子——产物不进主干，真跑的信息量远大于影子跑。仅当 Phase 0 输入质量存疑时才用 L0 试一页 |
| 任务契约形态 | 每页独立 task.yaml | 单一 night-manifest.yaml | **单一契约**。manifest 的 pages[] 吞并 task.yaml 全部字段（ui_policy / required_states / risk）。两个文件 = 两个真相源 = 夜间漂移风险 |

---

## 1. 第二轮采纳表

| 来源 | 采纳 | 修改/拒绝 | 理由 |
|---|---|---|---|
| GPT v2.0 | `ui_policy` 机器可读块、交互状态矩阵（idle→submitting→success/business_error/network_error）、`reuse-map.json`、证据 SHA 新鲜度规则（改码后旧证据自动失效）、DONE/BLOCKED/FAILED 三结果枚举、L0–L3 成熟度量化指标 | 独立 task.yaml → 并入 manifest pages[]；独立状态机系统 → 只取状态名，引擎仍是 carros_base.py；L0 影子周 → 可选；证据 sha256 文件哈希 → v1.2 | 首夜不建新系统；单一契约源 |
| Grok v1.1 | **全部 14 个 patch，无修改**：Patch A 锁定 / J0 六优先级 + assumptions schema / mock 不降业务等级 / 三机器门 / 阻塞码七枚举 / shared 腐蚀熔断 / 证据完成制 / Draft PR 四段模板 / 首周串行≤3 / 视觉可判定子集 / 失败分派 / Phase 0 首次 90–180min / 夜级熔断收紧 / 三 Owner 指定 | 无 | 与 v1.0 骨架完全同构，就是它缺的肉 |
| Opus 11 份物件 | 全部作为 v2.0 标准物件：3 模板（manifest / acceptance_report / assumptions）+ 5 脚本（scope-check / c7-check / evidence-check / preflight / morning-report）+ 3 治理文件（gap-registry / open-questions / phase0-checklist） | **落盘前必须修 §2 的 10 处勘误** | 见下 |

---

## 2. 对 Opus 11 份物件的勘误（E1–E10）★ 本文最有价值的部分

逐行审查结论：模板类（manifest / assumptions / gap-registry / open-questions / phase0-checklist / acceptance_report）**零缺陷**，直接可用。脚本类有 10 处会在真实首夜炸掉的缺陷，按危险度排序：

### E10（最危险）：morning-report.sh 阻塞聚合循环逻辑反转
- 位置：`opus.48.md:1879`，§2 阻塞码聚合循环
- 原文：`[[ -z "$task_dir" ]] || continue`
- 问题：`-z` 在目录名**非空**时为假 → 执行 `continue` → **跳过所有非空目录**。对比 §1 循环（1825 行）写的是正确的 `&& continue`
- 后果：早晨报告 §2"需你裁决"**永远为空**——BLOCKED_INPUT 的契约冲突静默丢失，人类以为一夜无阻塞。这是全套物件里唯一一处"系统撒谎"级缺陷，恰好炸在 Grok 早晨 8 问的第 5 问上
- 修法：`||` 改 `&&`

### E9：morning-report.sh 字段提取与 acceptance_report 模板格式全部不匹配
- 位置：`opus.48.md:1837-1841, 1883, 2050-2052`
- 问题：脚本 grep `^final_status:` / `^branch:` / `^draft_pr_url:` / `^blocked_code:` / `^model_calls_total:` / `^ac_total`，但 acceptance_report 模板里这些字段全在 markdown 表格行内（`| branch | ... |`）或 `- blocked_code:` 列表项内，**全部落空** → 晨报 §1/§6 显示 UNKNOWN 和 0
- 修法（双改，落盘时一并做）：
  1. acceptance_report.md 模板末尾强制追加机器可读块：
     ````markdown
     ## 11. machine_summary（脚本专用，禁止手改）
     ```yaml
     final_status: DONE
     ac_total: 14
     ac_passed: 14
     branch: draft/fe-order-20260718
     draft_pr_url: ""
     blocked_code: null
     model_calls_total: 18
     fix_rounds_used: 2
     wall_clock_min: 71
     kimi_used: 0
     ```
     ````
  2. morning-report.sh 改为 `sed -n '/## 11\. machine_summary/,/```/p'` 提取后解析该 yaml 块
  3. 顺带统一字段名：manifest 用 `created_at`，morning-report grep 的是 `started_at`（1798 行）→ 统一为 `created_at`

### E1：scope-check.sh 的允许列表未含 e2e spec 路径
- 位置：`opus.48.md:425-434`
- 问题：FILES_ALLOWED 只含 `src/pages/{domain}/`，但 manifest 模板 `paths.spec` 指向 `tests/e2e/{domain}.spec.ts` → 夜间提交 spec 后 C1 必 FAIL → 误熔断每一页
- 修法（二选一，我推荐 A）：
  - **A. 改约定**：spec 放 `src/pages/{domain}/__e2e__/{domain}.spec.ts`，与页面同域。C1 零改动天然覆盖，符合页面目录自治；代价是 playwright.config 的 testDir/testMatch 加一条 glob
  - B. 改脚本：从 manifest 解析 `paths.spec` 加入允许列表（引入 yq 依赖）

### E2：scope-check.sh / c7-check.sh 的 untracked 文件盲区
- 位置：`opus.48.md:455, 623`
- 问题：`git diff --name-only "$BASE_SHA"` 看不见未跟踪文件。模型若写了 `src/styles/tokens/evil.ts` 且未 commit，两个门都放行
- 修法：两个脚本各加一段——`git ls-files --others --exclude-standard -- src/` 非空即 FAIL（夜间规则：C1 前必须原子提交，存在 untracked 即违规）。顺带：scope-check smoke 模式 `echo > "$SMOKE_FILE"` 前加 `mkdir -p "$(dirname "$SMOKE_FILE")"`，否则目标 repo 无 tokens 目录时 smoke 在 set -e 下直接死

### E6：evidence-check.sh 不验证证据真实性和新鲜度
- 位置：`opus.48.md:868-882`
- 问题：① 证据关键词表缺 `.zip` / `.webm` / `trace`；② 只查证据字段非空，不查截图文件**真实存在**；③ 不查绑定 SHA == 当前 HEAD——GPT 的"改码后旧证据自动失效"规则没有落地
- 修法：PASS 的 AC 逐条加两查——证据中的 `.png` 路径 `[ -f ]` 存在性检查；绑定 SHA 列与 `git rev-parse HEAD` 比对，不等即 FAIL（证据过期，需重验）

### E3：c7-check.sh 魔法 px 检查误伤 `1px` 边框
- 位置：`opus.48.md:670`
- 问题：正则 `[^0-9]([1-9][0-9]*)px` 命中 `border: 1px solid`——这是 tokens 体系通常不覆盖的惯用法，首夜会白白烧掉修复轮次
- 修法：放行 0px/1px，正则改 `[^0-9]([2-9]|[1-9][0-9]+)px`

### E5：c7-check.sh 裸色值检查误伤注释/字符串
- 位置：`opus.48.md:660`
- 问题：`#[0-9a-fA-F]{3,8}` 会命中注释里的设计稿标注（如 `// 设计稿主色 #1D7AFA`）→ 夜间无人，误伤即误熔断
- 修法：限定属性值位置，正则改 `[:=(]\s*["']?#[0-9a-fA-F]{3,8}`（冒号/等号/左括号后的 #hex 才算裸色值）

### E4：c7-check.sh antd-theme 豁免是死代码
- 位置：`opus.48.md:647-651`
- 问题：豁免判断在 `.scss` 分支内匹配 `*antd-theme*`，但 antd-theme 是 `.ts` 文件，永不触发；且首夜 Patch A 根本不需要此豁免
- 修法：首夜直接删除该分支；Patch B 启用时再放回正确位置

### E7：preflight.sh 未检查人类签署
- 位置：`opus.48.md:1504-1522`（manifest 检查段）
- 问题：只查 manifest 存在和字段完整，不查 `human_signoff.go_nogo` → 未签署也能放行，`lx-goal on` 前最后一道闸门有洞
- 修法：加 `grep -E 'go_nogo:\s*"?(GO|CONDITIONAL_GO)"?' "$MANIFEST_PATH"`，不命中即 FAIL 并提示"先签署 phase0-checklist"

### E8：preflight.sh 的 lint 参数传递依赖 package.json
- 位置：`opus.48.md:1442`
- 问题：`pnpm lint --max-warnings 0` 能否生效取决于 repo 的 lint script 定义，参数可能被吞
- 修法：改 `pnpm exec eslint . --max-warnings 0`（或落盘安装时人工验证一次）

**勘误总评**：10 处里 1 处系统撒谎级（E10）、2 处功能失效级（E9/E1）、其余为误伤与健壮性。模板零缺陷。修完后这套物件达到落盘标准。

---

## 3. 合并后的唯一契约：night-manifest.yaml v2.0 变更点

以 Grok 的 manifest 模板为底，并入 GPT task.yaml 的字段（**不新建文件**）：

```yaml
# pages[] 每页新增三个字段（来自 GPT task.yaml）：
pages:
  - id: "FE-order"
    # ... Grok 原有字段不变 ...
    risk: "B1"                        # B0|B1|B2（首夜无 B3）
    ui_policy:
      mode: "custom"                  # custom|antd6|hybrid，首夜锁 custom
      token_source: "src/styles/tokens/"
      allow_global_override: false
    required_states:                  # 与 Grok e2e_min_required 合并为这一个字段
      - success
      - empty
      - loading
      - business_error
      - network_error
      - double_submit
      - modal_close_rollback
```

配套机器执行（新增，进 c7-check.sh 或独立 ui-policy-check）：
- `ui_policy.mode == custom` 时：`grep -rn "from ['\"]antd" src/pages/{domain}/` 非空 → C3 FAIL
- `allow_global_override == false` 时：diff 中出现 `:global` / `!important` → C3 FAIL（warn 起步，首夜直接 FAIL）

`e2e_min_required` 字段删除，统一用 `required_states`（一个字段一个含义）。

---

## 4. 状态机定名（GPT 11 态 ↔ v1.0 十二步 ↔ carros_base.py）

不建新状态机系统，只把 GPT 的状态名映射为 carros_base.py token.json 的合法状态值：

| GPT 状态 | v1.0 步骤 | 门禁 | 引擎 |
|---|---|---|---|
| INTAKE | Phase 0（人类） | C0 | manifest 签署 |
| RESEARCHED | 步 1 research | — | carros_base init |
| CONTRACT_FROZEN | 步 2 plan 冻结 | — | plan.md frozen 标记 |
| IMPLEMENTING | 步 3–5 原子提交 | — | git |
| STATIC_VERIFIED | 步 7 | C2 typecheck/lint/build | pnpm |
| ARCHITECTURE_VERIFIED | 步 8 | C3 c7-check + ui_policy | c7-check.sh |
| BEHAVIOR_VERIFIED | 步 9 | C4/C5 七态 spec | playwright |
| VISUAL_VERIFIED | 步 10 | C6 可判定子集 | chrome-devtools |
| EVIDENCE_BOUND | 步 12 前半 | C7 evidence-check | evidence-check.sh |
| DRAFT_PR | 步 12 后半 | C8 archive | carros_base verify/archive + gh |
| （任意态）→ BLOCKED_* / FAILED | 熔断 | — | 阻塞码七枚举 |

**与 GPT 的顺序差异**：GPT 把 ARCHITECTURE 放 VISUAL 之后；我保持 C3 在 C4 前——静态检查便宜，行为/视觉贵，便宜先跑、贵了少跑。这是 v1.0 就定的"前门不过不进后门"原则，第三轮可辩。

断点恢复规则（GPT 的 executor.jsonl 思想，落到现有机制）：每步完成即更新 token.json + executor.md；崩溃恢复时从**最后一个 VERIFIED 态**续跑，不重规划——这正是 CarrorOS 抗 Compact 磁盘态已有的能力，只需把状态名对齐。

---

## 5. 回答 GPT 的五个开放问题

**Q1：规则写出来 ≠ 机器执行得对。**
同意，这正是 Grok Patch-04 + Opus 三脚本 + 我 §2 勘误的组合答案。落盘标准：三脚本 `--smoke` 必须能故意 fail（preflight 第 9–11 项强制），E1–E10 修完才允许进 Phase 0。

**Q2：J0 还需彻底机器化。**
已机器化到边界：六优先级 + 七阻塞码 + assumptions schema（reason_priority 引用编号）覆盖了"走哪条出口"的判定。剩下不可机判的部分（"两种实现工作量差 2 倍"的估算）由 Pro 在 plan 冻结前自评写入 assumptions.yaml——**J0 从不要求机器判断"对不对"，只要求机器判断"走哪条出口、留什么证据"**。对不对，早晨人审。这是"执行时无高阶模型"硬约束下的理论极限，再进一步就需要裁决者，而裁决者不存在。

**Q3：Mock 不消除前端风险。**
全盘接受 Grok Patch-03：mock 只坍缩外部副作用风险，不坍缩业务等级。落地为两条硬规则：① 写操作页 `required_states` 七态全过才允许 DONE，缺任一最多 `DONE_WITH_ASSUMPTIONS`；② mock 契约与真实 API 的偏离风险不由夜间吸收——白天联调发现偏离 → 记 error-dna，次日修 mock 层，不追溯夜间责任。

**Q4：antd 策略机器可读。**
已并入 manifest `ui_policy.mode: custom`（§3），c7-check 加 antd import 扫描。Patch B 的启用条件是**另一次人类签署 + 另一份 manifest**，夜间永不可能自行切换。

**Q5：缺真实基准数据。**
首夜即采集，指标就是晋升标准（§6）。晨报 §6 成本统计 + Grok 早晨 8 问控制面指标，全部从 machine_summary 自动聚合（E9 修完后）。

---

## 6. 首夜定义（最终版）与成熟度阶梯

### 首夜（L1）
- Phase 0 首次预留 **3 小时**（Grok Patch-12 的 90–180min 取上限），其中 preflight.sh 全绿 + 人类签署 GO 才可 `lx-goal on`
- ≤3 页、串行、**V0–V2**（采纳 GPT，V3 第二夜起）、L0–L2、无 B3、patch_a、kimi_calls_total=0、Draft PR only
- 三 Owner 睡前指定（可同一人）：Design System / CarrorOS 门禁 / 早晨审查
- 早晨预留 45–90 分钟，**先答 Grok 8 问（控制面），再看产量**

### L1 → L2 晋升标准（量化，连续 2 夜达标）
越界改动 = 0 且 假完成声明 = 0 且 AC 有证据通过率 ≥ 90% 且 断点恢复成功率 = 100% 且 单页人工返工 < 30min
→ 放开：≤5 页、V3≤1、kimi_calls_total≤2

### L2 → L3 晋升标准（再连续 2 夜 + 七态 spec 通过率 ≥ 95%）
→ 放开：并行 ≤2（lx-race 从 archived 恢复并验证）、shared 修改仍**永远**白天预授权

### 任何 L 都永不开放
自动合并主干 / 真实后端 / B3 / 夜间触碰 tokens·shared·router·auth / 夜间切换 ui_policy.mode

---

## 7. 给三位评审的靶子（第三轮，请直接攻击）

1. **攻击脚本，别攻击架构**：E1–E10 之外，五个脚本里还有哪一行会在真实首夜炸？请给行号和触发场景。
2. **spec 同域**（`src/pages/{domain}/__e2e__/`，我选）vs 集中（`tests/e2e/`，GPT/Opus 模板原样）——同域换 C1 零改动，代价是 playwright 配置一条 glob。谁反对，给理由。
3. **单一契约**（manifest 吞并 task.yaml）vs GPT 双文件——双文件的真实收益是什么？我没看到，只看到两个真相源。
4. **门禁顺序**：C3 架构门在 C4 行为门前（便宜先跑）vs GPT 架构门放最后——GPT 的顺序优势是什么？
5. **L0 影子周**：P0 全绿 + Draft PR only 的前提下，影子周的边际价值是什么？Draft PR 本身就是影子。
6. **证据新鲜度只绑 HEAD SHA、不加 sha256**："截图在最终 commit 之后被后续步骤覆盖"这个洞首夜要不要堵？我判不用（截图步骤在最终 commit 后、archive 前，中间无写码），请找反例。

---

## 8. 落盘计划（第三轮 sign-off 后执行，本轮不动手）

1. 11 份物件 + E1–E10 修复 → 落盘到目标前端 repo（`scripts/` + `.omc/`）与 CarrorOS（模板源）
2. c7-check.sh 增加 ui_policy 扫描（§3）
3. acceptance_report.md 模板增加 machine_summary 块（E9）
4. playwright.config 增加 `src/pages/**/__e2e__/` glob（若靶子 2 无人反对）
5. Phase 0 按 Grok 清单逐项打勾 → preflight 全绿 → 签署 → `lx-goal on`

---

一句话总结：

> **v1.0 证明骨架对，v2.0 把每一根骨头换成机器：契约一个文件、门禁五个脚本、阻塞七个码、证据绑 SHA、早晨一份报。三家评审的全部分歧已收敛为两个裁决点（L0 可选、单一契约），剩下的唯一风险是脚本缺陷——E1–E10 已修在纸上，第三轮请验证我修得对不对。**
