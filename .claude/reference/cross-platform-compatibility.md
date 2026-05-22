# Cross-Platform Compatibility Reference

> Carror OS 四平台 (Claude Code / OpenCode / Codex CLI / Cursor) + Windows/Mac 兼容性全景
> 调研来源：官方文档 + 源码级 SDK 类型定义 + 外部运行时实测 + unified.yaml 事件映射表

---

## 1. 四平台事件映射矩阵

### 1.1 Carror OS 9 通用事件 → 各平台原生事件

| # | 通用事件 | Claude Code | OpenCode | Codex CLI | Cursor |
|---|---------|-------------|----------|-----------|--------|
| 1 | `session:start` | `SessionStart` | `session.created` † | `UserPromptSubmit` * | ❌ 不支持 |
| 2 | `prompt:submit` | `UserPromptSubmit` | `message.updated` | `UserPromptSubmit` | ❌ 不支持 |
| 3 | `tool:before` | `PreToolUse` | `tool.execute.before` | `PreToolUse` | ❌ 不支持 |
| 4 | `tool:after` | `PostToolUse` | `tool.execute.after` | `PostToolUse` | ❌ 不支持 |
| 5 | `shell:before` | `PreToolUse` ‡ | `tool.execute.before` ‡ | `PreToolUse` ‡ | `beforeShellExecution` |
| 6 | `shell:after` | `PostToolUse` ‡ | `tool.execute.after` ‡ | `PostToolUse` ‡ | `afterShellExecution` |
| 7 | `file:write` | `PreToolUse` ‡ | `tool.execute.before` ‡ | `PreToolUse` ‡ | `beforeFileWrite` |
| 8 | `compact:before` | `PreCompact` | `session.compacted` | `PreCompact` | ❌ 不支持 |
| 9 | `stop` | `Stop` | `session.idle` † | `Stop` | ❌ 不支持 |

> **图例**：
> - `†` = 事件在 SDK 类型定义中存在，但外部运行时实测确认**不触发** (OpenCode SDK v1.14.28, 2026-05-22 实测)
> - `*` = 平台无对应事件，用最接近的替代事件降级
> - `‡` = 同事件名，通过脚本内 matcher 区分工具类型
> - `❌ 不支持` = 平台完全不提供该事件，该维度的 hook 在此平台静默失效

### 1.2 各平台事件覆盖度

| 平台 | 支持事件数 | 覆盖率 | 缺口 |
|------|----------|--------|------|
| **Claude Code** | 9/9 | 100% | 无 — 全事件原生支持 |
| **Codex CLI** | 7/9 | 78% | `session:start` (降级), `stop` (2 个缺口) |
| **OpenCode** | 7/9 | 78% | `session:start` (不触发†), `stop` (不触发†) |
| **Cursor** | 3/9 | 33% | 仅 shell 和 file write 事件 — 无 session/prompt/tool/compact 事件 |

> **Cursor 的现实**：`.cursor/hooks.json` 只支持 4 个事件 (`beforeShellExecution`, `afterShellExecution`, `beforeFileWrite`, `afterFileWrite`)。所有 PreToolUse/PostToolUse/SessionStart/Stop 类 hook 在 Cursor 下**完全静默失效**。

---

## 2. 工具输入字段名兼容性

### 2.1 核心差异

不同平台向 hook 脚本传递的 JSON 结构不同：

| 平台 | file_path 字段路径 | command 字段路径 | 说明 |
|------|-------------------|-----------------|------|
| **Claude Code** | `.tool_input.file_path` | `.tool_input.command` | 原生格式 |
| **OpenCode** | `.args.filePath` | `.args.command` | camelCase + `args` 前缀 |
| **Codex CLI** | `.tool_input.file_path` | `.tool_input.command` | 与 Claude Code 相同格式 |
| **Cursor** | `.current_file` | `.command` | 不同结构，仅 shell/file 事件 |

### 2.2 统一兼容解析模式

所有 Carror OS hook 脚本使用 jq 的 `//` (alternative) 运算符做双字段名回退：

