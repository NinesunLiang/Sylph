# 0006 CarrorOS是什么

**日期**: 2026-07-24
**来源**: AGENTS.md, OMC 架构设计

## 核心理念

让开发在使用Deepseek-v4-flash时，具备有Sonnet4.6同等的智能化开发体验；用「机械约束 + 证据强制」的架构补齐轻量模型的长上下文短板、状态飘移问题，不需要强依赖大模型原生推理能力即可完成高质量闭环开发。


## 哲学体系
1. 验证 > ai承诺：CarrorOS不信任AI口头结论，所有断言必须附带测试输出、磁盘日志、截图、改动diff行号等可复现证据佐证；
2. 对ai 零信任：先天不信任AI能自主把状态锁死、闭环收尾，开发之前先遍历全项目建立依赖树：先对存量依赖树做全TDD全绿，再对新增开发内容编写全量TDD用例至100%红，开发完毕后对全量依赖树+新增代码再执行全量TDD至100%全绿；
3. 先守护，后开发：任何涉及危险操作、不可逆变更的场景，执行前自动将原始快照缓存到`.omc/state/restore`目录下，生成硬链索引留存，随时支持一键回滚；CarrorOS核心治理资产（.claude/）不允许AI随意改动，必须先提交变更原因申请权限，Gate1校验通过后才允许写入；
4. 磁盘文档大于内存：不信任AI上下文记忆能力，尤其在上下文溢出、会话压缩、Agent接力场景下，100%依靠磁盘任务系统存储状态：任务侧路径为`.omc/tasks/{YYYYMMDD}/{task_name}/[research|plan|executor]`，特性沉淀侧路径为`rpe/{feature_name}/[research|plan|executor]`，配合`令牌系统`做唯一锚点，任务恢复完全从磁盘读取，不采信内存残余信息；
5. 以人为本：CarrorOS内置标准化AI自主决策链：`行为合法性校验（符合哲学支持>不违反铁律>匹配当前磁盘状态>高ROI大增益低噪声）`，非不可逆高风险场景全部由内核自主决策执行，仅触发三类极限风险时移交人类裁决，避免无意义的逐步骤人机交互；
6. the less，the more： 只做关键的、可量化全局增益的核心机制，不做大而全的冗余功能，任何新增特性必须先在feature-registry.yaml中提交增益证明才可进入开发流程；

灵魂优先级链（机械生效无需协商）：验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少

## 铁律体系
1. **不编造** — 所有断言必须携带可溯源标记 `[已验证:file:line]`
2. **证据门禁** — 每步代码修改完成后必须同步贴出命令执行输出或完整diff，作为放行门禁
3. **范围冻结** — 只允许修改plan.md中预先声明的文件列表，不允许即兴修改未声明文件
4. **隐私防线** — 无条件禁止读取.env/密钥文件/.ssh目录下所有敏感内容
5. **先 init 后动手** — 任何任务启动第一步必须先执行`carros_base.py init`完成令牌初始化，之后才可写入代码
6. **数值断言溯源** — 所有性能/指标类数字断言必须标注完整来源（file:line/reference/benchmark），不允许给出无来源的估算值
7. **治理文件不可改** — 核心治理目录下文件`.claude/hooks/*` / `scripts/carroros-gates/*` / `settings.json` 受Gate1永久保护，普通开发流程中禁止修改


## 机制集合

### 文档系统
CarrorOS 三层结构化文档体系，100%落盘任务状态：
- 单任务三维工作流文档：research.md 存储调研结果/用户问答/决策记录、plan.md 存储声明式实现阶段（一级）、步骤（二级）清单、executor.md 存储执行Checklist门禁+每步操作的EV证据块，四者配合驱动完整任务生命周期 [workflow.md:1-30]
- 特性沉淀文档系统：`rpe/{feature_name}/[research|plan|executor]` 复用单任务三维结构，将跨多任务的通用特性长期沉淀，避免同类型工作重复执行
- 全局证据索引：`02-evidence-index.md` 按评分维度聚合所有核心证据的file:line定位，线上机械校验时可快速跳转溯源 [02-evidence-index.md:1-20]

### 令牌系统
物理锁机制，作为磁盘唯一真相源的锚点：
- 核心令牌为 `.omc/tokens/{YYYYMMDD}/{task_name}.json`，内置任务状态、进度哈希、关联文档硬链索引，任务启动时自动创建，任务全生命周期内所有变更同步更新令牌状态 [0002-token-lock.md:1-40]
- 任务恢复时完全读取令牌内容逆向加载关联文档，完全跳过AI上下文记忆，避免compact/接力后的状态漂移
- 配套全局状态锁文件：`lifecycle.json`、`handoff.json`，跨会话全周期记录内核运行状态 [lifecycle_ssot.py:132-148]

