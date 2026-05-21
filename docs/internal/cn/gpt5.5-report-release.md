[ARCHIVED v6.2.1 — Historical record. Referenced scripts/hooks may no longer exist.]

     1|下面我给你一份**五月吃狗粮 + 持续预热 + 6 月 1 日正式发布的完整作战计划**。
     2|
     3|我会先给你一句总判断：
     4|
     5|> **你 5 月最重要的目标不是“继续堆功能”，而是把 Carror OS 从“强概念系统”打磨成“真实生产环境跑过、有证据、有案例、有传播资产、有商业承接”的产品。**
     6|
     7|你想做到“发布即在 harness 领域领先一代”，关键不是多做 20 个 feature，而是做到：
     8|
     9|1. **核心链路足够稳定**
    10|2. **差异化表达足够清晰**
    11|3. **证据链足够可信**
    12|4. **发布素材足够集中**
    13|5. **商业入口足够自然**
    14|6. **发布后 72 小时响应足够快**
    15|
    16|---
    17|
    18|# 一、总战略：5 月不是开发月，是“证据生产月”
    19|
    20|你知识库里已有一个很关键的策略：
    21|
    22|> **Dogfooding 产出即宣发弹药。**
    23|
    24|这句话非常对。
    25|5 月你每一次真实使用 Carror OS，都要同时产生三类资产：
    26|
    27|## 1. 产品资产
    28|
    29|- bug 修复
    30|- 文档修正
    31|- 安装体验优化
    32|- 核心链路验证
    33|- 用户路径简化
    34|- README / FAQ / demo 完善
    35|
    36|## 2. 证据资产
    37|
    38|- 被 gate 拦截的真实截图
    39|- context hard-gate 触发记录
    40|- error-dna 记录
    41|- lx-status 状态面板截图
    42|- dogfooding 日志
    43|- benchmark 数据
    44|- before / after 对比
    45|- 真实生产任务完成记录
    46|
    47|## 3. 宣发资产
    48|
    49|- 预热帖
    50|- 技术帖
    51|- demo 视频
    52|- 图解
    53|- case study
    54|- FAQ 回答
    55|- 发布主帖
    56|- 商业合作入口文案
    57|
    58|所以五月份你的节奏不是：
    59|
    60|```text
    61|开发 → 最后写宣传
    62|```
    63|
    64|而是：
    65|
    66|```text
    67|真实使用 → 记录证据 → 修产品 → 提炼故事 → 预热发布 → 再使用 → 再修产品
    68|```
    69|
    70|---
    71|
    72|# 二、发布目标拆解
    73|
    74|你希望：
    75|
    76|1. 6 月 1 日正式发布；
    77|2. 有广泛影响；
    78|3. 带来一定经济回报；
    79|4. 产品质量足够好；
    80|5. 在 harness 赛道领先一代。
    81|
    82|我建议把它拆成五个目标。
    83|
    84|---
    85|
    86|## 目标 A：产品目标
    87|
    88|6 月 1 日前，Carror OS 至少要达到：
    89|
    90|| 能力 | 发布前最低要求 |
    91||---|---|
    92|| 安装 | 10 分钟内跑通 |
    93|| Quickstart | 一个真实任务可以完整跑完 |
    94|| README | 60 秒内让人明白产品价值 |
    95|| 核心 Demo | 1 个强 demo + 3 个短 demo |
    96|| Gate | completion/context/permission/edit-scope 至少 4 个能稳定展示 |
    97|| Audit | lx-status 或 audit summary 能展示真实数据 |
    98|| Benchmark | 不一定很漂亮，但必须可信 |
    99|| Docs | 公共文档和内部文档分离 |
   100|| Claim | 不再有高风险未验证数字 |
   101|| 回滚 | 有清晰 migration / troubleshooting |
   102|
   103|---
   104|
   105|## 目标 B：传播目标
   106|
   107|到 6 月 1 日，你要让目标用户形成一个清晰认知：
   108|
   109|> **Carror OS 不是另一个 AI coding 工具，而是 AI coding 的治理层 / harness 操作层。**
   110|
   111|核心传播句可以是：
   112|
   113|> **AI coding 最大的问题不是 AI 不够聪明，而是它不受控。Carror OS 给 AI coding 加上家规、护栏、审计和验收。**
   114|
   115|或者更短：
   116|
   117|> **Carror OS turns AI coding from vibe-driven into evidence-driven.**
   118|
   119|中文：
   120|
   121|> **Carror OS 把 AI 编程从“凭感觉”变成“有纪律、有证据、有验收”。**
   122|
   123|---
   124|
   125|## 目标 C：证据目标
   126|
   127|6 月 1 日前至少准备：
   128|
   129|| 证据类型 | 最低数量 |
   130||---|---:|
   131|| dogfooding 真实案例 | 5 个 |
   132|| 完整 case study | 1 篇 |
   133|| lx-status / audit 截图 | 10 张 |
   134|| gate 拦截图 | 10 张 |
   135|| before / after 对比 | 3 组 |
   136|| demo 视频 | 2 条 |
   137|| benchmark 报告 | 1 份 |
   138|| FAQ | 20 个问题 |
   139|| 外部试用反馈 | 3-5 条 |
   140|| 真实 issue / bug 修复记录 | 10 条以上 |
   141|
   142|---
   143|
   144|## 目标 D：商业目标
   145|
   146|不要一上来就重度卖闭源功能。
   147|你当前最适合的商业路径是：
   148|
   149|```text
   150|开源入口 → 信任扩散 → Enhanced 咨询 / 企业试跑 / 团队接入
   151|```
   152|
   153|建议 6 月 1 日同时放三个商业入口：
   154|
   155|1. **GitHub Sponsor / Buy Me a Coffee**
   156|   - 面向个人支持者
   157|
   158|2. **Early Access / Private Pilot**
   159|   - 面向重度开发者和小团队
   160|
   161|3. **Consulting / Team Rollout**
   162|   - 面向团队和企业
   163|   - 卖的是 workflow 设计、harness 接入、治理策略、DLP / audit / gate 定制
   164|
   165|---
   166|
   167|## 目标 E：领先一代的标准
   168|
   169|你说希望在 harness 领域领先一代。
   170|我建议不要把“领先一代”定义成“功能最多”，而定义成：
   171|
   172|> **别人还在做 AI coding assistant，你已经做 AI coding governance OS。**
   173|
   174|领先一代的 6 个标准：
   175|
   176|| 标准 | Carror OS 要做到什么 |
   177||---|---|
   178|| Harness 可配置 | feature registry + config |
   179|| Governance 可执行 | gates 真能阻断 |
   180|| Evidence 可追踪 | audit / lx-status / logs |
   181|| Context 可治理 | hard gate / handoff |
   182|| Claims 可验证 | benchmark / acceptance test |
   183|| Docs 可上手 | quickstart + FAQ + demo |
   184|
   185|---
   186|
   187|# 三、5 月完整周计划
   188|
   189|假设从 5 月 1 日到 5 月 31 日，6 月 1 日发布。
   190|我建议分成四个阶段：
   191|
   192|```text
   193|Week 1：可信底座与问题定义
   194|Week 2：狗粮实战与核心 demo
   195|Week 3：证据放大与商业预热
   196|Week 4：发布冻结与资产冲刺
   197|May 29-31：Release Candidate / 最终彩排
   198|June 1：发布战役
   199|June 2-7：发布后 72 小时 + 第一波转化
   200|```
   201|
   202|---
   203|
   204|# Week 1：5 月 1 日 - 5 月 4 日
   205|## 主题：先修可信底座，不急着大声宣传
   206|
   207|### 本周目标
   208|
   209|- 完成 repository reality check
   210|- 建立 claim governance
   211|- 删除或降级高风险 claim
   212|- 明确 public / internal 文档边界
   213|- 搭好 dogfooding 记录系统
   214|- 确定 5 月内容主线
   215|
   216|---
   217|
   218|## 产品任务
   219|
   220|### 1. 执行 RPE-000：仓库现实校验
   221|
   222|产出：
   223|
   224|```text
   225|state/repository-reality-check.md
   226|docs/internal/canonical-path-map.md
   227|```
   228|
   229|必须检查：
   230|
   231|- hooks 是否真实存在
   232|- skills 是否真实存在
   233|- 空文件
   234|- 文档错配
   235|- `context_monitor.py` 是否存在
   236|- token writer 是否存在
   237|- `error-dna.sh` 是否可用
   238|- README / features / marketing 是否有高风险数字
   239|
   240|---
   241|
   242|### 2. 建立 Claim Registry
   243|
   244|产出：
   245|
   246|```text
   247|docs/internal/claim-registry.yaml
   248|scripts/claim-lint.sh
   249|docs/internal/claim-lint-report.md
   250|```
   251|
   252|重点处理这些词：
   253|
   254|```text
   255|19,280
   256|75%
   257|100% 功能完备
   258|完全可见
   259|行业独创
   260|真并发
   261|自评分
   262|Claude 默认 tokenizer
   263|```
   264|
   265|---
   266|
   267|### 3. 搭建 Dogfooding Log
   268|
   269|产出：
   270|
   271|```text
   272|docs/internal/DOGFOODING-LOG.md
   273|docs/internal/EVIDENCE-BANK.md
   274|docs/internal/RISK-REGISTER.md
   275|```
   276|
   277|每次 dogfooding 统一记录：
   278|
   279|```md
   280|## Dogfooding Session
   281|
   282|- Date:
   283|- Task:
   284|- Repo / Project:
   285|- Carror OS features used:
   286|- What was blocked:
   287|- What was improved:
   288|- What failed:
   289|- Evidence:
   290|  - screenshots:
   291|  - logs:
   292|  - terminal output:
   293|- Product fix created:
   294|- Marketing angle:
   295|- Commercial insight:
   296|```
   297|
   298|---
   299|
   300|## 宣发任务
   301|
   302|Week 1 不要急着发“产品很强”。
   303|先发问题定义。
   304|
   305|### 预热内容 1
   306|
   307|标题方向：
   308|
   309|> AI coding 最大的问题，不是 AI 不够聪明，而是它不受控。
   310|
   311|结构：
   312|
   313|1. AI coding 现在越来越强；
   314|2. 但真实生产里问题不是“不会写”，而是：
   315|   - 乱读文件
   316|   - 自证完成
   317|   - 上下文失控
   318|   - 修改范围失控
   319|   - 无审计
   320|   - 没验收
   321|3. 所以需要 harness / governance layer；
   322|4. 你正在 5 月真实生产环境 dogfooding 一套系统；
   323|5. 6 月 1 日发布。
   324|
   325|### 预热内容 2
   326|
   327|标题方向：
   328|
   329|> 我不想再让 AI coding 靠感觉完成任务了。
   330|
   331|核心句：
   332|
   333|> 我希望每一次 AI 修改，都有边界、有证据、有验收、有回滚。
   334|
   335|---
   336|
   337|## Week 1 交付物
   338|
   339|| 类型 | 交付物 |
   340||---|---|
   341|| 产品 | reality check 报告 |
   342|| 产品 | claim registry |
   343|| 产品 | dogfooding log 模板 |
   344|| 文档 | README 重构大纲 |
   345|| 宣发 | 2 条问题定义内容 |
   346|| 商业 | Early Access 表单草稿 |
   347|
   348|---
   349|
   350|# Week 2：5 月 5 日 - 5 月 11 日
   351|## 主题：真实狗粮开始，打第一个核心 Demo
   352|
   353|你知识库里已有类似安排：Week 2 先打“问题定义”，不要急着全讲产品。这个方向继续沿用。
   354|
   355|---
   356|
   357|## 本周目标
   358|
   359|- 完成 3 次真实 dogfooding session
   360|- 形成 1 个主 demo 雏形
   361|- 完成 README 首页初版
   362|- 完成 FAQ 初版
   363|- 开始展示第一批真实 evidence
   364|
   365|---
   366|
   367|## 产品任务
   368|
   369|### 1. 选择 3 个真实生产任务
   370|
   371|建议选择不同类型：
   372|
   373|| 任务类型 | 目标验证 |
   374||---|---|
   375|| 小型 bugfix | completion-gate / error-dna |
   376|| 中型重构 | edit-scope / context-guard |
   377|| 文档/代码同步 | doc-sync / feature registry |
   378|
   379|每个任务必须使用 Carror OS 全流程：
   380|
   381|```text
   382|需求输入 → plan → 执行 → gate → audit → evidence → dogfooding log
   383|```
   384|
   385|---
   386|
   387|### 2. 打磨一个主 Demo
   388|
   389|主 Demo 建议不要太复杂。
   390|推荐主题：
   391|
   392|> **AI 想跳过验收，Carror OS 拦住它。**
   393|
   394|Demo 流程：
   395|
   396|1. AI 完成代码修改；
   397|2. completion-gate 要求测试证据；
   398|3. 如果没有测试，阻断；
   399|4. 用户选择 numbered menu；
   400|5. 运行测试 / 修复；
   401|6. lx-status 显示事件；
   402|7. audit log 留痕。
   403|
   404|这个 demo 非常适合传播，因为普通开发者一看就懂：
   405|
   406|> 原来这个系统不是帮 AI 写更多代码，而是防止 AI 胡乱宣布完成。
   407|
   408|---
   409|
   410|### 3. README 首页初版
   411|
   412|README 首屏只讲 5 件事：
   413|
   414|```md
   415|# Carror OS
   416|
   417|AI coding governance and workflow layer for Claude Code.
   418|
   419|## Why
   420|AI coding is powerful, but uncontrolled.
   421|
   422|## What it does
   423|- Gates before done
   424|- Context hard guard
   425|- Audit trail
   426|- Feature registry
   427|- Structured workflows
   428|
   429|## Quickstart
   430|...
   431|
   432|## Demo
   433|...
   434|
   435|## Maturity
   436|...
   437|```
   438|
   439|不要一上来塞太多哲学词。
   440|
   441|---
   442|
   443|## 宣发任务
   444|
   445|### 内容 3：真实狗粮第一帖
   446|
   447|标题方向：
   448|
   449|> 我开始用自己的 AI coding harness 处理真实生产任务了，第一天它就拦住了一次“假完成”。
   450|
   451|结构：
   452|
   453|1. 今天真实任务是什么；
   454|2. AI 原本想怎么结束；
   455|3. Carror OS 怎么拦；
   456|4. 结果如何；
   457|5. 这说明什么；
   458|6. 6 月 1 日开源 / 发布。
   459|
   460|---
   461|
   462|### 内容 4：图解帖
   463|
   464|标题方向：
   465|
   466|> 一个 AI coding harness 至少应该有哪几道防线？
   467|
   468|图中画：
   469|
   470|```text
   471|Prompt → Plan → Edit Scope → Run → Test → Completion Gate → Audit → Handoff
   472|```
   473|
   474|Carror OS 在每层加治理。
   475|
   476|---
   477|
   478|## 商业任务
   479|
   480|建立一个简单入口：
   481|
   482|```text
   483|如果你也在用 AI coding 做真实生产开发，我正在开放 5 个 early dogfooding exchange slots。
   484|可以交流：
   485|- AI coding workflow
   486|- Claude Code harness
   487|- team rollout
   488|- governance / audit / safety
   489|```
   490|
   491|不要硬卖，先收集高意向用户。
   492|
   493|---
   494|
   495|## Week 2 交付物
   496|
   497|| 类型 | 交付物 |
   498||---|---|
   499|| 产品 | 3 次 dogfooding 记录 |
   500|| 产品 | 主 demo 脚本初版 |
   501|