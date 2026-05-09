# 项目知识导航

> >
> harness-kit 会话知识地图 — SessionStart 时首先注入，帮助 AI 快速定位所有资源
> 本文件由 harness-kit 安装时生成，可按项目实际情况补充

---

## ⚡ 铁律速查（ALWAYS ACTIVE · 每轮均有效）
> 无论对话进行到第几轮，以下规则始终生效。违反即停止当前操作。
| # | 铁律 | 行动要求 | 违反后果|
|---|------|---------|---------|
|1 | **禁止编造** | 每个技术断言必须有 `file:line` 来源，找不到则说"需要验证" | BLOCKED，回滚重做|
|2 | **证据门禁** | 说"完成/已验证"前必须提供 L1/L2 证据（`VERIFIED: ...`） | 重新验证，不得声明完成|
|3 | **Git 门禁** | 任何 git write 操作（commit/push）必须先报告，等用户明确批准 | 立即回滚|
|4 | **范围冻结** | 只改当前任务涉及的文件，额外发现的问题记 TODO，不顺手修 | 撤销越界改动|
|5 | **修复上限** | 同一问题最多修 3 轮，第 3 轮失败 → BLOCKED，向用户汇报 | 停止重试，等待指令|
|6 | **禁用词** | 禁止用"应该是/可能/通常"作为技术断言，必须标注置信度 | 重新表述|
|7 | **隐私防线** | 绝对禁止读取 .env/私钥，禁止在 Bash 敲明文 Token | 强阻断 |
**置信度标注格式（每个技术断言必须附带）：**- `[已验证: file:line]` — 从源码直接确认- `[已测试: 命令+输出]` — 运行验证通过- `[推断, 待确认]` — 基于上下文推理，未直接验证

---

## 治理规则
| 文件 | 内容 | 注入方式|
|------|------|---------|
|`kernel.md` | 代码执行内核（命名/错误处理/测试要求） | full|
|`anti-patterns.md` | 16 条反模式（A输出/B范围/C错误/D记忆/E效率/F推理/G报告/H语义） | summary|
|`claude-next.md` | 项目专属教训积累 | summary|
|`CLAUDE.md` | 宪法 + 7 条铁律 + 工作流原则 | 会话自动加载 |

## 记忆系统
| 路径 | 内容 | 写入时机|
|------|------|---------|
|`.omc/state/session-handoff.md` | 上次会话交接（进行中/阻塞/决策/踩坑） | Stop hook|
|`.omc/state/session-snapshot.json` | 会话快照（分支/轮次/未提交文件） | Stop hook|
|`.omc/state/error-dna.json` | 错误模式库（签名/次数/修复上下文） | PostToolUse:Bash|
|`.omc/state/todo-queue.md` | 当前 Todo 队列（FIFO，max 15） | 手动更新|
|`\~/.claude/flywheel.log` | 全局工作习惯日志 | Stop hook flush |

## 当前状态快速查看

```bash
# 查看上次会话交接cat .omc/state/session-handoff.md
# 查看未完成 Todocat .omc/state/todo-queue.md
# 查看错误记忆cat .omc/state/error-dna.json | python3 -c \ "import json,sys; [print(e['signature'][:60],'×',e['count']) \ for e in json.load(sys.stdin) if e.get('status')!='fixed']"
```

