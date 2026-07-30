# Opus 视角 · DeepSeek V4 Pro 实施版评审

> **身份定位**：我从 **约束工程、防作弊、证据链完备性** 角度审视已落地代码，补足 Grok 的 Token/Goal 设计与 GPT 的工具闭环之间可能的**执行侧漏洞**。  
> **当前状态**：已收到部分实施文件；需补齐信息后给出**可执行的加固清单**，而非重写方案。

---

## 0. 已读文件快照与缺口

### 0.1 已读取（15 个文件 + 知识库片段）

| 类别 | 文件 | 关键信息 |
|---|---|---|
| **控制面** | `SOP.md` / `README.md` / `phase0-checklist.md` / `intake.md` | Phase0 流程、夜跑边界、能力声明 |
| **编排核心** | `orchestrator.py` / `domain.py` / `convergence.py` | 状态机、Job 类型、收敛检测 |
| **评分/Token** | `scorer.py` / `token_bootstrap.py` / `token_refine.py` | UIF 七维、Token 提取/精化 |
| **配置/路由** | `config.py` / `model_router.py` / `task_generator.py` | 预算、Kimi 硬顶、Job 生成 |
| **清单模板** | `goal-manifest.template.yaml` | 运行时契约 |
| **文档** | `night-loop.md` / `OPTIMIZATION-FACTSET.md`(KB) / `UI_README.md`(KB) | 13 步循环、4 个已知问题、原型还原铁律 |

### 0.2 **关键缺口**（需补齐才能给出完整加固清单）

| # | 缺什么 | 为何必须 | 优先级 |
|---|---|---|---|
| **M1** | **补丁契约 schema 与 validator 实现**（对应 Grok 4/5 §3-6） | 没有 `ui-patch/2` JSON schema + P0–P6 验证管线 → Worker 可能绕过约束 | **P0** |
| **M2** | **C1–C3 gate 脚本**（`scope_check` / `c7_check` / `abstraction_check`） | 知识库提到但未见代码；无此 → RAW_VALUE / NIGHT_IMMUTABLE 不可机判 | **P0** |
| **M3** | **Assertion catalog 实现** + `C-IX` 交互门禁 | UI_README 提到 17 个 helper；未见 `ix.scroll.end` / `ix.hover.menu.*` 如何关联 D7 评分 | **P0** |
| **M4** | **补丁接受决策函数**（`decision.py` 或在 orchestrator 内） | 对应 Grok 4/5 §6；拒绝码、Token 回归检测、cheat 信号聚合在哪？ | P1 |
| M5 | `token-index.json` 生成与 D6 命中率计算细节 | `scorer.py` 提到 D6 但未见索引文件格式 | P1 |
| M6 | Region mask 与金标截图对齐逻辑 | 知识库提「模块截图」；`scorer.py` 是否按区域 IoU？ | P2 |
| M7 | checkpoint 持久化与崩溃续跑入口 | `orchestrator.py` 是否含 `load_checkpoint()` 与 `persist()`？ | P2 |
| M8 | `morning_report` 格式与 ProposeToken 队列输出 | 晨收必须含 Token proposals（≤3 优先）；未见模板 | P2 |

**Opus 纪律**：**M1–M3 未齐 = 本评审输出「条件性通过 + 待补清单」**；全齐才输出「可上生产 + 加固 patch」。

---

## 1. 已读代码的**三大优点**（继承正确）

### 1.1 状态机与层级门禁已落地

**`domain.py` - `HierarchyPhase` 枚举 + `orchestrator.py` - `_select_next_job()`**

```python
# domain.py L45-52（示意）
class HierarchyPhase(str, Enum):
    L0_TOKEN = "L0_TOKEN"
    L1_SHELL = "L1_SHELL"
    L2_LAYOUT = "L2_LAYOUT"
    L3_REGION = "L3_REGION"
    L4_ELEMENT = "L4_ELEMENT"
    L5_INTERACTION = "L5_INTERACTION"
    L6_POLISH = "L6_POLISH"
```

