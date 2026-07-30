# frontend-overnight 优化事实集

> **用途**：供线上大模型（DeepSeek V4 Flash / Kimi K3 / GPT-5.5 / Opus-4.8）读取本文件，理解工作流全貌后提出优化方案。
> **生成时间**：2026-07-28
> **来源**：Carror OS Base 项目 `.claude/workflows/frontend-overnight/` 全套文档 + `scripts/carroros-gates/` 门禁套件

---

## 目录

1. [工作流一句话定位](#1-工作流一句话定位)
2. [文件路径清单（全量）](#2-文件路径清单全量)
3. [角色与模型路由](#3-角色与模型路由)
4. [13 步夜循环详解](#4-13-步夜循环详解)
5. [Bash 精确白名单（执行模型的笼子）](#5-bash-精确白名单执行模型的笼子)
6. [UI 宪法核心约束](#6-ui-宪法核心约束)
7. [Token 系统（当前状态）](#7-token-系统当前状态)
8. [门禁链 C1–C8a 详解](#8-门禁链-c1c8a-详解)
9. [断言词表（Assertion Catalog）](#9-断言词表assertion-catalog)
10. [运行时 I/O 路径约定](#10-运行时-io-路径约定)
11. [决策点与 J0 出口](#11-决策点与-j0-出口)
12. [可观测指标](#12-可观测指标)
13. [文件耦合依赖图](#13-文件耦合依赖图)
14. [当前已知 4 个问题](#14-当前已知-4-个问题)
15. [优化方向建议锚点](#15-优化方向建议锚点)

---

## 1. 工作流一句话定位

**夜间无人值守前端 UI 还原工作流**。

白天人类备料（放原型 + PRD + 签署），夜间执行模型在 Bash 精确白名单笼子里，按 13 步主循环逐页还原 UI：research → plan → implement → C1–C7 机器门禁 → finalize → Draft PR。次日早上人类看记分卡收货。

核心哲学：**验收委托给机器门禁链（C1–C8a），人类不回消息也能自我闭环**。每页一轮 13 步，多页串行。

---

## 2. 文件路径清单（全量）

### 2.1 工作流文档（.claude/workflows/frontend-overnight/）

| 路径 | 用途 | 角色 |
|------|------|------|
| `README.md` | 总览、能力边界、输入分期、5步流程、命令速查 | 日间人类 |
| `SOP.md` | 可勾选操作手册：首次启用/每周期备料+点火+晨收/红灯速查 | 日间人类 |
| `intake.md` | 输入成熟度矩阵（1-4级）、reconcile流程 | 日间人类 |
| `phase0-checklist.md` | §A一次性骨架 + §B每夜备料checklist | 日间人类 |
| **`night-loop.md`** | **夜循环13步主循环、Bash白名单、禁止列表、J0出口** | **执行模型读本** |
| `OPTIMIZATION-FACTSET.md` | 本文件，供线上模型优化用 | 线上优化模型 |

### 2.2 门禁脚本套件（scripts/carroros-gates/）

**核心门禁（夜跑每页逐步调用）：**

| 脚本 | 对应步 | 作用 |
|------|--------|------|
| `scope_check.py` | C1 | 越界检测（只写files_allowed内的文件） |
| `run_gate.py` | C2/C4/C5 | 统一门禁运行器，wrapped命令=tsc/eslint/build/playwright |
| `c7_check.py` | C3 | 裸色值/魔法px/:global/!important/antd检测 |
| `evidence_check.py` | C7 | 证据链完整性检查 |
| `finalize_page.py` | C8a | 从gate-results重算final_status（模型禁写） |
| `abstraction_check.py` | C3补充 | 组件抽象检测 |
| `lib/gate_result.py` | — | 门禁结果信封（模型禁止直接调用） |
| `lib/common_lib.py` | — | 公共库 |
| `assertion-catalog.yaml` | — | 17个断言helper catalog（封闭词表） |
| `gate-contract.yaml` | — | 门禁契约定义 |

**白天人类工具（模型禁调）：**

| 脚本 | 用途 |
|------|------|
| `gen_control_plane_lock.py` | 生成控制面锁 |
| `install_night_hook.py` | 挂载夜跑hook（幂等） |
| `preflight.py` | 起飞前全项检查（含9b独立证据digest校验） |
| `morning_report.py` | 生成晨报+控制面记分卡 |
| `smoke/run_all.py` | 独立smoke测试 |

**模板：**

| 路径 | 用途 |
|------|------|
| `templates/night-manifest.template.yaml` | manifest模板 |
| `templates/night-manifest.signoff.template.yaml` | 签署模板 |

### 2.3 UI 宪法（原型还原硬规范）

| 路径 | 用途 |
|------|------|
| `.claude/UI_README.md` | 项目宪法v4.1：目录结构、CSS类名、Design Tokens、C6/C7检查点、API三层路由 |

### 2.4 自主执行框架

| 路径 | 用途 |
|------|------|
| `.claude/skills/lx-goal/SKILL.md` | lx-goal技能定义（Phase 0→N + 退出报告） |
| `.claude/skills/lx-goal/references/autonomous-execution.md` | 危险操作裁决链、硬边界、卡点处理、跨会话续跑 |

### 2.5 运行时路径

```
.omc/night/{YYYY-MM-DD}/
├── night-manifest.yaml              # 夜跑清单
├── night-manifest.signoff.yaml      # 人类签署
├── model-routing-proof.yaml         # 模型路由探针结果
├── assumptions.yaml                 # 推断契约登记
├── control-plane-scorecard.yaml     # 晨报记分卡（模型禁写）
├── execution-events.jsonl           # 事件日志（唯一合法>>追加）
├── page-baselines/{page}.sha        # 每页基线sha
├── gate-results/                    # 门禁结果信封（模型禁写）

.omc/state/
├── night-session.active             # 夜会话标记（preflight创建，晨报rm）
└── tokens/lx-goal.json              # lx-goal锁

.omc/screenshots/{任务名}/           # 运行截图（不可写项目根目录）
```

---

## 3. 角色与模型路由

| 角色 | 模型 | 做什么 |
|------|------|--------|
| **主执行模型** | DeepSeek V4 Flash | 夜循环13步主执行、修复subagent |
| **视觉识别** | Gemini-3-Flash（或Kimi K3） | 通过adapter(:8765)接入，原型测量+视觉对比 |
| **审计/评审** | GPT-5.5 / Opus-4.8 | 事后审计、证据链校验 |
| **优化模型** | DeepSeek V4 Flash + Kimi K3 | 本事实集的阅读者、优化方案产出者 |

adapter端点：`http://127.0.0.1:8765`，路由探针在Phase 0 A3。

---

## 4. 13 步夜循环详解

每页一轮。前置常量：`MANIFEST=.omc/night/{date}/night-manifest.yaml`、`NIGHT=.omc/night/{date}`、`R=<目标repo>`。

### 步0：PAGE_BOUNDARY_RESET
- 工作树干净
- 环境指纹比对（node/pnpm/lockfile/playwright版本）
- 清browser context/storage/mock内存态/端口
- 记录页基线：`git -C $R rev-parse HEAD > $NIGHT/page-baselines/{page}.sha`
- 失败→夜熔WORKSPACE_POISONED

### 步1：research
- 按`prototype.kind`分型测量：
  - interactive=逐触发器扫描
  - static/mixed=禁伪装点击，浮层只认PRD/标注/intake登记
- 分段滚动捕获fold以下
- 仓库模式扫描→`research.md` + overlay-inventory + `reuse-map.json`
- 铁律：fold以下没进research就不准进plan

### 步2：plan冻结
- files_allowed / AC逐条 / 七态断言落playwright（ID必须在assertion-catalog.yaml内）
- overlay_contract确认（status∈{declared, confirmed_none}，unknown→BLOCKED_INPUT）
- rollback方案→`plan.md`标frozen
- 铁律：overlay unknown不许冻结

### 步3–5：实现（原子提交）
- 骨架→结构→交互，原子提交（每提交可编译）
- 全mock
- api层按api_contract_status：inferred→每条推断契约补登assumptions.yaml
- 不碰files_allowed外任何文件

### 步6：C1 越界检测
```
python3 scripts/carroros-gates/scope_check.py --manifest $MANIFEST --night-dir $NIGHT --page-id {page} --target-repo $R
```
- exit 0；越界→回步3修，越界×2→页熔

### 步7：C2 编译链
```
python3 scripts/carroros-gates/run_gate.py --gate-id C2 -- pnpm -C $R exec tsc --noEmit
# 然后eslint --max-warnings 0
# 然后pnpm -C $R build
```
- 三次各写一个C2信封
- 失败→Fixer(V4 Flash)修，编译失败3轮→回步2

### 步8：C3 风格约束
```
python3 scripts/carroros-gates/c7_check.py
```
- 裸色值/魔法px/:global/!important/antd→回步4修

### 步9：C4/C5 Playwright测试
```
python3 scripts/carroros-gates/run_gate.py --gate-id C4 -- pnpm -C $R exec playwright test
# C5浮层矩阵（每浮层逐条）
```
- C5浮层关闭语义矩阵（7.1 R3）：
  - modal：遮罩+Esc+scroll-lock+焦点归还+焦点陷阱
  - click popover：外点+Esc+再点
  - hover menu：≥200ms延迟关闭且光标进入取消
  - tooltip：hover显/leave隐
- spec必须写evidence-index.yaml（code_sha + 每assert_id→证据文件）

### 步10：code freeze
- `git -C $R rev-parse HEAD`记为code_sha（含tests/）
- 清旧artifacts
- freeze后写src/ = FAILED_INVARIANT

### 步11：C6 视觉校验
- 视觉确定性子集：1440不崩/关键区域齐/无横向溢出/无console error/文本不截断/token色号间距可测/浮层开启态无遮挡
- 截图文件名带code_sha前缀
- FAIL→VISUAL_FIXING（只治同fingerprint最小修复，修后从C1全链重跑，旧gate-results标SUPERSEDED）
- 工具失败→BLOCKED_ENV，绝不许DONE

### 步12：C7 + C8a 证据最终化
```
python3 scripts/carroros-gates/evidence_check.py
python3 scripts/carroros-gates/finalize_page.py
```
- final_status由finalize宣布，不是模型

### 步13：C8b Draft PR（仅DONE）
- archive
- `gh pr create --draft`
- 五段模板：做了什么/AC过卡/assumptions/未动公共区/控制面摘要
- `api_contract_status=inferred`时第六段强制列出推断契约清单
- `delivery-receipt.yaml`
- gh故障→delivery_status: DRAFT_PR_FAILED

### 预算纪律
- Implementer调用≤per_page_calls
- Fixer≤4/页
- fix轮≤fix_rounds
- 页墙钟≤page_wall_clock_min
- 逼近上限→J0_BLOCKED_BUDGET

---

## 5. Bash 精确白名单（执行模型的笼子）

**元规则**：夜间Bash无条件默认拒绝，只有精确全匹配的白名单命令能执行。hook v3 fullmatch。不在白名单→exit 2。禁止字符串拆分/变量拼接/glob/引号变形绕过。

### 5.1 允许的命令

```
1. 门禁脚本：scope_check / c7_check / evidence_check / finalize_page / abstraction_check（python3调用）
2. lib/run_gate.py -- <wrapped>
3. carros_base.py 三API：manifest-json / gate-results-init / token-write
4. 页基线：git -C $R rev-parse HEAD > $NIGHT/page-baselines/{page}.sha（唯一合法>）
5. 事件追加：echo {...} >> $NIGHT/execution-events.jsonl（唯一合法>>）
6. 只读：cat/ls/grep/rg/head/tail/find(禁-exec)/shasum/stat/file/wc/date/sort/uniq/diff/realpath/readlink/basename/dirname/pwd/which
7. git只读：status/diff/log/show/rev-parse/ls-files；git写：add+commit（步3-5原子提交；壳元字符与括号只许在引号内）
8. gh pr create|status|view（步13）
9. lx-goal运行时：python3 .claude/skills/lx-goal/scripts/lx-goal.py ...
10. 版本探针：node|pnpm|npm|python3 --version（步0指纹比对）
11. mkdir -p；scoped rm -rf（仅.omc/task/** artifacts，步10）
```

### 5.2 绝对禁止

```
- 换行/heredoc
- 链式（&&/;/|）
- 重定向（除步4/5的两条合法路径）
- 命令替换（含双引号内$()与反引号）
- ln、find -exec/-delete
- 裸解释器（python3 -c/node -e/bash x.py等）
- 未列出的任何命令
- 运行preflight.py/morning_report.py/gen_control_plane_lock.py/install_night_hook.py/smoke/run_all.py
- 手写gate-result信封
- 滥用run_gate.py（包true/echo/空命令骗PASS）
- 在测试/脚本文件里写控制面路径
- 猜测/宣布final_status
- exit 3（FAILED_INVARIANT）=夜熔：停止本页一切动作，不许继续
```

---

## 6. UI 宪法核心约束

来源：`.claude/UI_README.md`

### 6.1 技术栈
Vite 8 + React 19 + TS 6 strict + Sass + CSS Modules + React Router v7 + Zustand v5 + Axios v1

### 6.2 目录铁律
- 每个页面组件必须文件夹结构：`ComponentName/index.tsx + index.module.scss + components/ + hooks/`
- 禁止平铺文件
- 父子关系通过components/目录维系

### 6.3 CSS 类名规范
- snake_case（全小写+下划线）
- 域名前缀：discover_page / ecosystem_kpi
- BEM修饰符：`--modifier`（双连字符）
- SCSS嵌套：源码结构反映DOM层级
- 禁止：裸page/shell/wrapper、camelCase类名

### 6.4 C7 红线
- .tsx ≤300行
- .module.scss ≤300行
- 文件内≤3个功能块
- 无裸色值/px魔法数

### 6.5 断点策略
- xl≥1440px：三栏全展示
- lg 1280-1439px：默认布局
- md 1024-1279px：侧边栏折叠（grid第一栏=0或仅图标）
- <1024px：不支持，最小宽度提示

---

## 7. Token 系统（当前状态）

**当前状态：Token 系统只有变量定义框架，缺少原型抽取→Tailwind迁移的自动化流程。**

### 7.1 现有 Token 文件位置
```
src/styles/tokens/
├── _colors.scss          # 色值变量
├── _typography.scss      # 字体变量
├── _spacing.scss         # 间距、断点变量
└── index.scss            # 统一导出
```

### 7.2 Token 在 C3 的作用
- C3（c7_check.py）检测裸色值/magic px时，唯一合法来源是 `src/styles/tokens/`
- 非新值或无近似值禁止从零定义新值

### 7.3 缺失的自动化
- **没有**从原型自动抽取色值/间距/圆角/字体的流程
- **没有**Tailwind配置化的迁移机制
- **没有**原型值与Token值之间的diff对比工具
- 当前是手动定义变量后人工对标原型

---

## 8. 门禁链 C1–C8a 详解

| 门禁 | 名称 | 作用 | 模型干预 |
|------|------|------|---------|
| C1 | scope_check | 越界检测——只写files_allowed内文件 | 越界→回步3修 |
| C2 | run_gate(tsc/eslint/build) | 类型检查+lint+编译 | 编译失败3轮→回步2 |
| C3 | c7_check + abstraction_check | 裸色值/px/:global/!important/antd + 组件抽象 | 违规→回步4修 |
| C4 | run_gate(playwright test) | 七态断言 + 功能测试 + 交互测试 | 失败→Fixer修复 |
| C5 | run_gate(playwright overlay) | 浮层关闭语义矩阵（每浮层逐条） | 同上 |
| C6 | 视觉确定性检查 | 1440不崩/关键区齐/无溢出/无console error等 | FAIL→VISUAL_FIXING→C1全链重跑 |
| C7 | evidence_check | 证据链完整性：code_sha→每assert_id→证据文件 | — |
| C8a | finalize_page | 从gate-results重算final_status | 模型不介入 |
| C8b(13) | gh pr create --draft | Draft PR创建 | 仅DONE时调 |

---

## 9. 断言词表（Assertion Catalog）

来源：`scripts/carroros-gates/assertion-catalog.yaml` v1.0

**封闭词表规则**：manifest引用的assert ID必须在本文件中。未知ID→preflight FAIL。禁止自由文本断言。

### 七态断言（state_assertions）

| ID | helper函数 | 用途 |
|----|-----------|------|
| skeleton_visible | assertSkeletonVisible | loading期间骨架屏可见 |
| no_layout_shift_on_resolve | assertNoLayoutShiftOnResolve | loading→success CLS≤0.1 |
| list_or_detail_refreshed | assertContentRefreshed | 渲染数据节点 |
| empty_state_visible | assertEmptyStateVisible | 空态文案可见 |
| retry_affordance_present | assertRetryAffordance | 重试入口可点击 |
| no_white_screen | assertNoWhiteScreen | 错误态非白屏 |
| trigger_disabled_during_inflight | assertTriggerDisabledDuringInflight | 提交中按钮禁用 |
| no_dirty_state_after_close | assertNoDirtyStateAfterClose | 关闭后状态复位 |

### 浮层断言（overlay_assertions）

| ID | helper函数 | 用途 |
|----|-----------|------|
| overlay_close_on_mask_click | assertOverlayCloseOnMaskClick | modal点击遮罩关闭 |
| overlay_close_on_esc | assertOverlayCloseOnEsc | Escape关闭 |
| scroll_lock_while_open | assertScrollLockWhileOpen | modal打开期间scroll lock |
| focus_return_to_trigger | assertFocusReturnToTrigger | 关闭后焦点归还 |
| focus_trap | assertFocusTrap | Tab/Shift+Tab焦点循环 |
| overlay_close_on_outside_click | assertOverlayCloseOnOutsideClick | click popover外点关闭 |
| overlay_close_on_retoggle | assertOverlayCloseOnRetoggle | click popover再点关闭 |
| hover_delay_close | assertHoverDelayClose | hover menu≥200ms延迟关闭 |
| tooltip_hover_show_leave_hide | assertTooltipHoverSemantics | tooltip hover显/离开关 |

---

## 10. 运行时 I/O 路径约定

### 10.1 preflight 检查项（Bash白名单对应的暗约束）
1. 工作树干净
2. target-repo存在
3. files_allowed文件全部存在
4. assertion-catalog.yaml 与 tests/e2e/helpers/assertions.ts 一一对应（grep ID字符串）
5. overlay_contract引用assert ID在catalog内
6. manifest pages至少1页
7.签署文件存在且decision=GO
8.页面编号不重复（FE-01，FE-02等统一前缀）
9b.独立smoke结果存在、runner=independent、all_green、tamper_suite_passed、digest匹配

### 10.2 事件日志格式
```json
{"ts":"...","page":"FE-x","event":"page_start|gate_fail|fix_round|crash_recovery|WORKSPACE_POISONED|blocked|night_fuse","detail":{...}}
```

### 10.3 崩溃恢复
读token.json定位→重验对应gate-results（不许见*_VERIFIED就续跑）→从最后一个合法PASS信封的门禁之后继续

---

## 11. 决策点与 J0 出口

J0 是模型唯一的"判断"空间，其他情况按规则执行。

| 情形 | 出口 |
|------|------|
| PRD/API/原型冲突 | BLOCKED_INPUT（登记冲突点，以原型为视觉事实源） |
| 架构歧义 | 最小风险六优先级 + assumptions.yaml + 晨审标记 |
| 宪法未覆盖 | 最小风险 + 记录，继续 |
| 根因裁决 | 不做，记error-dna |
| 公共面（tokens/shared/router/auth）需要改 | BLOCKED_SCOPE |
| 静态原型浮层不足 | BLOCKED_INPUT |
| 工作区中毒 | 夜熔（唯一不许继续下页） |
| 预算不足 | BLOCKED_BUDGET（不许跳门禁降断言删测试） |

---

## 12. 可观测指标

来源：`front-stepwise/origin.md §九`

| 指标 | 目标 |
|------|:-----|
| 平均每张卡用户提问数 | 越低越好 |
| 可自行检查的问题占比 | ≥80% |
| 卡片跳过率 | 0% |
| 越界修改次数 | 0 |
| 新增lint/type/test回归 | 0 |
| 公共契约未声明变化 | 0 |
| prompt cache hit rate | 持续监控 |

---

## 13. 文件耦合依赖图

```
白天人类准备
  SOP.md ──reads──► README.md
  SOP.md ──reads──► intake.md
  SOP.md ──reads──► phase0-checklist.md
  phase0-checklist.md ──refs──► assertion-catalog.yaml
  phase0-checklist.md ──refs──► night-manifest.template.yaml

点火
  SOP.md §2.2 ──runs──► preflight.py
  preflight.py ──reads──► manifest + signoff + assertion-catalog.yaml
  preflight.py ──validates──► independent-smoke-results
  preflight.py ──creates──► night-session.active

夜执行
  /lx-goal ──loads──► night-loop.md
  night-loop.md ──defines──► Bash白名单（hook执行）
  night-loop.md ──calls──► scope_check.py | run_gate.py | c7_check.py | evidence_check.py | finalize_page.py
  night-loop.md ──writes──► research.md | plan.md | execution-events.jsonl
  night-loop.md ──reads──► assertion-catalog.yaml | manifest | UI_README.md
  run_gate.py ──wraps──► tsc/eslint/build/playwright
  finalize_page.py ──reads──► gate-results/（模型禁写）

晨审
  morning_report.py ──reads──► manifest + events + gate-results/
  morning_report.py ──writes──► control-plane-scorecard.yaml

控制面（模型禁碰）
  scripts/carroros-gates/          ─── hook deny + control_plane_lock + 晨审git diff 三层拦截
  .claude/hooks/                   ─── hook deny精确白名单执行
  .claude/settings*.json           ─── hook deny
  manifest/signoff                ─── hook deny
  gate-results/**                 ─── hook deny + 信封验证

UI消费端
  UI_README.md ──defines──► src/styles/tokens/（原型还原的唯一合法色值/间距来源）
  assertion-catalog.yaml ──maps──► tests/e2e/helpers/assertions.ts（一一对应）
  compact_inject/ ──ui-styling.md / react-patterns.md / data-layer.md / qa-checklist.md（规范细节）
```

---

## 14. 当前已知 4 个问题

### 问题 1：不 loop → 跑一阵退出

**表现**：应该开启/loop模式一致迭代直到逼近原型，但目前执行一段时间后就退出。从80%→90%相似度要十几次人工推动。

**根因推测**：
- `/lx-goal`激活指令`12`（12小时budget）用完后自然退出
- 主循环没有自迭代机制——「检查→发现差距→自动修复」的闭环缺失
- 视觉对比（步11 C6）只做最小修复，没有迭代阈值

**需要优化**：
- `night-loop.md`的主循环需加迭代控制器：`similarity < threshold → continue（不exit循环）`
- 增加自迭代循环：检测相似度 → 无进展N次 → exit

### 问题 2：不科学 → 应该是整体→局部遍历

**表现**：没有先整体框架/布局→再到每个区域→再到每个区域里面的元素进行遍历和还原。

**根因推测**：
- 步1（research）和步3-5（实现）没有阶段拆分
- research阶段是平面式检查，不是先宏观再微观递归

**需要优化**：
- `night-loop.md`增加三层阶段：
  - **Phase A (宏观骨架)**：外布局框架、路由挂载、全局tokens初始化、页面容器定位
  - **Phase B (中观区域)**：逐区域（header/sidebar/main/footer）审视位置、大小、布局方式
  - **Phase C (微观元素)**：逐元素检查文字、间距、颜色、交互态
- 外循环嵌套内循环：每层通过门禁后再进入下一层

### 问题 3：没有正确 Token 系统

**表现**：没有用变量定义公共的颜色集合、距离集合、圆角集合、字体集合。没有从原型到 Tailwind 体系的自动化迁移。

**根因推测**：
- Token系统只在`UI_README.md`有框架定义（`src/styles/tokens/`）
- 没有「原型 → 抽取 → Tailwind / Sass 变量」的自动化流程
- Token定义是手动的，人工程度高，夜模型不会自动做

**需要优化**：
- 新增 step 0.5：「原型 Token 抽取」→ 扫码值/间距/圆角/字体 → 写 `_colors/_typography/_spacing.scss` → 初始化 Tailwind config
- Step 1 research 后增加「Token一致性校验」：页面使用颜色/间距/字体是否在Token集合内

### 问题 4：不按 UI_README.md 执行原型还原

**表现**：没有按要求完整还原，比如滚动到底、悬浮显示菜单、点击浮窗、侧边栏收缩展开、多模块页面。

**根因推测**：
- research阶段（步1）缺少清单式完整性检查
- 浮层发现的触发方式不完整（只检查了声明的浮层，没遍历隐藏的触发器）
- 交互态（hover/click/expand/collapse）未纳入research checklist

**需要优化**：
- research阶段（步1）增加完整性checklist：
  - 滚动到底：fold以下内容是否捕获
  - 悬浮菜单：所有可hover元素是否遍历
  - 点击浮窗：所有可点击触发器是否扫描
  - 侧边栏：收缩/展开两种状态是否记录
  - 多模块页面：每个page级模块是否全部列出（不要只聚焦主区域）
- 交互清单外部化成文件：`overlay-inventory.md` 必须是「交互状态 × 元素」的笛卡尔积全覆盖

---

## 15. 优化方向建议锚点

**核心原则**：`night-loop.md` 是执行模型的 prompt，它定义了一切。改动它 = 改变执行行为。

| 优化目标 | 改哪个文件 | 影响范围 |
|----------|-----------|---------|
| Loop自迭代 | `night-loop.md` 新增外循环控制器 | 执行模型的运行时行为 |
| 整体→局部三层 | `night-loop.md` 步1-5重构为Phase A/B/C | research+实现阶段 |
| Token自动化 | `night-loop.md` 新增步0.5 + `UI_README.md` 增补流程 | 骨架搭建阶段 |
| 完整性检查 | `night-loop.md` 步1强化research checklist + 交互清单外部化 | research阶段 |
| Budget模型 | `night-loop.md` 预算纪律段调整 | 预算耗尽决策 |
| 视觉迭代 | `night-loop.md` 步11 C6增补迭代阈值逻辑 | C6修复策略 |
| Bash白名单增补 | `night-loop.md` §Bash精确白名单 | 如需新增命令访问时必须同步 |

**不要改的文件**（保持稳定）：
- 门禁脚本（`scope_check.py / run_gate.py / c7_check.py / evidence_check.py / finalize_page.py`）
- `gate-result.py`、`gate-contract.yaml`
- 白天人类工具（`preflight.py / morning_report.py / gen_control_plane_lock.py / install_night_hook.py`）
- `.claude/hooks/` 全部
- `.claude/settings*.json`

---

*本文档供线上优化模型阅读。使用时将此文件全文 + 原型地址 + 模块静态截图一并作为context输入到优化模型，让其理解全貌后给出优化方案。*
