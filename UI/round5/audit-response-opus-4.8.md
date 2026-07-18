# §17a 审计响应（对 Opus 4.8 回执 · post-Opus-fix）

> 回执原文：`UI/round5/opus-4.8.md`
> 本文：逐条处置。源码行号均为当前工作区真实行号，可复核。
> 结论先行：**无新阻断性 P0**（与 Opus 一致）；三个新 P1 中 P1-10 确诊实洞已修，
> P1-O3 / P1-O5 经源码比对为**已闭环但 Opus 未读到**（其引用的"证据行"在文件中不存在），
> 现以 fresh payload 实测锁死三者。

## 0. 裁决总表

| Opus 项 | 处置 | 证据 |
|---|---|---|
| P1-O3 catalog 未知 id 未拦 | **源码已闭环**（preflight 检查 4）+ payload 锁 | preflight.sh:59-86；R1a/R1b 实测 |
| P1-O5 选页机判不完整 | **源码已闭环**（preflight 检查 3）+ payload 锁 | preflight.sh:47-57；R1c/R1d 实测 |
| P1-10 smoke attestation 未拦 | **确诊实洞，已修**（9b 硬拦 + digest 锚 + 晨报接线） | preflight.sh:157-179；R2–R5 实测 8/8 |
| P1-3 缺 monorepo 子目录 smoke | **已存在**（Grok 轮补的类 7） | run-all.sh:314-354 |
| P2-6 catalog impl 字段 | 接受为 v3.2 catalog v1.1（4b grep 绑定为首夜等价物） | preflight.sh:88-109 |
| P2-7 第三方机器复跑 | 接受，记 GA blocker | §5 |

## 1. P1-O3：preflight 检查 4 就是 Opus 要的那把刀（逐字比对）

Opus 称"preflight.sh 10 项检查中，未见遍历 pages 全部 assert id 未知 → C0 FAIL"，并给出 jq 版修法草图（假设 `required_states[]` 为列表、元素带 `.assert`）。

**实际源码 preflight.sh:59-86（检查 4）**：
- python 内联遍历 `pages[].required_states{}` —— v3.1 schema 是 **mapping**，逐态带 `assert`/`not`/`and` 三键（Opus 草图的列表假设与真实 schema 不符，jq 草图会直接漏检 `not`/`and` 两键）；
- 同时遍历 `overlay_contract.items[].asserts[]`；
- 凡 id ∉ catalog（`state_assertions ∪ overlay_assertions`）→ 打印"未知 assertion ID"逐个点名 → exit 1 → NO-GO。

**实测锁定（fresh payload，非 smoke 夹具复诵）**：
```
R1a O3: manifest 写入 skelton_visible（拼写错）→ preflight NO-GO，报"未知 assertion ID"  ✓
R1b O3: 输出逐字点名 FE-t.loading.assert=skelton_visible                                  ✓
```
（`UI/round5/logs/opus-p1-payloads-20260718.log`，驱动 `UI/round5/opus-p1-payloads.py`）

另：catalog id → helper 绑定由检查 4b（preflight.sh:88-109）逐个 grep `tests/e2e/helpers/assertions.ts`，缺绑定 = NO-GO。O3 "没有断言的状态不算覆盖"首夜链路 = **catalog 封闭（4）+ helper 绑定（4b）+ C7 evidence qualified 判定**，三层均在。

## 2. P1-O5：检查 3 已做五项机判，Opus 引用的"296–303 行"不存在

Opus 引用"preflight.sh 296–303 行"称检查 7 仅判 pages 非空。**该文件共 179 行（修后 201 行），不存在这些行**；检查 7 实为 S1 签署硬拦。

**实际源码 preflight.sh:47-57（检查 3，O5 机判）**：
- `pages==1` 硬规则（多页直接 note）；
- `first_night_selection` 五项逐项 fail-closed：`input_completeness=complete`、`complexity=V0_or_V1`、`prototype_accessible=true`、`acceptance_contract_complete=true`、`happy_path_testable=true`。
- 字段住所是 manifest 顶层 `first_night_selection.*`（FINAL §4.1 / 模板 L26-31），不是 Opus 假设的 `pages[0].variant`。

