# OC Plugin @carroros/gov — 对齐记录 & TODO

> 更新: 2026-06-07
> 目的: 记录 @carroros/gov (OpenCode plugin) 与 CC 侧 73 个 hook .py 的对齐状态

## 1. 当前状态总览

| 状态 | 计数 | 说明 |
|------|------|------|
| ✅ 已对齐 | 5 hooks | index.ts 中已注册 |
| 🟡 可对齐 | ~15+ events | OC 有对应 hook 事件但没有 plugin handler |
| ⬜ 不对齐 | ~53 | CC 特有的 hook（OC 无对应事件机制） |

## 2. 已对齐 (5/5)

| OC Event | Plugin 文件 | 对应 CC Hook(s) | 覆盖度 |
|----------|------------|----------------|--------|
| `chat.system.transform` | `system.ts` | AGENTS.compact.md inject | ✅ 完全 |
| `tool.execute.before` | composite: `privacy.ts` + `oracle.ts` | privacy-gate.py + pretool-oracle-gate.py | ✅ 完全 |
| `tool.execute.after` | `oracle-post.ts` | meta-oracle-trigger.py + posttool-anti-pattern-detect.py | ✅ 完全 |
| `permission.ask` | `permission.ts` | permission-gate.py | ⚠️ 未实现 CAPTCHA 回退 |
| `experimental.session.compacting` | `compact.ts` | handoff.py (session-handoff-v2.json) | ✅ 完全 |

## 3. OC 有事件但未对齐的 CC Hook

OC 的 Plugin/Hooks 系统支持 20+ 事件，以下事件在 CC 侧有对应 hook，但 plugin 尚未注册 handler：

### 3.1 tool.execute.before 补充钩子

CC 侧 **所有** PreToolUse hook 都在 `tool.execute.before` 下被 composite handler 处理。但 composite 只实现了 privacy + oracle 两个，以下是遗漏的：

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `pretool-edit-scope.py` | 范围冻结 | **P1** | 每次 edit 前校验 scope |
| `pretool-terminal-safety.py` | 终端安全命令拦截 | **P1** | 高危命令阻止 |
| `pretool-git-gate.py` | Git 操作前检查 | **P1** | 确保 git 门禁 |
| `pretool-blast-radius.py` | 爆炸半径计算 | P2 | 决策辅助 |
| `pretool-retry-check.py` | 三次修复上限 | P2 | 循环防止 |
| `pretool-sensitive-edit.py` | 敏感编辑预警 | P2 | 提醒而非阻断 |
| `pretool-plan-gate.py` | 规划门禁 | P2 | 强制规划 |
| `pretool-sensitive-file-guard.py` | 敏感文件保护 | P2 | 与 privacy 有重叠 |
| `pretool-b1-detect.py` | B1 反模式检测 | P3 | 可延迟 |
| `pretool-purify-gate.py` | 纯度门禁 | P3 | 仅在 CarrorOS 项目有用 |
| `pretool-skill-version-guard.py` | Skill 版本校验 | P3 | 可延迟 |
| `edit-guard.py` | 编辑守卫 | P3 | 范围检测 |
| `pre-edit-lsp-check.py` | LSP 语法检查 | P3 | |
| `context-guard.py` | 上下文守卫 | P2 | 上下文安全 |
| `pretool-write-lock.py` | 写锁 | P2 | 防止并发写 |
| `pretool-scope-gate.py` | 范围门禁 | P3 | 与 edit-scope 重叠 |
| `pretool-workflow-gate.py` | 工作流门禁 | P3 | 仅 CarrorOS |
| `pretool-python-bridge.py` | Python 桥接 | P3 | CC-specific |

### 3.2 tool.execute.after 补充

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `posttool-bash-audit.py` | Bash 安全审计 | **P1** | 高危 Bash 操作审计 |
| `posttool-claim-audit.py` | 断言真实审计 | **P1** | 防止编造 |
| `completion-gate.py` | 完成门禁 | **P1** | 防软完成语 |
| `posttool-edit-quality.py` | 编辑质量 | P2 | |
| `posttool-handoff-writer.py` | 会话交接写入 | P2 | 与 compact 相关 |
| `posttool-checkpoint.py` | 检查点 | P2 | |
| `error-dna.py` | 错误记录 | P2 | |
| `posttool-anti-pattern-detect.py` | 反模式检测 | P2 | 已部分覆盖 |
| `posttool-write-lock.py` | 写锁释放 | P3 | |

### 3.3 SessionStart

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `context-compressor.py` | 上下文压缩 | **P1** | |
| `oracle-gate.py` | Oracle 初始化 | **P1** | |
| `knowledge-condenser.py` | 知识蒸馏 | P2 | |
| `inject-project-knowledge.py` | 项目知识注入 | P2 | 与 system.transform 重叠 |
| `session-resume.py` | 会话恢复 | P2 | 与 compact 相关 |
| `ecosystem-probe.py` | 环境探测 | P3 | |

