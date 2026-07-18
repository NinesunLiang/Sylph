# CarrorOS 前端 AI 自主实现方案（最终版 v3.1）

> 2026-07-18 | 四轮十二份评审收敛后的定稿 | 整合：Kimi K3
> 本文取代：v1.0、v2.0-rc1、v3.0（UI/FINAL.md 初版）
> 状态（四层分离，第四轮 U4 修订）：
> - **Document: v3.1-final**（本文可冻结；R1–R6 / S1–S4 / O1–O5 / 第四轮执行语义五项已并入）
> - **Spec consensus: frozen**，附 1 条记录在案的残余风险（S1 侦探式信任边界，需 Owner 签署 = §18#9）
> - **Runtime: RC / NO-GO**——直到 §16 落盘 + 五类 smoke 实跑绿证 + §17a 审计无新 P0 + §18 闭合
> - **GA: 未宣布**。本文是"最终规格"，不是"发车许可"

## 场景定义（用户拍板）

| 阶段 | 可用模型 | 用途 |
|---|---|---|
| **设计时**（开发前） | Opus 4.8 / Grok 4.5 / GPT-5.6 Sol | 方案设计、物件审计、Phase 0 预审（§17） |
| **执行时**（夜间无人值守） | DeepSeek V4 Pro（实现）+ V4 Flash（修复）+ Kimi K3（视觉诊断工具，非裁判） | 全部编码、测试、证据生产 |
| 治理 | CarrorOS（AGENTS.md 宪法 + carros_base.py + lx-goal）+ MCP playwright / chrome-devtools | 边界、状态、证据、恢复 |

**铁律不变**：执行时无任何高阶模型；需要裁决 → J0 出口（§12）。preflight 强制校验模型路由真身：`claude-opus→v4-pro`、`claude-haiku→v4-flash` 实打实生效，**误连高阶模型 = 直接 No-Go**。

---

## 1. 四轮收敛终局

**骨架（v1.0 遗产，四家确认不动）**：模型舰队 / J0 / 夜循环 / C0–C8 / mock 风险坍缩 / 失败分类路由 / 磁盘态恢复 / 浮层滚动契约（§7.1）。

**第四轮修进的五根新承重柱**（前三轮四根：结论门禁生成、证据绑 code_sha、晨报 pages[] 遍历、fail-open smoke——继续有效）：

5. **信任边界**（GPT S1，推翻 Opus P0-4 的"物理上无权"表述）：同一执行身份下"模型不能写结论"只是约定。首夜落地五层最小隔离（§4.5），完整 supervisor 隔离列 v3.2。
6. **门禁权威链**（Grok R1）：`final_status = reduce(manifest, gate-results, execution-events)`；token.json 只是进度缓存，恢复必须重验 gate result，不得见 `*_VERIFIED` 即续跑。
7. **状态回退与证据失效传播**（Grok R2 + GPT 修订）：C6 失败进 `VISUAL_FIXING` 受限写码态；任何 src/tests/构建配置/锁变更使其后全部 gate 结果失效（标 SUPERSEDED 不删除），从 C1 全链重跑。
8. **质量假通过防线**（Opus O1–O3）：页内重复度、token 引用覆盖率进晨报指标；`required_states` 从存在性枚举升级为**逐态断言契约**（没有断言的状态不算覆盖）。
9. **预算实测**（Opus O4）：Phase 0 增 gate-cycle dry cost，预算 = 实测 P90 × 安全系数，不拍脑袋。

**整合者三处裁决的第四轮闭合状态**：
- R5 码表取 GPT/Opus 版（`execution_status` 正交，`final_status` 三值终局）——**Grok 第四轮已显式签字接受（"放弃把 CRASHED/NOT_STARTED 写入 final_status"），闭合**。
- S1 首夜取务实五层隔离（侦探式）而非完整 supervisor 隔离（预防式，v3.2 强制项）——**GPT 记录在案异议（recorded dissent）；Grok 接受为"限时风险承受"但要求五条写死 + Owner 签署。转为 §18#9 用户裁决项，未签署 = NO-GO**。
- O1/O2 首夜为晨报指标 + 启发式警告，不设阻断门（Opus 本人同意）——闭合。

