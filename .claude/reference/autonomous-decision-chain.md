# Autonomous Decision Chain

> **This file is injected into AI context whenever goal/ghost mode is active.**
> Every decision during autonomous execution follows this chain. No exceptions.
>
> **Phase 0** = the one-time human clarification window when a ghost/goal mode command is first issued. Phase 0 closes once the human confirms and autonomous execution begins. After Phase 0, no further questions are permitted.
>
> **If autonomous mode expires mid-task**: the chain is no longer authoritative. Revert to standard interaction mode. Notify the human if work was interrupted.

---

## 决策链：逐层升级（4 层）

AI 不做"能自己决定 vs 要问人"的二分判断。而是逐层升级——大部分决策在前两层就被消化，只有极少穿透到人。

```
Layer 1. AI 自行判断
   → 项目惯例（kernel.md / claude-next.md / 现有代码模式）能覆盖？
   → YES: 执行，标注 [AI: 惯例]
   → NO:  进入 Layer 2

Layer 2. 静态分析门禁
   → hook 规则匹配：这操作安全吗？在范围内吗？铁律允许吗？
   → 安全 + 范围内 → 放行，执行
   → 不安全 / 越界 / 违反铁律 → 进入 Layer 3

Layer 3. 运行时分析
   → 真跑一下：烟雾测试 / 编译 / Oracle 审核 / Meta-Oracle (G1-G4)
   → 通过 → 放行
   → 不通过 → 进入 Layer 4

Layer 4. 需人裁决 ← 仅以下四类穿透到此
   a. 权限（sudo / rm -rf / 生产环境写入）
   b. 风险级别（不可逆操作、数据删除）
   c. 方案路线（跨架构选型、新依赖引入）
   d. 资源分配（大文件下载、费用产生）
```

### 自主模式：Layer 4 截断为「记录↷跳过」

> **自主模式（lx-goal / lx-ghost）下，穿透到 Layer 4 的操作一律「记录↷跳过」，不问人。**
> 事后在退出报告中汇总，由人统一审阅裁决。

| 正常模式 | 自主模式 |
|---------|---------|
| Layer 4 → 问人 | Layer 4 → `skip-risk` / `hard-boundary-hit` / `blocked-human` → 跳过继续 |
| 人实时参与决策 | 人只看退出报告，批量裁决 |

---

## Standard Mode: The Chain (always in order)

```
1. AI judgment (conventions / kernel.md / claude-next.md)
   → Execute, annotate rationale

2. Static analysis (hooks: pretool-edit-scope / permission-gate / privacy-gate / context-guard)
   → PASS → continue
   → BLOCK → escalate to Layer 3

3. Runtime analysis (Oracle / Meta-Oracle G1-G4 / smoke test / compile)
   → PASS → continue
   → FAIL → escalate to Layer 4 (human)

4. Human decision — only these 4 categories:
   a. Permission   (sudo / rm -rf / production write)
   b. Risk level   (irreversible op / data deletion)
   c. Approach     (cross-architecture / new dependency)
   d. Resource     (large download / cost incurring)
```

## Autonomous Mode: Layer 4 → Record & Skip

```
1. AI judgment → Execute
2. Static analysis → PASS or record rationale
3. Runtime analysis → Oracle/Meta-Oracle still run
4. Human-required? → Record to exit report (skip-risk / hard-boundary-hit / blocked-human)
   → Continue to next task
```

---

## Situation Matrix

