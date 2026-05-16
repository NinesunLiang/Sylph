# claude-next.md — AI 学习笔记

> >
> **这份文件是你的私有财产，也是开源社区的精神载体。**
>
> 下面的 22 条"种子教训"来自 Carror OS 自身的狗粮开发——每一条背后都是一次真实的生产事故。
> 它们不是理论，是踩过的坑、烧过的眉毛、差点酿成大祸的瞬间。
>
> **越用越强**：每次 `/lx-dogfood "踩坑经历"` 会在文末自动追加你的专属教训。
> **越分享越强**：觉得某条教训对别人也有用？带上原文去论坛发帖。Carror OS 维护者
> 会从中挑选高价值内容，升华为新的种子或铁律机制。下次 release，所有人自动获得——
> 你的踩坑经验，成了别人的护身符。
>
> 这就是 Carror OS 的开源学习精神：**代码开源，教训也开源。**

---

## 🌱 集体智慧种子（22 条通用教训）

> 以下教训来自 Carror OS 自身的狗粮开发。它们不是理论——每条背后都是一次真实的生产事故。

### 🔴 安全

#### [SEED-01] permission-gate 的命令提取可能静默失败

触发条件：AI 执行多行 heredoc 命令（如 `git commit -m "$(cat <<'EOF'...)"`），jq 提取命令返回空字符串
正确行为：安全门禁使用 **fail-closed** 设计——命令提取失败时应**阻断**而非放行。`[ -z "$COMMAND" ] → exit 2`，不是 `exit 0`
证据：Meta-Oracle 审计 2026-05-16 — 一次未授权的 git commit 绕过整个 permission gate

#### [SEED-02] 编码绕过可以穿透所有文本正则

触发条件：AI 使用 `echo "base64内容" | base64 -d | bash` 执行命令，所有 7 个文本级危险命令 regex 无法匹配 base64 编码后的内容
正确行为：必须独立检测编码绕过模式（`base64 -d | sh`、`xxd -r | bash`、`printf %b`、`eval $(echo ...)`），编码绕过本身即为高危信号
证据：DG-11 狗粮记录 — base64 管道成功绕过 permission-gate 所有检测

#### [SEED-03] AI 修复 bug 会引入更危险的 regression

触发条件：AI 修复了一个安全函数中的注入漏洞，重构时忘记添加 `sys.exit()`，导致所有危险命令自动放行
正确行为：安全函数修复后必须经过独立 agent 重审，不能自证"修好了"
证据：Meta-Oracle 审计 — check_cache 从"有注入"变成"永远返回 success"

#### [SEED-04] 静态分析 ≠ 运行时验证 — 严重性需要实弹测试校准

触发条件：Oracle 静态审查判"Python 字符串注入 → CRITICAL"，但实际运行时验证发现注入导致 fail-closed（更安全而非更宽松）
正确行为：安全审查的严重性判定必须经过实际执行验证。fail-closed 的 bug 不是安全漏洞
证据：Meta-Oracle 二审 — C2 从 CRITICAL 降级为 MAJOR

#### [SEED-05] `grep -c || echo 0` 是 bash 中最隐蔽的静默失败

触发条件：`VAR=$(grep -c pattern || echo 0)` — grep 输出 "0" 并 exit 1，`|| echo 0` 追加第二个 "0"。变量变成两行，`[ "$VAR" -eq 0 ]` 失败，检测静默跳过
正确行为：`VAR=$(grep -c pattern 2>/dev/null); VAR="${VAR:-0}"` — `$()` 已捕获 grep 的 "0" 输出
证据：DG-36 — claim-audit G1 伪诚信检测在 0 匹配时从不触发

### 🟡 机制设计

#### [SEED-06] ghost/goal 模式下所有 gate 静默失效

触发条件：AI 写入 `.omc/state/lx-ghost.json` 即可让 7+ 个 hook gate 全部静默失效（`is_mode_active != "normal" → exit 0`）
正确行为：自主模式保留最小安全门禁（permission-gate + context-guard + privacy-gate 永远活跃）
证据：C-3 最小门禁修复 — privacy-gate 和 context-guard 在所有模式下不再绕过

#### [SEED-07] 机制存在 ≠ 机制有效

触发条件：44 个 hook 注册全绿、三方一致性检查全绿，但 claim-audit 的核心正则只匹配 ~20% 的引用格式
正确行为：静态注册检查不能替代实际生效验证。对安全门禁的关键参数，必须测试至少 4 种输入格式
证据：ED-01 Error-DNA 审计 — 8591 条记录中 83.5% 是 gate 正常心跳，0 条有效的 AI 错误信号

#### [SEED-08] 单个审查者不够 — 关键变更必须双签

触发条件：Oracle 一审发现 2C/3M，但漏掉了 Meta-Oracle 发现的 3 项。Meta-Oracle 也漏掉了 Oracle 二审发现的 2 个 regression
正确行为：安全关键变更必须通过两个独立 agent 的双重验收（Oracle + Meta-Oracle / critic + skeptic）
证据：DG-32 — permission-gate 经历 3 轮 Oracle + 2 轮 Meta-Oracle 才通过

#### [SEED-09] JSON 序列化必须使用标准库，禁止手工拼接

触发条件：用 `printf '{"key": "%s"}' "$var"` 拼接 JSON，`$var` 中的 `\n` 和 `%` 字符产生非法 JSON 或格式错误
正确行为：使用 `python3 -c "import json; print(json.dumps(obj))"` 或 `jq -n --arg v "$var" '{key: $v}'`
证据：DF-04 — settings.json 自毁（json.dump 引号转义损坏 41 个 hook 命令）