**第四轮并入的执行语义五项**（GPT §四 / Grok U3 / Opus §二，三家同一张清单，防"伪共识"）：O5 选页机器化（§4.1 `first_night_selection`，preflight fail-closed）/ assertion 封闭词表（§4.1 + §6 `assertion-catalog.yaml`）/ `control_plane_lock` 覆盖传递依赖（§4.1，取代单脚本 scripts_digest）/ gate-result 事务写入与信封（§4.4）/ delivery 与验证状态机完全正交（§4.2/§4.3）。

---

## 2. 系统总览

```
【设计时 · 有人 · 高阶模型可参与】
  输入收集 → §16 落盘 + 五类 smoke → Phase 0（路由空壳 + manifest + dry cost 实测 + 高阶预审）
    → detached 签署 → preflight 全绿（含模型路由真身）→ lx-goal on
【执行时 · 无人 · DeepSeek 舰队】
  每页：PAGE_BOUNDARY_RESET（含环境指纹）→ 13 步循环（§7）
    → 产物：分支 + 证据 + verification-summary.yaml（finalize 重算）+ Draft PR（仅 DONE）
【回收时 · 有人】
  morning-report.sh → control-plane-scorecard.yaml（机器作答 8 问）
    → control_plane_green=true 后才看产量 → 裁决假设/冲突 → 签署下一夜
```

---

## 3. 模型舰队（最终）

| 角色 | 模型 | 形态 | 预算 |
|---|---|---|---|
| Implementer | DeepSeek V4 Pro | 主会话（代理 `claude-opus`→v4-pro） | ≤16 调用/页（dry cost 校准后定） |
| Fixer | DeepSeek V4 Flash | Subagent（`claude-haiku`→v4-flash） | ≤4 调用/页 |
| Visual 诊断 | Kimi K3 | 工具脚本直连 Moonshot API | **首夜 0**；其后 V2≤1 / V3≤2 |
| 裁决者 | **不存在** | J0 出口（§12） | — |
| 设计时顾问 | Opus/Grok/GPT | 仅 Phase 0（§17） | 按需 |

`MOONSHOT_API_KEY` 只从环境变量读，禁止写入任何入库文件。

---

## 4. 契约与状态

### 4.1 night-manifest.yaml v3.1（唯一契约 · immutable · detached 签署）

```yaml
policy:
  ui_stack: "patch_a"
  parallelism: 1
  merge_policy: "draft_pr_only"
  real_backend: false
  visual_diagnosis: "disabled"          # 首夜
  manifest_immutable: true              # 运行态回写 → FAILED_INVARIANT
  draft_pr_on: "DONE_only"

control_plane_lock:                     # S1 强化（GPT #3）：覆盖传递依赖，不只入口脚本
  algorithm: "sha256"
  entries: []                           # Phase 0 生成：七脚本 + helper/lib + hook 配置 + assertion-catalog.yaml + carros_base.py；每次门禁运行前自验，不符 → FAILED_INVARIANT

trust_boundary:                         # S1 正式收口（Grok U2 五条 + GPT 建议）：Owner 未签署 = NO-GO
  first_night_mode: "detective_controls"        # 侦探式，非预防式
  preventive_isolation_complete: false
  residual_risk_accepted_by: ""                 # Owner 签署（§18#9）
  scope: "single_page_single_night"
  auto_renew: false                             # 不得默认续到第二夜
  mandatory_before_v3_2_ga: ["read_only_policy_dir", "supervisor_only_gate_results", "separate_execution_identity"]

first_night_selection:                  # O5 机器化（三家一致）：preflight 逐项 fail-closed
  input_completeness: "complete"
  complexity: "V0_or_V1"
  prototype_accessible: true
  acceptance_contract_complete: true
  happy_path_testable: true

assertion_catalog_version: "1.0"        # O3 封闭词表（GPT #2）：未知 assertion ID → preflight/C4 FAIL

inputs:
  prototype:
    kind: "interactive"                 # interactive | static | mixed（R3 分型）
    path_or_url: ""
    login_required: false

pages:                                  # 首夜 len == 1（硬规则）
  - id: "FE-example"
    risk: "B1"
    ui_policy: { mode: "custom", token_source: "src/styles/tokens/", allow_global_override: false }
    required_states:                    # O3：逐态断言契约，没有断言的状态不算覆盖
      loading:         { assert: "skeleton_visible", not: "layout_shift_on_resolve" }
      success:         { assert: "list_or_detail_refreshed" }
      empty:           { assert: "empty_state_visible" }
      business_error:  { assert: "retry_affordance_present" }
      network_error:   { assert: "no_white_screen", and: "retry_affordance_present" }
      double_submit:   { assert: "trigger_disabled_during_inflight" }
      modal_close_rollback: { assert: "no_dirty_state_after_close" }
    overlay_contract:                   # R3：unknown 不得冻结 plan
      status: "declared"                # declared | confirmed_none | unknown
      items: []                         # §7.1 overlay-inventory
    files_allowed: ["src/pages/example/**"]
    paths:
      spec: "tests/e2e/example.spec.ts"
      artifacts: ".omc/task/{date}/FE-example/artifacts/"

environment_fingerprint:                # S4：Phase 0 记录，PAGE_BOUNDARY_RESET 校验
  node_version: ""
  pnpm_version: ""
  lockfile_sha256: ""
  playwright_version: ""
  browser_version: ""
  env_allowlist_digest: ""
  dev_server_pid: null
  dev_server_started_at: ""

page_boundary_reset: { required: true, on_reset_failure: "NIGHT_FUSE_WORKSPACE_POISONED" }
shared_gap_policy: { registry_path: ".omc/night/{date}/shared-gap-registry.yaml", max_local_workarounds_per_gap: 2, on_exceed: "BLOCKED_SCOPE" }
budgets: { per_page_calls: null, fix_rounds: null, page_wall_clock_min: null, night_wall_clock_min: 600, kimi_calls_total: 0 }
  # ↑ per_page/fix_rounds/wall_clock 由 Phase 0 dry cost 实测 P90 × 安全系数填入（O4），禁止拍脑袋
```

