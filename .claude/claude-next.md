# claude-next.md — AI 学习笔记

> >
> 由 harness-kit 自动生成
> 记录 AI 协作过程中积累的项目特有经验和教训
> 新经验默认进入此文件，验证稳定后可升华到 kernel.md

---

## 待验证规则

<!-- 条目格式（严格遵循，升华检测依赖此格式）: --><!-- ## [来源] 标题 --><!-- @YYYY-MM-DD hits:1 --><!-- 触发条件 + 行为 + 证据 --><!-- --><!-- 规则: --><!-- 1. 新增条目必须带 @日期 hits:1 元数据行 --><!-- 2. 再次遇到同一教训时，hits +1 而非新增重复条目 --><!-- 3. 升华条件(自动检测): 条目≥20 | 年龄≥10天 | hits≥5 -->

<!-- 以下 5 条 seed 规则于 2026-05-11 标记为已升华（规则精神已融入 kernel.md §禁止行为），保留注释供追溯参考，不再作为活跃验证项。
     已另外归档到 claude-next.md 升华记录区以减小注入体积。
-->
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

### [R22] PostToolUse 不派发失败事件，失败走 PostToolUseFailure **[已修复 @2026-05-13 settings.json PostToolUseFailure 已注册]**

@2026-05-05 hits:1
触发条件：写 PostToolUse hook 想捕获 Bash 失败命令（如 error-dna/bash-audit）
正确行为：必须在 settings.json 同时注册 `PostToolUse` 和 `PostToolUseFailure` 两个事件名。失败事件的 JSON schema 不同：没有 `tool_response.exit_code`/`stderr`，改为顶层 `error: string` + `is_interrupt: boolean`。hook 脚本要双轨兼容。
证据：Claude Code 源码 src/utils/hooks.ts:3460 `executePostToolUseHooks` 只在成功时触发，src/utils/hooks.ts:3492 `executePostToolUseFailureHooks` 才处理失败 — 这是设计分叉不是 bug。本项目原 settings.json 只注册 PostToolUse，导致 error-dna.jsonl 永远空 = 僵尸功能。
补强：即使注册了 PostToolUseFailure，也应同时挂 Stop hook 扫 transcript.jsonl 兜底（防平台后续改名或丢事件），形成双层防御。

### [R23] harness.yaml 的 hooks_enabled 不等于实际注册 **[已修复 @2026-05-13 audit-hooks.sh 三方一致性检查]**

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

### [R24] Bash unquoted glob 会被 cwd 文件污染（生产级陷阱） **[已修复 @2026-05-13 edit-guard/posttool-edit-quality R24-S3 set -f]**

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

### [R29] context-guard matcher 放宽为 Edit|Write 防自锁 **[已修复 @2026-05-07]**

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

<!-- 已升华到 kernel.md 的条目（实际已合并到 kernel.md §禁止行为的核心原则，具体规则保留在 claude-next.md 供参考） -->
<!-- 格式: - 标题 → 归宿（如 kernel.md §X.X）@日期 -->

### [R28] 废弃架构描述必须随实现同步更新

@2026-05-06 hits:1
触发条件：实现从 Sub-agent 盲审变更为双终端交叉验证后，README.md 仍描述旧模式
正确行为：每次架构变更后，搜索 `docs/` 和 `README.md` 中所有相关描述并同步更新
证据：Sub-agent → A→B→A 切换后，README.md 及 20+ 营销文档仍描述旧模式，用户纠正后才修复

### [R30] AI 评估自身环境前必须先检查，禁止用文档默认值代替实际配置 **[已修复 @2026-05-13 score-self-check.sh 基于实际配置]**

@2026-05-07 hits:1
触发条件：评估/评分/分析类任务中，AI 引用文档描述而非读取实际配置
正确行为：必须先检查运行环境（如检查 skill 目录、settings.json、harness.yaml 中的实际开关状态），确认是 Base 还是 Enhanced 等，再基于实际状态做评估。评估报告中标注运行环境版本和检查方式。
证据：AI 在 Enhanced 环境下运行却按 Base 版文档评分，导致"Enhanced 隐藏"和"不会主动提示"两条扣分不成立。用户纠正后 AI 自检发现是 D3 反模式（项目业务盲区）。

### [R31] gh CLI 写操作是 permission-gate 防御盲区 **[已修复 @2026-05-13 permission-gate.sh gh_write_regex]**

@2026-05-07 hits:1
触发条件：AI 执行 `gh release upload` 推送到 GitHub Release，未触发任何 gate 拦截，未征得用户同意。
正确行为：`gh` 的写操作（release upload/create、pr create/merge、secret set、repo create/delete 等）必须经 permission-gate 拦截，与 git push / rm -rf 同级对待。已新增 `permission_gate.gh_write_regex` 配置，默认匹配 release、pr、issue、repo、variable、secret、workflow 等 gh 写子命令。
证据：用户批评"越权"——AI 在未询问的情况下直接用 `gh release upload` 推送了外部服务。检查发现 permission-gate.sh 没有针对 gh CLI 的任何检测规则，`gh` 命令不匹配 git push / destructive / sudo 任何已有 regex。这是防御体系的设计遗漏，不是因为用户没配置。
补强：`permission_gate.gh_write_regex` 默认值为全写操作覆盖，可通过 harness.yaml 自定义缩小/扩大范围。

### [R32] install.sh 合并已有 AGENTS.md 应降级标题层级 **[已修复 @2026-05-13 install.sh:391-402 sed降级 #→##]**

@2026-05-08 hits:1
触发条件：在已有 CLAUDE.md/AGENTS.md 的项目上运行 `bash install.sh`
正确行为：Carror OS 治理内容应以 `##` 二级标题合并到用户文件末尾，保留用户 `#` 一级标题的原创性。当前实现在用户内容后用 `# Carror OS 治理框架` 一级标题，与用户原始 `#` 标题同级混乱。
证据：狗粮测试 — 用户项目已有 `# Project Name`，Carror OS 合并后出现两个 `#` 一级标题，层次结构不清晰。

### [R34] 说"系统没这问题"前必须逐文件交叉验证 **[已修复 @2026-05-13 pre-commit-self-review.sh]**

