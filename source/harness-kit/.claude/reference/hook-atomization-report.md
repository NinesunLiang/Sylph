# Hook 原子化分析报告 — 重复逻辑提取方案

> 分析范围：`~/.claude/hooks/` 下全部 **56 个 `.sh` hook 文件**  
> 分析日期：2026-05-26  
> 总代码行数：10,145 行（不含 .py / .bak）

---

## 概述

本次分析识别出 **12 个重复逻辑模式**（出现 ≥3 次），其中：

| 分类 | 数量 | 处理状态 |
|------|------|---------|
| 已集中但存在过度重复调用 | 2 | harness_config.sh（已集中，但行数高达 673） |
| 值得抽取为新共享函数 | 6 | 需加入 harness_config.sh |
| 已在 agentic-ui.sh 解决 | 1 | UI 渲染已统一 |
| 结构性高重复（但语义不同） | 3 | 通过宏/辅助函数减少 |

**总计可削减约 1,500-2,000 行重复代码**（约占 15-20%）。

---

## 候选模式清单

### P1. `SCRIPT_DIR` / `PROJECT_ROOT` / `STATE_DIR` 初始化 [⭐⭐⭐⭐⭐]

**出现次数**：38 / 56 hooks（68%）  
**重复代码量**：~4 行/次 × 38 = **~152 行直接重复**

#### 代码片段（代表性）

```bash
# completion-gate.sh:5-6
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# permission-gate.sh:141-143
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# turn-counter.sh:7-9
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
```

#### 使用该模式的 hook（前 15）

| Hook | 行号 |
|------|------|
| completion-gate.sh | 5-6 |
| permission-gate.sh | 141-143 |
| error-dna.sh | 31-33 |
| turn-counter.sh | 7-9 |
| inject-project-knowledge.sh | 7-9 |
| auto-snapshot.sh | 8-10 |
| context-guard.sh | 17-18 |
| pre-ask-guard.sh | 15-16 |
| pretool-sensitive-edit.sh | 13-15 |
| pretool-plan-gate.sh | 7-8,58 |
| pretool-edit-scope.sh | 39-41 |
| posttool-bash-audit.sh | 70-72,181-183 |
| stop-drain.sh | 22-24 |
| pretool-oracle-gate.sh | 42-43,71 |
| fuzzy-block.sh | — |

#### 抽取方案

在 `harness_config.sh` 中添加：

```bash
# hc_boot — 标准初始化：设置 SCRIPT_DIR, PROJECT_ROOT, STATE_DIR
# 用法: eval "$(hc_boot)"
hc_boot() {
    local _sd="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    local _pr="$(cd "$_sd/../.." && pwd)"
    printf 'export SCRIPT_DIR=%q PROJECT_ROOT=%q STATE_DIR=%q\n' \
        "$_sd" "$_pr" "$_pr/.omc/state"
}
```

或者更简单（单行 source lib）：

```bash
# 在 hook 中只需一行：
source "$(dirname "$0")/harness_config.sh"
```

然后在 harness_config.sh 头部自动设置 `SCRIPT_DIR/PROJECT_ROOT/STATE_DIR` 三个变量。

**收益**：消除 38 处 × ~4 行 = ~152 行重复，统一路径解析。

---

### P2. `mkdir -p STATE_DIR` 模式 [⭐⭐⭐⭐]

**出现次数**：18 / 56 hooks（32%）  
**重复代码量**：~1 行/次 × 18 = **~18 行直接重复**

#### 代码片段

```bash
mkdir -p "$STATE_DIR" 2>/dev/null
```

#### 使用该模式的 hook

| Hook |
|------|
| auto-snapshot.sh, build-validator.sh, compact-detect.sh |
| context-compressor.sh, error-dna.sh, intent-tracker.sh |
| lsp-suggest.sh, posttool-bash-audit.sh, posttool-edit-quality.sh |
| posttool-handoff-writer.sh, posttool-subagent-audit.sh |
| pre-ask-guard.sh, read-tracker.sh, stop-drain.sh |
| subagent-guard.sh, token_writer.sh, turn-counter.sh |

#### 抽取方案

在 `harness_config.sh` 的 `hc_boot()` 中自动执行 `mkdir -p`，或者在 `hc_enabled()` 返回 true 后自动创建。

**收益**：消除 18 处重复，且确保所有 hook 的 state 目录在启动时就存在。

---

### P3. jq/Python 双通道 stdin JSON 解析 [⭐⭐⭐⭐⭐]