✅ **符合 Grok §1 层级不可跳**；`orchestrator` 按 phase 门禁分发 Job。

### 1.2 Token 只读 + Propose 分流已体现

**`config.py` - `IMMUTABLE_NIGHT` + `token_refine.py` - `ProposeTokenJob`**

```python
# config.py L78（示意）
IMMUTABLE_NIGHT = ["tokens/source", "tokens/generated", "shared", "router", "auth"]
```

✅ 对齐 Grok §2「夜跑不改 Token 源」；`token_refine.py` 产出 proposals 而非直接写死。

### 1.3 七维评分框架存在

**`scorer.py` - `UIFScorer.score_page()` 返回 `UIFScore` 含 D1–D7**

✅ 结构正确；但需确认：

- D6 `token_align` 是否真用 `token-index.json` 命中率？  
- D7 `interaction_coverage` 是否关联 assertion catalog 通过率（**M3 待验证**）？

---

## 2. 已发现的**五个执行侧风险**（Opus 防作弊角度）

### 风险 A：Worker 输出无强制 schema，补丁可能散文化

**证据**：`task_generator.py` 生成 prompt，但未见 **JSON schema 强制** 与 **P0–P6 验证管线**。

**后果**：  
- Agent 可能返回「请把按钮改小」而非结构化 `ui-patch/2`  
- `changed_files` 无 `before`/`after` 精确匹配 → C1 `CONTEXT_MISS` 不可判  
- 无 `self_check.uses_only_existing_tokens` → D6 可被话术绕过

**Opus 要求（对应 Grok 4/5 §3）**：

```python
# 必须新增：scripts/ui_autopilot/worker/patch_validator.py
def validate_patch_schema(proposal: dict) -> ValidationResult:
    """
    P0: schema version / limits / hash 去重
    P1: files ∈ page edit-scope（调用 C1 scope_check）
    P2: 扫描 before/after 是否含裸 #hex / \d+px（调 C3 c7_check）
         检查 token_ops 是否全在 token-index
         检查 touches_antd_global / touches_tokens_source
    返回：PASS | 拒绝码（RAW_VALUE/SCOPE_FAIL/TOKEN_REQUIRED/...）
    """
```

**加固清单 A**（P0 级）：

- [ ] **A1** `worker/patch_schema.json` 定义 `ui-patch/2` 全字段（含 `limits` / `token_ops` / `self_check`）  
- [ ] **A2** `worker/patch_validator.py` 实现 P0–P2（**M1**）  
- [ ] **A3** `orchestrator.py` 在 apply 前调用 validator；失败 → 拒绝 + reason_code  
- [ ] **A4** prompt 强制输出 JSON（system: "只输出 ui-patch/2 JSON，禁止散文"）

---

### 风险 B：C1–C3 门禁未见代码，可能仅话术约束

**证据**：知识库提 `c7_check` / `abstraction_check` / `scope_check`，但本批文件未含；`orchestrator.py` 未见调用。

**后果**：  
- 夜跑可能改到 `tokens/source`（违反 `IMMUTABLE_NIGHT`）  
- 裸 `px` / `#hex` / `:global` 可能进 PR  
- 跨 page scope 改文件不被拦截

**Opus 要求（对应 Grok 4/5 §4、现网 FailClosed）**：

```bash
# 必须存在（或等价逻辑）：
scripts/carroros-gates/scope_check.py      # C1
scripts/carroros-gates/c7_check.py         # C3 裸值
scripts/carroros-gates/abstraction_check.py # C3 :global / antd 乱盖
```

每个返回 **exit 0 = PASS | 非 0 = FAIL + stderr reason**；`orchestrator` FailClosed 处理。

**加固清单 B**（P0 级，**M2**）：

