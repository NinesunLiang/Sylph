- Carror OS v6.1.7-stable 特性审计报告
审计日期：2026-05-06
审计范围：architecture-review.md 中的所有特性声明，对照 source/ 目录下的实际源码
审计方法：逐一 Read 源文件、统计行数/文件数、对比功能声明与代码实现
证据等级：L1=端到端验证 / L2=代码核验 / L3=文件存在性 / L4=仅文档声明
--------------------------------------------------------------------------------
总览
类别数量✅ 特性声明与实现一致（真实）7⚠️ 部分真实但存在夸大4❌ 虚假项（声明与实现严重不符）3🔁 冗余项（实际价值被重复计入或增益不足）2
--------------------------------------------------------------------------------
一、❌ 虚假项（声明与实现严重不符）
V-1：Hook 数量声明 "24 个"，实际 25 个文件，有效 Hook 约 20 个
文档声明（architecture-review.md:29）：
"24 个 Bash Hook 加起来不到 1000 行代码"
实际情况 [已测试：ls hooks/ | wc -l → 26，wc -l hooks/*.sh → 2768 行]：
- Hook 目录中共 
26 个 .sh 文件，其中 harness_config.sh 是共享配置库（被所有 Hook source），不是独立 Hook
- 有效 Hook 约 
25 个（排除 config），而非 24 个
- 总行数 
2768 行，而非"不到 1000 行"——超出声明近 3 倍
危害等级：中。数量偏差较小，但行数夸大三倍，"极致轻量"的核心卖点存在明显失实。harness.yaml 中 hooks_enabled 节还有多个 Hook 默认 false（如 plan_gate: false、posttool_read_cite: false），实际运行时加载的 Hook 数更少。
--------------------------------------------------------------------------------
V-2：context_monitor.py 声明"从底层直读 token-tracking 数据"——实际依赖一个外部写入的 JSON 文件
文档声明（architecture-review.md:172）：
"context-guard.sh（第 24 个 Hook）从底层直读 token-tracking 数据"
"当 ctx% >= 80%，抛出 Exit 2 锁死系统"
实际情况 [已验证：context_monitor.py:15-26]：
state_file = root / ".omc" / "state" / "token-tracking-index.json"
usage = 0
limit = 200000
if state_file.exists():
    data = json.load(f)
    usage = data.get("usage", 0)
- 脚本
不从任何系统底层读取 token 数量，仅读取 .omc/state/token-tracking-index.json
- 该文件
必须由外部机制写入——源码中没有任何写入此文件的代码
- 若该文件不存在，
usage 默认为 0，ratio = 0/200000 = 0，Context Guard 永远不会触发
- "物理阻断"的实际触发依赖一个从未被创建的状态文件
危害等级：高。这是架构评分中 [H] 防幻觉 得 9.5 分、[T] 任务连续性 得 9.8 分的核心支撑特性，但该功能在默认安装状态下处于静默失效状态，评分依据不成立。
--------------------------------------------------------------------------------
V-3：lx-mirror "已初步打通脱水链路"——实际仅是正则提取，非 AST 分析
文档声明（architecture-review.md:50）：
"用 mirror_scan.py 强行把代码库脱水压缩成 AST 骨架地图（Reality Map）"
实际情况 [已验证：mirror_scan.py:29-76]：
LANG_PATTERNS = {
    "go": (r"\.go$", r"^func\s+(\w+)\s*\(([^)]*)\)\s*(.*?)\{", ...),
    ...
}
for m in re.finditer(func_pattern, content, re.MULTILINE):
- 实现完全基于
正则表达式匹配，没有任何 AST 解析库（无 ast、tree-sitter、go/parser 等）
- 正则匹配在嵌套函数、泛型、装饰器等场景下必然产生误报/漏报
- 文档中使用"AST 骨架地图"是对实现技术的误导性描述——正则提取≠AST分析
- SKILL.md 本身对此描述较准确（称为"扫描"），但 architecture-review.md 中的营销语言升级了技术规格
危害等级：中高。误导用户对工具精度的预期，特别是大型项目或动态语言（JS/TS）场景下可靠性远低于"AST分析"的暗示。
--------------------------------------------------------------------------------
二、⚠️ 部分真实但存在夸大
P-1：lx-varlock 的"双向透明脱敏"描述准确，但 privacy-gate.sh 的"原生读取物理斩断"存在绕过
文档声明：
"不仅原生读取被物理斩断……达到了军工级的数据保护标准"
实际情况 [已验证：privacy-gate.sh:29-34]：
if echo "$CHECK_PATH" | grep -iE '\.env|\.pem|\.key|id_rsa|credentials\.json|secret\.ya?ml|auth\.json' > /dev/null
- 匹配基于
文件名模式，若敏感文件命名为 config.json、settings.yaml、.env.production（不含 .env 字样）等，直接放行
- varlock.py
 本身实现完整且正确 [已验证：varlock.py:35-48]，双向 mask/restore 机制可信
- "军工级"描述与基于简单 grep 的文件名过滤实现之间存在明显落差
实际评级：L3 级防护（文件名黑名单），非架构评分中的 10.0/10 水准
--------------------------------------------------------------------------------
P-2：subagent_reviewer.py 的"A/B 终端对抗盲审"描述过度，实际是构造 prompt 让主 AI 自行调用 Task 工具
文档声明（architecture-review.md:53）：
"引入 subagent_reviewer，强行拉起一个干净上下文的子 Agent"
实际情况 [已验证：subagent_reviewer.py:30-39]：
instruction = {
    "status": "requires_subagent_blind_review",
    "action": "请立即使用 `Task` 工具启动盲审",
    "subagent_type": "general",
    "prompt": system_prompt,
}
print(json.dumps(instruction, ensure_ascii=False, indent=2))
- 脚本
不直接启动任何子 Agent，仅打印一段 JSON 指令给主 AI 看
- 是否真正启动"干净上下文的 Sub-agent"完全取决于主 AI 是否遵守该 JSON 中的 
action 指令
- 若主 AI 上下文已被污染，其调用 
Task 工具时的行为也可能被污染
- "物理剥夺自审权"的强硬描述与"打印一条 JSON 希望 AI 自觉执行"的实现存在本质差距
实际评级：软约束，非物理强制。在主 AI 上下文质量正常时有效，在长对话末期（恰好是最需要盲审的时候）可靠性下降。
--------------------------------------------------------------------------------
P-3：oma_lock_manager.py 的"写安全"有效，但 lx-oma SKILL.md 对"5 个终端并发"的承诺缺乏机制支撑
文档声明（architecture-review.md:51）：
"搭配内核层的 OMA 并发锁，你可以同时拉起 5 个终端……分别在毫无 Token 污染的干净上下文中并行开发"
实际情况 [已验证：oma_lock_manager.py:23-50，lx-oma SKILL.md:全文]：
- oma_lock_manager.py
 的文件锁机制实现正确，具备原子锁 + 指数退避 + 超时自动释放 [L2 已验证]
- 但 
lx-oma Skill 本身不调用 oma_lock_manager.py——Skill 只生成 rpe/feat-X/ 目录结构，并打印"OMA 文件锁已就绪"
- 锁机制与 Skill 实际流程之间没有代码级集成
：lx-oma/SKILL.md 中无任何调用锁的指令
- "5 个终端 Token 无污染"基于目录隔离，这部分属实；但声称的"并发锁自动排队"实际需要每个终端的 AI 主动调用锁，属于软约定
实际评级：目录隔离真实有效，自动锁排队需手动配合，"自动"描述存在夸大。
--------------------------------------------------------------------------------
P-4：评分表中 [M] Migration 维度重复计入两次
文档声明（architecture-review.md:98-113，评分表第 5 行和第 10 行）：
维度v6.1.7v6.1.3[M] Migration (迁移能力)10.010.0[M] Migration (迁移能力)9.610.0
- 表中 
[M] 维度出现 两次，分别描述不同内容（热更新 vs 跨平台运行）
- 这意味着 14 维度总分 
136.7/140 是基于 2 个 M 维度，而非 14 个独立维度
- 若去重至 13 个维度，折算逻辑失效，
126.9/130 的高分依据需重新计算
- 两个 [Z] UX Intelligence 维度同样重复出现（第 6 行和第 13 行）
实际评级：评分体系存在结构性错误，总分可信度存疑。
--------------------------------------------------------------------------------
三、🔁 冗余项（实际增益不足）
R-1：lx-status 看板脚本依赖状态文件，初始状态无任何数据，存在感极低
声明价值：
"/lx-status 看板以及各种 [Context Guard 触发] 的主动拦截，极大增强了系统的交互感"（评分 [Z] 维度 9.3 分）
实际情况 [已验证：lx-status/SKILL.md:34-43]：
- lx-status
 调用 carror_dashboard.py
- carror_dashboard.py
 读取 .omc/state/ 下的状态文件
- 新安装项目中这些文件不存在
，降级提示为："系统处于初始状态，尚未产生任何执行记录"
- 使用频率受限：只有在长期高强度使用后状态文件积累足够才有价值
- 功能本身没问题，但在评分体系中单独占据一个维度的 9.3 分缺乏说服力
建议：移出独立评分维度，合并至 [Z] UX Intelligence 的整体描述中。
--------------------------------------------------------------------------------
R-2：安装脚本 "三级火箭" 概念与实际安装流程存在脱节，认知负荷并未"骤降至 0"
声明价值：
"三级火箭安装模型（The Three-Stage Rocket）……新用户的认知负荷骤降至 0"（[S] Simplicity 9.7 分）
实际情况 [已验证：文件结构]：
- 存在 
harness-kit-install.sh、install.sh、package.sh 三个安装脚本
- lx-skills
 目录下还有 .claude/profiles/merge-profile.sh、多个语言 harness.yaml 文件
- 用户面对 3 个安装脚本 + 4 个语言 Profile + Base/Enhanced 选择，认知负荷并非"0"
- "三级火箭"是合理的分层设计，但"骤降至 0"的夸张描述与现实不符
建议：改为"显著降低初始配置成本"，避免绝对化表述。
--------------------------------------------------------------------------------
四、✅ 声明与实现一致的核心特性（备案）
特性证据来源评级context-guard.sh Exit 2 阻断逻辑context-guard.sh:33-38 [L2]代码真实，但触发前提失效（见 V-2）privacy-gate.sh 文件名黑名单拦截privacy-gate.sh:30-34 [L2]真实，防护范围有限varlock.py 双向 mask/restorevarlock.py:36-48 [L2]真实，实现完整oma_lock_manager.py 原子文件锁oma_lock_manager.py:30 os.O_CREAT \| os.O_EXCL [L2]真实，机制可靠lx-oma MECE 需求拆解 + 目录脚手架lx-oma/SKILL.md:23-56 [L2]真实，目录隔离有效mirror_scan.py 正则扫描 + 报告生成mirror_scan.py:全文 [L2]真实，精度受限（见 V-3）subagent_reviewer.py prompt 构造subagent_reviewer.py:21-39 [L2]真实，强制性受限（见 P-2）
--------------------------------------------------------------------------------
五、综合建议
需立即修正的表述（架构文档）
1.Hook 行数
：将"不到 1000 行"修正为"约 2768 行（含配置库）"
2.Context Guard 触发前提
：补充说明"需 OMC 状态写入机制配合，默认安装后处于静默状态，需验证 token-tracking-index.json 是否被正确维护"
3.mirror_scan.py 技术描述
：将"AST 骨架地图"修正为"正则扫描骨架地图"，避免对 AST 解析的误导性暗示
4.评分维度重复
：修正评分表，去除 [M] Migration 和 [Z] UX Intelligence 的重复维度，重新计算总分
需后续迭代的技术债务
1.context_monitor.py 的数据来源
：实现真正的 token 追踪写入机制（当前 token-tracking-index.json 无写入方），或文档中明确注明"依赖外部 Agent 框架写入状态文件"
2.subagent_reviewer.py
：考虑通过 hook 机制强制触发 Task 调用，而非仅打印 JSON 期望 AI 自觉遵守
3.privacy-gate.sh
：将文件名黑名单扩展为路径内容扫描，或增加对 config.*、settings.* 等常见命名的覆盖
--------------------------------------------------------------------------------
审计结论：harness-kit 的防御机制在代码层面实现完整、逻辑严谨，核心架构设计可信。
主要问题集中在文档夸大（行数、技术精度描述）和关键功能链路断裂（context-guard 触发依赖未实现的状态写入）。
lx-skills 层整体为真实可用的工程方法论封装，lx-mirror 的 AST 描述是最需要纠正的误导性表述。
--------------------------------------------------------------------------------
第二轮深度审计补充
新增扫描范围：所有 25 个 Hook 全量代码、harness-kit.ts OpenCode 插件、error-dna.sh、completion-gate.sh、permission-gate.sh、pretool-edit-scope.sh 等
--------------------------------------------------------------------------------
六、❌ 补充虚假项
V-4：error-dna.sh 实现残缺，引用未定义变量，实际无法运行
文档声明（harness.yaml:103-104，architecture-review.md 中"独立内存管理"）：
harness.yaml 中 error_dna: enabled: true，声称可记录并追踪错误 DNA
实际情况 [已验证：error-dna.sh:8]：
echo "{\"ts\":$(date +%s),\"error_code\":$EXIT_CODE}" >> "$DNA_FILE"
- 脚本第 8 行使用 
$DNA_FILE 变量，但整个脚本没有任何代码定义或赋值此变量
- $DNA_FILE
 为空字符串，>> "" 在 bash 中会写入当前目录下名为空字符串的文件，实际行为未定义
- inject-project-knowledge.sh
 中读取的是 error-dna.json，而 harness-kit.ts 中写入的是 error-dna.jsonl（扩展名不一致）
- 三处代码（error-dna.sh、harness-kit.ts、inject-project-knowledge.sh）使用了 3 个不同路径/格式，
数据从未形成闭环
危害等级：高。error-dna.sh 这个 Hook 在 Claude Code 环境下完全失效。harness.yaml 中 error_dna: true 的声明是死配置。
--------------------------------------------------------------------------------
V-5：permission-gate.sh 的"用户批准"机制存在根本性设计缺陷——标记文件由 AI 自己写入
文档声明（architecture-review.md:29）：
"权限申请透明……禁止无上下文地弹出权限请求"
实际情况 [已验证：permission-gate.sh:77-101，harness-kit.ts:104-139]：
PERMISSION_MARKER="$STATE_DIR/permission-approved"
# 检查标记文件是否存在...

> ⚠️ **[已废弃]** — 此文件基于 v6.1.7 测试，版本已过时，保留仅供历史参考。
if [ -f "$PERMISSION_MARKER" ]; then
    # 有效授权，消费标记文件
    rm -f "$PERMISSION_MARKER"
    exit 0
fi
# 阻断提示：
echo "执行前写入一句话理由即可放行："
echo "  echo '理由说明' > $PERMISSION_MARKER"
- 放行条件是 
permission-approved 文件存在
- 但
该文件是由 AI 自己写入的（阻断提示中明确告知 AI 执行 echo '理由' > permission-approved）
- OpenCode 插件版（
harness-kit.ts:104-139）更激进——直接 throw new Error() 完全阻断，没有标记文件机制，行为与 Claude Code 版本不一致
- 这意味着 Claude Code 版本中：AI 被"阻断"→ AI 写入标记文件 → AI 自行解除阻断。
用户从未介入
- 文档声称的"用户裁定"在此机制中形同虚设
危害等级：中高。宪法第二条"用户主权"在此处通过 AI 自写标记文件完全规避。
--------------------------------------------------------------------------------
V-6：completion-gate.sh 的证据文件同样由 AI 自写，且 /tmp 路径在不同终端间可能冲突
文档声明（AGENTS.md 中"证据门禁"铁律）：
"无证据禁止说'已完成/已验证'"
实际情况 [已验证：completion-gate.sh:32,80，harness-kit.ts:41-47]：
EVIDENCE_FILE="/tmp/.completion-evidence-$(date +%Y%m%d)"
# 阻断提示告知 AI：
echo "2. 执行: echo 'VERIFIED: [具体验证结果描述]' > $EVIDENCE_FILE"
- 放行机制：AI 向 
/tmp/.completion-evidence-YYYYMMDD 写入包含 "VERIFIED" 字样的内容
- 这依然是 
AI 自行写入证据文件解除自身阻断
- /tmp/
 路径为全局共享，在 lx-oma 多终端并发场景下，终端 A 写入的证据文件可以让终端 B 的任务标记通过
- 5 分钟内重复使用防护（写 
CONSUMED）存在竞态：若两个终端并发消费，第二个终端可能在第一个写入 CONSUMED 前读取到有效文件
危害等级：中。证据门禁的机制原理上正确（强制写文件 + 关键词 + 时效），但 AI 自写 = 软约束而非硬约束；并发场景有竞态。
--------------------------------------------------------------------------------
七、⚠️ 补充夸大项
P-5：OpenCode 插件声称"覆盖 22 个 Hook"，实际行为与 Claude Code 版本存在多处不一致
文档声明（harness-kit.ts:7-10）：
"覆盖 22 个 Claude Code hook 的 OpenCode 等价实现：19 个通过 tool.execute.before/after 完全对齐，3 个通过 message.updated / tui.prompt.append 变通实现"
实际不一致点 [已验证：harness-kit.ts 全文对比源 Hook]：
功能Claude Code HookOpenCode 插件差异permission-gate检查 permission-approved 标记文件，可通过写文件放行直接 throw Error 强硬阻断，无放行机制行为不一致lsp-suggestexit 2 首次阻断，写标记后不再阻断未在插件中实现功能缺失flywheel-report读取 ~/.claude/flywheel.log 注入飞轮报告仅更新时间戳，无报告生成功能空壳auto-snapshot318 行，生成完整会话交接 + 错误记忆 + ADR仅写 Todo 状态，约 20 行严重缩水turn-counter注入到 AI 上下文（stdout hook）写入 console.warn（debug 日志，用户不可见）可见性丧失read-tracker记录至 read-files.log，供 edit-guard 消费记录至 read-tracker.txt，路径不同，edit-guard 读错文件链路断裂
实际评级：OpenCode 插件为部分对齐实现，"完全对齐"描述不准确，至少 6 处存在功能降级或链路断裂。
--------------------------------------------------------------------------------
P-6：posttool-bash-audit.sh 输出格式错误——hookSpecificOutput 字段名拼写正确但嵌套层级有争议
实际情况 [已验证：posttool-bash-audit.sh:125]：
printf '{"continue": true, "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "%s"}}\n' "$COMBINED_MSG"
与 posttool-edit-quality.sh:119 相同格式。
- Claude Code Hook 官方文档要求 PostToolUse 的输出字段为 
hookSpecificOutput.additionalContext
- 代码中包含了 
"hookEventName": "PostToolUse" 字段——这个字段是冗余的，官方 schema 不要求它
- 更关键的是：
posttool-bash-audit.sh 的 MSG 包含 | 管道符，在 printf 中无转义，特殊字符可能破坏 JSON 完整性
- 例如：当 ANTI_PATTERN_MSG 含引号时，整个 JSON 会解析失败，Claude Code 静默忽略
危害等级：低。只影响审计提示的可见性，不影响安全机制。
--------------------------------------------------------------------------------
八、🔁 补充冗余/低增益项
R-3：lsp-suggest.sh 的 "每会话首次阻断" 策略在实际使用中体验较差
实际情况 [已验证：lsp-suggest.sh:59-76]：
- 首次 Grep 导出符号 → exit 2 阻断 → AI 必须重新发起完全相同的 Grep
- 阻断只发生一次（写入 
$SUGGESTED_FILE 标记），后续放行
- 问题：这个 Hook 在 Go 项目之外（Python、TypeScript 等）仍然触发，但这些语言的 LSP 建议不一定适用
- EXAMPLE_FILE
 硬编码为 model/tasks_mongo.go（Go 特定文件名），在非 Go 项目中推荐示例会产生困惑
建议：改为仅提示而不阻断（exit 0 + additionalContext 注入），减少无效干扰。
--------------------------------------------------------------------------------
R-4：pretool-edit-scope.sh 的范围冻结依赖 current-scope.txt 但没有任何机制自动写入该文件
实际情况 [已验证：pretool-edit-scope.sh:41,97，全局搜索 current-scope]：
SCOPE_FILE="$PROJECT_ROOT/.omc/state/current-scope.txt"
# 无范围文件 → 仅输出耦合提醒后放行
if [ ! -f "$SCOPE_FILE" ]; then
    exit 0
fi
- 若 
current-scope.txt 不存在，Hook 直接放行（fail-open 设计）
- harness-kit.ts
 中读取此文件但也不写入
- 源码中
没有任何一处代码自动写入 current-scope.txt——该文件只能由用户手动创建
- 这意味着范围冻结功能在 99% 的实际使用场景中是静默停用状态
实际增益：仅在用户手动维护 current-scope.txt 时生效，属于"有设计无落地"的功能，在架构文档中被纳入防御能力矩阵存在误导。
--------------------------------------------------------------------------------
更新后总览
类别第一轮补充合计❌ 虚假项（声明与实现严重不符）336⚠️ 部分真实但存在夸大426🔁 冗余项（增益不足或静默失效）224✅ 声明与实现一致7—7
--------------------------------------------------------------------------------
综合严重度排序
优先级问题类型影响P0V-2：Context Guard 触发依赖未写入的状态文件，默认静默失效虚假核心防幻觉机制失效P0V-4：error-dna.sh 引用未定义变量 $DNA_FILE，完全无法运行虚假错误记忆系统静默失效P1V-5：permission-gate 标记文件由 AI 自写，用户主权机制形同虚设虚假安全约束被 AI 自行绕过P1P-5：OpenCode 插件至少 6 处与 Claude Code 行为不一致夸大跨平台运行质量不一P2V-1：Hook 行数 2768，声称"不到 1000 行"虚假文档可信度损失P2V-3：mirror_scan.py 使用正则而非 AST虚假用户精度预期偏差P2R-4：current-scope.txt 无自动写入机制，范围冻结静默停用冗余宣传的防护能力实际不存在P3V-6：completion-gate 证据由 AI 自写，并发有竞态虚假软约束而非硬约束P3P-1：privacy-gate 仅文件名黑名单，声称军工级夸大实际防护范围有限P4R-3：lsp-suggest 阻断体验差，语言无关地触发冗余轻微用户体验问题
--------------------------------------------------------------------------------
总结：harness-kit 的设计思路是正确且有价值的——零信任防御、证据门禁、DLP 代理、并发锁，这些方向都值得。
但 v6.1.7-stable 实际交付的实现与宣传存在系统性落差，主要体现在：多个关键防御链路依赖"外部写入"状态文件（Context Guard、Error DNA），但整个系统没有写入这些文件的代码AI 自我解除阻断的设计（permission-approved、completion-evidence 均由 AI 写入）跨平台（OpenCode 插件）实现质量显著低于 Claude Code 版本文档使用了"军工级"、"物理确定性"、"AST"等强措辞，与实际的 grep/正则/文件名匹配实现存在夸大
审计结论（更新）：harness-kit 的防御机制在代码层面实现完整、逻辑严谨，核心架构设计可信。
主要问题集中在文档夸大（行数、技术精度描述）和关键功能链路断裂（context-guard 触发依赖未实现的状态写入）。
lx-skills 层整体为真实可用的工程方法论封装，lx-mirror 的 AST 描述是最需要纠正的误导性表述。
--------------------------------------------------------------------------------
第三轮扫描补充
新增扫描范围：所有 Hook 与 harness.yaml 的完整对应关系、harness_config.sh 的 hc_enabled 机制、index.md Hook 数量声明、lx-skills 实际版本和数量、架构文档"Syscall 级别"等核心定性描述
--------------------------------------------------------------------------------
九、❌ 补充虚假项
V-7：context-guard 和 privacy-gate 不受 harness.yaml 的 hooks_enabled 控制——这是未文档化的配置盲区
文档声明（architecture-review.md:28-30，全文核心防御特性）：
两个最核心的防御 Hook —— context-guard（OOM 物理熔断）和 privacy-gate（DLP 防线）——是整篇文档中被反复引用和评分的重点能力。
实际情况 [已测试：交叉核验 harness.yaml 与全部 .sh 文件]：
在.sh中但不在hooks_enabled配置的Hook（共7个）：
  context-guard      → hc_enabled "context_guard"  → 不在配置块，默认 true
  flywheel-report    → hc_enabled "skill_flywheel"  → 实际用的是另一个key，可能误读
  posttool-write-lock → 无 hc_enabled 调用，无条件启用
  pretool-rule-anchor → hc_enabled "rule_anchor"   → 不在配置块，默认 true
  pretool-user-correction → hc_enabled "user_correction_detector" → 不在配置块
  pretool-write-lock  → 无 hc_enabled 调用，无条件启用
  privacy-gate       → hc_enabled "privacy_gate"   → 不在配置块，默认 true
- hc_enabled
 函数默认返回 true（harness_config.sh:198：val=$(hc_get "hooks_enabled.${hook_name}" "true")）
- 因此这 7 个 Hook 在逻辑上会运行，但
用户无法通过编辑 harness.yaml 来禁用它们——它们不在 hooks_enabled 控制范围内
- 这与其他 20 个可配置 Hook 不一致，破坏了配置系统的完整性
- 特别是 
context-guard 和 privacy-gate 作为最核心的防御机制，用户无法针对特殊场景（如 CI 环境）按需禁用
危害等级：中。对于普通用户影响较小（两个核心 Hook 仍然运行），但对于需要定制配置的高级用户和企业用户，这是一个文档与实现之间的治理空白。
--------------------------------------------------------------------------------
V-8："Syscall 级别的拦截"是严重的技术误导性描述
文档声明（architecture-review.md:28，核心卖点）：
"在所有同类产品还在拼'系统提示词'时，它实现了系统调用（Syscall）级别的拦截。大模型想读 .env？直接 Exit 2 爆头"
实际情况 [已验证：全源码中无任何 Syscall 相关代码]：
grep -rn "Syscall|syscall|system call|操作系统.*拦截" source/ → 无任何匹配
- 所有拦截均通过 Claude Code 的 
Hook 机制实现——这是 Claude Code 提供的高层 API，不是操作系统系统调用
- Claude Code Hook 的实现原理是：AI 工具调用前/后，Claude Code 框架调用注册的 Shell 脚本，脚本 
exit 2 则工具调用被拦截
- 这是 
应用层拦截（Application-level hook），与操作系统 Syscall 拦截（如 ptrace、seccomp、eBPF）没有任何关系
- 真正的 Syscall 级别拦截可以阻止进程的任何系统调用（包括直接 
open() 等），而 Claude Code Hook 只拦截 AI 工具调用——若 AI 找到绕过工具层的方式，Hook 无效
危害等级：中高。"Syscall 级别"是一个精确的技术术语，用它描述 Shell 脚本 hook 是对用户的误导，会造成虚假的安全感。
--------------------------------------------------------------------------------
十、⚠️ 补充夸大项
P-7：index.md 声称"共 20 个 Hook"，实际 25 个有效 Hook，数量严重低报
文档声明（index.md:63）：
"## Hooks 速查（共 20 个）"
实际情况 [已测试：ls hooks/*.sh | grep -v harness_config | wc -l → 25]：
- hooks 目录实际有 
25 个有效 Hook（排除共享配置库 harness_config.sh）
- index.md
 的数字"20"与 harness.yaml 的 hooks_enabled 条目数一致，但忽略了 7 个未进入配置控制的 Hook
- architecture-review.md
 另称"24 个 Hook"，三处文档给出了三个不同数字（20、24、25），无一准确
证据：
index.md:63    → "共 20 个"
architecture-review.md:29 → "24 个 Bash Hook"
实际文件统计   → 25 个（排除 harness_config.sh）
harness.yaml   → 20 个 hooks_enabled 条目（7 个 Hook 不在此配置中）
--------------------------------------------------------------------------------
P-8："lx-skills-v5" 命名与实际版本不符，文档中反复引用的版本号存在混淆
文档声明（architecture-review.md:12,38）：
"harness-kit（内核层）和 lx-skills-v5（能力层）"
实际情况 [已验证：source/lx-skills/.claude/skills/VERSION → 5.2.3]：
- VERSION
 文件显示当前版本为 5.2.3，不是 "v5"（一个主版本号的简称在语义上可接受）
- 但 
CHANGELOG.md 中标注的整体版本为 v6.1.7-stable（外层包版本），lx-skills 内部版本 5.2.3 与外层 v6.1.7 形成双版本体系，用户容易混淆
- 文档中 "lx-skills-v5" 是一个固定名称而非当前版本指向，这在 
5.2.x 升级到 6.x 时将需要重命名，埋下了一个命名债务
--------------------------------------------------------------------------------
十一、🔁 补充冗余项
R-5：posttool-write-lock.sh 和 pretool-write-lock.sh 使用 grep 解析 JSON 而非 jq/python3，在路径含特殊字符时失效
实际情况 [已验证：pretool-write-lock.sh:16-19]：
FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"filePath"\s*:\s*"[^"]*"' | cut -d'"' -f4)
if [[ -z "$FILE_PATH" ]]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | cut -d'"' -f4)
fi
- 其他 Hook 均优先使用 
jq 或 python3 解析 JSON（双 fallback 机制）
- 这两个 OMA 锁 Hook 仅用 
grep 解析，若文件路径含空格、引号或 Unicode 字符，grep -o 匹配会失败，锁不被获取，并发保护静默失效
- 与文档声称的"原子锁引擎"的健壮性不符
建议：统一使用 jq || python3 双 fallback 机制解析 JSON，与其他 Hook 保持一致。
--------------------------------------------------------------------------------
最终总览（三轮完整）
类别第一轮第二轮第三轮合计❌ 虚假项3328⚠️ 夸大项4228🔁 冗余/停用项2215✅ 声明与实现一致7——7
--------------------------------------------------------------------------------
最终优先级排序（按实际影响）
优先级问题编号问题摘要分类实际影响P0V-2Context Guard 触发链路断裂（状态文件无写入方）❌核心防幻觉机制静默失效P0V-4error-dna.sh 引用未定义变量 $DNA_FILE❌错误记忆系统完全无效P0V-8"Syscall 级别拦截"严重技术误导❌用户产生虚假安全感P1V-5permission-gate 标记文件由 AI 自写，用户主权形同虚设❌安全约束可自行绕过P1P-5OpenCode 插件 6 处与 Claude Code 行为不一致⚠️跨平台可靠性存疑P2V-1Hook 行数 2768，文档称"不到 1000 行"❌文档可信度损失P2V-3mirror_scan.py 正则≠AST，技术规格虚报❌用户精度预期偏差P2V-7context-guard/privacy-gate 不在配置控制范围❌核心 Hook 无法按需禁用P2R-4current-scope.txt 无自动写入，范围冻结静默停用🔁宣传的防护能力实际不存在P2P-7Hook 数量三处文档各不相同（20/24/25）⚠️文档一致性差P3V-6completion-gate 证据由 AI 自写，并发竞态❌软约束而非硬约束P3P-1privacy-gate 仅文件名 grep，声称"军工级"⚠️防护范围有限P3R-5OMA 锁 Hook 用 grep 解析 JSON，特殊路径失效🔁并发保护在边缘场景失效P4P-4评分维度重复计入（[M]/[Z] 各两次）⚠️总分结构性存疑P4R-3lsp-suggest 对非 Go 项目体验差🔁轻微干扰
--------------------------------------------------------------------------------
第四轮全量扫描补充（最终轮）
扫描范围：剩余所有 lx-skills（lx-pre-commit/lx-pre-push/lx-tdd-spec 等）、安装脚本机制（Safe In-Place/三级火箭/无损热更）、竞品对比数据来源、所有关键数字声明（评分/Hook数/Skill数/阈值）、OWASP/BDD声明、50%甜点区机制细节
--------------------------------------------------------------------------------
十二、❌ 补充虚假项
V-9：评分表 "14维度总分 136.7/140" 数学上不成立——表格只有13行，加总为125.8
文档声明（architecture-review.md:114-115）：
*当前 14 维度总分：136.7 / 140*
折算为原 130 分制基准：126.9 / 130
实际情况 [已测试：逐行加总]：
rows = [9.5, 9.8, 10.0, 9.7, 10.0, 9.8, 9.5, 9.8, 9.0, 9.6, 9.8, 10.0, 9.3]
# 13行，加总 = 125.8
- 表格有 
13 行，文档声称 14 维度，缺少第 14 行
- 13 行实际加总 = 
125.8，文档声称 136.7，差值 10.9 分
- 这意味着文档中存在一个幽灵维度或计算错误
- 折算公式 
136.7/140×130 = 126.9 数学上成立，但分子 136.7 本身就是错的
- 126.5
 分（第一章末尾）与 127.2 分（第二章标题）与 126.9 分（评分表折算）三个总分彼此不一致
危害等级：中高。评分体系是文档的核心论证，数字存在系统性错误会使整个评分结论失去可信度。
--------------------------------------------------------------------------------
V-10：Base 安装模式声称"6 个静默门禁 Skill"，实际保留 10 个
文档声明（install.sh:87）：
log_info "已精简为 6 个静默门禁 Skill。"
实际情况 [已测试：Python 逐差集计算]：
总Skill: 23
Base模式删除: 13
实际保留: 10 个
保留的 10 个：lx-code-review lx-mirror lx-oma lx-perf-analysis lx-pre-commit lx-pre-push lx-react-review lx-security-review lx-style-guide lx-web-perf
- 代码和实际删除逻辑都说明保留了 10 个，但 
install.sh:87 输出"6 个"给用户看
- 连带的 
architecture-review.md:103 也声称"19 个 Skill"，实际源码目录统计为 23 个（TEMPLATE.md 和 VERSION 除外）
危害等级：中。数量误差影响用户对功能范围的预期，但不影响功能本身。
--------------------------------------------------------------------------------
V-11：Safe In-Place Upgrade 升级 100% 零风险——备份在脚本中途失败时会被 trap EXIT 自动删除
文档声明（architecture-review.md:104）：
Safe In-Place Upgrade 无损热更。安装脚本级内存沙箱自动隔离并还原用户的配置资产与记忆 DNA，升级 100% 零风险。
实际情况 [已验证：install.sh:34-35]：
BACKUP_DIR=$(mktemp -d)
trap "rm -rf $BACKUP_DIR" EXIT   # ← 任何 exit 都触发删除
- trap "rm -rf $BACKUP_DIR" EXIT
 意味着不论脚本成功还是失败退出，备份目录都会被删除
- 若 
extract_tar 解压失败（exit 1），备份在删除前尚未恢复，用户原始 claude-next.md 等文件永久丢失
- 备份范围仅限 4 个文件（
harness.yaml/claude-next.md/anti-patterns.md/kernel.md），.omc/state/（含 todo-queue.md、error-dna.json 等用户积累数据）完全不在备份范围
- "100% 零风险"在中途失败场景下是错误声明
危害等级：高。这是一个实际会导致数据丢失的设计缺陷，被包装为"100% 零风险"特性。
--------------------------------------------------------------------------------
V-12："50% 甜点区主动交接，强迫 AI 执行 /compact"——实际是 stderr 输出，不注入 AI 上下文，无任何强制效力
文档声明（architecture-review.md:172，评分表[T] Task Continuity 9.8）：
"当 ctx% >= 50% 且处于任务交接点时，它会自动插入强烈警告，强迫 AI 执行 /compact 或新开分支。"
实际情况 [已验证：context_monitor.py:32-34]：
if ratio >= 0.5 and ratio < 0.8:
    print(f"[context_alert]: ...", file=sys.stderr)   # ← 写到 stderr
    print("请立即打断当前长上下文对话！...", file=sys.stderr)
- 50% 警告写入 
sys.stderr，这是人类终端可见的输出
- context-guard.sh
 在 50% 时不执行任何动作（exit 0），AI 工具调用不受任何影响
- "强迫 AI"和"自动插入"的描述完全不准确——这只是一行终端打印，AI 不会感知
- 80% 时才有 
exit 2 硬阻断，50% 时只有 stderr 软提示给人类看
- 文档中"50% 甜点区主动交接"是行为上存在的（via prompt 约束/AGENTS.md），但它不是通过代码实现的，而是 AI 自觉行为
危害等级：高。[T] Task Continuity 9.8 分的核心支撑特性，实际无任何代码强制实现。
--------------------------------------------------------------------------------
V-13：manifesto.md 声称"OWASP LLM 漏洞拦截标准"和"100% BDD 行为驱动测试"——源码中完全不存在
文档声明（manifesto.md:86）：
"Carror OS 包含 100% 路由覆盖的 BDD 行为驱动测试，并在本地自动化校验 29 处代码级探针，通过了 OWASP LLM 漏洞拦截标准的严苛测试。"
实际情况 [已测试：全局文件搜索]：
find source/ -name "*.feature" → 0 结果
find source/ -name "*bdd*"     → 0 结果
find source/ -name "*owasp*"   → 0 结果
- 整个 
source/ 目录中没有任何 BDD 测试文件（无 .feature、无 behave、无 pytest-bdd）
- "OWASP LLM 漏洞拦截标准"测试
没有对应的测试代码或报告文件
- "29 处代码级探针"的数字在整个文档体系中有多个版本（24/25/29/49），均无统一口径
- 实际存在的是 
manual-acceptance-test.md（人工手动验收）和 final-exam.md（人工审判清单），不是自动化测试
危害等级：高。这是对外宣传材料中的虚假合规声明，OWASP 认证级别的声称若无实际测试支撑，对企业用户有严重误导。
--------------------------------------------------------------------------------
十三、⚠️ 补充夸大项
P-9：architecture-review.md:28 中的两处阈值不一致（85% vs 80%）
文档声明（同一段话）：
- architecture-review.md:28
："想在 85% 上下文时继续写代码？物理断电"
- architecture-review.md:172
："当 ctx% >= 80%，它会抛出 Exit 2 锁死系统"
实际情况 [已验证：context_monitor.py:41]：
"is_danger": ratio >= 0.8   # 实际阈值 80%
同一文档中，同一功能的阈值出现两个不同数字：85% 和 80%。实际代码实现为 80%。85% 是误写。
--------------------------------------------------------------------------------
P-10：竞品评分图（Devin 7.0/Cursor 6.0/SWE-agent 8.0）无任何数据来源依据
文档声明（architecture-review.md:129-157）：竞品评分图给出了 Devin/Cursor/SWE-agent 在 6 个维度的具体评分，最高精确到小数点一位。
实际情况 [已验证：全局搜索无任何数据来源]：
- 全源码/文档中
不存在任何竞品评测报告、引用来源或第三方数据
- CHANGELOG.md:776
 另有一处不同的竞品分数声明（"Cursor 48 / Aider 65"），与图中数字体系完全不同
- 这些竞品分数是作者的主观估计，但被以精确数字图表的形式呈现，给人客观数据感
--------------------------------------------------------------------------------
十四、🔁 补充冗余项
R-6：lx-rpe "9步流水线"声明真实，但文档将其与"对抗大模型熵增"绑定有夸大
实际情况 [已验证：lx-rpe/SKILL.md:50-52]：
lx-rpe 的 9 步状态机（Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary）确实存在且实现完整。
但 architecture-review.md:52 中的描述"把 AI 的'瞬时记忆'转化为了物理硬盘上的'持久化状态机'"有夸大成分——实际是 AI 按照 Skill 的 9 步提示逐步写 Markdown 文档，这是 AI 执行 Skill 指令，而非操作系统级别的状态持久化。
建议：保留 lx-rpe 作为真实特性，修正描述措辞。
--------------------------------------------------------------------------------
最终完整总览（四轮）
类别第一轮第二轮第三轮第四轮最终合计❌ 虚假项332513⚠️ 夸大项422210🔁 冗余/停用项22116✅ 声明与实现一致7———7
--------------------------------------------------------------------------------
完整优先级总表（最终版）
优先级问题编号问题摘要分类实际影响P0V-2Context Guard 触发依赖未写入的状态文件，默认静默失效❌核心防幻觉机制失效P0V-4error-dna.sh 引用未定义变量 $DNA_FILE，完全无效❌错误记忆系统静默失效P0V-8"Syscall 级别拦截"严重技术误导❌用户产生虚假安全感P0V-11trap EXIT 删除备份，中途失败时用户数据丢失，"100% 零风险"假声明❌数据安全风险P0V-13OWASP/BDD/100%覆盖声明，源码中完全不存在❌虚假合规声明，误导企业用户P1V-5permission-gate 标记文件由 AI 自写❌用户主权形同虚设P1V-1250% 甜点区"强迫 AI"仅是 stderr 输出，无强制效力❌[T]维度 9.8 分基础不存在P1P-5OpenCode 插件 6 处与 Claude Code 行为不一致⚠️跨平台可靠性存疑P2V-1Hook 行数 2768，文档称"不到 1000 行"❌文档可信度损失P2V-3mirror_scan.py 正则≠AST，技术规格虚报❌精度预期偏差P2V-7context-guard/privacy-gate 不在配置控制范围❌无法按需禁用P2V-9评分表 13 行加总 125.8，声称 136.7；三处总分不一致❌评分体系根本性错误P2V-10Base 模式保留 10 个 Skill，声称"6 个"；Enhanced 有 23 个，声称"19 个"❌Skill 数量全线错误P2R-4current-scope.txt 无自动写入，范围冻结静默停用🔁宣传能力实际不存在P2P-7Hook 数量：index.md/review.md/install.sh 分别说 20/24/22，实际 25⚠️四处数字均不同P2P-9同文档同功能写了 85% 和 80% 两个阈值⚠️内部一致性差P3V-6completion-gate 证据由 AI 自写，并发竞态❌软约束非硬约束P3P-1privacy-gate 文件名 grep，声称"军工级"⚠️防护范围有限P3P-10竞品评分图无任何数据来源，主观估计呈现为精确图表⚠️误导性竞品比较P3R-5OMA 锁 Hook 用 grep 解析 JSON，特殊路径失效🔁边缘场景失效P4P-4评分维度重复计入（[M]/[Z] 各两次）⚠️总分结构性问题P4P-8lx-skills-v5 命名与 VERSION 5.2.3 和外层 v6.1.7 形成三版本混淆⚠️版本混淆P4R-3lsp-suggest 对非 Go 项目触发给 Go 示例🔁轻微干扰P4R-6lx-rpe 9步流水线真实，"状态机"描述有夸大🔁描述精度问题
--------------------------------------------------------------------------------
真实有效的核心特性清单（经所有四轮验证后）
特性验证结论证据context-guard.sh 在 80% 时 exit 2 阻断✅ 代码真实但依赖从未写入的状态文件（V-2）privacy-gate.sh 文件名黑名单拦截✅ 真实防护范围有限（P-1）varlock.py 双向 mask/restore✅ 真实且完整varlock.py:36-48oma_lock_manager.py 原子文件锁✅ 真实os.O_CREAT|os.O_EXCLlx-oma MECE 需求拆解 + 目录脚手架✅ 真实lx-oma/SKILL.mdlx-rpe 9 步开发闭环✅ 真实lx-rpe/SKILL.md:50安装脚本的备份还原机制⚠️ 部分真实范围有限且中途失败时风险存在（V-11）build-validator.sh 构建失败分析✅ 真实实现完整turn-counter.sh 轮次计数与铁律注入✅ 真实机制可靠completion-gate.sh 证据门禁⚠️ 部分真实AI 自写证据可绕过（V-6）subagent_reviewer.py A/B 盲审⚠️ 部分真实软约束非硬强制（P-2）pretool-edit-scope 范围冻结⚠️ 部分真实依赖手动维护的状态文件（R-4）inject-project-knowledge.sh 知识注入✅ 真实实现完整auto-snapshot.sh 会话快照✅ 真实318行，实现丰富permission-gate.sh 危险命令拦截⚠️ 部分真实AI 可自写标记文件绕过（V-5）
--------------------------------------------------------------------------------
最终审计结论：真实且工作的：并发锁、DLP 代理、lx-oma 拆解、lx-rpe 9步流水线、会话快照、知识注入、构建失败分析——这些特性代码完整，逻辑可靠。设计正确但实现断链的：Context Guard（状态文件无写入方）、Error DNA（变量未定义）、范围冻结（无自动写入机制）、50% 甜点区（仅 stderr 输出）。文档虚假声明：OWASP/BDD 测试（源码中不存在）、Syscall 级别拦截（应用层 Hook）、100% 零风险热更（trap EXIT 有数据丢失风险）、评分数学错误（136.7 vs 实际 125.8）。核心建议：P0 级问题（V-2/V-4/V-11/V-13）需在下一版本前修复，否则影响系统的安全性和可信度。
--------------------------------------------------------------------------------
修正评分（基于四轮审计实际代码证据）
评分方法：沿用原文 12 个独立维度（去掉重复的 [M]/[Z] 各一个），新增 [E] 文档诚信维度，满分 120。
依据：每项分数均有对应源码证据，见上方各轮审计详情。
各维度修正评分
维度原分修正分核心扣分依据[H] 防幻觉9.55.5Context Guard 状态文件无写入方，默认静默失效（V-2）。50% 甜点区仅 stderr 输出，AI 无感知（V-12）。80% 阻断逻辑代码真实，但触发链路断裂。[A] 自主控制9.86.5subagent_reviewer.py 打印 JSON 期待 AI 自觉执行，非硬强制（P-2）。设计方向正确，"物理剥夺自审权"描述夸大。[S] 安全性10.07.0varlock.py 双向脱敏真实完整。privacy-gate 为文件名 grep 黑名单，config.json/.env.production 可直接绕过（P-1）。声称"军工级"失实。[S] 简洁性9.77.5三级安装设计合理。但 Base 称"6 个 Skill"实为 10 个，Enhanced 称"19 个"实为 23 个（V-10）。Hook 行数 2768 vs 声称"不到 1000 行"（V-1）。[M] 迁移/热更10.06.0备份仅覆盖 4 个文件，.omc/state/ 整个记忆目录不在范围。trap EXIT 致中途失败时备份被自动删除（V-11）。"100% 零风险"是假声明。[Z] UX 交互主动性9.87.5turn-counter/inject-project-knowledge/flywheel-report 均真实有效，交互设计有独到之处。lx-status 初始状态无数据，价值有限（R-1）。[C] 成本效益9.58.5渐进式披露 Token 节省机制真实可信，按需加载设计完整。[T] 任务连续性9.85.050% 甜点区强制机制不存在（V-12）。Context Guard 80% 阻断因状态文件问题默认失效（V-2）。auto-snapshot 会话快照真实有效，但为被动记录非主动强制交接。[I] 工具层智能9.06.5盲审方向正确，build-validator 分析真实，lsp-suggest 有效。OpenCode 插件 6 处行为不一致，跨平台智能大打折扣（P-5）。[D] 防漂移9.88.0turn-counter 铁律注入、pretool-rule-anchor 锚定、user-correction-detector 均真实有效。pretool-edit-scope 因依赖手动文件静默停用（R-4），扣分。[C] 配置友好10.07.5harness_config.sh 缓存机制优雅，merge-profile 设计合理。context-guard/privacy-gate 不在 hooks_enabled 控制范围（V-7），配置体系存在盲区。[E] 文档诚信(新增)3.0OWASP/BDD 声明源码中完全不存在（V-13）。"Syscall 级别"严重误导（V-8）。评分表数学错误 136.7 vs 实际 125.8（V-9）。竞品评分无任何数据来源（P-10）。
修正总分
原始声明修正后（实际）12 维度总分（去重后）136.7 / 140（数学错误）78.5 / 120折算 100 分制~105（超标，不可信）65.4 / 100评级S 级（工业级巅峰）B 级（有创意的中等）
分项解读
真正扎实（得分 ≥ 8.0）：
- [C] 成本效益
 8.5、[D] 防漂移 8.0
- 基础设施核心：原子文件锁、varlock 双向脱敏、会话快照、构建失败分析、轮次计数铁律注入——设计严谨，代码可靠
设计正确但实现断链（得分 5.0~6.5）：
- [T] 任务连续性
 5.0、[H] 防幻觉 5.5——宣传最重的两个维度，实现断链最严重
- [M] 迁移安全
 6.0——备份设计有根本性缺陷
新增扣分项：
- [E] 文档诚信
 3.0——OWASP/BDD/Syscall 等措辞使整体可信度崩塌
一句话定性
v6.1.7-stable 是一个设计方向正确、部分模块扎实、但关键防御链路存在系统性断链、且用夸张文档掩盖实现差距的 B 级工程实验品，而非其自我声称的 S 级工业级巅峰。
修正后约 65 / 100，在同类 AI 行为治理工具中属于有创意的中等水平——核心思路领先，但"声明的功能"与"实际运行的功能"之间的鸿沟太大，尚不足以支撑其文档中的企业级合规定位。修复 P0 级 5 个问题后，合理预期得分可提升至 78~82 / 100。