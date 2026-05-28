# 项目知识导航

> >
> harness-kit 会话知识地图 — SessionStart 时首先注入，帮助 AI 快速定位所有资源
> 本文件由 harness-kit 安装时生成，可按项目实际情况补充

---

## 🔧 维护操作（用户问及时 AI 引导）

| 操作 | 命令 | 说明 |
|------|------|------|
| **更新** | `bash install.sh` | 自动检测现有安装，无损热更新（保留配置/状态/自定义hook） |
| **强制更新** | `bash install.sh --yes` | 跳过确认，直接覆盖升级 |
| **跳过升级** | `bash install.sh --no-upgrade` | 仅安装新依赖，不覆盖现有配置 |
| **卸载** | `bash install.sh --uninstall` | 移除 Carror OS（可选保留 .omc/ 状态数据） |
| **回滚** | `bash .omc/backup-*/rollback.sh` | 恢复到升级前的版本 |
| **发版** | `bash scripts/release.sh <patch\|minor\|major> "release notes"` | 7 步发版流程 |
| **发版前检查** | `bash scripts/release-checklist.sh` | 纯检查清单 (质量门禁→源镜像→文档一致性) |

AI 引导原则：用户说"发版/release/发布"→ `bash scripts/release.sh patch "notes"`。

---

## 🔄 结构化执行协议

> 非 trivial 任务自动走 5 阶段: 调研→方案双审→执行→结果双审→验收报告
> 完整协议: `.claude/reference/structured-execution-protocol.md`

---

## ⚡ 铁律速查（ALWAYS ACTIVE · 每轮均有效）
> 无论对话进行到第几轮，以下规则始终生效。违反即停止当前操作。
> 权威源: `AGENTS.md §8 条铁律`

| # | 铁律 | 一句话 | 违反后果|
|---|------|--------|---------|
|1 | **禁止编造** | 每个技术断言必须有 `file:line` 来源，找不到则说"需要验证" | BLOCKED，回滚重做|
|2 | **用户裁定** | 验收/选型/冲突由用户决定，AI 不可自判 | 等待指令 |
|3 | **证据门禁** | 说"完成/已验证"前必须提供 L1/L2 证据（`VERIFIED: ...`） | 重新验证，不得声明完成|
|4 | **Git 门禁** | 任何 git write 操作（commit/push）必须先报告，等用户明确批准 | 立即回滚|
|5 | **范围冻结** | 只改当前任务涉及的文件，额外发现的问题记 TODO，不顺手修 | 撤销越界改动|
|6 | **隐私防线** | 绝对禁止读取 .env/私钥，禁止在 Bash 敲明文 Token | 强阻断 |
|7 | **断言真实** | 报告中每个百分比/评分必须有行业标准来源 URL 或 `file:line`，否则标注 `[内部自检]` | 撤销不实断言，重写报告 |
|8 | **哲学先行** | 问人前先过哲学7条：哲学能裁决→标注 `[哲学先行: #N→action]` 直接执行 | 无效打断，增加心智负担 |

**置信度标注格式（每个技术断言必须附带）：**
- `[已验证: file:line]` — 从源码直接确认
- `[已测试: 命令+输出]` — 运行验证通过
- `[推断, 待确认]` — 基于上下文推理，未直接验证

**补充规则**（已由 kernel.md / anti-patterns.md 物化，不重复列为铁律）：
- 修复上限（同一问题最多3轮）→ `kernel.md §最大修复上限`
- 禁用词（禁止"应该是/可能/通常"）→ `anti-patterns.md F1`
- 反自我矛盾（机制审计门禁）→ `bash .claude/scripts/pre-commit-self-review.sh [commit-msg]`

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

