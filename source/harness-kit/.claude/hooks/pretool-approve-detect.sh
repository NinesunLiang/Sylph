#!/usr/bin/env bash
# pretool-approve-detect.sh — UserPromptSubmit — 检测 approve<token> 格式
# Role: 拦截用户输入中的 approve<token> → 写入对应的 approved 文件 → 解锁危险操作
# 哲学 #5 (以人为本): 支持多 token 空格分隔，一次输入解锁全部待审批门禁
# 哲学 #6 (0信任): 验证每个 token 必须与对应的 required 文件匹配

source "$(dirname "$0")/harness_config.sh"
hc_enabled "approve_detect" || exit 0
set -f  # R24: 防御 glob 污染

INPUT=$(cat)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# ── 解析输入 ──────────────────────────────
# 支持: approve<token1> <token2> ...  或  deny<token>
IS_DENY=false
TOKENS=()

# 去掉开头的 approve 或 deny
if echo "$INPUT" | grep -qE '^approve([[:space:]]|$)'; then
    TOKENS_RAW=$(echo "$INPUT" | sed -E 's/^approve[[:space:]]*//')
    for tok in $TOKENS_RAW; do
        CLEAN=$(echo "$tok" | tr -cd 'a-zA-Z0-9')
        [ ${#CLEAN} -ge 6 ] && [ ${#CLEAN} -le 16 ] && TOKENS+=("$CLEAN")
    done
elif echo "$INPUT" | grep -qE '^deny([[:space:]]|$)'; then
    IS_DENY=true
    TOKENS_RAW=$(echo "$INPUT" | sed -E 's/^deny[[:space:]]*//')
    for tok in $TOKENS_RAW; do
        CLEAN=$(echo "$tok" | tr -cd 'a-zA-Z0-9')
        [ ${#CLEAN} -ge 6 ] && [ ${#CLEAN} -le 16 ] && TOKENS+=("$CLEAN")
    done
else
    exit 0
fi

[ ${#TOKENS[@]} -eq 0 ] && exit 0

# ── 门禁文件列表 ──────────────────────────
# 格式: "显示名:required文件:approved文件"
GATES=(
    "permission-gate:permission-required:permission-approved"
    "sensitive-edit:sensitive-required:sensitive-approved"
    "oracle-gate:oracle-gate-required:oracle-gate-approved"
)

# ── 处理 ──────────────────────────────────
MATCHED=0
FAILED=0
DENIED=0

for GATE in "${GATES[@]}"; do
    IFS=':' read -r GATE_NAME REQ_FILE APPR_FILE <<< "$GATE"
    REQ_PATH="$STATE_DIR/$REQ_FILE"
    APPR_PATH="$STATE_DIR/$APPR_FILE"

    [ ! -f "$REQ_PATH" ] && continue

    EXPECTED=$(cat "$REQ_PATH" 2>/dev/null | tr -d '\n')

    if [ "$IS_DENY" = true ]; then
        # deny: 删除所有 pending 的 required 文件
        for token in "${TOKENS[@]}"; do
            if [ "$token" = "$EXPECTED" ]; then
                rm -f "$REQ_PATH"
                echo "[Approve] 🚫 ${GATE_NAME} 已拒绝。验证码已作废。" >&2
                DENIED=$((DENIED + 1))
                break
            fi
        done
        continue
    fi

    # approve: 匹配 token
    for token in "${TOKENS[@]}"; do
        if [ "$token" = "$EXPECTED" ]; then
            echo "$token" > "$APPR_PATH"
            echo "[Approve] ✅ ${GATE_NAME} 已批准！5 分钟内同签名命令自动放行。" >&2
            MATCHED=$((MATCHED + 1))
            break
        fi
    done

    # token 都不匹配
    if [ ! -f "$APPR_PATH" ] || [ "$(cat "$APPR_PATH" 2>/dev/null | tr -d '\n')" != "$EXPECTED" ]; then
        FAILED=$((FAILED + 1))
    fi
done

# ── 报告 ──────────────────────────────────
if [ "$IS_DENY" = true ]; then
    echo "[Approve] 已拒绝 ${DENIED} 个待审批操作。" >&2
    echo "denied"
elif [ $MATCHED -gt 0 ] && [ $FAILED -eq 0 ]; then
    echo "[Approve] 全部 ${MATCHED} 个门禁已批准。" >&2
    echo "Continue"
elif [ $MATCHED -gt 0 ]; then
    echo "[Approve] ${MATCHED} 个已批准，${FAILED} 个 token 不匹配。请检查验证码。" >&2
else
    echo "[Approve] ❌ 无匹配的验证码。待审批的验证码：$(ls $STATE_DIR/*-required 2>/dev/null | while read f; do echo -n "$(basename $f | sed 's/-required//'): $(cat $f | tr -d '\n') "; done)" >&2
fi

exit 0