```bash
# file_path 兼容解析
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)

# command 兼容解析
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
```

### 2.3 已适配 Hook 清单（15 个）

通过 `grep -rl 'file_path.*filePath\|\.args\.filePath\|\.args\.command' .claude/hooks/` 验证：

| # | Hook | 事件 | 适配字段 |
|---|------|------|---------|
| 1 | `edit-guard.sh` | PreToolUse:Edit | `file_path // .args.filePath` |
| 2 | `plan-gate.sh` | PreToolUse:Edit | `file_path // .args.filePath` |
| 3 | `pretool-edit-scope.sh` | PreToolUse:Edit | `file_path // .args.filePath` |
| 4 | `pretool-sensitive-edit.sh` | PreToolUse:Edit | `file_path // .args.filePath` |
| 5 | `pre-edit-lsp-check.sh` | PreToolUse:Edit | `file_path // .args.filePath` |
| 6 | `posttool-claim-audit.sh` | PostToolUse:Edit | `file_path // .args.filePath` |
| 7 | `posttool-edit-quality.sh` | PostToolUse:Edit | `file_path // .args.filePath` |
| 8 | `posttool-read-cite.sh` | PostToolUse:Read | `file_path // .args.filePath` |
| 9 | `posttool-write-cite.sh` | PostToolUse:Write | `file_path // .args.filePath` |
| 10 | `permission-gate.sh` | PreToolUse:Bash | `command // .args.command` |
| 11 | `privacy-gate.sh` | PreToolUse:Bash | `command // .args.command` |
| 12 | `pretool-blast-radius.sh` | PreToolUse:Bash | `command // .args.command` |
| 13 | `posttool-bash-audit.sh` | PostToolUse:Bash | `command // .args.command` |
| 14 | `build-validator.sh` | PostToolUse:Bash | `command // .args.command` |
| 15 | `read-tracker.sh` | PostToolUse:Read | `file_path // .args.filePath` |

---

## 3. 各平台实现架构

### 3.1 Claude Code — 原生全栈

```
settings.json (Hook 注册) → harness.yaml (开关) → hooks/*.sh (脚本)
```

- **100% 事件支持**：9/9 通用事件全部原生可用
- **字段格式**：`.tool_input.file_path` / `.tool_input.command`
- **无需适配器**：直接读取 `.claude/settings.json`
- **安装方式**：`install.sh` 写入 `.claude/settings.json`

### 3.2 OpenCode — 双层桥接

```
settings.json (Hook 注册)
    ├─ OMO (oh-my-openagent) → 处理 PreToolUse / PostToolUse / PreCompact (3/9)
    └─ carror-hooks-compat.ts → 补齐 SessionStart / Stop / UserPromptSubmit / PostToolUseFailure (4/9)
```

- **OMO 原生处理**：PreToolUse, PostToolUse, PreCompact — 直接读 settings.json
- **carror-hooks-compat.ts 补齐**：session.created, message.updated, session.idle, tool.execute.after(失败检测)
- **字段格式**：`.args.filePath` / `.args.command` (camelCase)
- **已知问题**：
  - `session.created` — SDK 类型定义存在但实测不触发 (2026-05-22 外部实测确认)。**已修复**: carror-hooks-compat.ts 改为首次 `message.updated` 回退触发 SessionStart hooks，marker 文件防重复
  - `harness-kit.ts` — 完整实现但被 `.disabled` 后缀禁用
- **配置文件**：`.opencode/opencode.json` → 注册 `carror-hooks-compat.ts` + `session-guardian.ts`
- **安装方式**：`install.sh` 创建 `.opencode/opencode.json` 和 `.opencode/plugins/`

### 3.3 Codex CLI — Python 适配器生成

```
.hooks/unified.yaml → .hooks/adapters/codex.py → .codex/hooks.json
```

- **事件映射**：7/9 通用事件可用
- **SessionStart 降级**：无原生事件 → 用 `UserPromptSubmit`（首次 prompt 时触发）
- **Stop 降级**：无原生事件 → 静默跳过
- **配置格式**：`.codex/hooks.json`（JSON 格式，不同于 Claude Code 的 settings.json）
- **关键配置**：Codex 需要 `hooks = true` 在 `config.toml` 中显式开启
- **安装方式**：`install.sh` 运行 `python3 .hooks/generate.py generate codex`