- [ ] **B1** `scope_check.py` 读 `goal-manifest` 的 `page.edit_scope`，拒绝越界文件  
- [ ] **B2** `c7_check.py` 正则扫 diff：`#[0-9a-fA-F]{3,6}` / `\d+px`（白名单 `tokens/generated`）  
- [ ] **B3** `abstraction_check.py` 扫 `:global` / `!important` / 无 ConfigProvider 的 `.ant-*`  
- [ ] **B4** `orchestrator.py` apply 后按序调用 C1→C2(tsc/eslint)→C3；任一 FAIL → revert worktree  
- [ ] **B5** 拒绝码统一：`SCOPE_FAIL` / `RAW_VALUE` / `ABSTRACTION_FAIL`（进 `patch_decision.json`）

---

### 风险 C：交互维 D7 可能虚高（未见 assertion 强制执行）

**证据**：  
- `scorer.py` 有 `D7: interaction_coverage`  
- 知识库提「17 个 helper」「浮层矩阵」  
- **但本批未见** `assertion-catalog.yaml` / `C-IX` 门禁 / `ix.scroll.end` 等 ID 如何关联评分

**后果**：  
- 页面静态 98 分、交互 0 → 总分可能被算成 95+（违反 Grok §3「D7 不满封顶 0.94」）  
- hover 菜单、滚动到底未验证就 `finalize_page`

**Opus 要求（对应 Grok 3/5 §4-5、现网 catalog）**：

```yaml
# 必须存在：inputs/{产品}/assertion-catalog.yaml
assertions:
  - id: ix.scroll.end
    page: orders/list
    trigger: { type: scroll, target: "main", to: bottom }
    predicate:
      - type: dom, selector: "footer", visible: true
      - type: viewport, contains: "#last-card"
  - id: ix.hover.menu.user
    page: "*"  # 全局
    trigger: { type: hover, target: "[data-qa=user-avatar]", wait_ms: 200 }
    predicate:
      - type: dom, selector: ".user-menu-overlay", visible: true
      - type: style, selector: ".user-menu-overlay", zIndex: ">= var(--ds-z-dropdown)"
  - id: ix.overlay.dismiss.user-menu
    depends_on: ix.hover.menu.user
    trigger: { type: key, key: Escape }
    predicate:
      - type: dom, selector: ".user-menu-overlay", visible: false
```

```python
# 必须新增：scripts/ui_autopilot/scoring/interaction_runner.py
def run_assertions(page_id: str, catalog: dict) -> dict[str, bool]:
    """
    C-IX 门禁（或并入 C4/C5）
    遍历 catalog 中属于 page_id 的 assertion
    Playwright 执行 trigger → 验证 predicate → 截图证据
    返回：{ assertion_id: pass/fail }
    """
```

**加固清单 C**（P0 级，**M3**）：

- [ ] **C1** `assertion-catalog.yaml` 从 `UI_README` 人工抽取或 Phase0 辅助生成（至少含 scroll/hover/click/dismiss/sidebar）  
- [ ] **C2** `interaction_runner.py` 实现；输出 `assertions/{id}.json`（状态 + 截图路径）  
- [ ] **C3** `scorer.py` 的 `D7` 读 assertions 通过率：`passed / declared`  
- [ ] **C4** **封顶规则**：`if D7 < 1.0: uif_total = min(uif_total, 0.94)`（代码强制，不靠话术）  
- [ ] **C5** `orchestrator.finalize_page()` 前必须 `assert D7 == 1.0 or page.allow_ix_debt`

---

### 风险 D：补丁接受决策可能仅靠 UIF 涨分，缺防作弊

**证据**：  
- `convergence.py` 有 `detect_stagnation` / `detect_thrash`  
- **但未见**「高视觉涨 + 低 Token 命中 = 拒绝」的 cheat 信号聚合

**后果**：  
- Worker 改 `gap: 8px → 7px` 无 token、只为 SSIM +0.01 → 可能被 accept  
- 重复 patch hash 可能只检测「完全相同」，漏掉「改一个数字」的震荡

**Opus 要求（对应 Grok 4/5 §6-7、现网 cheat 检测）**：

