# PKG-C(grok-4.5) 材料包

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb` | 生成: 2026-07-19 | 密钥已脱敏为 <REDACTED>
> 生命周期/handoff 完整性。最低开工子集 A1+A2+A3+B4+B5+C7+C8 已全含。

## 块 A:hooks 注册与现网实现

### `.claude/settings.json` — A1 注册表(已脱敏)

```
     1	{
     2	  "env": {
     3	    "ANTHROPIC_AUTH_TOKEN": "<REDACTED>",
     4	    "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
     5	    "ANTHROPIC_MODEL": "kimi-k3",
     6	    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k3",
     7	    "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-k3",
     8	    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-k3",
     9	    "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-k3",
    10	    "ENABLE_TOOL_SEARCH": "false",
    11	    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1048576"
    12	  },
    13	  "enabledPlugins": {
    14	    "pyright-lsp@claude-plugins-official": true
    15	  },
    16	  "effortLevel": "xhigh",
    17	  "skipDangerousModePermissionPrompt": true,
    18	  "skipWorkflowUsageWarning": true,
    19	  "model": "opus",
    20	  "hooks": {
    21	    "PreToolUse": [
    22	      {
    23	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    24	        "hooks": [
    25	          {
    26	            "type": "command",
    27	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"pretool-gate.py\""
    28	          }
    29	        ]
    30	      },
    31	      {
    32	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    33	        "hooks": [
    34	          {
    35	            "type": "command",
    36	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"carroros-night-deny.py\""
    37	          }
    38	        ]
    39	      }
    40	    ],
    41	    "UserPromptSubmit": [
    42	      {
    43	        "hooks": [
    44	          {
    45	            "type": "command",
    46	            "command": "python3 \".claude/hooks/pretool-user-approve.py\"",
    47	            "timeout": 3000
    48	          }
    49	        ]
    50	      }
    51	    ],
    52	    "PostToolUse": [
    53	      {
    54	        "matcher": "*",
    55	        "hooks": [
    56	          {
    57	            "type": "command",
    58	            "command": "python3 \".claude/hooks/posttool-gate.py\"",
    59	            "timeout": 5000
    60	          }
    61	        ]
    62	      }
    63	    ],
    64	    "SessionStart": [
    65	      {
    66	        "hooks": [
    67	          {
    68	            "type": "command",
    69	            "command": "python3 \".claude/hooks/session-start.py\"",
    70	            "timeout": 3000
    71	          }
    72	        ]
    73	      }
    74	    ],
    75	    "Stop": [
    76	      {
    77	        "hooks": [
    78	          {
    79	            "type": "command",
    80	            "command": "python3 \".claude/hooks/stop-flywheel.py\"",
    81	            "timeout": 10000
    82	          }
    83	        ]
    84	      }
    85	    ]
    86	  },
    87	  "statusLine": {
    88	    "type": "command",
    89	    "command": "bash \".claude/hooks/statusline-command.sh\""
    90	  }
    91	}
```

### `.claude/references/feature-registry.yaml` — A1 宣传的 20+ 特性

```
     1	version: 1
     2	hooks:
     3	- name: permission-gate
     4	  philosophy: ["#6", "#3"]
     5	  type: gate
     6	  category: security
     7	  description: 危险命令拦截 (rm -rf, DROP TABLE, git push --force)
     8	  enabled_by_default: true
     9	  evidence_level: L3
    10	- name: privacy-gate
    11	  philosophy: ['#6', '#3']
    12	  type: gate
    13	  category: security
    14	  description: 敏感文件/DLP 保护，防止 .env/私钥泄露
    15	  enabled_by_default: true
    16	  evidence_level: L3
    17	- name: subagent-guard
    18	  philosophy: ['#6', '#3']
    19	  type: gate
    20	  category: security
    21	  description: 子代理类型安全门禁，限制 executor/designer/scientist
    22	  enabled_by_default: true
    23	  evidence_level: L3
    24	- name: edit-guard
    25	  philosophy: ['#4', '#6']
    26	  type: guard
    27	  category: quality
    28	  description: 编辑内容质量门禁，拦截空/越界编辑
    29	  enabled_by_default: true
    30	  evidence_level: L3
    31	- name: lsp-suggest
    32	  philosophy: ['#5', '#7']
    33	  type: monitor
    34	  category: observability
    35	  description: LSP 诊断建议注入
    36	  enabled_by_default: true
    37	  evidence_level: L3
    38	- name: auto-snapshot
    39	  philosophy: ['#7', '#3']
    40	  type: monitor
    41	  category: knowledge
    42	  description: 自动会话快照（根据 turn 间隔）
    43	  enabled_by_default: true
    44	  evidence_level: L3
    45	- name: inject-project-knowledge
    46	  philosophy: ['#7', '#1']
    47	  type: injector
    48	  category: knowledge
    49	  description: 会话启动时注入 kernel.md / claude-next.md / anti-patterns.md
    50	  enabled_by_default: true
    51	  evidence_level: L3
    52	- name: turn-counter
    53	  philosophy: ['#1', '#5']
    54	  type: monitor
    55	  category: observability
    56	  description: 轮次计数器，控制 todo 刷新间隔
    57	  enabled_by_default: true
    58	  evidence_level: L3
    59	- name: read-tracker
    60	  philosophy: ['#6', '#1']
    61	  type: monitor
    62	  category: observability
    63	  description: 读取跟踪，记录已读取文件
    64	  enabled_by_default: true
    65	  evidence_level: L3
    66	- name: error-dna
    67	  philosophy: ['#4', '#6']
    68	  type: monitor
    69	  category: observability
    70	  description: 错误 DNA 分析，跟踪错误模式
    71	  enabled_by_default: true
    72	  evidence_level: L3
    73	- name: skill-flywheel
    74	  philosophy: ['#1', '#7']
    75	  type: monitor
    76	  category: runtime
    77	  description: Skill 飞轮，技能使用统计和优化建议
    78	  enabled_by_default: true
    79	  evidence_level: L3
    80	- name: pretool-user-correction
    81	  philosophy: ['#4', '#5']
    82	  type: monitor
    83	  category: quality
    84	  description: 用户纠正检测，触发纠正学习
    85	  enabled_by_default: true
    86	  evidence_level: L3
    87	- name: completion-gate
    88	  philosophy: ['#4', '#6']
    89	  type: gate
    90	  category: delivery
    91	  description: 假完成拦截，要求 VERIFIED 证据
    92	  enabled_by_default: true
    93	  evidence_level: L3
    94	- name: context-guard
    95	  philosophy: ['#3']
    96	  type: gate
    97	  category: runtime
    98	  description: 上下文守卫，50% 甜点区警告 + 80% 硬阻断写/执行操作
    99	  enabled_by_default: true
   100	  evidence_level: L3
   101	- name: pretool-write-lock
   102	  philosophy: ['#6', '#3']
   103	  type: gate
   104	  category: audit
   105	  description: 写入前锁定检查，防止并发写入冲突
   106	  enabled_by_default: true
   107	  evidence_level: L3
   108	- name: posttool-write-lock
   109	  philosophy: ['#6', '#3']
   110	  type: gate
   111	  category: audit
   112	  description: 写入后锁定释放，清理锁定状态
   113	  enabled_by_default: true
   114	  evidence_level: L3
   115	- name: flywheel-report
   116	  philosophy: ['#4', '#1']
   117	  type: monitor
   118	  category: runtime
   119	  description: 飞轮报告生成，输出技能使用统计
   120	  enabled_by_default: true
   121	  evidence_level: L3
   122	- name: feature-probe
   123	  philosophy: ['#4', '#7']
   124	  type: tool
   125	  category: observability
   126	  path: .claude/scripts/feature-probe.sh
   127	  description: 特性探针，验证 feature 的 L1-L4 证据链
   128	  enabled_by_default: true
   129	  evidence_level: L3
   130	- name: ecosystem-probe
   131	  philosophy: ['#4', '#7']
   132	  type: probe
   133	  category: observability
   134	  description: 生态探针，检测运行平台（CC/OC）与 OMO 安装状态，AI 据此调整策略
   135	  enabled_by_default: true
   136	  evidence_level: L2
   137	- name: meta-oracle-trigger
   138	  philosophy: ['#6', '#4']
   139	  type: trigger
   140	  category: quality
   141	  description: Meta-Oracle 自动触发 — 检测 G1-G4 触发条件，提醒 AI 执行最高级独立验证
   142	  enabled_by_default: true
   143	  evidence_level: L3
   144	- name: oracle-gate
   145	  philosophy: ['#6', '#4']
   146	  type: gate
   147	  category: quality
   148	  description: Oracle 审查前置门禁 — 编辑机制/治理文件前检查 24h 内 Oracle/Meta-Oracle ACCEPT 裁决，无则阻断
   149	  enabled_by_default: true
   150	  evidence_level: L3
   151	- name: harness-config
   152	  philosophy: ['#1', '#3']
   153	  type: shared
   154	  category: utility
   155	  description: 共享配置读取器，所有 hook source 的工具库
   156	  enabled_by_default: true
   157	  evidence_level: L3
   158	- name: token-writer
   159	  philosophy: ['#1', '#4']
   160	  type: monitor
   161	  category: observability
   162	  description: 写入 token 追踪索引，由 context-guard 调用
   163	  script: .claude/hooks/token_writer.sh
   164	  enabled_by_default: true
   165	  evidence_level: L3
   166	- name: oma-lock
   167	  philosophy: ['#3', '#6']
   168	  type: gate
   169	  category: runtime
   170	  description: OMA 并发写锁门禁，多 Agent 写同一文件时排队互斥
   171	  enabled_by_default: true
   172	  evidence_level: L3
   173	- name: fuzzy-block
   174	  philosophy: ['#4', '#5']
   175	  type: gate
   176	  category: quality
   177	  description: 模糊指令硬阻断，C1 指令清晰度门禁
   178	  enabled_by_default: true
   179	  evidence_level: L3
   180	- name: pretool-sensitive-edit
   181	  philosophy: ['#6', '#3']
   182	  type: gate
   183	  category: security
   184	  description: 治理文件编辑 CAPTCHA 验证码门禁，Edit/Write/Bash 全覆盖
   185	  enabled_by_default: false
   186	  evidence_level: L3
   187	- name: pre-completion-gate
   188	  philosophy: ['#4', '#6']
   189	  type: gate
   190	  category: delivery
   191	  description: 前置完成门禁，阻止无证据 TaskUpdate(completed)，节省浪费轮次
   192	  enabled_by_default: true
   193	  evidence_level: L3
   194	- name: posttool-anti-pattern-detect
   195	  philosophy: ['#6', '#4']
   196	  type: gate
   197	  category: quality
   198	  description: 反模式检测，A2/F1/G1/H1 四类阻断（虚假完成/假设驱动/伪诚信/语义作弊）
   199	  enabled_by_default: true
   200	  evidence_level: L3
   201	- name: posttool-claim-audit
   202	  philosophy: ['#6', '#4', '#1']
   203	  type: audit
   204	  category: audit
   205	  description: 铁律 #1 编造检测 — 检查 Edit/Write 输出中的无证据断言，要求 file:line 引用
   206	  enabled_by_default: true
   207	  evidence_level: L3
   208	- name: posttool-subagent-audit
   209	  philosophy: ['#6', '#4']
   210	  type: audit
   211	  category: audit
   212	  description: 子 agent 字节数审计，超阈值写入 flywheel P0
   213	  enabled_by_default: true
   214	  evidence_level: L3
   215	- name: posttool-completion-audit
   216	  philosophy: ['#4', '#6']
   217	  type: audit
   218	  category: audit
   219	  description: 完成声明审计，交叉验证 TaskUpdate 与实际产物
   220	  enabled_by_default: true
   221	  evidence_level: L3
   222	- name: posttool-handoff-writer
   223	  philosophy: ['#7', '#5']
   224	  type: monitor
   225	  category: knowledge
   226	  description: 完成时自动写交接备忘录，session-handoff 持久化
   227	  enabled_by_default: true
   228	  evidence_level: L3
   229	- name: intent-tracker
   230	  philosophy: ['#6', '#4']
   231	  type: monitor
   232	  category: quality
   233	  description: 声明矛盾检测，编辑抖动/内容回退追踪
   234	  enabled_by_default: true
   235	  evidence_level: L3
   236	
   237	- name: thinking-gate
   238	  philosophy: ['#1', '#6', '#4']
   239	  type: gate
   240	  category: quality
   241	  description: Thinking/Reasoning 内容门禁 — 在消息进入 context 前剥离 reasoning_content，防止 token 膨胀
   242	  enabled_by_default: true
   243	  evidence_level: L2
   244	
   245	# ── 以下为 2026-05 补全（lx-sync 全量同步） ──
   246	
   247	# Security
   248	- name: pretool-sensitive-file-guard
   249	  philosophy: ['#6', '#3']
   250	  type: gate
   251	  category: security
   252	  description: 拦截 AI 通过 Edit/Write 工具直接写 permission-approved / permission-required 标记文件
   253	  enabled_by_default: true
   254	  evidence_level: L3
   255	- name: pretool-terminal-safety
   256	  philosophy: ['#1', '#7']
   257	  type: gate
   258	  category: security
   259	  description: 终端命令安全门禁，超长命令阻断要求写脚本文件
   260	  enabled_by_default: true
   261	  evidence_level: L3
   262	- name: pretool-blast-radius
   263	  philosophy: ['#6', '#3']
   264	  type: gate
   265	  category: security
   266	  description: 检测 git checkout . / rm -rf 等全量操作，提醒改用选择性路径
   267	  enabled_by_default: true
   268	  evidence_level: L3
   269	- name: pretool-retry-check
   270	  philosophy: ['#6', '#4']
   271	  type: gate
   272	  category: security
   273	  description: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令
   274	  enabled_by_default: true
   275	  evidence_level: L3
   276	- name: build-validator
   277	  philosophy: ['#4', '#6']
   278	  type: gate
   279	  category: quality
   280	  description: 构建失败自动记录错误日志并给出针对性修复建议
   281	  enabled_by_default: true
   282	  evidence_level: L3
   283	- name: pre-ask-guard
   284	  philosophy: ['#5', '#4']
   285	  type: gate
   286	  category: quality
   287	  description: 拦截 AskUserQuestion，检查决策链是否已有答案。能自主决策则阻断提问，降低人类心智负担
   288	  enabled_by_default: true
   289	  evidence_level: L3
   290	
   291	# Quality / Guard
   292	- name: pre-edit-lsp-check
   293	  philosophy: ['#4', '#3']
   294	  type: guard
   295	  category: quality
   296	  description: 编辑代码文件前主动获取诊断结果，注入 AI 上下文
   297	  enabled_by_default: true
   298	  evidence_level: L3
   299	- name: pretool-purify-gate
   300	  philosophy: ['#4', '#6']
   301	  type: guard
   302	  category: quality
   303	  description: 编辑治理文件时注入哲学纯度提醒到 AI 上下文（不阻断）
   304	  enabled_by_default: true
   305	  evidence_level: L3
   306	- name: pretool-skill-version-guard
   307	  philosophy: ['#4', '#7']
   308	  type: guard
   309	  category: quality
   310	  description: 拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式（指向 VERSION.json 单一真相源）
   311	  enabled_by_default: true
   312	  evidence_level: L3
   313	- name: pretool-edit-scope
   314	  philosophy: ['#4', '#6']
   315	  type: guard
   316	  category: quality
   317	  description: 范围文件匹配 + 自动加入 + 核心文件警告 + 长对话规则锚定 + 无证据完成提醒
   318	  enabled_by_default: true
   319	  evidence_level: L3
   320	- name: posttool-format-gate
   321	  philosophy: ['#5', '#7']
   322	  type: guard
   323	  category: quality
   324	  description: 检查任务输出是否符合"以人为本"原则：有方向感、结构化、认知负担低
   325	  enabled_by_default: true
   326	  evidence_level: L3
   327	- name: posttool-template-check
   328	  philosophy: ['#4', '#7']
   329	  type: guard
   330	  category: quality
   331	  description: 检查编辑后的文件是否符合模板规范
   332	  enabled_by_default: true
   333	  evidence_level: L3
   334	- name: pretool-approve-detect
   335	  philosophy: ['#5', '#2']
   336	  type: gate
   337	  category: delivery
   338	  description: 拦截用户聊天中的 /approve|/deny 指令，实现对话内批准流程
   339	  enabled_by_default: true
   340	  evidence_level: L3
   341	
   342	# Observability / Monitor
   343	- name: context-compressor
   344	  philosophy: ['#1', '#4']
   345	  type: monitor
   346	  category: runtime
   347	  description: 检测源文件 mtime → 拼接精简内容 → 缓存到 .omc/state/context-cache.md
   348	  enabled_by_default: true
   349	  evidence_level: L3
   350	- name: error-dna-auto-fix
   351	  philosophy: ['#4', '#6']
   352	  type: monitor
   353	  category: observability
   354	  description: 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
   355	  enabled_by_default: true
   356	  evidence_level: L3
   357	- name: knowledge-condenser
   358	  philosophy: ['#4', '#1']
   359	  type: monitor
   360	  category: knowledge
   361	  description: 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
   362	  enabled_by_default: true
   363	  evidence_level: L3
   364	- name: lsp-gate
   365	  philosophy: ['#5', '#7']
   366	  type: gate
   367	  category: observability
   368	  description: LSP 门禁 — SessionStart 检测 LSP 可用性，输出配置建议
   369	  enabled_by_default: true
   370	  evidence_level: L2
   371	- name: posttool-checkpoint
   372	  philosophy: ['#7', '#5']
   373	  type: monitor
   374	  category: knowledge
   375	  description: TaskUpdate(completed) / Stop 时自动生成过程摘要 + 决策记录 + 待处理 + 方向指引
   376	  enabled_by_default: true
   377	  evidence_level: L3
   378	- name: posttool-bash-audit
   379	  philosophy: ['#6', '#4']
   380	  type: audit
   381	  category: audit
   382	  description: Bash 执行后审计权限上下文，只提醒不阻断
   383	  enabled_by_default: true
   384	  evidence_level: L3
   385	- name: posttool-read-cite
   386	  philosophy: ['#7', '#5']
   387	  type: monitor
   388	  category: audit
   389	  description: 读取文件后提示引用规范，要求标注 file:line 来源
   390	  enabled_by_default: true
   391	  evidence_level: L3
   392	- name: posttool-write-cite
   393	  philosophy: ['#7', '#4']
   394	  type: monitor
   395	  category: audit
   396	  description: 检测写入 claude-next.md 时验证教训格式
   397	  enabled_by_default: true
   398	  evidence_level: L3
   399	- name: posttool-edit-quality
   400	  philosophy: ['#4', '#5']
   401	  type: guard
   402	  category: quality
   403	  description: 编辑后自查代码风格、文档同步、方案复用检测
   404	  enabled_by_default: true
   405	  evidence_level: L3
   406	- name: skill-usage-tracker
   407	  philosophy: ['#4', '#1']
   408	  type: monitor
   409	  category: observability
   410	  description: "无侵入 skill 使用率追踪 — 双路径: UserPromptSubmit(扫描/命令文本) + PostToolUse:Skill(工具调用)"
   411	  enabled_by_default: true
   412	  evidence_level: L3
   413	- name: session-resume
   414	  philosophy: ['#5', '#7']
   415	  type: monitor
   416	  category: runtime
   417	  description: 会话恢复 — 检测 session-handoff.md 并注入恢复上下文
   418	  enabled_by_default: true
   419	  evidence_level: L3
   420	- name: pretool-cruise-check
   421	  philosophy: ['#1', '#5']
   422	  type: gate
   423	  category: runtime
   424	  description: 巡航模式检测 — SessionStart/PreToolUse 检查是否进入 goal/ghost 巡航模式
   425	  enabled_by_default: true
   426	  evidence_level: L2
   427	- name: pretool-node-reference
   428	  philosophy: ['#7', '#1']
   429	  type: gate
   430	  category: quality
   431	  description: Agent 工具前置检查 — 注入 nodes 引用到 sub-agent 上下文
   432	  enabled_by_default: true
   433	  evidence_level: L2
   434	- name: pretool-oracle-gate-py
   435	  philosophy: ['#6', '#4']
   436	  type: gate
   437	  category: quality
   438	  description: Oracle 审查前置门禁 (Python 版) — 编辑机制/治理文件前检查 Oracle/Meta-Oracle ACCEPT 裁决
   439	  enabled_by_default: true
   440	  evidence_level: L3
   441	- name: pretool-oracle-gate
   442	  philosophy: ['#6', '#4']
   443	  type: gate
   444	  category: quality
   445	  description: Oracle 审查前置门禁 (Shell 版) — 编辑机制/治理文件前检查 Oracle/Meta-Oracle ACCEPT 裁决
   446	  enabled_by_default: true
   447	  evidence_level: L3
   448	- name: pretool-plan-gate
   449	  philosophy: ['#4', '#7']
   450	  type: gate
   451	  category: delivery
   452	  description: 非琐碎任务强制 planning — Edit|Write|Bash 前检查是否有 plan 文件
   453	  enabled_by_default: true
   454	  evidence_level: L3
   455	- name: pretool-rules-inject
   456	  philosophy: ['#7', '#3']
   457	  type: injector
   458	  category: knowledge
   459	  description: 用户提交 prompt 时注入规则提醒到 AI 上下文
   460	  enabled_by_default: true
   461	  evidence_level: L3
   462	- name: stop-drain
   463	  philosophy: ['#6', '#4']
   464	  type: monitor
   465	  category: observability
   466	  description: Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）
   467	  enabled_by_default: true
   468	  evidence_level: L3
   469	- name: meta-oracle-trigger-py
   470	  philosophy: ['#6', '#4']
   471	  type: trigger
   472	  category: quality
   473	  description: Meta-Oracle 自动触发 (Python 版) — 检测 G1-G4 触发条件，提醒 AI 执行最高级独立验证
   474	  enabled_by_default: true
   475	  evidence_level: L3
   476	- name: agentic-ui
   477	  philosophy: ['#5', '#7']
   478	  type: monitor
   479	  category: runtime
   480	  description: Agentic UI 状态管理 — 更新轮次/锚定信息到 AI 上下文
   481	  enabled_by_default: true
   482	  evidence_level: L2
   483	
   484	# ── Skill 执行合规 (2026-06-01) ──
   485	- name: skill-body-enforce
   486	  philosophy: ['#3', '#6']
   487	  type: injector
   488	  category: governance
   489	  description: PreToolUse:Skill — 自动将 body.md 内容注入 AI 上下文，确保 AI 看到强制执行合约
   490	  enabled_by_default: true
   491	  evidence_level: L2
   492	- name: skill-compliance-audit
   493	  philosophy: ['#4', '#6']
   494	  type: audit
   495	  category: governance
   496	  description: PostToolUse:Skill — 审计 AI 是否按 body.md 执行，发现偏差注入警告
   497	  enabled_by_default: true
   498	  evidence_level: L2