**出现次数**：~20 hooks 有 `if command -v jq` / `else python3` 模式  
**重复代码量**：~5-15 行/次 × 20 = **~200-300 行重复**

#### 代码片段（代表性）

```bash
# permission-gate.sh:12-22
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
else
    COMMAND=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('command', data.get('tool_input', {}).get('command', '')))
except:
    pass" 2>/dev/null)
fi

# pretool-sensitive-edit.sh:26-41 — 同样模式但字段名不同
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // .tool_input.path // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "...")
fi
```

#### 使用该模式的 hook（入选 ≥3 次重复）

| Hook | 提取字段 |
|------|---------|
| permission-gate.sh | command |
| completion-gate.sh | status |
| posttool-bash-audit.sh | command, exit_code, stderr |
| pretool-sensitive-edit.sh | file_path |
| pretool-oracle-gate.sh | file_path |
| pretool-plan-gate.sh | tool_name, file_path, new_content |
| privacy-gate.sh | tool, file_path, pattern, command |
| error-dna.sh | tool_name |
| context-guard.sh | tool_name |
| stop-drain.sh | transcript_path, session_id |
| pretool-edit-scope.sh | file_path |
| plan-gate.sh | file_path |
| turn-counter.sh | count (session-turns.json) |
| pre-ask-guard.sh | questions |

#### 抽取方案

在 `harness_config.sh` 中添加通用 JSON 字段提取函数：

```bash
# hc_json_get_field — 从 stdin JSON 提取字段值（自动 fallback jq → python3）
# 用法: FIELD=$(echo "$INPUT" | hc_json_get_field '.tool_input.command,.args.command')
# 多个备选路径用逗号分隔
hc_json_get_field() {
    local paths="${1:-.}" python3_path
    if command -v jq &>/dev/null; then
        # 转换逗号分隔路径为 jq 的 // 语法
        local jq_path
        jq_path=$(echo "$paths" | sed 's/,/ \\/\\/ /g')
        jq -r "${jq_path} // empty" 2>/dev/null
    else
        python3_path=$(echo "$paths" | sed 's/,/\",\"/g')
        ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for p in [\"$python3_path\"]:
        v = d
        for k in p.split('.'):
            if isinstance(v, dict):
                v = v.get(k)
            elif isinstance(v, list) and k.isdigit():
                v = v[int(k)] if int(k) < len(v) else None
            else:
                v = None
                break
        if v is not None:
            print(v)
            break
except: pass" 2>/dev/null
    fi
}
```

**收益**：消除 ~20 处 × ~10 行的重复 jq/python3 分支，约 200 行。

---

### P4. `is_mode_active` + 模式降级逻辑 [⭐⭐⭐⭐]

**出现次数**：8 hooks 直接调用，更多 hook 隐式依赖  
**重复代码量**：~3-30 行/次 × 8 = **~80 行重复**

#### 代码片段

```bash
# completion-gate.sh:32-38 (自主模式检测)
AUTONOMOUS=false
if [ -f "$PROJECT_ROOT/.omc/state/tokens/autonomous.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/ghost-mode.active" ] || \
   ...
# vs permission-gate.sh:148 — 使用统一的 is_mode_active
MODE=$(is_mode_active "$STATE_DIR")

# context-guard.sh:30-35
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    MODE_LABEL="[${MODE} mode]"
fi

# pretool-oracle-gate.sh:62-68
MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")
if [ "$MODE" != "normal" ]; then
    echo "[oracle-gate] WARN: ${MODE} mode — Oracle gate skipped" >&2
    flywheel_event "oracle_gate" "mode_warn" "P2" || true
    echo '{"continue": true}'
    exit 0
fi
```

#### 使用 is_mode_active 的 hook

| Hook | 降级行为 |
|------|---------|
| completion-gate.sh | 自主模式：检查但降级为 warn |
| permission-gate.sh | 非 normal：记录 skipped-errors + flywheel |
| context-guard.sh | 非 normal：不硬阻断，仅 info |
| pretool-oracle-gate.sh | 非 normal：warn-only |
| pretool-sensitive-edit.sh | 非 normal：log+skip |
| pre-ask-guard.sh | 非 normal：全部阻断提问 |
| pretool-plan-gate.sh | ghost: allow, goal: 需 phase0 |
| fuzzy-block.sh / turn-counter.sh | 检测模式 |

#### 抽取方案