### 3.4 Stop

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `stop-drain.py` | 停止排空 | P2 | |
| `skill-flywheel.py` | Flywheel 关闭 | P3 | |
| `posttool-checkpoint.py` | 最后检查点 | P2 | |

### 3.5 UserPromptSubmit

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `pretool-approve-detect.py` | 批准检测 | **P1** | 对话内 /approve |
| `pretool-user-correction.py` | 用户纠正 | P2 | |
| `turn-counter.py` | 轮次计数 | P2 | |
| `thinking-gate.py` | Thinking 过滤 | P2 | |
| `pretool-rules-inject.py` | 规则注入 | P3 | |

### 3.6 PostToolUseFailure

| CC Hook | 功能 | 优先级 | 备注 |
|---------|------|--------|------|
| `error-dna.py` | 错误 DNA 记录 | P2 | |
| `posttool-bash-audit.py` | Bash 失败审计 | P2 | |

## 4. OC 无对应事件的 CC Hook (CarrorOS 特有)

以下 hook 是 Claude Code 特有的 hook 事件接口（如 `TaskUpdate`、`Skill`、`Task`、`UserPromptSubmit` 的 stdin JSON schema），OC 无等价事件：

| 事件 | Hook 数 | 说明 |
|------|---------|------|
| TaskUpdate | 9 | OC 无 `afterTaskUpdate` 等价 |
| Bash | ~7 | PostToolUse/Bash matcher |
| Skill | 2 | OC skill 机制不同 |
| Task / Agent | 2 | OC 使用 plugin 而非 agent |
| PostToolUseFailure | 3 | OC 无 `onToolError` 等价 |
| Read | 2 | OC 无 read 后事件 |
| Stop | 3 | OC 无 onStop 等价 |

这些 **不对齐**，保持 CC 原生。

## 5. 执行 TODO

### Phase 1: P1 紧急 (当前 sprint)

| # | 任务 | 工作量 | 依赖 |
|---|------|--------|------|
| 1 | `pretool-edit-scope.py` → `tool.execute.before` | 中 | 需了解 OC scope 模型 |
| 2 | `pretool-terminal-safety.py` → `tool.execute.before` | 小 | 高危命令列表已定义 |
| 3 | `pretool-git-gate.py` → `tool.execute.before` | 小 | git 操作拦截 |
| 4 | `posttool-bash-audit.py` → `tool.execute.after` | 中 | Bash 审计逻辑迁移 |
| 5 | `posttool-claim-audit.py` → `tool.execute.after` | 中 | 断言验证迁移 |
| 6 | `completion-gate.py` → `tool.execute.after` | 中 | 完成检测迁移 |
| 7 | `context-compressor.py` → `chat.system.transform` 增强 | 小 | 复用 system.ts |
| 8 | `pretool-approve-detect.py` → `permission.ask` 增强 | 小 | 对话内批准 |
| 9 | `oracle-gate.py` → `experimental.session.start` | 中 | 需确认 OC 有 session.start |

### Phase 2: P2 常规

| # | 任务 | 工作量 |
|---|------|--------|
| 10 | `posttool-edit-quality.py` → `tool.execute.after` | 中 |
| 11 | `posttool-handoff-writer.py` → 增强 compact hook | 小 |
| 12 | `error-dna.py` → `tool.execute.after` + failure | 中 |
| 13 | `pretool-retry-check.py` → `tool.execute.before` | 小 |
| 14 | `pretool-blast-radius.py` → `tool.execute.before` | 小 |
| 15 | `knowledge-condenser.py` → `chat.system.transform` 增强 | 中 |
| 16 | `session-resume.py` → `experimental.session.start` | 中 |
| 17 | `pretool-sensitive-edit.py` → `tool.execute.before` | 小 |
| 18 | `inject-project-knowledge.py` → `chat.system.transform` 增强 | 小 |

### Phase 3: P3 延迟

19-25: 剩余 P3 hook（pretool-plan-gate / pretool-purify-gate / context-guard / 等）
这些大部分与已对齐功能重叠或仅 CC 环境有用，等 Phase 1-2 完成后评估是否有必要。

## 6. 架构决策记录

1. **tool.execute.before 用 composite handler**: OC 只允许一个 handler per event → CC 侧 16 个 PreToolUse hook 必须合并到一个 composite 中。当前用 2-phase（privacy → oracle），可以扩展为 3-phase（+ scope/git/terminal）
2. **event 覆盖不追求 1:1**: 73 个 CC hook 对应 OC 仅 20+ 事件，some CC hooks 可合并实现（如多个 pretool-* → 一个 composite handler 的不同 phase）
3. **TaskUpdate 无法映射**: OC 无 TaskUpdate 等价事件 → 相关 9 个 CC hook 保持 CC 原生
4. **`.ts` 直接编译**: @carroros/gov 用 raw TypeScript，无 bundler，`tsconfig.json` 的 `outDir` 已配置