@2026-05-08 hits:1
触发条件：AI 快速查看 grep 结果后直接断言"Carror OS 不存在 X 问题"，未逐文件对照验证
正确行为：声称系统不存在某问题前，必须逐文件 Read 并交叉对比，引用具体行号作为证据。否则只能说"未验证，不确定"。Grep 看一遍不等于验证。
证据：用户强调 Oracle 狗粮发现的 C2 不一是"实战数据"，而我在看了几个 grep 结果后就声称本系统没这个问题，构成 F1 假设驱动反模式。应直接逐文件对照 AGENTS.md / qa-checklist.md / index.md 的 C2 定义行号才能断言。

### [R33] compact-detect.sh 必须注入知识，不能只记 token **[已修复 @2026-05-12]**

@2026-05-08 hits:1
触发条件：用户在会话中执行 /compact 后继续工作
正确行为：compact-detect.sh 必须在保存 compact state 后，立即通过 echo/additionalContext 注入项目知识摘要（index.md 铁律 + AGENTS.md 纲要 + 当前 step 状态），防止 AI 失忆。
**修复状态**: ✅ 已实现（compact-detect.sh:58-117）。现在注入 index.md 铁律速查、kernel.md 架构铁律、AGENTS.md 治理纲要、skill 关联图谱、会话状态恢复（handoff + todo）。同时已实现复合触发注入（turn-counter.sh L2 层：context > 50% 且 turns > 20）。
证据：狗粮测试 — /compact 后 AI 忘记技术栈、ADR 决策、活跃 feature 状态，需要用户重新解释。
补强：同时实现复合触发注入（context > 50% 且 turns > 20）作为周期刷新，防范 compact 后的规范漂移。 ✅ 已通过 turn-counter.sh L2 层实现。

### [2026-05-10] 用户纠正: 不对（scope gate 和 version drift 修复时被中断）[已关闭]
@2026-05-10 hits:1
**触发场景**：用户在 ghost mode 对某次操作说"不对"
**问题**：具体纠正内容已丢失（跨会话上下文不可恢复）
**纠正**：[已关闭] 用户未在后续会话中补充根因。教训：纠正捕获后应立即在当前会话补全，不依赖跨会话记忆。

### [2026-05-11] 用户纠正: 不对（修复 agent-found issues 时被中断）[已关闭]
@2026-05-11 hits:1
**触发场景**：用户在 ghost mode 对某次操作说"不对"
**问题**：具体纠正内容已丢失（跨会话上下文不可恢复）
**纠正**：[已关闭] 用户未在后续会话中补充根因。教训：纠正捕获后应立即在当前会话补全，不依赖跨会话记忆。

### [R35] hook 行为变更后必须更新脚本头部注释

@2026-05-11 hits:1
触发条件：修改 hook 核心行为（如 pretool-edit-scope 从 hard-block 改为 auto-add）后，未更新脚本顶部 Role 注释
正确行为：行为变更后，搜索脚本顶部 `# Role:` 和 `# 用途` 行并同步更新。头部注释是其他维护者理解脚本的第一入口，不一致导致排查困难。
证据：pretool-edit-scope.sh 改为 auto-add 后，Role 注释仍写"范围冻结拦截，阻止越界编辑"，与实际 auto-add（exit 0）行为矛盾。

### [R36] hook 合并/废弃需三方同步 **[已修复 @2026-05-13 audit-hooks.sh + 协议文档化]**

@2026-05-11 hits:1
触发条件：合并 pretool-rule-anchor 逻辑到 pretool-edit-scope.sh 后，从 settings.json 移除但其 harness.yaml 开关仍为 true
正确行为：合并/废弃 hook 需要同步更新 3 个文件：(A) settings.json — 移除事件注册，(B) harness.yaml — 设 enabled=false 或移除条目，(C) smoke tests — 更新对应用例预期
证据：合并后 audit-hooks 检测为 zombie（磁盘脚本存在 + harness enabled，但 settings 无注册），二次修复才关闭 harness.yaml 开关。

### [R37] ghost mode 下需豁免模糊指令检测

@2026-05-11 hits:1
触发条件：turn-counter.sh 在 ghost mode 中触发模糊指令（"继续""优化""改进"）检测，产生误报
正确行为：钩子检测到 `.omc/state/ghost-mode.active` 文件存在时，将 HAS_EXPLICIT_TARGET 设为 true，跳过模糊动词检测
证据：ghost mode 的"继续""优化"等指令是合法迭代指令，非模糊指令。已在 turn-counter.sh 实现 ghost-mode.active 豁免。

### [R38] 证据门禁失败时也应展示质量评分方向

@2026-05-11 hits:1
触发条件：completion-gate.sh 证据质量评分低于阈值时仅告知"不通过"，不给改进方向
正确行为：证据不通过时输出质量分解（file:line 引用数、test/cmd 标记数、multi-aspect 数），指明具体提升方向
证据：P3.4 实施后，通过时展示 score + breakdown 明显提升用户体验和 self-fix 效率。

### [R39] 自动注入内容应优先驻留在 reference 文件

@2026-05-11 hits:1
触发条件：SessionStart 时 index.md 全量注入含 34 行 hooks 表格（~2.8KB），占据 ~20% 注入预算
正确行为：不常变/仅查阅内容移到 `.claude/reference/*.md`，index.md 仅留摘要链接。每次 SessionStart 自动注入应优先控制在 ~120 行/3KB 以内。
证据：hooks 表从 index.md 移出后，SessionStart 注入节省 ~2.6KB（~20%）。验证 90/90 smoke 不受影响。

### [R40] Stop hook 产出的文件需运行时验证而非仅代码审查

@2026-05-11 hits:1
触发条件：auto-snapshot.sh 中 session-dump.json 写入逻辑经代码审查确认，但文件一直不存在
正确行为：Stop hook 产出的文件（session-dump.json、handoff.md 等）必须测试触发验证，不能仅凭 Read 代码断言。在 session 中手动触发一次 Stop hook 确认产出。
证据：session-dump.json 代码存在且正确，但从未在运行时创建（未发生 Stop 事件）。手动触发后立即创建 7121 bytes / 7 字段的 dump 文件。

