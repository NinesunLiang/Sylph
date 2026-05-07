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
|`anti-patterns.md` | 14 条反模式（A牙膏输出/B范围/C错误/D记忆/E效率/F推理） | summary|
|`claude-next.md` | 项目专属教训积累 | summary|
|`CLAUDE.md` | 宪法宪法 + 6 条铁律 + 工作流原则 | 会话自动加载 |

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

## Hooks 速查（共 32 个）
| Hook | 触发 | 作用|
|------|------|------|
|`completion-gate` | PreToolUse:TaskUpdate | 无证据禁止标 completed|
|`permission-gate` | PreToolUse:Bash | git/rm/sudo 需申请理由|
|`pretool-edit-scope` | PreToolUse:Edit\|Write | 范围冻结（current-scope.txt）|
|`turn-counter` | UserPromptSubmit | 轮次计数 + 模糊指令检测|
|`auto-snapshot` | Stop / PostToolUse:Edit\|Write | 会话快照 + 交接备忘录|
|`error-dna` | PostToolUse\|PostToolUseFailure:Bash | 错误模式积累|
|`inject-project-knowledge` | SessionStart | 注入本文件 + 知识上下文|
|`pretool-user-correction` | UserPromptSubmit | 纠正信号 → 提示写 claude-next.md|
|`context-guard` | PreToolUse:.* | Token 监控 + 50%/80% 熔断（全工具）|
|`privacy-gate` | PreToolUse:Read/Grep/Bash | 密钥文件拦截 + 明文脱敏|
|`build-validator` | PostToolUse\|PostToolUseFailure:Bash | 编译验证 + 错误追踪|
|`bash-audit` | PostToolUse\|PostToolUseFailure:Bash | 命令审计日志|
|`edit-guard` | PreToolUse:Edit | 文件写入范围保护|
|`edit-quality` | PostToolUse:Edit\|Write | 编辑质量分析|
|`read-tracker` | PostToolUse:Read | 读取追踪|
|`skill-flywheel` | Stop | 技能飞轮数据收集|
|`lsp-suggest` | PreToolUse:Grep | LSP 智能提示|
|`subagent-guard` | PreToolUse:Task | Sub-agent 用量审计|
|`flywheel-report` | SessionStart | 飞轮报告生成|
|`rule-anchor` | PreToolUse:Edit\|Write | 写前铁律锚定|
|`write-cite` | PostToolUse:Write\|Edit | 写入引用验证|
|`write-lock` (pre) | PreToolUse:Edit\|Write | 并发写入锁|
|`write-lock` (post) | PostToolUse:Edit\|Write | 并发写入解锁|
|`stop-drain` | Stop | 兜底扫 transcript 补录失败事件|
|`compact-detect` | UserPromptSubmit | 检测 /compact 命令保存 usage 快照|
|`posttool-subagent-audit` | PostToolUse:Task | Sub-agent 用量落盘 + flywheel P0|
|`pretool-write-lock` | PreToolUse:Edit\|Write | OMA 并发锁前置拦截|
|`token_writer` | PostToolUse:.* / SessionStart | Token 用量追踪 + 重置|

### 磁盘保留但未注册的脚本（共 4 个）

以下脚本存在于磁盘（计入 32 总数）但未在 settings.json 注册，发版前如需激活请自行添加注册：

| 脚本 | 原事件 | 说明 |
|------|--------|------|
| plan-gate.sh | PreToolUse:Write | 计划文档门禁 — Enhanced 专属，Base 版本暂不启用 |
| proactive-handoff.sh | PostToolUse | 上下文>50%主动交接 — R23 移除反向漂移 |
| feature-probe.sh | — | 独立工具脚本（非 Hook），L1-L4 证据验证 |
| posttool-read-cite.sh | PostToolUse:Read | 读取后引用标注 — R23 僵尸，待 Enhanced 再激活 |

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

