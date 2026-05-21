# Carror OS 能力矩阵（Capability Matrix）

> 版本: v1.0 | 生成时间: 2026-05-21 | 基于: Carror OS v6.2.2  
> 用途: 作为测试 Carror OS 能力的完整标准，覆盖所有机制+测试标准
> 
> 每个能力项 = 机制描述 + 物化载体 + 测试方法 + 通过标准 + 已知问题

---

## Part A: 治理哲学 → 机制 → 测试链

### A1. 7 条哲学原则

| # | 哲学 | 物化机制 | 测试方法 | 通过标准 | 已知问题 |
|---|------|---------|---------|---------|---------|
| 1 | **The Less, The More** | context_compressor (runtime inject compact版), R39 注入预算@turn-counter.sh | `bash harness-smoke-test.sh` context_compressor 用例 | context-cache.md 生成且大小 < 原文件 15% | DG-82: 39/44 hooks 无 flywheel 数据 |
| 2 | **少量正确大增益** | pretool-edit-scope (范围冻结), 反模式 B1 | scope file 存在时编辑越界被阻断 | exit 2 on scope violation | DG-74: 反模式框架 16% 覆盖率 |
| 3 | **先守护，后激发** | context-guard (>80% block), permission-gate, privacy-gate, pretool-sensitive-edit | 模拟超 80% context 写操作 + 危险命令 | 超 80% 阻断写操作; rm -rf 被拦截 | — |
| 4 | **没通过验证=没做** | completion-gate (6 层), pre-completion-gate, 软完成语禁令 | 提交无证据 TaskUpdate(completed) | 拦截 exit 2，要求 VERIFIED | DG-102: auto-score 与真实改进方向正交 |
| 5 | **以人为本** | pre-ask-guard (哲学先行门禁), posttool-output-format (方向感) | AskUserQuestion 之前哲学裁决被注入 | 无效问题被拦截 | — |
| 6 | **先天对 AI 0 信任** | 三重门 A→B→A, Oracle Agent v2, Meta-Oracle G1-G4, 铁律#1 禁编造 | 提交方案→Oracle agent spawn→独立裁决 | Oracle 独立审核返回 ACCEPT/REVISE | DG-86: Oracle 超时降级未双签 |
| 7 | **文档优先，调研先行** | plan-gate, RPE 文档体系, lx-oracle-v2 | 非琐碎任务无 plan.md 被 plan-gate 拦截 | exit 2 when plan missing | — |

### A2. 8 条铁律

| # | 铁律 | 物化 hook | 测试输入 | 通过标准 |
|---|------|----------|---------|---------|
| 1 | **禁止编造** | posttool-claim-audit | 无 file:line 的技术断言 | exit 2 |
| 2 | **用户裁定** | permission-gate | AI 自行 git commit/push | exit 2 |
| 3 | **证据门禁** | completion-gate + pre-completion-gate | 无 VERIFIED 关键字的完成声明 | exit 2, 要求补证据 |
| 4 | **Git 门禁** | permission-gate git_commit_regex | 未获批准的 git commit | exit 2 |
| 5 | **范围冻结** | pretool-edit-scope | scope 外文件编辑 | exit 2 |
| 6 | **隐私防线** | privacy-gate | 读取 .env 文件 | exit 2 |
| 7 | **断言真实** | posttool-claim-audit + posttool-anti-pattern-detect (H1 语义编造) | 报告中无来源的百分比/评分 | exit 2 |
| 8 | **哲学先行** | pre-ask-guard | AskUserQuestion 前哲学未裁决 | exit 2 |

---

## Part B: Hook 能力矩阵（共 45 个 scripts: 43 hooks + 2 共享库）

