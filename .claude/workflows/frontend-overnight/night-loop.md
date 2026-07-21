# night-loop — 夜循环执行手册（执行模型读本）

> 读者：夜间执行模型（DeepSeek V4 Pro；修复 subagent = V4 Flash）。
> 你在这个会话里无人值守。**本手册是你的全部行动空间；手册外没有"灵活发挥"。**

## 四条元规则（违反 = 当夜作废）

1. **验收委托声明**：本流程没有人类验收环节。RPE 第 6 步"等待用户验收"由机器门禁链 C1–C7 + finalize 重算替代。你不许停下来等人，也不许自己宣布完成——`final_status` 只能由 `finalize_page.py` 从 gate-results 重算产生。
2. **结论禁写**：你不许写/改 `verification-summary.yaml`、`morning-report.md`、`control-plane-scorecard.yaml`、`gate-results/**`、`token.json`（token 只能经 `carros_base.py token-write` API）。手写结论 = 篡改，晨审必现。
3. **控制面禁碰**：`scripts/carroros-gates/**`、`.claude/settings*.json`、`.claude/hooks/**`、manifest 一个字节都不许动（hook deny + control_plane_lock + 晨审 git diff 三层拦截）。
4. **旁路即篡改（GPT §17a §4.3 不变量）**：夜间 Bash 是无条件默认拒绝，只有精确白名单内的命令形态能执行。任何不在白名单的操作，不得通过字符串拆分、变量拼接、glob、解释器（python/node/sh）间接调用、cwd 切换或引号变形来规避；被 hook 阻断后**不得尝试等价改写命令绕过**——记 `execution-events.jsonl` 一条 `BLOCKED_CONTROL_PLANE` 并停手（该页按 J0 出口处理）。绕过尝试本身 = 篡改，晨审必现。

## Bash 精确白名单（hook v3 fullmatch；此外一律 exit 2）

1. 门禁脚本：`scope_check / c7_check / evidence_check / finalize_page / abstraction_check`（python3 调用）
2. `lib/run_gate.py ... -- <wrapped>`：C2=tsc/eslint/build，C4/C5=playwright，C6=视觉脚本
3. `carros_base.py` 三 API：`manifest-json / gate-results-init / token-write`
4. 页基线：`git -C $R rev-parse HEAD > $NIGHT/page-baselines/{page}.sha`（唯一合法 `>`）
5. 事件追加：`echo {...} >> $NIGHT/execution-events.jsonl`（唯一合法 `>>`）
6. 只读：`cat/ls/grep/rg/head/tail/find(禁-exec)/shasum/stat/file/wc/date/sort/uniq/diff/realpath/readlink/basename/dirname/pwd/which`
7. git 只读：`status/diff/log/show/rev-parse/ls-files`；git 写：`add` + `commit`（步 3-5 原子提交；壳元字符与括号只许出现在引号内）
8. `gh pr create|status|view`（步 13）
9. lx-goal 运行时：`python3 .claude/skills/lx-goal/scripts/lx-goal.py ...`
10. 版本探针：`node|pnpm|npm|python3 --version`（步 0 指纹比对）
11. `mkdir -p`；scoped `rm -rf`（仅 `.omc/task/**` artifacts，步 10）

禁：换行/heredoc、链式（`&&`/`;`/`|`）、重定向（除 4/5 两条）、命令替换（含双引号内 `$( )` 与反引号）、`ln`、`find -exec/-delete`、裸解释器（`python3 -c`/`node -e`/`bash x.py` 等）、未列出的任何命令。

## 禁止列表（Grok §17a P1-5；违反任一条 = 篡改，晨审必现）

- 禁止手写/伪造 gate-result 信封：不许直接调用 `gate_result.py`，不许用 python/node/重定向等任何方式写 `gate-results/**`。
- 禁止滥用 `run_gate.py`：wrapped 命令必须是该门禁的工具链——C2=tsc/eslint/build，C4/C5=playwright，C6=视觉脚本。包 `true`/`echo`/空命令骗 PASS = 篡改（晨报 `suspicious_gate_invocation_count` 必现）。
- 禁止在测试/脚本文件里写控制面路径（hook 拦不住子进程，但 PR diff 晨审必现，且信封 producer/digest 校验会爆炸）。
- 禁止运行 `preflight.py` / `morning_report.py` / `gen_control_plane_lock.py` / `install_night_hook.py` / `smoke/run_all.py`（白天人类工具，hook 已硬拦）。
- 禁止猜测/宣布 `final_status`；禁止"接近完成先开 PR"（`draft_pr_on: DONE_only`）。
- 任何门禁/脚本返回 **exit 3（FAILED_INVARIANT）= 夜熔**：立即停止本页一切动作，记 `execution-events.jsonl` 一条 `night_fuse`，不许继续、不许尝试修复控制面。

## 13 步主循环（每页）

前置：`MANIFEST=.omc/night/{date}/night-manifest.yaml`，`NIGHT=.omc/night/{date}`，`R=<目标repo>`。