在 `harness_config.sh` 中提供「模式感知的 Gate 函数」：

```bash
# hc_gate_mode_warn — 非 normal 模式时降级为 warn
# 用法: hc_gate_mode_warn "oracle_gate" && { echo '{"continue": true}'; exit 0; }
# 返回: 0=应降级跳过, 1=继续正常门禁逻辑
hc_gate_mode_warn() {
    local gate_name="$1"
    local mode
    mode=$(is_mode_active "${_HC_STATE_DIR:-.omc/state}" 2>/dev/null || echo "normal")
    if [ "$mode" != "normal" ]; then
        echo "[$gate_name] WARN: ${mode} mode — gate skipped (mode downgrade)" >&2
        flywheel_event "$gate_name" "mode_warn" "P2" || true
        return 0
    fi
    return 1
}
```

**收益**：6-8 个 hook 中每个减少 5-15 行重复的模式检测代码 → ~60 行。

---

### P5. Token/CAPTCHA 生成 + 验证码流程 [⭐⭐⭐]

**出现次数**：3 个 hook 有完整 CAPTCHA + 1 个 hook 有简化版  
**重复代码量**：~30 行/次 × 4 = **~120 行重复**

#### 代码片段

```bash
# permission-gate.sh:274-283 — 五级降级 token 生成
APPROVAL_CODE=$(
  ${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(4))" 2>/dev/null ||
  ${PYTHON_BIN:-python3} -c "import random,..." 2>/dev/null ||
  { od -vAn -N4 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n'; } ||
  openssl rand -hex 4 2>/dev/null ||
  printf '%08x' ...
)
[ -z "$APPROVAL_CODE" ] && APPROVAL_CODE=$(printf '%08x' "$(( ($$ * ...) & 0xFFFFFFFF ))")
echo "$APPROVAL_CODE" > "$PERMISSION_REQUIRED"

# pretool-sensitive-edit.sh:119 — 简化版
APPROVAL_CODE=$(${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex(4))" 2>/dev/null || echo "sen-$$-$(date +%s)")

# pretool-oracle-gate.sh:143 — 简化版 (简化为 md5)
CAPTCHA=$(date +%s | md5 ...)
```

#### 使用该模式的 hook

| Hook | Token 生成方式 |
|------|--------------|
| permission-gate.sh:274-283 | 五级降级（secrets → random → /dev/urandom → openssl → printf） |
| pretool-sensitive-edit.sh:119 | 简化二级（secrets → pid+ts） |
| pretool-oracle-gate.sh:143 | MD5 简化版 |

#### CAPTCHA 验证码检查（同一模式，三个 hook）

```bash
# permission-gate.sh:232-260
# pretool-sensitive-edit.sh:93-116
# pretool-oracle-gate.sh:74-98
# 三处实现几乎完全相同：
#   检查 require/marker 文件 → 比较验证码 → 检查 300s 新鲜度 → 放行或清理
```

#### 抽取方案

在 `harness_config.sh` 中添加：

```bash
# hc_generate_token — 生成随机 hex token（五级降级）
hc_generate_token() {
    local len="${1:-8}"
    local byte_count=$((len / 2))
    local token
    token=$(${PYTHON_BIN:-python3} -c "import secrets; print(secrets.token_hex($byte_count))" 2>/dev/null) ||
    token=$(od -vAn -N"$byte_count" -tx1 /dev/urandom 2>/dev/null | tr -d ' \n') ||
    token=$(openssl rand -hex "$byte_count" 2>/dev/null) ||
    token=$(printf "%0${len}x" "$(($$ * $(date +%s) & 0xFFFFFFFF))")
    echo "$token"
}

# hc_captcha_check — 检查 CAPTCHA 验证码（返回 0=通过, 1=未通过）
hc_captcha_check() {
    local required_file="$1" approved_file="$2" freshness_sec="${3:-300}"
    [ -f "$required_file" ] || return 1
    [ -f "$approved_file" ] || return 1
    local expected=$(cat "$required_file" 2>/dev/null)
    local actual=$(cat "$approved_file" 2>/dev/null)
    [ "$expected" = "$actual" ] || return 1
    [ -z "$expected" ] && return 1
    # 新鲜度检查
    ${PYTHON_BIN:-python3} -c "import os,time; exit(0 if time.time()-os.path.getmtime('$approved_file')<$freshness_sec else 1)" 2>/dev/null || return 1
    return 0
}
```

**收益**：消除 3-4 个 hook 中 ~120 行重复的 token 生成+验证逻辑。