```python
# 必须增强：orchestrator.py 或新建 decision.py
def accept_patch_decision(
    old_score: UIFScore,
    new_score: UIFScore,
    proposal: dict,
    validation: ValidationResult,
    history: list
) -> Decision:
    """
    H1/H2 硬门 → 直接拒绝
    cheat_signals 检测：
      - Δ(D1+D2) > 0.03 且 Δ(D6) < -0.01 → CHEAT_HARDCODE
      - patch hash 在近 5 次内 → EDIT_REPEAT
      - 单行只改一个魔法数字（启发式）→ CHEAT_HARDCODE
    accept 条件：
      - validation.pass
      - Δuif >= min_delta 或关键 hole 关闭
      - D6_new >= D6_old - ε
      - D6_new >= phase_threshold
      - cheat_score < ε
    """
```

**加固清单 D**（P1 级，**M4**）：

- [ ] **D1** `decision.py` 集成 cheat 四信号（hardcode / repeat / magic / scope-drift）  
- [ ] **D2** `orchestrator._apply_task()` 调用 decision；reject → `reason_code` 回灌 evidence  
- [ ] **D3** `patch_decision.json` 含 `cheat_signals` 字段（晨报可聚合）  
- [ ] **D4** 页级 `cheat_score` 累加；超阈 → 只允许 InteractionRepair / ProposeToken

---

### 风险 E：内环可能仍「单次修就走」，未真 loop

**证据**：  
- `orchestrator.py` 有 `run_goal()` 外环  
- **但 `_execute_single_page()` 内部是否 while 不确定**（需看完整逻辑）

**知识库已知问题①**：「步 11 C6 只最小修、无自迭代」

**后果**：  
- 页 UIF 0.92 → 改一次 → 0.93 仍 < 0.99 → 就 finalize（违反 Goal §1 内环 while）

**Opus 要求（对应 Grok 5/5 §1）**：

```python
# orchestrator.py 伪码必须形如：
def _execute_single_page(page: PageTarget):
    while wall_ok and page_budget_ok and not page.goal_met:
        board = scorer.score_page(page)
        if board.uif_total >= 0.99 and board.D7 == 1.0 and board.proto_ok:
            break  # goal_met
        job = task_gen.next(board, phase)
        if job is None: break  # 真无可做
        decision = self._apply_task(job)
        if decision.accept: commit; checkpoint()
        elif decision.thrash: redirect_counter += 1
        if redirect_counter >= 3: skip_risk; break direction  # 换 region/job
    # 出循环仅当：goal_met | budget_exhausted | skip_risk
```

**加固清单 E**（P1 级）：

- [ ] **E1** `orchestrator._execute_single_page()` 确认含 `while not goal_met`  
- [ ] **E2** 单页软顶：`min(90min, remaining / pages_left * 1.3)`；超时 skip-risk  
- [ ] **E3** `goal_met` 条件：`uif >= 0.99 ∧ D7 == 1.0 ∧ proto.* 策略满足`（三联且）

---

## 3. Token 系统完备性（已有 bootstrap，需确认三端同源）

**已读**：`token_bootstrap.py` / `token_refine.py` —— 提取 + 聚类 + ProposeToken

**Opus 必须确认（对应 Grok 2/5）**：

| 检查点 | 期望 | 如何验证 |
|---|---|---|
| **T1** | `tokens/source/*.yaml` 冻结 hash 写入 manifest | `goal-manifest` 是否含 `token_set_hash`？ |
| **T2** | codegen: source → `generated/tokens.css` + `tailwind.theme.ts` + `antd.theme.ts` | 是否有 `scripts/.../codegen_tokens.py`？ |
| **T3** | 业务组件只用 `var(--ds-*)` / tw token 类 / AntD ConfigProvider | C3 `c7_check` 是否扫裸值（**B2**）？ |
| **T4** | D6 token_align 命中率 = 声明落在 `token-index.json` | `scorer.py` 是否读该索引（**M5**）？ |
| **T5** | 夜跑 ProposeToken 只写 `proposals/*.yaml`，不改 source | config `IMMUTABLE_NIGHT` 已含；C1 是否拦截（**B1**）？ |