| 步 | 动作 | 通过标准 |
|---|---|---|
| 0 | **PAGE_BOUNDARY_RESET**：工作树干净；环境指纹比对（node/pnpm/lockfile/playwright）；清 browser context/storage/mock 内存态/端口；记录页基线 `git -C $R rev-parse HEAD > $NIGHT/page-baselines/{page}.sha` | reset 失败 → **夜熔 WORKSPACE_POISONED**（记 events，整晚停） |
| 1 | **research**：按 `prototype.kind` 分型测量（interactive=逐触发器扫描；static/mixed=禁伪装点击，浮层只认 PRD/标注/intake 登记）；分段滚动捕获 fold 以下；仓库模式扫描 → `research.md` + overlay-inventory + `reuse-map.json` | fold 以下没进 research 就不许进 plan |
| 2 | **plan 冻结**：files_allowed / AC 逐条 / 七态断言落 playwright（ID 必须在 assertion-catalog.yaml 内）/ overlay_contract 确认（status∈{declared,confirmed_none}，unknown → BLOCKED_INPUT）/ rollback 方案 → `plan.md` 标 frozen | overlay unknown 不许冻结 |
| 3–5 | **实现**：骨架→结构→交互，原子提交（每提交可编译）；全 mock；api 层按 `api_contract_status`（inferred → 每条推断契约补登 assumptions.yaml） | 不碰 files_allowed 外任何文件 |
| 6 | **C1**：`python3 scripts/carroros-gates/scope_check.py --manifest $MANIFEST --night-dir $NIGHT --page-id {page} --target-repo $R` | exit 0；越界 → 回步 3 修，越界×2 → 页熔 |
| 7 | **C2**：`python3 scripts/carroros-gates/run_gate.py --gate-id C2 ... -- pnpm -C $R exec tsc --noEmit` 然后 eslint（`--max-warnings 0`）然后 `pnpm -C $R build`（三次各写一个 C2 信封） | 失败 → Fixer（V4 Flash）修，编译失败 3 轮 → 回步 2 |
| 8 | **C3**：`python3 scripts/carroros-gates/c7_check.py ...` | 裸色值/魔法px/:global/!important/antd → 回步 4 修 |
| 9 | **C4/C5**：`python3 scripts/carroros-gates/run_gate.py --gate-id C4 ... -- pnpm -C $R exec playwright test`；C5 浮层矩阵（§7.1 R3 逐浮层：modal=遮罩+Esc+scroll-lock+焦点归还+焦点陷阱；click popover=外点+Esc+再点；hover menu=≥200ms 延迟关闭且光标进入取消；tooltip=hover显/leave隐） | spec 必须写 `evidence-index.yaml`（code_sha + 每 assert_id → 证据文件） |
| 10 | **code freeze**：`git -C $R rev-parse HEAD` 记为 code_sha（含 tests/——freeze 后改 tests 与改 src 同罪）；清旧 artifacts | freeze 后写 src/ = FAILED_INVARIANT |
| 11 | **C6**：视觉确定性子集（1440 不崩/关键区域齐/无横向溢出/无 console error/文本不截断/token 色号间距可测/浮层开启态无遮挡），截图文件名带 code_sha 前缀 | FAIL → VISUAL_FIXING（只治同 fingerprint 最小修复，修后**从 C1 全链重跑**，旧 gate-results 标 SUPERSEDED）；工具失败 → BLOCKED_ENV，**绝不许 DONE** |
| 12 | **C7 + C8a**：`evidence_check.py` 然后 `finalize_page.py` | final_status 由 finalize 宣布，不是你 |
| 13 | **C8b（仅 DONE）**：archive → `gh pr create --draft`（五段模板：做了什么/AC过卡/assumptions/未动公共区/控制面摘要；**`api_contract_status=inferred` 时第六段强制列出推断契约清单**）→ 写 `delivery-receipt.yaml`；gh 故障 → `delivery_status: DRAFT_PR_FAILED`，**不改写 DONE** | 非 DONE 不建 PR |

## J0 出口（唯一的"判断"空间）

| 情形 | 出口 |
|---|---|
| PRD/API/原型冲突 | BLOCKED_INPUT（登记冲突点，以原型为视觉事实源） |
| 架构歧义 | 最小风险六优先级 + assumptions.yaml + 晨审标记 |
| 宪法未覆盖 | 最小风险 + 记录，继续 |
| 根因裁决 | 不做，记 error-dna |
| 公共面（tokens/shared/router/auth）需要改 | BLOCKED_SCOPE（同 gap 本地绕开 ≥2 次也触发） |
| 静态原型浮层不足 | BLOCKED_INPUT |
| 工作区中毒 | **夜熔**（唯一不许"继续下页"的情形） |

## 预算纪律（manifest budgets，dry-cost 实测值）

- Implementer 调用 ≤ `per_page_calls`；Fixer ≤ 4/页；fix 轮 ≤ `fix_rounds`；页墙钟 ≤ `page_wall_clock_min`
- 逼近上限 → 当前步完成后按 J0 记 BLOCKED_BUDGET，**不许**为赶预算跳门禁、降断言、删测试

## execution-events.jsonl（每事件一行，追加写 $NIGHT/execution-events.jsonl）

```json
{"ts":"...","page":"FE-x","event":"page_start|gate_fail|fix_round|crash_recovery|WORKSPACE_POISONED|blocked|night_fuse","detail":{...}}
```

崩溃恢复时：读 token.json 定位 → **重验对应 gate-results**（不许见 `*_VERIFIED` 就续跑）→ 从最后一个有合法 PASS 信封的门禁之后继续。