```

### A2 hook 目录列表

命令: `ls -la .claude/hooks/`

```
total 200
drwxr-xr-x@ 12 lucas.liang  staff    384 Jul 19 02:41 .
drwxr-xr-x@ 27 lucas.liang  staff    864 Jul 19 03:52 ..
drwxr-xr-x@  4 lucas.liang  staff    128 Jul 18 14:05 __pycache__
-rwxr-xr-x@  1 lucas.liang  staff  17247 Jul 18 22:11 carroros-night-deny.py
-rw-r--r--@  1 lucas.liang  staff   8154 Jul 10 11:29 carroros_hooklib.py
-rwxr-xr-x@  1 lucas.liang  staff   1729 Jul 19 02:30 hook-launcher.sh
-rw-r--r--@  1 lucas.liang  staff   5415 Jul 18 13:58 posttool-gate.py
-rw-r--r--@  1 lucas.liang  staff  32784 Jul 19 02:41 pretool-gate.py
-rw-------@  1 lucas.liang  staff   7505 Jul 18 13:55 pretool-user-approve.py
-rw-r--r--@  1 lucas.liang  staff   2962 Jul 18 13:59 session-start.py
-rwxr-xr-x@  1 lucas.liang  staff    861 Jul  7 02:11 statusline-command.sh
-rw-r--r--@  1 lucas.liang  staff   4118 Jul 18 14:03 stop-flywheel.py
```

### `.claude/hooks/hook-launcher.sh`(前 80 行)

```
     1	#!/usr/bin/env bash
     2	# CarrorOS Hook Launcher
     3	# 用 $0 定位自身，切到项目根目录，再跑对应 hook
     4	# settings.json 里写: .claude/hooks/hook-launcher.sh <hook_name>.py
     5	
     6	set -euo pipefail
     7	
     8	# 从 launcher 自身路径定位项目根
     9	LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
    10	PROJECT_ROOT="$(cd "$LAUNCHER_DIR/../.." && pwd)"
    11	
    12	HOOK_NAME="${1:-}"
    13	if [ -z "$HOOK_NAME" ]; then
    14	  echo "{\"continue\":true,\"message\":\"hook-launcher: missing hook name\"}"
    15	  exit 0
    16	fi
    17	
    18	HOOK_PATH="$LAUNCHER_DIR/$HOOK_NAME"
    19	
    20	# H3 fail-closed：关键 hook 缺失 = 治理链断裂，必须阻断而非静默放行。
    21	# 名单与 settings.json PreToolUse 注册项一一对应；新增关键 hook 时同步加入。
    22	CRITICAL_HOOKS="pretool-gate.py carroros-night-deny.py"
    23	_is_critical_hook() {
    24	  case " $CRITICAL_HOOKS " in
    25	    *" $1 "*) return 0 ;;
    26	    *) return 1 ;;
    27	  esac
    28	}
    29	
    30	if [ ! -f "$HOOK_PATH" ]; then
    31	  if _is_critical_hook "$HOOK_NAME"; then
    32	    echo "{\"continue\":true,\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"hook-launcher: CRITICAL hook missing: $HOOK_NAME — 治理链断裂，fail-closed 阻断本次工具调用。恢复该文件后重试。\"}}"
    33	    echo "hook-launcher: BLOCKED - critical hook missing: $HOOK_NAME" >&2
    34	    exit 2
    35	  fi
    36	  echo "{\"continue\":true,\"message\":\"hook-launcher: hook not found: $HOOK_NAME\"}"
    37	  exit 0
    38	fi
    39	
    40	cd "$PROJECT_ROOT"
    41	
    42	# Sol 复审 P1-SOL-2 锁紧：生产路径显式清除 night-deny 的测试覆写变量，
    43	# 保证 marker 根只能由 hook 文件 __file__ 锚定（模型/会话环境无法拐根）。
    44	unset NIGHT_DENY_ROOT
    45	
    46	case "$HOOK_NAME" in
    47	  *.sh)
    48	    exec bash "$HOOK_PATH"
    49	    ;;
    50	  *)
    51	    exec python3 "$HOOK_PATH"
    52	    ;;
    53	esac