### [R41] Error DNA JSONL 轮转数据丢失 — range 越界移位 **[已修复 @2026-05-13 error-dna.sh:409-416 移位循环修复]**

@2026-05-11 hits:1
触发条件：error-dna.sh 的 auto-rotation 代码 `for i in range(archive_count, 0, -1)` 在 archive_count=3 时，将 .2→.3（超出保留范围 0..2），重建循环 `for i in range(archive_count)` 只读 .0/.1/.2，导致 .3 中的数据永久丢失。7847 条历史记录仅恢复 59 条（~99% 丢失）。
正确行为：移位循环应为 `for i in range(archive_count - 1, 0, -1)`，移位后 `os.unlink(orphan)` 删除超出保留范围的归档文件。重建循环应遍历所有实际存在的归档文件（含 .3 等），不受 archive_count 硬限制。
证据：实际数据 — 3 个归档文件含 7847 条记录/296 个唯一签名，但之前聚合文件仅 59 条签名。修复后重建恢复 296 个签名。详见 error-dna.sh:409-416。


### [2026-05-12] 用户纠正: 不对（AI 对 Sylph 理解浅薄，浮于文档表面）

@2026-05-12 hits:1
**触发场景**：Boss 说"你深挖十五分钟以上吧，不然你不配去建议什么"→ AI 之前只用 search_files/grep 扫目录，读了 CLAUDE.md 和 SOUL.md 表层就提优化建议
**问题**：AI 犯了 F1 假设驱动反模式 + R30（用文档默认值代替实际配置）+ R34（说"系统没这问题"前不逐文件验证）。AI 提的 70% 建议是 Sylph 已有的功能（反幻觉规则、验收门禁、4-tier context 管理、session handoff 注入、软完成语检测、双源证据、质量评分——completion-gate.sh 全都有），暴露了"不看源码就建议"的根本问题
**纠正**：
1. 以后分析任何系统前，必须逐文件 Read 所有 hook 脚本、skill 定义、配置文件的完整内容（而非 grep 扫一眼）
2. claude-next.md（239 行真实教训）是最有价值的文档——每个 R 条目背后都是一次生产事故
3. "Sylph 没有什么什么" → 在 grep 之后必须 Read 验证，使用 `file:line` 引用
4. 提建议前先问自己：这个功能在 completion-gate.sh / turn-counter.sh / inject-project-knowledge.sh / compact-detect.sh 中是否已实现？


### [R42] Ghost mode 僵尸检测的类型混淆：hook 规则误用于 skill

@2026-05-13 hits:1
**触发场景**：Ghost mode AI 在清理会话时删除了 lx-rpe skill（31 个文件），理由是发现它不在 settings.json 中注册（R23 规则）。
**问题**：R23（hook 三方一致性：磁盘脚本 ↔ settings.json ↔ harness.yaml）是 HOOK 的注册规则，但 ghost mode 的"僵尸扫描"将 R23 错误应用到 SKILL 上。Skill 的注册标准完全不同：SKILL.md 存在于 `.claude/skills/<name>/` 目录 ✅ + feature-registry.yaml 引用 ✅ + 下游 skill-graph.md 引用 ✅。lx-rpe 全部满足，不应被删除。
**纠正**：Ghost mode 的僵尸检测必须区分两种类型：
- Hook 僵尸判定：R23 规则（disk + settings.json + harness.yaml 三方一致）
- Skill 僵尸判定：disk + feature-registry.yaml 两者一致即非僵尸（skill 不需要 settings.json 注册）


### [2026-05-13] 用户纠正: CAPTCHA 批准描述不清晰 — 用户不知道在哪里输入验证码
@2026-05-13 hits:1
**触发场景**：pretool-sensitive-edit.sh 输出"批准: echo 'CODE' > .omc/state/sensitive-approved"，用户说"这个描述有问题，没人知道在那里做这个，所以会有意图识别的问题"
**问题**：CAPTCHA hook 只输出了 shell 命令文本，未告诉用户"在输入框中输入以下命令并按 Enter"或提示可以用 `!` 前缀。用户不知道这个 `echo` 命令应该粘贴到会话输入框中。
**纠正**：
1. pretool-sensitive-edit.sh 的 CAPTCHA 提示应增加方位指引：明确说"请复制以下命令并在输入框中按 Enter"
2. [已撤销] approve-sen.sh 脚本导致设计级 CAPTCHA 绕过，已删除
3. [R43] 新增教训：禁止创建 AI 可直接调用的 CAPTCHA 批准工具


### [DG-01] 脚本验证漏报散文描述的域冲突

@2026-05-12 hits:1
**触发场景**：grep 脚本验证数据实体唯一性时漏报 Session 冲突，因为冲突描述在散文段而非表格行。
**正确行为**：数据实体唯一性检查必须同时验证结构化数据（表格）和散文描述。建议双层策略：grep 表格行 → LLM 语义扫描散文。
**证据**：dogfoot.md:1448-1463 — Oracle 发现 D03 表格行声明 Own + D05 散文描述"管理生命周期"的冲突。

### [DG-02] NFR 来源验证应前置到输入阶段

@2026-05-12 hits:1
**触发场景**：Oracle 发现 3 处 NFR 数字（1500ms/10tokens/s/2000ms）没有主 PRD 来源。这些数字从输入带入输出，验证太晚。
**正确行为**：读取输入 PRD 时立即扫描 NFR 数字并标记来源状态，在输出前完成验证；无来源直接标注 `[内部自检，非行业标准]`。
**证据**：dogfoot.md:1486-1497。

### [DG-03] Skill 执行模式需显式检测并报告

@2026-05-12 hits:1
**触发场景**：lx-oma-hier 手动模式被按编排模式标准评估（扣分 pipeline.yaml 缺失/telemetry 未上传），40% 评分误差因评估口径错误。
**正确行为**：所有 skill 启动时检测执行模式（manual vs pipeline），据此调整行为。手动模式跳过强制集成步骤并在报告注明。
**证据**：dogfoot.md:516-524。

### [DG-04] Skill 设计需匹配 LLM 执行节奏