### goal模式
全自主无人值守任务执行模式：
- 前置澄清步骤，收集任务相关的项目上下文信息，确认任务开发的不确定项目，请求人类补齐信息或者决策路径；
- 执行阶段，不需要人类逐步骤确认，AI自动按照goal-report.md声明的目标构建依赖树，对依赖树内容资源做TDD测试（全绿）、拆解任务（复杂任务分两层，先拆分阶段，每个阶段拆分step；简单任务只需要step list）、实现、执行校验、跑回归、跑Tdd、输出完整结果，全程只在触发不可逆高风险场景时才唤醒人工裁决
- 执行输出结果强制要求结构化生成result-goalmode.txt，全量记录执行过程证据链，支持事后完整回溯 [result-goalmode.txt:1-50, goal-report.md]

### compact 机制
上下文溢出场景下的安全压缩机制：
- 触发上下文水位阈值时自动运行pre-completion-gate.py，对全量历史状态做快照写入磁盘，生成result-precomp.txt固化压缩前所有证据 [test-pre-completion-gate.py]// 已经删除上下文水位，由原生compact  上下文传递包括：任务状态列表（每个任务含有任务文档系统link）last_user_prompts(用会最近20条prompt)
- 压缩完成后由session-start.py在下一会话自动从令牌+全量磁盘文档恢复完整任务上下文，完全规避compact导致的信息丢失、状态飘移问题 [session-start.py:1-30, precompact-lifecycle.py] // session-start.py 通过隐式状态注入（摆出任务状态让AI判断）+ postcompact.py写入resume-note.md的显式指令（"立即继续，不要询问"）实现自动恢复。
- compact交换的信物： last_user_prompts(用户最后二十条prompt) 和handoff(任务列表，含执行状态和任务文档系统的token指向；整体摘要

### 飞轮系统
自我增强的闭环演进机制：

分为三层：

- 采集层：采集CarrorOS运行时错误 > error-dna | 用用户纠正记录&项目偏好&错误模式&通用代码质量基线 > claude-next
- 沉淀层：当采集层满了100条，进行与沉淀池的内容进行合并、去重，清空采集层数据；error-dna > .claude/references/error_rulers.json ;claude-next > .claude/references/anti-patterns.md
- 应用层: 两种错误采集的应用层不一样，anti-patterns.md和claude-next 被 AGENTS.md 硬连接引入，主要目的是为了放错；error-dna 和error_rulers.json 是.claude/index.md 软连接引入，目的是ai犯错之后看一下犯错日志，找应对方式；


### 交互

交互方式使用现代的：Agentic UI
分层门禁交互谱系（从轻到重）：`PASS → NARROW → REDIRECT（推荐） → ESCALATE(高风险）→BLOCK → HARD_BLOCK`
- 低于BLOCK级别的非高风险场景使用REDIRECT软打断，输出oracle级别的指引自动纠正行为，不直接阻断执行、不唤醒人工，实现「纠正+继续」的无感知治理，完全符合人本低交互要求 [redirect-mechanism.md:1-50, 0012-redirect.md]
- 仅触发不可逆/越权/核心资产篡改场景时才触发BLOCK/HARD_BLOCK硬阻断，移交人类独占裁决 [pretool-user-approve.py]

任务完成后要有输出报告，摘要说明做了什么、有什么状况、推荐下一步（待默认值的多个选项）

### 双法官
双层并行验证判决体系：
- 第一法官（Pre工具链）：pretool-gate.py + pretool-scorecard-gate.py 组成前置校验层，在工具调用前完成铁律合规、评分框架校验 [pretool-gate.py, 0013-scorecard-gate.md]// 实际机制：lx-oracle skill 的 Oracle-D 协议（静态分析），通过 pretool-gate.py 集成。compound-verify-gate.py 已删除。
- 第二法官（Post工具链）：posttool-output-schema.py + posttool-sensitive-filter.py + posttool-claim-audit.py 组成后置验证层，工具执行完成后对输出做证据审计、敏感过滤、声明校验。// 实际机制：lx-oracle skill 的 Oracle-V 协议（运行时验证）和 Duo 协议（双重校验），通过 TDD/冒烟测试验证。Meta-Oracle（非 Mate-Oracle）归一裁决。
- 两层法官完全独立运行，任意一层判决不通过直接走REDIRECT/BLOCK流程，双校验无死角覆盖全操作链路 // AI + Oracle-D（静态分析）+ Meta-Oracle（运行时验证 Oracle-V + 双重校验 Duo）保障质量。实现：.claude/skills/lx-oracle/
```



### ⑥ 禁止事项
1. 不得修改0006文档中核心理念的核心表述：「让Deepseek-v4-flash具备Sonnet4.6同等智能化体验」，任何修改都会破坏内核目标契约
2. 不得新增第8个顶层机制条目，所有新扩展功能必须归入已有的7个机制条目子范畴内，禁止架构膨胀
3. 不得删除任意机制条目中的实体关联行，所有方括号标注的关联文件必须在项目根路径下真实物理存在，禁止关联虚构路径
4. 不得篡改7条铁律的完整文本，铁律内容受Gate1顶层保护，任何删减均触发HARD_BLOCK
5. 不得在文档末尾追加未经过Grep机械校验、无明确落地实体映射的空泛描述，所有新增内容必须完全匹配知识库内存量工程定义