**签署（S2 detached，避免 digest 自引用）**：`night-manifest.signoff.yaml` 独立文件——

```yaml
manifest_sha256: ""        # 对 night-manifest.yaml 原始字节的 SHA-256（不做 YAML 规范化）
decision: "NO_GO"          # NO_GO | CONDITIONAL_GO | GO
signer: ""
signed_at: ""
```

preflight 在 `lx-goal on` 前重算文件字节哈希比对；manifest 签后任何字节变动 → 拒绝放行。这不是双契约：manifest 是唯一任务契约，signoff 只是签署证明。

### 4.2 两阶段交付（S3，拆除 finalize↔PR URL 时序循环）

| 文件 | 生成时机 | 内容 | 性质 |
|---|---|---|---|
| `verification-summary.yaml` | C8a finalize | final_status / completion / gates / code_sha / ac_* / 证据索引 | **immutable**，生成后禁改 |
| `delivery-receipt.yaml` | C8b delivery | delivery_status / draft_pr_url / delivered_at / evidence_commit_sha | 交付回执 |
| `acceptance_report.md` | 两者渲染 | 展示产物 | 渲染品 |

**PR URL 不进验证结论文件**；delivery 与验证状态机完全正交（GPT #5）：`delivery_status: NOT_ATTEMPTED | IN_PROGRESS | DRAFT_PR_CREATED | DRAFT_PR_FAILED`，GitHub 故障只产生 `DRAFT_PR_FAILED`，不改写 DONE/BLOCKED/FAILED、不污染 FINALIZED。字段唯一机器来源表沿用 v3.0（final_status←状态机终态、ac_*←evidence-check 聚合、branch/code_sha←git、blocked_code←合法阻塞事件、calls/wall_clock←执行日志），但**输入源从 token.json 改为 gate-results**（§4.4）。

### 4.3 状态机（v3.1）

```
INTAKE → RESEARCHED → CONTRACT_FROZEN → IMPLEMENTING
  → SCOPE_VERIFIED (C1) → STATIC_VERIFIED (C2) → ARCHITECTURE_VERIFIED (C3)
  → BEHAVIOR_VERIFIED (C4/C5) → VISUAL_VERIFIED (C6)
  → EVIDENCE_BOUND (C7) → FINALIZED (C8a)     ← 验证状态机终态

C8b 交付层（与验证状态机正交，GPT #5）：
  delivery_status: NOT_ATTEMPTED → IN_PROGRESS → DRAFT_PR_CREATED | DRAFT_PR_FAILED
  DRAFT_PR_FAILED 不改写 DONE、不进验证状态机

C6 FAIL → VISUAL_FIXING（受限写码态，R2）：
  1. 撤销当前 code_sha 证据资格，旧 artifacts 隔离
  2. 只允许治同一 fingerprint 的最小修复；跨指纹改动计新 fix round
  3. 修复后从 C1 全链重跑；旧 gate-results 标 SUPERSEDED（不删除）
  4. 超 fix_rounds → BLOCKED_BUDGET，不得带旧图宣称接近完成

失效传播（R2/GPT）：任何 src/ tests/ 构建配置/ 锁文件变更
  → 其后所有 gate 结果立即失效，必须重跑对应链
```