---

### P6. `flywheel_event` 调用模式 [⭐⭐⭐]

**出现次数**：全局 80 次 flywheel_event 调用（已通过 harness_config.sh 集中）  
**重复代码量**：此模式已经很好地集中，但调用签名仍有 3 种变体：

```bash
flywheel_event "hook_name" "event_type" "P1" || true
flywheel_event "hook_name" "event_type" "P2" || true
flywheel_event "hook_name" "event_type" "P2" "extra_info" || true
```

`|| true` 后缀出现 80 次 — 这本身是重复的防御性代码。

**抽取方案**：在 `flywheel_event` 函数内部 trap 所有错误，消除所有调用处的 `|| true`。

---

### P7. 双源 Error 分类器（classify/sanitize） [⭐⭐⭐]

**出现次数**：2 个 hook 有完全相同的 classify() 函数（≥3 行相同算 3+ 条件不完全满足，但相似度极高）  
**额外**：sanitize 函数逻辑也高度重复

#### 代码片段

```bash
# error-dna.sh:190-207 (Python inline)
if any(x in cmd_lower for x in ['go build', 'go test', 'npm run build', ...]):
    error_type = 'build'
elif any(x in cmd_lower for x in ['go test', 'npm test', 'pytest', 'jest']):
    error_type = 'test'
...

# stop-drain.sh:93-103 (Python inline — 几乎完全相同)
def classify(cmd):
    c = cmd.lower()
    if any(x in c for x in ['go build', 'npm run build', 'cargo build', 'tsc']): return 'build'
    if any(x in c for x in ['go test', 'npm test', 'pytest', 'jest']): return 'test'
    ...
```

#### Credential sanitization 重复

```bash
# error-dna.sh:113-128 & stop-drain.sh:73-91
# 两者有相同的：
#   --password ***, --token ***, --secret ***, --key ***
#   API key 环境变量脱敏
#   JWT token 脱敏
#   U+D800 代理对清理
```

**抽取方案**：将 classify/sanitize 作为 `hc_classify_error()` 和 `hc_sanitize_credentials()` 加入 `harness_config.sh`。

**收益**：消除 2 个 hook 中各 ~50 行的重复 inline 逻辑。

---

### P8. 双通道输出（stderr 给用户，stdout JSON 给 AI） [⭐⭐⭐⭐]

**出现次数**：~8 个 hook 有 stderr + stdout 双通道输出  
**重复代码量**：~5 行/次 × 8 = **~40 行重复**

```bash
# 多处重复出现的模式
echo "⚠️ [Gate] 消息" >&2           # stderr → 人类可见
printf '{"continue":false,...}'      # stdout → AI/平台消费
exit 2

# 或使用 hc_emit_hook_json
echo "message" | hc_emit_hook_json "PostToolUse" "false"
```

#### 使用 hooks

completion-gate.sh, context-guard.sh, permission-gate.sh, pretool-sensitive-edit.sh, privacy-gate.sh, pretool-oracle-gate.sh, pretool-plan-gate.sh, plan-gate.sh

#### 抽取方案

提供 `hc_gate_block()` / `hc_gate_warn()` / `hc_gate_pass()` 宏：

```bash
# hc_gate_block "GateName" "stderr_message" "additionalContext"
hc_gate_block() {
    local name="$1" stderr_msg="$2" context_msg="$3"
    echo "⛔ [${name}] ${stderr_msg}" >&2
    flywheel_event "$name" "blocked" "P1" || true
    printf '%s' "$context_msg" | hc_emit_hook_json "PreToolUse" "false"
    exit 2
}
```

**收益**：8 个 hook 减少每个 ~5 行的双输出逻辑 → ~40 行。

---

### P9. 文件新鲜度检查（Freshness Check） [⭐⭐]

**出现次数**：4 个 hook 有相似的文件 mtime 新鲜度检查  
**重复代码量**：~6 行/次 × 4 = **~24 行**

```bash
# completion-gate.sh:66-75 & pretool-sensitive-edit.sh:98-107
if command -v python3 &>/dev/null; then
    FRESH=$(${PYTHON_BIN:-python3} -c "import os, time
try:
    age = time.time() - os.path.getmtime('$FILE')
    print('yes' if age < $MAX_AGE else 'no')
except:
    print('no')" 2>/dev/null)
else
    FRESH="yes"
fi
```

#### 使用 hooks