### 3.4 Cursor — 有限事件集

```
.hooks/unified.yaml → .hooks/adapters/cursor.py → .cursor/hooks.json
```

- **事件覆盖**：仅 3/9（shell:before, shell:after, file:write）
- **根本限制**：Cursor hooks.json 只支持 4 个原生事件类型
- **失效的 Hook 类别**：
  - 所有 PreToolUse:Edit hook（edit-guard, pretool-edit-scope 等）→ ❌
  - 所有 PostToolUse hook（read-tracker, posttool-claim-audit 等）→ ❌
  - 所有 SessionStart/Stop hook → ❌
  - 所有 PreCompact hook（context-compressor 等）→ ❌
- **仍生效的 Hook**：permission-gate (shell:before), privacy-gate (shell:before + file:write), posttool-bash-audit (shell:after)
- **已知问题**：`postToolUse` stdin 为空 bug — Cursor 不向 afterShellExecution hook 传递完整上下文

### 3.5 Gemini CLI / Qwen Code

通过 `.hooks/adapters/gemini.py` 和 `.hooks/adapters/qwen.py` 生成配置。

| 平台 | 事件覆盖 | 主要缺口 |
|------|---------|---------|
| **Gemini CLI** | 5/9 | SessionStart(降级→BeforeTool), Stop(不支持), compact(不支持) |
| **Qwen Code** | 7/9 | SessionStart(降级→UserPromptSubmit), Stop(降级→UserPromptSubmit) |

---

## 4. Windows/Mac 差异

### 4.1 已识别差异矩阵

| 维度 | macOS | Windows (Git Bash) | Windows (原生 Powershell) | 当前状态 |
|------|-------|-------------------|--------------------------|---------|
| **路径分隔符** | `/` | `/` (Git Bash 转换) | `\` | ✅ Git Bash 兼容 |
| **`sed -i` 语法** | `sed -i ''` (BSD) | `sed -i` (GNU) | 不适用 | ✅ `sed -i.backup` 回退方案 |
| **sed 量词** | `\+` 不支持 (POSIX BRE) | `\+` 支持 (GNU) | 不适用 | ✅ DG-77 修复: 用 `sed -E` |
| **`/dev/null`** | ✅ 可用 | ✅ 可用 | ❌ 应为 `$null` 或 `NUL` | ⚠️ hooks 中使用 `2>/dev/null` |
| **Shell** | `bash`/`zsh` | `bash` (Git Bash) | `powershell`/`pwsh` | ⚠️ hooks 假设 bash 可用 |
| **`jq` 可用性** | ✅ | ✅ (Git Bash) | ❌ 需单独安装 | ⚠️ jq 缺失时降级为 python3 |
| **文件权限模型** | Unix (chmod) | Unix (Git Bash) | Windows ACL | ✅ install.sh 跳过 chmod on Windows |
| **行尾符** | LF | LF (Git Bash) | CRLF | ✅ .gitattributes 控制 |
| **HOME 路径** | `/Users/xxx` | `/c/Users/xxx` | `C:\Users\xxx` | ⚠️ 硬编码路径风险 (DG-31 已修复) |

### 4.2 Windows 适配优先级

| 优先级 | 问题 | 影响范围 | 修复方案 |
|--------|------|---------|---------|
| **P0** | `2>/dev/null` 在 Powershell 无效 | 所有 hook 脚本 | 添加 `NUL` 回退或使用 bash 重定向兼容写法 |
| **P1** | jq 在原生 Windows 不可用 | jq 解析的所有 hook | python3 回退已实现，需验证 PowerShell 下 `python3` vs `python` |
| **P2** | Git Bash 路径转换 (`/c/Users/...`) | 路径比较的 hook (edit-guard, context-guard) | 路径规范化函数 |
| **P3** | 原生 PowerShell 不支持 bash 脚本 | 所有 hook | 需要 PowerShell 翻译层或 WSL 依赖 |

> **当前定位**：Carror OS Windows 支持以 **Git Bash** 为最低基线。原生 PowerShell 支持需要完整的 `.ps1` 翻译层，不在当前 scope 内。

---

## 5. 与 Carror OS 哲学/铁律的对齐分析

### 5.1 哲学对齐

| # | 哲学 | 对齐状态 | 分析 |
|---|------|---------|------|
| **#1** | The Less, The More | ✅ 对齐 | `// .args.filePath` 回退是单行变更，静默生效，用户无感 |
| **#2** | 少量正确大增益 | ✅ 对齐 | 15 个 hook 各改一行，换来四平台兼容 |
| **#3** | 先守护，后激发 | ✅ 对齐 | 安全 hook (permission-gate, privacy-gate, blast-radius) 优先适配 |
| **#4** | 没验证=没做 | ⚠️ 部分 | Mac (CC + OpenCode) 已验证；Windows/Codex/Cursor 未做运行时验证 |
| **#5** | 以人为本 | ✅ 对齐 | 自动化配置生成，用户无需手动处理平台差异 |
| **#6** | 0信任 | ✅ 已修复 | Oracle 审查发现 python3 回退盲区 (P0.2) + pretool-sensitive-edit 缺失回退 (P0.1) → 已修复 12 个 hook |
| **#7** | 文档优先，调研先行 | ✅ 已修复 | 本文档即为缺失的调研结晶 (此前被 context guard 阻断) |