正交码表（R5 取 GPT 版）：

```yaml
execution_status: NOT_STARTED | RUNNING | CRASHED | TERMINATED   # 晨报派生/展示用
final_status: DONE | BLOCKED | FAILED | null                     # 终结后才非空
blocked_code: BLOCKED_INPUT | BLOCKED_SCOPE | BLOCKED_ENV | BLOCKED_BUDGET | BLOCKED_HUMAN | BLOCKED_VISUAL_P0 | null
failed_code: FAILED_INVARIANT | FAILED_TOOLCHAIN | FAILED_FIX_LOOP | FAILED_UNKNOWN | null
delivery_status: NOT_ATTEMPTED | IN_PROGRESS | DRAFT_PR_CREATED | DRAFT_PR_FAILED
completion: { qualified: bool, assumptions_present: bool }       # 七态断言缺任一 → qualified=false → 强制 BLOCKED
```

### 4.4 门禁权威链（R1，替代"token 是状态源"）

```
manifest            = 人类签署的 desired state（immutable）
gate-results/*.json = 门禁产生的 observed facts（唯一事实源）
token.json          = carros_base 据 facts 推导的进度缓存（恢复提示，不作结论输入）
verification-summary = finalize 据 facts 重算的结论
acceptance_report   = 渲染产物

final_status = reduce(manifest, gate-results, execution-events)
```

硬规则：状态迁移合法性 = (当前态， 门禁 exit code, 证据指针) 三元组，不许"只改 token 不附 gate-results"；模型对 token 的写入仅允许经 carros_base.py API；token 与 gate-results 冲突 → `FAILED_INVARIANT`；恢复时必须重验对应 gate result。

**gate-results 事务写入与信封（GPT #4）**：临时文件 → schema 校验 → fsync → 原子 rename；同一 gate 多次执行保留历史，仅合法最新结果参与 reducer；exit code 与结果文件冲突 → fail-closed。信封缺任一权威字段 → reducer fail-closed：

```yaml
gate_run_id: "uuid"
gate_id: "C4"
status: PASS | FAIL | ERROR | SUPERSEDED
manifest_sha256: "..."
code_sha: "..."
control_plane_digest: "..."
started_at: "..."
finished_at: "..."
process_exit_code: 0
evidence: []
```

### 4.5 信任边界（S1，首夜五层最小隔离 + 诚实残余风险）

```
1. PreToolUse hook deny：禁写 scripts/carroros-gates/**、**/gate-results/、
   night-manifest*.yaml、token.json（仅 carros_base API）、.claude/settings*.json
2. control_plane_lock（传递依赖哈希清单）入签署 manifest；每次门禁运行先自验，不符 → FAILED_INVARIANT
3. gate-results 每条带 script_hash + 时间戳；finalize 交叉校验全部条目
4. scripts/ 不在任何 files_allowed → 改动必现 git diff → C1 兜底
5. 早晨审计：治理路径 git diff 零改动 + scorecard.forged_summary_attempts == 0
```

**残余风险（诚实声明）**：模型若编辑 settings 禁用 hook 并等待会话重启，理论上可绕；夜级熔断 + 早晨 git 审计可发现痕迹。完整 supervisor 进程隔离 / gate-results 签名 = **v3.2 演进项**，不阻塞首夜。

---

## 5. 证据模型（v3.1 时序）

```
code freeze（含 tests/——freeze 后改 tests 与改 src 同罪，demote + 重验）
  → 记录 code_sha → 清 artifacts（E12）
  → C4/C5 → C6
  → C6 成功进入 VISUAL_VERIFIED → 此后写 src/ = FAILED_INVARIANT（hook + diff 双保险）
     （C6 FAIL 不进 VISUAL_VERIFIED，进 VISUAL_FIXING，不禁写——GPT 修订）
  → finalize 生成 verification-summary.yaml（immutable）
  →（仅 DONE）Draft PR → delivery-receipt.yaml
```

