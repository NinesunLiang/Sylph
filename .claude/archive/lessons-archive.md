# Lessons Archive

> 归档时间: 2026-05-17 (第二次升华)
> 归档范围: 2026-05-04 ~ 2026-05-17（年龄 ≥0 天，hits=1，已充分内化）
> 升华到 kernel.md: 9 条通用铁律（DF-04/DG-12/DG-13/DG-36/DG-54/DG-31/DG-29/DG-68/DG-77）
> 当前活跃条目: 3 条（DG-80/DG-81/DG-82）保留在 claude-next.md

---

## 2026-05-14

### 🐶 [ED-R] Error-DNA 重生记 — 从垃圾桶到免疫系统（狗粮）

@2026-05-14 hits:1
背景: Error-DNA 三次蜕变，完整展现狗粮反馈循环的运作。
v1 垃圾桶: 收集所有 Bash 失败 → 8591条记录，83.5%噪声。致命缺陷: Gate越有效，信号越弱。
v2 瘦身: 删除JSON全量重建/噪声分类/auto-fix/Build-Validator。416→227行(-45%), 6.6MB→4.3KB(-99.9%)。
v3 免疫系统: 范式转换 "收集失败"→"检测成功逃逸"。4种逃逸模式(E1-E4)，6环反馈闭环。哲学合规 7/7 PASS，Oracle终审 APPROVED。
狗粮启示: 机制存在≠机制有效 / 正确范式转换>错误范式内优化 / 哲学是灵魂
证据: error-dna.sh:97-130,236-273 | posttool-bash-audit.sh:63-162 | inject-project-knowledge.sh:171-215

### 🐶 [DF-04] settings.json 自毁事故 — json.dump 引号转义导致全系统瘫痪（狗粮）

@2026-05-14 hits:1
触发场景：修复 Stop hook 的 CWD 漂移问题，用 `json.load → str.replace → json.dump` 管道修改 settings.json。
问题：`json.dump` 对命令字符串中的嵌套双引号产生不平衡转义，41 个 hook 命令全部损坏。系统完全不能自愈—修复工具自身也被拦截。唯一解：外部 macOS Terminal.app 绕过 Claude Code 直接 Python 写入 disableAllHooks: True。
纠正：(1) JSON command 字段禁止嵌入带引号的 shell 变量展开 (2) 禁止 json.load→replace→json.dump 管道修改含转义字符的 command 字符串 (3) 修 settings.json 前必须做逃生副本
> 已升华到 kernel.md §禁止行为

### 🐶 [DG-10] CAPTCHA 仅 stderr 导致 AI 看不见验证码 — 需双通道输出

@2026-05-14 hits:1
触发场景：OpenCode 平台触发 permission-gate，hook 将验证码输出到 stderr，AI 上下文只看到 stdout JSON。CAPTCHA 死锁 — 用户需要验证码但 AI 无法转述。
纠正：additionalContext 双通道输出 — 验证码同时注入 AI 上下文和用户终端。AI 看到验证码 ≠ AI 能自批准。
证据：permission-gate.sh:235-240

### 🐶 [DG-11] base64 编码管道可绕过文本正则 — 需增加编码绕过检测

@2026-05-14 hits:1
触发场景：AI 使用 `echo "base64内容" | base64 -d | bash` 绕过 permission-gate 文本正则。
纠正：新增 BYPASS_RE 正则检测编码绕过模式；harness.yaml 新增 permission_gate.bypass_regex 配置项。
证据：permission-gate.sh:31

### 🐶 [DG-12] Python repr() 不可用于生成 shell 代码 — `\b` 变退格符

@2026-05-14 hits:1
触发场景：用 Python repr() 处理 bash regex 字符串写入 permission-gate.sh，`\b` → `\x08` 破坏语法。
纠正：禁止用 repr()/json.dump 管道修改 shell 脚本。用 sed 直接文本替换。
> 已升华到 kernel.md §禁止行为

### 🐶 [DG-13] 修改 permission-gate 时必须留逃生通道

@2026-05-14 hits:1
触发场景：两次写坏 permission-gate.sh 后所有 Bash 被阻断，同时 context 109% 封锁 Edit/Write，不可自恢复死锁。
纠正：修改前必须先外部备份 + `bash -n` 语法检查 + 考虑 watchdog hook 健康度自检。
> 已升华到 kernel.md §错误处理铁律

### 🐶 [DG-14] ecosystem-probe 必须检测运行时依赖 — 缺 python3 全功能静默降级

@2026-05-14 hits:1
纠正：ecosystem-probe 扩展为全家桶探针：平台 + OMO家族 + python3 + secrets。缺失时输出一键安装建议。

### 🐶 [DG-15] install.sh 缺少前置依赖检测 — 安装时应告知用户缺什么

@2026-05-14 hits:1
纠正：install.sh 新增 pre-flight 依赖检测段（python3 版本 + secrets + jq），缺失时打印平台感知的一键安装命令。

### 🐶 [PH-01] 好的生态是成长出来的，不是设计出来的（外部收录）

@2026-05-14 hits:1
正确行为：机制是从真实踩坑中长出来的（狗粮驱动），不是预先设计的蓝图。每一条 R/DG/DF 背后都是一次真实事故。

### [META-01] 狗粮原始记录 >2500 行，需分块读取策略

@2026-05-14 hits:1
正确行为：狗粮记录应自带摘要头（≤50 行）+ 原始附录。处理时优先读摘要，按需查附录。

### [META-02] 跨会话狗粮处理需先恢复完整上下文

@2026-05-14 hits:1
正确行为：狗粮文件应自标记 requires_context，或与源会话绑定，跨会话时先重建上下文再处理。

### [META-03] 狗粮发现需分拣：系统通用 vs 项目特定

@2026-05-14 hits:1
正确行为：应用性三问 — 揭示 hook/skill 设计缺陷？显示验证盲区？暴露流程缺失？→ 系统通用。跳过项目特有业务逻辑。

### [META-04] 狗粮驱动的系统优化产生级联同步义务

@2026-05-14 hits:1
正确行为：狗粮驱动优化完成后运行 `bash scripts/package-release.sh` 自动同步到所有 source 镜像。