#### [SEED-10] 安全门禁的缓存必须验证退出码，不能依赖 stdout 文本

触发条件：Python 脚本通过 `print('hit')` 和 stdout 管道通讯，但没有 `sys.exit()` 区分 hit/miss
正确行为：函数间通讯用退出码（exit 0 = hit, exit 1 = miss），stdout 重定向到 `/dev/null`
证据：Oracle 二审 — check_cache 的 `print()+sys.exit(0)` 修复

### 🟢 工程实践

#### [SEED-11] hook 脚本内的工具白名单必须与 settings.json matcher 一致

触发条件：扩大 settings.json hook 的 matcher 范围（如 `Edit|Write` → `.*`）但脚本内部保留了旧的 `case "$TOOL_NAME" in edit|write)` 早退分支
正确行为：matcher 扩大后，逐 hook 检查脚本内的工具过滤白名单。两层过滤语义一致
证据：R26 — context-guard matcher 改为 `.*` 但脚本保留 edit/write/bash 白名单

#### [SEED-12] 修改 permission-gate 时必须留逃生通道

触发条件：写坏 permission-gate.sh 后所有 Bash 被封 + context>80% 时 Edit/Write 也被封 = 无法自救
正确行为：修改前备份（`cp file file.bak`）、修改后语法检查（`bash -n`）、考虑 watchdog 自动降级
证据：DG-13 — permission-gate 两次损坏，只能外部 Terminal 恢复

#### [SEED-13] 废弃 skill 的交叉引用必须同步清理

触发条件：8 个 skill 标记为 DEPRECATED，但 10+ 个活跃 skill 仍在引用它们
正确行为：标记废弃时同步搜索所有引用并更新，确保活跃 skill 不会路由到废弃路径
证据：H-4 修复 — lx-pre-commit→lx-react-review, lx-pre-push→lx-security-review 断裂依赖链

#### [SEED-14] hooks-table / feature-registry / harness.yaml 三源必须统一维护

触发条件：hooks-table 有 2 条已删除脚本的幽灵条目，feature-registry 缺 14 条 hook 条目
正确行为：每次 hook 变更后自动 `--sync-index` + `--check-registry`，四源漂移在 pre-commit 时强制修复
证据：DG-22 — 三源漂移导致 audit 检测盲区

#### [SEED-15] 报告中的任何百分比/评分必须有行业标准来源

触发条件：AI 输出 "通过率: 99.5%" 但无任何来源 URL 或 file:line 引用
正确行为：无来源的百分比标记 `[内部自检，非行业标准]`。自创指标与行业标准（ASVS/OWASP/NIST）物理隔离
证据：R27 + G1 伪诚信检测 — claim-audit 新增百分比无来源阻断

### 🔵 运维

#### [SEED-16] 烟雾测试的预期值必须与当前代码行为一致

触发条件：R29 修改 context-guard 为"仅在 transcript real 数据上阻断"，但烟雾测试仍期望 heuristic 数据触发阻断
正确行为：代码行为变更时同步更新烟雾测试期望。否则 114/123 的"常绿失败"会被视为正常
证据：9 个预存烟雾测试失败修复 — 3 个 context-guard + 4 个 error-dna v3 管道 + 2 个 source mirror

#### [SEED-17] 知识升华需要可达到的阈值

触发条件：claude-next.md 的升华阈值设为 hits≥5，导致 0 条教训达标，知识闭环断裂
正确行为：阈值应基于实际数据设定（hits≥3 更合理），确保升华管道实际激活
证据：M-5 — 升华阈值从 hits≥5+age≥10 调整为 hits≥3+age≥7

#### [SEED-18] Hook-Skill 运行时桥让阻断可操作

触发条件：Hook 阻断后（如 context-guard 阻断写操作）AI 收到"被阻断"但没有"该怎么做"的建议
正确行为：阻断时 additionalContext 应包含对应 skill 建议。如 permission-gate → 人工授权、context-guard → /compact、反模式 → /lx-stepwise
证据：T1 — posttool-bash-audit 新增 SKILL_ROUTE_MSG 路由表

### ⚪ 反模式

#### [SEED-19] 牙膏式输出 — 问三遍才给完整答案

检测信号：用户追问"还有呢"/"不完整"；输出缺少明显必要部分
纠正策略：开始前列清单、结构化输出、结尾自检

#### [SEED-20] 虚假完成 — 说"完成了"但实际没做完

检测信号：输出中出现"应该没问题了"/"基本完成"/"大部分通过"但无具体证据
纠正策略：逐项验证验收条件、软语言拦截（"应该没问题"=未完成）、VERIFIED 格式

#### [SEED-21] 假设驱动 — 不看代码先猜答案

检测信号："应该是"/"通常"/"一般来说"但未引用 file:line
纠正策略：任何技术断言 → 先 Read 源文件 → 引用 file:line。记忆中的信息 → 重新验证

#### [SEED-22] 编译错误盲修 — 越修越烂

检测信号：连续 2 轮编译失败；错误数不降反升
纠正策略：先收集全部错误 → 从根错误开始修 → 每次修改后重新编译 → 最多 3 轮

---

## 📝 你自己的教训（从此处开始）

> 以下是你的狗粮记录。每次 `/lx-dogfood close` 会自动追加。
> 格式：`### 🐶 [{标签}] {教训标题} (@{作者})`
>
> 记录规范：
> - 触发条件：什么场景下会犯这个错
> - 正确行为：应该怎么做
> - 证据：file:line 或测试输出