| You encounter... | Action |
|-----------------|--------|
| A decision conventions already cover | **Execute**. Annotate `[AI: 惯例]`. Do NOT ask. |
| An iron rule violation | **Follow the rule**. Block/refuse as required. |
| A dangerous operation (rm/git push/etc.) | **Hard boundary**: skip, record, report at end. NEVER execute. |
| Uncertainty about code behavior | **Read the file**. Do NOT guess. Do NOT ask the user. |
| A fix that failed 3 times | **BLOCKED**: record hypothesis, skip, continue other tasks. |
| An ambiguous requirement | **AI judgment**. Use existing conventions. Record rationale. |
| A decision affecting ≥2 subsystems | **Oracle agent**. Spawn Agent(critic) for independent review. |
| Oracle ACCEPT with score ≥8.5, OR any CRITICAL finding, OR G1-G4 | **Meta-Oracle mandatory**. Use runtime trace, not static-only. DG-56. |
| Something outside task scope | **Record as side finding**. Do NOT fix. Do NOT expand scope. |
| Need to commit/push | **Hard boundary**: list changed files, let human decide at end. |
| Non-dangerous actionable items within scope | **Execute immediately**. DO NOT ask "要不要/需要我/是否应该". |
| Non-trivial task completed / bug fix applied | **Spawn Oracle critic for independent re-review**. DG-18, DG-23, DG-33. |
| Sub-agent / child agent returned data | **Verify against source files before writing**. DG-44. |
| Oracle findings (CRITICAL/MAJOR/REVISE) | **Evaluate against design intent first**. Separate real bugs from design disagreements. DG-21. |
| Security mechanism or safety-critical change | **Oracle + Meta-Oracle DUAL sign-off**. DG-32. |
| Ghost vs Goal mode selection | **AI self-evaluates direction type**. DG-55, GL-01. |
| Writing persuasive / marketing / non-technical content | **Apply stricter verification**. All numeric claims traceable. DG-43. |
| Autonomous mode nearing completion / phase end | **Generate exit report immediately**. DG-58. |
| Oracle REVISE/REJECT with clear, fixable issues | **Fix immediately, re-submit to Oracle**. DG-91. |
| ROI data vs philosophy/iron-rule | **Philosophy > ROI**. DG-94. |
| Governance file deletion or rename | **grep -r first, clean ALL hits**. DG-81. |
| A genuinely novel situation | **Try AI judgment first**. If blocked, record for human report. |

---

## Forbidden in Autonomous Mode

- ❌ AskUserQuestion (except Phase 0 clarification window)
- ❌ "需要我...吗？" / "要我...吗？" / "是否应该..." — just do it
- ❌ Waiting for user confirmation before non-dangerous actions
- ❌ Stopping execution to report progress (report only at end)
- ❌ Asking for preferences between valid options — pick the best one
- ❌ Manually creating `autonomous.active` or mode signal files — always use `lx-goal.sh on` or `lx-ghost.sh on`. Manual touch bypasses half the activation chain. DG-46.
- ❌ Skipping the 4-layer chain and jumping directly to Layer 4 — use Layer 1→2→3 first

---

## What Goes in the Exit Report

### ⚠️ Needs Human Decision — Aggregated Summary (REQUIRED)

> **Every exit report MUST include this aggregated section** as the first "needs attention" block.

Format:
```
## ⚠️ 需人为决策汇总

| # | 类型 | 层级 | 描述 | AI 推荐 | 依据 |
|---|------|------|------|---------|------|
| 1 | 硬边界 | L4a 权限 | ... | 建议人类执行: ... | 触碰哪条硬边界 |
| 2 | 阻断 | L3 运行时 | ... | 已尝试方案: A/B/C | 为何无法继续 |
| 3 | 跳过风险 | L4b 风险 | ... | 推荐方案 + 理由 | 决策链依据 |
| 4 | 推迟决策 | L4c 方案 | ... | 推荐方案 + 理由 | 决策链依据 |
| 5 | 资源 | L4d 资源 | ... | 推荐方案 + 理由 | 决策链依据 |
```

### Categories to aggregate:
- **Hard boundary items** (L4a 权限) — operations AI cannot execute (rm, git push, commit, credentials)
- **Skip-risk items** (L4b 风险) — irreversible ops skipped, with rationale
- **BLOCKED items** (L3 运行时) — core path blocked, 3 hypotheses tried and failed
- **Postponed decisions** (L4c 方案路线) — cross-architecture / new dependency choices
- **Resource items** (L4d 资源) — large downloads / cost-incurring operations skipped
- **Uncertain judgments** — low-confidence AI decisions flagged for human review

### Per-item format:
- **What was blocked/postponed** — specific operation or decision
- **Which Layer** — L3 (runtime) or L4a/b/c/d (permission/risk/approach/resource)
- **Why** — which condition triggered the postponement
- **AI recommendation** — what the AI would do if authorized
- **Decision basis** — which step in the chain informed the recommendation

---

## Standard Exit Report Sections

- Skipped hard-boundary items (for human to execute) — L4a
- Skip-risk items (with rationale) — L4b
- Postponed approach decisions (with recommendation) — L4c
- Postponed resource decisions (with recommendation) — L4d
- BLOCKED items (with 3 hypotheses tried) — L3
- Side findings (out of scope, not acted on)
- Oracle/Meta-Oracle verdicts (with trace)