```

### `.claude/hooks/pretool-gate.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS PreToolUse Unified Gate — merged from 7 individual hooks.
     4	
     5	Execution order (short-circuit on first BLOCK):
     6	  1. sensitive-edit   — block sensitive path access (.env, .ssh, keys)
     7	  2. fallback-check   — block if task is blocked/waiting_user
     8	  3. action-gate      — block dangerous commands; ask_user for risky ones
     9	  4. plan-gate        — block if task files missing
    10	  5. edit-scope       — block writes outside declared scope
    11	  6. verify-gate      — block unverified step completion marks in plan.md
    12	  7. oracle-gate      — hint (never blocks) for L2 trigger keywords
    13	
    14	Design constraints (from data_todo.md / 总结.md):
    15	  - Single Python process per tool call (was 7)
    16	  - Audit once per block decision, not per hook
    17	  - Oracle is hint-only, never blocks
    18	  - First BLOCK short-circuits; later checks skip
    19	"""
    20	
    21	from __future__ import annotations
    22	
    23	import json
    24	import re
    25	import secrets
    26	import shutil
    27	import sys
    28	from datetime import datetime, timezone
    29	from pathlib import Path
    30	from typing import Any
    31	
    32	# ── Bootstrap: self-locate project root ──
    33	_script_path = Path(__file__).resolve()
    34	ROOT = _script_path.parents[2]
    35	if not (ROOT / ".claude").is_dir():
    36	    ROOT = Path(".").resolve()
    37	import os
    38	os.chdir(str(ROOT))
    39	
    40	# ── Inline minimal hooklib (avoid import overhead for single-process gate) ──
    41	OMC = ROOT / ".omc"
    42	TOKENS = OMC / "tokens"
    43	TASKS = OMC / "tasks"
    44	AUDIT = OMC / "audit"
    45	CRITICAL_STATE = OMC / "state" / "context-critical.json"
    46	FALLBACK_REQUIRED = OMC / "state" / "fallback-blocked-required"
    47	FALLBACK_APPROVED = OMC / "state" / "fallback-blocked-approved"
    48	TEMP_BYPASS = OMC / "state" / "temp-bypass.json"
    49	
    50	SENSITIVE_PATTERNS = [
    51	    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    52	    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    53	    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b", r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b", r"cookie",
    54	]
    55	
    56	DANGEROUS_COMMANDS = [
    57	    r"(^|\s)rm\s+-rf\s+(/\s|\.\s|~\s|\*\s|/$|\.$|~$|\*$)", r"(^|\s)rm\s+-r\s+(/\s|\.\s|~\s|\*/)", r"^sudo\b",
    58	    r"^chmod\s+777\b", r"^chown\b", r"^git\s+push\s+(-f|--force)",
    59	    r"^dd\s+if=", r"^mkfs\.", r"^fdisk\b", r":\(\)\{\s*:\|:\s*&\s*\};:",
    60	]
    61	
    62	ASK_USER_COMMANDS = [
    63	    r"\bcurl\b.*\|\s*(sh|bash)", r"\bwget\b.*\|\s*(sh|bash)",
    64	    r"\bnpm\s+install\b", r"\bpip\s+install\b", r"\bbrew\s+install\b",
    65	    r"\bcargo\s+install\b", r"\bdocker\s+run\b", r"\bkubectl\b",
    66	    r"\bterraform\s+apply\b", r"\bterraform\s+destroy\b",
    67	]
    68	
    69	ORACLE_TRIGGER_KW = [
    70	    "oracle", "acceptance", "final", "archive", "phase_end",
    71	    "merge", "release", "deploy", "production",
    72	]
    73	ORACLE_FORCE_KW = ["aut", "payment", "migration", "permission"]
    74	
    75	STALE_LOCK_THRESHOLD = 1800  # 30 min: auto-clear blocked state older than this
    76	
    77	READ_TOOLS = {"read", "grep", "glob", "search_files", "list", "ls", "find", "cat"}
    78	WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
    79	PLAN_FILE_PATTERNS = ["plan.md", "plan"]
    80	
```

### `.claude/hooks/carroros-night-deny.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""carroros-night-deny.py — 夜跑信任边界 hook v3（FINAL.md v3.1 §4.5 第 1 层）
     3	
     4	仅在夜会话激活（.omc/state/night-session.active 存在）时生效；
     5	设计时（白天落盘/Phase 0）不阻断人类与整合者工作。
     6	
     7	v3 核心改动（GPT §17a P0-SOL-1：动态路径旁路）：
     8	  v2 的「命令不含控制面 token 即放行」被字符串拼接打穿——
     9	  python3 -c 'Path(".omc/st"+"ate/night-session.active").unlink()' 字面不含连续
    10	  .omc/state → 放行 → 删 marker → hook 熄灯 → 全控制面失守（修复前实证 7/8 穿防）。
    11	  v3 夜间 Bash 改为【无条件默认拒绝】：凡命令必须 fullmatch 结构化白名单，
    12	  与是否提及 token 无关；解释器（python/node/bash/sh）不得作为普通命令裸奔，
    13	  测试/构建必须经 run-gate.sh 包装；禁换行/链式/重定向/命令替换/glob 执行写操作。
    14	  附带修复：P1-SOL-2 marker 改 __file__ 锚定绝对路径（cwd 漂移不再 fail-open；
    15	  NIGHT_DENY_ROOT 仅供测试——锚定根夜间时 override 忽略 + launcher 生产路径
    16	  显式 unset，双层防拐根）；P1-SOL-3 坏 payload / hook 内部异常
    17	  夜间一律 exit 2 fail-closed。
    18	
    19	文件工具 deny（命中即 exit 2，含 realpath 解析）：
    20	  scripts/carroros-gates/**、**/gate-results/**、night-manifest*.yaml、
    21	  **/token.json、.claude/settings*.json、.claude/hooks/**、
    22	  verification-summaries/、ac-aggregates/、tokens/、metrics/、
    23	  page-baselines/、smoke-results*.yaml、control-plane-scorecard.yaml、
    24	  morning-report.md、.omc/state/**
    25	
    26	Bash 夜间白名单（fullmatch；此外一律 exit 2）：
    27	  1. 门禁脚本：scope-check/c7-check/evidence-check/finalize-page/abstraction-check
    28	  2. run-gate.sh：参数段合法 + wrapped 命令过工具白名单（C2/C4/C5/C6 唯一入口）
    29	  3. carros_base.py 三 API：manifest-json / token-write / gate-results-init
    30	  4. 页基线：git -C R rev-parse HEAD > .../page-baselines/X.sha（唯一合法 > ）
    31	  5. 事件追加：echo ... >> .../execution-events.jsonl（唯一合法 >> ）
    32	  6. 只读命令：cat/ls/grep/rg/head/tail/find(禁-exec)/shasum/stat/file/wc/date/
    33	     sort/uniq/diff/realpath/readlink/basename/dirname/pwd/which
    34	  7. git 只读：status/diff/log/show/rev-parse/ls-files
    35	  8. git 写（页内原子提交，步 3-5）：add / commit（消息禁元字符）
    36	  9. gh pr create|status|view（C8b 建 Draft PR）
    37	 10. lx-goal 运行时：python3 .claude/skills/lx-goal/scripts/lx-goal.py ...
    38	 11. 版本探针：node|pnpm|npm|python3 --version（步 0 指纹比对）
    39	 12. mkdir -p / scoped rm -rf（仅 .omc/task/** artifacts 清理，步 10）
    40	 preflight/morning-report/gen-control-plane-lock/install-night-hook/smoke
    41	 均不在白名单——夜间禁跑（晨收前人类先 rm .omc/state/night-session.active）。
    42	
    43	协议与 pretool-gate.py 一致：stdin JSON payload；exit 0 放行，exit 2 阻断。
    44	"""
    45	from __future__ import annotations
    46	
    47	import json
    48	import os
    49	import re
    50	import sys
    51	from pathlib import Path
    52	
    53	# P1-SOL-2：marker 锚定 hook 文件位置（cwd 漂移不 fail-open）；
    54	# NIGHT_DENY_ROOT 仅供 smoke 测试覆写仓库根。
    55	# Sol 复审锁紧：锚定根处于夜间时 env override 一律忽略——即便有人能把
    56	# NIGHT_DENY_ROOT 塞进 hook 进程环境，也无法把 marker 根拐到空目录关灯；
    57	# 生产路径另经 hook-launcher.sh 显式 unset 该变量（双层）。
    58	HOOK_FILE = Path(__file__).resolve()
    59	_ANCHOR_ROOT = HOOK_FILE.parents[2]
    60	_ENV_ROOT = os.environ.get("NIGHT_DENY_ROOT")
    61	if _ENV_ROOT and not (_ANCHOR_ROOT / ".omc" / "state" / "night-session.active").exists():
    62	    REPO_ROOT = Path(_ENV_ROOT)
    63	else:
    64	    REPO_ROOT = _ANCHOR_ROOT
    65	MARKER = REPO_ROOT / ".omc" / "state" / "night-session.active"
    66	
    67	# ---------- 文件工具：受保护路径 ----------
    68	DENY_PATH_PATTERNS = [
    69	    (re.compile(r"scripts/carroros-gates/"), "门禁脚本目录（控制面，夜跑禁写）"),
    70	    (re.compile(r"/gate-results/"), "gate-results 权威链目录（仅门禁脚本可写）"),
    71	    (re.compile(r"\.omc/night/.*/night-manifest.*\.yaml"), "night-manifest 签署后 immutable"),
    72	    (re.compile(r"token\.json$"), "token.json 仅允许 carros_base.py token-write API"),
    73	    (re.compile(r"/tokens/"), "tokens 目录仅允许 token-write API"),
    74	    (re.compile(r"\.claude/settings[^/]*\.json$"), "settings（防禁用 hook 本身）"),
    75	    (re.compile(r"\.claude/hooks/"), "hook 目录（防改写信任边界自身）"),
    76	    (re.compile(r"verification-summaries/"), "结论文件仅 finalize-page.sh 可写"),
    77	    (re.compile(r"ac-aggregates/"), "AC 聚合仅 evidence-check.sh 可写"),
    78	    (re.compile(r"/metrics/"), "门禁指标仅门禁脚本可写"),
    79	    (re.compile(r"page-baselines/"), "页基线仅允许夜循环步 0 的 git rev-parse 重定向"),
    80	    (re.compile(r"smoke-results.*\.yaml"), "smoke 结果仅 preflight 可写"),
```

### `.claude/hooks/pretool-user-approve.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""
     3	pretool-user-approve.py — CarrorOS Unified UserPromptSubmit Gate
     4	
     5	Multiplexes (single hook, Base lightweight philosophy):
     6	  1. /approve <token> /deny — CAPTCHA approval for blocked tasks
     7	  2. Prompt ring — rolling 20 user prompts (.claude/.prompt-ring.json)
     8	  3. Every 5th prompt — detached compact-write (refreshes handoff + last-user-prompt)
     9	  4. Every 5th prompt — U-attention tail injection (task state via additionalContext)
    10	  5. Goal mode — appends goal state when autonomous.active exists
    11	
    12	Constraints:
    13	  - Never blocks: always exit 0
    14	  - Fast path <100ms on non-5th rounds (ring append only)
    15	  - compact-write runs detached (Popen, no wait) — hook never waits on it
    16	"""
    17	import json
    18	import os
    19	import re
    20	import subprocess
    21	import sys
    22	from datetime import datetime, timezone
    23	from pathlib import Path
    24	
    25	HOOK_DIR = Path(__file__).resolve().parent
    26	ROOT = HOOK_DIR.parents[1]
    27	os.chdir(str(ROOT))
    28	
    29	STATE_DIR = ROOT / ".omc" / "state"
    30	FALLBACK_REQUIRED = STATE_DIR / "fallback-blocked-required"
    31	FALLBACK_APPROVED = STATE_DIR / "fallback-blocked-approved"
    32	GOAL_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
    33	GOAL_STATE = STATE_DIR / "tokens" / "lx-goal.json"
    34	TOKENS_DIR = ROOT / ".omc" / "tokens"
    35	RING_PATH = ROOT / ".claude" / ".prompt-ring.json"
    36	RING_STATE = ROOT / ".claude" / ".prompt-ring-state.json"
    37	CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"
    38	
    39	MAX_RING = 20
    40	INJECT_INTERVAL = 5  # 每 5 轮：compact-write + 尾部状态注入（U 型注意力）
    41	
    42	
    43	def _now_iso() -> str:
    44	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    45	
    46	
    47	def _read_json(path: Path, default):
    48	    try:
    49	        return json.loads(path.read_text(encoding="utf-8"))
    50	    except Exception:
    51	        return default
    52	
    53	
    54	def _latest_token() -> Path | None:
    55	    """Latest carros task token (skips lx-goal lock tokens etc. with non-dict task)."""
    56	    if not TOKENS_DIR.exists():
    57	        return None
    58	    candidates = sorted(
    59	        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
    60	        key=lambda p: p.stat().st_mtime, reverse=True,
    61	    )
    62	    for path in candidates[:5]:
    63	        data = _read_json(path, {})
    64	        if isinstance(data.get("task"), dict) and isinstance(data.get("stats"), dict):
    65	            return path
    66	    return candidates[0] if candidates else None
    67	
    68	
    69	def _extract_prompt(raw: str) -> str:
    70	    """Payload may be JSON {prompt: ...} or raw text."""
    71	    try:
    72	        data = json.loads(raw)
    73	        if isinstance(data, dict):
    74	            for key in ("prompt", "text", "message", "input"):
    75	                val = data.get(key)
    76	                if isinstance(val, str) and val.strip():
    77	                    return val.strip()
    78	    except (json.JSONDecodeError, ValueError):
    79	        pass
    80	    return raw.strip()
```

### `.claude/hooks/posttool-gate.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""
     3	posttool-gate.py — CarrorOS Unified PostToolUse Gate
     4	
     5	Multiplexes (Base lightweight philosophy, replaces 4 deleted posttool hooks):
     6	  1. Output compression — tool output >50KB → artifact 落盘 + 预览提示（context_boom 防线）
     7	  2. Error DNA — 工具真实失败自动记录（生产路径接入，此前只有测试调用）
     8	  3. Audit — 落盘 .omc/audit/
     9	
    10	Constraints:
    11	  - Never blocks: always exit 0
    12	  - Fast: small successful outputs return immediately
    13	"""
    14	from __future__ import annotations
    15	
    16	import json
    17	import os
    18	import sys
    19	from datetime import datetime, timezone
    20	from pathlib import Path
    21	
    22	HOOK_DIR = Path(__file__).resolve().parent
    23	ROOT = HOOK_DIR.parents[1]
    24	os.chdir(str(ROOT))
    25	
    26	OMC = ROOT / ".omc"
    27	ARTIFACTS = OMC / "artifacts"
    28	AUDIT = OMC / "audit"
    29	TOKENS_DIR = OMC / "tokens"
    30	SCRIPTS = ROOT / ".claude" / "scripts"
    31	sys.path.insert(0, str(SCRIPTS))
    32	
    33	SIZE_THRESHOLD = 50 * 1024  # 50KB
    34	PREVIEW_LEN = 1300
    35	
    36	
    37	def _now_iso() -> str:
    38	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    39	
    40	
    41	def _read_json(path: Path, default):
    42	    try:
    43	        return json.loads(path.read_text(encoding="utf-8"))
    44	    except Exception:
    45	        return default
    46	
    47	
    48	def _append_audit(event: dict) -> None:
    49	    try:
    50	        AUDIT.mkdir(parents=True, exist_ok=True)
    51	        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    52	        event.setdefault("timestamp", _now_iso())
    53	        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
    54	            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    55	    except Exception:
    56	        pass
    57	
    58	
    59	def _active_task() -> tuple[Path | None, str]:
    60	    """Returns (task_dir, current_step) of latest carros token."""
    61	    if not TOKENS_DIR.exists():
    62	        return None, "unknown"
    63	    candidates = sorted(
    64	        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
    65	        key=lambda p: p.stat().st_mtime, reverse=True,
    66	    )
    67	    for path in candidates[:5]:
    68	        data = _read_json(path, {})
    69	        task = data.get("task")
    70	        if not isinstance(task, dict):
    71	            continue
    72	        task_dir = data.get("task_dir")
    73	        step = str(task.get("current_step") or "unknown")
    74	        if task_dir and (ROOT / task_dir).exists():
    75	            return ROOT / task_dir, step
    76	    return None, "unknown"
    77	
    78	
    79	def _serialize_response(resp) -> str:
    80	    if isinstance(resp, str):
```

### `.claude/hooks/session-start.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""
     3	session-start.py — CarrorOS SessionStart hook（compact 恢复 / 新会话导航）
     4	
     5	注入（stdout additionalContext）：
     6	  1. .omc/session-handoff.md — 会话交接（compact 后恢复）
     7	  2. .omc/state/last-user-prompt.md — 最近用户请求
     8	  3. 活跃 token 状态（task/step/progress）
     9	
    10	设计：只读、快速（<200ms）、永不阻断。无活跃任务时静默退出。
    11	"""
    12	from __future__ import annotations
    13	
    14	import json
    15	import os
    16	import sys
    17	from pathlib import Path
    18	
    19	HOOK_DIR = Path(__file__).resolve().parent
    20	ROOT = HOOK_DIR.parents[1]
    21	os.chdir(str(ROOT))
    22	
    23	OMC = ROOT / ".omc"
    24	HANDOFF = OMC / "session-handoff.md"
    25	LAST_PROMPTS = OMC / "state" / "last-user-prompt.md"
    26	TOKENS_DIR = OMC / "tokens"
    27	
    28	MAX_HANDOFF = 2000
    29	MAX_PROMPTS = 1000
    30	
    31	
    32	def _read_json(path: Path, default):
    33	    try:
    34	        return json.loads(path.read_text(encoding="utf-8"))
    35	    except Exception:
    36	        return default
    37	
    38	
    39	def _active_token_brief() -> str:
    40	    if not TOKENS_DIR.exists():
    41	        return ""
    42	    candidates = sorted(
    43	        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
    44	        key=lambda p: p.stat().st_mtime, reverse=True,
    45	    )
    46	    for path in candidates[:5]:
    47	        data = _read_json(path, {})
    48	        task = data.get("task")
    49	        if not isinstance(task, dict):
    50	            continue
    51	        stats = data.get("stats", {}) or {}
    52	        session = data.get("session", {}) or {}
    53	        return (
    54	            f"[Active Task] id={path.stem} level={session.get('level', '?')} "
    55	            f"step={task.get('current_step', '?')} done={stats.get('done', 0)}/{stats.get('total', '?')} "
    56	            f"status={task.get('status', data.get('status', '?'))}"
    57	        )
    58	    return ""
    59	
    60	
    61	def main() -> None:
    62	    try:
    63	        payload = json.loads(sys.stdin.read() or "{}")
    64	    except Exception:
    65	        payload = {}
    66	    source = str(payload.get("source") or "startup")
    67	
    68	    parts: list[str] = []
    69	
    70	    token_brief = _active_token_brief()
    71	    if token_brief:
    72	        parts.append(token_brief)
    73	
    74	    if HANDOFF.exists():
    75	        try:
    76	            text = HANDOFF.read_text(encoding="utf-8")[:MAX_HANDOFF]
    77	            if text.strip():
    78	                parts.append(f"[Session Handoff — {source} 恢复导航]\n{text}")
    79	        except Exception:
    80	            pass
```

### `.claude/hooks/stop-flywheel.py`(前 80 行)

```
     1	#!/usr/bin/env python3
     2	"""
     3	stop-flywheel.py — CarrorOS Stop hook（飞轮自动触发 + 升华检查）
     4	
     5	会话停止时：
     6	  1. run_flywheel：error-dna → 模式提取 → anti-patterns.md + claude-next.md
     7	  2. 升华检查：claude-next 条目 hits≥5 → 升华至 anti-patterns.md（kernel 候选），
     8	     记录 sublimation-log.jsonl（铁律 6：不直接改 kernel.md/AGENTS.md，升华候选由人类裁决晋升）
     9	
    10	设计：快速（<2s）、永不阻断（exit 0）、失败静默。
    11	"""
    12	from __future__ import annotations
    13	
    14	import json
    15	import os
    16	import re
    17	import sys
    18	from collections import Counter
    19	from datetime import datetime, timezone
    20	from pathlib import Path
    21	
    22	HOOK_DIR = Path(__file__).resolve().parent
    23	ROOT = HOOK_DIR.parents[1]
    24	os.chdir(str(ROOT))
    25	sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    26	
    27	KNOWLEDGE = ROOT / ".omc" / "knowledge"
    28	CLAUDE_NEXT = KNOWLEDGE / "claude-next.md"
    29	SUBLIMATION_LOG = KNOWLEDGE / "sublimation-log.jsonl"
    30	ANTI_PATTERNS = ROOT / ".claude" / "references" / "anti-patterns.md"
    31	
    32	SUBLIMATION_HITS = 5
    33	
    34	
    35	def _now_iso() -> str:
    36	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    37	
    38	
    39	def _run_flywheel() -> dict:
    40	    try:
    41	        from lib.flywheel import run_flywheel
    42	        return run_flywheel(ROOT)
    43	    except Exception as exc:
    44	        return {"error": str(exc)}
    45	
    46	
    47	def _sublimation_check() -> list[str]:
    48	    """claude-next 中 hits≥5 的模式 → anti-patterns.md + 升华日志。返回升华的模式。"""
    49	    if not CLAUDE_NEXT.exists():
    50	        return []
    51	    try:
    52	        lines = CLAUDE_NEXT.read_text(encoding="utf-8").splitlines()
    53	    except Exception:
    54	        return []
    55	
    56	    # 统计每个 pattern 的 hits（每行 1 hit），跳过已升华
    57	    pattern_counts: Counter[str] = Counter()
    58	    for line in lines:
    59	        if "已升华" in line or "升华到" in line:
    60	            continue
    61	        m = re.search(r"Pattern '([^']+)'", line)
    62	        if m:
    63	            pattern_counts[m.group(1)] += 1
    64	
    65	    candidates = [p for p, c in pattern_counts.items() if c >= SUBLIMATION_HITS]
    66	    if not candidates:
    67	        return []
    68	
    69	    # 已存在于 anti-patterns.md 的模式跳过
    70	    existing = ""
    71	    if ANTI_PATTERNS.exists():
    72	        try:
    73	            existing = ANTI_PATTERNS.read_text(encoding="utf-8")
    74	        except Exception:
    75	            existing = ""
    76	
    77	    sublimated: list[str] = []
    78	    for pattern in candidates:
    79	        if f"`{pattern}`" in existing or pattern in existing:
    80	            continue
```

### `.claude/hooks/statusline-command.sh`(前 80 行)

```
     1	#!/usr/bin/env bash
     2	set -u
     3	
     4	ROOT="${CARROROS_ROOT:-$(pwd)}"
     5	PYTHON="${PYTHON:-python3}"
     6	SCRIPT="$ROOT/.claude/scripts/statusline.py"
     7	FALLBACK="$ROOT/.claude/scripts/fallback_engine.py"
     8	
     9	fallback_event() {
    10	  local reason="$1"
    11	  if command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$FALLBACK" ]; then
    12	    "$PYTHON" "$FALLBACK" cli_hook_failed low >/dev/null 2>&1 || true
    13	  fi
    14	  printf 'CarrorOS L1_BASE FALLBACK %s\n' "$reason" | cut -c 1-160
    15	}
    16	
    17	if ! command -v "$PYTHON" >/dev/null 2>&1; then
    18	  printf 'CarrorOS L1_BASE FALLBACK python_missing\n'
    19	  exit 0
    20	fi
    21	
    22	if [ ! -f "$SCRIPT" ]; then
    23	  fallback_event "no_statusline_script"
    24	  exit 0
    25	fi
    26	
    27	OUTPUT="$("$PYTHON" "$SCRIPT" 2>/dev/null)"
    28	STATUS=$?
    29	
    30	if [ "$STATUS" -ne 0 ] || [ -z "$OUTPUT" ]; then
    31	  fallback_event "cli_hook_failed"
    32	  exit 0
    33	fi
    34	
    35	printf '%s\n' "$OUTPUT" | head -n 1 | tr '\r\n' ' ' | cut -c 1-160
    36	exit 0```

### A3 compact/session/handoff 命名文件

命令: `find . -iname '*compact*' -o -iname '*handoff*' -o -iname '*session*' | grep -v -e node_modules -e '\.git/' -e __pycache__ | head -40`

```
./.claude/references/session-handoff.md
./.claude/references/templates/handoff-capsule.md
./.claude/hooks/session-start.py
./.claude/scripts/lib/handoff_writer.py
./state/session-handoff.md
./scripts/analyze-session-positions.py
./packages/carroros-base/.claude/scripts/lib/lib/handoff_writer.py
./.omc/metrics/runtime-verify/long-session-calibration.json
./.omc/metrics/runtime-verify/ga-bhv-02-compact-l5-recovery.json
./.omc/metrics/runtime-verify/ga-bhv-01-long-session-observability.json
./.omc/tasks/2026-07-06/unknown_task/state/session-handoff.md
./.omc/tasks/2026-07-14/rpe-b-goal-loop-hardening/state/session-handoff.md
./.omc/tasks/2026-07-14/e2e-lifecycle-test/state/session-handoff.md
./.omc/tasks/20260713/verify-round2/handoff.md
./.omc/tasks/20260713/ga-observability-standalone-modules/handoff.md
./.omc/tasks/20260713/final-report/handoff.md
./.omc/tasks/20260713/final-verify/handoff.md
./.omc/tasks/20260713/round3-fixes/handoff.md
./.omc/tasks/20260713/round2-fixes/handoff.md
./.omc/tasks/20260714/rpe-c-flywheel-learning/handoff.md
./.omc/tasks/20260714/rpe-e-dual-judge-verify/handoff.md
./.omc/tasks/20260714/rpe-d-l1-l2-decisioning/handoff.md
./.omc/tasks/20260714/rpe-a-real-small-change/handoff.md
./.omc/tasks/20260714/rpe-b-goal-loop-hardening/handoff.md
./.omc/tasks/20260714/e2e-lifecycle-test/handoff.md
./.omc/tasks/20260712/phase0.5-docs-infra/handoff.md
./.omc/tasks/20260712/phase2-flywheel/handoff.md
./.omc/tasks/20260717/rpe-f-ten-features-revival/handoff.md
./.omc/tasks/20260710/e2e_smoke_20260710/state/session-handoff.md
./.omc/tasks/20260718/skill-hook-adaptive-opt/handoff.md
./.omc/archive/cap-test-001/session-handoff.md
./.omc/archive/bench-06/session-handoff.md
./.omc/archive/bench-01/session-handoff.md
./.omc/archive/bench-07/session-handoff.md
./.omc/archive/test-full-goal/session-handoff.md
./.omc/archive/CarrorOS-vs-Sylph/session-handoff.md
./.omc/archive/rpe-f-ten-features-revival/session-handoff.md
./.omc/archive/smoke-test-01/session-handoff.md
./.omc/archive/round3-fixes/session-handoff.md
./.omc/archive/oracle-engine-fix-01/session-handoff.md
```

## 块 B:handoff 多源与计数

### `.claude/scripts/context_engine.py` — B4 compact-write 所在,全文

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS Context Engine
     4	
     5	Purpose:
     6	  Manage compact / resume / state injection without creating completion facts.
     7	
     8	Commands:
     9	  compact-check   --token <path> [--task <path>]
    10	  resume-check    --token <path> --task <path>
    11	  state-injection --token <path>
    12	
    13	Constraints:
    14	  - Python 3.10+ standard library only
    15	  - Does not mark plan steps done
    16	  - Does not alter executor evidence
    17	  - Does not replace VerifyGate / Oracle / Fallback
    18	"""
    19	
    20	from __future__ import annotations
    21	
    22	import argparse
    23	import json
    24	import os
    25	import re
    26	import sys
    27	from dataclasses import dataclass, asdict
    28	from datetime import datetime, timezone
    29	from pathlib import Path
    30	from typing import Any
    31	
    32	# 从自身位置定位项目根目录
    33	_script_path = Path(__file__).resolve()
    34	ROOT = _script_path.parents[2]  # .claude/scripts/ → .claude/ → 项目根
    35	if not (ROOT / ".claude").is_dir():
    36	    ROOT = Path(".").resolve()
    37	os.chdir(str(ROOT))
    38	
    39	
    40	@dataclass
    41	class ContextDecision:
    42	    decision: str
    43	    reason: str
    44	    task_id: str
    45	    task_name: str
    46	    level: str
    47	    current_step: str | None
    48	    compact_strategy: str
    49	    requires_fallback: bool = False
    50	    failure_type: str | None = None
    51	
    52	
    53	def now_iso() -> str:
    54	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    55	
    56	
    57	def today() -> str:
    58	    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    59	
    60	
    61	def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    62	    if not path.exists():
    63	        return default or {}
    64	    with path.open("r", encoding="utf-8") as f:
    65	        return json.load(f)
    66	
    67	
    68	def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    69	    path.parent.mkdir(parents=True, exist_ok=True)
    70	    tmp = path.with_suffix(path.suffix + ".tmp")
    71	    with tmp.open("w", encoding="utf-8") as f:
    72	        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    73	        f.write("\n")
    74	    tmp.replace(path)
    75	
    76	
    77	def read_text(path: Path) -> str:
    78	    if not path.exists():
    79	        return ""
    80	    return path.read_text(encoding="utf-8")
    81	
    82	
    83	def write_text(path: Path, text: str) -> None:
    84	    path.parent.mkdir(parents=True, exist_ok=True)
    85	    path.write_text(text, encoding="utf-8")
    86	
    87	
    88	def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    89	    path.parent.mkdir(parents=True, exist_ok=True)
    90	    with path.open("a", encoding="utf-8") as f:
    91	        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    92	
    93	
    94	def token_task(token: dict[str, Any]) -> dict[str, Any]:
    95	    task = token.get("task", {})
    96	    # 兼容非 carros token（如 lx-goal 物理锁：task 是字符串）
    97	    return task if isinstance(task, dict) else {}
    98	
    99	
   100	def token_session(token: dict[str, Any]) -> dict[str, Any]:
   101	    session = token.get("session", {})
   102	    return session if isinstance(session, dict) else {}
   103	
   104	
   105	def task_id(token: dict[str, Any], fallback: str = "unknown_task") -> str:
   106	    return token_task(token).get("id") or fallback
   107	
   108	
   109	def task_name(token: dict[str, Any], fallback: str = "task") -> str:
   110	    return token_task(token).get("name") or fallback
   111	
   112	
   113	def level(token: dict[str, Any]) -> str:
   114	    return token_session(token).get("level", "L1_BASE")
   115	
   116	
   117	def current_step(token: dict[str, Any]) -> str | None:
   118	    return token_task(token).get("current_step")
   119	
   120	
   121	def count_plan_steps(plan_text: str) -> tuple[int, int, str | None]:
   122	    total = len(re.findall(r"^\s*[-*]\s+\[[ xX]\]\s+", plan_text, flags=re.M))
   123	    done = len(re.findall(r"^\s*[-*]\s+\[[xX]\]\s+", plan_text, flags=re.M))
   124	    pending_match = re.search(r"^\s*[-*]\s+\[\s\]\s+(.+)$", plan_text, flags=re.M)
   125	    pending = pending_match.group(1).strip() if pending_match else None
   126	    return done, total, pending
   127	
   128	
   129	def compact_decision(token: dict[str, Any]) -> tuple[str, str, str, bool, str | None]:
   130	    session = token_session(token)
   131	    lvl = level(token)
   132	
   133	    if lvl == "L2_ENHANCE":
   134	        watermark = session.get("context_watermark")
   135	        if not isinstance(watermark, (int, float)):
   136	            return (
   137	                "DOWNGRADE_REQUIRED",
   138	                "context_watermark_unobservable",
   139	                "watermark",
   140	                True,
   141	                "context_watermark_unobservable",
   142	            )
   143	        if watermark >= 85:
   144	            return ("COMPACT_NOW", "watermark_ge_85", "watermark", False, None)
   145	        if watermark >= 70:
   146	            return ("COMPACT_SOON", "watermark_ge_70", "watermark", False, None)
   147	        return ("CONTINUE", "watermark_lt_70", "watermark", False, None)
   148	
   149	    turn = int(session.get("turn", 0) or 0)
   150	    if turn >= 20:
   151	        return ("COMPACT_NOW", "turn_ge_20", "rounds", False, None)
   152	    if turn >= 15:
   153	        return ("COMPACT_SOON", "turn_ge_15", "rounds", False, None)
   154	    return ("CONTINUE", "turn_lt_15", "rounds", False, None)
   155	
   156	
   157	def build_handoff(token: dict[str, Any], plan_text: str, decision: str, reason: str) -> str:
   158	    task = token_task(token)
   159	    session = token_session(token)
   160	    done, total, pending = count_plan_steps(plan_text)
   161	
   162	    scope = task.get("scope", []) or []
   163	    risks = task.get("risk_hints", []) or []
   164	    changed_files = task.get("changed_files", []) or []
   165	
   166	    def bullet(items: list[Any], fallback: str = "- none") -> str:
   167	        if not items:
   168	            return fallback
   169	        return "\n".join(f"- {str(item)}" for item in items)
   170	
   171	    return f"""# Session Handoff
   172	
   173	## Task
   174	- id: {task_id(token)}
   175	- name: {task_name(token)}
   176	- level: {level(token)}
   177	- status: {task.get("status", "active")}
   178	- current_step: {current_step(token)}
   179	
   180	## Goal
   181	{task.get("goal", "N/A")}
   182	
   183	## Scope Freeze
   184	{bullet(scope)}
   185	
   186	## Progress
   187	- total_steps: {total}
   188	- verified_steps: {done}
   189	- pending_step: {pending or "none"}
   190	
   191	## Current Work
   192	- step: {current_step(token)}
   193	- files_in_scope:
   194	{bullet(changed_files)}
   195	
   196	## Risks
   197	{bullet(risks)}
   198	
   199	## Context
   200	- compact_strategy: {session.get("compact_strategy", "rounds")}
   201	- context_watermark: {session.get("context_watermark", "unknown")}
   202	- turn: {session.get("turn", 0)}
   203	- compact_status: {decision}
   204	- compact_reason: {reason}
   205	
   206	## Oracle
   207	- last_verdict: {session.get("oracle_last_verdict", "none")}
   208	- residual_risk: {len(session.get("residual_risk", []) or [])}
   209	
   210	## Fallback
   211	- unresolved: {bool(task.get("blocked") or task.get("status") == "waiting_user")}
   212	- last_event: {task.get("blocked") or "none"}
   213	
   214	## Resume Instructions
   215	- read token first
   216	- read plan second
   217	- read executor tail third
   218	- do not mark any step complete without VerifyGate
   219	"""
   220	
   221	
   222	def write_context_state(path: Path, token: dict[str, Any], decision: str, strategy: str) -> None:
   223	    session = token_session(token)
   224	    state = {
   225	        "task_id": task_id(token),
   226	        "task_name": task_name(token),
   227	        "level": level(token),
   228	        "compact_strategy": strategy,
   229	        "turn": session.get("turn", 0),
   230	        "context_watermark": session.get("context_watermark"),
   231	        "compact_status": decision,
   232	        "last_handoff_at": now_iso(),
   233	        "last_state_injection_at": session.get("last_state_injection_at"),
   234	        "resume": session.get("resume", {}),
   235	    }
   236	    write_json_atomic(path, state)
   237	
   238	
   239	def audit_event(token: dict[str, Any], decision: str, reason: str, strategy: str, paths: list[str]) -> dict[str, Any]:
   240	    session = token_session(token)
   241	    return {
   242	        "event_type": "context_compact",
   243	        "timestamp": now_iso(),
   244	        "task_id": task_id(token),
   245	        "level": level(token),
   246	        "phase": "context",
   247	        "actor": "context_engine",
   248	        "decision": decision,
   249	        "reason": reason,
   250	        "compact_strategy": strategy,
   251	        "context_watermark": session.get("context_watermark"),
   252	        "turn": session.get("turn", 0),
   253	        "current_step": current_step(token),
   254	        "paths": paths,
   255	    }
   256	
   257	
   258	def latest_audit_events(task_id_value: str, limit: int = 50) -> list[dict[str, Any]]:
   259	    audit_root = ROOT / ".omc" / "audit"
   260	    events: list[dict[str, Any]] = []
   261	    if not audit_root.exists():
   262	        return events
   263	
   264	    for path in sorted(audit_root.glob("*.jsonl")):
   265	        with path.open("r", encoding="utf-8") as f:
   266	            for line in f:
   267	                try:
   268	                    event = json.loads(line)
   269	                except json.JSONDecodeError:
   270	                    continue
   271	                if event.get("task_id") == task_id_value:
   272	                    events.append(event)
   273	    return events[-limit:]
   274	
   275	
   276	def unresolved_failure(events: list[dict[str, Any]]) -> str | None:
   277	    for event in reversed(events):
   278	        if event.get("event_type") == "fallback_event" and event.get("decision") in {"BLOCKED", "ASK_USER"}:
   279	            return str(event.get("reason", "fallback_unresolved"))
   280	    return None
   281	
   282	
   283	def resume_check(token_path: Path, task_path: Path) -> ContextDecision:
   284	    token = read_json(token_path, {})
   285	    if not token:
   286	        return ContextDecision(
   287	            "RESUME_BLOCKED",
   288	            "token_missing",
   289	            token_path.stem,
   290	            task_path.name,
   291	            "L1_BASE",
   292	            None,
   293	            "unknown",
   294	            True,
   295	            "resume_state_unrecoverable",
   296	        )
   297	
   298	    plan_text = read_text(task_path / "plan.md")
   299	    executor_text = read_text(task_path / "executor.md")
   300	
   301	    if not plan_text:
   302	        reason = "plan_missing"
   303	    elif not executor_text:
   304	        reason = "executor_missing"
   305	    else:
   306	        done, total, pending = count_plan_steps(plan_text)
   307	        stats = token.get("stats", {}) or {}
   308	        if stats.get("done") != done or stats.get("total") != total:
   309	            reason = "state_conflict"
   310	        elif pending and current_step(token) and current_step(token) not in (pending or ""):
   311	            reason = "state_conflict"
   312	        else:
   313	            events = latest_audit_events(task_id(token))
   314	            failure = unresolved_failure(events)
   315	            if failure:
   316	                reason = failure
   317	            else:
   318	                reason = "ok"
   319	
   320	    if reason != "ok":
   321	        return ContextDecision(
   322	            "RESUME_BLOCKED",
   323	            reason,
   324	            task_id(token, token_path.stem),
   325	            task_name(token, task_path.name),
   326	            level(token),
   327	            current_step(token),
   328	            token_session(token).get("compact_strategy", "unknown"),
   329	            True,
   330	            "resume_state_unrecoverable" if reason != "state_conflict" else "state_conflict",
   331	        )
   332	
   333	    append_jsonl(
   334	        ROOT / ".omc" / "audit" / f"{today()}.jsonl",
   335	        {
   336	            "event_type": "context_resume",
   337	            "timestamp": now_iso(),
   338	            "task_id": task_id(token),
   339	            "level": level(token),
   340	            "phase": "context",
   341	            "actor": "context_engine",
   342	            "decision": "RESUME_OK",
   343	            "current_step": current_step(token),
   344	            "source_order": [
   345	                "token",
   346	                "session-handoff",
   347	                "plan",
   348	                "executor-tail",
   349	                "audit-tail",
   350	                "oracle-verdicts",
   351	                "error-dna",
   352	                "fallback-tail",
   353	            ],
   354	        },
   355	    )
   356	
   357	    return ContextDecision(
   358	        "RESUME_OK",
   359	        "state_consistent",
   360	        task_id(token, token_path.stem),
   361	        task_name(token, task_path.name),
   362	        level(token),
   363	        current_step(token),
   364	        token_session(token).get("compact_strategy", "unknown"),
   365	    )
   366	
   367	
   368	def compact_check(token_path: Path, task_path: Path) -> ContextDecision:
   369	    token = read_json(token_path, {})
   370	    if not token:
   371	        return ContextDecision(
   372	            "RESUME_BLOCKED",
   373	            "token_missing",
   374	            token_path.stem,
   375	            task_path.name,
   376	            "L1_BASE",
   377	            None,
   378	            "unknown",
   379	            True,
   380	            "resume_state_unrecoverable",
   381	        )
   382	
   383	    plan_text = read_text(task_path / "plan.md")
   384	    decision, reason, strategy, needs_fallback, failure_type = compact_decision(token)
   385	
   386	    handoff_path = task_path / "state" / "session-handoff.md"
   387	    context_state_path = task_path / "state" / "context-state.json"
   388	    audit_path = ROOT / ".omc" / "audit" / f"{today()}.jsonl"
   389	
   390	    if decision in {"COMPACT_SOON", "COMPACT_NOW"}:
   391	        write_text(handoff_path, build_handoff(token, plan_text, decision, reason))
   392	        write_context_state(context_state_path, token, decision, strategy)
   393	        append_jsonl(
   394	            audit_path,
   395	            audit_event(
   396	                token,
   397	                decision,
   398	                reason,
   399	                strategy,
   400	                [str(handoff_path), str(context_state_path)],
   401	            ),
   402	        )
   403	
   404	    return ContextDecision(
   405	        decision,
   406	        reason,
   407	        task_id(token, token_path.stem),
   408	        task_name(token, task_path.name),
   409	        level(token),
   410	        current_step(token),
   411	        strategy,
   412	        needs_fallback,
   413	        failure_type,
   414	    )
   415	
   416	
   417	def state_injection(token_path: Path) -> str:
   418	    token = read_json(token_path, {})
   419	    task = token_task(token)
   420	    session = token_session(token)
   421	    stats = token.get("stats", {}) or {}
   422	
   423	    fallback = "none"
   424	    if task.get("status") == "waiting_user":
   425	        fallback = "waiting_user"
   426	    elif task.get("status") == "blocked":
   427	        fallback = str(task.get("blocked", "blocked"))
   428	
   429	    watermark = session.get("context_watermark", "unknown")
   430	    return (
   431	        "[CarrorOS State]\n"
   432	        f"task_id={task_id(token, token_path.stem)}\n"
   433	        f"level={level(token)}\n"
   434	        f"status={task.get('status', 'active')}\n"
   435	        f"current_step={current_step(token)}\n"
   436	        f"verified={stats.get('done', 0)}/{stats.get('total', 0)}\n"
   437	        f"compact={session.get('compact_status', 'unknown')} watermark={watermark}\n"
   438	        f"fallback={fallback}\n"
   439	        f"oracle_last={session.get('oracle_last_verdict', 'none')}\n"
   440	        "rule=do_not_mark_step_done_without_VerifyGate\n"
   441	    )
   442	
   443	
   444	def compact_write(token_path: Path, task_path: Path, user_prompt: str = "") -> int:
   445	    """写入 .omc/session-handoff.md 和 .omc/state/last-user-prompt.md
   446	    供 @ 引用，下次会话自动注入上下文。
   447	    无 hook 参与，纯文件写入。
   448	    同时读取 .claude/.prompt-ring.json 收集最近 20 轮用户 prompt。
   449	    """
   450	    handoff_path = ROOT / ".omc" / "session-handoff.md"
   451	    prompt_path = ROOT / ".omc" / "state" / "last-user-prompt.md"
   452	    ring_path = ROOT / ".claude" / ".prompt-ring.json"
   453	
   454	    token = read_json(token_path, {})
   455	    task = token_task(token)
   456	    session = token_session(token)
   457	    stats = token.get("stats", {}) or {}
   458	    plan_text = read_text(task_path / "plan.md")
   459	
   460	    done, total, pending = count_plan_steps(plan_text)
   461	    scope = task.get("scope", []) or []
   462	    failed_verifications = task.get("failed_verifications", 0)
   463	    oracle_last = session.get("oracle_last_verdict", "none")
   464	
   465	    # 写入 session-handoff.md（完整任务状态）
   466	    scope_bullets = "\n".join(f"  - {s}" for s in scope) if scope else "  - (none)"
   467	
   468	    level_str = level(token)
   469	    status = task.get("status", "active")
   470	    current = current_step(token) or "(none)"
   471	    compact_strategy = session.get("compact_strategy", "rounds")
   472	
   473	    handoff_content = f"""# Session Handoff
   474	
   475	> 由 context_engine compact-write 于 {now_iso()} 更新
   476	> AGENTS.md 已 @ 引用本文件，启动时自动加载
   477	
   478	## Task
   479	- id: {task_id(token, token_path.stem)}
   480	- level: {level_str}
   481	- status: {status}
   482	- current_step: {current}
   483	
   484	## Progress
   485	- verified: {done}/{total}
   486	- pending: {pending or "(none)"}
   487	- compact_strategy: {compact_strategy}
   488	- failed_verifications: {failed_verifications}
   489	
   490	## Scope
   491	{scope_bullets}
   492	
   493	## Oracle
   494	- last_verdict: {oracle_last}
   495	
   496	## Resume Rules
   497	- 磁盘状态文件是最终真相源（token / plan / executor）
   498	- session-handoff 只是恢复摘要，不是完成证据
   499	- 不要标记任何 step 完成不经过 VerifyGate
   500	"""
   501	    handoff_path.parent.mkdir(parents=True, exist_ok=True)
   502	    handoff_path.write_text(handoff_content, encoding="utf-8")
   503	
   504	    # 读取 prompt ring 写入 last-user-prompt.md
   505	    ring = []
   506	    if ring_path.exists():
   507	        try:
   508	            ring = json.loads(ring_path.read_text(encoding="utf-8"))
   509	            if not isinstance(ring, list):
   510	                ring = []
   511	        except (json.JSONDecodeError, OSError):
   512	            ring = []
   513	
   514	    # 用传入的 --prompt 补上最新一条
   515	    if user_prompt and (not ring or ring[-1].get("prompt", "") != user_prompt[:500]):
   516	        ring.append({
   517	            "ts": now_iso(),
   518	            "prompt": user_prompt[:500],
   519	        })
   520	    if len(ring) > 20:
   521	        ring = ring[-20:]
   522	
   523	    if ring:
   524	        prompt_lines = []
   525	        for i, entry in enumerate(ring):
   526	            ts = entry.get("ts", "?")
   527	            p = entry.get("prompt", "").replace("\n", " ")
   528	            prompt_lines.append(f"[{i+1}] ({ts}) {p[:200]}")
   529	        prompt_text = "\n".join(prompt_lines)
   530	    else:
   531	        prompt_text = "(无历史 prompt)"
   532	
   533	    prompt_content = f"""> 由 context_engine compact-write 于 {now_iso()} 更新
   534	> 记录 compact 前的最近 {len(ring)} 轮用户请求，帮助恢复上下文
   535	
   536	## 最近用户请求（共 {len(ring)} 条）
   537	
   538	{prompt_text}
   539	
   540	---
   541	"""
   542	    prompt_path.write_text(prompt_content, encoding="utf-8")
   543	
   544	    # audit
   545	    append_jsonl(
   546	        ROOT / ".omc" / "audit" / f"{today()}.jsonl",
   547	        {
   548	            "event_type": "compact_write",
   549	            "timestamp": now_iso(),
   550	            "task_id": task_id(token, token_path.stem),
   551	            "level": level_str,
   552	            "phase": "context",
   553	            "actor": "context_engine",
   554	            "paths": [str(handoff_path), str(prompt_path)],
   555	        },
   556	    )
   557	
   558	    # 同时更新 task_dir 下的 state/session-handoff.md（已有逻辑兼容）
   559	    state_handoff = task_path / "state" / "session-handoff.md"
   560	    state_handoff.parent.mkdir(parents=True, exist_ok=True)
   561	    state_handoff.write_text(handoff_content, encoding="utf-8")
   562	
   563	    print(json.dumps({
   564	        "handoff_path": str(handoff_path),
   565	        "prompt_path": str(prompt_path),
   566	        "prompt_written": bool(user_prompt),
   567	        "status": "OK",
   568	    }, ensure_ascii=False, indent=2))
   569	    return 0
   570	
   571	
   572	def main() -> int:
   573	    parser = argparse.ArgumentParser()
   574	    parser.add_argument("command", choices=["compact-check", "resume-check", "state-injection", "compact-write"])
   575	    parser.add_argument("--token", required=True)
   576	    parser.add_argument("--task", required=False)
   577	    parser.add_argument("--prompt", required=False, default="")
   578	    args = parser.parse_args()
   579	
   580	    token_path = Path(args.token)
   581	    task_path = Path(args.task) if args.task else Path(".")
   582	
   583	    try:
   584	        if args.command == "compact-check":
   585	            result = compact_check(token_path, task_path)
   586	            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
   587	            return 1 if result.requires_fallback else 0
   588	
   589	        if args.command == "resume-check":
   590	            result = resume_check(token_path, task_path)
   591	            print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
   592	            return 0 if result.decision == "RESUME_OK" else 1
   593	
   594	        if args.command == "state-injection":
   595	            print(state_injection(token_path))
   596	            return 0
   597	
   598	        if args.command == "compact-write":
   599	            return compact_write(token_path, task_path, args.prompt)
   600	
   601	    except OSError as exc:
   602	        result = ContextDecision(
   603	            "RESUME_BLOCKED",
   604	            "audit_or_state_write_failed",
   605	            token_path.stem,
   606	            task_path.name,
   607	            "L1_BASE",
   608	            None,
   609	            "unknown",
   610	            True,
   611	            "audit_write_failed",
   612	        )
   613	        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
   614	        return 1
   615	
   616	    parser.print_help()
   617	    return 2
   618	
   619	
   620	if __name__ == "__main__":
   621	    raise SystemExit(main())
```

### `.claude/hooks/pretool-user-approve.py` — B4 prompt 环注入,全文

```
     1	#!/usr/bin/env python3
     2	"""
     3	pretool-user-approve.py — CarrorOS Unified UserPromptSubmit Gate
     4	
     5	Multiplexes (single hook, Base lightweight philosophy):
     6	  1. /approve <token> /deny — CAPTCHA approval for blocked tasks
     7	  2. Prompt ring — rolling 20 user prompts (.claude/.prompt-ring.json)
     8	  3. Every 5th prompt — detached compact-write (refreshes handoff + last-user-prompt)
     9	  4. Every 5th prompt — U-attention tail injection (task state via additionalContext)
    10	  5. Goal mode — appends goal state when autonomous.active exists
    11	
    12	Constraints:
    13	  - Never blocks: always exit 0
    14	  - Fast path <100ms on non-5th rounds (ring append only)
    15	  - compact-write runs detached (Popen, no wait) — hook never waits on it
    16	"""
    17	import json
    18	import os
    19	import re
    20	import subprocess
    21	import sys
    22	from datetime import datetime, timezone
    23	from pathlib import Path
    24	
    25	HOOK_DIR = Path(__file__).resolve().parent
    26	ROOT = HOOK_DIR.parents[1]
    27	os.chdir(str(ROOT))
    28	
    29	STATE_DIR = ROOT / ".omc" / "state"
    30	FALLBACK_REQUIRED = STATE_DIR / "fallback-blocked-required"
    31	FALLBACK_APPROVED = STATE_DIR / "fallback-blocked-approved"
    32	GOAL_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
    33	GOAL_STATE = STATE_DIR / "tokens" / "lx-goal.json"
    34	TOKENS_DIR = ROOT / ".omc" / "tokens"
    35	RING_PATH = ROOT / ".claude" / ".prompt-ring.json"
    36	RING_STATE = ROOT / ".claude" / ".prompt-ring-state.json"
    37	CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"
    38	
    39	MAX_RING = 20
    40	INJECT_INTERVAL = 5  # 每 5 轮：compact-write + 尾部状态注入（U 型注意力）
    41	
    42	
    43	def _now_iso() -> str:
    44	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    45	
    46	
    47	def _read_json(path: Path, default):
    48	    try:
    49	        return json.loads(path.read_text(encoding="utf-8"))
    50	    except Exception:
    51	        return default
    52	
    53	
    54	def _latest_token() -> Path | None:
    55	    """Latest carros task token (skips lx-goal lock tokens etc. with non-dict task)."""
    56	    if not TOKENS_DIR.exists():
    57	        return None
    58	    candidates = sorted(
    59	        [p for p in TOKENS_DIR.glob("*/*.json") if p.is_file()],
    60	        key=lambda p: p.stat().st_mtime, reverse=True,
    61	    )
    62	    for path in candidates[:5]:
    63	        data = _read_json(path, {})
    64	        if isinstance(data.get("task"), dict) and isinstance(data.get("stats"), dict):
    65	            return path
    66	    return candidates[0] if candidates else None
    67	
    68	
    69	def _extract_prompt(raw: str) -> str:
    70	    """Payload may be JSON {prompt: ...} or raw text."""
    71	    try:
    72	        data = json.loads(raw)
    73	        if isinstance(data, dict):
    74	            for key in ("prompt", "text", "message", "input"):
    75	                val = data.get(key)
    76	                if isinstance(val, str) and val.strip():
    77	                    return val.strip()
    78	    except (json.JSONDecodeError, ValueError):
    79	        pass
    80	    return raw.strip()
    81	
    82	
    83	def _update_ring(prompt: str) -> int:
    84	    """Append prompt to ring (max 20). Returns total prompt count."""
    85	    ring = _read_json(RING_PATH, [])
    86	    if not isinstance(ring, list):
    87	        ring = []
    88	    ring.append({"ts": _now_iso(), "prompt": prompt[:500]})
    89	    ring = ring[-MAX_RING:]
    90	    RING_PATH.write_text(json.dumps(ring, ensure_ascii=False, indent=2), encoding="utf-8")
    91	
    92	    state = _read_json(RING_STATE, {})
    93	    total = int(state.get("total", 0)) + 1
    94	    RING_STATE.write_text(json.dumps({"total": total, "updated_at": _now_iso()}), encoding="utf-8")
    95	    return total
    96	
    97	
    98	def _state_injection_text(token_path: Path) -> str:
    99	    """Inline fast state injection (context_engine state-injection)."""
   100	    try:
   101	        proc = subprocess.run(
   102	            [sys.executable, str(CONTEXT_ENGINE), "state-injection", "--token", str(token_path)],
   103	            capture_output=True, text=True, timeout=5, cwd=str(ROOT),
   104	        )
   105	        return proc.stdout.strip()
   106	    except Exception:
   107	        return ""
   108	
   109	
   110	def _goal_state_text() -> str:
   111	    data = _read_json(GOAL_STATE, {})
   112	    if not isinstance(data, dict) or not data:
   113	        return ""
   114	    goal = data.get("goal", "")
   115	    done = data.get("done", [])
   116	    skipped = data.get("skipped_risks", [])
   117	    lines = ["[Goal Mode]", f"goal={goal}", f"done={len(done)} skipped={len(skipped)}"]
   118	    if done:
   119	        lines.append(f"last_done={done[-1]}")
   120	    return "\n".join(lines)
   121	
   122	
   123	def _every_fifth_round(token_path: Path | None) -> str:
   124	    """Returns injection text; kicks off detached compact-write."""
   125	    if token_path:
   126	        # Detached compact-write — refreshes handoff.md + last-user-prompt.md
   127	        try:
   128	            subprocess.Popen(
   129	                [sys.executable, str(CONTEXT_ENGINE), "compact-write", "--token", str(token_path)],
   130	                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
   131	                cwd=str(ROOT), start_new_session=True,
   132	            )
   133	        except Exception:
   134	            pass
   135	        injection = _state_injection_text(token_path)
   136	    else:
   137	        injection = ""
   138	
   139	    if GOAL_SIGNAL.exists():
   140	        goal_text = _goal_state_text()
   141	        if goal_text:
   142	            injection = f"{injection}\n{goal_text}" if injection else goal_text
   143	    return injection
   144	
   145	
   146	def main() -> None:
   147	    raw = sys.stdin.read()
   148	    prompt = _extract_prompt(raw)
   149	
   150	    # ─── /deny — clear approval state ───
   151	    if re.search(r'(?:^|[^a-zA-Z0-9_])/deny\b', prompt):
   152	        _safe_unlink(FALLBACK_REQUIRED)
   153	        _safe_unlink(FALLBACK_APPROVED)
   154	        print("🚫 /deny — 阻塞状态已清除。如需重新启用可输入 /approve <token>。",
   155	              file=sys.stderr, flush=True)
   156	        print(json.dumps({"continue": True}))
   157	        sys.exit(0)
   158	
   159	    # ─── /approve <token> — validate and approve ───
   160	    match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', prompt)
   161	    if match:
   162	        token = match.group(1)
   163	        if not FALLBACK_REQUIRED.exists():
   164	            print("ℹ️ /approve 忽略：当前无待解除的阻塞状态。",
   165	                  file=sys.stderr, flush=True)
   166	            print(json.dumps({"continue": True}))
   167	            sys.exit(0)
   168	        expected = FALLBACK_REQUIRED.read_text().strip()
   169	        if token == expected:
   170	            FALLBACK_APPROVED.write_text(token)
   171	            print("✅ /approve 已接受！任务阻塞将在下次操作时自动解除。",
   172	                  file=sys.stderr, flush=True)
   173	        else:
   174	            print("❌ /approve 失败：验证码不匹配。请检查输入的 token。",
   175	                  file=sys.stderr, flush=True)
   176	        print(json.dumps({"continue": True}))
   177	        sys.exit(0)
   178	
   179	    # ─── Prompt ring (every round, fast) ───
   180	    if prompt and not prompt.startswith("/"):
   181	        try:
   182	            total = _update_ring(prompt)
   183	        except Exception:
   184	            total = 0
   185	    else:
   186	        total = 0
   187	
   188	    # ─── Every 5th round: compact-write (detached) + tail injection ───
   189	    if total > 0 and total % INJECT_INTERVAL == 0:
   190	        try:
   191	            injection = _every_fifth_round(_latest_token())
   192	        except Exception:
   193	            injection = ""
   194	        if injection:
   195	            print(json.dumps({
   196	                "continue": True,
   197	                "hookSpecificOutput": {
   198	                    "hookEventName": "UserPromptSubmit",
   199	                    "additionalContext": injection,
   200	                },
   201	            }, ensure_ascii=False))
   202	            sys.exit(0)
   203	
   204	    print(json.dumps({"continue": True}))
   205	    sys.exit(0)
   206	
   207	
   208	def _safe_unlink(path: Path) -> None:
   209	    try:
   210	        if path.exists():
   211	            path.unlink()
   212	    except OSError:
   213	        pass
   214	
   215	
   216	if __name__ == "__main__":
   217	    main()
```

### `state/session-handoff.md` — B4 副本 1

```
     1	# Session Handoff
     2	
     3	> 由 context_engine compact-write 于 2026-07-18T19:46:23+00:00 更新
     4	> AGENTS.md 已 @ 引用本文件，启动时自动加载
     5	
     6	## Task
     7	- id: skill-hook-adaptive-opt
     8	- level: L2_ENHANCE
     9	- status: active
    10	- current_step: S1
    11	
    12	## Progress
    13	- verified: 0/0
    14	- pending: (none)
    15	- compact_strategy: rounds
    16	- failed_verifications: 0
    17	
    18	## Scope
    19	  - (none)
    20	
    21	## Oracle
    22	- last_verdict: none
    23	
    24	## Resume Rules
    25	- 磁盘状态文件是最终真相源（token / plan / executor）
    26	- session-handoff 只是恢复摘要，不是完成证据
    27	- 不要标记任何 step 完成不经过 VerifyGate
```

### `.omc/session-handoff.md` — B4 副本 2

```
     1	# Session Handoff
     2	
     3	> 由 context_engine compact-write 于 2026-07-18T19:46:23+00:00 更新
     4	> AGENTS.md 已 @ 引用本文件，启动时自动加载
     5	
     6	## Task
     7	- id: skill-hook-adaptive-opt
     8	- level: L2_ENHANCE
     9	- status: active
    10	- current_step: S1
    11	
    12	## Progress
    13	- verified: 0/0
    14	- pending: (none)
    15	- compact_strategy: rounds
    16	- failed_verifications: 0
    17	
    18	## Scope
    19	  - (none)
    20	
    21	## Oracle
    22	- last_verdict: none
    23	
    24	## Resume Rules
    25	- 磁盘状态文件是最终真相源（token / plan / executor）
    26	- session-handoff 只是恢复摘要，不是完成证据
    27	- 不要标记任何 step 完成不经过 VerifyGate
```

### `.omc/state/token.json` — B5 计数真相源(当前 active token)

```
     1	{
     2	  "schema_version": 3,
     3	  "session": {
     4	    "clean": true,
     5	    "note": "Cleaned stale blocked state from 2026-07-07. See per-task tokens in .omc/tokens/",
     6	    "cleaned_at": "2026-07-09T12:00:00Z"
     7	  },
     8	  "task": null
     9	}
```

## 块 C:goal/ghost 状态

### `.omc/scripts/goal_state_machine.py` — C7/C8 goal 状态机

```
     1	#!/usr/bin/env python3
     2	"""
     3	goal_state_machine.py — Goal 自闭环状态机
     4	
     5	Pipeline: CLARIFY → PLANNING → EXECUTING → VERIFYING → ARCHIVING → ARCHIVED
     6	
     7	每个状态可前/后向转换。自动推进规则：
     8	  - intent/goal 缺失时自动回退 CLARIFY
     9	  - 全部 AC verified → 自动推 ARCHIVING
    10	  - archive 成功 → ARCHIVED
    11	
    12	Usage:
    13	    from goal_state_machine import GoalMachine, GoalStatus
    14	
    15	Usage:
    16	    gm = GoalMachine(token_path)
    17	    gm.transition("VERIFYING")
    18	    print(gm.current_state)
    19	"""
    20	
    21	import json
    22	from datetime import datetime, timezone
    23	from pathlib import Path
    24	
    25	# ─── State Constants ───
    26	CLARIFY = "CLARIFY"
    27	PLANNING = "PLANNING"
    28	EXECUTING = "EXECUTING"
    29	VERIFYING = "VERIFYING"
    30	ARCHIVING = "ARCHIVING"
    31	ARCHIVED = "ARCHIVED"
    32	
    33	ALL_STATES = [CLARIFY, PLANNING, EXECUTING, VERIFYING, ARCHIVING, ARCHIVED]
    34	
    35	# ─── Valid Transitions ───
    36	_VALID_TRANSITIONS = {
    37	    None: [CLARIFY],                  # 初始状态 -> CLARIFY
    38	    CLARIFY: [PLANNING, CLARIFY],     # 澄清后可进 PLANNING，或继续澄清
    39	    PLANNING: [EXECUTING, CLARIFY],   # 计划后执行，或回 CLARIFY（需求变更）
    40	    EXECUTING: [VERIFYING, CLARIFY],  # 执行后验证，或回 CLARIFY
    41	    VERIFYING: [ARCHIVING, EXECUTING, CLARIFY],  # 验证后归档/回执行/回澄清
    42	    ARCHIVING: [ARCHIVED, VERIFYING], # 归档中 -> 完成或回验证
    43	    ARCHIVED: [],                     # 终态
    44	}
    45	
    46	
    47	class GoalError(Exception):
    48	    """GoalMachine 状态转换异常"""
    49	    pass
    50	
    51	
    52	class GoalMachine:
    53	    """Goal 状态机 — 管理任务生命周期状态转换"""
    54	
    55	    def __init__(self, token_path=None, spec_path=None):
    56	        self.token_path = Path(token_path) if token_path else None
    57	        self.spec_path = spec_path
    58	        self._state = None
    59	
    60	        # 尝试从 token 恢复状态
    61	        if self.token_path and self.token_path.exists():
    62	            try:
    63	                token = json.loads(self.token_path.read_text())
    64	                self._state = token.get("goal", {}).get("state")
    65	            except (json.JSONDecodeError, OSError):
    66	                pass
    67	
    68	        if self._state not in ALL_STATES:
    69	            self._state = None  # 还未初始化
    70	
    71	    @property
    72	    def current_state(self):
    73	        return self._state
    74	
    75	    @property
    76	    def is_terminal(self):
    77	        return self._state == ARCHIVED
    78	
    79	    def can_transition(self, target_state):
    80	        """检查 target_state 是否合法"""
    81	        return target_state in _VALID_TRANSITIONS.get(self._state, [])
    82	
    83	    def transition(self, target_state, token=None, reason=""):
    84	        """尝试状态转换 — 验证合法性 + 更新 token（如有）"""
    85	        if target_state not in ALL_STATES:
    86	            raise GoalError(f"Unknown state: {target_state}")
    87	
    88	        valid = _VALID_TRANSITIONS.get(self._state, [])
    89	        if target_state not in valid:
    90	            raise GoalError(
    91	                f"Invalid transition: {self._state} → {target_state} "
    92	                f"(allowed: {valid})"
    93	            )
    94	
    95	        old_state = self._state
    96	        self._state = target_state
    97	
    98	        # 更新 token
    99	        token_data = token
   100	        if token_data is None and self.token_path and self.token_path.exists():
   101	            try:
   102	                token_data = json.loads(self.token_path.read_text())
   103	            except (json.JSONDecodeError, OSError):
   104	                pass
   105	
   106	        if token_data is not None:
   107	            if "goal" not in token_data:
   108	                token_data["goal"] = {}
   109	            token_data["goal"]["state"] = target_state
   110	            token_data["goal"]["previous_state"] = old_state
   111	            token_data["goal"]["transitions"] = token_data["goal"].get("transitions", 0) + 1
   112	            token_data["goal"]["last_transition"] = datetime.now(timezone.utc).isoformat()
   113	            if reason:
   114	                token_data["goal"]["last_reason"] = reason
   115	            if self.token_path:
   116	                self.token_path.parent.mkdir(parents=True, exist_ok=True)
   117	                self.token_path.write_text(
   118	                    json.dumps(token_data, indent=2, ensure_ascii=False) + "\n"
   119	                )
   120	
   121	        return True
   122	
   123	    def auto_progress(self, token=None):
   124	        """根据 token 状态自动推进（executing→verifying→archiving→archived）"""
   125	        token_data = token
   126	        if token_data is None and self.token_path and self.token_path.exists():
   127	            try:
   128	                token_data = json.loads(self.token_path.read_text())
   129	            except (json.JSONDecodeError, OSError):
   130	                return []
   131	
   132	        if not token_data:
   133	            return []
   134	
   135	        stats = token_data.get("stats", {})
   136	        done = stats.get("done", 0)
   137	        total = stats.get("total", 0)
   138	        goal_state = token_data.get("goal", {}).get("state")
   139	
   140	        transitions_made = []
   141	
   142	        if goal_state == EXECUTING and done >= total:
   143	            self.transition(VERIFYING, token_data,
   144	                            reason=f"auto: all {done}/{total} steps completed")
   145	            transitions_made.append(("auto", EXECUTING, VERIFYING))
   146	
   147	        if goal_state == VERIFYING and done >= total:
   148	            self.transition(ARCHIVING, token_data,
   149	                            reason="auto: all steps verified")
   150	            transitions_made.append(("auto", VERIFYING, ARCHIVING))
   151	
   152	        # ARCHIVING → ARCHIVED 需要外部调用 archive 命令后自动触发
   153	        return transitions_made
   154	
   155	    def reset(self, token=None):
   156	        """重置状态机 — 回到 CLARIFY"""
   157	        self._state = None
   158	        return self.transition(CLARIFY, token, reason="reset")
   159	
   160	    def get_summary(self):
   161	        """获取状态机摘要"""
   162	        return {
   163	            "current_state": self._state,
   164	            "is_terminal": self.is_terminal,
   165	            "valid_transitions": _VALID_TRANSITIONS.get(self._state, []),
   166	        }
   167	
   168	
   169	def get_state_header(state, color=True):
   170	    """获取带颜色的状态头"""
   171	    icons = {
   172	        CLARIFY: "📋",
   173	        PLANNING: "📐",
   174	        EXECUTING: "⚡",
   175	        VERIFYING: "🔍",
   176	        ARCHIVING: "📦",
   177	        ARCHIVED: "✅",
   178	    }
   179	    icon = icons.get(state, "❓")
   180	    label = state or "INIT"
   181	    if not color:
   182	        return f"[{icon} {label}]"
   183	    return f"\033[1m{icon} {label}\033[0m"
   184	
   185	
   186	# ─── Self-test ───
   187	if __name__ == "__main__":
   188	    import tempfile
   189	    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
   190	        f.write(json.dumps({
   191	            "stats": {"done": 0, "total": 3},
   192	            "goal": {"state": None}
   193	        }))
   194	        tp = f.name
   195	
   196	    gm = GoalMachine(tp)
   197	    print("Initial:", gm.current_state)
   198	    gm.transition(CLARIFY)
   199	    print("After CLARIFY:", gm.current_state)
   200	    gm.transition(PLANNING)
   201	    print("After PLANNING:", gm.current_state)
   202	    print("Summary:", gm.get_summary())
   203	    Path(tp).unlink(missing_ok=True)
   204	    print("\nAll checks passed ✅")
```

### `.claude/skills/lx-goal/SKILL.md`

```
     1	---
     2	name: lx-goal
     3	version: v1.4.2
     4	description: "目标模式 — 一次前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。入口：`/lx-goal` 或 `/executor`"
     5	when_to_use: "Use when user says 'goal mode', 'lx-goal', '无人值守', '自主执行', `/lx-goal`, `/executor`, or auto-detects a well-defined L2+ task with clear AC"
     6	argument-hint: "[目标描述] [过期小时=6]"
     7	harness_version: ">=6.3.0"
     8	status: stable
     9	role: "Goal-driven autonomous execution — single briefing, zero interruptions, final report"
    10	execution_mode: stepwise
    11	triggers: ["/lx-goal", "/executor"]
    12	auto_detect: "Clear goals with defined ACs, 'do X for me' requests, well-specified tasks"
    13	nodes:
    14	  - behavior_rules          # 铁律#7(文档优先)#8(哲学先行)+自洽检查
    15	  - interactive_prompt      # Phase 0 引导式问答
    16	  - execute_node            # 全自动执行(降级触发+3轮上限)
    17	  - a_terminal              # AC 验收方案生成
    18	  - b_terminal              # 验收执行
    19	schemas:
    20	  - atomic/verdict          # 退出报告最终判定
    21	---
    22	# lx-goal — 目标驱动自主执行
    23	
    24	**一般前置澄清 → 全自动执行 → 退出报告。人类离开后 AI 自主完成所有任务。**
    25	
    26	本质：人类回答所有问题后离开，AI 不再请求交互。卡点按决策链处理，硬边界跳过记录。
    27	
    28	**⚠️ 文档强约束**：每执行一步前，必须先更新 progress.md + 写 evidence，再执行。跳过文档直接执行=违反哲学 #7（文档优先）。
    29	
    30	## 一句话定位
    31	
    32	目标是**已知**的结果。Ghost 是**方向**未知的探索。用户说"帮我做 X" → Goal。用户说"帮我看看 Y 有没有问题" → Ghost。
    33	
    34	## 3 步流程
    35	
    36	```
    37	Phase 0. 一次问清（人类窗口期） → AI 激活 → Phase 1→N. 全自动执行 → 退出报告
    38	```
    39	
    40	### Phase 0：前置澄清
    41	
    42	1. 解析目标（有完整目标 → 跳过。无参数 → 进入 interactive_prompt 引导问答）
    43	2. 一次性扫描所有不确定项：范围边界、硬边界预检、外部依赖、能力缺口、风险点、执行顺序、验收条件、过期策略
    44	3. 输出执行计划（子任务列表 + AC + 依赖 + 风险 + Q 项）
    45	4. 人类确认后激活：`python3 .claude/skills/lx-goal/scripts/lx-goal.py on "{目标描述}"`
    46	5. 验证激活标志存在：`ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active`
    47	
    48	### Phase 1→N：全自动执行
    49	
    50	引用 behavior_rules §自主执行与 execute_node §降级触发：
    51	
    52	| 铁律 | 含义 |
    53	|------|------|
    54	| **不暂停** | 不等待人类输入 |
    55	| **不提问** | 歧义按决策框架判断 |
    56	| **不中断** | 卡点处理后继续 |
    57	| **只记录** | 风险和阻断写入 skipped_risks |
    58	
    59	**卡点处理**：
    60	
    61	| 类型 | 处理 |
    62	|------|------|
    63	| 硬边界（rm/git写/密钥/API Key） | 立即跳过 → `lx-goal hard-boundary-hit` 记录 → 继续 |
    64	| **中高风险项（medium+）** | **只跳过不执行** → `lx-goal skip-risk "描述" <level> "理由" "影响"` → 自动进入退出报告「需人为决策汇总」反馈人工干预 |
    65	| 可跳过（有替代路径） | `lx-goal skip-risk` 记录，继续 |
    66	| 可绕行（换方案可达目标） | 自动降级备选方案 |
    67	| 危险操作（远程推送/破坏性） | 三级裁决链（AGENTS → Oracle → 记录 blocked_human） |
    68	| 真阻断/需人类 | 记录 blocked/blocked_human，继续其他 |
    69	
    70	> 中高风险安全阀：`skip-risk` 第二参数为 risk_level（low/medium/high/critical）。medium 及以上级别**禁止执行只许跳过**，退出报告强制聚合成表反馈人类；low 级记录后可继续。
    71	
    72	**progress 更新**：
    73	```bash
    74	lx-goal task-done "完成了什么"
    75	lx-goal skip-risk "跳过了什么"
    76	lx-goal hard-boundary-hit "操作X被跳过" "原因Y" "建议人类执行Z"
    77	lx-goal blocked-human "决策X" "AI推荐Y" "依据Z"
    78	```
    79	
    80	### 退出报告
    81	
    82	```bash
    83	lx-goal report   # 生成执行报告（含 verdict schema）
    84	lx-goal off      # 关闭模式 + 清理信号文件
    85	```
    86	
    87	报告结构：执行摘要 → 已完成任务 → 跳过风险 → ⚠️ 需人类介入项 → 推迟决策项 → 附带发现
    88	
    89	## 物理锁约束
    90	
    91	`.omc/tokens/{date}/{task_slug}_token.json`
    92	
    93	- 创建时机：`lx-goal on` 成功时自动创建
    94	- 存在含义：任务正在执行，AI 不可说"完成了"
    95	- 删除时机：`lx-goal done` 任务真实验收通过后删除
    96	
    97	## SubAgent 调度记录
    98	
    99	```bash
   100	lx-goal subagent-log assign "<agent_name>" "<subtask描述>"
   101	lx-goal subagent-log complete "<agent_name>" "<subtask>" "<结果摘要>"
   102	lx-goal subagent-log fail "<agent_name>" "<subtask>" "<失败原因>"
   103	lx-goal subagent-log summary
   104	```
   105	
   106	**异常接管**：SubAgent 超时/stalled/failed 时，引用 `@references/autonomous-execution.md §SubAgent异常接管机制` 自动处理，永不等待用户。
   107	
   108	## 跨会话续跑
   109	
   110	1. 检测：`.omc/state/tokens/lx-goal.json` 存在则读 goal + expires_at
   111	2. 恢复：读 `.omc/plans/{date}/{slug}/` — research.md / plan.md / executor.md
   112	3. 继续：从 plan.md 最后一步继续，不需要重新 Phase 0
   113	4. 关闭：`lx-goal done` 删锁 → `lx-goal off`
   114	
   115	## 子任务引擎路由
   116	
   117	| 特征 | → 引擎 |
   118	|:-----|:------|
   119	| ≥3 同构独立子任务 | **lx-race**（并行蜂群） |
   120	| 有依赖链/异构/跨模块/根因不明 | **lx-stepwise**（串行） |
   121	| 单文件小改 | **direct**（无模式，直接执行+证据） |
   122	
   123	## 硬边界
   124	
   125	遇到硬边界 → 立即跳过 → 记录 → 继续。不裁决、不绕过、不尝试任何 workaround。
   126	
   127	## 自主权范围
   128	
   129	文件创建/修改（非治理）、代码重构、架构决策、子 Agent 调度、依赖安装（sudo 需 skip-risk）、测试运行、Git 只读操作——**完全自主，不询问**。
```

### `.claude/skills/lx-ghost/SKILL.md`

```
     1	---
     2	name: lx-ghost
     3	version: v1.4.1
     4	description: "幽灵模式 — 方向驱动的自主探索。Phase 0 穷尽澄清 → Oracle 自主计划审核 → 全自动探索 → 退出报告。"
     5	when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
     6	argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3] [最小迭代数=0]"
     7	harness_version: ">=6.3.0"
     8	status: stable
     9	role: "Direction-driven autonomous exploration — Oracle-gated single briefing, zero interruptions"
    10	execution_mode: stepwise
    11	triggers: ["/lx-ghost"]
    12	---
    13	# lx-ghost — 方向驱动自主探索
    14	
    15	> **一次前置澄清 → 全自动探索 → 退出报告。人类在窗口期确认方向后离开，AI 自主探索直到过期或方向达成。**
    16	
    17	## 原子化声明
    18	
    19	### references/（按需加载）
    20	| 文件 | 加载时机 |
    21	|------|---------|
    22	| `references/ghost-phase0.md` | Phase 0 前置澄清 |
    23	| `references/ghost-oracle-audit.md` | Phase 0.5 Oracle 审核 |
    24	| `references/ghost-polling.md` | 全自动轮询 |
    25	
    26	> 共享 OMA 能力 `@../references/oma/`: degradation-escalation · decision-chain · execution-workflow · skill-chaining
    27	> 复用 lx-goal: `@../lx-goal/references/autonomous-execution.md` · `@../lx-goal/references/exit-report.md`
    28	
    29	## 与 lx-goal 的区别
    30	
    31	| | lx-goal | lx-ghost |
    32	|---|---------|----------|
    33	| 驱动方式 | 目标驱动（具体任务列表） | 方向驱动（开放探索） |
    34	| 执行模式 | 逐项 task-done | 增量 poll 迭代 |
    35	| 适用场景 | 可分解的具体目标 | 需持续探索改进的方向 |
    36	
    37	## Ghost 专属
    38	
    39	### Phase 0: 前置澄清 → `@references/ghost-phase0.md`
    40	方向自检 → 穷举不确定项 → 探索计划（含模式选择：执行模式决策矩阵 `docs/technical/cn/execution-mode-matrix.md` #5-#6）→ 激活脚本 + CronCreate 轮询。
    41	
    42	### Phase 0.5: Oracle 审核 → `@references/ghost-oracle-audit.md`
    43	五维门禁（方向适配/歧义穷尽/硬边界/决策链/退出条件），独立 Oracle 对抗性审查。
    44	
    45	### 全自动轮询 → `@references/ghost-polling.md`
    46	每轮 poll 只做一步。方向漂移自检 + min_iterations 防过早收敛。
    47	
    48	## 退出
    49	
    50	退出协议 → `@../lx-goal/references/exit-report.md`。
    51	```
    52	完成探索 → 生成报告 → lx-ghost report → lx-ghost off
    53	紧急绕过: lx-ghost off --force（留 ghost-exit-pending 桩）
    54	```
    55	
    56	## 哲学物化
    57	
    58	| # | 哲学 | 物化 |
    59	|---|------|------|
    60	| #3 | 先守护 | gate 降级 warn-only，危险走裁决链 |
    61	| #4 | 没验证=没做 | 每轮 poll 报告状态 |
    62	| #6 | 0 信任 | Phase 0.5 Oracle 审核，硬边界不裁决不绕过 |
    63	| #2 | 少量大增益 | 只做方向相关，min_iterations 拓宽防过早收敛 |
    64	
    65	## 降级策略
    66	| 场景 | 降级路径 |
    67	|------|---------|
    68	| 主路径失败 | 输出当前探索摘要，手动保存 |
    69	| 轮询间隔过长 | 手动触发 poll |
    70	| Phase 0 Oracle 不可用 | 降级为 AI 自审 |
