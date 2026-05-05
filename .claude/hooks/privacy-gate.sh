#!/usr/bin/env bash

# harness-kit:managed v1.0.0

# privacy-gate.sh — PreToolUse:Read / Grep / Bash Hook

# 功能：防止隐私数据泄露 (DLP)

# - 拦截读取 .env, *.pem, id_rsa 等敏感文件

# - 拦截命令中明文出现的 Token (如 sk-ant-*, ghp_*)

# 退出码 2 = 阻断（涉及隐私违规）


source "$(dirname "$0")/harness_config.sh"
hc_enabled "privacy_gate" || exit 0
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
    if echo "$CHECK_PATH" | grep -iE '\.env|\.pem|\.key|id_rsa|credentials\.json|secret\.ya?ml|auth\.json' > /dev/null; then
        echo "👉 Re-insp-Kernel-Design:1.1-PrivacyGate" >&2
        echo "🚫 [Privacy Gate 触发] 禁止直接读取包含配置、凭据或密钥的敏感文件（$CHECK_PATH）。" >&2
        echo "请通过本地环境变量注入，或安装增强版 (lx-skills) 启用 \`lx-varlock\` 脱敏代理进行安全读取。绝不能让明文泄漏到 AI 上下文中。" >&2
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
        echo "🚫 [Privacy Gate 触发] 检测到在命令中包含了明文 API Key 或 Token！这是严重的数据泄露风险。请立即停止并在独立终端配置 varlock，然后使用 \`python3 .claude/skills/lx-varlock/scripts/varlock.py run \"命令 {你的变量名}\"\` 来安全执行。" >&2
        exit 2
    fi
fi

exit 0
