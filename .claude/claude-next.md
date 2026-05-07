# claude-next.md — AI 学习笔记

> >
> 由 harness-kit 自动生成
> 记录 AI 协作过程中积累的项目特有经验和教训
> 新经验默认进入此文件，验证稳定后可升华到 kernel.md

---

## 待验证规则

<!-- 条目格式（严格遵循，升华检测依赖此格式）: --><!-- ## [来源] 标题 --><!-- @YYYY-MM-DD hits:1 --><!-- 触发条件 + 行为 + 证据 --><!-- --><!-- 规则: --><!-- 1. 新增条目必须带 @日期 hits:1 元数据行 --><!-- 2. 再次遇到同一教训时，hits +1 而非新增重复条目 --><!-- 3. 升华条件(自动检测): 条目≥20 | 年龄≥10天 | hits≥5 -->

### [seed:typescript] 禁止 any 类型逃逸

@2026-01-01 hits:3触发条件：编写 TypeScript 代码时使用 `any` 绕过类型检查正确行为：使用 `unknown` + 类型守卫，或定义精确的接口类型证据：any 类型会导致下游所有类型推断失效，形成"类型黑洞"

### [seed:typescript] useEffect 依赖数组必须完整

@2026-01-01 hits:3触发条件：编写 useEffect 时省略依赖或使用 `// eslint-disable`正确行为：完整列出所有依赖；若依赖过多，拆分 effect 或提取自定义 Hook证据：遗漏依赖导致 stale closure，表现为状态不更新或无限渲染

### [seed:typescript] API 响应必须定义完整类型

@2026-01-01 hits:2触发条件：fetch/axios 调用后直接使用 `response.data` 无类型正确行为：在 `src/types/` 定义响应接口，fetch 封装中使用泛型 `Promise<T>`证据：无类型的 API 响应在下游使用时编译器无法检查字段名拼写错误

### [seed:general] 修改接口前必须查引用

@2026-01-01 hits:4触发条件：修改 interface/type 定义的字段名或类型正确行为：先 `lsp_find_references` 列出所有引用方，全部同步修改后再编译验证证据：只改定义不改引用方导致连锁编译错误，越修越多

### [seed:general] 长对话中禁止依赖记忆引用文件内容

@2026-01-01 hits:5触发条件：对话超过 10 轮后引用之前读过的文件内容正确行为：每次需要文件内容时重新 Read，标注 [已验证: file:line]证据：长对话记忆衰减导致引用的代码片段与实际不一致

### [rpe-014] OMA Lock 增强 — os.rename 解决 TOCTOU

@2026-05-04 hits:1
触发条件：实现文件系统锁管理器，需要在检测到锁过期后夺锁
正确行为：使用 os.rename(tmp_file, lock_file) 原子替换锁文件，然后验证所有权（写后读确认）。不应使用 unlink()+O_EXCL 两步操作。
证据：unlink+continue 在 unlink 和 O_EXCL 之间存在 TOCTOU 窗口，另一个进程可能在此窗口内抢先创建锁。os.rename 是 POSIX 原子操作，配合验证确保唯一赢家。

### [rpe-014] 锁可观测性用 tmp+rename 实现原子写入

@2026-05-04 hits:1
触发条件：多个进程可能并发写入 JSON 状态文件（如 .omc/state/locks.json）
正确行为：写临时文件 → os.rename(tmp, target) 实现原子替换，避免部分写入被并发读取
证据：直接 write_text 不是原子操作，并发读取可能读到部分内容。os.rename 确保读取端始终看到完整内容。

### [R22] PostToolUse 不派发失败事件，失败走 PostToolUseFailure

@2026-05-05 hits:1
触发条件：写 PostToolUse hook 想捕获 Bash 失败命令（如 error-dna/bash-audit）
正确行为：必须在 settings.json 同时注册 `PostToolUse` 和 `PostToolUseFailure` 两个事件名。失败事件的 JSON schema 不同：没有 `tool_response.exit_code`/`stderr`，改为顶层 `error: string` + `is_interrupt: boolean`。hook 脚本要双轨兼容。
证据：Claude Code 源码 src/utils/hooks.ts:3460 `executePostToolUseHooks` 只在成功时触发，src/utils/hooks.ts:3492 `executePostToolUseFailureHooks` 才处理失败 — 这是设计分叉不是 bug。本项目原 settings.json 只注册 PostToolUse，导致 error-dna.jsonl 永远空 = 僵尸功能。
补强：即使注册了 PostToolUseFailure，也应同时挂 Stop hook 扫 transcript.jsonl 兜底（防平台后续改名或丢事件），形成双层防御。