新鲜度校验：`git diff --quiet "$code_sha"..HEAD -- src/ tests/ package.json pnpm-lock.yaml vite.config.* playwright.config.*`。每条证据记录：code_sha、相对路径、存在性、非空、生成时间、对应 AC、playwright run 结果路径；截图文件名带 code_sha 前缀。

---

## 6. 门禁体系（C0–C8a/C8b + 七脚本 + 攻击集 smoke）

| 门 | 内容 | 执行者 |
|---|---|---|
| C0 输入 | Phase 0 完成，D2 清空或登记，overlay_contract.status ≠ unknown | 人类 |
| C1 范围 | diff+untracked ⊆ files_allowed+spec；deny 零触碰；治理路径零改动 | scope-check.sh（消费 carros_base 规范化 JSON） |
| C2 静态 | typecheck / `pnpm exec eslint . --max-warnings 0` / build | pnpm |
| C3 架构 | C7 启发式+allowlist + ui_policy（ESLint no-restricted-imports） | c7-check.sh |
| C4/C5 行为 | 七态**断言契约**（封闭词表）+ 浮层关闭语义矩阵 | playwright + assertion-catalog.yaml |
| C6 视觉 | 确定性子集（§10） | chrome-devtools |
| C7 证据 | 存在性+非空+code_sha 新鲜度+AC 绑定；生成 ac_* | evidence-check.sh |
| C8a 定稿 | 从 gate-results 重算，生成 verification-summary.yaml | finalize-page.sh |
| C8b 交付 | archive + Draft PR（仅 DONE）→ delivery-receipt.yaml | carros_base + gh |

**assertion-catalog.yaml（O3 封闭词表，GPT #2 / Opus 深水区）**：每个 assertion ID 映射 playwright helper + params schema + pass/fail 规则 + evidence type；manifest 引用未知 ID → preflight FAIL；spec 出现词表外断言 → C4 FAIL。禁止自由文本断言——否则"逐态断言"退化回"存在性枚举"，O3 白升级。

**五类 smoke（preflight 强制，篡改类含 R4 权威链攻击集）**：正向 / 反向 / 崩溃恢复 / fail-open（解析失败、空允许列表、git 失败、缺字段、0 文件称 PASS）/ **篡改攻击**——手写 machine-summary 为 DONE、手写 token 为 DELIVERED 但缺 C6 gate-result、引用旧 code_sha 截图、C6 工具 exit 非 0、弱化 tests 断言但截图仍旧、解析损坏 manifest、修改门禁脚本自身或其传递依赖 helper（control_plane_lock 必须报警）、exit 0 但结果文件缺失、结果 PASS 但 exit 非 0（冲突时 fail-closed）。

**preflight 新增两项**：模型路由真身校验（§2 铁律）；signoff 文件字节哈希比对（§4.1）。

---

## 7. 夜间单页循环（13 步）

| 步 | 动作 | 产物/门禁 |
|---|---|---|
| 0 | PAGE_BOUNDARY_RESET（§8，含环境指纹） | 不绿不进页 |
| 1 | research：原型测量（§7.1 R1/R2 按 prototype.kind 分型）+ 仓库模式扫描 + reuse-map.json | research.md + overlay-inventory |
| 2 | plan 冻结：files_allowed / AC 逐条 / 七态断言落 playwright / overlay_contract 确认 / rollback | plan.md（frozen） |
| 3–5 | 骨架→结构→交互实现，原子提交，全 mock | commits |
| 6 | C1 scope-check | SCOPE_VERIFIED |
| 7 | C2 typecheck/lint/build | STATIC_VERIFIED |
| 8 | C3 c7-check + ui_policy | ARCHITECTURE_VERIFIED |
| 9 | C4/C5 七态断言 + 浮层矩阵 | BEHAVIOR_VERIFIED |
| 10 | code freeze（含 tests/）→ 记 code_sha → 清 artifacts | code_sha |
| 11 | C6 视觉确定性子集，截图带 code_sha 前缀 | VISUAL_VERIFIED / VISUAL_FIXING |
| 12 | C7 evidence-check → C8a finalize 生成 verification-summary.yaml | EVIDENCE_BOUND → FINALIZED |
| 13 | C8b：archive → Draft PR（仅 DONE）→ delivery-receipt.yaml | DELIVERED |

### 7.1 浮层与滚动契约（v3.1 分型修订）

**R1 滚动完整性**：研究步必须对原型分段滚动捕获，fold 以下内容不进 research.md 就不许进 plan。

