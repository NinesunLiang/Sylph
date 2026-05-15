#!/usr/bin/env bash
# privacy-gate.sh — PreToolUse:Bash|Read|Grep — 防止隐私数据泄露（DLP 门禁）
# Role: 防止隐私数据泄露（DLP 门禁）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "privacy_gate" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"

# Mode detection: ghost/goal 降级为 log+skip
_MODE=$(is_mode_active "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.omc/state")
if [ "$_MODE" != "normal" ]; then
    echo "[$_MODE] privacy-gate 已记录（模式降级，不阻断）" >&2
    echo '{"continue": true}'
    exit 0
fi

INPUT=$(cat)

if command -v jq &>/dev/null; then
    TOOL=$(echo "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
    PATTERN=$(echo "$INPUT" | jq -r '.tool_input.pattern // empty' 2>/dev/null)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
    # 极简回退解析
    TOOL=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    [ -z "$TOOL" ] && TOOL=$(echo "$INPUT" | grep -o '"tool"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    PATTERN=$(echo "$INPUT" | grep -o '"pattern"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    CMD=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
fi

# 统一小写化以兼容 Claude Code 的 PascalCase 工具名 (R16)
TOOL=$(echo "$TOOL" | tr '[:upper:]' '[:lower:]')

# 1. 检查读取/搜索的文件名
CHECK_PATH="$FILE_PATH$PATTERN"
if [ -n "$CHECK_PATH" ]; then
    if echo "$CHECK_PATH" | grep -iE '\.env|\.pem|\.key|\.p12|\.pfx|\.jks|id_rsa|credentials\.(json|ya?ml)|secret[es]?\.ya?ml|auth\.json|kubeconfig' > /dev/null; then
        echo "$(date +%Y-%m-%d),privacy_gate_triggered,P0,carror-os" >> "$HOME/.claude/flywheel.log"
        agentic_status danger \
            "Privacy Gate 触发" \
            "禁止直接读取包含配置、凭据或密钥的敏感文件（${CHECK_PATH}）。" \
            "请通过本地环境变量注入，或安装增强版 (lx-skills) 启用 lx-varlock 脱敏代理进行安全读取。绝不能让明文泄漏到 AI 上下文中。"
        exit 2
    fi
fi

# 2. 检查命令中的明文 Token
if [ "$TOOL" = "bash" ] && [ -n "$CMD" ]; then
    # 跨平台兼容：BSD grep 的 ERE 不支持 {20,} 单边界，改用 Python 做精确匹配 (R16 修复)
    TOKEN_HIT=$(echo "$CMD" | python3 -c "
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
        echo "$(date +%Y-%m-%d),privacy_gate_token_triggered,P0,carror-os" >> "$HOME/.claude/flywheel.log"
        agentic_status danger \
            "Privacy Gate 触发" \
            "检测到在命令中包含明文 API Key 或 Token！这是严重的数据泄露风险。" \
            "请立即停止并在独立终端配置 varlock 后安全执行。绝不能让明文泄漏到 AI 上下文中。"
        exit 2
    fi
fi

echo '{"continue": true}'
exit 0