**实测锁定**：
```
R1c O5: pages=2       → NO-GO，报"pages=2（首夜硬规则 ==1）"            ✓
R1d O5: input_completeness=partial → NO-GO，报"selection.input_completeness=partial（需 complete）" ✓
```

## 3. P1-10：确诊实洞，已修（这是 Opus 本轮最有价值的一击）

**确诊**：Opus 说"preflight 未强制 attestation != self"——对，而且比 Opus 写的更糟：
- preflight 检查 9 **内联**跑 smoke 且不带 `SMOKE_RUNNER` → 写出的 `$NIGHT_DIR/smoke-results.yaml` 恒为 `runner=self`；
- Phase 0 A4 的 independent 复跑证据只落在 `UI/round5/logs/`，**从未进入夜目录袋**；
- 晨报读 smoke-results.yaml → 首夜真实 scorecard 必报 `smoke_attestation=self` → Grok Conditional GO 第 2 项"independent 入袋"在真实链路里会**直接破功**。

**修复（四件套）**：
1. `run-all.sh` 结果 yaml 新增 `control_plane_digest` 字段（独立跑当刻的控制面指纹，新鲜度锚）；
2. **preflight 新增 9b**（preflight.sh:157-179）：`$NIGHT_DIR/smoke-results-independent.yaml` 必须存在 + `runner=independent` + `all_green/tamper_suite_passed=true` + **`control_plane_digest` 等于当前 digest**（防"改完控制面拿三天前的独立绿冒充"），缺一 = NO-GO；
3. `morning-report.sh`：`smoke_attestation` 改从 independent 文件取（回退 self）；scorecard 新增 `smoke_independent_in_bag`；**green 条件加 `smoke_attestation=="independent"`**；
4. `phase0-checklist.md` A4 写明产物契约（含"改任何控制面脚本后必须重跑 A4"）。

**实测（8/8 + 晨报微测 + 独立复跑）**：
```
R2 缺 independent 文件        → NO-GO "smoke 独立复跑证据缺失"        ✓
R3 runner=self                → NO-GO "runner=self（需 independent"   ✓
R4 digest 过期（0*64）        → NO-GO "digest 过期或不符"             ✓
R5 完全合法                   → 9b ✓ 且无任何 9b 红项                 ✓
晨报微测 A（仅 self 文件）     → attestation=self, in_bag=false        ✓
晨报微测 B（+independent）     → attestation=independent, in_bag=true  ✓
独立复跑（rsync→/tmp，git init+commit，SMOKE_RUNNER=independent）
  → 43/43 绿，runner=independent，digest=d1255cd2… 入袋               ✓
  日志：UI/round5/logs/smoke-independent-rerun-20260718-post-opus.log
```

## 4. 意外收获：payload 抓到一个真 latent bug（crash 伪装成 NO-GO）

R2/R3 首轮失败不是断言问题：preflight 在 9b 的 note 行**直接崩死**——
`$SMOKE_IND（…` 中 `$VAR` 紧跟全角括号，本机 locale 下 bash 把高字节计入变量名，
`set -u` 抛 `SMOKE_IND�: unbound variable` 以 exit 1 崩死——**崩溃码与正常 NO-GO 同为 1，伪装成合法裁决**。

同类隐患全库扫描，6 处全修（`$VAR` → `${VAR}`）：
- preflight.sh 5 处（含存量 L117 模型代理在线、L154 smoke 未全绿——此前从未触发所以潜伏至今）；
- finalize-page.sh:31 1 处（**summary immutable 守卫**——夜间重复 finalize 的报错路径，真实夜路径）。

这正是 Grok-A/B 式 fresh payload 的价值：smoke 43 例全绿也照不亮从未执行过的报错分支。

## 5. 对 Opus 其余论断的校正与处置

