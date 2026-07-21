# frontend-overnight — 夜间无人值守前端开发工作流

> 你提供：设计稿原型（必需）、PRD（可选）、API 文档（可滞后）。
> 系统交付：次日早晨的 Draft PR + 机器晨报 + 控制面记分卡。
> 规格：`UI/FINAL.md` v3.1（冻结）；本文是操作规程。
> **操作请直接走 `SOP.md`（可勾选的操作手册，几周后回来照做即可）**；本文讲"为什么"。

## 能力边界

| 做 | 不做（永不开放） |
|---|---|
| 静态 UI 还原（tokens 驱动，Patch A 自定义组件） | 自动合并 PR（只建 Draft） |
| 交互还原（含浮层关闭语义矩阵、滚动完整性） | 接真实后端（夜间全 mock） |
| 业务逻辑（api 层按契约；API 文档滞后时走推断契约+登记） | B3 高风险页、夜间改 tokens/shared/router/auth |
| 七态断言（loading/success/empty/双错误/双提交/modal回滚） | 夜间切换 ui_policy.mode |

## 输入分期到达（允许不同时拿到）

| 你手里有 | 本期能开发 | 业务逻辑处理 |
|---|---|---|
| 仅设计稿原型 | 静态 UI + 交互 | 按原型/PRD 推断契约，逐条登记 assumptions.yaml，`api_contract_status: inferred` |
| 原型 + PRD | 上述 + 更准的 AC/七态 | 同上 |
| 原型 + PRD + API 文档 | 全量 | 按真实契约，`api_contract_status: real` |
| API 文档后到 | 走 **intake reconcile**（见 intake.md §3）更新 api 层 | inferred → real |

**没有原型 = 不开发**（UI 还原硬输入，C0 直接 NO-GO）。

## 每次开发的完整流程（5 步）

```
① 放输入   → ② intake + Phase 0（白天，约半天） → ③ 你签署 → ④ 夜跑（无人） → ⑤ 晨收
```

### ① 放输入
把文件放到 `inputs/{产品名}/`：`prototype/`（图或 URL 清单）、`prd.md`（可选）、`api.md`（可后到）。

### ② intake + Phase 0（白天，你或整合者在场）
按 `intake.md` 判定输入成熟度 → 生成 manifest → Phase 0 按 `phase0-checklist.md` 执行：
目标 repo 骨架（首次）→ dry-cost 实测 → 预算入 manifest → `gen_control_plane_lock.py --write` → 高阶模型预审（可选，§17b）。

### ③ 你签署（不可省）
- manifest `trust_boundary.residual_risk_accepted_by` 签你的名字（S1 残余风险，FINAL §18#9）
- 生成 signoff：`sha256(night-manifest.yaml)` 填入 `night-manifest.signoff.yaml`，decision=GO
- **未签署 = NO-GO**

### ④ 夜跑（你离开）
```bash
python3 scripts/carroros-gates/preflight.py --manifest .omc/night/$(date +%F)/night-manifest.yaml \
  --night-dir .omc/night/$(date +%F) --target-repo <目标repo>
# preflight GO 后：
/lx-goal "执行 .omc/night/$(date +%F)/night-manifest.yaml 夜循环：严格按 .claude/workflows/frontend-overnight/night-loop.md 的 13 步；验收=C1–C7 机器门禁（无人类验收）；J0 出口；禁止写结论/手写 summary；禁止碰控制面" 12
```
夜间执行模型：DeepSeek V4 Pro（主）+ V4 Flash（修复 subagent）。K3 首夜 0 配额。

### ⑤ 晨收（你回来）
```bash
rm .omc/state/night-session.active   # 第一步：摘除夜会话标记（否则夜跑 hook 会拦晨报脚本）
python3 scripts/carroros-gates/morning_report.py --manifest .omc/night/<日期>/night-manifest.yaml --night-dir .omc/night/<日期>
```
**顺序锁死**：先看 `control-plane-scorecard.yaml`——`control_plane_green=true` 才准看页面还原度和 Draft PR。不绿 = 首夜失败（哪怕页面好看）。
scorecard 重点字段：`producer_mismatch_count` / `suspicious_gate_invocation_count`（信封伪造侦探，Grok §17a P0-3）、`smoke_attestation`（self=实现方自陈，independent=独立复跑）、`untrusted_contract_pages`（推断契约红旗，API 文档到后须对账）。

**晨审 checklist（Grok §17a 复审放行条件，逐项人肉过）：**
1. **repo 根 `git diff` 全量过一遍**（不只 files_allowed 内）——C1 看不到 target 子目录之外的 monorepo 改动（P1-3 记名残余），控制面零触碰靠这刀兜底
2. **测试/脚本内写控制面嗅探**：diff 里搜 `gate-results` / `.omc/night` / `verification-summar` / `token.json` 出现在 tests/、scripts/ 新增行 = 子进程伪造嫌疑（S1 残余的唯一实战形态）
3. scorecard 三零：`producer_mismatch_count==0`、`suspicious_gate_invocation_count==0`、`forged_summary_attempts==0`
4. 抽查 C4/C5 证据链：playwright 产物文件真实存在、截图/trace 非空、与 `ac-aggregates` 的 covered 列表一致

## 命令速查

| 场景 | 命令 |
|---|---|
| 生成控制面锁 | `python3 scripts/carroros-gates/gen_control_plane_lock.py --manifest M --write` |
| 起飞前检查 | `python3 scripts/carroros-gates/preflight.py --manifest M --night-dir D --target-repo R` |
| 手动跑单门禁 | `scope_check.py / c7_check.py / evidence_check.py / finalize_page.py`（同参数） |
| 晨报 | `morning_report.py --manifest M --night-dir D` |
| 挂载夜跑 hook | `python3 scripts/carroros-gates/install_night_hook.py`（幂等，已装过会跳过） |

## 当前状态

**Runtime: RC / 待首夜**——§17a 三家审计已闭环（Grok/Opus/GPT，无遗留技术项；证据 `UI/round5/`）。首夜前置只剩：Phase 0 完成（SOP §1+§2.1）+ 你签署（SOP §2.2）。§18/P2 supervisor 等是 **GA** blocker，不阻塞首夜。之后每夜重复 SOP §2（②中非首次项可省）。