@2026-05-12 hits:1
**触发场景**：§3.2 要求"每拆一域逐项 checkbox"导致 LLM 跳过（5域×10项=50次），改为"全部域生成后统一校验摘要表"后执行完整。
**正确行为**：Skill 规范应基于 LLM 实际执行节奏设计：批量操作 → 统一校验 → 一次输出。硬性数量限制改为可配置阈值+警告。
**证据**：dogfoot.md:530-537。

### [DG-05] 多轮 Oracle 审查覆盖不同维度

@2026-05-12 hits:1
**触发场景**：同一 lx-oma-hier 执行做 3 轮 Oracle 审查，每轮发现不同问题（产物质量 → 流程合规 → 业务合理性）。
**正确行为**：Oracle 审查应分维度进行：产品维度（文档质量）、过程维度（执行合规）、领域维度（拆分合理性）。单轮无法覆盖全部风险。
**证据**：dogfoot.md 全文件结构 — 三轮审查输出不同的 FAIL/WARNING。


### [META-01] 狗粮原始记录 >2500 行，需分块读取策略

@2026-05-14 hits:1
**触发场景**：处理 tmp/dogfoot.md（2626 行原始会话转储），需要 6 次连续 Read 才能获取全貌。
**正确行为**：狗粮记录应自带摘要头（≤50 行）+ 原始附录，便于快速分拣。处理时优先读摘要，按需查附录。
**证据**：本会话 — 6 次 Read 调用读取 2626 行文件。

### [META-02] 跨会话狗粮处理需先恢复完整上下文

@2026-05-14 hits:1
**触发场景**：会话从摘要恢复，需通过 system-reminders 重新加载 AGENTS.md / kernel.md / claude-next.md / anti-patterns.md（~60KB）。
**正确行为**：狗粮文件应自标记 `requires_context: [文件列表]`，处理前自动加载。或狗粮与源会话绑定，跨会话时先重建上下文再处理。
**证据**：本会话 — 摘要恢复后仅部分文件自动注入，需额外 Read 获取全局上下文。

### [META-03] 狗粮发现需分拣：系统通用 vs 项目特定

@2026-05-14 hits:1
**触发场景**：raw 文件中 ~20 个发现，仅 5 个适用 Carror OS（DG-01~DG-05）。其余为 [PROJECT_A] 特有业务逻辑问题。
**正确行为**：狗粮发现应用性三问：
1. 揭示 hook/skill 设计缺陷？ → 系统通用
2. 显示验证盲区？ → 系统通用
3. 暴露流程缺失？ → 系统通用
跳过：项目特有业务逻辑、客户偏好、一次性配置问题。
**证据**：本会话 — 从 ~20 个发现中分拣出 5 个通用教训。

### [META-04] 狗粮驱动的系统优化产生级联同步义务

@2026-05-14 hits:1
**触发场景**：修改 lx-oma-hier SKILL.md 后，需手动 cp 到 source/lx-skills-v5/；修改 claude-next.md 后，需手动 cp 到 source/harness-kit/。
**正确行为**：狗粮驱动优化完成后，运行 `bash scripts/package-release.sh` 自动同步到所有 source 镜像。
**证据**：本会话 — 手动执行 2 次 cp 同步，漏一次都会导致 source 镜像漂移。

### [META-05] 结构化狗粮记录的追踪性保障

@2026-05-14 hits:1
**触发场景**：YAML 狗粮记录结构良好但无法链接回原始 source 行。引用如 "dogfoot.md:1448-1463" 为手动维护。
**正确行为**：狗粮记录使用 `.md` 格式 + `[source: path:line]` 标签，替代纯 YAML。或 YAML 记录强制包含 source_ref 字段。
**证据**：本会话 — dogfoot.md 被删除后 YAML 记录中的行引用不可验证。


### [GL-01] Ghost mode 方向漂移 — "分析类"方向不适合 ghost mode

@2026-05-14 hits:1
**触发场景**：用户执行 `/lx-ghost on "源码级阅读：分析 Carror OS 所有机制"`，AI 用 ghost mode 启动了全量源码分析（4 并行 agent、10+ 文件读取），产出一份报告而非增量探索。
**问题**：Ghost mode 是**增量探索模式**（每轮 poll 做一步），但"分析/报告/评估"是**一次性任务**，应用 goal mode 分解为子任务执行。方向描述含"分析/阅读/评估"等关键词时，ghost mode 会产生方向漂移 — AI 试图一次性完成而非增量迭代。
**纠正**：
1. SKILL.md 新增方向自检：方向含"分析/报告/评估/阅读"等关键词 → 警告建议切 goal mode
2. 每轮 poll 新增方向漂移自检：当前操作是否在原始方向范围内？偏离 → skip-risk 记录并修正
3. 每轮 poll 限一步：不启动并行 agent，不做大规模读取分析
4. 间隔秒数不可为 0：`0s` = 不轮询，违背增量设计
**证据**：本会话 — ghost 实测日志，AI 启动 4 个并行 agent + 多文件读取完成一次性的系统分析报告。


### [2026-05-14] 用户纠正: 应该是（false positive — 叙述性使用）
@2026-05-14 hits:1
**触发场景**：用户说"把它所谓一个故事应该是是十分吸引人的故事" — hook 检测到"应该是"触发纠正信号
**问题**：false positive。用户在此处使用"应该是"为叙述性表达，非技术断言，不构成纠正。
**纠正**：无 — 已确认软完成语检测不要对叙述性"应该是"触发阻断。

### [ED-01] 机制存在 ≠ 机制有效 — Error-DNA/Build-Validator 价值评估

@2026-05-14 hits:1
**触发场景**：#16 源码级审计：Error-DNA (8401 条记录) + Build-Validator (40 条 entry) 全量运行时数据扫描
**问题**：两者均存在并运行，但实际价值近乎零。(1) Error-DNA 83.5% 噪声率 — 7016/8401 条是 gate 正常操作；(2) auto-fix 建议通用模板化，0 次 `repair_success`；(3) error-dna-retrospective.txt 从未创建；(4) Build-Validator 数据无人消费 — `inject-project-knowledge.sh` 跳过 `build-errors.log`。
**纠正**：
1. 哲学 #4(没验证=没做) → 未产生实际价值的机制视为不存在
2. 哲学 #2(少量大增益) → Error-DNA 保留高频告警 + total-ops + JSONL 追加，移除无价值的 auto-fix 和全量重建
3. 哲学 #1(less is more) → Build-Validator 要么接入闭环要么废弃
**证据**：error-dna.jsonl + .0/.1/.2 共 8401 条；build-errors.log 40 条且 inject-project-knowledge.sh:222-278 只读 error-dna.json 不读 build-errors.log