**R2 触发器扫描——按 prototype.kind 分型（Grok R3 修订）**：
- `interactive`：逐一触发可交互元素（点击每个按钮/链接、悬停每个导航项），产出 overlay-inventory。"可点未点"导致的漏浮层 = 研究失职，修复路由 Pro 重研，不许转 BLOCKED_INPUT 蒙混。
- `static` / `mixed`：**禁止伪装点击**。浮层只能来自：PRD 显式清单、设计稿标注、Phase 0 人类/高阶预审写入的 `overlay_contract.items`。静态输入下浮层信息不足 → `overlay_contract.status: unknown` → **BLOCKED_INPUT（缺输入），不是研究失职**。
- plan 冻结前提：`overlay_contract.status ∈ {declared, confirmed_none}`。

**R3 浮层关闭语义矩阵（C4/C5 必测，逐浮层落断言）**：

| 浮层类型 | 必测行为 |
|---|---|
| modal / drawer | 点击遮罩关闭（PRD 允许时）、Esc 关闭、打开时主页面 scroll-lock、关闭后焦点归还触发器、焦点陷阱（modal） |
| popover / menu（click） | 点击浮层外关闭、Esc 关闭、再点触发器关闭 |
| popover / menu（hover） | **延迟关闭 ≥200ms**，延迟窗口内光标进入浮层则取消关闭（防"菜单还没点到就消失"）；点击菜单项后关闭 |
| tooltip | hover 即显、离开即关、不截获焦点 |

延迟参数默认 200ms（manifest 可覆盖）；safe-triangle 属 V3 精修，首夜用延迟关闭（J0 最小风险路径）。

**视觉门配套**：C6 必含浮层开启态截图，查 z-index 遮挡/裁剪。

**页级熔断**：同指纹×2 无有效变化 / 超预算 / 越界 diff×2 / D2 输入缺口。
**夜级熔断**：dev server 预授权重启仍挂 / 连续 3 页同环境问题 / git 状态损坏 / 未授权触 deny / WORKSPACE_POISONED / 视觉工具失败×2 / **control_plane_lock 自验报警（信任边界被碰）**。

---

## 8. 页间隔离（v3.1 = git 基线 + 环境指纹）

```
PAGE_BOUNDARY_RESET:
1. 工作树相对 page_start_sha 干净；diff 仅含当前页 files_allowed
2. 环境指纹比对（S4）：node/pnpm/lockfile/playwright/browser 版本、env digest 漂移 → 修复或夜熔
3. 非 git 状态清理：browser context、storage state、mock server 内存态、任务级测试产物、端口占用
4. 失败页隔离：恢复 page_start_sha，或移出毒化文件并标 BLOCKED_ENV/FAILED
5. reset 未完成 → 禁止进下一页；reset 失败 → NIGHT_FUSE: WORKSPACE_POISONED 整晚停
```

## 9. shared 腐蚀熔断（不变）

registry 机器读写；同 gap_id 绕开 ≥2 → BLOCKED_SCOPE；晨报"公共面腐蚀候选"独立节按 gap_id 聚合。

## 10. 视觉门（不变 + 一条）

确定性子集：1440 布局不崩 / 关键区域齐全 / 无横向溢出 / 无 console error / 文本不截断到不可用 / token 色号间距可测量对齐 / 浮层开启态无遮挡无 z-index 裁剪。工具失败 → 最多 BLOCKED_ENV，绝不能 DONE；N/A 只给声明不适用的 AC；环境失败×2 → 夜熔。

## 11. 交付规则（v3.1）

| final_status | 交付 |
|---|---|
| DONE | Draft PR（五段模板：做了什么 / AC 过卡 / assumptions / 未动公共区 / **控制面摘要：code_sha、gates map、qualified、overlays covered**） |
| BLOCKED | 不建 PR；分支 + open-questions/assumptions 现场 |
| FAILED/CRASHED | 不建 PR；分支 + 现场包 + 恢复入口 |

`gh` 未 auth 或 GitHub 故障 → `delivery_status=NOT_ATTEMPTED/DRAFT_PR_FAILED`，**不影响 DONE 判定**（通道故障 ≠ 实现失败）。

## 12. 失败分类路由 + J0（v3.1）

