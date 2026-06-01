# 数字资产管理内核

> Carror OS 知识进化引擎 — 从运行时事件到铁律生长的完整管道
> 资产: flywheel.log / error-dna.jsonl / governance-audit.jsonl / retry-budget.json / escape-patches.json / claude-next.md
> 全部位于 .omc/state/ 和 ~/.claude/ 下，kernel.md 是这些资产的管理员

──────────────────────
资产地图
──────────────────────

flywheel.log          → 全hook事件流（每个hook通过 flywheel_event 写入）
error-dna.jsonl       → E2验证码伪造攻击记录（最高优先级，归档轮转）
governance-audit.jsonl→ E1治理文件绕过记录（Bash绕过Edit|Write门禁）
error-signals.jsonl   → 普通Bash错误（7天自动清除，>512KB清空）
retry-budget.json     → 按signature追踪重试次数（3轮上限执法依据）
escape-patches.json   → E1/E2触发后自动生成的修复建议（30天pending过期）
claude-next.md        → 用户纠正→DG教训（58条，knowledge-condenser扫描升华）

──────────────────────
管道: 事件 → 教训 → 规则 → 铁律
──────────────────────

Phase 1: 采集（飞轮 + 错误基因）
  每个hook调用 flywheel_event → flywheel.log
  error-dna.sh 拦截 PostToolUse:Bash + PostToolUseFailure:Bash
    ├─ 隐私脱敏: API key/Bearer token/JWT 自动替换为 ***
    ├─ 签名生成: md5(cmd)[:16] → 去重统计
    ├─ 分类器: build/test/git/dependency/lint/docker/network/file_ops/runtime
    └─ E1/E2逃逸检测: 治理文件路径匹配 + CAPTCHA标记匹配 + 符号链接追踪

Phase 2: 感知（飞轮报告 + 高频告警）
  flywheel-report.sh (SessionStart): 扫描30天窗口
    P0事件 ≥5次 + 未被ack/snooze → 生成报告 + macOS通知
    告警抑制: flywheel-ack.log (resolved/snooze N天/ignore)
  error-dna.sh 实时高频扫描: 同一signature ≥5次 → 注入session告警
    逃逸E1/E2: 即时写入additionalContext（Agent立即可见）
  error-dna-auto-fix.sh (Stop): 跨会话回顾
    扫描 error-dna.json → 顽固错误(≥3次仍active) → 写入状态文件

Phase 3: 记录（纠正检测 → claude-next）
  pretool-user-correction.sh (UserPromptSubmit):
    检测"不对/错了/应该是/不是这样/重新来/你弄错了"等信号
    → 自动写入 DG-[N] 骨架到 claude-next.md（每日最多一次）
    → 要求Agent补充根因+纠正内容后标记hits+1
  claude-next.md 格式: ### [DG-xxx] [状态] 描述 @日期 hits:N
    触发条件 + 正确行为 + 证据

Phase 4: 升华（knowledge-condenser → kernel）
  knowledge-condenser.sh (Stop, 默认禁用):
    扫描 claude-next.md 提取 hits≥2 条目
    hits≥5 + age≥10d + kernel已有 → "更新 kernel.md（补证据）"
    hits≥5 + age≥10d + kernel无   → "升华至 kernel.md"
    hits≥3 + age≥7d               → "升华至 kernel.md"
    hits≥3 + age≥5d               → "建议升华，待确认"
    hits=1 + age>30d              → "建议归档移除"
    >40条目                        → "警告: 建议清理至<30条"
  harness.yaml sublimation thresholds:
    count_threshold: 20, age_days: 10, hit_threshold: 5
  升华执行: AI/开发者手动将DG条目转写为kernel规则
    规则格式: "禁止/必须 xxx — （升华自 DG-xxx）"
    已有7条升华为kernel规则 (DG-13/29/31/36/54/68/77)

Phase 5: 生长（kernel → AGENTS 铁律/哲学）
  极稳定kernel规则 → 候选新铁律 → Boss仲裁
  当前8条铁律均无DG来源标注（稳定到无需追溯）

──────────────────────
资产生命周期
──────────────────────

flywheel.log:
  写入: 每个hook触发 flywheel_event
  读取: flywheel-report.sh (SessionStart, 30天窗口)
  清理: 无自动清理（用户手动管理）
  抑制: flywheel-ack.log (resolved/snooze/ignore)

error-dna.jsonl (E2 captcha forgery):
  写入: error-dna.sh 检测E2 → append
  轮转: >1MB → .0 → .1 → .2 (保留3个归档)
  清理: 7天后自动删除归档文件

governance-audit.jsonl (E1 bypass):
  写入: error-dna.sh 检测E1 → append
  轮转: 无（E1比E2频率低）
  清理: 无自动清理

