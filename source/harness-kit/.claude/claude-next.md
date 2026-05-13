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