**补充清单（若缺）**：

- [ ] **T1** `goal-manifest.template.yaml` 增 `token_set_hash: ""` 字段  
- [ ] **T2** `scripts/.../codegen_tokens.py`（或确认已有等价）  
- [ ] **T3** 走 **B2 c7_check**  
- [ ] **T4** `token-index.json` 格式定义 + `scorer.py` 读取逻辑（**M5**）  
- [ ] **T5** C1 scope 拦截（**B1**）

---

## 4. 预算与 Kimi 硬顶（已配置，需确认熔断）

**已读**：`config.py` - `KIMI_VISION_CAP_PER_RUN = 60` / `model_router.py` 有 escalate 逻辑

✅ **Grok 5/5 §2 对齐**

**Opus 必须确认**：

- [ ] **P1** `model_router` 超 cap 后是否**降级为 DOM/几何分**（而非瞎标 0.99）？  
- [ ] **P2** 每次 escalate 是否记 `why_escalated` 进 `model_usage.json`（晨报可审计）？  
- [ ] **P3** 时墙到 → `orchestrator` 有序退出、persist checkpoint（而非 kill -9）？

---

## 5. Checkpoint 与崩溃续跑（需确认实现，**M7**）

**知识库提及**：「checkpoint 持续落盘」「崩溃续跑」

**Opus 必查（对应 Grok 5/5 §3）**：

```python
# orchestrator.py 必须存在（或等价）：
def load_checkpoint(run_id: str) -> RunState | None:
    """读 artifacts/goal/{run_id}/checkpoint.json"""

def persist_checkpoint(state: RunState):
    """写 page 指针、region 队列、redirect 计数、budget_spent、git_sha_last_accept"""
```

**加固清单（若缺，**M7**）**：

- [ ] **CP1** `checkpoint.json` schema 定义  
- [ ] **CP2** `orchestrator.run_goal()` 首先尝试 `load_checkpoint()`  
- [ ] **CP3** 每次 accept 后 `persist_checkpoint()`  
- [ ] **CP4** 崩溃后人工可复跑：`python orchestrator.py --resume {run_id}`

---

## 6. 晨收格式（需确认 ProposeToken 最小决策包，**M8**）

**知识库**：「晨收最小决策」「≤3 个 Token 命名」

**Opus 必须**：

```yaml
# artifacts/goal/{run_id}/morning_report.yaml 必须含：
pages:
  - id: orders/list
    uif_total: 0.943
    capped_by: interaction_coverage  # 0.94 封顶原因
    d7_missing: [ix.scroll.end, ix.hover.menu.user]
propose_tokens:
  - value: "#E8EDF5"
    nearest: color.gray.100 (ΔE=3.2)
    usage_count: 8
    proposal: 升格为 color.bg.elevated-secondary 或合并到最近阶？
  # 最多 3 个优先
redirect_blocks:
  - page: orders/detail
    direction: region.header
    reason: EDIT_REPEAT × 3
    ttl_expires: 2026-07-29T08:00
model_usage:
  flash: 1847
  kimi_vision: 38 / 60
  escalations: [{ why: "遮挡争议 modal vs dropdown", at: "02:34" }]
budget:
  wall_clock: 6.2h / 8h
  cost_usd: ~estimate
```

**加固清单（**M8**）**：

- [ ] **MR1** `morning_report.yaml` 模板定义  
- [ ] **MR2** `orchestrator.finalize_run()` 输出该文件  
- [ ] **MR3** ProposeToken 队列按 `usage_count` 降序、只取 Top-3

---

## 7. Opus 总评与执行路径

### 7.1 **架构继承度 = 85%**（优秀）

| 项 | 状态 |
|---|---|
| Goal 状态机 + 层级门禁 | ✅ 已落地 |
| Token 只读 + Propose 分流 | ✅ 已落地 |
| 七维评分框架 | ✅ 已落地 |
| 模型路由 + Kimi 硬顶 | ✅ 已配置 |
| 13 步夜循环语义 | ✅ 文档清晰 |