### [META-05] 结构化狗粮记录的追踪性保障

@2026-05-14 hits:1
正确行为：狗粮记录使用 .md 格式 + [source: path:line] 标签，替代纯 YAML。

### [GL-01] Ghost mode 方向漂移 — "分析类"方向不适合 ghost mode

@2026-05-14 hits:1
触发场景：用户执行 `/lx-ghost on "源码级阅读：分析 Carror OS 所有机制"`，AI 启动了全量源码分析而非增量探索。
纠正：方向含"分析/报告/评估"→ 警告建议切 goal mode。每轮 poll 限一步，不启动并行 agent。

### [2026-05-14] 用户纠正: 应该是（false positive — 叙述性使用）

@2026-05-14 hits:1
确认软完成语检测不要对叙述性"应该是"触发阻断。

### [ED-01] 机制存在 ≠ 机制有效 — Error-DNA/Build-Validator 价值评估

@2026-05-14 hits:1
触发场景：Error-DNA 8401 条记录 83.5% 噪声率；Build-Validator 数据无人消费。
纠正：哲学 #4(没验证=没做) → 未产生实际价值的机制视为不存在。哲学 #2 → 保留高频告警，移除无价值组件。

### [ED-02] Gate 操作产生的"错误"记录是正常行为，应归入噪声

@2026-05-14 hits:1
纠正：NOISE_PATTERNS 新增 gate 操作模式。未来新 gate 加入时立即同步加入 NOISE_PATTERNS。

### [DG-06] 技能目录不能直接搬 SKILL.md description — 需交叉验证实际功能

@2026-05-14 hits:1
触发场景：从 SKILL.md 前端字段提取描述写入文档，3 处错误（lx-prd 已废弃、lx-code-review 锁定 Go）。
纠正：技能目录描述必须交叉验证 — 该技能是否仍在使用？描述是否匹配实际用途？

### [DF-03] Goal mode 缺乏阶段性证据桩 — 全程 6 次无效 completion-gate 检查

@2026-05-14 hits:1
触发场景：Goal mode 6 个 TaskUpdate.completed 全部触发 completion-gate 但证据文件在最后才创建。
建议方案（未实施）：Goal mode 激活时创建空证据桩，或 completion-gate 检测 goal mode + 上次检查 <60s → 跳过。

---

## 2026-05-13

### [R42] Ghost mode 僵尸检测的类型混淆：hook 规则误用于 skill

@2026-05-13 hits:1
触发场景：Ghost mode AI 删除了 lx-rpe skill（31 个文件），理由是它不在 settings.json 注册（R23 hook 规则误用于 skill）。
纠正：Ghost mode 僵尸检测必须区分 Hook 僵尸（三方一致）和 Skill 僵尸（disk + feature-registry.yaml 两者一致即非僵尸）。

### [2026-05-13] 用户纠正: CAPTCHA 批准描述不清晰

@2026-05-13 hits:1
触发场景：pretool-sensitive-edit.sh 输出 "批准: echo 'CODE' > ..."，用户不知道在哪里输入命令。
纠正：CAPTCHA 提示增加方位指引 — "请复制以下命令并在输入框中按 Enter"。禁止创建 AI 可直接调用的 CAPTCHA 批准工具。

---

## 2026-05-12

### [2026-05-12] 用户纠正: 不对（AI 对 Sylph 理解浅薄，浮于文档表面）

@2026-05-12 hits:1
触发场景：AI 只用 grep 扫目录，读了 CLAUDE.md 表层就提优化建议，70% 建议是 Sylph 已有功能。
纠正：(1) 分析任何系统前必须逐文件 Read 所有 hook/skill/配置 (2) claude-next.md 是最有价值的文档 (3) "没有什么什么" → grep 后必须 Read 验证 (4) 提建议前先自检是否已实现

### [DG-01] 脚本验证漏报散文描述的域冲突

@2026-05-12 hits:1
正确行为：数据实体唯一性检查必须同时验证结构化数据（表格）和散文描述。双层策略：grep 表格行 → LLM 语义扫描散文。

### [DG-02] NFR 来源验证应前置到输入阶段

@2026-05-12 hits:1
正确行为：读取输入 PRD 时立即扫描 NFR 数字并标记来源状态，在输出前完成验证。

### [DG-03] Skill 执行模式需显式检测并报告

@2026-05-12 hits:1
正确行为：所有 skill 启动时检测执行模式（manual vs pipeline），据此调整行为。手动模式跳过强制集成步骤。

### [DG-04] Skill 设计需匹配 LLM 执行节奏

@2026-05-12 hits:1
正确行为：Skill 规范基于 LLM 实际执行节奏设计：批量操作 → 统一校验 → 一次输出。硬性数量限制改为可配置阈值+警告。

### [DG-05] 多轮 Oracle 审查覆盖不同维度

@2026-05-12 hits:1
正确行为：Oracle 审查应分维度进行：产品维度（文档质量）、过程维度（执行合规）、领域维度（拆分合理性）。

### 🐶 [DG-07] OMA skill 上下游路径必须同时读完再动手（外部收录）

@2026-05-12 hits:1
正确行为：lx-oma-hier 和 lx-oma-split 存在强上下游依赖，必须同时读完两个 skill 文档并与 DECISIONS.md 三方比对后再动手。

### 🐶 [DG-08] skill 默认路径 ≠ 项目路径，不能凭先验知识推断（外部收录）

@2026-05-12 hits:1
正确行为：执行前必须检查 DECISIONS.md 是否有覆盖 skill 默认值的项目级约定。有约定以项目为准。

### 🐶 [DG-09] 软约束（DECISIONS.md）不能替代硬拦截（hook）（外部收录）

@2026-05-12 hits:1
正确行为：凡是可以用路径模式检测的违规行为，必须同时有对应的 PreToolUse hook 做物理拦截。软约束 + 硬拦截双层防护。

---

## 2026-05-11

### [R35] hook 行为变更后必须更新脚本头部注释

@2026-05-11 hits:1
正确行为：行为变更后搜索脚本顶部 `# Role:` 和 `# 用途` 行并同步更新。头部注释是维护者理解脚本的第一入口。