| Opus 表述 | 校正 |
|---|---|
| "smoke 13/13、五类 smoke" | 过时印象：Grok 轮已扩至 **7 类 43 例**（run-all.sh 头注释 L2-5） |
| "缺 monorepo 子目录 smoke（P1-3）" | 已存在：**类 7**（run-all.sh:314-354）合成 monorepo + `apps/web` 子目录，in-scope PASS / out-of-scope FAIL 双例，本次两轮复跑均绿 |
| §10 操作清单命令 | 四处笔误，勿照抄：① 夜目录是 `date +%F`（YYYY-MM-DD）非 `+%Y%m%d`；② `gen-control-plane-lock.sh` 需 `--manifest M --write` 才落盘；③ 无 jq/yq 依赖，统一 `carros_base.py manifest-json --get`；④ 首夜入口是 `/lx-goal` 技能（DeepSeek 代理会话 `ANTHROPIC_BASE_URL=http://127.0.0.1:9998`），无 `lx-goal.py on` 此命令 |
| argv_digest finalize 未强制校验 | 确认现状与 Opus 判断一致：一阶防护是 digest+producer，argv_digest 为晨报侦探字段（suspicious_gate_invocation），v3.2 再评估升格 |
| P2-6 catalog `impl: module#fn` + 参数 schema | 接受为 **v3.2 catalog v1.1**；首夜等价物 = 4b grep 绑定（17 id 全在 helper registry 方可起飞） |
| P2-7 第三方机器全量复跑 | 接受，记 **GA blocker**（与 P2-1 supervisor、§18 全证据链、真实首夜、P1-4 红队并列） |

## 6. 措辞合规（按 Opus 禁用表）

- ✅ 本文及后续文档一律写"**无新阻断性 P0**"（有 3 个新 P1，已全部处置）；
- ✅ 权威链表述为"**工具面旁路已封**"（S1 子进程写为 FINAL §4.5 声明残余，Owner 签署承责）；
- ✅ O3 表述升级为"**闭环**"——catalog 封闭（检查 4）+ helper 绑定（4b）+ payload 实测锁，不再是"部分落地"。

## 7. Conditional GO 清单更新（Opus 版 5 项）

| # | 条件 | 状态 |
|---|---|---|
| 1 | deny v2 hook 激活 | ✅ 机器绿 |
| 2 | independent smoke 43/43 + Grok-A/B 7/7 | ✅ 机器绿（post-Opus 复跑日志在袋） |
| 3 | Owner 签署 S1 | ⬜ 用户动作（Phase 0 B7；preflight 检查 7 硬拦） |
| 4 | preflight 全绿 | ✅ 机制就位（现 12 步：1/2/3/4/4b/5/6/7/8/9/9b/10；Opus 关切的三项已全部硬化并 payload 锁定） |
| 5 | control_plane_lock 生成且 immutable | ✅ 机器绿 |

**GA blockers（更新后）**：P2-1 v3.2 supervisor 独立写身份 / §18 全证据链 / 真实首夜实跑 / P1-4 night-loop 红队（scorecard 已写死 `red_team_night_loop: due=after_first_trial`）/ P2-7 第三方机器复跑。
~~P1-O3/O5/10 三项修复~~——已消项（O3/O5 源码本已闭环、P1-10 本轮修复，全部 payload 实测锁定）。

## 8. 证据索引

| 证据 | 路径 |
|---|---|
| Opus P1 payload 驱动（fresh） | `UI/round5/opus-p1-payloads.py` |
| payload 日志 13/13 | `UI/round5/logs/opus-p1-payloads-20260718.log` |
| smoke 自跑回归 43/43 | `UI/round5/logs/smoke-self-20260718-post-opus.log` |
| smoke 独立复跑 43/43（runner=independent） | `UI/round5/logs/smoke-independent-rerun-20260718-post-opus.log` |
| 修复 diff | preflight.sh（9b + 5 处花括号）/ run-all.sh（digest 字段）/ morning-report.sh（attest 接线 + green 条件 + in_bag 字段）/ finalize-page.sh（1 处花括号）/ phase0-checklist.md（A4 产物契约） |