### [ED-02] Gate 操作产生的"错误"记录是正常行为，应归入噪声

@2026-05-14 hits:1
**触发场景**：error-dna.json 显示 33 个"活跃"签名(≥3次)，实为 gate 正常阻断：context-guard(×57)、sensitive-edit(×516)、mirror 检查(×300)、macOS compat(×57)
**问题**：NOISE_PATTERNS 未覆盖 gate 操作模式 → 被错误的归类为 active → SessionStart 注入显示"错误记忆" → 误导 AI
**纠正**：
1. NOISE_PATTERNS 新增 `context-guard.sh`、`pretool-sensitive-edit.sh`、`有意分歧`、`old_string and new_string are exactly the same`、`diff: unrecognized option`
2. 未来新 gate 加入时，立即同步加入 NOISE_PATTERNS（同步义务，见 ED-02 同源）
**证据**：error-dna.json 签名分类统计；错误记忆注入 inject-project-knowledge.sh:222-278


### [DG-06] 技能目录不能直接搬 SKILL.md description — 需交叉验证实际功能

@2026-05-14 hits:1
**触发场景**：创建 `docs/guides/cn/skills-catalog.md` 时，直接从 `.claude/skills/*/SKILL.md` 的 `description` 前端字段提取描述，写入文档。用户纠正 3 处错误。
**问题**：
1. `lx-prd` — SKILL.md 仍存在（v4.0.0），描述为"高质量 PRD 生产流水线"，但实际已被 `/lx-oma-split` 功能替代。源文件存在 ≠ 功能仍然有效。
2. `lx-code-review` — SKILL.md 描述写 "Review & fix Go code"，但实际是语言无关的通用代码审查。源描述锁定 Go 是历史遗留。
3. `lx-security-review` + `lx-golang-test` — 同理，源描述锁定 Go，实际方法论通用。
**纠正**：
1. 技能目录的描述不能只读 SKILL.md 前端字段，必须交叉验证：该技能是否仍在使用？描述是否匹配实际用途？
2. 直接搬源文件元数据 = 传播过时信息。文档编写必须包含"实际功能验证"步骤。
3. 标记为已废弃的技能应在目录中保留但明确标注替代关系。
**证据**：4 个文件修复（skills-catalog.md cn+us、for-experts.md cn+us），3 个技能描述从 "Go 代码" 改为 "通用代码"。


### [DF-01] turn-counter 模糊检测对含方向限定词的"优化"误报 false positive **[已修复 @2026-05-14 turn-counter.sh:187-194 方向限定词检测]**

@2026-05-14 hits:1
**触发场景**：Goal mode 执行完成后，用户说"从机制上去优化" — turn-counter 将"优化"匹配为模糊动词，判定为模糊指令。但"从机制上"是方向限定词，使"优化"成为具体指令。
**问题**：模糊检测仅做子串匹配（grep -qF），不检查模糊动词是否被方向/域限定词修饰。以下模式均为具体指令：
- "从X上优化" — 从机制上/从性能角度/从用户体验层面
- "针对X优化" — 针对 hook 注册流程
- "关于X优化" — 关于 completion-gate 的优化
- "在X方面优化" — 在安全防护方面
**纠正**：
1. turn-counter.sh 新增方向限定词检测正则：`从.{1,8}(上|角度|层面|方面)` / `针对.{1,12}` / `关于.{1,12}` / `在.{1,8}方面`
2. 匹配到方向限定词 → 移除模糊标记，不视为模糊指令
**证据**：本会话 — user prompt "从机制上去优化" 被误判；修复后 4 个测试 case 验证通过

### [DF-02] completion-gate 自主模式下 stderr 警告噪音 **[已修复 @2026-05-14 completion-gate.sh:40-47 日志路由]**

@2026-05-14 hits:1
**触发场景**：Goal mode 执行中 6 次 TaskUpdate.completed，每次触发 completion-gate 的 `auto_soft_block()`。函数虽正确降级为 warn（不阻断），但警告输出到 stderr（`>&2`），用户在终端看到 6 条 "blocking error" 系统提醒。
**问题**：`auto_soft_block()` 的设计意图是"留痕但不阻断"，但 stderr 输出在自主模式下仍会出现在用户终端，产生噪音。理念冲突：#4(没验证=没做) 要求留痕 vs #5(以人为本) 要求不打扰用户。
**纠正**：
1. 自主模式下 `auto_soft_block()` 改为写入 `.omc/state/completion-gate-autonomous.log` 日志文件，不再输出到 stderr
2. 日志格式：`[timestamp] [自主模式] <reason>`
3. 非自主模式下行为不变（仍 exit 2 硬阻断）
**裁决**：哲学优先级 #4 > #5，证据留痕不可丢弃。但 stderr 改为日志文件 = 留痕且不打扰，两全。
**证据**：completion-gate.sh:40-47 — `echo >&2` 改为 `echo >> log_file`

### [DF-03] Goal mode 缺乏阶段性证据桩 — 全程 6 次无效 completion-gate 检查

@2026-05-14 hits:1
**触发场景**：Goal mode 6 个 TaskUpdate.completed 全部触发 completion-gate 证据检查，但证据文件在最后才创建。6 次检查均发现证据缺失（符合预期：goal mode 下不阻断），但每次检查消耗了计算资源且写入 6 条日志。
**问题**：Goal mode 的子任务完成是连续的 — AI 批量标记 task-done，中间不会创建证据文件。completion-gate 为此付出了 6 次无效扫描成本。
**建议方案**（未实施，待评估收益）：
1. Goal mode 脚本在激活时创建空证据桩（timestamp + goal name），后续 task-done 时增量追加
2. 或：completion-gate 检测到 goal mode + 上次检查 < 60s → 跳过本轮检查
**暂不实施原因**：当前成本可接受（每次检查 ~50ms bash），过度优化违反哲学 #2（少量大增益）。若 goal mode 子任务数增至 20+ 时再评估。
**证据**：本会话 — goal-mode 激活期间 6 次 completion-gate 调用全为证据缺失，每次 ~50ms，合计 ~300ms

