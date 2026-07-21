# SOP — frontend-overnight 操作规程（操作者读本）

> 读者：几周后回来的你。不需要记得任何细节，按本文勾选执行即可。
> 深度文档：能力边界/输入分期 → `README.md`；白天执行细节 → `phase0-checklist.md`；
> 输入成熟度判定 → `intake.md`；夜模型读本（你不用读，夜模型读）→ `night-loop.md`。
> 规格冻结于 `UI/FINAL.md` v3.1；三家审计闭环证据在 `UI/round5/`。

## 0. 心智模型（30 秒版）

```
你只有 3 个动作点：放输入 → 签署 → 晨审。其余全是机器跑。
白天备料（轻）→ 下班前点火（3 个动作）→ 夜里 DeepSeek 在白名单笼子里干活 → 早上看记分卡收货。
骨架（路由/tokens/断言 helper/mock 层）只搭一次；之后每天白天约半小时。
```

## 1. 首次启用（一次性，整个产品生命周期只做一遍）

- [ ] **输入落位**：`inputs/{产品名}/prototype/`（原型图或 URL 清单，**必需**）、`prd.md`（可选）、`api.md`（可后到）
- [ ] **目标 repo 位置**：选 `apps/{产品名}/`（monorepo 子目录；C1 越界检测/门禁执行/PR 三道边界都锚在这里）
- [ ] **A1 骨架**（按 `phase0-checklist.md` §A1 逐项）：Vite8+React19+TS6 strict、tokens、`src/app/router/` **全量预注册路由+stub 页**、mock 层、ESLint 禁 antd、`tests/e2e/helpers/assertions.ts` 按 catalog 实现全部 17 个 helper、playwright.config
- [ ] **A2 夜跑 hook**：`python3 scripts/carroros-gates/install_night_hook.py`（幂等）
- [ ] **A3 模型路由探针**：对 `http://127.0.0.1:9998` 用 opus/haiku 别名各发最小请求，验真身=v4-pro/v4-flash → `model-routing-proof.yaml`
- [ ] **A4 独立 smoke**：rsync 到 /tmp 干净目录 → `SMOKE_RUNNER=independent python3 scripts/carroros-gates/smoke/run_all.py --manifest <模板> --night-dir <临时> --target-repo <真仓> --out $NIGHT_DIR/smoke-results-independent.yaml` 全绿
  - ⚠️ **改完任何控制面脚本（hooks/scripts/carroros-gates）后必须重跑本步**，否则 preflight 9b 因 digest 过期硬拦

## 2. 每个开发周期 SOP（拿到新需求/PRD/UI 后）

### 2.1 白天备料（约半小时；首夜加 dry-cost 约半天）

- [ ] **选页**：规则 = **输入最全 + 复杂度最低**（顺序不能反）。
  - ❌ 不要默认选首页——首页通常是聚合页（多 API/多浮层），首夜避雷
  - ✅ 好候选：登录/设置/单列表页；首夜强制 `pages==1`（preflight 机判），跑通后每夜可排多页
- [ ] **B1 intake**：按 `intake.md` 填成熟度 + `api_contract_status`（API 文档没到 = inferred，推断契约登记 assumptions.yaml，晨报挂红旗，到后 reconcile 对账——**不阻塞开发**）
- [ ] **B2 feature 目录**：`prd/{app}/feat-{PAGE_ID}/prd.md` 头部写"夜间模式：验收委托机器门禁"
- [ ] **B3 dry-cost**（**仅首夜**）：拿本夜页手动走一遍完整门禁周期，实测调用数/墙钟/fix 轮 → `budgets = P90 × 1.5` 填 manifest（禁止拍脑袋）
- [ ] **B4 环境指纹**：node/pnpm/lockfile sha256/playwright 版本填 manifest
- [ ] **B5 控制面锁**：`python3 scripts/carroros-gates/gen_control_plane_lock.py --manifest .omc/night/$(date +%F)/night-manifest.yaml --write`

### 2.2 下班前点火（3 个动作，缺一个都点不着）

- [ ] **① 签署**（不可省）：
  - manifest 签 `trust_boundary.residual_risk_accepted_by: "<你的名字>"`（S1 六条残余：同 UID 无物理隔离 / hook 依赖宿主 exit 2 语义 / timeout·kill / regex≠完整 shell / 白名单语义误用 / supervisor 未上线）
  - `shasum -a 256 .omc/night/$(date +%F)/night-manifest.yaml` → 填 `night-manifest.signoff.yaml`：`manifest_sha256` + `decision: GO` + `signer` + `signed_at`
- [ ] **② preflight 全绿**：
  ```bash
  python3 scripts/carroros-gates/preflight.py \
    --manifest .omc/night/$(date +%F)/night-manifest.yaml \
    --night-dir .omc/night/$(date +%F) \
    --target-repo apps/{产品名}
  ```
  任何红项 → 修完重跑，**不许跳项**。GO 后它会自动创建夜会话标记（别手动 touch）。
