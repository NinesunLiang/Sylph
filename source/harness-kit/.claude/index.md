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
|2 | **用户裁定** | 验收/选型/冲突由用户决定，AI 不可自判 | 等待指令|
|3 | **证据门禁** | 说"完成/已验证"前必须提供 L1/L2 证据（`VERIFIED: ...`） | 重新验证，不得声明完成|
|4 | **Git 门禁** | 任何 git write 操作（commit/push）必须先报告，等用户明确批准 | 立即回滚|
|5 | **范围冻结** | 只改当前任务涉及的文件，额外发现的问题记 TODO，不顺手修 | 撤销越界改动|
|6 | **隐私防线** | 绝对禁止读取 .env/私钥，禁止在 Bash 敲明文 Token | 强阻断 |
|7 | **断言真实** | 每个百分比/评分必须有行业标准来源 URL 或 file:line，否则标注 `[内部自检]` | 撤销不实断言，重写报告|
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

## 执行模式（Ghost / 无人值守）

| 模式 | 驱动 | 默认过期 | 适用场景 | 命令 |
|------|------|---------|---------|------|
| **Ghost** | 方向驱动，自由探索 | 3h | 代码体检/审计/巡检/架构漂移检测 | `ghost-mode.sh` |
| **无人值守** | 目标驱动，执行到底 | 6h | 批量重构/功能开发/Bug 修复清单 | `lx-unattended-toggle.sh` |

**Ghost Mode**：`ghost-mode on "方向" [间隔秒] [过期小时]` — AI 按方向自动探索和修复，每 N 秒轮询。所有门禁降级为"记录+跳过"。不会干扰用户。

**无人值守模式**：`lx-unattended on "目标" [过期小时]` — AI 执行指定目标直到完成。`task-done` 标记进度，`report` 输出最终报告。所有门禁降级。

**驱动方式**：手动执行或 `/loop <间隔> ghost-mode.sh poll` 自动轮询。

## Hooks 速查

> 完整 34 个 hooks 列表见 `.claude/reference/hooks-table.md`（Read 按需查看）

默认禁用 3 个：`plan-gate` / `posttool-read-cite` / `proactive-handoff`
独立工具：`feature-probe.sh`（L1-L4 证据验证）

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

