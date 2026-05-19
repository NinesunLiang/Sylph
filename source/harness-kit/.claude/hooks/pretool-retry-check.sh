#!/usr/bin/env bash
# pretool-retry-check.sh — PreToolUse — 阻断超过重试上限的 Bash 命令
# Role: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令
#
# 原理：
#   retry-budget.json 记录每个错误签名的重试次数。
#   当某个签名超过 MAX_RETRIES（默认 3），后续 Bash 调用被阻断。
#   避免 AI 在同一个错误上无限重试（C9 错误恢复）。
#
# 注意：直接读取 retry-budget.json，不调用 retry-budget.sh check
# （retry-budget.sh 存在 bash 退出码传播 bug）

source "$(dirname "$0")/harness_config.sh"
hc_enabled "retry_budget_check" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"

# Mode detection: ghost/goal 降级为 log+skip
_MODE=$(is_mode_active "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.omc/state")
if [ "$_MODE" != "normal" ]; then
    echo "[$_MODE] pretool-retry-check 已记录（模式降级，不阻断）" >&2
    echo '{"continue": true}'
    exit 0
fi

INPUT=$(cat)

# 仅检查 Bash 命令（重试只发生在命令执行失败时）
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // ""' 2>/dev/null)
else
    TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool', ''))
except:
    pass" 2>/dev/null)
fi
[ "$TOOL_NAME" != "Bash" ] && [ "$TOOL_NAME" != "bash" ] && { echo '{"continue": true}'; exit 0; }

# 直接读取 retry-budget.json 检查是否超过上限
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUDGET_FILE="$PROJECT_ROOT/.omc/state/retry-budget.json"