- [ ] **③ 启动**（在 DeepSeek 代理会话里，即 `ANTHROPIC_BASE_URL=http://127.0.0.1:9998` 的会话）：
  ```
  /lx-goal "执行 .omc/night/<日期>/night-manifest.yaml 夜循环：严格按 .claude/workflows/frontend-overnight/night-loop.md 的 13 步；验收=C1–C7 机器门禁（无人类验收）；J0 出口；禁止写结论/手写 summary；禁止碰控制面" 12
  ```
  然后你回家。夜模型被 hook 拦会记 `BLOCKED_CONTROL_PLANE` 停手，不会绕过。

### 2.3 早上晨收（10 分钟，顺序锁死）

- [ ] **① 摘除标记（第一步必做，否则 hook 拦晨报脚本）**：`rm .omc/state/night-session.active`
- [ ] **② 生成晨报**：
  ```bash
  python3 scripts/carroros-gates/morning_report.py \
    --manifest .omc/night/<日期>/night-manifest.yaml --night-dir .omc/night/<日期>
  ```
- [ ] **③ 先看记分卡**：`control-plane-scorecard.yaml` 的 `control_plane_green=true` **才准看页面和 Draft PR**。不绿 = 当夜失败，哪怕页面好看
- [ ] **④ 晨审 4 项（人肉，是信任闭环的最后一环，不可省）**：
  1. repo 根 `git diff` 全量过一遍（不只 files_allowed——C1 看不到 target 子目录外的 monorepo 改动）
  2. diff 里搜 `gate-results` / `.omc/night` / `verification-summar` / `token.json` 出现在 tests/scripts 新增行 = 伪造嫌疑
  3. scorecard 三零：`producer_mismatch_count==0` 且 `suspicious_gate_invocation_count==0` 且 `forged_summary_attempts==0`
  4. 抽查 C4/C5 证据链：playwright 产物真实存在、截图/trace 非空、与 ac-aggregates 的 covered 一致
- [ ] **⑤ 处置**：DONE 页 → 审 Draft PR（五段模板；inferred 契约页有第六段清单，API 对账后才准合）；BLOCKED_* 页 → 按 J0 分类处理（缺输入补输入、缺路由白天补骨架、预算不够调预算）

## 3. 决策规则卡（忘了就查这张）

| 问题 | 规则 |
|---|---|
| 目标 repo 放哪 | `apps/{产品名}/`（首夜）；独立 repo 等产品长大再拆 |
| 首夜选哪页 | 输入最全 + 复杂度最低；不默认首页；`pages==1` 硬约束 |
| 路由什么时候配 | **永远白天骨架期**；router 是公共面，夜里碰 = BLOCKED_SCOPE（宁可停不许越权） |
| API 文档没到 | 能跑：推断契约 + assumptions 登记 + 晨报红旗；到后 reconcile 对账 |
| 改了控制面脚本 | 当天**不能直接夜跑**：先重跑 A4 独立 smoke（9b digest 硬拦） |
| preflight 红项 | 修完重跑，没有"跳项"这个操作 |
| tokens/shared/router/auth 要改 | 白天改；夜里触发 = BLOCKED_SCOPE，早上你补，下夜重跑 |

## 4. 红灯速查

| 现象 | 含义 | 动作 |
|---|---|---|
| preflight 9b 红（独立证据缺失/runner=self/digest 过期） | 独立 smoke 没跑或控制面又改了 | 重跑 §1 A4 |
| preflight 7 红 | 没签署 | 回 §2.2 ① |
| 夜熔 exit 3（FAILED_INVARIANT） | 权威链检测到矛盾 | 不许修控制面；早上看 events 里 `night_fuse`，找根因 |
| scorecard 不绿 | 控制面被碰过或证据链断 | 当夜全部产出作废处理，按晨审 4 项定位 |
| 页 BLOCKED_INPUT | 输入（PRD/原型/API）不足或冲突 | 白天补输入，不追究夜模型 |
| 页 BLOCKED_BUDGET | 预算小了或页太大 | 拆页或调预算（参考 dry-cost 实测） |
| Draft PR 第六段有 inferred 清单 | 该页用了推断契约 | API 文档对账前**不合 PR** |

## 5. 当前状态备忘（写入时间：2026-07-18）

- §17a 三家审计：Grok ✅ / Opus ✅ / GPT ✅（有条件闭环，终验物料在 `UI/round5/`，无遗留技术项）
- smoke 80/80 双绿（self + independent）；hook v3.1 夜间 Bash 无条件默认拒绝
- 首夜剩余前置：本 SOP §1 首次启用 + §2.2 签署
- GA blockers（不影响首夜，影响"正式 GA"）：P2-1+P2-SOL-1 supervisor 独立写身份 / §18 / 真实首夜 / P1-4 红队 / P2-7
