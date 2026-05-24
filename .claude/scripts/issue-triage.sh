#!/usr/bin/env bash
# issue-triage.sh — 统一问题分流脚本
# Role: 发现问题 → 模式判定 → 分流决策 → 建议行动
#
# 用法:
#   source issue-triage.sh
#   triage_issue "问题描述" "发现来源" "优先级提示" [上下文JSON]
#
# 输出: JSON to stdout
# 副作用: a-mode 写 auto-optimizations.jsonl, b-mode 写 pending-decisions.md
#
# 集成点（4 个发现 hook）:
#   - error-dna.sh: 捕获到新错误模式时
#   - completion-gate.sh: 证据评分低/RCA 缺失时
#   - posttool-bash-audit.sh: 检测到危险模式(E4/C1/E3)时
#   - posttool-claim-audit.sh: 检测到虚假断言时

# Hook 不可失败原则：不使用 set -e / set -u，确保任何路径都 exit 0

# ─── 路径初始化（从脚本自身位置推导项目根）───
_IT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# _IT_SCRIPT_DIR = .claude/scripts → ../.. → project root
_IT_PROJECT_ROOT="$(cd "$_IT_SCRIPT_DIR/../.." && pwd)"
# 验证 project_root 合理性：应含 .claude/ 目录
if [ ! -d "$_IT_PROJECT_ROOT/.claude" ]; then
    # 回退: 从当前目录向上搜索含 .claude/ 的目录
    _search="$(pwd)"
    while [ "$_search" != "/" ]; do
        if [ -d "$_search/.claude" ]; then
            _IT_PROJECT_ROOT="$_search"
            break
        fi
        _search="$(dirname "$_search")"
    done
fi
_IT_STATE_DIR="$_IT_PROJECT_ROOT/.omc/state"
mkdir -p "$_IT_STATE_DIR" 2>/dev/null

# ─── 加载 harness_config（获取 is_mode_active）───
if [ -f "$_IT_PROJECT_ROOT/.claude/hooks/harness_config.sh" ]; then
    source "$_IT_PROJECT_ROOT/.claude/hooks/harness_config.sh"
fi

# ══════════════════════════════════════════════════════════════════
# 模式判定
# ══════════════════════════════════════════════════════════════════

# is_autonomous_mode — 判定当前是否为自主模式（a-mode）
# 返回: 0 (a-mode: ghost/goal/score/oracle) 或 1 (b-mode: normal)
# a-mode 定义: ghost mode / goal mode / score mode / Oracle review mode
is_autonomous_mode() {
    # 1) ghost/goal mode（通过 is_mode_active）
    local mode
    mode=$(is_mode_active "$_IT_STATE_DIR" 2>/dev/null || echo "normal")
    if [ "$mode" = "ghost" ] || [ "$mode" = "goal" ]; then
        return 0
    fi

    # 2) score mode 检测: 最近 2 分钟内有 auto-score-*.json 写入
    if [ -d "$_IT_STATE_DIR" ]; then
        local latest_score
        latest_score=$(find "$_IT_STATE_DIR" -maxdepth 1 -name 'auto-score-*.json' -mmin -2 2>/dev/null | head -1)
        if [ -n "$latest_score" ]; then
            return 0
        fi
    fi

    # 3) Oracle review mode 检测: 最近 5 分钟内有 oracle 相关活动
    #    检查 .omc/state/ 中 oracle-verdict 或 cross-verify-handoff 近期修改
    if [ -d "$_IT_STATE_DIR" ]; then
        local oracle_active
        oracle_active=$(find "$_IT_STATE_DIR" -maxdepth 1 \
            \( -name 'oracle-verdict*.json' -o -name 'meta-oracle-verdicts.md' -o -name 'cross-verify-handoff.md' \) \
            -mmin -5 2>/dev/null | head -1)
        if [ -n "$oracle_active" ]; then
            return 0
        fi
    fi

    return 1
}

# get_mode_label — 返回当前模式的可读标签
get_mode_label() {
    if is_autonomous_mode; then
        local mode
        mode=$(is_mode_active "$_IT_STATE_DIR" 2>/dev/null || echo "normal")
        case "$mode" in
            ghost) echo "ghost" ;;
            goal)  echo "goal" ;;
            normal)
                # 检查是否为 score/oracle 子模式
                if [ -n "$(find "$_IT_STATE_DIR" -maxdepth 1 -name 'auto-score-*.json' -mmin -2 2>/dev/null | head -1)" ]; then
                    echo "score"
                else
                    echo "oracle-review"
                fi
                ;;
            *) echo "autonomous" ;;
        esac
    else
        echo "normal"
    fi
}

# ══════════════════════════════════════════════════════════════════
# P0-P3 问题分类
# ══════════════════════════════════════════════════════════════════