completion-gate.sh:66-75, pretool-sensitive-edit.sh:98-107, permission-gate.sh:238-247, pretool-oracle-gate.sh:78-88

#### 抽取方案

```bash
# hc_is_fresh "/path/to/file" 300 → 0=fresh, 1=stale
hc_is_fresh() {
    local file="$1" max_age="${2:-300}"
    [ ! -f "$file" ] && return 1
    ${PYTHON_BIN:-python3} -c "
import os, time
try:
    age = time.time() - os.path.getmtime('$file')
    exit(0 if age < $max_age else 1)
except: exit(1)" 2>/dev/null
}
```

---

### P10. `hc_sanitize_utf8` 使用不统一 [⭐⭐]

**出现次数**：8 个 hook 提及 surrogate/sanitize  
**现状**：`harness_config.sh` 已提供 `hc_sanitize_utf8()` 函数，但：
- 部分 hook 用 `hc_sanitize_utf8` 管道
- 部分 hook 在 Python inline 中手动处理 surrogates
- 部分 hook 同时做了两件事

重复的 surrogate 剥离出现在：auto-snapshot.sh (2 次), intent-tracker.sh (1 次), error-dna.sh (多次), stop-drain.sh, pretool-rules-inject.sh, pre-edit-lsp-check.sh

**抽取方案**：统一所有 hook 使用 `hc_sanitize_utf8`，移除内联 surrogate 处理。

---

### P11. Issue-Triage 集成 [⭐⭐]

**出现次数**：5 个 hook  
**重复代码量**：~8 行/次 × 5 = **~40 行**

```bash
# completion-gate.sh:44-47
if [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
    triage_msg=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook "completion-gate" "$1" "" "{}" 2>/dev/null || echo "")
fi

# error-dna.sh:452-455 — 相同模式
if [ -n "$PY_OUTPUT" ] && (echo "$PY_OUTPUT" | grep -q "pattern"); then
    if [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
        TRIAGE_MSG=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook ...)
    fi
fi
```

#### 使用 hooks

completion-gate.sh, error-dna.sh, inject-project-knowledge.sh, posttool-bash-audit.sh, posttool-claim-audit.sh

#### 抽取方案

```bash
# hc_triage "hook_name" "issue_summary" "P1" — 单行调用
hc_triage() {
    local hook="$1" issue="$2" priority="${3:-P2}"
    local triage_script="${_HC_PROJECT_ROOT:-.}/.claude/scripts/issue-triage.sh"
    [ -f "$triage_script" ] || return 0
    source "$triage_script" && triage_for_hook "$hook" "$issue" "$priority" "{}" 2>/dev/null || true
}
```

**收益**：5 个 hook 各减少 ~8 行的 triage 集成代码 → ~40 行。

---

### P12. `escape_detection` 二段开关 [⭐⭐]

**出现次数**：3 个 hook  
**重复代码量**：~3 行/次 × 3 = **~9 行**

```bash
# error-dna.sh:11-12
_ed_val="$(hc_get 'escape_detection' 'true')"; _ed_val="${_ed_val%\\}"
[ "$_ed_val" = "true" ] || { echo '{"continue": true}'; exit 0; }

# posttool-bash-audit.sh:8-9 — 完全相同
_ed_val="$(hc_get 'escape_detection' 'true')"; _ed_val="${_ed_val%\\}"
[ "$_ed_val" = "true" ] || { echo '{"continue": true}'; exit 0; }
```

#### 抽取方案

```bash
# hc_escape_enabled — 检查 escape_detection 是否启用（默认 true）
hc_escape_enabled() {
    local val
    val=$(hc_get 'escape_detection' 'true')
    val="${val%\\}"
    [ "$val" = "true" ]
}
```

---

## 综合抽取策略

### 阶段 1：低风险（立即可做）→ harness_config.sh 扩展

| 新增函数 | 解决模式 | 削减行数 |
|---------|---------|---------|
| `hc_boot()` | P1+P2 (SCRIPT_DIR/PROJECT_ROOT + mkdir) | ~170 行 |
| `hc_json_get_field()` | P3 (jq/python3 解析) | ~200 行 |
| `hc_gate_mode_warn()` | P4 (模式降级) | ~60 行 |
| `hc_generate_token()` | P5a (Token 生成) | ~40 行 |
| `hc_captcha_check()` | P5b (CAPTCHA 验证) | ~60 行 |
| `hc_classify_error()` | P7a (错误分类) | ~30 行 |
| `hc_sanitize_credentials()` | P7b (凭证脱敏) | ~30 行 |
| `hc_gate_block()` / `hc_gate_warn()` | P8 (双通道输出) | ~40 行 |
| `hc_is_fresh()` | P9 (新鲜度检查) | ~24 行 |
| `hc_triage()` | P11 (issue-triage) | ~40 行 |
| `hc_escape_enabled()` | P12 (escape 开关) | ~9 行 |
| flywheel_event 内置错误处理 | P6 | ~80 行 `\|\| true` |