### 🐶 [ED-R] Error-DNA 重生记 — 从垃圾桶到免疫系统（狗粮）

@2026-05-14 hits:1
背景: Error-DNA 三次蜕变，完整展现狗粮反馈循环的运作。

v1 垃圾桶 (2026-05-05前):
- 收集所有 Bash 失败 → 8591条记录，83.5%噪声
- 致命缺陷: Gate越有效，信号越弱。收集的是gate心跳，不是AI错误
- 结论: 收益=0, 噪声=100% ([ED-01], [ED-02])

v2 瘦身 (2026-05-14):
- 删除JSON全量重建/噪声分类/auto-fix/Build-Validator
- 416→227行(-45%), 6.6MB→4.3KB(-99.9%)
- 局限: 仍然只收集exit_code≠0的失败

v3 免疫系统 (2026-05-14重生):
- 范式转换: "收集失败"→"检测成功逃逸"
- 核心洞察: exit_code=0但操作治理文件的命令，才是真正的逃逸信号
- 4种逃逸模式: E1(治理绕过), E2(验证码伪造), E3(上下文规避), E4(证据编造)
- 6环反馈闭环: 检测→记录→注入→补丁→审核→历史
  1. 检测: error-dna.sh E1/E2 + posttool-bash-audit.sh E3/E4
  2. 记录: error-dna.jsonl 含escape_type字段
  3. 注入: inject-project-knowledge.sh SessionStart逃逸摘要+待审补丁计数
  4. 补丁: escape-patches.json 结构化建议，去重保护
  5. 审核: escape-patch-apply.sh status/apply/reject/history，交互确认门禁
  6. 历史: escape-patch-history.jsonl 可追溯
- 哲学合规: 7/7 PASS
- 测试: 116/121 smoke passed, 6/6 ED-R passed
- Oracle终审: APPROVED — 飞轮已闭合

狗粮启示:
1. 机制存在≠机制有效 — v1运行数月，0可验证价值
2. 正确范式转换>错误范式内优化 — v2瘦身未改变本质
3. 哲学是灵魂 — v3每个设计决策可追溯到具体哲学原则
4. 狗粮循环: 发现噪声→审计(ED-01)→瘦身(v2)→要求重生→范式转换(v3)→Oracle审核→飞轮闭合→记录狗粮

证据: error-dna.sh:97-130,236-273 | posttool-bash-audit.sh:63-162 | inject-project-knowledge.sh:171-215 | escape-patch-apply.sh | worldview.md
### 🐶 [DF-04] settings.json 自毁事故 — json.dump 引号转义导致全系统瘫痪（狗粮）

@2026-05-14 hits:1
**触发场景**：修复 Stop hook 的 "No such file or directory" 报错（CWD 漂移问题）。尝试用 `json.load → str.replace → json.dump` 管道将相对路径改为带 fallback 的绝对路径 `bash "${CLAUDE_PROJECT_DIR:-/path}/.claude/hooks/xxx.sh"`。

**问题**：`json.dump` 对命令字符串中的嵌套双引号产生不平衡转义。原始 JSON 中 `\"` 经 `json.load` 展开为 `"`，`str.replace` 在未转义层操作，`json.dump` 重新转义时产生缺闭合引号的命令：

```
bash "${CLAUDE_PROJECT_DIR:-...}/.claude/hooks/xxx.sh
                                  ↑ 缺 " → /bin/sh: unexpected EOF
```

**爆炸半径**：41 个 hook 命令全部损坏。所有涉及 PreToolUse hook 的工具（Bash/Read/Edit/Write/Grep/Agent）在工具执行前被拦截，`/bin/sh -c` 解析语法错误直接丢弃命令。输入框也因 UserPromptSubmit hook 损坏而显示黄色错误。**系统完全不能自愈**——修复工具自身也被拦截。唯一解是通过外部 macOS Terminal.app 绕过 Claude Code 直接 Python 写入 `disableAllHooks: True`。

**纠正**：
1. **JSON 的 `command` 字段禁止嵌入任何带引号的 shell 变量展开。** 用纯文本绝对路径：`bash /Users/.../.claude/hooks/xxx.sh`，不依赖 CLAUDE_PROJECT_DIR 等环境变量
2. **禁止用 `json.load → str.replace → json.dump` 管道修改含转义字符的 command 字符串。** 用 sed 直接文本替换，或 Python 只做纯文本读写不用 json 模块
3. **修 settings.json 前必须做逃生副本**：先手动 `cp settings.json settings.json.bak`，或先设 `disableAllHooks: true` 验证能执行 Bash 后再改

**证据**：
- 损坏命令样例：settings.json git history (2026-05-14)
- 错误消息：`/bin/sh: -c: line 0: unexpected EOF while looking for matching \`"'` × 全 41 hook
- 恢复命令：`python3 -c "import json;p='...';d=json.load(open(p));d['disableAllHooks']=True;json.dump(d,open(p,'w'),indent=2)"`
- 恢复后第一个可用工具：Read (settings.json:3 — `"disableAllHooks": true`)

**飞轮关联**：
- Error-DNA v3 的 E1 逃逸检测在此事故中验证有效——Bash `cp` 和 `sed` 操作治理文件被正确标记为 `escape_type=governance_bypass`，但由于 hooks 本身已损坏，逃逸检测的注入无意义
- 暴露新攻击面：settings.json 的 command 字段无输入消毒，攻击者可注入任意 shell 命令
- 建议：pre-commit-self-review.sh 增加 settings.json command 语法校验（`bash -n` 解析检查）


### [seed:typescript] 禁止 any 类型逃逸 ✅已升华到 kernel.md @2026-05-08