if [ -f "$BUDGET_FILE" ]; then
    EXCEEDED=$(python3 -c "
import json, sys
try:
    with open('$BUDGET_FILE') as f:
        d = json.load(f)
    sigs = d.get('signatures', {})
    max_r = 3
    exceeded = [(k, v.get('retry_count', 0)) for k, v in sigs.items() if v.get('retry_count', 0) >= max_r]
    if exceeded:
        for sig, cnt in exceeded:
            label = sigs[sig].get('label', sig)[:80]
            print(f'{sig[:40]} ({cnt} retries): {label}')
        sys.exit(2)
    else:
        sys.exit(0)
except Exception:
    sys.exit(0)
")
    PY_EXIT=$?
    if [ $PY_EXIT -eq 2 ] && [ -n "$EXCEEDED" ]; then
        if [ "$_MODE" != "normal" ]; then
            echo "[pretool-retry-check] 自主模式: 重置重试计数并继续" >&2
            echo '{"continue": true}'
            exit 0
        fi
        agentic_menu \
            "Retry Budget" \
            "存在超过重试上限的重复失败: ${EXCEEDED}" \
            "重置重试计数并重试" "清除错误签名计数，重新尝试" \
            "升级到 lx-task-spec" "启动结构化任务处理流程"
        flywheel_event "pretool_retry_check" "blocked" "P2" || true
        exit 0
    fi
fi

# ── E4 惯性执行诊断门禁 ──
# 当 retry_count >= 2（距硬阻断还有 1 次），扫描多个来源查找诊断关键词。
# 来源优先级: (a) 证据文件 (b) error-signals.jsonl 命令日志 (c) diagnosis.json 标记文件
# 若未找到诊断记录 → agentic_menu 阻断，要求先诊断再修复。
E4_STATE_DIR="$PROJECT_ROOT/.omc/state"
ERROR_SIGNALS_FILE="$E4_STATE_DIR/error-signals.jsonl"
DIAGNOSIS_FILE="$E4_STATE_DIR/diagnosis.json"

if [ -f "$BUDGET_FILE" ]; then
    E4_NEAR_LIMIT=$(python3 -c "
import json, sys, os
try:
    with open('$BUDGET_FILE') as f:
        d = json.load(f)
    sigs = d.get('signatures', {})
    near = [(k, v.get('retry_count', 0), v.get('label', k)[:80]) for k, v in sigs.items() if 2 <= v.get('retry_count', 0) < 3]
    if near:
        for sig, cnt, label in near:
            print(f'{sig[:40]} (count={cnt}): {label}')
        sys.exit(2)
    sys.exit(0)
except Exception:
    sys.exit(0)
")
    if [ $? -eq 2 ] && [ -n "$E4_NEAR_LIMIT" ]; then
        HAS_DIAGNOSIS=$(python3 -c "
import json, sys, os, re, glob
# E4 Layer 1: 结构化诊断检测 (>=3/5 字段)
diag_fields = {
    'root_cause': re.compile(r'root.cause[:=]\s*\S+', re.I),
    'repro': re.compile(r'(repro|复现|触发条件)[:=]\s*\S+', re.I),
    'underlying': re.compile(r'(underlying|底层原因|why.*fail)[:=]\s*\S+', re.I),
    'fix_approach': re.compile(r'(fix.approach|修复方式|approach)[:=]\s*\S+', re.I),
    'diff_prev': re.compile(r'(diff.*prev|direction.change|different|方向变更|新方向)[:=]\s*\S+', re.I),
}
kw = diag_fields  # backward-compat alias
found = 0

# Source A: scan recent evidence files in state dir
ev_files = sorted(glob.glob('$E4_STATE_DIR/.completion-evidence-*'), key=os.path.getmtime, reverse=True)[:5]
for ef in ev_files:
    try:
        with open(ef) as f:
            text = f.read(); sc = sum(1 for _, rx in diag_fields.items() if rx.search(text)); if sc >= 3:
                found += 1
    except: pass

# Source B: scan error-signals.jsonl last 100 lines
if os.path.exists('$ERROR_SIGNALS_FILE'):
    try:
        with open('$ERROR_SIGNALS_FILE') as f:
            lines = f.readlines()
        for line in lines[-100:]:
            try:
                rec = json.loads(line)
                text = (rec.get('message', '') or '') + ' ' + (rec.get('cmd', '') or ''); sc = sum(1 for _, rx in diag_fields.items() if rx.search(text)); if sc >= 3:
                    found += 1
            except: pass
    except: pass

# Source C: diagnosis marker file (recently created)
if os.path.exists('$DIAGNOSIS_FILE'):
    try:
        mtime = os.path.getmtime('$DIAGNOSIS_FILE')
        age = __import__('time').time() - mtime
        if age < 3600:  # within 1 hour
            with open('$DIAGNOSIS_FILE') as f:
                text = f.read(); sc = sum(1 for _, rx in diag_fields.items() if rx.search(text)); if sc >= 3:
                    found += 1
    except: pass

if found:
    print(f'found {found} diagnostic record(s) across sources')
    sys.exit(0)
else:
    sys.exit(2)
")
        if [ $? -eq 2 ]; then
            if [ "$_MODE" != "normal" ]; then
                echo "[pretool-retry-check] 自主模式: E4 诊断门禁跳过" >&2
            else
                flywheel_event "pretool_retry_check" "e4_gate_blocked" "P2" || true
                agentic_menu \
                    "E4 Inertia Gate" \
                    "重试接近上限，但未检测到诊断分析: ${E4_NEAR_LIMIT}
请先做根因分析(5-Why)并记录诊断结论，再重试修复。
提示: echo '{\"root_cause\":\"...\",\"direction\":\"...\"}' > .omc/state/diagnosis.json" \
                    "执行 5-Why 根因分析" "先完成诊断分析，再重新尝试修复" \
                    "强制继续（下次将硬阻断）" "跳过诊断检查，但需承担风险"
                exit 0
            fi
        fi
    fi
fi

# ── E5 Build Fail Gate (B3 增强) ──
BUILD_FAIL_GATE="$PROJECT_ROOT/.omc/state/build-fail-gate.json"
if [ -f "$BUILD_FAIL_GATE" ]; then
    E5_CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    t = json.load(sys.stdin)
    cmd = t.get('tool_input', {}).get('command', '') or ''
    print(cmd[:300])
except:
    pass" 2>/dev/null)

    # B3: 区分读诊断命令 vs 盲目重试命令
    IS_BUILD_CMD=false
    IS_READ_CMD=false
    if echo "$E5_CMD" | grep -qE '(go build|go test|npm (install|test|build)|make|cargo build|cargo test|pip install|poetry install|yarn|pnpm|compile|cmake)' 2>/dev/null; then
        IS_BUILD_CMD=true
    fi
    if echo "$E5_CMD" | grep -qiE '(cat|head|tail|less|more|Read|grep.*error|journalctl|dmesg|log|查看|检查|诊断|analyze|why.*fail|error.*show|build.*fail|test.*output)' 2>/dev/null; then
        IS_READ_CMD=true
    fi

    # 读取 build-fail-gate 详情
    BUILD_FAIL_STREAK=$(python3 -c "
import json, sys
try:
    d = json.load(open('$BUILD_FAIL_GATE'))
    print(d.get('streak', 0))
except:
    print(0)" 2>/dev/null)

    if [ "$IS_BUILD_CMD" = true ] && [ "$IS_READ_CMD" = false ]; then
        if [ "$_MODE" != "normal" ]; then
            echo "[pretool-retry-check] 自主模式: E5 Build Fail Gate active — streak=${BUILD_FAIL_STREAK}" >&2
        else
            agentic_menu \
                "E5 Build Fail Gate (B3)" \
                "构建已在${BUILD_FAIL_STREAK}次连续失败中。直接重试通常无效。
请先读取编译错误消息做根因分析，而非盲目重试。

可选操作:" \
                "先读取编译错误" "执行 cat/head/grep 查看错误日志" \
                "查看诊断记录" "检查之前的诊断记录和分析" \
                "强制重试" "跳过诊断，直接重试构建"
            exit 0
        fi
    elif [ "$IS_BUILD_CMD" = true ]; then
        echo "[pretool-retry-check] ✅ E5 Build Fail Gate — 当前为先读后修模式，放行" >&2
    fi
fi

echo '{"continue": true}'
exit 0