### [R23] harness.yaml 的 hooks_enabled 不等于实际注册

@2026-05-05 hits:1
触发条件：磁盘上有 hook 脚本、harness.yaml 里 hooks_enabled.<name>=true，但 settings.json 没注册命令 → 产品承诺生效但 Claude Code 运行时根本不派发事件给它（僵尸脚本）。
正确行为：三方必须齐一：(A) 磁盘脚本存在、(B) settings.json 有对应事件 + matcher 注册、(C) harness.yaml 开关打开。任一缺失就是漂移。
证据：本轮发现 12 个脚本中 8 个属于"A+C 有但 B 缺"（lsp-suggest / pretool-rule-anchor / pretool-write-lock / subagent-guard / posttool-edit-quality / posttool-write-lock / flywheel-report / skill-flywheel），另 1 个属于"B 有但 C=false"的反向漂移（proactive-handoff）。
兜底：已添加 `.claude/scripts/audit-hooks.sh`，Claude Code 升级改事件名时一键发现；已纳入 harness-smoke 回归。

### [R25] subagent-guard max_turns 只能"软约束+事后对账"，不能硬停

@2026-05-05 hits:1
触发条件：设计 hook 以约束子 agent 用量（防账单雪崩）。
正确行为（三层防线，注意定位边界）：
1. **声明层**（PreToolUse: `subagent-guard.sh`）：Task 工具 schema 没有 `max_turns` 字段，AI 无法在 tool_input 合法传参。改为三级 fallback：`tool_input.max_turns` > description/prompt 正则扫 `max_turns[=:]N` > 默认值（harness.yaml `subagent_guard.default_max_turns`，默认 20）。默认值放行时输出 additionalContext 提醒 AI。
2. **执行层**（PostToolUse: `posttool-subagent-audit.sh`）：记录所有危险 agent 返回的 `content_bytes` 到 `.omc/state/subagent-usage.jsonl`；超过阈值（默认 50KB，`high_usage_threshold_bytes` 可配置）写 flywheel P0 事件 + additionalContext 告警。
3. **人工层**：flywheel P0 在下次 SessionStart 弹表格告警，让用户决定。
证据：
- Claude Code Task 工具 `tool_response` 不暴露子 agent 实际 turns/tokens 字段给 hook（2026-05 schema 实测），只能用 content 字节数做启发性估算。
- 因此 `max_turns=N` 本质是"AI 自我约束 + 人工事后感知"，**不是运行时强制中断**。子 agent 若跑飞（死循环 100 轮），hook 中断不了，只能事后通过 flywheel P0 让用户感知。
- 若 Claude Code 将来开放 `tool_response.turns/usage/tokens`，执行层可升级为硬门禁（阻断/退款）— 目前留的占位：harness-smoke `R25 posttool-subagent-audit` case 已预留 content_bytes → flywheel P0 的回路。
定位文案（写清楚避免误认"已根治账单雪崩"）：
> max_turns = AI 行为约束 + 事后对账，不是运行时硬停。防线三层：声明层约束 AI 意识，使用层落盘留痕，人工层 SessionStart 告警。

### [R24] Bash unquoted glob 会被 cwd 文件污染（生产级陷阱）

@2026-05-05 hits:1
触发条件：hook 或任意 shell 脚本里写 `for x in $GLOB_VAR` 且 `$GLOB_VAR` 包含 `*` 等通配符（例如 `SOURCE_EXT="*.go"`）。
正确行为：进入这类循环前 `set -f` 禁用 pathname expansion，循环结束 `set +f` 恢复；或用数组 + `"${arr[@]}"` 完全避开 word splitting。
证据：bash 对未加引号的变量先做 word splitting、再做 pathname expansion。配置里的 `*.go` 如果 cwd 刚好存在 `main.go`，整个 glob 会被展开成具体文件名（只剩 `main.go`），后续 case 匹配就只对 basename=main.go 生效，其他所有 .go 都漏过。本项目 cwd 有 `main.go`，导致 `edit-guard.sh` / `posttool-edit-quality.sh` / `posttool-read-cite.sh` 三个 hook 在真实项目目录下形同虚设（smoke 刚好用 `main.go` 做样例才侥幸绿）。
补强：harness-smoke 的 R18 回归 case 改为 `/Users/demo/project/src/main.go`（真实全路径）+ `/tmp/notes.txt`（非源文件），避免未来再出现"靠 cwd 巧合通过测试"。