## Hooks 速查（共 26 个）
| Hook | 触发 | 作用|
|------|------|------|
|`auto-snapshot` | PostToolUse / Stop | auto-snapshot.sh — Stop Hook|
|`build-validator` | PostToolUse / PostToolUseFailure | build-validator.sh — PostToolUse:Bash 构建失败自动记录 + 修复建议|
|`compact-detect` | UserPromptSubmit | compact-detect.sh — UserPromptSubmit Hook|
|`completion-gate` | PostToolUse | completion-gate.sh — PreToolUse:TaskUpdate Hook|
|`context-guard` | PreToolUse | context-guard.sh — PreToolUse:.* Hook (R26: 全工具走阈值, see claude-next.md)|
|`edit-guard` | PreToolUse | edit-guard.sh — PreToolUse:Edit Hook|
|`error-dna` | PostToolUse / PostToolUseFailure | PostToolUse hook: Capture structured error DNA for cross-session error memory|
|`flywheel-report` | SessionStart | flywheel-report.sh — SessionStart Hook (RPE-017 enhanced)|
|`inject-project-knowledge` | SessionStart | 项目级 SessionStart hook：注入 .claude/ 核心知识到 AI context|
|`lsp-suggest` | PreToolUse | lsp-suggest.sh — PreToolUse:Grep Hook|
|`permission-gate` | PreToolUse | permission-gate.sh — PreToolUse:Bash Hook|
|`posttool-bash-audit` | PostToolUse / PostToolUseFailure | PostToolUse:Bash 权限上下文审计 - 只提醒不阻断|
|`posttool-edit-quality` | PostToolUse | PostToolUse:Edit 代码风格自查 + 文档同步提醒 + 方案复用检测|
|`posttool-subagent-audit` | PostToolUse | posttool-subagent-audit.sh — PostToolUse:Task Hook|
|`posttool-write-cite` | PostToolUse | posttool-write-cite.sh — PostToolUse:Write Hook|
|`posttool-write-lock` | PostToolUse | write-lock-release.sh (PostToolUse) — Carror OS OMA 并发锁释放|
|`pretool-edit-scope` | PreToolUse | PreToolUse:Edit — 范围冻结拦截 + 核心文件警告 + 耦合提醒|
|`pretool-rule-anchor` | PreToolUse | pretool-rule-anchor.sh — PreToolUse:Write Hook|
|`pretool-user-correction` | UserPromptSubmit | pretool-user-correction.sh — UserPromptSubmit Hook|
|`pretool-write-lock` | PreToolUse | write-lock-gate.sh (PreToolUse) — Carror OS OMA 并发锁前置拦截|
|`privacy-gate` | PreToolUse | privacy-gate.sh — PreToolUse:Read / Grep / Bash Hook|
|`read-tracker` | PostToolUse | read-tracker.sh — PostToolUse:Read Hook|
|`skill-flywheel` | Stop | skill-flywheel.sh — Stop Hook|
|`stop-drain` | Stop | stop-drain.sh — Stop hook 兜底重放|
|`subagent-guard` | PreToolUse | subagent-guard.sh — PreToolUse:Task Hook|
|`turn-counter` | UserPromptSubmit | turn-counter.sh — UserPromptSubmit Hook|

### 已注册但默认禁用的脚本（共 3 个）

以下脚本已注册到 settings.json，但在 harness.yaml 中默认关闭，按需启用：

| 脚本 | 事件 | 说明 |
|------|------|------|
| plan-gate | PreToolUse | plan-gate.sh — PreToolUse:Edit Hook [DISABLED: harness.yaml 默认关闭] |
| posttool-read-cite | PostToolUse | PostToolUse:Read 来源标注提醒 - 读取文件后提示引用规范 [已注册，默认禁用] |
| proactive-handoff | PostToolUse | proactive-handoff.sh — PostToolUse Hook [INACTIVE: 未注册, 反向漂移] |

### 独立工具脚本（非 Hook）

| 脚本 | 说明 |
|------|------|
| feature-probe.sh | L1-L4 证据验证工具，手动调用 |

## Language Profile 选择

```bash
# Go 项目cp .claude/profiles/go/harness.yaml .claude/harness.yaml

# Node.js / TypeScript 项目cp .claude/profiles/node/harness.yaml .claude/harness.yaml

# Python 项目cp .claude/profiles/python/harness.yaml .claude/harness.yaml

# 恢复 generic（任意语言）# 重新安装即可
```

---
> >
> **第一次使用**：直接和 Claude Code 说出你要做的事，harness-kit 在后台保护你。
> **积累 2 周后**：AI 开始记住你的习惯和踩过的坑。
> **积累 3 个月后**：`.claude/` 成为你的数字分身，换项目 10 秒恢复。