### 7.2 **执行侧完备度 = 60%**（待加固 M1–M8）

| 缺口 | 风险等级 | 对应清单 |
|---|---|---|
| 补丁契约 schema + P0–P6 验证 | 🔴 **P0** | **A1–A4**（M1） |
| C1–C3 gate 脚本缺失 | 🔴 **P0** | **B1–B5**（M2） |
| Assertion catalog + C-IX 交互门禁 | 🔴 **P0** | **C1–C5**（M3） |
| 补丁接受决策 + cheat 聚合 | 🟡 P1 | **D1–D4**（M4） |
| 内环 while 确认 | 🟡 P1 | **E1–E3** |
| token-index 与 D6 细节 | 🟡 P1 | **M5** / T4 |
| Checkpoint 实现确认 | 🟡 P1 | **CP1–CP4**（M7） |
| 晨收格式 | 🟢 P2 | **MR1–MR3**（M8） |

### 7.3 **条件性通过与下一步**

**Opus 判决**：

✅ **方案侧**（Grok 1–5 册设计）已被 DeepSeek V4 Pro 正确继承 85%。  
⚠️ **执行侧**（Worker 笼子 / 门禁 FailClosed / 交互法律化）需补齐 **M1–M3（P0 级）** 才能上生产。

**推荐路径**：

```text
阶段 1（本周，P0 加固）：
  → 补齐 M1 补丁 validator（A1–A4）
  → 补齐 M2 gate 脚本（B1–B5）
  → 补齐 M3 assertion catalog + C-IX（C1–C5）
  → dry-run Volume-0（单页 6h 限时）

阶段 2（下周，P1 完善）：
  → 补齐 M4 decision + cheat（D1–D4）
  → 确认内环 while（E1–E3）
  → 补齐 M5/M7/M8

阶段 3（就绪）：
  → Phase0 人工签署 GO
  → 首次真 6h Goal
```

---

## 8. Opus 可立即输出的加固 Patch（若你确认缺 M1–M3）

若你回复「**M1–M3 确实缺失，请直接给代码**」，我将输出：

1. `worker/patch_schema.json`（ui-patch/2 完整 schema）  
2. `worker/patch_validator.py`（P0–P2 验证，调 C1/C3）  
3. `carroros-gates/scope_check.py`（C1）  
4. `carroros-gates/c7_check.py`（C3 裸值）  
5. `carroros-gates/abstraction_check.py`（C3 :global/antd）  
6. `assertion-catalog.yaml` 模板（含 scroll/hover/dismiss）  
7. `scoring/interaction_runner.py`（C-IX）  
8. `scorer.py` 增强片段（D7 封顶规则）  
9. `orchestrator.py` 焊接点（validator + gates + decision）

**当前不输出原因**：等你确认**哪些真缺、哪些只是未给我文件**，避免重复造轮子。

---

## 9. 需要你回复的信息（优先级排序）

| # | 问题 | 用于 |
|---|---|---|
| **Q1** | **M1–M3 是否真缺失**？若只是未上传文件，请补发 | 决定是否立即输出 Patch |
| **Q2** | `orchestrator._execute_single_page()` 是否含 `while not goal_met`（可粘关键 10 行）？ | 风险 E 确认 |
| **Q3** | `scorer.py` 的 `D7` 如何计算？是否读 assertion 通过率？ | 风险 C 确认 |
| **Q4** | `token-index.json` 格式是什么？D6 如何命中率？ | Token T4 / M5 |
| Q5 | Region mask 是否按模块截图 bbox 评分？还是整页 SSIM？ | M6 |
| Q6 | Checkpoint 逻辑在哪个文件？ | M7 |
| Q7 | 晨收输出路径与字段？ | M8 |

**回复方式建议**：

```yaml
Q1_M1_patch_validator: 缺失