# classify_priority "问题描述" "来源hook" "提示优先级"
# 输出: P0 | P1 | P2 | P3
classify_priority() {
    local desc="$1"
    local source="$2"
    local hint="${3:-}"

    # 如果调用方已明确提示优先级，优先采纳
    case "$hint" in
        P0|P1|P2|P3)
            # 但仍需验证：P0 必须真的是安全问题
            if [ "$hint" = "P0" ]; then
                if echo "$desc" | grep -qiE '(security|安全|漏洞|injection|注入|隐私|privacy|secret|token|password|credential|auth|绕过|bypass|escape)'; then
                    echo "P0"
                    return
                fi
                # 不匹配安全关键词，降级为 P1
                echo "P1"
                return
            fi
            echo "$hint"
            return
            ;;
    esac

    # ── 自动分类 ──
    # P0: 安全问题
    if echo "$desc" | grep -qiE '(security|安全|漏洞|injection|注入|隐私泄露|privacy|secret|token|password|credential|auth.*bypass|绕过.*门禁|escape.*detect)'; then
        echo "P0"
        return
    fi

    # P1: 功能缺陷 / 机制失效
    if echo "$desc" | grep -qiE '(bug|缺陷|失效|broken|not.working|regression|退化|block|阻断|误杀|false.positive|exit.*code|fail|crash|崩溃|机制.*失效|hook.*fail|门禁.*无效)'; then
        echo "P1"
        return
    fi

    # P3: 风格/命名（检测到则优先判定为 P3）
    if echo "$desc" | grep -qiE '(style|风格|命名|naming|rename|重命名|format.*style|indent|缩进|lint.*warn|whitespace|trailing|空白)'; then
        echo "P3"
        return
    fi

    # P2: 设计改进 / 可优化（默认）
    echo "P2"
}

# ══════════════════════════════════════════════════════════════════
# 分流决策矩阵
# ══════════════════════════════════════════════════════════════════

# dispatch_action "mode" "priority"
# 输出: auto_fix | auto_optimize | skip | block_and_report | record_and_submit | record_todo
#
# 决策矩阵:
#           │ P0 (安全)      │ P1 (功能缺陷)   │ P2 (设计改进)    │ P3 (风格/命名)
# ──────────┼────────────────┼─────────────────┼─────────────────┼────────────────
# a-mode    │ auto_fix       │ auto_fix        │ auto_optimize   │ skip
# b-mode    │ block+report   │ record+submit   │ record+suggest  │ record_todo
dispatch_action() {
    local mode="$1"
    local priority="$2"

    if [ "$mode" = "autonomous" ]; then
        case "$priority" in
            P0) echo "auto_fix" ;;
            P1) echo "auto_fix" ;;
            P2) echo "auto_optimize" ;;
            P3) echo "skip" ;;
            *)  echo "auto_optimize" ;;
        esac
    else
        case "$priority" in
            P0) echo "block_and_report" ;;
            P1) echo "record_and_submit" ;;
            P2) echo "record_and_submit" ;;
            P3) echo "record_todo" ;;
            *)  echo "record_and_submit" ;;
        esac
    fi
}

# ══════════════════════════════════════════════════════════════════
# 核心分流函数
# ══════════════════════════════════════════════════════════════════

# triage_issue "问题描述" "发现来源" "优先级提示" ["额外上下文JSON"]
# 输出 JSON 到 stdout
# 副作用: a-mode → auto-optimizations.jsonl, b-mode → pending-decisions.md
triage_issue() {
    local desc="$1"
    local source="${2:-unknown}"
    local hint="${3:-}"
    local context="${4:-{}}"

    [ -z "$desc" ] && { echo '{"error": "empty description"}'; return 1; }

    local mode_label priority action now_ts now_iso
    mode_label=$(get_mode_label)

    if is_autonomous_mode; then
        mode_label="${mode_label:-autonomous}"
        priority=$(classify_priority "$desc" "$source" "$hint")
        action=$(dispatch_action "autonomous" "$priority")
    else
        mode_label="normal"
        priority=$(classify_priority "$desc" "$source" "$hint")
        action=$(dispatch_action "normal" "$priority")
    fi

    now_ts=$(date +%s 2>/dev/null || echo 0)
    now_iso=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")

    # ── 生成建议文本 ──
    local suggestion=""
    case "$action" in
        auto_fix)
            suggestion="[a-mode/$priority] 自主修复: $desc（max 3 轮 → Oracle 验证 → 记录）"
            ;;
        auto_optimize)
            suggestion="[a-mode/$priority] 评估后自主优化: $desc"
            ;;
        skip)
            suggestion="[a-mode/$priority] 范围冻结 — 跳过: $desc"
            ;;
        block_and_report)
            suggestion="[b-mode/$priority] 立即阻断 + 报告用户: $desc"
            ;;
        record_and_submit)
            suggestion="[b-mode/$priority] 结构化记录 → 提交用户决策: $desc"
            ;;
        record_todo)
            suggestion="[b-mode/$priority] 记录 TODO，不主动提示: $desc"
            ;;
        *)
            suggestion="[分流] $desc"
            ;;
    esac

    # ── 统一导出 env vars（供所有 python3 子进程使用，防 shell 注入）──
    export _IT_DESC="$desc" _IT_NOW_TS="$now_ts" _IT_NOW_ISO="$now_iso"
    export _IT_MODE="$mode_label" _IT_PRIORITY="$priority" _IT_ACTION="$action"
    export _IT_SOURCE="$source" _IT_CONTEXT="$context" _IT_SUGGESTION="$suggestion"
    export _IT_STATE_DIR="$_IT_STATE_DIR"

    # ── 副作用: a-mode 写入 auto-optimizations.jsonl ──
    if is_autonomous_mode; then
        local opt_file="$_IT_STATE_DIR/auto-optimizations.jsonl"
        ${PYTHON_BIN:-python3} -c "
