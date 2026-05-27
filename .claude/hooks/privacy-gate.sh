#!/usr/bin/env bash
# privacy-gate.sh — PreToolUse:Bash|Read|Grep — 防止隐私数据泄露（DLP 门禁）
# Role: 防止隐私数据泄露（DLP 门禁）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "privacy_gate" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
set -f

# C-3: privacy-gate 在所有模式下保持活跃 — 凭据泄露零容忍
# ghost/goal 模式也不例外: .env/密钥泄露在任何模式下都是严重安全事件

INPUT=$(cat)

if command -v jq &>/dev/null; then
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
    PATTERN=$(echo "$INPUT" | jq -r '.tool_input.pattern // empty' 2>/dev/null)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
else
    # 极简回退解析
    TOOL=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$TOOL" ] && TOOL=$(echo "$INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$FILE_PATH" ] && FILE_PATH=$(echo "$INPUT" | grep -o '"filePath"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    PATTERN=$(echo "$INPUT" | grep -o '"pattern"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    CMD=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi

# 统一小写化以兼容 Claude Code 的 PascalCase 工具名 (R16)
TOOL=$(echo "$TOOL" | tr '[:upper:]' '[:lower:]')

# 1. 检查读取/搜索的文件名
CHECK_PATH="$FILE_PATH$PATTERN"
if [ -n "$CHECK_PATH" ]; then
    if echo "$CHECK_PATH" | grep -iE '\.env|\.pem|\.key|\.p12|\.pfx|\.jks|id_rsa|credentials\.(json|ya?ml)|secret[es]?\.ya?ml|auth\.json|kubeconfig' > /dev/null; then
        flywheel_event "privacy_gate" "triggered" "P2" || true
        agentic_status danger \
            "Privacy Gate 触发" \
            "禁止直接读取包含配置、凭据或密钥的敏感文件（${CHECK_PATH}）。" \
            "请使用 /lx-varlock 脱敏代理安全读取此文件，避免明文凭据泄漏到 AI 上下文中。"
        printf '[Hook-Skill桥] privacy-gate → /lx-varlock: 敏感文件读取被拦截（%s），请用 /lx-varlock 脱敏代理安全打开此文件。' "$CHECK_PATH" | hc_emit_hook_json "PreToolUse" "false"
        exit 2
    fi
fi

# 2. 检查命令中的明文 Token
if [ "$TOOL" = "bash" ] && [ -n "$CMD" ]; then
    # 跨平台兼容：BSD grep 的 ERE 不支持 {20,} 单边界，改用 Python 做精确匹配 (R16 修复)
    TOKEN_HIT=$(echo "$CMD" | ${PYTHON_BIN:-python3} -c "
import sys, re
s = sys.stdin.read()
patterns = [
    r'sk-[a-zA-Z0-9]{20,}',
    r'sk-ant-[a-zA-Z0-9_-]{20,}',
    r'ghp_[a-zA-Z0-9]{36}',
    r'xoxb-[0-9]{10,}-[0-9]{10,}',
    r'Bearer\s+[A-Za-z0-9\-\._~+/]{20,}=*',
]
for p in patterns:
    if re.search(p, s):
        print('hit')
        break
" 2>/dev/null)
    if [ "$TOKEN_HIT" = "hit" ]; then
        flywheel_event "privacy_gate" "token_triggered" "P2" || true
        agentic_status danger \
            "Privacy Gate 触发" \
            "检测到在命令中包含明文 API Key 或 Token！这是严重的数据泄露风险。" \
            "请使用 /lx-varlock 脱敏代理安全执行，绝不能让明文凭据泄漏到 AI 上下文中。"
        printf '{"continue":false,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[Hook-Skill桥] privacy-gate → /lx-varlock: 命令中包含 API Key 明文，已被拦截。请用 /lx-varlock 脱敏代理安全执行此命令。"}}\n'
        exit 2
    fi
fi

echo '{"continue": true}'
exit 0