### 5.2 Oracle 审查记录 (2026-05-22)

| # | 严重度 | 问题 | 状态 |
|---|--------|------|------|
| P0.1 | 🔴 CRITICAL | `pretool-sensitive-edit.sh` 缺少 `.args.filePath` + `.tool` 回退 — OpenCode 下治理文件保护完全失效 | ✅ 已修复 |
| P0.2 | 🔴 CRITICAL | 15 个 hook 的 python3 回退代码不识别 OpenCode 的 `.args.*` 字段 | ✅ 已修复 (12 hooks) |
| P1.1 | 🟡 MAJOR | unified.yaml cursor.file:write=null 与 .cursor/hooks.json 矛盾 | ✅ 已修复 |
| P1.2 | 🟡 MAJOR | Cursor hooks.json 注册 edit-guard 但 read-tracker 永不被触发 | ✅ 已修复 (移除 edit-guard) |
| P2.4 | 🟢 MINOR | privacy-gate.sh grep 回退未处理 OpenCode `filePath` | ✅ 已修复 |

### 5.2 铁律/架构规则对齐

| 规则 | 来源 | 对齐状态 | 分析 |
|------|------|---------|------|
| Hook 不可失败 | kernel.md | ✅ | `// empty` 回退确保字段缺失时不崩溃 |
| hc_enabled 门禁 | kernel.md | ✅ | 所有适配 hook 保留 `hc_enabled` 检查 |
| 禁止 `set -e` | kernel.md | ✅ | 跨平台适配未引入 `set -e` |
| macOS sed `\+` 禁令 | kernel.md DG-77 | ✅ | 已在 install.sh 中修复 |
| 发行包路径脱敏 | kernel.md DG-31 | ✅ | `__PROJECT_ROOT__` 占位符方案跨平台安全 |

### 5.3 已知风险与缺口

| # | 风险 | 严重度 | 说明 |
|---|------|--------|------|
| **R1** | OpenCode `session.created` 静默失效 | 🟢 已修复 | carror-hooks-compat.ts 改为首次 `message.updated` 回退触发 SessionStart hooks + `.omc/state/.session-start-marker` 防重复。session.idle (Stop) 仍无回退 — 影响较小 |
| **R2** | Cursor 仅 3/9 事件 | 🟡 P1 | 设计级限制，无法通过适配层修复。需在文档中明确告知 Cursor 用户的防御能力降级 |
| **R3** | Codex `hooks=true` 未文档化 | 🟡 P2 | Codex 需要显式开启 hooks。install.sh 未提示用户。修复：在 install.sh 输出中添加 Codex 配置提醒 |
| **R4** | Windows 非 Git Bash 环境 | 🟢 P3 | 原生 PowerShell 下 2>/dev/null 和 jq 不可用。python3 回退已实现但未经 Windows 实测 |
| **R5** | 跨平台运行时测试缺失 | 🟡 P2 | 无自动化测试验证各平台 hook 实际触发。外部测试 (tmp/question.md) 是手工进行的 |