失败路由不变（Compile/Lint→Flash；类型传导/状态流→Pro；交互根因不清→Pro+trace；ApiContractError→BLOCKED_INPUT；EnvironmentError→恢复流程；VisualError→Pro 1 轮→次夜起 K3 配额内；RequirementGap→阻塞）。

J0 出口：PRD/API 冲突 → BLOCKED_INPUT；架构歧义 → 最小风险六优先级 + assumptions.yaml + 早晨复核；宪法未覆盖 → 最小风险+记录；根因裁决 → 不做，error-dna；公共面变更 → BLOCKED_SCOPE；**静态原型浮层信息不足 → BLOCKED_INPUT（§7.1 R2）**；工作区中毒 → 夜级熔断（唯一不许"继续下页"的情形）。

## 13. 健壮性矩阵（v3.1）

上下文压缩/会话崩溃 → token.json 定位 + **重验 gate-results** 后从最后 VERIFIED 态续跑（R1：不得见 VERIFIED 即续跑）；MCP 断线 → 退避 3 次 → BLOCKED_ENV；DeepSeek 限流 → 指数退避，连续 3 页 → 夜熔；K3 故障 → 降级不阻塞；dev server 死 → 预授权重启一次；越界写 → hook 拦截 + C1 兜底；模型手写 summary/token/改门禁脚本或其 helper → 篡改攻击集 + control_plane_lock + finalize 重算三重拦截；提前完成 → lx-goal report → off。

## 14. 首夜定义（1 页试毒夜 · 硬规则）

- **pages = 1**，且选页 = **输入最全 + 复杂度最低的"简单真页"**（O5：让 happy path 有机会真走通一次；简单页跑不绿 → 问题一定在控制面/预算，定位干净。选难页 = 控制面和产量同时失败，什么都学不到）。manifest `first_night_selection` 五字段由 preflight 逐项 fail-closed 机判，不许只查 `len==1`
- 串行 / Patch A / V0–V1 优先 / 无 B3 / K3=0 / Draft PR only / 全 mock
- Phase 0 首次预留 3 小时 + **gate-cycle dry cost 实测**（O4）；三 Owner 具名
- 早晨顺序锁死：**control-plane-scorecard.yaml 机器作答 8 问，`control_plane_green=true` 后才准看页面还原度**。scorecard 不绿，页面再好看首夜也算失败

**control-plane-scorecard.yaml（R6，morning-report 生成，reducer 推导非手填）**：

```yaml
gates_can_fail_on_purpose: bool      # 五类 smoke 实跑证据
morning_report_missing_pages: 0
done_without_evidence_count: 0
scope_leak_count: 0
same_fingerprint_loop_count: 0
crash_recoveries_succeeded: "n/n"
workspace_poison_events: 0
forged_summary_attempts: 0
visual_tool_failure_marked_done: 0
intra_page_duplication_flags: n      # O1 指标（首夜仅报告）
token_reference_coverage: "0%"       # O2 指标（首夜仅报告）
control_plane_green: bool            # reducer 推导；晋升与"首夜成功"的唯一判据
```

## 15. 成熟度阶梯（晋升绑定 scorecard）

- **L1→L2**（连续 2 夜 `control_plane_green=true` 且）：越界=0、假完成=0、AC 有证据通过率≥90%、恢复成功率=100%、单页人工返工<30min → ≤5 页、V3≤1、K3≤2
- **L2→L3**（再连续 2 夜 + 七态断言通过率≥95%）→ 并行≤2（lx-race 恢复）
- **任何 L 永不开放**：自动合并 / 真实后端 / B3 / 夜间触 tokens·shared·router·auth / 夜间切 ui_policy.mode

## 16. 落盘清单（GA 全部工作）

**脚本 7 份**：scope-check.sh（JSON 消费 + 全仓库 untracked `-z` + 基线记录 + 治理路径零改动断言）/ c7-check.sh（0-1px 放行 + 属性值限定 + allowlist + ESLint no-restricted-imports 覆盖 antd 全家族含动态 import/require/re-export，`:global`/`!important` 只扫 diff 新增行）/ evidence-check.sh（存在性+非空+code_sha 新鲜度+SUPERSEDED 排除）/ preflight.sh（signoff 字节哈希 + control_plane_lock 自验 + first_night_selection 机判 + assertion 词表校验 + **模型路由真身** + 五类 smoke 强制）/ morning-report.sh（只读 verification-summary + delivery-receipt；pages[] 遍历；**生成 control-plane-scorecard.yaml** + O1/O2 指标格）/ finalize-page.sh（**从 gate-results 重算**，两阶段产出，token 冲突判 FAILED_INVARIANT）/ **abstraction-check.sh（新，O1：jscpd 式页内近似重复检测，首夜仅出晨报指标）**

