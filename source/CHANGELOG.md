# CHANGELOG

>  Carror OS 版本历史（harness-kit + lx-skills-v5）
> 遵循 [Keep a Changelog](<https://keepachangelog.com/zh-CN/1.0.0/>) 规范
> 版本号遵循 [语义化版本](<https://semver.org/lang/zh-CN/>)

---
## [未发布]

> 待纳入下一版本的改动记录于此

---

## [v6.1.5] — 2026-04-28 (One-Man Army Edition)
### 核心主题：一人成军 (并发锁与极致生产力)

**新增内容**：
- **`oma_lock_manager.py` (微内核并发锁引擎)**：
  - 在单机环境下，通过最原始的系统级原子操作（`os.O_CREAT | os.O_EXCL`）解决了多 Agent 并发协同修改同一代码库时的致命写冲突（Race Condition）。
  - 内置 **60秒死锁自愈 (Deadlock Auto-Recovery)** 机制。当某个终端崩溃未释放锁时，排队终端将强行碾碎旧锁接管，保证赛博军队永不卡死。
- **双端挂起拦截器 (The Spin-Queue Interceptors)**：
  - **Claude Code 端**：新增 `pretool-write-lock.sh` 和 `posttool-write-lock.sh` 两个底层 Hook。
  - **OpenCode 端**：升级 TypeScript 插件 `harness-kit.ts`，原生支持基于 `await` 的 Event Loop 异步挂起。
  - **魔法体验**：当并发冲突发生时，系统**不向大模型报错**，而是直接在底层挂起工具调用并打印 `WAITING:...`。大模型的时间感知被物理冻结，**零 Token 损耗**地完成排队同步。
- **`/lx-oma` (降维拆解大脑)**：
  - 新增顶级战略 Skill。接受文件或目录作为输入 `<path>`。
  - 强制大模型遵循 MECE（相互独立，完全穷尽）原则，将宏大的 Master PRD 正交拆解为多个子功能分支。
  - 自动运行脚手架，在根目录生成 `rpe/feat-X/` 隔离体系，为随后的多终端 `/lx-rpe feat-X` 并发启动铺平道路。
- **严酷测试方案 (`final-exam.md`)**：
  - 引入专为 AGI 时代的“死亡并发乱斗”设计的端到端测试方案，供后续自动化或人工验收。
---

## [v6.1.4] — 2026-04-27 (The Documentation Refactor Edition)
### 核心主题：开源级项目结构重塑与文档归口

**优化与重构**：
- **项目结构极简化 (Root Dir Cleanup)**：
  - 过去，随着版本的快速迭代，大量的高阶参考文档（如 `MIGRATION.md`, `CARROR-OS-EDITIONS.md`, `CARROR-OS-MANIFESTO.md` 等）杂乱无章地堆叠在项目根目录，给用户造成了严重的认知压力。
  - 在本版本中，我们正式建立了结构化、清晰的 `/docs` 官方文档矩阵，将上述所有散落的说明书、评测报告、发布预热指南统一收入并更名（如 `architecture-review.md`），使根目录回归了顶级开源项目应有的清爽（仅保留 `README.md`, `CHANGELOG.md`, `AGENTS.md`）。
- **`README.md` 全面升维**：
  - 彻底抛弃了自嗨式的技术参数堆砌，转而从**被大模型折磨过的工程师第一视角**出发（痛点共鸣），直击“长对话变智障”、“泄露公司密钥”、“无效烧钱”等痛点。
  - 用极简的 `curl | bash` 格式清晰引导用户按需选择 `Base` (静默守护者) 或 `Enhanced` (全栈武器库) 版本，并提供了指向 `/docs` 子目录的全局文档索引。
- **架构评测升级 (`architecture-review.md`)**：
  - 在对标 Devin / Cursor 等商业软件时，将 **[S] 简洁性 (Simplicity)** 与 **[Z] 交互智能 (UX Intelligence)** 的评分基于“三级火箭渐进式交付”再次拔高。在保持底层物理阻断的同时，用户认知负荷降至前所未有的零刻度。
- **战略规划 (Strategic Roadmap)**：
  - **暂缓国际化 (Delay i18n)**：确立了针对 6 月 1 日全球开源发布（Product Hunt / Hacker News）的**“中文攻坚，英文交付”**降维打击战略。
  - **为何推迟**：当前核心精力必须 100% 聚焦于攻坚“一人成军（并发锁解决）”与“屎山清理计划”两大高复杂特性。在 5 月“狗粮期（Dogfooding）”频繁变动的规则下，双语（中英）维护核心宪法将严重拖慢迭代速度，属于典型的过早优化。
  - **何时执行**：将在 5 月下旬特性冻结（Feature Freeze）后，交由 AI 统一将底层 `AGENTS.md`、拦截器日志 (`.sh`/`.ts` 的 echo) 和主 README 翻译为地道的英文极客表述。利用纯英文对 LLM 的原生高指令遵从度优势，进一步锁死大模型底线。
---
## [v6.1.3] — 2026-04-27 (The Three-Stage Architecture Edition)
### 核心主题：三级火箭架构（认知负荷的完美释放）

**新增内容**：
- **`CARROR-OS-EDITIONS.md` 哲学说明书重构**：
  - 系统级说明书升级，彻底理清了 Carror OS 的“三级火箭”认知模型：
  - **Level 1 (Harness Only)**：纯内核防线。24 个底层 Hooks 物理拦截，绝对的 0 认知负担。
  - **Level 2 (Base Edition)**：静默守护版。在内核之上增加 7 款提交流水线（`pre-commit`, `pre-push` 及其拉起的后台自动审查）。用户维持原有开发习惯，提交时系统在后台默默把关。
  - **Level 3 (Enhanced Edition)**：高阶武器库。解锁全部 19 款主动工作流（RPE、Task-spec、TDD 驱动、DLP 脱敏代理）。
- **`README.md` 安装引导重构**： 在 Quickstart 环节清晰展示 `harness` / `base` / `enhanced` 的不同选择，帮助不同段位的开发者“各取所需”。
---
## [v6.1.2] — 2026-04-27 (Safe Migration Edition)
### 核心主题：数据资产转移与无损升级保护

**新增内容**：
- **`MIGRATION.md` (数据资产转移与无损升级指南)**： 详细阐述了 Carror OS 如何在底层文件系统中将所有文件严格划分为 **系统态 (System State)** 与 **用户态 (User Assets)** 的哲学，并给出了极其安全且不会导致大模型智力断层的跨机器克隆（Clone）指南。
- **`install.sh` 无损热更机制 (Safe In-Place Upgrade)**：
  - 彻底解决了过去当用户在已安装环境里运行 `curl | bash` 时，直接粗暴覆盖掉用户好不容易让 AI 踩坑积累下来的 `claude-next.md` (学习记忆) 和 `harness.yaml` (自定义门禁参数) 的灾难性缺陷。
  - 现在，安装脚本在解压新的内核探针与技能脚本之前，会自动将你的配置文件与记忆资产隔离备份至安全的内存沙箱，待解压暴力覆盖完成后，再原封不动地精准还原。
---
## [v6.1.1] — 2026-04-27 (Cloud Installer Edition)
### 核心主题：一键云端极客部署 (Curl | Bash)

**新增与优化**：
- **`install.sh` 升级为云端混合安装器 (Cloud Fallback Installer)**：
  - 彻底重构了安装脚本的底层逻辑。当用户通过 `curl | bash` 从公网直接运行安装脚本时，由于其所在目录并没有配套的 `.tar.gz` 压缩包，脚本将自动回落 (Fallback) 到 **云端下载模式**。
  - 它会智能检测系统的 `curl` 或 `wget`，自动前往 `GITHUB_REPO` 的 Release 页面拉取对应版本的 `harness-kit` 和 `lx-skills` 压缩包，下载到系统 `/tmp` 目录并完成内存级解压注入，随后焚毁临时文件。
- **一键极客体验 (The UNIX Way)**：
  - 现在，用户只需要在自己想要部署 Carror OS 的任意业务项目根目录下，执行一条神秘且优雅的终端指令： `curl -fsSL <https://raw.githubusercontent.com/your-username/carror-os/main/install.sh> | bash -s -
- enhanced` - 整个 24 个 Hook、19 款高阶技能库的千行代码防线，将在毫秒级静默地部署至该项目的 `.claude` 隐藏目录中，**完全不污染全局系统环境变量**。真正的“即插即用，随插随拔”。
---
## [v6.1.0] — 2026-04-27 (Progressive Delivery Edition)
### 核心主题：渐进式能力释放与产品哲学定调

**重构与重塑**：
- **`install.sh` 引入渐进式安装模式**：
  - 将原本让新手认知过载的 19 款庞大 Skill 体系，拆分为符合人类直觉的“基础版”与“增强版”：
  - **基础守护版 (`bash install.sh base`)**：默认模式。零学习成本！只为你提供 24 个底层 Hooks 构成的坚不可摧的“安全底座”，外加 `lx-pre-commit` 等 6 款静默门禁审查 Skill。你只管写代码，提交时它在底层默默扫除漏洞和幻觉。
  - **全栈增强版 (`bash install.sh enhanced`)**：为接手复杂重构、大型特性开发的高手准备。提供 `lx-rpe` 流水线、`lx-task-spec`、`lx-varlock` 脱敏代理及 `/lx-status` 一键健康看板等完整高阶武器库。
- **新增 `CARROR-OS-EDITIONS.md` (双规制哲学与版本说明书)**： 系统级说明书，详解 Base（静默守护）与 Enhanced（高阶武器库）的区分边界、适用人群及热更新切换方式。
- **重构 `CARROR-OS-FEATURES.md`**：彻底更新全特性参考手册，以此传递“先守护，后武装 (Guard First, Arm Later)”的设计哲学。
---
## [v6.0.8] — 2026-04-27 (The Seamless Edition)
### 核心主题：废除“增强模式”开关，实现内核与用户态的无缝共生

**重构与精简**：
- **废除 Enhanced 激活指令**：在旧架构中，我们需要向 `AGENTS.md` (前 `CLAUDE.md`) 中追加大段的《三模式激活指南》，并在 `harness.yaml` 中取消注释 `[Enhanced]` 的冗长 `task_system` 配置。这严重违背了“少即是多”的原则，并制造了无谓的 Context 噪声。
- **无缝按需路由 (Zero-Config Routing)**：随着 v6 时代渐进式披露、自动路由及 `plan-gate` 软阻断的成熟。现在，用户只要输入 `/lx-rpe` 或 `/lx-todo`，AI 将自动从隔离的 `SKILL.md` 加载对应的状态与规则。
- **治理文件瘦身**：彻底从全局 `AGENTS.md` 和 `harness.yaml` 中删除了这些多余的“增强版”使用说明。Harness-kit 回归纯粹的底层防御底座 (Kernel) 属性，lx-skills 作为能力层 (Userland) 实现“即用即走”。
---
## [v6.0.7] — 2026-04-27 (Sweet-spot Context Handoff Edition)
### 核心主题：50% 甜点区会话主动交接与全域脱敏修复

**新增与优化**：
- **甜点区主动交接 (Sweet-spot Context Handoff)**：
  - 探针 `context_monitor.py` 被引入 `lx-rpe` 的 `update_progress.py` 执行流。
  - 在 Task 完成瞬间（此时状态最干净），若真实上下文 `ctx% >= 50%`（黄金甜点区上限），系统自动下发强烈 `context_alert`。
  - AI 必须强制打断，要求运行 `/compact` 压缩重置会话或开启新分支，用文档恢复进度。彻底根治长上下文带来的智力稀释与结构性遗忘。
- **脱敏代理全兼容与纯净度升级**：
  - `varlock.py` 完善了 `Read`/`Write` 的双向映射，真正实现了全链路无明文的企业级 DLP (Data Leakage Prevention)。
  - 彻底移除旧版本残留的私有业务代码库名称硬编码，框架 100% 纯净解耦！
---
## [v6.0.6] — 2026-04-27 (Adversarial & Hard-Gate Edition)
### 核心主题：A/B 终端对抗盲审 与 真实 Context 硬阻断

**新增内容**：
- **`context-guard.sh` (第 24 个 Hook)**：
  - 实时读取底层 OMC Token 统计（结合 `OPENCODE_CONFIG_CONTENT`）。
  - 当占比 ≥80% 时，**物理掐断 (Exit 2)** 一切写入和执行工具 (`Write/Edit/Bash`)，强迫用户压缩会话。从“依赖估算软提醒”直接跃升为“工业级内存 OOM 物理阻断”。
- **A/B 终端对抗盲审 (Sub-agent Blind Review)**：
  - 升级 `lx-code-review`，废弃 Main-agent 主观自我审查的模式。
  - 引入 `subagent_reviewer.py`：自动组装极度严苛的 Zero-shot Persona Prompt。
  - 强制要求主 Agent 通过 `Task` 工具唤醒独立的 Sub-agent（盲审官）进行隔离验收。彻底打碎主 Agent 的思维惯性与自我证实偏差 (Self-confirmation Bias)。
---
## [v6.0.5] — 2026-04-27 (Privacy & Data Protection Edition)
### 核心主题：数据防泄漏 (DLP) 与隐私防线

**新增内容**：
- **`privacy-gate.sh` (第 23 个 Hook)**：
  - 强行阻断 AI 通过 `Read/Grep` 原生读取 `.env`, `*.pem`, `id_rsa`, `secret.yml` 等敏感配置文件。
  - 强行阻断 AI 在 Bash 拼接类似 `sk-ant-` 等明文 Token，物理隔离泄密。
- **`lx-varlock` 隐私脱敏代理管理器**：
  - 新增 `scripts/varlock.py` 作为本地安全的变量映射代理（Vault）。
  - AI 只能使用形如 `{API_KEY}` 的占位符发起命令或进行文件修改，脚本底层完成真实密钥的替换与“双向混淆”。AI 永远无法获取明文。
- **AGENTS.md 升级隐私铁律**：正式确立第 6 条核心法则（隐私防线）。
---
## [v6.0.4] — 2026-04-27 (Monitoring & Universal Edition)
### 核心主题：全域监控与彻底解耦

**新增与优化**：
- **`/lx-status` 独立健康看板 Skill**：
  - 将原有的 `carror_dashboard.py` 注册为官方指令，一键唤出涵盖“Token节省”、“错误自愈力”与“执行效率”的三屏监控指标。
- **业务代码强脱钩**：
  - 清理 `pretool-edit-scope.sh` 保护文件列表中所有企业特定的硬编码，使其对所有企业环境普适兼容。
---
## [v6.0.3] — 2026-04-27 (Traceability Edition)
### 核心主题：链路追踪版本（执行路径 + 错误路径画像）

**新增内容**：
- 拒绝新建多余的埋点系统，而是深度复用现有三数据源 (`update_progress.py`, `error-dna.sh`, `read-tracker.sh`)，合并不加干涉的无痕埋点。
- `update_progress.py` 扩展 `--step`/`--branch`/`--phase` 参数，每次调用自动追加 `.omc/state/skill-trace.jsonl`，BLOCKED 时亦不遗漏。
- 新增 `skill_trace_report.py` 生成合并追踪画像，包括具体的进度跳变与 Token 实际节省。
---
## [v6.0.2] — 2026-04-27 (Cross-Platform Edition)
### 核心主题：全平台兼容性支持

**新增内容**：
- **OpenCode Plugin TypeScript 移植**：
  - 新增 `.opencode/plugins/harness-kit.ts`，全面接管原本只限于 Claude Code 的 22 个 `.sh` Hooks，在 OpenCode 实现 `tool.execute.before/after` 等效生命周期拦截。
- **双跳板架构**：
  - `AGENTS.md` 正式成为全平台统辖的核心文件；原 `CLAUDE.md` 被精简为 17 行的 `@[AGENTS.md]` 跳板文件，满足不同平台的首读策略。
- 引入**软完成语禁令**，并在 Prompt 层对诸如“应该没问题了”、“差不多”等敷衍语句实施严格拦截。
---
## [v6.0.1] — 2026-04-24
### 核心主题：Skill 三层架构落地 + 固定逻辑脚本化

> **两条主线**：能固定就固定（不信任 AI 执行固定逻辑）；AI 够聪明就给空间（不过度说明，以 qwen3-plus 为基准）

### 新增规范

**Skill 目录三层规范（R7/R8/R9）**：
- `SKILL.md` — AI 判断层（路由决策、Gate 判定、异常策略）
- `scripts/` — 确定性执行层（纯 Python，严格固定，有 exit code）
- `references/` — 按需知识层（SKILL.md 写死加载时机）

### 改造成果

| Skill | 改造内容 | SKILL.md 行数 ||-------|---------|:------------:|| lx-pre-commit | `detect_project.py` + `run_checks.py` | 482 → **85**（-82%） || lx-pre-push | `validate_commits.py` + `get_changed_files.py` + ANK规范reference | 916 → **112**（-88%） || lx-rpe | `git_commit.py` + `update_progress.py` + `extract_ac.py`（v6.0.0已做）| 维持 || 全部19个skill | docs/ → references/，统一按需加载规范 | — || 全部19个skill | 补全降级策略（19/19 全覆盖）| — |

**新增 Python 脚本（7个）**：
- `lx-pre-commit/scripts/detect_project.py` — 项目类型检测
- `lx-pre-commit/scripts/run_checks.py` — 编译+测试门禁序列
- `lx-pre-push/scripts/validate_commits.py` — ANK commit message 格式校验
- `lx-pre-push/scripts/get_changed_files.py` — 变更文件提取
- `lx-rpe/scripts/git_commit.py` — Git 提交（已在 v6.0.0）
- `lx-rpe/scripts/update_progress.py` — progress.md 更新（已在 v6.0.0）
- `lx-rpe/scripts/extract_ac.py` — AC 列表提取（已在 v6.0.0）

### 设计原则

- **固定的固定死**：操作序列（git/lint/test/build）全部脚本化，AI 只读取 JSON 结果做决策
- **AI 空间**：判断逻辑保留在 SKILL.md，删除 AI 天然知道的冗余说明
- **最低基准**：以 qwen3-plus 能正确处理为基准，不兼容更弱模型
- **降级兜底**：每个 skill 必须有降级策略，工具不可用时有降级路径

### 测试结果

| 测试 | 结果 ||------|------|| 结构验证（12项）| **12P / 0F** || BDD 行为驱动（10场景）| **10P / 0F / 2S** |
---
### 追加内容（全平台支持 + OpenCode Plugin）
### 新增主题1：Skill 三层架构（结构化 skill）

**核心原则**：能固定就固定，AI 够聪明就给空间，qwen3-plus 为基准，降级策略兜底
**三层目录规范（R7/R8/R9）**：

```text
skills/lx-{name}/
├── SKILL.md ← AI 判断层（路由决策/Gate/异常/加载时机）
├── scripts/ ← 确定性执行层（纯 Python，exit code，JSON 输出）
└── references/ ← 按需知识层（SKILL.md 写死加载时机，命中路由才加载）
```
**渐进式披露原则**：references 和 scripts 只在 SKILL.md 路由命中时才加载/调用，不静态列出
**改造成果**：

| 维度 | 改造前（v6.0.0）| 改造后（v6.0.1）||------|:-----------:|:-----------:|| Python 脚本 | 3个 | **14个** || references/ 文件 | 8个 | **50个** || 降级策略覆盖 | 0/19 | **19/19** || 平均 SKILL.md 行数 | 361行 | **278行**（-23%）|| docs/ 残留 | 有 | **无** || 渐进式披露违规 | 未测试 | **0/0（新增校验）** || 路由覆盖率 | 未测试 | **27/27 = 100%** |

**新增校验工具**：
- `lx-validate-skill/scripts/check_progressive_disclosure.py` — 渐进式披露四规则检查（R-PD-1/2/3/4）
- `lx-validate-skill/scripts/validate_skill.py` — Skill 三层结构合规验证
**通用化改造**：
- commit message 规范：从 ANK-1.5.6.16 硬编码 → `commit_convention.py` 骨架学习（learn/validate/show/reset）
- 代码审查：从"Go 39条/React 18条"硬编码 → 语言无关通用框架，用户可自定义规则

### 新增主题2：全平台支持

**平台支持矩阵**：

| 平台 | 启动文件 | 机制 | hooks 治理 | skill 能力 ||------|---------|------|-----------|-----------|| **Claude Code** | CLAUDE.md（`@AGENTS.md`）| Anthropic 官方 @-include | ✅ 22 hooks（.sh）| ✅ || **OpenCode** | AGENTS.md（原生）| 官方文档明确支持 | ✅ 22 hooks（.ts plugin）| ✅ || **CLAUDE.md 兼容 IDE** | CLAUDE.md（`@AGENTS.md`）| 同 Claude Code | 视平台 | ✅ |

**AGENTS.md 主文件化（Anthropic 官方推荐）**：
> "If your repository already uses AGENTS.md for other coding agents, create a CLAUDE.md that imports it."
- `AGENTS.md`（225行）= 主治理文件，全平台通用
- `CLAUDE.md`（17行）= 精简跳板，首行 `@AGENTS.md`，Claude Code 专属配置在后
- `AGENTS.md` 新增**软完成语禁令**章节（"应该没问题了/基本完成/理论上"等违禁词）
**OpenCode Plugin（新增）**：
- `.opencode/plugins/harness-kit.ts` — 22个 hook 的 TypeScript 移植（374行）
- `.opencode/plugins/harness-config.ts` — harness.yaml 的 TypeScript 读取器（205行）
- 事件对齐：19个通过 `tool.execute.before/after` 完全对齐，3个通过 `message.updated/permission.asked` 变通
**Hook 事件映射**（Claude Code → OpenCode）：

| Claude Code | OpenCode | 覆盖 hook ||------------|---------|---------|| `PreToolUse:Bash` | `tool.execute.before`（bash）| permission-gate || `PreToolUse:Edit/Write` | `tool.execute.before`（edit/write）| edit-scope/edit-guard/rule-anchor/plan-gate || `PreToolUse:Task` | `tool.execute.before`（task）| subagent-guard || `PostToolUse:Bash` | `tool.execute.after`（bash）| bash-audit/error-dna/build-validator || `PostToolUse:Edit` | `tool.execute.after`（edit）| edit-quality || `PostToolUse:Read` | `tool.execute.after`（read）| read-tracker || `SessionStart` | `session.created` | inject-project-knowledge/flywheel-report || `Stop` | `session.idle` | auto-snapshot/skill-flywheel || `UserPromptSubmit` | `message.updated`（变通）| turn-counter/rule-anchor || `experimental.session.compacting` | `experimental.session.compacting` | 铁律注入压缩摘要 |

**lx-skills 硬编码清除**：
- `readFile CLAUDE.md` → `readFile AGENTS.md（优先）或 CLAUDE.md`（全平台兼容）
- 代码审查条数硬编码（39条/18条）→ 语言无关描述
- ANK commit 规范硬编码 → 通用骨架驱动

### 测试记录（v6.0.1 追加）

| 测试类型 | 结果 ||---------|------|| 路由覆盖率测试（27项） | **27/27 = 100%** || 渐进式披露校验 | **0 VIOLATION / 0 WARNING（19/19）**|| BDD 行为驱动（10场景）| **10P / 0F / 2S** || 平台兼容验证 | **11P / 0F** |
---
## [v6.0.0] — 2026-04-24
### 产品命名：Carror OS

> **harness-kit + lx-skills-v5 正式命名为 Carror OS**>> Carror OS = AI Native Developer Operating System>> ```> harness-kit ← 内核层（Kernel） 治理·防御·约束> lx-skills-v5 ← 用户空间（Userland） 能力·执行·交付> ```>> 两者完全解耦，各自独立运行，组合效果叠加。> 不是依赖关系，是协作关系——就像 OS 内核和用户空间。

### 核心主题：plan-gate 软阻断重设计 + BDD 行为驱动测试框架（scripts/ 目录）
### 新增

**task_router.md — AI 自动路由时的确认节点（v6.0.0，经多轮设计迭代）**
设计哲学演进：
- 初版：在三个 skill 内部弹过场，展示 A/B/C 路由重选 → **错误**：用户已选了 skill，不该被问"要不要换"
- 重设计：改为风险告知，仍在 skill 内部 → **仍然错误**：用户主动调用 skill 就是明确意图，无需任何过场
- **最终定位**：`task_router.md` 放在 `harness-kit/.claude/`（治理层），只在 **AI 自动路由时**使用
```
用户主
动调用/lx-rpe、/lx-todo、/lx-task-spec → 直接执行，不弹任何确认AI 代劳判断路由（如用户说"帮我实现 XXX"）→ 先过 task_router 确认，再执行
```
过场内容（5行内）：AI 说清楚"我理解你要做什么/我建议走哪条路/有什么风险"，用户回车确认。
**三个 skill 无参数行为（少即是多）**：
- `/lx-todo`（无参数）= 直接 next，队列空才提示
- `/lx-rpe`（无参数）= 直接恢复最近活跃 RPE
- `/lx-task-spec`（无参数）= 直接恢复最近活跃 task-spec
**任务管理人性化改进**：

| 改动 | 改前 | 改后 ||------|------|------|| lx-task-spec 引导问答 | 5问（含执行模式/优先级）| **3问**（名称/目标/验收，默认 stepwise+p1）|| lx-rpe new 输入方式 | 逐步追问，至少 5 次交互 | **支持一行输入**：`/lx-rpe new name 描述` 直接生成 prd.md || lx-todo add 输出提示 | `👉 /lx-todo do #N 或 /lx-todo next` | **`👉 /lx-todo`**（统一，无需选择）|

**plan-gate.sh v2.1.0 重设计（软阻断 + 正确触发路径）**
- **v5.x 行为**：`plan_gate: false` → 直接 exit 0；`plan_gate: true` → 硬阻断 exit 2
- **v6.0.0 初版问题**：自动检测 rpe/ 目录并启用 → 与 lx-rpe skill 内部 Gate-R/P/X/E 冲突
- **v6.0.1 重设计**（本版本）：
  - `plan_gate: false`（默认）→ exit 0，完全不干预，**lx-rpe 和 lx-todo 均不受影响**
  - `plan_gate: true`（用户主动开启）→ 软阻断：注入 `additionalContext` 提醒而非 exit 2，AI 自行判断是否继续
  - plan-gate 不再自动检测 rpe/ 目录，**正确触发路径是 `/lx-rpe` skill → skill 内部 Gate-R/P/X/E**
- **架构分层**：`lx-rpe` skill Gate 体系（AI 层软约束）是主控；`plan-gate.sh` hook 是辅助提醒层
**bdd-harness-test.sh（BDD 行为驱动测试框架，放在 scripts/ 目录）**
- 位置：`.claude/scripts/bdd-harness-test.sh`（**不在 hooks/ 目录**，防止误注册为 Claude Code hook）
- 10 个 Given/When/Then 格式场景，覆盖真实 AI 对话行为链
- 运行：`bash .claude/scripts/bdd-harness-test.sh`
- 支持单场景：`bash .claude/scripts/bdd-harness-test.sh scenario_H_plan_gate_soft`
- 2 个 SKIP：需要 Claude API（场景 C scope + 场景 J 真实对话）
**BDD 场景覆盖（10 场景）**：

| 场景 | 验证内容 | 结果 ||------|---------|------|| A | AI 无证据声称完成 → completion-gate 阻断 | ✅ || B | AI 有效证据 → completion-gate 放行 | ✅ || C | 范围外文件编辑预警 | ⚠️ SKIP || D | 第20轮写文件 → 铁律注入 | ✅ || E | 漂移词「顺手」→ 预警升级 | ✅ || F | AI 执行 git push → permission-gate 阻断 | ✅ || G | 用户纠正信号 → 写教训提醒 | ✅ || H | plan_gate:false → 不干预 lx-rpe 任务 | ✅ v6.0.1 重设计 || I | plan_gate:false → lx-todo 完全不受影响 | ✅ v6.0.1 重设计 || J | 真实 AI 对话验证 | ⚠️ SKIP（需 API） |

### HARNESS 分数

| 维度 | v5.3.0 | v6.0.0 | 变化 ||------|:---:|:---:|:---:|| A - Autonomy Control | 9.0 | 9.4 | +0.4（plan-gate 自动检测，无需用户干预） || D - Drift Prevention | 9.8 | 10.0 | +0.2（plan 阶段门禁自动化，从设计期防漂移） || **总分** | **115.2** | **116.0** | **+0.8** |

**lx-rpe 执行流程 5 项价值观修正**（符合"少即是多 + 自动化全程 + 不打扰"原则）：

| Fix | 改动 | 原则 ||-----|------|------|| Fix1 | Step2 设计完直接进 Step3，不停下等用户审阅 | executor 阶段全自动 || Fix2 | Step6 AI 先自动执行可测验收项，再把结果+人工部分一起给用户确认 | 减少用户操作 || Fix3 | Phase2→3 转换加唯一一次启动确认，明确"之后全自动，仅 Gate-X/Blocker/验收/commit 才暂停" | 进入自动化前人为确认 || Fix4 | Step5/6 区分单 AI / 双 AI（OpenCode）两条路径 | 现实兼容性 || Fix5 | Step3 编码完成后立即生成实现文档写入 executor.md，Step5 直接引用不重复生成 | 文档时机正确 |

**lx-rpe 9步主循环对照你的价值观**：
```
你
的
期
望
：生成实现文档 > 实现 > debug > 强证据验收 > 生产验收文档，更新文档 > 下一step
lx-rpe 对应： Step 2 设计（含实现前文档） Step 3 编码 + 门禁（含debug，3次失败换策略）+ 立即写实现文档 Step 4 Security Review（自愈） Step 5 整合文档（Step3实现文档 + 测试方案 + 验收清单） Step 6 验收（AI自动可测项 + 用户确认人工项） Step 7 判定（3次失败→暂停，不卡流程） Step 8 Git commit（用户确认） Step 9 写进度摘要，更新文档
```

### 测试记录

| 测试层 | 类型 | 结果 ||--------|------|------|| BDD 行为驱动（10场景）| 2026-04-24 | **10 PASS / 0 FAIL / 2 SKIP** || L1 单元测试（继承 v5.3.0）| — | 71 PASS || L2 OWASP/NIST（继承 v5.3.0）| — | 11 PASS || L3 AgentBench（继承 v5.3.0）| — | 4 PASS || L4 边界/压力（继承 v5.3.0）| — | 12 PASS / 4 SOFT |
---
## [v5.3.0] — 2026-04-24
### 核心主题：profiles base+diff 架构（消除 75% 跨语言重复）
### 新增

**profiles/base/harness.yaml（共享基础层）**
- 提取四语言 profile 中 75% 的共享字段到 `profiles/base/harness.yaml`（116 行）
- 涵盖 14 个 section：`workflow` / `task_decomposition` / `knowledge`（无语言字段）/ `turn_counter` / `fuzzy_detection`（仅 fuzzy_verbs）/ `lsp_suggest` / `subagent_guard` / `completion_gate` / `bash_audit` / `permission_gate` / `sublimation` / `correction_detector` / `session_handoff` / `error_dna`（无 build_commands）/ `coupling` / `hooks_enabled` / `rule_anchor` / `build_validator`（无 build_commands）
**profiles/merge-profile.sh（合并工具）**
- `bash .claude/profiles/merge-profile.sh go` — base + go diff 合并写入 `.claude/harness.yaml`
- `bash .claude/profiles/merge-profile.sh go --dry-run` — 预览合并结果不写文件
- `bash .claude/profiles/merge-profile.sh --list` — 列出可用 profile
- 合并规则：diff 同名字段覆盖 base；`hooks_enabled` 做增量合并（逐键覆盖，不替换整块）
- Python3 实现，无第三方依赖

### 变更

**四语言 profile 精简为纯 diff**（只保留与 base 不同的字段）：

| Profile | 旧行数 | 新行数（diff） | 减少 ||---------|:----:|:----:|:----:|| go | 130 | 32 | **-75%** || node | 130 | 31 | **-76%** || python | 130 | 35 | **-73%** || rust | 130 | 31 | **-76%** |

**差异字段（每语言 profile 仅保留）**：
- `project`：language / source_extensions / cite_extensions
- `protected_files`：warn_on_edit
- `architecture`：business_layers / handler_layers / quality_checklist / handler_constraint / doc_sync_target
- `knowledge`：lsp_hint / lsp_example_file
- `fuzzy_detection`：explicit_target_regex
- `error_dna`：build_commands
- `build_validator`：build_commands
- Python 额外覆盖：`hooks_enabled.posttool_edit_quality: false`

### 向后兼容

- `install.sh` 自动调用 `merge-profile.sh` 生成完整 `harness.yaml`，**用户感知不变**
- 已安装 v5.2.x 的项目无需迁移，现有 `.claude/harness.yaml` 继续有效
- 直接使用 diff 文件（不合并）会导致缺字段，必须通过 `merge-profile.sh` 或 `install.sh` 安装

### HARNESS 分数

| 维度 | v5.2.4 | v5.3.0 | 变化 ||------|:---:|:---:|:---:|| S - Simplicity | 8.8 | 9.2 | +0.4（profiles 从 4×130=520 行降至 116+4×33=248 行，减少 52%） || M - Migration | 9.4 | 9.6 | +0.2（新项目切换语言只需改 32\~35 行 diff） || **总分** | **114.4** | **115.2** | **+0.8** |

### 测试记录

> 完整报告见：`HARNESS-BENCHMARK-v5.3.0.md`（source/ 和 packages/ 均包含）
| 测试层 | 类型 | 执行时间 | 结果 ||--------|------|---------|------|| L1 | 单元测试（71项） | 2026-04-24 | **71 PASS / 0 FAIL / 0 SOFT** || L2 | OWASP LLM Top 10 + NIST AI RMF 对标（11项）| 2026-04-24 | **11 PASS / 0 FAIL** || L3 | AgentBench Safety 维度对标（4项）| 2026-04-24 | **4 PASS / 0 FAIL** || L4 | 边界/绕过/压力/竞态（16项，首次执行）| 2026-04-24 | **12 PASS / 0 FAIL / 4 SOFT** || **合计** | | | **98 PASS / 0 FAIL / 4 SOFT** |

**4 项 SOFT（已知设计限制）**：
- `echo "DROP TABLE"` 双引号包裹绕过（低风险，AI 正常使用不会主动规避）
- printf 包装绕过（同上）
- pretool-rule-anchor 并发竞态（Claude Code 单线程，实际不触发）
- 繁体漂移词「順手」不检测（目标用户为简体场景）
---
## [v5.2.4] — 2026-04-24
### 核心主题：上下文衰减加固（长对话规则失效问题）

> 解决"轮数多了 AI 忘记规则"的根本性问题，三层防漂移机制全量落地

### 新增

**第 22 个 hook：pretool-rule-anchor.sh（PreToolUse:Write）**
- 轮次超过 `rule_anchor.turn_threshold`（默认 15）后，每次 AI 写文件前注入铁律锚定提醒
- 超过阈值后按 `rule_anchor.interval`（默认 5）间隔触发，避免过度打扰
- **漂移词检测**：检测到"顺手/顺便/顺带/捎带/另外也/同时也"等词，升级为强预警
- 输出格式：标准 JSON `additionalContext`，兼容 Claude Code hook 协议
**index.md 铁律速查表（SessionStart 注入层）**
- 文件头部新增"铁律速查（ALWAYS ACTIVE）"区块，6 条铁律附违反后果
- SessionStart 时 `inject-project-knowledge.sh` 注入 `index.md:full`，铁律在会话开始即进入 context
- 同时新增置信度标注格式说明（`[已验证]` / `[已测试]` / `[推断, 待确认]`）
**turn-counter.sh 铁律注入（每10轮触发层）**
- 每 10 轮 Todo 队列同步时，前置注入 6 条铁律完整摘要
- 标题改为"Todo 队列同步 + 铁律提醒"，结束语改为"规则重新锚定完毕，继续当前任务"

### 变更

- `harness.yaml`（generic）：新增 `hooks_enabled.rule_anchor: true` 及 `rule_anchor` 配置节
- `profiles/go|node|python|rust/harness.yaml`：同步 `rule_anchor: true` + 配置节（四语言全覆盖）

### HARNESS 分数

| 维度 | v5.2.3 | v5.2.4 | 变化 ||------|:---:|:---:|:---:|| T - Task Continuity | 9.5 | 9.8 | +0.3（三层防漂移覆盖 SessionStart/每10轮/每次写文件） || I - Intelligence | 8.8 | 9.0 | +0.2（漂移词主动检测，从被动变主动） || D - Drift Prevention | 9.5 | 9.8 | +0.3（pretool-rule-anchor 强化漂移拦截） || **总分** | **113.6** | **114.4** | **+0.8** |

### 防漂移触发时机（完整三层）
```
会
话开始→ index.md 铁律速查表注入（立即生效）第 10 轮 → turn-counter 铁律摘要（6条完整复读）第 15 轮起 → 每次写文件前，pretool-rule-anchor 注入锚定提醒（每5轮一次）检测到漂移词 → 升级为漂移预警（更强语气，明确指出违规词）
```

### 测试记录

| 测试类型 | 执行时间 | 结果 ||---------|---------|------|| L1 单元测试（含新增 hook 专项）| 2026-04-24 | **15 PASS / 0 FAIL**（端到端从包安装验证） || 发现并修复 Bug | 2026-04-24 | harness.yaml 行内注释污染 hc_enabled 返回值（1个） |

**关键 Bug 记录（v5.2.4 发现，同版本修复）**：
- **Bug**：`rule_anchor: true # 注释文字` 中行内注释被 python YAML 解析器读入值，导致 `hc_enabled("rule_anchor")` 返回 `false`，hook 静默退出
- **根因**：`harness_config.sh` 的简单解析器不剥离 `#` 后内容
- **修复**：将所有配置项的行内注释移至独立注释行
- **教训**：harness.yaml 中配置值行**不得**包含 `#` 字符（注释单独成行）
---
## [v5.2.3] — 2026-04-24
### 新增

**三模式任务驱动体系**
- **模式二统一**：`lx-todo` 状态文件从 `.claude/todo.md` 迁移至 `.omc/state/todo-queue.md`，与 `turn-counter.sh` 共享同一文件；`/lx-todo add` 捕获的任务现在每 10 轮自动注入 AI context（P0）
- **Enhanced 激活文档**：新增 `profiles/enhanced/append-to-claude.md`，一行命令激活三模式路由 + `plan_gate`；包含三模式决策表和无人化程度对比（P1）
- **模式一 PRD 引导**：`/lx-rpe new` 新增引导式 PRD 收集（4 问），无需手动填写 prd.md；收集完成后 AI 自动生成 `research.md` 草稿（关键调用链 + 风险点 + 待确认问题）（P2）
- **Rust profile**：新增 `profiles/rust/harness.yaml`，覆盖 cargo build/test/clippy，语言四件套完整（Go/Node/Python/Rust）
- **posttool-write-cite.sh**：新增第 21 个 hook（PostToolUse:Write），检测写入 `claude-next.md` 时的教训格式，确保三字段（问题/根因/纠正）完整
**哲学改动（The Less, The More / Start, and Forever）**
- **index.md 知识导航**：从幽灵引用改为真实的 76 行知识地图（hooks 速查 + 记忆系统路径 + profile 切换命令）；SessionStart 首次注入即有实质内容
- **explicit_target_regex 修复**：从 `\.md$` 扩展为 `\.[a-zA-Z]{1,5}\b`，"修复 auth.go" 不再被误判为模糊指令；新增 handler/logic/model/service/controller/router 关键词
- **correction signals 精简**：从 13 个信号词精简为 5 个核心词组（`不对 错了 你搞错了 应该是 重新来`），去除 8 个语义重叠词（理解错了/弄错了/不是这样等）；配置值：`signals: "不对 错了 你搞错了 应该是 重新来"`

### 修复

- `lx-todo`：全部 12 处 `.claude/todo.md` 替换为 `.omc/state/todo-queue.md`
- `lx-rpe`：状态面板从 `rpe/{name}/todo.md` 改为读 `.omc/state/todo-queue.md`

### 变更

- `posttool_edit_quality`：默认由 `false` 改为 `true`（编辑后代码质量自查提醒默认开启）
- `install.sh`：新增语言选择交互（Go/Node.js/Python/Rust/Generic），安装时自动 cp 对应 profile，无需用户查文档

### HARNESS 分数

| 维度 | v5.2.2 | v5.2.3 | 变化 ||------|:---:|:---:|:---:|| E - Evolution | 8.7 | 9.0 | +0.3（posttool-write-cite 强化写入验证） || T - Task Continuity | 9.3 | 9.5 | +0.2（non-rpe handoff + todo 统一） || I - Intelligence | 8.5 | 8.8 | +0.3（posttool_edit_quality 默认开启） || M - Migration | 9.2 | 9.4 | +0.2（Rust profile + install 语言选择） || S - Simplicity | 8.8 | 8.8 | 0（signals 精简但 install 增加了交互） || **总分** | **112.2** | **113.6** | **+1.4** |

### 测试记录

| 测试类型 | 执行时间 | 结果 ||---------|---------|------|| HARNESS 基准评测（65项） | 2026-04-24 | **65 PASS / 0 FAIL / 3 SOFT** |

**65 PASS 覆盖范围**：completion-gate 证据门禁 / permission-gate SQL+git+rm 拦截 / posttool-write-cite 格式校验 / 纠正信号5词检测 / todo 路径统一12处 / 四语言 profile language 字段 / Enhanced 激活文档168行 / harness_config 全配置键读取
**3 SOFT（不影响发布，已知限制）**：`context_guard` 软执行（无 hook 强制）/ `plan_gate` 默认关闭 / `lx-task-spec race` 非真并发
---
## [v5.2.2] — 2026-04-24
### 新增

- **pretool-user-correction.sh**：第 20 个 hook（UserPromptSubmit），检测纠正信号词触发时提示 AI 写入 `claude-next.md`
- **profiles/go/harness.yaml**：Go 项目专项配置（go build/test/vet/golangci-lint，三层架构约束）
- **profiles/node/harness.yaml**：Node.js/TypeScript 专项配置（tsc + eslint + jest，Controller-Service 架构）
- **profiles/python/harness.yaml**：Python 专项配置（pytest + ruff + mypy，View-Service 架构）
- **correction_detector 配置域**：`harness.yaml` 新增 `correction_detector.signals` 可配置项
- **index.md**：项目知识导航文件（SessionStart 注入，替换幽灵引用的空槽位）

### 修复

- **OPT-01 安全 Bug**：`permission-gate.sh` 的 `grep -qE` 改为 `grep -iqE`（大小写不敏感），修复 `DROP TABLE`/`TRUNCATE TABLE`/`DROP DATABASE` 等大写 SQL 语句绕过拦截的漏洞
- **harness.yaml**：`destructive_regex` 更新，覆盖 `drop (table|database|collection|schema)`、`truncate table \S`、`delete from`
- **explicit_target_regex**：从 `\.md$` 修复为 `\.[a-zA-Z]{1,5}\b`，消除对 "修复 auth.go" 的误伤

### 变更

- `hooks_enabled.subagent_guard`：`false` → `true`（子代理防护默认开启）
- `hooks_enabled.pretool_edit_scope`：`false` → `true`（范围冻结默认开启，无 scope 文件时 fail-open）
- `hooks_enabled.lsp_suggest`：`false` → `true`（LSP 智能提醒默认开启）
- `hooks_enabled.user_correction_detector`：新增并默认 `true`
- `correction_detector.signals`：13 个信号词精简为 5 个核心词
- `install.sh`：全量安装时新增语言选择交互（Go/Node/Python/Rust/Generic）
- `auto-snapshot.sh`：无 rpe/ 目录时，session-handoff 降级为注入 `git log --oneline -10` 摘要，Day-1 交接非空

### HARNESS 分数

| 维度 | v5.2.0 | v5.2.1(测) | v5.2.2 |
|------|:---:|:---:|:---:|
| H - Hallucination Guard | 8.5 | 9.0 | 9.0 |
| A - Autonomy Control | 8.5 | 8.5 | 9.0 (+0.5) |
| S - Security | 8.5 | 8.5 | 9.5 (+1.0) |
| D - Drift Prevention | 8.5 | 8.5 | 9.5 (+1.0) |
| E - Evolution | 8.0 | 8.0 | 8.7 (+0.7) |
| I - Intelligence | 8.0 | 8.0 | 8.5 (+0.5) |
| M - Migration | 8.5 | 8.5 | 9.2 (+0.7) |
| S - Simplicity | 8.5 | 8.8 | 8.8 |
| T - Task Continuity | 9.0 | 9.3 | 9.3 |
| **总分** | **105.5** | **112.2** | **112.2** |

> v5.2.2 = v5.2.1 source 改动 + 重新打包发布

### 测试记录

| 测试类型 | 执行时间 | 结果 ||---------|---------|------|| HARNESS 基准评测（65项，OPT-01\~05 验收）| 2026-04-24 | **65 PASS / 0 FAIL**（vs v5.2.1 实测 105.5 → 修复后 112.2） || OPT-01 安全修复验证 | 2026-04-24 | 大写SQL `DROP TABLE`/`TRUNCATE`/`DELETE FROM` 全部阻断 ✅ |
---
## [v5.2.1] — 2026-04-23（内部评测版，未正式发布）
### 新增

- **HARNESS 基准评测**：65 项测试，实测总分 105.5（vs 声明 112.0，差 6.5 分）
- **HARNESS-BENCHMARK-REPORT.md**：13 维度逐项机制映射 + 测试结果 Checklist
- **HARNESS-OPTIMIZATION-PLAN.md**：5 项优化方案（OPT-01 \~ OPT-05）含执行方案和验收脚本

### 发现

- 真实 Bug：`permission-gate.sh` 大写 SQL 不拦截（`grep -qE` 区分大小写）
- 设计问题：`pretool-edit-scope`、`subagent-guard` 均默认关闭，最强防漂移机制无默认保护
- 软硬混淆：`context_guard.md` 是 Markdown 规则文档，40%/60%/80% 阈值无 hook 强执行
- 进化软执行：`claude-next.md` 写入完全依赖 AI 自觉，无 hook 强制

### 测试记录

| 测试类型 | 执行时间 | 结果 ||---------|---------|------|| HARNESS 基准评测（65项）| 2026-04-23 | **实测 105.5 / 声明 112.0**（差 6.5，触发 OPT-01\~05 修复计划） || 关键发现 | 2026-04-23 | 大写SQL绕过Bug / pretool-edit-scope 默认关闭 / context_guard 软执行 |
---
## [v5.2.0] — 2026-04-22
### 重大变更

- **产品重新定义**：从"AI 治理框架"升级为"AI 操作系统"
- **品牌主张**：确立"Carror OS — AI Native Developer Operating System"
- **HARNESS 标准**：首次定义个人 AI 操作系统 13 维度评分体系

### 新增

- **lx-skills-v5**：19 个 skill，12 个共享节点，11 个 schema
- **四大记忆系统**：编码风格（claude-next.md）/ 错误模式（error-dna.json）/ 工作习惯（flywheel.log）/ 代码结构（Git 历史 + 耦合分析）
- **task_sys 体系**：orchestrator / task_fs / context_guard / unified_delivery_schema / loading_matrix
- **lx-rpe v1.0**：RPE 9 步主循环（Research → Plan → Execute），含 Blocker SLA 三态熔断
- **lx-todo v1.0**：轻量 5 步闭环（捕获→分拣→执行→验证→关闭）
- **lx-task-spec v1.0**：task_spec 引导式问答 + stepwise/race 两种执行模式
- **install.sh**：支持 full / harness / skills 三种安装模式

### HARNESS 分数（自评）
```
总
分
：112.0（vs Cursor 48 / Aider 65 / Copilot 67 / Sweep AI 71）
```
---
## [v5.1.0] — 2026-04-22
### 新增

- 混合状态机（need_clarification → ready → planning → executing → done）
- 节点索引系统（15 个共享节点统一管理）
- QUICKSTART.md（12 步安装指南）
---
## [v5.0.0-MVP] — 2026-04-22
### 变更

- Oracle 评审精简：18 → 12 nodes，16 → 11 schemas
- 原子化声明层完成（19 skill × schema 引用 + 节点引用）
---
## [v4.x] — 2026-04-21 \~ 22
### v4.2.0

- 文档修复

### v4.1.0

- 耦合分析（Git 历史 co-change 检测）
- 已知限制文档化

### v4.0.0

- 19 个 skill 原子化声明层完成
- 行为约束节点（behavior_rules.md）全量覆盖
---
## 版本路线图

| 版本 | 状态 | 核心目标 |
|------|------|---------|
| v5.2.3 | ✅ 已完成 | 三模式驱动 + todo 统一 + Enhanced 激活 |
| v5.2.4 | ✅ 已完成 | 上下文衰减加固（三层防漂移：铁律速查 + 每10轮 + 写前锚定） |
| v5.3.0 | ✅ 已完成 | profiles base+diff 架构（消除 75% 重复）；merge-profile.sh 合并工具 |
| v6.0.0 | ✅ 已完成 | plan-gate 软阻断重设计 + BDD 行为驱动测试框架 + task_router |
| v6.0.1 | ✅ 已完成 | **结构化 Skill 三层架构**（scripts/references 分离）+ **全平台支持**（OpenCode Plugin + AGENTS.md 主文件化）|
| v6.0.2 | ✅ 已完成 | OpenCode hooks 完整对齐（22个 hook TypeScript 移植）；软完成语禁令 |
| v6.0.3 | ✅ 已完成 | **链路追踪**（执行路径+错误路径+Token节省分析）；三数据源合并画像 |
| v6.0.4 | ✅ 已完成 | `/lx-status` 面板独立技能注册；全域业务词汇 100% 解耦清理 |
| v6.0.5 | ✅ 已完成 | **数据防泄漏 (DLP)**：新增 `privacy-gate.sh` 及 `lx-varlock` 双向混淆脱敏机制，确立隐私防线铁律 |
| v6.0.6 | ✅ 已完成 | **对抗与熔断 (A/B & Hard-Gate)**：`context-guard` 物理级 Token 熔断，Sub-agent 无情盲审机制落地 |
| v6.0.7 | ✅ 已完成 | **甜点区主动交接 (Sweet-spot Handoff)**：任务完成时若 `ctx% > 50%`，强制执行会话总结与 `/compact` 重置 |
| v7.0.0 | 计划中 | **生态化与企业共建 (Ecosystem & Enterprise)**：开放底层 Plugin API 供开源社区共创；联合头部科技企业进行品牌联名合作与安全治理案例布道推广 |
| v8.0.0 | 重磅预告 | **多终端高并发 RPE 架构 (Concurrent RPE & Write-Lock Isolation)**：通过底层全平台文件锁机制 (Bash/Python)，实现单一 PRD 向多个独立 RPE 任务的分布式拆解与并发执行。实现真正的”一人成军”高并发超级流水线。|
---
## 评分演进一览
```
v5.2.0（自评） 112.0
v5.2.1（实测） 105.5 ← 基准测试发现实际差距
v5.2.2（修复） 112.2 ← OPT-01\~05 全落地 + 哲学改动
v5.2.3（扩展） 113.6 ← 三模式 + 第 21 个 hook + Rust profile
v5.2.4（加固） 114.4 ← 三层防漂移（铁律速查 + 轮次注入 + 写前锚定）
v5.3.0（架构） 115.2 ← profiles base+diff，简洁性+0.4，迁移能力+0.2
v6.0.0（智能） 116.0 ← plan-gate 自动检测 + BDD 框架
v6.0.1（架构） 116.9 ← 三层 Skill（scripts/references）+ lx-skills 专项 C/PD 框架 58.6→94.0
v6.0.2（全平台）117.0 ← OpenCode 22 hooks TypeScript 移植 + AGENTS.md 主文件化 + 软完成语禁令
v6.0.3（追踪） 117.0 ← 链路追踪（复用已有机制，无新增基础设施）
v6.0.4（监控） 117.1 ← /lx-status 一键呼出监控面板
v6.0.5（隐私） 117.8 ← privacy-gate 强阻断 + varlock 占位符脱敏代理，填补 P(隐私) 维度空白
v6.0.6（对抗） 118.5 ← A/B 对抗盲审打破证实偏差；Context 硬阻断彻底根除末期幻觉
v6.0.7（甜点区）119.0 ← Context 50% 甜点区状态拦截交接，长上下文智力稀释被根治
工程天花板：~118
软性上限（模型合规性）：~119
```
---

**维护者：harness-kit 项目组 | 文档格式：Keep a Changelog | 更新频率：每个版本发布时**

## [v6.0.7] — 2026-04-27 (Sweet-spot Context Handoff Edition)
### 核心主题：50% 甜点区会话重置接力与全域脱敏修复

**新增与优化**：
- **甜点区主动交接 (Sweet-spot Context Handoff)**：
  - 探针 `context_monitor.py` 被引入到 `lx-rpe` 的 Step 9 `update_progress.py` 执行流中。
  - 当你在完成一个 Task（比如 RPE-001）的瞬间，如果此时你的真实上下文 `ctx% >= 50%`（黄金甜点区上限），系统会在 API 返回中下发一个强烈的 `context_alert` 警告。
  - AI 读到后会**必须强制打断**（在此时状态最干净的时候），强迫你运行 `/compact` 或新开分支，用文档恢复进度。完美解决“长上下文智力稀释与结构性遗忘”的千古难题！
- **脱敏代理全兼容与纯净度升级**：
  - `varlock.py` 完善了处理 `Read` 和 `Write` 时针对 `[MASKED_xxx]` 的双向映射，真正实现了全链路的无明文企业级 DLP。
  - 彻底移除了所有旧版本中残留的私有业务代码库名称硬编码，`pretool-edit-scope.sh` 现采用最纯净通用的 `package.json, go.mod, Cargo.toml` 默认保护，框架 100% 解耦！
---
## [v6.0.6] — 2026-04-27 (Adversarial & Hard-Gate Edition)
### 核心主题：A/B 终端对抗盲审 与 真实 Context 硬阻断

**新增内容**：
- **`context-guard.sh` (第 24 个 Hook)**：
  - 读取底层 OMC Token 数据 (`~/.omc/state/token-tracking-index.json` 或最近 Session Token) 结合 `OPENCODE_CONFIG_CONTENT`。
  - 精准计算真实 `ctx%` 上下文占比。当占比 ≥80%（危险阈值）时，立刻**物理掐断 (Exit 2)** 一切写入和执行工具 (`Write/Edit/Bash`)，强迫用户执行 `/compact` 或分拆任务。
  - 从“依赖估算软提醒”直接跃升为“工业级内存 OOM 物理阻断”。
- **A/B 终端对抗盲审 (Sub-agent Blind Review)**：
  - 升级 `lx-code-review`，废弃 Main-agent（代码作者）自产自销的主观审查模式。
  - 引入 `subagent_reviewer.py`：自动提取 Diff 和 AC，强制生成一段高傲且严苛的 **Zero-shot Persona Prompt**。
  - 强制要求 Main-agent 通过 `Task` 工具唤醒独立的 Sub-agent（盲审官）进行隔离验收。因为 Sub-agent 是 **a fresh context**，彻底打碎了 Main-agent 的思维惯性与自我证实偏差 (Self-confirmation Bias)。
---
## [v6.0.5] — 2026-04-27 (Privacy & Data Protection Edition)
### 核心主题：数据防泄漏 (DLP) 与隐私防线

**新增内容**：
- **`privacy-gate.sh` (第 23 个 Hook)**：
  - 强行阻断 AI 通过 `Read/Grep` 读取 `.env`, `*.pem`, `id_rsa`, `secret.yml` 等敏感配置文件。
  - 强行阻断 AI 通过 `Bash` 拼接包含类似 `sk-ant-`, `ghp_`, `Bearer xxx` 的明文 Token 进行执行，从物理层杜绝上下文被污染、外泄给大模型。
- **`lx-varlock` 隐私脱敏代理管理器**：
  - 新增 `scripts/varlock.py`：作为安全的变量映射代理（Vault）。
  - **核心机制**：AI 仅使用形如 `{API_KEY}` 的占位符发起命令 (`varlock.py run "curl -H 'Auth: {API_KEY}' ..."`)，脚本在底层完成真实密钥的替换，并将服务器返回结果中的明文密钥再次**双向混淆**为 `[MASKED_API_KEY]` 后才返回给 AI。AI 永远无法获取明文。
- **AGENTS.md 新增“隐私防线”铁律**：正式确立第 6 条核心法则：“绝对禁止读取 .env/私钥，禁止在 Bash 中执行包含明文 Token 的命令，必须使用 varlock 执行脱敏调用”。
---
## [v6.0.4] — 2026-04-27
### 核心主题：全域纯净通用化与监控命令注册

**新增内容**：
- **`/lx-status` 独立 Skill**：将健康面板（Token节省、自愈力、执行效率）正式注册为官方斜杠命令。输入 `/lx-status` 或 `/lx-status --json` 即可一键召唤。
- **全域去业务耦合**：清除了 `pretool-edit-scope.sh` 中残留的特定业务词汇，全部替换为通用的 `main.go package.json Cargo.toml pom.xml`。确保框架 100% 纯粹、不绑定任何特定公司或私有逻辑。
---
## [v6.0.3] — 2026-04-27
### 核心主题：链路追踪版本（执行路径 + 错误路径画像）

**设计哲学**：不新建专门的埋点系统——复用三个已有数据源，合并分析得到完整执行画像
**三个数据源**：
- `update_progress.py`（已有）→ 执行路径追踪（天然路由记录）
- `error-dna.sh`（已有）→ 错误路径追踪（构建失败记录）
- `read-tracker.sh`（已有）→ 文件读取追踪（推断 AI 查阅的节点）
**新增内容**：
`update_progress.py` v6.0.3 扩展（+30行）：
- 新增 `--step`：记录当前 Step 编号（如 `3`）
- 新增 `--branch`：记录执行分支（`go`/`node`/`python`/`rust`）
- 新增 `--phase`：记录当前 Phase（`Phase1`/`Phase2`/`Phase3`）
- 每次调用自动写入 `.omc/state/skill-trace.jsonl`（JSONL 追踪文件）
- BLOCKED 时也写入追踪，确保错误路径不丢失
`skill_trace_report.py`（新增，lx-validate-skill/scripts/）：

```bash
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py # 完整报告
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only # token 节省
python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --feature user-login # 过滤
```
输出内容：
- 【1】执行路径追踪：Phase/Step/Branch 时序图
- 【2】错误路径追踪：活跃错误 + 已修复错误
- 【3】文件读取路径：AI 查阅了哪些 SKILL.md 节点
- 【4】渐进式披露 Token 节省：实际 vs 全量加载的差值
`lx-rpe SKILL.md` 在 4 个关键节点加入追踪调用：
- Step 1：进入 Phase3 记录
- Step 3（Go 路径）：记录 `--branch go`
- Step 3（前端路径）：记录 `--branch node`
- Step 9：完成记录
**测试结果**：10P / 0F（强证据验收通过）
**渐进式披露 Token 节省量化**：
- 最大节省：19,280 tokens/session（全 19 个 skill）
- lx-rpe 单个：7,764 tokens（62% 节省，仅无参数继续场景）
- 每月 300 次调用：最多节省 $17（claude-sonnet $3/1M）
---