---

## 6. 实现状态 Checklist

### 6.1 已完成

- [x] 15 个 hook 添加 `.tool_input.xxx // .args.xxx` 双字段回退
- [x] `carror-hooks-compat.ts` OpenCode 4 事件补齐插件
- [x] `.hooks/unified.yaml` 9 事件统一模型 + 6 平台映射表
- [x] `.hooks/adapters/` 6 平台 Python 配置生成器 (claude_code/codex/gemini/qwen/cursor/opencode)
- [x] `install.sh` sed 跨平台兼容 (`sed -i.backup` + `@` 分隔符)
- [x] `install.sh` `__PROJECT_ROOT__` 占位符替换
- [x] DG-77 macOS sed `\+` 量词修复
- [x] `.cursor/hooks.json` 静态配置 (shell + file 事件)
- [x] 本文档 (cross-platform-compatibility.md) — 补齐调研文档

### 6.2 待完成

- [ ] **P0**: Windows 原生 PowerShell `2>/dev/null` 兼容 (影响所有 hook)
- [ ] **P1**: Codex `hooks=true` 配置提醒加入 install.sh 输出
- [ ] **P1**: Cursor 能力降级警告加入 install.sh 输出
- [x] **P1**: OpenCode `session.created` 回退修复 — carror-hooks-compat.ts 首次 `message.updated` 触发 SessionStart (2026-05-22)
- [ ] **P2**: 跨平台运行时 smoke test (至少覆盖 CC + OpenCode on Mac)
- [ ] **P2**: `pretool-blast-radius.sh` 在 Cursor 的 `beforeShellExecution` 事件下验证
- [ ] **P3**: Cursor `postToolUse` stdin-empty bug workaround adapter
- [ ] **P3**: 原生 PowerShell hook 翻译层 (`.ps1` 版本)

---

## 7. 外部运行时验证证据

> 来源：`tmp/question.md` — 2026-05-22 在 `fe_react_anka` 项目的 OpenCode 环境实测

| 测试项 | 结果 | 证据 |
|--------|------|------|
| `tool.execute.before` 触发 | ✅ 工作 | permission-gate 每次 Bash 前弹出拦截 |
| `tool.execute.after` 触发 | ✅ 工作 | read-tracker 每次 Read 后追加条目 |
| `chat.message` 触发 (轮次计数) | ✅ 工作 | session-turns count 从 2→6→8 实时更新 |
| `session.created` 触发 | ❌ 不工作 | 事件在 SDK 中存在但从不触发 |
| `session.idle` 触发 | ❌ 不工作 | 同上 |
| 字段名 `tool_input.file_path` vs `args.filePath` | ⚠️ 不匹配 | 确认 OpenCode 使用 camelCase `args` 前缀，CC 格式的脚本需要双字段回退 |

---

## 8. 参考资料

| 资源 | 路径 | 内容 |
|------|------|------|
| 统一事件模型 | `.hooks/unified.yaml` | 9 通用事件 + 6 平台映射表 |
| 平台适配器 | `.hooks/adapters/*.py` | 各平台配置生成逻辑 |
| OpenCode 桥接插件 | `.opencode/plugins/carror-hooks-compat.ts` | 4 事件补齐 |
| Cursor hooks 配置 | `.cursor/hooks.json` | shell + file 事件静态配置 |
| OpenCode SDK 类型 | `.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` | 官方事件定义 |
| 外部运行时测试 | `tmp/question.md` | 2026-05-22 OpenCode 实测报告 |
| Windows/Mac sed 修复 | `install.sh` + `kernel.md DG-77` | sed 跨平台兼容实现 |