**治理文件 6 份**：night-manifest.yaml v3.1 / night-manifest.signoff.yaml（detached）/ shared-gap-registry.yaml / phase0-checklist.md / open-questions.md / **assertion-catalog.yaml（O3 封闭词表：assertion ID → playwright helper → params schema → pass/fail 规则 → evidence type）**

**任务模板 2 份**：assumptions.yaml / acceptance_report.md（渲染模板）

**CarrorOS 侧 5 项**：carros_base.py 增 `manifest-json` + token 写入 API 化 + gate-results 目录管理（事务写入：临时文件→schema 校验→fsync→原子 rename）/ PreToolUse hook deny 规则组（§4.5）/ 目标 repo ESLint no-restricted-imports / **Phase 0 gate-cycle dry cost 流程**（O4：拿首夜页人工/半自动走完整门禁周期，实测调用数/墙钟/fix 轮分布，预算=P90×安全系数）/ **control_plane_lock 生成器（GPT #3：遍历七脚本 + 传递依赖 helper/lib + hook 配置 + assertion-catalog.yaml + carros_base.py，路径排序后逐文件 sha256 入 manifest）**

**验收（GA 门）**：五类 smoke 实跑绿（含 R4 攻击集）+ §17a 高阶审计 diff 无新 P0 + §18 闭合。

## 17. 设计时高阶模型使用点

- **17a 物件审计**：落盘+smoke 后审六脚本 diff 与 smoke 输出（防"修错"）
- **17b manifest + plan 预审**：AC、七态断言、overlay_contract、D2 冲突，输出仅为建议，人类签署才是 GO
- **17c 首夜选页建议**：按"输入最全 + 复杂度最低"推荐那 1 页（O5）

## 18. 不确定项清单（请用户裁决；附三家投票）

| # | 事项 | 三家投票 | 我的建议 |
|---|---|---|---|
| 1 | **antd 去留** | 一致 A | **A**（Patch A 自定义组件） |
| 2 | **首夜页数** | 一致 1 页 | **1 页** |
| 3 | **目标 repo + 首夜页面 + 输入** | 必须齐；Opus 加"复杂度最低" | 请提供：repo 路径、首夜页（**输入最全+最简单的真页**）、PRD/API/原型路径、prototype.kind（interactive/static/mixed）、需登录则备登录态 |
| 4 | **Draft PR 通道** | gh 已 auth 才允许 DONE→PR；否则 NOT_ATTEMPTED 仍可 DONE | 确认 `gh auth status` |
| 5 | **K3** | 一致首夜 0 | **首夜 0**；确认 `MOONSHOT_API_KEY` 在环境变量 |
| 6 | **三 Owner** | 可同人；早晨 Owner 必须答 scorecard | 默认都是你 |
| 7 | **预算** | **Opus 拦截：默认值不可直接用** | 先跑 dry cost 实测，预算=P90×安全系数；night 600min 可先用 |
| 8 | **排期** | Grok：禁止"今晚边落盘边首夜" | 今天落盘+smoke（约半天）→ 隔一个清醒窗口 → 明晚首夜 |
| 9 | **S1 残余风险签署**（第四轮新增，GO 的前置条件） | GPT：recorded dissent，需 Owner 显式接受；Grok：五条写死+签署否则 NO-GO；Opus：S1 优先于他全部原创补丁 | 你作为 Owner 在 manifest `trust_boundary.residual_risk_accepted_by` 签署：接受首夜**单页单夜**侦探式信任边界（可发现≠不可发生）、`auto_renew: false` 不自动续期、v3.2 GA 前完成预防式隔离三件套（只读策略目录 / supervisor 独占 gate-results / 独立执行身份）。**未签署 = NO-GO** |

---

一句话总结：

> **宪法管边界，manifest 管契约，gate-results 管事实，finalize 重算结论，token 只是缓存，DeepSeek 干活，playwright/chrome-devtools 出证据，七态断言管"好用"，scorecard 管"诚实"，高阶模型只在睡前说话，裁决全归早晨的人类——首夜 1 页简单真页，先证明系统不撒谎、也不在不撒谎的同时把活干烂，再谈产量。**