### B1. 安全门禁 (Security Gates)

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| permission-gate | PreToolUse | Bash | 危险命令拦截(rm -rf, DROP TABLE, git push --force, sudo, gh write, base64|bash) | `bash harness-smoke-test.sh` permission-gate 用例 | 匹配危险命令 → exit 2 |
| privacy-gate | PreToolUse | Bash\|Read\|Grep | .env/密钥/Token 文件读取拦截 | `bash harness-smoke-test.sh` privacy-gate 用例 | 匹配敏感文件路径 → exit 2 |
| pretool-sensitive-edit | PreToolUse | Edit\|Write\|Bash | 治理文件编辑 CAPTCHA 验证码门禁 | 编辑 settings.json 等治理文件 | CAPTCHA 要求 |
| subagent-guard | PreToolUse | Task | 子代理类型安全门禁(executor/designer/scientist 禁) | spawn 危险子 agent | exit 2 |

### B2. 质量门禁 (Quality Gates)

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| pretool-edit-scope | PreToolUse | Edit\|Write | 编辑范围预检，阻止 scope 外修改 | 编辑 scope file 之外的文件 | exit 2 |
| edit-guard | PreToolUse | Edit\|Write | 编辑内容质量拦截(空/越界/溢出) | `bash harness-smoke-test.sh` edit-guard 用例 | 非法编辑 → exit 2 |
| plan-gate | PreToolUse | Edit\|Write | 非琐碎任务无 plan → 拦截 | 3+ 步任务无 plan 文件 → 编辑 | exit 2 |
| pretool-write-lock | PreToolUse | Edit\|Write | 写入前锁定检查(防并发冲突) | 同一文件已有活跃 lock | exit 2 |
| fuzzy-block | PreToolUse | .* | 模糊指令硬阻断('优化''改进''处理一下') | 输入含模糊动词 | exit 2 |
| pre-completion-gate | PreToolUse | TaskUpdate | 前置完成门禁，无证据不可 completed | TaskUpdate(completed) 无证据文件 | exit 2 |
| pretool-retry-check | PreToolUse | Bash | 重试预算检查，同一签名 3 轮上限 | 同签名第 4 次重试 | exit 2 |

### B3. 完成门禁 (Completion Gates)

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| completion-gate | PostToolUse | TaskUpdate | 6 层验证：证据存在→长度→VERIFIED→语义格式→软完成语→双源证据→质量≥65 | `bash harness-smoke-test.sh` completion-gate 用例 | 证据质量 ≥60 → pass; <60 → exit 2 |
| posttool-completion-audit | PostToolUse | TaskUpdate | 完成声明审计，交叉验证 TaskUpdate vs 实际产物 | completed 状态但产物文件 0 字节 | exit 2 |
| posttool-handoff-writer | PostToolUse | TaskUpdate | 自动写 session-handoff.md | TaskUpdate(completed) | 生成 handoff 文件 |