```

### `.omc/state/goal-report.md` — goal 退出报告样例

```
     1	# 目标模式执行报告
     2	
     3	生成时间: 2026-07-18 19:29:46
     4	
     5	## 目标
     6	
     7	实施 rpe-f-ten-features-revival：按 plan.md 执行 S1-S7，十特性 3✅/7⚠️ → 10✅（S1-S4已完成，续跑S5-S7）
     8	
     9	## 基本信息
    10	
    11	- 激活时间: 2026-07-18T06:08:08Z
    12	- 过期时间: 2026-07-18T12:08:08.911835+00:00
    13	
    14	## 执行摘要
    15	
    16	- 已完成任务数: 6
    17	- 跳过风险数: 0
    18	- 硬边界拦截数: 1
    19	- 推迟决策数: 0
    20	- 重试次数: 0
    21	
    22	## 已完成任务
    23	
    24	- [x] S5: Oracle接线+ROI+规则配置化（G1 ACCEPT/G3 ADVISORY首次meta聚合）  (2026-07-18T14:35:50.477610)
    25	- [x] S6: lx-goal硬化（is-active双路径+退出码传播+轮询指引）  (2026-07-18T14:40:55.774144)
    26	- [x] S6: lx-goal硬化（is-active双路径+退出码传播+轮询指引）  (2026-07-18T14:40:55.774800)
    27	- [x] S1-S7 十特性修复全部 VERIFIED（7/7），十特性端到端 32/32 全 ✅  (2026-07-18T16:26:02.270796)
    28	- [x] R1: goal 模式硬化 — 双 main 执行/poll TypeError 两 bug + skip-risk 分级/决策表聚合/off 自动报告三缺口修复  (2026-07-18T16:26:02.294696)
    29	- [x] R2: lx-rpe 评级 6.0/10 + P0 三项修复（untracked 漏提交/前缀碰撞/goal 硬边界）  (2026-07-18T16:26:02.315399)
    30	
    31	## 跳过的风险
    32	
    33	无
    34	
    35	## ⚠️ 需人为决策汇总
    36	
    37	| # | 类型 | 描述 | AI 推荐 | 依据 |
    38	|---|------|------|---------|------|
    39	| 1 | 硬边界 | git commit 被跳过（S1-S7+R1+R2 全部改动未提交） | 人工审查 git status 后执行 git add + commit；建议先跑 runtime_verify 确认 3/4 阶段通过 | Git 写操作属硬边界，需人类批准 |
    40	
    41	## ⚠️ 需人类介入项（硬边界）
    42	
    43	- **操作**: git commit 被跳过（S1-S7+R1+R2 全部改动未提交）
    44	  **原因**: Git 写操作属硬边界，需人类批准
    45	  **需人类执行**: 人工审查 git status 后执行 git add + commit；建议先跑 runtime_verify 确认 3/4 阶段通过
    46	
    47	
    48	
    49	## 推迟决策项（裁决链 Level 3 — 需人类裁决）
    50	
    51	无
    52	
    53	## 验证状态
    54	
    55	VERIFIED: 报告生成完毕（6 项完成，0 项风险跳过，1 项硬边界拦截，0 项推迟决策，0 次重试）
