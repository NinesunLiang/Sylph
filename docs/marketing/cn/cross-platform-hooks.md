# Sylph Harness — 跨平台 Hook 系统

> **一套治理，全域通行。**
> 一次定义安全策略与工作流守卫，自动适配 6 大主流 AI Coding CLI。

---

## 一句话

Sylph Harness 的 Hook 系统是 **AI Coding CLI 领域的通用治理层**。它在 Claude Code、Codex CLI、Gemini CLI、Qwen Code、Cursor、OpenCode 六平台之上定义了一套统一的执行事件模型，让安全守卫、质量门禁、知识注入和审计追踪不再受限于单一工具。

---

## 支持平台

| 平台 | 开发商 | 配置形式 | 覆盖 Hook |
|------|--------|---------|:---------:|
| **Claude Code** | Anthropic | `.claude/harness.yaml`（原生配置） | 29/29 |
| **Codex CLI** | OpenAI | `.codex/hooks.json`（自动生成） | 19/29 |
| **Gemini CLI** | Google | `.gemini/settings.json`（自动生成） | 17/29 |
| **Qwen Code** | 阿里巴巴 | `settings.json`（自动生成） | 19/29 |
| **Cursor** | Cursor Inc. | `.cursor/hooks.json`（自动生成） | 9/29 |
| **OpenCode** | 开源社区 | `.opencode/plugins/sylph-hooks.ts`（自动生成） | 13/29 |

---

## Hook × Platform 能力矩阵

```
  Hook                   Block  claude_code  codex        gemini       qwen         cursor       opencode    
  ---------------------- ------ ------------------------------------------------------------------------
  auto_snapshot          👁      ✅            ✅            ✅            ✅            ❌            ❌           
  bash_audit             👁      ✅            ✅            ✅            ✅            ✅            ✅           
  build_validator        👁      ✅            ✅            ✅            ✅            ❌            ❌           
  compact_detect         👁      ✅            ✅            ✅            ✅            ✅            ✅           
  completion_gate        ⛔      ✅            ✅            ✅            ✅            ❌            ✅           
  context_guard          👁      ✅            ✅            ✅            ✅            ❌            ❌           
  edit_guard             ⛔      ✅            ✅            ✅            ✅            ❌            ❌           
  edit_scope             ⛔      ✅            ✅            ✅            ✅            ❌            ✅           
  error_dna              👁      ✅            ✅            ✅            ✅            ❌            ❌           
  flywheel_report        👁      ✅            ✅            ✅            ✅            ❌            ✅           
  inject_knowledge       👁      ✅            ✅            ✅            ✅            ❌            ❌           
  permission_gate        ⛔      ✅            ✅            ✅            ✅            ✅            ✅           
  privacy_gate           ⛔      ✅            ✅            ✅            ✅            ❌            ✅           
  stop_drain             👁      ✅            ✅            ✅            ✅            ❌            ✅           
  token_writer           👁      ✅            ✅            ✅            ✅            ❌            ✅           
  turn_counter           👁      ✅            ✅            ✅            ✅            ✅            ✅           
  user_correction_detector 👁      ✅            ✅            ✅            ✅            ❌            ✅           
  write_lock_post        👁      ✅            ✅            ✅            ✅            ❌            ✅           
  write_lock_pre         ⛔      ✅            ✅            ✅            ✅            ❌            ✅           
  Claude Only (10)       —      ✅            ❌            ❌            ❌            ❌            ❌           
```

> ⛔ = 阻断型 hook（exit 2），👁 = 观察型 hook（不阻断）
> 矩阵通过 `python3 .hooks/generate.py list` 自动生成，与框架完全同步

## 平台事件覆盖明细

```
  claude_code          19 hooks, 9/9 events
  codex                19 hooks, 9/9 events
  gemini               17 hooks, 7/9 events — 缺失: session:start, compact:before
  qwen                 19 hooks, 9/9 events
  cursor               9 hooks, 6/9 events — 缺失: session:start, file:write, compact:before
  opencode             13 hooks, 9/9 events
```

## Event × Platform 事件覆盖矩阵

```
  Event                claude_code  codex        gemini       qwen         cursor       opencode
  -------------------- ------------------------------------------------------------------------
  session:start        ✅            ✅            ❌            ✅            ❌            ✅
  prompt:submit        ✅            ✅            ✅            ✅            ✅            ✅
  tool:before          ✅            ✅            ✅            ✅            ✅            ✅
  tool:after           ✅            ✅            ✅            ✅            ✅            ✅
  shell:before         ✅            ✅            ✅            ✅            ✅            ✅
  shell:after          ✅            ✅            ✅            ✅            ✅            ✅
  file:write           ✅            ✅            ✅            ✅            ❌            ✅
  compact:before       ✅            ✅            ❌            ✅            ❌            ✅
  stop                 ✅            ✅            ✅            ✅            ✅            ✅
```