### [R26] hook 脚本内白名单 vs settings.json matcher 一致性陷阱

@2026-05-05 hits:1
触发条件：扩大 `.claude/settings.json` 某个 hook 的 `matcher` 范围（如 `Edit|Write|Bash` → `.*`）但未同步审查脚本内部的工具过滤逻辑。
正确行为：matcher 扩大后，必须逐 hook 检查脚本内是否有 `case "$TOOL_NAME" in edit|write|bash) ... ;; *) exit 0 ;;` 之类的早退分支。两层过滤必须语义一致 — 要么 matcher 收窄，要么脚本里删白名单。
证据：本项目 R19 把 `context-guard` matcher 改为 `.*`（产品承诺"所有工具受门禁"），但 `context-guard.sh` 保留了 `edit/write/bash` 白名单，结果 Read/Grep 在 95% 上下文时被脚本层再次放行，与"冷酷无情 AI 管理员"定位矛盾。R26 手动实弹 D3 Read @ 95% 才发现。
补强：`hook-production-verify.sh` D3 的四工具循环（Write/Bash/Edit/Read @ 95%）永久守护此回归 — 任何工具例外都会立即 🔴。

### [R29] context-guard matcher 放宽为 Edit|Write 防自锁

@2026-05-07 hits:1
触发条件：context-guard 使用 `.*` matcher 封锁所有工具，导致 90% 上下文时无法用 Read/Grep 诊断、无法用 Bash 修复 `token-tracking-index.json`，形成不可恢复的自锁（self-inflicted DoS）。
正确行为：context-guard matcher 改用 `Edit|Write`，保留对写操作的物理阻断，但开放 Read/Grep/Bash 作为诊断恢复通道。原则："读是诊断，写是破坏"。
逃生门：同时在脚本内实现 `context-force-override` 标记文件机制 — 文件存在时跳过阻断，由 Bash 创建（因为 Bash 已不再被 context-guard 封锁）。
证据：
- `.*` matcher + exit 2 = 所有工具被拦 → 无法修复导致自锁的 index 文件 → 死锁
- 修改后 D3 测试改为：Write/Edit → expect exit 2，Read/Bash → expect exit 0
- permission-gate.sh（Bash matcher）仍独立守护危险命令（rm -rf, git push --force），安全边界不丢失

补强：harness-smoke-test 新增 context-force-override 逃生门测试 case；hook-production-verify D3 改为两路断言。

### [R27] 报告中任何百分比/评分必须有行业标准来源 URL 或 file:line

@2026-05-06 hits:2
触发条件：在 docs/ 下编写报告，含百分比或评分或"通过率"时
正确行为：同行必须有 URL / 文献 / file:line 作为来源证据。无来源则标记 `[内部自检，非行业标准]`。自创指标与行业标准物理隔离（不同表格/章节），禁止并排放置于同一主表。
证据：pass-rate-summary-20260505.md §三 初版将自创 C/E 口径（文件级 Clean 率 / 最严格口径）与 ASVS/ATLAS/NIST 行业标准并排放于同一张"多口径汇总"表，未标注"自创""无行业标准来源"，构成铁律 #1 编造违规。用户纠正后移除 C/E，追加 §十二 标准映射附录。事件复盘确认"形式门禁（证据文件存在）全部通过，语义门禁（断言真实性）无对应 hook"。


---

<!-- 已升华到 kernel.md 或 style-guide.md 的条目记录在此 -->
<!-- 格式: - \~\~原标题\~\~ → 归宿（如 kernel.md §X.X 已覆盖）@日期 -->

### [R28] 废弃架构描述必须随实现同步更新

@2026-05-06 hits:1
触发条件：实现从 Sub-agent 盲审变更为双终端交叉验证后，README.md 仍描述旧模式
正确行为：每次架构变更后，搜索 `docs/` 和 `README.md` 中所有相关描述并同步更新
证据：Sub-agent → A→B→A 切换后，README.md 及 20+ 营销文档仍描述旧模式，用户纠正后才修复
