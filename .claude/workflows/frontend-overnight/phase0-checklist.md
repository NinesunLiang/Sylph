# phase0-checklist — Phase 0 执行清单（白天，有人在场）

> 首夜全做；其后每夜只做 §B（§A 一次性）。

## §A 一次性（首个夜跑周期）

- [ ] **A1 目标 repo 骨架**（§18#3 决定位置）：Vite 8 + React 19 + TS6 strict + Sass/CSS Modules + React Router v7 + Zustand v5 + Axios
  - [ ] `src/styles/tokens/`（色/间距/圆角/阴影变量，C3 的唯一合法来源）
  - [ ] `src/app/router/`、`src/shared/api/api-routing.ts`（mock 层）
  - [ ] ESLint `no-restricted-imports`：禁 antd 全家族（含动态 import/require/re-export）
  - [ ] `tests/e2e/helpers/assertions.ts`：实现 `scripts/carroros-gates/assertion-catalog.yaml` 全部 17 个 helper，**以 catalog id 为键导出 registry**（preflight 4b 会逐个 grep id 字符串，缺一个 = NO-GO）
  - [ ] playwright.config.ts（1440 视口、trace/video 开、artifacts 输出到 manifest 约定路径）
- [ ] **A2 夜跑 hook 挂载**：`python3 scripts/carroros-gates/install_night_hook.py`（幂等）
- [ ] **A3 模型路由探针**：对代理（http://127.0.0.1:9998）用 `claude-opus`/`claude-haiku` 别名各发一个最小请求，记录上游真实模型 → 写 `.omc/night/{date}/model-routing-proof.yaml`（opus→v4-pro、haiku→v4-flash 才算真身；误连高阶 = No-Go）
- [ ] **A4 §17a**：把落盘 diff 发 Opus 4.8 / Grok 4.5 / GPT-5.6 Sol 审计，无新阻断性 P0
  - [ ] 附**独立复跑日志**（Grok P0-2）：rsync 仓库到 /tmp 干净目录 → `SMOKE_RUNNER=independent python3 scripts/carroros-gates/smoke/run_all.py ...` 全绿 → 日志落 `UI/round5/logs/`（self 自陈不得作为首夜放行证据）
  - [ ] 独立复跑结果 yaml 必须落 **`$NIGHT_DIR/smoke-results-independent.yaml`**（Opus P1-10：preflight 9b 硬拦——runner=independent + all_green + tamper_suite_passed + control_plane_digest 与当前一致，缺一 = NO-GO；改完任何控制面脚本后必须重跑本步，否则 digest 不符）

## §B 每夜（含首夜）

- [ ] **B1 intake**：按 `intake.md` 成熟度矩阵填 `inputs.*.status` + 选页（输入最全+复杂度最低，O5）+ `api_contract_status`
- [ ] **B2 feature 目录**（OMA split 格式）：`prd/{app}/feat-{PAGE_ID}/prd.md`（头部写"夜间模式：验收委托机器门禁"）+ state/contracts/mocks
- [ ] **B3 dry-cost 实测**（首夜必做，O4）：拿本夜页人工/半自动走一遍完整门禁周期（research→plan→实现→C1–C7），实测调用数/墙钟/fix 轮 → `budgets = P90 × 1.5` 填 manifest（禁止拍脑袋）
- [ ] **B4 环境指纹**：node/pnpm/lockfile sha256/playwright/browser 版本填 `environment_fingerprint`
- [ ] **B5 控制面锁**：`python3 scripts/carroros-gates/gen_control_plane_lock.py --manifest .omc/night/{date}/night-manifest.yaml --write`
- [ ] **B6 高阶预审**（可选，§17b）：manifest + plan 发一家高阶模型看 AC/七态/overlay_contract，输出仅为建议
- [ ] **B7 你签署**：
  - [ ] `trust_boundary.residual_risk_accepted_by: "<你的名字>"`（S1 残余风险：首夜单页单夜侦探式边界、不自动续期、v3.2 前补预防式隔离三件套）
  - [ ] `shasum -a 256 .omc/night/{date}/night-manifest.yaml` → 填 `night-manifest.signoff.yaml` 的 `manifest_sha256` + `decision: GO` + `signer` + `signed_at`
- [ ] **B8 preflight**：
  ```bash
  python3 scripts/carroros-gates/preflight.py --manifest .omc/night/{date}/night-manifest.yaml \
    --night-dir .omc/night/{date} --target-repo <目标repo>
  ```
  全绿 → 按 README ④ 启动 lx-goal。任何红项 → 修完重跑，不许跳项。