### B4. 反模式/语义检测

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| posttool-anti-pattern-detect | PostToolUse | TaskUpdate\|Edit\|Write | A2/F1/G1/H1 四类阻断(虚假完成/假设驱动/伪诚信/语义编造) | 输出含软完成语/无来源百分比 | exit 2 |
| posttool-claim-audit | PostToolUse | Edit\|Write | 铁律#1/#7 断言审计 | 输出无 file:line 的技术断言 | exit 2 |
| posttool-output-format | PostToolUse | TaskUpdate\|Edit\|Write | 输出格式方向感检查(哲学#5) | 输出缺少方向指引 | exit 2 (warn mode?) |

### B5. 上下文与运行时

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| context-guard | PreToolUse | Edit\|Write | 上下文 >50% 警告，>80% 硬阻断写操作 | context 80%+ 时 Edit/Write | exit 2 |
| context-compressor | SessionStart | — | 运行时上下文压缩(context-cache.md 生成) | 源文件 mtime 变更 → 重新生成 cache | cache 文件存在且非空 |
| compact-detect | UserPromptSubmit | — | /compact 后全量重注铁律/kernel/AGENTS/skill-graph | /compact 后 | 知识重新注入 |
| turn-counter | UserPromptSubmit | — | 轮次计数+分层知识注入(L0-L3) | 每 N 轮触发知识锚定 | stdout 输出锚定文本 |
| token_writer | PostToolUse + SessionStart | .* | Token 消耗追踪索引 | 每次操作后 | token 计数更新 |
| stop-drain | Stop | — | Stop hook 兜底重放(持久化 handoff+error-dna) | 会话自然结束 | snapshots 写入成功 |

### B6. 知识记忆系统

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| inject-project-knowledge | SessionStart | — | 会话启动时注入 kernel/anti-patterns/claude-next + session-handoff | 新会话 | key files 注入确认 |
| auto-snapshot | PostToolUse + Stop | Edit\|Write | 自动会话快照(按 turn 间隔) | 编辑后触发 snapshot | snapshot 文件写入 |
| knowledge-condenser | Stop | — | claude-next.md 压缩归档 | 会话结束，lessons 达阈值 | 旧条目归档 |
| flywheel-report | SessionStart | — | 飞轮报告生成(技能使用统计) | 新会话启动 | 飞轮统计输出 |
| skill-flywheel | Stop | — | 技能飞轮持久化 | 会话结束 | 使用统计写入 |

### B7. 错误与审计

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| error-dna | PostToolUse + PostToolUseFailure | Bash | 错误 DNA 分析(签名+次数+修复上下文) | Bash 命令 exit≠0 | JSONL 写入 error-dna.jsonl |
| posttool-bash-audit | PostToolUse + PostToolUseFailure | Bash | bash 命令审计日志 + 危险模式检测 | 每次 Bash 执行后 | 危险模式 → exit 2 |
| posttool-subagent-audit | PostToolUse | Task | 子 agent 输出字节数 P0 检测 | 子 agent 返回 > 阈值 | P0 写入 flywheel |
| read-tracker | PostToolUse | Read | 读取文件跟踪(已读记录) | Read 操作后 | read manifest 更新 |
| skill-usage-tracker | PostToolUse | Skill | Skill 使用率追踪(/lx-xxx 命令) | Skill 调用后 | JSONL 记录追加 |

### B8. 辅助工具体系

| Hook Script | 事件 | Matcher | 能力描述 | 测试方法 | 通过标准 |
|------------|------|---------|---------|---------|---------|
| ecosystem-probe | SessionStart | — | 生态探针(CC/OC/OMO 安装检测) | 新会话启动 | 输出平台+OMO 状态 |
| lsp-suggest | PreToolUse | Grep | LSP 诊断建议注入 | Grep 操作前 | LSP 建议替代 grep |
| meta-oracle-trigger | PostToolUse | .* | Meta-Oracle G1-G4 自动触发提醒 | Oracle ACCEPT 高分时 | 提醒注入 |
| pre-ask-guard | PreToolUse | AskUserQuestion | 哲学先行门禁(问人前先过哲学) | AskUserQuestion 前 | 哲学裁决 → 拦截不必要的问题 |
| pretool-user-correction | UserPromptSubmit | — | 用户纠正信号检测('不对''应该是'等) | 用户输入含纠正词 | claude-next.md 记录触发 |
| posttool-edit-quality | PostToolUse | Edit\|Write | 编辑后质量检查 | 编辑后 | 质量评分 |
| posttool-write-lock | PostToolUse | Edit\|Write | 写入后锁释放 | 编辑完成 | lock 文件清理 |
| posttool-write-cite | PostToolUse | Write\|Edit | 写入后引用标注 | Write 操作后 | 引用格式检查 |
| intent-tracker | PostToolUse | Edit\|Write | 声明矛盾检测(编辑抖动/内容回退) | 连续编辑同一文件+内容回退 | P0 矛盾告警 |
| pre-edit-lsp-check | PreToolUse | Edit\|Write | 编辑前 LSP 诊断提醒(代码文件). 非阻断，仅提醒 | 编辑 .py/.go/.rs/.ts 等代码文件前 | stdout 注入诊断提醒 |

### B9. 共享库 (Shared Libraries)

| Script | 用途 | 调用者 |
|--------|------|--------|
| harness_config.sh | 共享配置读取器(feature-registry + harness.yaml 门禁) | 所有 hook source |
| agentic-ui.sh | Agentic UI 标准化输出(菜单/CAPTCHA/确认/状态横幅) | pretool-sensitive-edit, permission-gate 等 |

---

## Part C: 三源一致性与 Oracle 体系

### C1. 三源一致性

| 维度 | Source I (生成源) | Source II (静态规则) | Source III (运行时事实) | 测试方法 |
|------|------------------|---------------------|----------------------|---------|
| **载体** | AGENTS.md(哲学+铁律), kernel.md, anti-patterns.md | settings.json(hook 注册), harness.yaml, feature-registry.yaml | flywheel.log, error-dna.jsonl, harness-smoke-test.sh | `bash audit-hooks.sh` 三方对齐检查 |
| **测试** | 铁律文本与 hook 源码逻辑一致 | 注册 hook 文件实际存在且语法正确 | hook 产生 flywheel 事件 ≠ 0 | `bash harness-smoke-test.sh` + `audit-hooks.sh --check-flywheel` |
| **分歧处理** | 规则冲突→哲学优先级裁决 | 规则未生效→audit-hooks 修复 | 规则被违反→BLOCKED | 人工触发分歧验证 |

### C2. Oracle Agent v2

| 能力 | 说明 | 测试方法 | 通过标准 |
|------|------|---------|---------|
| Oracle-D 决策链审核 | Agent(critic) 独立进程审核方案质量 | 提交 PRD/方案 → `pipeline 310` spawn | 返回 ACCEPT/REVISE/REJECT + P0 列表 |
| Oracle-V A→B→A 验证 | A预测→B盲执行→A自证 → Oracle 裁决 | 完整三重门流程 | 三端交叉验证一致 → ACCEPT |
| 物理隔离 | 独立 opus 进程，不共享主会话上下文 | `ps aux` 验证独立进程 | 独立 PID，独立上下文 |
| 裁决留痕 | oracle-verdicts.md 持久化 | `cat .omc/state/oracle-verdicts.md` | 每次审核含 verdict + P0 数量 + 修复状态 |

### C3. Meta-Oracle 4 触发点

| 触发 | 条件 | 测试方法 | 通过标准 |
|------|------|---------|---------|
| G1: 架构决策终审 | 涉及 ≥2 子系统 + 不可逆变更 | 触发 scenario → meta-oracle-trigger.sh | 注入提醒 → AI 执行 Meta-Oracle 审查 |
| G2: PRD 最后一步 | PRD 完整生命周期最终阶段 | Oracle ACCEPT → 触发 Meta-Oracle | 独立二审裁决 |
| G3: Oracle ACCEPT 高分 | Oracle 评分 ≥8.5 | Oracle high score → trigger | 独立校准评分 |
| G4: Release 门禁 | package-release.sh 执行前 | 执行 release 前 | smoke test full green → 允许发布 |

---

## Part D: Skill 能力矩阵（26 个 lx-* skills）

### D1. 核心工作流 Skills

| Skill | 类型 | 能力描述 | 测试方法 | 通过标准 |
|-------|------|---------|---------|---------|
| lx-task-spec | workflow | 任务驱动: 引导问答x3→结构化输入→规划→执行→验收 | 输入复杂需求 | 生成 tasks.md + plan.md |
| lx-rpe | workflow | RPE 特性开发循环: TDD/代码审查/安全/验收 | 触发 feature 开发 | Step1-7 全流程闭环 |
| lx-goal | workflow | 目标驱动自主执行→输出报告 | `lx-goal {目标}` | 执行完毕+报告文件 |
| lx-ghost | workflow | 方向驱动自主探索修复 | `lx-ghost {方向}` | 自主修复+不打扰用户 |
| lx-dogfood | workflow | 狗粮记录: 事故发生时趁热记录→处理完提炼教训 | 主动触发 | claude-next.md +1 条目 |
| lx-skillify | workflow | Skill 自动生成器(6阶段管道) | `lx-skillify {需求}` | 生成完整 SKILL.md+验证 |

### D2. 编排层 Skills

| Skill | 类型 | 能力描述 | 测试方法 | 通过标准 |
|-------|------|---------|---------|---------|
| lx-oma-hier | orchestrator | 超大型 PRD MECE 拆分为多个 Sub PRD | 输入超长 PRD | 拆分为正交 Sub PRD |
| lx-oma-split | orchestrator | Sub PRD → feature 级 RPE (一人成军) | 对 Sub PRD 拆分 | 正交 feature RPE |
| lx-oma-gov | orchestrator | PRD 治理: 漂移检测→冲突裁决→增量同步 | Sub PRD 变更 | 检测漂移→裁决 |
| lx-oma-orch | orchestrator | 管线编排: 状态查看→阶段推进→Oracle 门禁 | `pipeline status` | 全阶段状态+推进 |
| lx-race | orchestrator | 蜂群协调: 并行处理同构任务 | 批量任务 | 多 agent 并行+汇总 |
| lx-stepwise | orchestrator | 高难度 bug 单步推进(隔离→定位→方案→修复→加固) | 输入 bug | 每步验证+最终修复 |

### D3. 质量审查 Skills

| Skill | 类型 | 能力描述 | 测试方法 | 通过标准 |
|-------|------|---------|---------|---------|
| lx-code-review | reviewer | 通用代码审查: 8类别39规则 | `lx-code-review {file}` | 评分+问题列表 |
| lx-test-gen | tester | 语言无关测试生成(Go/TS/Python/Rust/Java/Ruby) | `lx-test-gen {file}` | 生成测试文件 |
| lx-validate-skill | reviewer | Skill 验收: frontmatter/原子化/节点引用/11项 | `lx-validate-skill {skill}` | 校验结果+修复建议 |
| lx-sync | reviewer | 变更后一致性检查: frontmatter↔registry, source mirror, harness_version | `lx-sync` | 漂移检测报告 |
| lx-oracle-v2 | reviewer | Oracle Agent v2 物理隔离审核(双协议) | `lx-oracle-v2 {target}` | ACCEPT/REVISE/REJECT |
| lx-root-cause-analysis | analyzer | 根因分析: Five Whys/证据链/置信度/免疫 | `lx-rca {问题}` | RCA 报告+置信度 |

### D4. 门禁/Gate Skills

| Skill | 类型 | 能力描述 | 测试方法 | 通过标准 |
|-------|------|---------|---------|---------|
| lx-pre-commit | gate | 提交前: 类型检测→编译→测试→代码审查 | `lx-pre-commit` | 全绿→允许 commit |
| lx-pre-push | gate | 推送前深度门禁: commit msg→测试覆盖→安全扫描 | `lx-pre-push` | 全绿→允许 push |
| lx-varlock | guard | 隐私脱敏代理: 密码/API Key/Token 明文保护 | 检测到敏感变量 | 脱敏处理 |

### D5. 辅助 Skills

| Skill | 类型 | 能力描述 |
|-------|------|---------|
| lx-status | monitor | 健康面板: 执行效率/自愈力/token 节省 |
| lx-todo | workflow | 轻量 TODO: capture/triage/fix/verify/close |
| update-carror-os | workflow | Carror OS 安装更新: 备份→安装→恢复→验证 |
| lx-learner | workflow | 从对话模式检测→提取可重用 skill |

---

## Part E: 测试基础设施

### E1. 测试套件

| 测试 | 路径 | 用例数 | 覆盖范围 | 通过标准 |
|------|------|--------|---------|---------|
| harness-smoke-test.sh | `.claude/scripts/harness-smoke-test.sh` | ~58 (动态) | 所有 PreToolUse + PostToolUse hooks | exit 0 = 全绿 |
| hook-production-verify.sh | `.claude/scripts/hook-production-verify.sh` | 动态计数 | 所有 gate 场景 | exit 0 = 全绿 |
| audit-hooks.sh | `.claude/scripts/audit-hooks.sh` | — | 三源一致性(settings↔harness↔文件系统) | 三方对齐 |
| auto-score.sh | `.claude/scripts/auto-score.sh` | — | 文件存在/注册数/smoke pass/fail/regex | 综合评分 |
| test_oma_lock.py | `.claude/scripts/test_oma_lock.py` | — | OMA 锁逻辑 | Python test pass |

### E2. 监控数据源

| 数据源 | 路径 | 写入时机 | 用途 |
|--------|------|---------|------|
| flywheel.log | `~/.claude/flywheel.log` | Stop hook flush | hook 拦截计数、ROI 计算 |
| error-dna.jsonl | `.omc/state/error-dna.jsonl` | PostToolUse:Bash exit≠0 | 错误模式追踪 |
| skill-usage.jsonl | `.omc/state/skill-usage.jsonl` | PostToolUse:Skill | skill 使用率统计 |
| session-handoff.md | `.omc/state/session-handoff.md` | Stop hook | 跨会话状态交接 |
| oracle-verdicts.md | `.omc/state/oracle-verdicts.md` | Oracle 审核后 | Oracle 裁决留痕 |
| meta-oracle-verdicts.md | `.omc/state/meta-oracle-verdicts.md` | Meta-Oracle 审核后 | Meta-Oracle 裁决留痕 |
| meta-oracle-overrides.md | `.omc/state/meta-oracle-overrides.md` | Meta-Oracle REJECT 覆写时 | AI 覆写 Oracle 理由记录 |

---

## Part F: 完整性自检清单

### F1. Hook 覆盖率 (自 harness.yaml hooks_enabled)

| # | Hook Name | 有脚本? | 有 smoke 测试? | 有 flywheel 埋点? |
|---|-----------|---------|---------------|------------------|
| 1 | anti_pattern_detect | ✅ | ✅ | 待验证 |
| 2 | auto_snapshot | ✅ | ✅ | 待验证 |
| 3 | compact_detect | ✅ | ✅ | 待验证 |
| 4 | completion_gate | ✅ | ✅ | ✅ |
| 5 | context_guard | ✅ | ✅ | ✅ |
| 6 | context_compressor | ✅ | ✅ | 待验证 |
| 7 | ecosystem_probe | ✅ | 待验证 | 待验证 |
| 8 | edit_guard | ✅ | ✅ | ✅ |
| 9 | error_dna | ✅ | ✅ | ✅ |
| 10 | fuzzy_block | ✅ | ✅ | ✅ |
| 11 | inject_project_knowledge | ✅ | ✅ | 待验证 |
| 12 | intent_tracker | ✅ | 待验证 | 待验证 |
| 13 | issue_triage | ❌ (无脚本) | — | — | 概念性，未实现 |
| 14 | knowledge_condenser | ✅ | 待验证 | 待验证 | |
| 15 | lsp_suggest | ✅ | ✅ | 待验证 | |
| 16 | lsp_gate | ❌ (无独立脚本) | — | — | 通过 pre-edit-lsp-check.sh 间接实现 |
| 17 | meta_oracle_trigger | ✅ | 待验证 | 待验证 | |
| 18 | permission_gate | ✅ | ✅ | ✅ |
| 19 | plan_gate | ✅ | ✅ | 待验证 |
| 20 | posttool_bash_audit | ✅ | ✅ | ✅ |
| 21 | posttool_claim_audit | ✅ | 待验证 | 待验证 |
| 22 | posttool_completion_audit | ✅ | 待验证 | 待验证 |
| 23 | posttool_edit_quality | ✅ | 待验证 | 待验证 |
| 24 | posttool_handoff_writer | ✅ | 待验证 | 待验证 |
| 25 | posttool_output_format | ✅ | 待验证 | 待验证 |
| 26 | posttool_subagent_audit | ✅ | 待验证 | 待验证 |
| 27 | posttool_write_cite | ✅ | 待验证 | 待验证 |
| 28 | posttool_write_lock | ✅ | 待验证 | 待验证 |
| 29 | pre_completion_gate | ✅ | ✅ | ✅ |
| 30 | pre_ask_guard | ✅ | ✅ | 待验证 |
| 31 | pretool_edit_scope | ✅ | ✅ | ✅ |
| 32 | pretool_sensitive_edit | ✅ | ✅ | ✅ |
| 33 | pretool_write_lock | ✅ | 待验证 | 待验证 |
| 34 | privacy_gate | ✅ | ✅ | ✅ |
| 35 | read_tracker | ✅ | 待验证 | 待验证 |
| 36 | retry_budget_check | ✅ | ✅ | ✅ |
| 37 | skill_flywheel | ✅ | 待验证 | 待验证 |
| 38 | stop_drain | ✅ | ✅ | ✅ |
| 39 | subagent_guard | ✅ | ✅ | 待验证 |
| 40 | token_writer | ✅ | 待验证 | 待验证 |
| 41 | skill_usage_tracker | ✅ | 待验证 | ✅ |
| 42 | turn_counter | ✅ | ✅ | 待验证 |
| 43 | user_correction_detector | ✅ | 待验证 | 待验证 |
| 44 | rule_anchor | ❌ (内置机制) | — | — | turn-counter 内置，无需独立脚本 |

### F2. 已知系统性缺陷

| 编号 | 问题 | 严重度 | 影响 |
|------|------|--------|------|
| DG-82 | 39/44 hooks 无 flywheel 埋点 → ROI 系统性偏低 | P0 | 去留决策错误 |
| DG-25 | audit-hooks --sync-index 从未工作 | P1 | Source mirror 漂移未检测 |
| DG-74 | 哲学-机制矩阵覆盖率 16% | P1 | 哲学缺少物化验证 |
| DG-102 | auto-score 评分方向与真实改进正交 | P0 | 优化效果不可验证 |
| DG-100 | auto-score 静态评分系统性天花板 | P1 | 语义修复无法被感知 |
| DG-96 | Oracle 审查仅静态读代码漏掉运行时假阳性 | P1 | Oracle 漏审 |
| DG-30 | claim-audit 核心正则从未匹配 | P1 | 铁律#1/#7 无实际拦截 |
| DG-86 | Oracle 超时降级协议未强制执行 | P1 | Oracle 失效时退化为自审 |

---

## Part G: 评分维度

### 能力矩阵评分体系

每次对 Carror OS 进行能力评估，按以下 5 维度打分，加权合成综合分：

| 维度 | 权重 | 评分标准 | 数据源 |
|------|------|---------|--------|
| **Hook 注册完整性** | 20% | settings.json 注册数 / harness.yaml hooks_enabled 数 = 对齐率 | audit-hooks.sh |
| **Hook 实际生效** | 25% | 有 flywheel 事件 >0 的 hook 数 / 总数 | flywheel.log |
| **三源一致性** | 20% | Source I ↔ II ↔ III 三方无分歧项数 / 总检查项 | audit-hooks.sh 输出 |
| **Smoke Test 通过率** | 20% | PASS 数 / 总用例数 | harness-smoke-test.sh |
| **已知缺陷修复率** | 15% | claude-next.md 中 hits≥3 且已修复条目 / 总数 | claude-next.md |

**综合评分 = Σ(维度得分 × 权重)**

> 参考: 哲学#2 (少量正确大增益) — 不追求满分，优先提升生效率和已知缺陷修复率。