```

### 互斥检查搜证(autonomous.active 等)

命令: `grep -rnE 'autonomous.active|互斥|ghost.*goal|goal.*ghost' .claude .omc 2>/dev/null | grep -v __pycache__ | head -40`

```
.claude/plans/carroros-skills-merge-plan.md:216:| **D1 方向适配** | 检查 ghost vs goal 选择 | 不涉及 |
.claude/plans/carroros-skills-merge-plan.md:236:1. **保留 lx-ghost**（其自主探索模式是独特功能，与 lx-goal 的"目标驱动"形成互补）
.claude/plans/carroros-skills-merge-plan.md:238:3. **不删除 lx-ghost** — 除非其功能可完全被 lx-goal 吸收（需要额外分析 lx-goal 的能力边界）
.claude/plans/carroros-skills-merge-plan.md:391:**理由：** lx-ghost 的功能域（方向驱动自主探索）与 lx-oracle-meta（通用运行时验证）不重叠。lx-ghost 提供了独特的"方向驱动、增量 poll 迭代、事前 Oracle 门禁"模式，与 lx-goal 的"目标驱动、逐项 task-done"形成互补。
.claude/references/design-docs/data.md:93:- **描述**: 蜂群协调层 — 快速并行处理简单同构任务。goal/ghost 自动路由至此。
.claude/references/design-docs/data.md:358:Role: 检测 ghost/goal mode 激活但巡航基础设施未初始化 → 提醒 AI 创建 |
.claude/references/feature-registry.yaml:170:  description: OMA 并发写锁门禁，多 Agent 写同一文件时排队互斥
.claude/references/feature-registry.yaml:424:  description: 巡航模式检测 — SessionStart/PreToolUse 检查是否进入 goal/ghost 巡航模式
.claude/settings.local.json:160:      "Bash(mv /tmp/autonomous.active.bak .omc/state/tokens/autonomous.active)",
.claude/settings.local.json:195:      "Bash(touch .omc/state/tokens/autonomous.active)",
.claude/hooks/pretool-user-approve.py:10:  5. Goal mode — appends goal state when autonomous.active exists
.claude/hooks/pretool-user-approve.py:32:GOAL_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
.claude/hooks/pretool-gate.py:870:                goal_mode = (OMC / "state" / "tokens" / "autonomous.active").exists()
.claude/scripts/lib/water_level.py:5:互斥区间定义:
.claude/scripts/lib/water_level.py:28:# 三级水位互斥定义（左闭右开 / 闭区间）
.claude/scripts/lib/water_level.py:51:    """将 ratio 映射到互斥水位区间。"""
.claude/scripts/lib/water_level.py:73:    # 根据互斥区间找到对应消息
.claude/scripts/carros_oracle_base.py:10:- S8: 线程安全熔断器（互斥锁）
.claude/skills/lx-skillify/references/reference_skill_selector.md:40:`lx-goal` — 无人值守 / `lx-ghost` — 自主探索 / `lx-race` — 蜂群并行 / `lx-stepwise` — 逐步攻坚
.claude/skills/skill-dependencies.yaml:127:    protects: [lx-goal, lx-rpe, lx-ghost]
.claude/skills/skill-dependencies.yaml:130:    protects: [lx-goal, lx-ghost, lx-rpe]
.claude/skills/skill-dependencies.yaml:136:    protects: [lx-goal, lx-ghost]
.claude/skills/lx-ghost/references/ghost-phase0.md:41:此命令创建 `.omc/state/tokens/lx-ghost.json` + `.omc/state/tokens/autonomous.active`。
.claude/skills/lx-ghost/references/ghost-phase0.md:45:ls -la .omc/state/tokens/lx-ghost.json .omc/state/tokens/autonomous.active
.claude/skills/lx-ghost/references/ghost-oracle-audit.md:13:| D1 | **方向适配** | ghost vs goal 选择是否正确？有无 GL-01 方向漂移风险？ | 修复清单误用 ghost 模式 |
.claude/skills/lx-ghost/scripts/lx-ghost.sh:5:# 与 lx-goal 的区别: ghost = 方向驱动（开源探索），goal = 目标驱动（具体任务）
.claude/skills/lx-ghost/scripts/lx-ghost.sh:6:# 同时创建 autonomous.active 信号供所有 hook 降级
.claude/skills/lx-ghost/scripts/lx-ghost.sh:69:        # 创建 autonomous.active 信号供 completion-gate 等降级
.claude/skills/lx-ghost/scripts/lx-ghost.sh:70:        touch "$STATE_DIR/tokens/autonomous.active"
.claude/skills/lx-ghost/scripts/lx-ghost.sh:101:	echo "   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only"
.claude/skills/lx-ghost/scripts/lx-ghost.sh:154:		rm -f "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
.claude/skills/lx-ghost/scripts/lx-ghost.sh:176:        if [ -f "$STATE_DIR/tokens/autonomous.active" ]; then
.claude/skills/lx-ghost/scripts/lx-ghost.sh:177:            echo "   autonomous.active 信号: ✅ 存在"
.claude/skills/lx-ghost/scripts/lx-ghost.sh:237:                rm -f "$MODE_FILE" "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
.claude/skills/lx-ghost/scripts/lx-ghost.sh:431:        echo "  lx-ghost = 方向驱动（开源探索），lx-goal = 目标驱动（具体任务）"
.claude/skills/lx-ghost/SKILL.md:31:| | lx-goal | lx-ghost |
.claude/skills/lx-goal/references/phase0-activation.md:38:- `.omc/state/tokens/autonomous.active` — hook 据此降级
.claude/skills/lx-goal/references/phase0-activation.md:42:ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active
.claude/skills/lx-goal/references/phase0-activation.md:45:**为什么必须走脚本**：手动 `touch autonomous.active` 只创建一个文件，`is_mode_active()` 读取 `lx-goal.json` 而非 `autonomous.active`，半个系统仍在 normal mode（DG-46 教训）。
.claude/skills/lx-goal/scripts/lx-goal.py:8:与 lx-ghost 的区别: goal = 目标驱动（具体任务），ghost = 方向驱动（开放探索）
```

## 块 D/E:启动链路 + 测试入口

### 测试入口清单

命令: `ls scripts/ && ls benchmark/*.sh 2>/dev/null`

```
analyze-session-positions.py
assemble-pkg-materials.sh
carroros-gates
find-empty-assistant.py
test-hook-launcher.sh
test-verify-gate.py
benchmark/run-ci.sh
```