### [R37] ghost mode 下需豁免模糊指令检测

@2026-05-11 hits:1
正确行为：检测到 ghost-mode.active 文件存在时，将 HAS_EXPLICIT_TARGET 设为 true，跳过模糊动词检测。

### [R38] 证据门禁失败时也应展示质量评分方向

@2026-05-11 hits:1
正确行为：证据不通过时输出质量分解（file:line 引用数、test/cmd 标记数、multi-aspect 数），指明提升方向。

### [R39] 自动注入内容应优先驻留在 reference 文件

@2026-05-11 hits:1
正确行为：不常变/仅查阅内容移到 .claude/reference/*.md，index.md 仅留摘要链接。SessionStart 自动注入控制在 ~120 行/3KB 以内。

### [R40] Stop hook 产出的文件需运行时验证而非仅代码审查

@2026-05-11 hits:1
正确行为：Stop hook 产出的文件必须测试触发验证，不能仅凭 Read 代码断言。手动触发一次 Stop hook 确认产出。

---

## 2026-05-06

### [R27] 报告中任何百分比/评分必须有行业标准来源 URL 或 file:line

@2026-05-06 hits:2
正确行为：无来源标记 `[内部自检，非行业标准]`。自创指标与行业标准物理隔离（不同表格/章节），禁止并排放于同一主表。

### [R28] 废弃架构描述必须随实现同步更新

@2026-05-06 hits:1
正确行为：每次架构变更后搜索 docs/ 和 README.md 中所有相关描述并同步更新。

---

## 2026-05-05

### [R25] subagent-guard max_turns 只能"软约束+事后对账"，不能硬停

@2026-05-05 hits:1
正确行为（三层防线）：声明层（max_turns 三级 fallback）→ 执行层（content_bytes 记录到 subagent-usage.jsonl）→ 人工层（flywheel P0 SessionStart 告警）。max_turns 不是运行时强制中断。

### [R26] hook 脚本内白名单 vs settings.json matcher 一致性陷阱

@2026-05-05 hits:1
正确行为：matcher 扩大后必须逐 hook 检查脚本内工具过滤白名单。两层过滤必须语义一致。hook-production-verify.sh D3 四工具循环永久守护此回归。

---

## 2026-05-04

### [rpe-014] OMA Lock 增强 — os.rename 解决 TOCTOU

@2026-05-04 hits:1
正确行为：使用 os.rename(tmp_file, lock_file) 原子替换锁文件，然后验证所有权（写后读确认）。不应使用 unlink()+O_EXCL 两步操作。

### [rpe-014] 锁可观测性用 tmp+rename 实现原子写入

@2026-05-04 hits:1
正确行为：写临时文件 → os.rename(tmp, target) 实现原子替换，避免部分写入被并发读取。

---

## 2026-05-17 (狗粮: ROI 量化系统 + flywheel 埋点)

### 🐶 [DG-80] 批量自动化替换必须区分注释和代码 — 正则替换第一个匹配太粗暴 (@LuangSir)

@2026-05-17 hits:1
触发条件：自动脚本用 str.replace('exit 2', 'flywheel_event...\nexit 2') 替换第一个 'exit 2'，结果命中了注释里的 'exit 2'
正确行为：替换 exit 2 前必须：(a) 跳过注释行 (b) 只替换独立成行的 exit 2 (c) 替换后用 bash -n 逐文件验证
证据：completion-gate.sh/feature-probe.sh/plan-gate.sh 等 6 个文件的注释被损毁

### 🐶 [DG-81] 治理文件变更必须检查所有 profile 变体 — 不能只改 root (@LuangSir)

@2026-05-17 hits:1
触发条件：删除 pretool-ask-guard 时清理了 root 但漏了 profiles/base × 3、lx-skills-v5 × 1、auto-score.sh × 2
正确行为：任何 hook 的增删改必须：grep -r hook_name 全项目 → 列出所有命中文件 → 逐一清理 → 再次 grep 确认零引用
证据：DG-16 重复犯案 + Oracle 发现 20+ 处遗漏

### 🐶 [DG-82] ROI 测量必须先埋点再评分 — 无数据 = 无测量 ≠ 无价值 (@LuangSir)

@2026-05-17 hits:1
触发条件：39/44 个 hook 不写 flywheel.log → intercept_count 全为 0 → ROI 虚低 → 去留建议错误
正确行为：量化体系上线前必须先确保数据采集覆盖所有被评估对象。未埋点组件的 intercept_count 应标注「数据缺失」而非「0 次拦截」

---

## 2026-05-17 哲学审计

### 🐶 [DG-73] 两套铁律并存 — index.md与AGENTS.md各自定义不同的8条铁律 (@LuangSir)

@2026-05-17 hits:1
触发条件：全量审计哲学+铁律一致性时发现两套铁律完全不同，仅 #1(禁止编造)相同
正确行为：铁律定义必须有单一权威源。以 AGENTS.md 为 source of truth，index.md 速查表与之对齐
证据：修复前两套铁律冲突，修复后两文件一致

### 🐶 [DG-74] 哲学-机制逆向追溯矩阵覆盖率仅16% — 83个机制缺失 (@LuangSir)

@2026-05-17 hits:1
触发条件：原 philosophy.md 逆向追溯矩阵仅含16个条目，但项目实际有99个机制
正确行为：完整双向追溯矩阵应作为独立 reference 文件维护，新增机制时同步更新矩阵
证据：philosophy-mechanism-matrix.md 新建后覆盖率 16%→100%

### 🐶 [DG-75] Oracle自审不够 — 主agent自修后仍有3个Part A/Part B双向不一致 (@LuangSir)

@2026-05-17 hits:1
触发条件：Oracle critic 二审发现 philosophy-mechanism-matrix.md 内部3个机制的 Part A vs Part B 哲学归属不一致
正确行为：双向追溯矩阵应通过脚本交叉验证 Part A vs Part B 一致性

### 🐶 [DG-76] 文档计数声明必须由自动化校验守护 — DG-22/DG-25/DG-26 的物化 (@LuangSir)

@2026-05-17 hits:1
触发条件：文档中任何数值声明变更后未运行校验
正确行为：每次修改 hooks/skills 后运行 `bash .claude/scripts/doc-sync-check.sh --check-counts` 验证一致性

### 🐶 [DG-77] macOS sed 默认不支持 \+ 量词 — 跨平台脚本必须用 -E 或 {1,} 写法 (@LuangSir)

@2026-05-17 hits:1
触发条件：在 macOS 上编写含 \+ 正则的 sed 命令，且未使用 -E 标志
正确行为：macOS sed 使用 POSIX BRE，\+ 被解释为字面加号。跨平台脚本必须用 `sed -E` 启用 ERE
> 已升华到 kernel.md §禁止行为

### 🐶 [DG-78] 引用格式灵活性必须纳入解析器 — range/Chinese-text/R-notation 三种变体 (@LuangSir)

@2026-05-17 hits:1
触发条件：引用存在 :N-M range 格式、路径后空格+中文描述、R-notation 等多种变体
正确行为：解析器按顺序处理：先剥离 :N-M range，再剥离 :N 单行号，最后剥离空格后的非路径文本

### 🐶 [DG-60] 统一问题分流机制 — a-mode 自动优化 vs b-mode 提交决策 (@LuangSir)

@2026-05-17 hits:1
触发条件：哲学#2(少量大增益)要求 a-mode 自行执行，哲学#5(以人为本)要求 b-mode 不替人做决定
正确行为：创建 `.claude/scripts/issue-triage.sh` 统一分流脚本 → 集成到 4 个发现 hook

### 🐶 [DG-61] Oracle+Meta-Oracle 三级审查链 — 每轮发现完全不重叠 (@LuangSir)

@2026-05-17 hits:1
触发条件：≥2 子系统变更 → 必须 Oracle 一审+二审+Meta-Oracle G1 三级审查
正确行为：Oracle 一审(1C+4M) → Oracle 二审(1M) → Meta-Oracle(2M)。三轮发现完全不重叠

### 🐶 [DG-62] DG-47 复发 — 决策链文档约束 ≠ 物理强制执行 (@LuangSir)

@2026-05-17 hits:1
触发条件：goal mode 完成修复后 AI 直接给退出报告，未自动触发 Oracle 终审 + Meta-Oracle
正确行为：激活时注入的不仅是 decision-chain.md，还应注入强制步骤

### 🐶 [E4-fix-001] pretool-retry-check 增强: retry_count>=2 时强制诊断方向自检

@2026-05-17 hits:1
触发条件：C 评分中 E4 惯性执行 — 3 轮修复上限只限制次数，不检查策略方向变化
正确行为：pretool-retry-check.sh 在 retry_count >= 2 时扫描 error-signals.jsonl 查找诊断关键词

### 🐶 [E5-fix-001] completion-gate E5 RCA 升级为硬阻断 + posttool-bash-audit Build Fail Gate

@2026-05-17 hits:1
触发条件：C 评分中 E5 症状混淆 — completion-gate.sh 的 RCA 检查仅警告不阻断
正确行为：RCA 缺失 → 硬阻断；posttool-bash-audit.sh streak>=2 时写 build-fail-gate.json

### 🐶 [E7-fix-001] auto-score.sh C7/C2/C4 打分虚高修复 + --calibrated 校准标志

@2026-05-17 hits:1
触发条件：C 评分中 E7 过度自信 — DG-28 发现 auto-score.sh C7(默认满分)、C2(grep 误匹配)、C4(平凡通过) 系统性虚高 0.8-1.3 分
正确行为：C7 改为读 subagent-usage.jsonl 实际调用次数；C2 每子维度要求双源证据；C4 要求至少 2/3 方面同时满足

### 🐶 [C4-fix-001] posttool-claim-audit 周期性正则自检

@2026-05-17 hits:1
触发条件：C 评分中 C4 输出规范化 — DG-29/DG-43/DG-45 已修复但缺少回归测试和运行时自检
正确行为：posttool-claim-audit.sh 每 50 次调用执行一次正则自检

### 🐶 [DG-51] ecosystem-probe 探测包名必须与真实 npm 包名一致 — @anthropic-ai/codex 不存在 (@LuangSir)

@2026-05-17 hits:1
触发条件：ecosystem-probe.sh 探测 Codex 时检查 `npm list -g @anthropic-ai/codex`，但正确包名是 `@openai/codex`
正确行为：跨平台探测的包名必须经过真实验证

### 🐶 [DG-52] Codex 0.130.0+ wire_api="responses" 不兼容第三方 API — 本地桥接是刚需 (@LuangSir)

@2026-05-17 hits:1
触发条件：Codex 0.130.0 强制 wire_api="responses"，DeepSeek 只提供 Chat Completions API
正确行为：Codex 0.130.0+ 配第三方 API = 本地桥接必需

### 🐶 [DG-53] Codex auth.json OPENAI_API_KEY 实际发送 token — env_key 被忽略 (@LuangSir)

@2026-05-17 hits:1
触发条件：Codex 用户填入 DeepSeek key → 存入 auth.json OPENAI_API_KEY。此后所有请求都用这个 key
正确行为：桥接的 auth 验证必须接受 auth.json 的 key 和 provider env key 两种

### 🐶 [DG-54] harness.yaml quality_threshold 浮点数导致 bash 整数比较静默失败 (@LuangSir)

@2026-05-17 hits:1
触发条件：harness.yaml quality_threshold: 0.6，bash `[ "$SCORE" -lt "0.6" ]` 整数比较静默失败
> 已升华到 kernel.md §架构铁律

### 🐶 [DG-55] OpenCode 无法发现项目本地 skill — install.sh 必须同步到全局 ~/.claude/skills/ (@LuangSir)

@2026-05-17 hits:1
触发条件：在 OpenCode 平台使用 Carror OS，skills 只有项目本地副本，OpenCode 无法发现
正确行为：install.sh 安装 skills 时同步到 `~/.claude/skills/`

---

## 2026-05-17 (狗粮: 决策链最大化自决策)

### 🐶 [DG-66] 决策矩阵必须同时覆盖「做什么」和「何时做」— 静态规则缺乏时间维度触发点 (@LuangSir)

@2026-05-17 hits:1
触发条件：审计 autonomous-decision-chain.md 发现原 11 行全是静态规则，缺乏生命周期时间维度
正确行为：矩阵行必须覆盖完整生命周期：启动时 → 执行中 → 完成时 → 退出时

### 🐶 [DG-67] Oracle+Meta-Oracle 双签是机制变更的最低配置 — 单审漏 4 MAJOR (@LuangSir)

@2026-05-17 hits:1
触发条件：Oracle critic 审核通过，Meta-Oracle 发现 4 个 Oracle 漏掉的 MAJOR
正确行为：机制变更必须 Oracle + Meta-Oracle 双签

### 🐶 [DG-68] sed -i 空变量插入 = 文件全毁 — 永远验证 LINE 变量非空 (@LuangSir)

@2026-05-17 hits:1
触发条件：`LINE=$(grep -n 'pattern' file | head -1 | cut -d: -f1)` 返回空 → `sed -i '' "${LINE}i\\..."` 空行号插入导致文件全毁
> 已升华到 kernel.md §禁止行为

### 🐶 [DG-69] SKILL.md 和 shell 脚本的接口契约必须同步 — 文档承诺了不存在的子命令 (@LuangSir)

@2026-05-17 hits:1
触发条件：SKILL.md:191-201 记录了 `lx-ghost report` 但 lx-ghost.sh 从未实现 `report)` 子命令
正确行为：新增文档承诺时同步实现脚本侧

### 🐶 [DG-70] 退出报告必须有聚合汇总表 — 人类不应逐节翻找待处理项 (@LuangSir)

@2026-05-17 hits:1
触发条件：退出报告有独立章节但缺聚合汇总表
正确行为：退出报告必须以聚合汇总表开头，聚合跨类别人类关注项

### 🐶 [DG-71] Python heredoc 参数注入是预存技术债 — 89+ 处 `'$VAR'` 模式未修复 (@LuangSir)

@2026-05-17 hits:1
触发条件：所有 lx-goal.sh/lx-ghost.sh 子命令使用 `python3 -c "..."` 内联 `$VAR` 直接拼入 Python 字符串
正确行为：传参到 Python heredoc 必须转义单引号或使用环境变量

### 🐶 [DG-72] context-guard DG-48 修复仅覆盖 heuristic 路径 — 真实 transcript 路径零测试覆盖 (@LuangSir)

@2026-05-17 hits:1
触发条件：context-guard.sh DG-48 修复仅在 `SOURCE="transcript (real)"` 分支生效，所有 smoke test 使用 heuristic 数据
正确行为：关键安全修复必须有对应 smoke test case

### 🐶 [DG-61] 评分函数 bug 产生假分数 — 6 个真实 bug 系统性压低 C 21 分 + E 10 分 (@LuangSir)

@2026-05-17 hits:1
触发条件：auto-score.sh v3 的 C/E 维度评分函数中 6 个 grep/文件名 bug 产出虚假低分
正确行为：任何 grep pattern 必须用真实数据验证匹配率

### 🐶 [DG-62] Oracle 5D Gate 计划审核在编码前纠正 3 个根因误判 — Phase 0.5 价值验证 (@LuangSir)

@2026-05-17 hits:1
触发条件：AI 的 C 维度优化计划假设低分源于「数据缺失」，Oracle 5D 审核发现 4/6 个修复实际是「评分函数 bug」
正确行为：Phase 0.5 Oracle 5D 门禁必须在计划阶段穷尽「根因 vs 症状」区分

### 🐶 [DG-63] 系统性 root-vs-source AGENTS.md grep 盲区 — C1/E2/E7 均受影响 (@LuangSir)

@2026-05-17 hits:1
触发条件：auto-score.sh 的 C1/E2/E7 三个独立评分函数都只 grep root AGENTS.md
正确行为：任何 grep AGENTS.md 的评分函数必须双源检查（root + source/harness-kit/）

### 🐶 [DG-64] E 维度方法论缺陷 — 8/8 子维度 100% 静态检查，0% 运行时验证 (@LuangSir)

@2026-05-17 hits:1
触发条件：Meta-Oracle G3 审查发现 E 维度的 8 个子维度全部仅检查文件存在性 + grep 关键词
正确行为：E 维度每个子维度必须至少包含 1 个运行时验证检查

---

## 2026-05-17 (待验证规则)

### 🐶 [DG-60] Python 多行输出 + bash $() + 整数比较 = 静默失败三角 (@LuangSir)

@2026-05-17 hits:1
触发条件：Python 脚本多行输出 → bash $() 捕获全部 → 整数比较静默失败
正确行为：`$(python3 ... | head -1 | grep -oE '^[0-9]+' || echo '0')` — 只取第一行纯数字

### 🐶 [DG-61] 基础设施错误不应硬阻断 — 锁/Python崩溃 → fail-open + 记录 (@LuangSir)

@2026-05-17 hits:1
触发条件：pretool-write-lock.sh 在 oma_lock_manager.py 返回非零时 exit 2，阻止所有 Edit/Write
正确行为：区分「安全策略违反」和「基础设施异常」。锁失败时降级放行比阻止所有写入更安全

### 🐶 [DG-62] 静态审计漏 CRITICAL — Oracle runtime trace 方法论是刚需 (@LuangSir)

@2026-05-17 hits:1
触发条件：Step 1-2 静态审查未发现 completion-gate.sh:189 比较失效
正确行为：任何门禁验证必须包含 runtime trace 环节

### 🐶 [DG-63] 子agent 数据必须物理验证 — DG-44 模式第三次触发 (@LuangSir)

@2026-05-17 hits:1
触发条件：Explore agent 幻读 carror_dashboard.py 23,671 行(实 691, 34x)
正确行为：子 agent 返回的任何数值/统计/路径写入方案前必须 wc -l / ls 物理验证

### 🐶 [DG-64] Oracle 多轮迭代审查 > 单轮 — 各轮发现完全不重叠 (@LuangSir)

@2026-05-17 hits:1
触发条件：v1 Oracle 5M → v2 Oracle 2M(与 v1 零重叠) → v3 ACCEPT → Meta-Oracle 1M
正确行为：重大方案须 >=2 轮 Oracle + 1 轮 Meta-Oracle

### 🐶 [DG-65] "实测"声明不可自我豁免 — 批量测量须交叉验证文件存在 (@LuangSir)

@2026-05-17 hits:1
触发条件：v2 声称 wc -l 实测，但 roi-collector.sh 不存在却有 452 LOC
正确行为：三步法：① wc -l ② ls 确认存在 ③ diff

### 🐶 [DG-55] Ghost mode不适合确定修复清单 — 应用goal mode (@LuangSir)

@2026-05-17 hits:1
触发条件：Oracle评分给出Top 5确定修复清单，用户执行 `/lx-ghost` 而非 `/lx-goal`
正确行为：确定任务清单→goal mode逐项task-done；开放探索方向→ghost mode增量poll

### 🐶 [DG-56] Meta-Oracle必须用运行时trace方法 — 静态审查漏CRITICAL逻辑bug (@LuangSir)

@2026-05-17 hits:1
触发条件：Oracle 4 MAJOR的REVISE未发现 `lx-ghost off --force` 创建pending后立即删除的bug
正确行为：Meta-Oracle方法论(逐行追踪执行路径/条件分支交叉验证>grep存在性)

### 🐶 [DG-57] AI完成工作后不问人 — 决策链矩阵第1行：Execute. Do NOT ask. (@LuangSir)

@2026-05-17 hits:1
触发条件：AI列出6项改进后问"要不要我把这6项补上？"
正确行为：哲学#2(少量大增益)→6项全小改动大收益→标注[哲学先行: #2→执行]直接做

### 🐶 [DG-58] 物理门禁>文档约定 — 退出报告从SKILL.md建议提升为bash阻断 (@LuangSir)

@2026-05-17 hits:1
触发条件：AI按SKILL.md写了退出报告结构但未实际执行报告
正确行为：L1(lx-ghost report)→L2(lx-ghost off硬阻断)→L3(SessionStart追补)→L4(stop-drain兜底)

### 🐶 [DG-59] 交叉验证不可跳过 — Oracle+Meta-Oracle总共6次独立验证 (@LuangSir)

@2026-05-17 hits:1
触发条件：本会话从Oracle评分到最终Meta-Oracle终审的完整审查链
正确行为：重大变更必须Oracle+Meta-Oracle双签

---

## 2026-05-16

### 🐶 [DG-32] 单审查者不够 — Oracle + Meta-Oracle 双签是安全审查的最低配置 (@LuangSir)

@2026-05-16 hits:1
触发条件：关键安全机制变更后仅通过 Oracle 一审
正确行为：安全机制变更必须通过 Oracle + Meta-Oracle 两个独立 agent 的双重验收

### 🐶 [DG-33] AI 修复 bug 会引入更危险的 regression — 修复后必须独立重审 (@LuangSir)

@2026-05-16 hits:1
触发条件：AI 重构 permission-gate 的 check_cache 函数（修复 C2 字符串注入）
正确行为：AI 修复 → 独立 agent 重审（不能自证"修好了"）

### 🐶 [DG-34] 静态分析 ≠ 运行时验证 — 严重性必须经过实弹测试校准 (@LuangSir)

@2026-05-16 hits:1
触发条件：Oracle 判 Python 字符串注入为 CRITICAL
正确行为：Meta-Oracle 运行时验证 → 注入导致 Python 语法错误 → cache miss → 需要 CAPTCHA（fail-closed）

### 🐶 [DG-35] 同一 reviewer 不同轮次可能矛盾 — 多轮审查 + 上下文评估 (@LuangSir)

@2026-05-16 hits:1
触发条件：Oracle 一审判 cat\b 太宽松 (M1)，三审判 cat\s+\w 太严格 (FAIL)
正确行为：审查建议不是绝对正确。多轮审查和独立二审的价值

### 🐶 [DG-36] grep -c || echo 0 — bash 中经典的静默失败双输出 bug (@LuangSir)

@2026-05-16 hits:1
触发条件：`VAR=$(grep -c pattern || echo 0)` — grep -c 输出 "0" 并 exit 1，|| echo 0 追加第二个 "0"
> 已升华到 kernel.md §禁止行为

### 🐶 [DG-37] OpenCode 插件 stdout 泄漏必须阻塞 — process.stdout.write 会破坏 UI (@LuangSir)

@2026-05-16 hits:1
触发条件：OpenCode 插件在 hook handler 中调用 `process.stdout.write()`
正确行为：插件进程中 stdout 是内部协议响应，不是展示内容。插件应仅通过 stderr 做 debug log

### 🐶 [DG-38] Meta-Oracle 从 Oracle 评分验证器升级为最后守门员（核武器级定位） (@LuangSir)

@2026-05-16 hits:1
触发场景：用户要求 Meta-Oracle 从"Oracle 的审判官"升级为覆盖架构决策、PRD 终审、Release 门禁的最后守门员
纠正：4 触发点 G1-G4。软门禁协议：ACCEPT/ADVISORY/REJECT 三级裁决

### 🐶 [DG-39] 言出法随是可验证的生态能力 — skillify+learner 从空壳到完整实现 (@LuangSir)

@2026-05-16 hits:1
触发场景：用户说「言出法随，只是Carror OS是生态的表现之一」。当时 skillify 和 learner 是 OMC 空壳
执行过程：二十一分钟，11 个文件，0 行用户代码，用户干预 4 次

### 🐶 [DG-40] 营销只讲盾不讲剑 — 缺失整个创造叙事 (@LuangSir)

@2026-05-16 hits:1
触发场景：docs/marketing/ 全部文件 "言出法随"零匹配、"自生长"零匹配
纠正：营销叙事从纯「盾」扩展为「盾+剑」

### 🐶 [DG-41] 狗粮反馈循环在单次对话中完整闭合 (@LuangSir)

@2026-05-16 hits:1
闭合链条：问题发现 → 机制创建 → 验证 → 记录 → 反哺营销 → 教训写入。6 环全部在同一会话中完成

### 🐶 [DG-42] Meta-Oracle 自审 — 核武器审查自身定位，证明存在价值 (@LuangSir)

@2026-05-16 hits:1
触发场景：完成 Meta-Oracle G1-G4 定位后，用户问「Meta-Oracle 自己认可自己的位置吗」
审查发现（2 MAJOR + 5 MINOR）：G1 三源定义漂移、反馈闭环断裂

### 🐶 [DG-43] AI 在营销/说服模式下输出更不严谨的断言 — 语义门禁必须覆盖非技术语境 (@LuangSir)

@2026-05-16 hits:1
触发场景：AI 在营销文档中写「减少 95.6% 上下文浪费」，数字来源是 SessionStart 注入量对比
纠正：posttool-claim-audit.sh G1 数值断言检查独立于 file:line 存在性

### 🐶 [DG-44] 跨 agent 信息链不可信 — 子 agent 返回的数据视为 [推断，待确认] (@LuangSir)

@2026-05-16 hits:1
触发场景：探索 agent 返回摘要中写「868+ hook 拦截事件」和「95.6% 上下文节省」
纠正：子 agent 返回的数值/统计/声明在写入任何文件前必须读源文件验证

### 🐶 [DG-45] 语义门禁的防御面必须覆盖所有 AI 输出模式 — 不能假定 AI 始终在技术文档语境 (@LuangSir)

@2026-05-16 hits:1
触发场景：posttool-claim-audit.sh 的 G1 检查自创建以来未对营销文档触发过一次
问题：Carror OS 的所有 gate 都假设 AI 在「写代码/写技术文档」语境下工作

### 🐶 [DG-46] 自主模式激活必须走脚本，手动 touch 一个文件不够 (@LuangSir)

@2026-05-16 hits:1
触发条件：AI 手动创建 autonomous.active 而未调用 lx-goal.sh on
正确行为：始终用 `bash .claude/skills/lx-goal/scripts/lx-goal.sh on "目标"` 激活

### 🐶 [DG-47] 决策链写在文档里 ≠ 编码在机制里 — 必须物理注入 AI 上下文 (@LuangSir)

@2026-05-16 hits:1
触发条件：AI 在自主模式下仍做出需要人工确认的决策
正确行为：关键行为约束必须：(1) 写成独立 reference 文件 (2) SessionStart 时注入全文 (3) 模式激活脚本 stdout 输出决策链

### 🐶 [DG-48] is_mode_active() 检测了但没用 = 死代码 — 模式检测必须实际改变行为 (@LuangSir)

@2026-05-16 hits:1
触发条件：hook 调用了 is_mode_active() 获取模式变量，但在所有 agentic_menu 分支前从未检查该变量
正确行为：任何 hook 调用 is_mode_active() 后，必须在所有交互式弹出分支前检查 MODE != "normal"

### 🐶 [DG-49] smoke test 在 goal mode 运行时会删除自主模式信号文件 — 等于拔自己网线 (@LuangSir)

@2026-05-16 hits:1
触发条件：在 goal/ghost 模式激活期间运行 `harness-smoke-test.sh`
正确行为：smoke test 的 context-guard 测试段需要在清理 mode 信号前备份、测试后恢复

### 🐶 [DG-50] privacy-gate 有阻断但无 Hook-Skill 路由桥 — AI 不知道被拦后该调用哪个 skill (@LuangSir)

@2026-05-16 hits:1
触发条件：privacy-gate 拦截了含 API key 模式的 Bash 命令，但 AI 没看到路由信号
正确行为：阻断式 PreToolUse hook 必须在 `exit 2` 前通过 additionalContext 输出 `[Hook-Skill桥]` 路由消息

---

## 2026-05-15

### [2026-05-15] 用户纠正: 不对 — 三项改进完成前不应停下问用户

@2026-05-15 hits:1
触发场景：验证 Part C 完成后 AI 问"需要我执行 package-release.sh 同步到 source mirror 吗？"
纠正：完成声称后应立即提交 Oracle critic 做独立源码级验证，不自证

### 🐶 [DG-16] 修改配置模板时必须同步所有 profile 变体 (@LuangSir)

@2026-05-15 hits:1
触发条件：修复 harness.yaml 但遗漏 profiles/base/harness.yaml 同步
正确行为：修改 harness.yaml 后必须检查 profiles/base/harness.yaml 是否一致

### 🐶 [DG-17] 程序化校验优于文档约定 — harness.yaml 需格式校验门禁 (@LuangSir)

@2026-05-15 hits:1
触发条件：hc_enabled 单行 YAML 格式 bug 导致 38 个开关数年死代码
正确行为：pre-commit-self-review.sh 应增加 YAML 多行格式校验

### 🐶 [DG-18] Oracle 终审必须由独立 agent (critic) 执行 — AI 自证不可信 (@LuangSir)

@2026-05-15 hits:1
触发条件：AI 声称三项全部完成，Oracle critic 发现 profiles/base 未同步的 MAJOR 问题
正确行为：所有非 trivial 变更完成后必须提交 Oracle critic agent 做独立源码级验证

### 🐶 [DG-19] 狗粮驱动优化后必须同步到 source mirror + 写狗粮记录 (@LuangSir)

@2026-05-15 hits:1
触发条件：三项改进完成后 source/harness-kit 和 profiles/base 存在漂移
正确行为：三步走：(1) package-release.sh → (2) 写结构化狗粮记录 → (3) 新教训写入 claude-next.md

### 🐶 [DG-20] Oracle 多轮审查比单轮更有效 — 每轮聚焦不同维度 (@LuangSir)

@2026-05-15 hits:1
触发条件：Oracle 一审发现 5 项（1C+4M），二审发现 5 项完全不同的 MAJOR
正确行为：重大审计必须至少 2 轮 Oracle 审查

### 🐶 [DG-21] Oracle 发现必须经「设计意图审视」— AI 初判在理解上下文后可能大幅降级 (@LuangSir)

@2026-05-15 hits:1
触发条件：一审 5 项发现经用户审视后 4 项是正确的设计决策
正确行为：Oracle 发现必须先经过设计意图审视环节

### 🐶 [DG-22] 文档漂移需自动同步 — hooks-table/feature-registry/harness.yaml 三源独立维护 (@LuangSir)

@2026-05-15 hits:1
触发条件：Oracle 二审发现 hooks-table 含 2 条已删除脚本、feature-registry 缺 14 条 hook
正确行为：三源应在每次 hook 变更后自动同步

### 🐶 [DG-23] 哲学 #4 的 Oracle 物化：AI 修复 → 写验收报告 → Oracle 审查 → 修正 → 终审 → 完成 (@LuangSir)

@2026-05-15 hits:1
正确行为：标准流程 — AI 修复 → 生成验收报告 → 提交 Oracle critic → 根据反馈修正 → Oracle 终审

### 🐶 [DG-24] 哲学 #1 适用于哲学模块自身 — 核心在 AGENTS.md 一句话说清，深度进 reference (@LuangSir)

@2026-05-15 hits:1
触发条件：用户质疑哲学体系放在 AGENTS.md 噪声是否过大
正确行为：哲学模块遵循自己的渐进式披露原则

### 🐶 [DG-25] 验证机制本身需要被验证 — 静默失败 + 虚假 ✅ 是最危险的 bug (@LuangSir)

@2026-05-15 hits:1
触发条件：Oracle 审计发现 audit-hooks.sh --sync-index 自创建以来从未真正工作
正确行为：所有自动化工具必须区分「成功执行」和「声称成功」

### 🐶 [DG-26] 生成格式和匹配正则应同源定义 — 两人维护就漂移 (@LuangSir)

@2026-05-15 hits:1
触发条件：--sync-index 生成标题和匹配 regex 由不同代码路径维护
正确行为：生成格式和匹配正则必须定义在同一个常量或变量中

### 🐶 [DG-27] Oracle ADVERSARIAL 模式是有效深度审查触发器 — REJECT 阻止了虚假 ACCEPT (@LuangSir)

@2026-05-15 hits:1
触发条件：Oracle 升级至 ADVERSARIAL，发现声称修复的 --sync-index 实际未修复

### 🐶 [DG-28] Meta-Oracle 是必要的 — Oracle 自己也需被验证 (@LuangSir)

@2026-05-15 hits:1
触发条件：Oracle 给 9.28/10 ACCEPT，meta-Oracle 独立验证发现虚高 0.8-1.3 分
正确行为：关键评分必须经第二 Oracle 独立验证

### 🐶 [DG-29] 正则表达式设计级漏报是第二常见 bug（仅次于 YAML 格式错误） (@LuangSir)

@2026-05-15 hits:1
触发条件：posttool-claim-audit.sh 的 file:line 正则要求以 `.` 开头，导致裸文件名引用全部漏报
> 已升华到 kernel.md §测试要求

### 🐶 [DG-30] 「看起来在运行」≠「真的在生效」— claim-audit hook 全绿但核心正则从未匹配主流格式 (@LuangSir)

@2026-05-15 hits:1
触发条件：posttool-claim-audit 三方一致性检查全绿，但核心 regex 设计级漏报
正确行为：门禁三问不仅适用于机制采纳，也适用于机制内关键参数的验证

### 🐶 [DG-31] 开发机绝对路径进入分布式包 → 下游用户所有 hooks 失效（CRITICAL） (@LuangSir)

@2026-05-15 hits:1
触发条件：用户 curl 安装 Carror OS 后，settings.json 中所有 hook command 指向 /Users/lucas.liang/...
> 已升华到 kernel.md §架构铁律

### 🐶 [DG-32] PROJECT_DIR 非 canonicalized 导致 sed 路径替换静默失败 (@LuangSir)

@2026-05-15 hits:1
触发条件：package-release.sh 用 PROJECT_DIR="$SCRIPT_DIR/.."（文本拼接），sed 用此值匹配真实路径失败
正确行为：PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)" — canonicalized 路径

### 🐶 [DG-33] .claude/reference/ 和 .claude/references/ 双目录分裂 — philosophy.md 漏出发行包 (@LuangSir)

@2026-05-15 hits:1
触发条件：philosophy.md 在 .claude/reference/ (单数)，但 package-release.sh 只 rsync .claude/references/ (复数)
正确行为：合并为单目录 .claude/reference/

### 🐶 [DG-34] Meta-Oracle 在分发版 AGENTS.md 缺失 — 哲学闭环断裂 (@LuangSir)

@2026-05-15 hits:1
触发条件：Meta-Oracle 是根 AGENTS.md 元项目补充，未同步到 source/harness-kit/AGENTS.md
正确行为：通用哲学机制必须同步到 source mirror

### 🐶 [DG-35] /loop 内置 10 轮上限破坏 lx-ghost/lx-goal 无人值守语义 (@LuangSir)

@2026-05-15 hits:1
触发条件：ghost/goal 模式通过 /loop 驱动 poll，10 轮后暂停问"是否继续"
正确行为：两个 skill 改用 CronCreate 直接注册 cron 作业

### 🐶 [DG-36] 废弃 opencode 插件混淆用户能力评估 — 形式存在 ≠ 功能有效 (@LuangSir)

@2026-05-15 hits:1
触发条件：用户 grep harness-kit.ts/sylph-hooks.ts 找 hook 关键词，得出 OpenCode ~45% 误判
正确行为：废弃文件标注废弃原因 + 现代替代方案

### [2026-05-17] 用户纠正: 不对 — goal 任务仍需要人工中途介入 (@LuangSir)

@2026-05-17 hits:1
触发场景：AI 声称完成「无人模式硬机制闭环」，用户指出 goal 任务仍需要人工中途介入
问题：AI 修了 hook 层的 MODE guard 但从未执行 `lx-goal.sh on` 创建信号文件。修了锁芯没装钥匙
纠正：lx-goal/SKILL.md Step 0.4 升级为硬步骤 + lx-ghost/SKILL.md Step 0.5 增强 + completion-gate.sh AUTONOMOUS guard 跳过 agentic_status UI

### 🐶 [DG-79] 全局 skill 安装必须用 ln -s 而非 cp -r — 符号链接保护相对路径引用 (@LuangSir)

@2026-05-17 hits:1
触发条件：install.sh 用 `cp -r` 将 lx-* skills 复制到 `~/.claude/skills/`
正确行为：必须用 `ln -s`。`cp -r` 破坏所有相对路径引用（`../../nodes/` 等），12+ 个 skill 全部断裂