error-signals.jsonl (普通错误):
  写入: error-dna.sh 检测普通Bash错误 → append
  清理: 7天自动清除 / >512KB清空重启
  用途: C5/C9/E3 scoring数据源

retry-budget.json:
  更新: 每次error-dna捕获 → signature retry_count+1
  读取: pretool-retry-check.sh (PreToolUse:Bash, 3轮上限执法)
  清理: 无自动清理

escape-patches.json:
  写入: E1/E2首次触发 → 自动生成修复建议 (severity: critical/high)
  过期: 30天pending → 自动标记expired
  读取: Oracle/Meta-Oracle审查时参考

claude-next.md:
  写入: pretool-user-correction检测到纠正信号 → DG骨架
  更新: Agent补充根因/纠正内容 → hits递增
  升华: knowledge-condenser扫描 → 人工转写到kernel.md
  归档: hits=1+age>30d → 建议移除（当前58条，超过40条告警线）

──────────────────────
Compact 记忆恢复 — 跨压缩知识恢复
──────────────────────

  /compact 是 Claude Code 内置命令，Carror OS 通过以下机制实现记忆恢复：

  Before compact (Stop 事件):
    1. stop-drain.sh 调用 extract-compact-memory.py
       → 从 transcript 提取最近 20 条用户询问
       → 读取 session-handoff.md + session-dump.json
       → 写入 todo-queue.md (最近询问 + 任务摘要)

  After compact (SessionStart):
    2. inject-project-knowledge.sh 注入 todo-queue.md (最近询问 + 任务摘要)
    3. inject-project-knowledge.sh 注入 session-handoff.md (Feature/进度/决策)
    4. inject-project-knowledge.sh 注入 session-dump.json 摘要 (修改文件/错误/活跃特性)
    5. context-compressor.sh 注入 context-cache.md (铁律/反模式/架构压缩)

  涉及的资产文件:
    todo-queue.md:
      写入: extract-compact-memory.py (via stop-drain.sh on Stop)
      内容: 最近 20 条用户询问 + 已完成/待完成任务
    session-handoff.md:
      写入: auto-snapshot.sh (Stop/PostToolUse:Edit|Write) + posttool-handoff-writer (PostToolUse:TaskUpdate)
      格式: Feature/进度/关键决策/TODO (max 10行 ADR, 10行 TODO, 3条 lessons)
    session-dump.json:
      写入: auto-snapshot.sh (PostToolUse:Edit|Write + Stop)
      内容: git_state(modified_files) + active_features + edit_log + error_summary

──────────────────────
E1/E2 逃逸检测详情
──────────────────────

E1 (治理文件绕过):
  触发: Bash命令中包含治理文件路径
  检测文件: harness.yaml, settings.json, kernel.md, anti-patterns.md,
            index.md, claude-next.md, feature-registry.yaml,
            CLAUDE.md, AGENTS.md, .cursor/hooks.json, .opencode/opencode.json
  符号链接追踪: 命令参数解析 → os.path.realpath → 交叉匹配治理路径
  写入路径: governance-audit.jsonl
  自动补丁建议: "扩展 pretool-sensitive-edit matcher 到 Bash"

E2 (验证码伪造):
  触发: Bash命令中包含CAPTCHA批准标记
  检测标记: sensitive-approved, sensitive-required,
            permission-approved, permission-required
  写入路径: error-dna.jsonl
  自动补丁建议: "检查 permission-gate 的CAPTCHA文件保护"

──────────────────────
运行模式（保留自旧kernel）
──────────────────────

三种无人值守模式: goal / ghost / rpe
  信号文件: .omc/state/tokens/ 子目录
  L4权限/风险/路线/资源: 无人→记录↷跳过, 有人→穿透打断
  ghost模式: hook不硬阻断(critical除外), 方向驱动
  goal模式: Phase0澄清→Phase1-∞自主→Phase∞∞退出

三种有人值守模式: ToDo / Task-spec / 标准交互
  L4行为: 穿透到人裁决
  ToDo: 单步/明确修复
  Task-spec: 多步/需规划, Phase0方案审批

文档路径:
  goal/ghost: .omc/state/{plan|task|test|token}/{date}/{feature}/
  rpe: rpe/{feature}/
  oma: main_prd/{sub_prd}/{feature}/
  废弃路径: prd/, sub-prds/, rpe/feat-*

──────────────────────
Skill body.md 强制执行
──────────────────────
skill body.md 不是可读可不读的参考文档，而是必须严格执行的执行合约。
PreToolUse:Skill hook (pretool-skill-body-enforce.sh) 自动将 body.md 内容
注入 AI 上下文，AI 无法"选择不看"。PostToolUse:Skill hook
(posttool-skill-compliance.sh) 审计执行合规性，发现偏差注入警告。
哲学 #3(先守护) + #6(0信任) 物化。