import json, os
desc = os.environ.get('_IT_DESC', '')
ctx_str = os.environ.get('_IT_CONTEXT', '{}')
try:
    ctx = json.loads(ctx_str) if ctx_str else {}
except:
    ctx = {}
record = {
    'ts': int(os.environ.get('_IT_NOW_TS', '0')),
    'ts_iso': os.environ.get('_IT_NOW_ISO', ''),
    'mode': os.environ.get('_IT_MODE', ''),
    'priority': os.environ.get('_IT_PRIORITY', ''),
    'action': os.environ.get('_IT_ACTION', ''),
    'source': os.environ.get('_IT_SOURCE', ''),
    'desc': desc,
    'context': ctx
}
opt_file = os.environ.get('_IT_STATE_DIR', '') + '/auto-optimizations.jsonl'
with open(opt_file, 'a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
" 2>/dev/null || true
    fi

    # ── 副作用: b-mode 写入 pending-triage.md（独立文件，不与 lx-oma-gov 的 pending-decisions.md 冲突）──
    if ! is_autonomous_mode && [ "$action" != "skip" ]; then
        local pending_file="$_IT_STATE_DIR/pending-triage.md"
        if [ ! -f "$pending_file" ]; then
            cat > "$pending_file" <<'PENDING_HEADER'
# 待分流决策清单（issue-triage）

> 自动生成于 AI 发现但非自主模式下的问题。
> SessionStart 时由 inject-project-knowledge.sh 注入提醒。
> 用户决策后删除对应条目，或整个文件 `rm -f .omc/state/pending-triage.md` 清除全部。
> 注意: 此文件与 lx-oma-gov 的 pending-decisions.md 独立，不会冲突。

<!-- issue-triage: pending decisions marker -->

PENDING_HEADER
        fi

        # 追加待决策项（使用临时文件避免转义问题）
        local entry_tmp="${_IT_STATE_DIR}/.triage-entry-$$.md"
        cat > "$entry_tmp" <<ENTRY_EOF
### [$now_iso] [$priority] 来源: $source
- **问题**: $desc
- **建议行动**: $suggestion
- **上下文**: $context

ENTRY_EOF
        export _IT_PEND_FILE="$pending_file" _IT_ENTRY_TMP="$entry_tmp"
        ${PYTHON_BIN:-python3} -c "
import os, re, hashlib, time
pf = os.environ.get('_IT_PEND_FILE', '')
entry_path = os.environ.get('_IT_ENTRY_TMP', '')
source = os.environ.get('_IT_SOURCE', '')
desc = os.environ.get('_IT_DESC', '')
now_ts = int(os.environ.get('_IT_NOW_TS', '0'))
try:
    with open(entry_path, 'r') as f:
        entry_content = f.read()
    # Dedup: extract signature from desc (first 100 chars after stripping error signatures)
    sig_text = desc[:100]
    dedup_key = hashlib.md5((source + '::' + sig_text).encode()).hexdigest()
    with open(pf, 'r') as f:
        content = f.read()
    # Check if same dedup key exists within 24h
    existing = re.findall(r'### \[([^\]]+)\].*?来源: (\S+).*?dedup_key: ([a-f0-9]+)', content, re.DOTALL)
    should_skip = False
    for ts_str, src, key in existing:
        if key == dedup_key:
            try:
                from datetime import datetime
                entry_ts = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%SZ').timestamp()
                if now_ts - entry_ts < 86400:  # 24h
                    should_skip = True
                    break
            except:
                pass
    if should_skip:
        pass  # skip duplicate
    else:
        # Append with dedup key embedded for future dedup
        lines = content.splitlines(keepends=True)
        new_lines = []
        marker = '<!-- issue-triage: pending decisions marker -->'
        for line in lines:
            new_lines.append(line)
            if marker in line:
                new_lines.append('\n')
                # Inject dedup_key into the context field for future dedup
                entry_with_key = entry_content.rstrip() + '\n- **dedup_key**: ' + dedup_key + '\n\n'
                new_lines.append(entry_with_key)
        with open(pf, 'w') as f:
            f.writelines(new_lines)
except Exception:
    pass
" 2>/dev/null || true
        rm -f "$entry_tmp" 2>/dev/null
    fi

    # ── 输出 JSON 结果（env vars 已在函数开头统一导出，防 shell 注入）──
    ${PYTHON_BIN:-python3} -c "
import json, os
result = {
    'mode': os.environ.get('_IT_MODE', ''),
    'priority': os.environ.get('_IT_PRIORITY', ''),
    'action': os.environ.get('_IT_ACTION', ''),
    'suggestion': os.environ.get('_IT_SUGGESTION', ''),
    'source': os.environ.get('_IT_SOURCE', ''),
    'ts': int(os.environ.get('_IT_NOW_TS', '0'))
}
print(json.dumps(result, ensure_ascii=False))
"
    return 0
}

