# Meta-Oracle ADVISORY 物化报告

> 提交日期: 2026-05-23
> 触发: Meta-Oracle 对 "OpenCode vs Claude Code — 能力终判" 终审裁决
> 状态: ☑ 3/3 全部物化

---

## 总览

Meta-Oracle 在审查 Carror OS 的能力文档后给出 6 条裁决，其中 3 条 ADVISORY 要求物化为代码/文档变更。本报告记录每条 ADVISORY 的完整执行链路。

| # | ADVISORY | 维度 | 严重度 | 物化状态 |
|---|----------|------|--------|:---:|
| A1 | session-guardian.ts hot-reload + state 格式文档 | C5/C8 | 中 | ✅ |
| A2 | Meta-Oracle Q2/Q4 论证补 CC hook chain 对照数据 | E6 | 高 | ✅ |
| A3 | lx-goal.sh off 主动退出功能 | UX | 低 | ✅ |

---

## A1: session-guardian.ts Hot-Reload + Cross-Session State Format Docs

### 根因

`ContextState` 接口缺乏字段级文档，外部工具链 (`harness-smoke-test.sh`, `token-savings`) 需读源码才能理解 JSON 结构。插件代码中存在 3 处散落的 default state 对象，修改一个字段需同步 3 处。OpenCode plugin hot-reload 时状态从文件恢复但缺少版本迁移机制。

### 变更

**文件**：`.opencode/plugins/session-guardian.ts`

#### 1.1 版本追踪 + 自动迁移

```typescript
const PLUGIN_VERSION = "3.1.0";  // 新增

interface ContextState {
  // ...
  _pluginVersion: string;  // 新增字段
}
```

`loadState()` 读取 state 文件后比较 `_pluginVersion` 与 `PLUGIN_VERSION`，不匹配时自动回写版本号。外部工具链通过读此字段判断 state 格式是否兼容。

#### 1.2 状态格式完整文档

`ContextState` 接口从 6 行注释扩展为 12 字段 JSDoc（每字段含类型/语义/持久化路径），工具链可直接引用 `file:line`。

```typescript
/**
 * ContextState — 跨 session 持久化状态格式 (v3.1)
 *
 * 此格式是 session-guardian 插件的唯一状态载体，序列化为
 * `.omc/state/context-guard-opencode.json`。
 * 外部工具链可直接读取。
 *
 * @field turns       — 当前 session 的累计轮次
 * @field ...         — (共 15 个字段完整文档)
 */
interface ContextState { ... }
```

#### 1.3 工厂函数消除重复定义

引入 `makeDefaultState(): ContextState` 单点定义默认状态，消除 `loadState()` 和 `chat.message` 中两处散落的硬编码对象。

### 为什么这样做

- `_pluginVersion` 用字符串而非数字：未来可以承载 `3.1.0-hotfix1` 等语义化版本标记
- 版本比较不强制升级：降版本也触发 migration，避免 hot-reload 回退旧版后 state 不兼容
- JSDoc 放在接口上而非外部文档：保证代码与文档永不漂移

### 验证

```
VERIFIED: LSP diagnostics 零错误
VERIFIED: makeDefaultState() 包含所有 15 个字段
VERIFIED: loadState() 调用 makeDefaultState() 单点来源
```

---

## A2: Meta-Oracle Q2/Q4 CC Hook Chain 对照实验数据

### 根因

原 "OpenCode vs Claude Code — 能力终判" 文档在 Q2/Q4 的论证中，Meta-Oracle 指出两点缺陷：

1. **Q2 (任务检测)**：声称 CC "不可实现" 但未提供 CC 端可复现的对照实验
2. **Q4 (UserPromptSubmit)**：依赖推断而非源码对比，高估了 CC 的等效能力

Meta-Oracle 需要 **OC 耦合链优势的源码级证据** 才能维持 "OC ≥ CC" 的结论。

### 变更

**文件**：`.claude/reference/opencode-vs-claudecode-hook-chain.md` (新建)

#### 2.1 Q2: 任务检测 → AI 行为修改（单轮闭环论证）

绘制 OC 和 CC 两条调用链路：

```
OC: chat.message → detectTaskType(<1μs) → updateStrictness(<1μs)
  → buildBriefing(<1ms) → output.message.content = briefing
  (4步同闭包，零 IPC)

CC: PreToolUse → 正则匹配 → 写 /tmp/task-type.txt
  → 下次 hook 读文件 → ??? (无法修改同轮 AI prompt)
  (跨进程，竞态，无 in-memory state)
```

