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
|8 | **反自我矛盾** | 新机制引入时必须检查：(a) 非 AI 可调用批准通道 (b) 域规则正确适用 (c) 新 hook 注册完整性。见 claude-next.md R42/R43 | 机制审计失败时回滚|
**置信度标注格式（每个技术断言必须附带）：**- `[已验证: file:line]` — 从源码直接确认- `[已测试: 命令+输出]` — 运行验证通过- `[推断, 待确认]` — 基于上下文推理，未直接验证

**反自我矛盾（新增自检工具）：** `bash .claude/scripts/pre-commit-self-review.sh [commit-msg]` — 提交前检查 (a) CAPTCHA 绕过 (b) 域规则误用 (c) 新 hook 注册完整性。见 claude-next.md R42/R43。exit 2 = 阻断，exit 0 = 通过。

---

## 治理规则
| 文件 | 内容 | 注入方式|
|------|------|---------|
|`kernel.md` | 代码执行内核（命名/错误处理/测试要求） | full|
|`anti-patterns.md` | 16 条反模式（A输出/B范围/C错误/D记忆/E效率/F推理/G报告/H语义） | summary|
|`claude-next.md` | 项目专属教训积累 | summary|
|`CLAUDE.md` | 宪法 + 8 条铁律 + 工作流原则 | 会话自动加载 |

## 记忆系统
| 路径 | 内容 | 写入时机|
|------|------|---------|
|`.omc/state/session-handoff.md` | 上次会话交接（进行中/阻塞/决策/踩坑） | Stop hook|
|`.omc/state/session-snapshot.json` | 会话快照（分支/轮次/未提交文件） | Stop hook|
|`.omc/state/error-dna.json` | 错误模式库（签名/次数/修复上下文） | PostToolUse:Bash|
|`.omc/state/todo-queue.md` | 当前 Todo 队列（FIFO，max 15） | 手动更新|
|`.omc/state/dogfood/` | 狗粮记录（结构化 YAML + 故事） | 每次狗粮处理后|
|`\~/.claude/flywheel.log` | 全局工作习惯日志 | Stop hook flush |

## 飞轮故事

> 一次真实的狗粮反哺 Carror OS 自身的完整记录。
> 客户项目 → Oracle 审查 → 教训分拣 → lx-oma-hier v1.2.0→v1.3.0 → claude-next.md +10 条教训

- [📖 飞轮初转（中文）](../docs/dogfooding/cn/flywheel-first-turn.md)
- [📖 The First Turn of the Flywheel (English)](../docs/dogfooding/us/flywheel-first-turn.md)

## 当前状态快速查看

```bash
# 查看上次会话交接cat .omc/state/session-handoff.md
# 查看未完成 Todocat .omc/state/todo-queue.md
# 查看错误记忆cat .omc/state/error-dna.json | python3 -c \ "import json,sys; [print(e['signature'][:60],'×',e['count']) \ for e in json.load(sys.stdin) if e.get('status')!='fixed']"
```

## Hooks 速查（共 45 个活跃）

详见 `.claude/reference/hooks-table.md`（Read 查看）。