# ══════════════════════════════════════════════════════════════════
# Hook 集成辅助函数
# ══════════════════════════════════════════════════════════════════

# triage_for_hook "hook_name" "问题描述" "优先级提示" ["上下文JSON"]
# 对 hook 友好的封装: 输出 additionalContext 格式的 JSON
triage_for_hook() {
    local hook_name="$1"
    local desc="$2"
    local hint="${3:-}"
    local context="${4:-{}}"

    local result
    result=$(triage_issue "$desc" "$hook_name" "$hint" "$context" 2>/dev/null || echo '{}')

    local action
    action=$(echo "$result" | ${PYTHON_BIN:-python3} -c "import json,sys; d=json.load(sys.stdin); print(d.get('action',''))" 2>/dev/null || echo "")

    local suggestion
    suggestion=$(echo "$result" | ${PYTHON_BIN:-python3} -c "import json,sys; d=json.load(sys.stdin); print(d.get('suggestion',''))" 2>/dev/null || echo "")

    # 返回 additionalContext 格式，让 hook 可以通过 printf 输出
    # P0 + b-mode → 路由到 [Hook-Skill桥] 格式
    local priority
    priority=$(echo "$result" | ${PYTHON_BIN:-python3} -c "import json,sys; d=json.load(sys.stdin); print(d.get('priority',''))" 2>/dev/null || echo "")

    if [ "$action" = "auto_fix" ] || [ "$action" = "auto_optimize" ]; then
        echo "[issue-triage] a-mode/${priority} → ${action}: ${suggestion}"
    elif [ "$action" = "block_and_report" ]; then
        echo "[issue-triage] ⚠️ b-mode/${priority} → ${action}: ${suggestion} | [Hook-Skill桥] 安全问题需用户立即处理 → 检查 pending-decisions.md"
    elif [ "$action" = "skip" ]; then
        echo "[issue-triage] a-mode/${priority} → skipped (范围冻结)"
    else
        echo "[issue-triage] b-mode/${priority} → ${action}: ${suggestion}"
    fi
}

# ══════════════════════════════════════════════════════════════════
# CLI 入口（用于直接调用或测试）
# ══════════════════════════════════════════════════════════════════

if [ "${1:-}" = "--self-test" ]; then
    echo "=== issue-triage.sh self-test ==="
    echo ""
    echo "Mode: $(get_mode_label)"
    echo "Autonomous: $(is_autonomous_mode && echo 'YES' || echo 'NO')"
    echo ""
    echo "--- Test 1: P0 security issue ---"
    triage_issue "security vulnerability in permission-gate: command injection via cache" "test" "P0"
    echo ""
    echo "--- Test 2: P1 functional bug ---"
    triage_issue "completion-gate quality scoring returns wrong values for edge cases" "test" "P1"
    echo ""
    echo "--- Test 3: P2 design improvement ---"
    triage_issue "posttool-bash-audit E4 detection could use regex optimization" "test" "P2"
    echo ""
    echo "--- Test 4: P3 style issue ---"
    triage_issue "variable naming inconsistency in harness_config.sh" "test" "P3"
    echo ""
    echo "=== self-test complete ==="
    exit 0
fi

# 直接调用（非 source）:
#   bash issue-triage.sh "问题描述" "来源" "优先级"
if [ "${BASH_SOURCE[0]}" = "$0" ] && [ $# -ge 1 ]; then
    triage_issue "${1:-}" "${2:-unknown}" "${3:-}" "${4:-{}}"
fi