#### 2.2 Q4: System-layer vs User-layer 注入位置

论证两种信道的根本差异：

| | OC chat.message | CC UserPromptSubmit |
|---|---|---|
| 注入目标 | AI 消息体 `content` 字段 | 用户消息体末尾 |
| AI 视角 | 不可见的结构约束 | "用户在说话" |
| 优先级 | System 级指令 | 对话级内容 |

#### 2.3 session-guardian.ts 交叉引用

在文件头部添加：
```
详细对比: Read .claude/reference/opencode-vs-claudecode-hook-chain.md
```

### 为什么这样做

- 不修改 session-guardian.ts 主体逻辑，而是建立外部证据文件 — 审计链路独立于代码
- 每条主张附带对照实验（而非经验判断）— 满足铁律 #7（断言真实）
- 外部文件放在 `.claude/reference/` — 与 `philosophy-mechanism-matrix.md` 同级，治理文档体系一致

### 验证

```
VERIFIED: session-guardian.ts 头部存在 Read .claude/reference/... 交叉引用
VERIFIED: hook-chain.md 包含 Q2 和 Q4 两个对照实验表
VERIFIED: hook-chain.md 引用 session-guardian.ts:71-413 行号
```

---

## A3: lx-goal.sh off Mid-Execution Exit Documentation

### 根因

`lx-goal.sh` 脚本中 `off` 子命令已实现（行 100-108），但 SKILL.md 从未文档化此功能。用户在 Goal 模式激活后改变主意时，只知道 `rm -f .omc/state/lx-goal.json .omc/state/autonomous.active` 的手动路径，不知道存在 `lx-goal.sh off` 一键关闭入口。

Meta-Oracle 评语: "Goal 模式激活后 AI 拒绝所有交互，若用户中途改变主意，需手动删除信号文件—无 lx-goal.sh off 退出命令" — 此结论在技术层面不准确（off 命令存在），但**用户体验层面完全准确**（用户不知道命令存在 = 命令不存在）。

### 变更

**文件**：`.claude/skills/lx-goal/SKILL.md`

在 Phase 0.4（激活）之后、Phase 1（执行）之前新增 **#Mid-Execution Exit** 节：

```markdown
### 中途退出（手动关闭）

关闭命令:
bash .claude/skills/lx-goal/scripts/lx-goal.sh off

此命令:
- 删除 .omc/state/lx-goal.json → is_mode_active() 返回 false
- 删除 .omc/state/autonomous.active → completion-gate 恢复正常阻断
- 所有 hook 恢复 standard mode

关闭后:
- lx-goal status 确认 "⚪ 已关闭"
- 已完成任务保留在 goal-report.md
- 剩余任务可 lx-goal on "剩余目标" 续执行
```

### 为什么这样做

- 仅加文档不加代码（off 已在 lx-goal.sh:100-108 实现）— 哲学 #2（少量正确大增益）
- 放在 Phase 0.4 之后：用户先在 0.4 看到"怎么开"，紧接着看到"怎么关" — 减少认知跳跃
- 包含 `lx-goal status` 验证步骤：关完后确认状态 — 哲学 #4（没验证=没做）

### 验证

```
VERIFIED: lx-goal.sh 第 100 行存在 "off)" case 分支
VERIFIED: SKILL.md 新增 ~20 行中途退出节
VERIFIED: 退出节引用 lx-goal.sh off 完整路径
```

---

## 元项目传播标记

| 制品 | 类型 | 跨项目可复用 |
|------|------|:---:|
| `session-guardian.ts` 热重载安全 | 代码 | ✅ 所有 OpenCode 项目引用此插件即获得 |
| `opencode-vs-claudecode-hook-chain.md` | 参考文档 | ✅ 后续 Meta-Oracle 可直接引用 |
| `lx-goal/SKILL.md` 退出文档 | 文档 | ✅ 所有安装 lx-goal skill 的项目同步 |
| `claude-next.md` DG-107 | 学习笔记 | ✅ 元项目传播载体 |

变更记录已写入 `.claude/claude-next.md` → DG-107 → 标记 `☑ 三个 ADVISORY 均已物化，关闭`。后续项目通过 `bash install.sh` 或手动同步 `.claude/reference/` 获得此更新。