> `python3 .hooks/generate.py list` 自动生成，与框架完全同步

### 平台独占（10 个 — Claude Code 特有）

这些守卫依赖 Claude Code 内建能力（LSP、Subagent、Skill、Plan 系统），是架构级差异：

| 独占守卫 | 依赖 |
|---------|------|
| lsp_suggest | LSP 工具系统 |
| subagent_guard | Subagent API |
| skill_flywheel | Skill 系统 |
| plan_gate | Plan Mode |
| read_tracker | Read 工具拦截 |
| read_cite | Read 工具输入输出协议 |
| edit_quality | Edit 工具输出分析 |
| write_cite | Write 工具协议 |
| rule_anchor | 回合计数 |
| subagent_audit | Subagent/Task API |

---

## 架构亮点

### 一次定义，全域生效

```
一个 .hooks/unified.yaml
        ↓
.hooks/generate.py
        ↓
    ┌──→ .codex/hooks.json           (Codex CLI)
    ├──→ .gemini/settings.json       (Gemini CLI)
    ├──→ settings.json               (Qwen Code)
    ├──→ .cursor/hooks.json          (Cursor)
    └──→ .opencode/plugins/*.ts      (OpenCode)
```

### 统一事件模型

| 抽象事件 | 平台映射 |
|---------|---------|
| `session:start` | 会话初始化 — 注入知识、恢复状态 |
| `prompt:submit` | 用户提交前 — 注入上下文、检测纠正 |
| `tool:before` | 工具执行前 — 校验参数、阻断危险操作 |
| `tool:after` | 工具执行后 — 验证结果、审计追踪 |
| `shell:before` | Shell 命令前 — 权限检查、危险命令拦截 |
| `shell:after` | Shell 命令后 — 编译错误追踪 |
| `file:write` | 文件写入前 — 密钥扫描、路径保护 |
| `compact:before` | 上下文压缩前 — 关键状态保留 |
| `stop` | 暂停点 — 快照、续跑信号 |

### I/O 协议

```
输入: stdin JSON { event, tool_input, tool_response, session }
输出: stdout JSON { continue: bool, hookSpecificOutput?: {} }
阻断: exit code 2 (硬阻断，AI 不可绕过)
通过: exit code 0
```

该协议与主流平台完全兼容，不依赖任何特定框架。

---

## 快速接入

```bash
# 1. 检测本机可用平台
python3 .hooks/generate.py detect

# 2. 生成所有已检测平台的原生配置
python3 .hooks/generate.py install

# 3. 验证配置
python3 .hooks/generate.py validate

# 4. 查看完整支持矩阵
python3 .hooks/generate.py list
```

### 各平台激活

| 平台 | 额外步骤 |
|------|---------|
| Claude Code | ✅ 无需操作（harness.yaml 已就绪） |
| Codex CLI | 开启 `~/.codex/config.toml` 中 `codex_hooks = true` |
| Gemini CLI | 已读 `.gemini/settings.json` 后自动生效 |
| Qwen Code | 已读 `settings.json` 后自动生效 |
| Cursor | 安装 `.cursor/hooks.json` 后重启生效 |
| OpenCode | 插件自动加载（`import.meta` 机制） |

---

## 能力对照速览

```
Claude Code  ████████████████████████████████████████████████████  29 守卫（原生全量）
Codex CLI    ██████████████████████████████████████              19 守卫（全事件）
Gemini CLI   ████████████████████████████████████              17 守卫（缺 2 事件）
Qwen Code    ██████████████████████████████████████              19 守卫（全事件）
OpenCode     ████████████████████████                            13 守卫（可扩展）
Cursor       █████████████████                            9 守卫（架构局限）
```

---

## 设计原则

1. **不绑定平台** — 核心守卫逻辑使用独立 shell 脚本，任何支持命令调用的 Hook 系统都可复用
2. **不改动原作** — 不修改 `.claude/hooks/*.sh` 脚本，适配层只生成平台原生配置
3. **渐进增强** — 每个平台按事件覆盖能力自然分组，非全有即全无
4. **配置即代码** — `unified.yaml` 可版本化管理，`generate.py` 保证多平台配置一致性
5. **可验证** — 每份生成配置经结构校验，`continue: false` 和 `exit 2` 的阻断逻辑是平台规范而非 hack

---

## 生态定位

```
                    ┌──────────────────────┐
                    │    Sylph Harness      │
                    │    29 守卫 / 1 模型    │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
     Claude Code          Codex CLI            OpenCode
     (原生, 29/29)        (生成, 19/29)        (插件, 13/29)
          │                    │                    │
     Gemini CLI            Qwen Code             Cursor
     (生成, 19/29)         (生成, 19/29)        (生成, 4/29)
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  同一套 Hook 脚本     │
                    │  .claude/hooks/*.sh  │
                    └─────────────────────┘
```

---

> Sylph Harness v6.1.9 — 2026.05
> 跨平台 AI CLI 治理框架