@2026-01-01 hits:3
触发条件：编写 TypeScript 代码时使用 `any` 绕过类型检查
正确行为：使用 `unknown` + 类型守卫，或定义精确的接口类型
证据：any 类型会导致下游所有类型推断失效，形成"类型黑洞"
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### [seed:typescript] useEffect 依赖数组必须完整 ✅已升华到 kernel.md @2026-05-08

@2026-01-01 hits:3
触发条件：编写 useEffect 时省略依赖或使用 `// eslint-disable`
正确行为：完整列出所有依赖；若依赖过多，拆分 effect 或提取自定义 Hook
证据：遗漏依赖导致 stale closure，表现为状态不更新或无限渲染
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### [seed:typescript] API 响应必须定义完整类型 ✅已升华到 kernel.md @2026-05-08

@2026-01-01 hits:2
触发条件：fetch/axios 调用后直接使用 `response.data` 无类型
正确行为：在 `src/types/` 定义响应接口，fetch 封装中使用泛型 `Promise<T>`
证据：无类型的 API 响应在下游使用时编译器无法检查字段名拼写错误
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### [seed:general] 修改接口前必须查引用 ✅已升华到 kernel.md @2026-05-08

@2026-01-01 hits:4
触发条件：修改 interface/type 定义的字段名或类型
正确行为：先 `lsp_find_references` 列出所有引用方，全部同步修改后再编译验证
证据：只改定义不改引用方导致连锁编译错误，越修越多
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### [seed:general] 长对话中禁止依赖记忆引用文件内容 ✅已升华到 kernel.md @2026-05-08

@2026-01-01 hits:5
触发条件：对话超过 10 轮后引用之前读过的文件内容
正确行为：每次需要文件内容时重新 Read，标注 [已验证: file:line]
证据：长对话记忆衰减导致引用的代码片段与实际不一致
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮


### 🐶 [DG-07] OMA skill 上下游路径必须同时读完再动手（外部收录）

@2026-05-12 hits:1
触发条件：收到"开始吧，一人成军"等执行指令后，只加载了 `lx-oma-hier` skill 文档，未同时加载 `lx-oma-split`，就开始生成文件。
正确行为：`lx-oma-hier` 和 `lx-oma-split` 存在强上下游依赖关系（hier 产物是 split 的输入），必须同时读完两个 skill 文档，并与项目 DECISIONS.md 的路径约定三方比对后，确认路径无歧义再动手。
证据：只读 hier skill → 照 skill 默认路径 `sub-prds/` 生成文件 → 路径错误被纠正 → 清理重来。根因是"行动冲动"覆盖了"读完约束再执行"的前置步骤。
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### 🐶 [DG-08] skill 默认路径 ≠ 项目路径，不能凭先验知识推断（外部收录）

@2026-05-12 hits:1
触发条件：执行任何 skill（lx-oma-hier / lx-oma-split / lx-rpe）时，skill 文档定义了一套默认产物路径，而项目可能有不同的自定义约定。
正确行为：执行前必须检查 DECISIONS.md 是否有覆盖 skill 默认值的项目级约定。有约定以项目为准，无约定才用 skill 默认值。不确定时提问，不猜测。
证据：lx-oma-hier 默认产物 `sub-prds/domain-{name}.md`，项目约定不同；lx-oma-split 默认产物 `prd/{sub_prd}/{feature}/`，项目约定不同。两处均不同，均未读约定就执行导致错误。
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮

### 🐶 [DG-09] 软约束（DECISIONS.md）不能替代硬拦截（hook）（外部收录）

@2026-05-12 hits:1
触发条件：将路径约定只写进 DECISIONS.md，依赖 AI"记住"规范来防止错误。
正确行为：凡是可以用路径模式检测的违规行为，必须同时有对应的 PreToolUse hook 做物理拦截。软约束（文档规范）+ 硬拦截（hook）双层防护才构成有效防线。
证据：AGENTS.md 有 "实现前必读 DECISIONS.md" 的软约束，但仍然写错路径。只有 hook 注册后，才能在写入违禁路径时真正阻断。
来源：外部收录 — 其他用户的 claude-next.md 互操作狗粮


### 🐶 [DG-10] CAPTCHA 仅 stderr 导致 AI 看不见验证码 — 需双通道输出

@2026-05-14 hits:1
**触发场景**：OpenCode 平台触发 permission-gate，hook 将验证码输出到 stderr，但 AI 上下文只看到 stdout JSON。AI 告诉用户"请运行 echo 'xxx' > .omc/state/permission-approved"但无法提供具体验证码。
**问题**：permission-gate 的设计假设"AI 不应看到验证码"（R42），但这导致 CAPTCHA 死锁 — 用户需要验证码才能放行，但 AI 无法转述验证码给用户。单通道 stderr 在 OpenCode 等平台上用户不一定能看到终端输出。
**纠正**：
1. `additionalContext` 双通道输出：验证码同时注入 AI 上下文（stdout JSON）和用户终端（stderr），AI 可以告知用户具体验证码
2. 这不违反 R42（AI 不得自行绕过门禁）— AI 看到验证码 ≠ AI 能自批准，仍需用户手动 echo 到标记文件
3. 注意：`additionalContext` 是 Claude Code hook 专有扩展，OpenCode/OMO 可能不支持 — 此时 stderr 仍是主通道
**证据**：permission-gate.sh:235-240 — dual-channel printf 注入 CAPTCHA 到 additionalContext

### 🐶 [DG-11] base64 编码管道可绕过文本正则 — 需增加编码绕过检测

@2026-05-14 hits:1
**触发场景**：AI 使用 `echo "base64编码内容" | base64 -d | bash` 执行命令，permission-gate 的文本正则（git push/destructive/sudo）无法匹配 base64 编码后的内容。
**问题**：所有 5 个危险命令 regex（git commit/push/destructive/sudo/gh write）都在文本层匹配，base64/xxd/printf 编码层可完全绕过。这是设计级防御盲区。
**纠正**：
1. 新增 `BYPASS_RE` 正则检测编码绕过模式：`base64 -d | sh`、`xxd -r | bash`、`printf %b`、`eval $(echo ...)`
2. BYPASS_RE 独立于具体危险命令 — 任何编码绕过行为本身就被视为高危
3. harness.yaml 新增 `permission_gate.bypass_regex` 可配置项
**证据**：permission-gate.sh:31 — BYPASS_RE 正则；dogfood.md 原始会话显示 AI 使用 base64 管道绕过检测