### 阶段 2：中等风险（需测试）→ 统一 surrogate 处理

| 操作 | 影响范围 |
|------|---------|
| 所有 hook 统一使用 `hc_sanitize_utf8` | 8 个 hook 移除内联 sanitize |
| 移除重复的 `_strip_surr()` 函数定义 | auto-snapshot.sh (×2), intent-tracker.sh |

### 阶段 3：结构优化（按需）

| 操作 | 收益 |
|------|------|
| 分离 `harness_config.sh` 为核心 + 扩展 | 673 行 → ~300 行核心 + ~400 行扩展 |
| 创建 `hooks/_lib_json.sh` | 收拢 JSON 解析逻辑 |

---

## 汇总收益

| 阶段 | 削减行数（估计） | 风险 |
|------|----------------|------|
| 阶段 1（harness_config 扩展） | ~800-1,000 行 | 低 |
| 阶段 2（sanitize 统一） | ~200 行 | 中 |
| 阶段 3（结构拆分） | ~400 行 | 中 |
| **总计** | **~1,400-1,600 行** | — |

**关键洞察**：`harness_config.sh` 已经做了很好的集中（49/56 hooks 都已 source 它），当前主要问题是：
1. 缺少针对常见模式的高级辅助函数（导致每个 hook 自己实现）
2. `harness_config.sh` 自身 673 行，需要按职责拆分（配置解析 / 模式管理 / 输出辅助 / 安全工具）

---

## 已集中化（无需再动）

以下模式已在集中库中，运作良好：

| 模式 | 载体 | 使用数 |
|------|------|--------|
| `hc_enabled` 功能开关 | harness_config.sh | 49 hooks |
| `hc_get` 配置读取 | harness_config.sh | ~40 hooks |
| `hc_emit_hook_json` | harness_config.sh | ~10 hooks |
| `agentic_status/captcha/menu` | agentic-ui.sh | 6 hooks |
| `flywheel_event` (定义) | harness_config.sh | ~44 hooks |
| `PYTHON_BIN` 跨平台解析 | harness_config.sh | ~40 hooks |
| DG-82 运行时证据追踪 | harness_config.sh (trap) | 自动覆盖所有 source 它的 hook |

---

## 反向映射：Hook → 涉及的重复模式

| Hook | 涉及模式 | 建议替换 |
|------|---------|---------|
| completion-gate.sh | P1,P2,P3,P4,P5,P9,P11 | 最大收益 (~50 行削减) |
| permission-gate.sh | P1,P2,P3,P4,P5,P8,P9 | ~40 行削减 |
| error-dna.sh | P1,P2,P3,P7,P11,P12 | ~50 行削减 |
| turn-counter.sh | P1,P2,P3,P4 | ~20 行削减 |
| inject-project-knowledge.sh | P1,P2,P10,P11 | ~20 行削减 |
| auto-snapshot.sh | P1,P2,P3,P10 | ~30 行削减 |
| context-guard.sh | P1,P3,P4,P8 | ~15 行削减 |
| pre-ask-guard.sh | P1,P2,P3,P4 | ~15 行削减 |
| pretool-sensitive-edit.sh | P1,P3,P4,P5,P8,P9 | ~30 行削减 |
| pretool-plan-gate.sh | P1,P3,P4,P8 | ~20 行削减 |
| pretool-oracle-gate.sh | P1,P3,P4,P5,P8,P9 | ~25 行削减 |
| pretool-edit-scope.sh | P1,P3,P4 | ~15 行削减 |
| posttool-bash-audit.sh | P1,P2,P3,P11,P12 | ~25 行削减 |
| stop-drain.sh | P1,P2,P3,P7,P10 | ~30 行削减 |
| privacy-gate.sh | P3,P8 | ~10 行削减 |
| plan-gate.sh | P3,P8 | ~10 行削减 |
| 其他 40 hooks | P1,P2,P3 (部分) | 各 3-10 行 |