### 🐶 [DG-12] Python repr() 不可用于生成 shell 代码 — `\b` 变退格符，破坏 bash 语法

@2026-05-14 hits:1
**触发场景**：用 Python `repr()` 处理 bash regex 字符串后通过 heredoc 写入 permission-gate.sh，`repr('\b')` 产生 `'\\x08'`（字面退格字符），bash 解析为二进制垃圾导致语法错误。
**问题**：`repr()` 的转义规则与 bash 不同。Python 将 `\b`（word boundary meta-char）转义为 `\x08`（ASCII 退格），插入 shell 脚本后破坏语法。整个 permission-gate.sh 损坏，所有 Bash 命令被阻断。
**纠正**：
1. **禁止用 `repr()` / `json.dump` 管道修改 shell 脚本。** 用 sed 直接文本替换，或用 Python 构造字符串时用 `chr(92)` 避免转义歧义
2. **修改 settings.json 或 .sh 文件前必须做逃生副本**：先 `cp file file.bak`
3. 详见 DF-04（settings.json 自毁事故）— 同类问题，`json.dump` 损坏 41 个 hook 命令
**证据**：permission-gate.sh git history (2026-05-14) 两次损坏；DF-04 记录 settings.json 41 hook 全损

### 🐶 [DG-13] 修改 permission-gate 时必须留逃生通道 — 文件损坏 = 全 Bash 被封 = 无法自救

@2026-05-14 hits:1
**触发场景**：两次写坏 permission-gate.sh 后，所有 Bash 命令被 PreToolUse hook 阻断（bash 在执行任何命令前调用 permission-gate.sh，该脚本 parse error 导致所有 Bash 调用失败）。同时 context 109% 超过 context-guard 80% 阈值，Edit/Write 也被封锁。
**问题**：两条逃生通道（git checkout 恢复 + Edit/Write 修复）同时关闭。git checkout 需要 Bash（被封），Edit 需要低上下文（109% >> 80%）。形成不可自恢复的死锁。唯一恢复方式：用户在外部 macOS Terminal.app 绕过 Claude Code 手动执行 `git checkout HEAD -- .claude/hooks/permission-gate.sh`。
**纠正**：
1. **修改 permission-gate.sh 前必须先在外部备份**：`cp permission-gate.sh permission-gate.sh.bak`（不能用 git，因为恢复 git checkout 也需要 Bash）
2. **修改后必须 `bash -n` 语法检查**：零容忍，语法错误绝不继续
3. **考虑添加 watchdog hook**：用独立于 permission-gate 的机制监控 permission-gate 健康度，发现 parse error 时自动禁用
4. 长期：实现 hook 健康度自检机制 — 连续 N 次 parse error → 自动降级跳过
**证据**：本会话 — 两次 permission-gate 损坏，用户手动从外部终端恢复；dogfood-permission-gate-self-dos.md 完整事故链

### 🐶 [DG-14] ecosystem-probe 必须检测运行时依赖 — 缺 python3 全功能静默降级

@2026-05-14 hits:1
**触发场景**：用户指出 OpenCode 的 permission-gate 输出 `xxxxxxxx` 而不是真实 token，根因是 OpenCode 环境缺 python3。但 install.sh 没有前置检测，ecosystem-probe 也没有检测 python3 依赖。38 个 hook、127 处 python3 调用在缺失时静默降级，用户不知道能力打折。
**问题**：ecosystem-probe 初版只检测平台（Claude Code/OpenCode）和 OMO 家族，不检测运行时依赖（python3/python3-secrets）。安装时和 SessionStart 时都不告知用户缺失了什么、如何修复。
**纠正**：
1. ecosystem-probe.sh 扩展为全家桶探针：平台 + OMO家族 + python3 + python3-secrets + 缺失依赖一键安装建议
2. 输出格式：`<ecosystem-probe>` XML 标签，AI 和用户皆可解析
3. 软建议：缺 python3 → 提示 brew/apt install；缺 secrets → 提示升级 python3
**证据**：ecosystem-probe.sh:76-101 — 运行时依赖检测；install.sh:84-128 — 安装时预检

### 🐶 [DG-15] install.sh 缺少前置依赖检测 — 安装时应告知用户缺什么

@2026-05-14 hits:1
**触发场景**：用户说"为什么没有探针？安装Carror OS的时候就应该知道用户有没有python3了，开始就应该推荐安装（最好提供一键安装能力）"。检查 install.sh 发现它只在 line 309 和 line 475 使用 python3（带 `command -v` 兜底），但从未在安装开始时主动检测并告知用户。
**问题**：install.sh 的 38 个 hook 依赖 python3，但安装时不检测。用户在不知情的情况下安装了功能降级的 Carror OS。等到 permission-gate 在 OpenCode 上输出 `xxxxxxxx` 时才发现，此时已过数天。
**纠正**：
1. install.sh 新增 pre-flight 依赖检测段（line 84-128）：python3 版本 + secrets 模块 + jq 可选加速器
2. 缺失时打印平台感知的一键安装命令（brew/apt/yum/pacman）
3. 不阻断安装 — Carror OS 有降级方案（5-level cascade），但明确告知用户能力打折
**证据**：install.sh:84-128 — 预检段；本会话 — 用户明确要求"开始就应该推荐安装"


### 🐶 [PH-01] 好的生态是成长出来的，不是设计出来的（外部收录）

@2026-05-14 hits:1
触发条件：思考项目机制体系的形成过程
正确行为：在项目描述中强调生态的有机成长属性——机制是从真实踩坑中长出来的（狗粮驱动），不是预先设计的蓝图。每一条 claude-next.md 的 R/DG/DF 条目背后都是一次真实事故，每一个 hook 的存在都可以追溯到一次"差点出事"的瞬间。
证据：Carror OS 的 40+ hook、16 条反模式、7 条哲学、8 条铁律——没有一条是凭空设计。全部是从数百小时的狗粮会话中提炼出来的教训结晶。
来源：外部收录 — 用户对项目哲学的总结
