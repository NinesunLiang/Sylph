#!/usr/bin/env bash
# posttool-claim-audit.sh — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验
# 检测 AI 对文件内容的断言（file:line 引用 + 数值断言来源）是否基于真实读取
# Role: 铁律 #1 enforce — AI 不能编造没读过的代码事实 + 不能写无来源的数值断言

source "$(dirname "$0")/harness_config.sh"
hc_enabled "posttool_claim_audit" || { echo '{"continue": true}'; exit 0; }

# Mode detection: ghost/goal 降级为 warn-only（仍检测，但不硬阻断）
_MODE=$(is_mode_active "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.omc/state")
_AUTONOMOUS=false
if [ "$_MODE" != "normal" ]; then
    _AUTONOMOUS=true
fi

INPUT=$(cat)
TOOL_NAME="$1"

# 仅审计 Edit/Write — AI 输出断言的主要出口
case "$TOOL_NAME" in
    Edit|Write) ;;
    *) exit 0 ;;
esac

# 提取 file_path（工具输入）
if command -v jq &>/dev/null; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .args.filePath // empty' 2>/dev/null)
else
    FILE_PATH=$(echo "$INPUT" | ${PYTHON_BIN:-python3} -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('args', {}).get('filePath', data.get('tool_input', {}).get('file_path', '')))
except:
    pass" 2>/dev/null)
fi

# 无路径 → 放行（避免误杀）
[ -z "$FILE_PATH" ] && exit 0

# 提取文件绝对路径用于 read-tracker 比对
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
READ_LOG="$STATE_DIR/read-tracker.txt"

# 提取所有 file:line 引用（AGENTS.md:42, kernel.go:15, .claude/hooks/plan-gate.sh:15）
# 不再要求以 . 开头（之前漏掉了 AGENTS.md:42 等裸文件名引用）
# 注意: 即使没有 file:line 引用，G1 数值断言检查仍然必须执行（见下方）
CLAIMED_FILES=$(echo "$INPUT" | grep -oE '(\.?/)?[a-zA-Z0-9_./-]+\.[a-z]+:[0-9]+' | sed 's|^\./||' || true)

# 读取 read-tracker（可能跨轮次累积）
# 修复: read-tracker 不存在 → 视为零读取记录，所有 file:line 断言均不可信
read_files=""
_READ_TRACKER_EXISTS=true
if [ -f "$READ_LOG" ]; then
    read_files=$(cat "$READ_LOG")
else
    _READ_TRACKER_EXISTS=false
fi

# 检测 claim 文件是否在 read-tracker 中
CLAIMED_BASENAMES=$(echo "$CLAIMED_FILES" | sed 's|:.*||' | xargs -I{} basename {} 2>/dev/null | sort -u || true)
CLAIMED_DIRS=$(echo "$CLAIMED_FILES" | sed 's|:.*||' | xargs -I{} dirname {} 2>/dev/null | sort -u || true)

VIOLATIONS=""
while IFS= read -r claimed; do
    [ -z "$claimed" ] && continue

    # Strip line number suffix (:NNN) for path comparison
    claimed_path=$(echo "$claimed" | sed 's/:[0-9]*$//')

    # 检查1: read-tracker 中有完整路径匹配
    if echo "$read_files" | grep -qxF "$(realpath "./$claimed_path" 2>/dev/null || echo "$claimed_path")"; then
        continue
    fi

    # 检查2: basename 匹配（同一文件被多次 Read）
    if echo "$read_files" | grep -qF "/$(basename "$claimed_path")"; then
        continue
    fi

    # 检查3: dirname 下有同名文件被 Read（包级引用）
    set -f
    for dir in $CLAIMED_DIRS; do
        if echo "$read_files" | grep -qF "$dir/$(basename "$claimed_path")"; then
            set +f
            continue 2
        fi
    done
    set +f

    VIOLATIONS="${VIOLATIONS}⚠️ IRRELEVANT_CLAIM: ${claimed}\n"
done <<< "$CLAIMED_FILES"

# === G1 数值断言来源强制检查 ===
# 检测所有数值断言（百分比/倍数/增减量），强制要求来源引用
# 覆盖: 技术文档 + 营销文档 + 任何含数字断言的文件
# 这是铁律 #1(禁止编造) + #7(报告规范) + DG-29(regex设计级漏报) 的物化
G1_VIOLATIONS=""

# 扩展数值断言模式（中英文全覆盖）
# - 百分比: 95.6%, 14%-53%, 减少 50%, +16.64
# - 倍数: 1/50, 五十分之一, 10 倍, X倍
# - 增减量: 减少/提升/节省/降低 X% 或 +X
NUM_CLAIMS=$(echo "$INPUT" | grep -oE '[0-9]{1,3}\.[0-9]+%|[0-9]{1,3}%|通过率|[0-9]+%[-~][0-9]+%|减少\s*[0-9]+%?|提升\s*[0-9]+%?|节省\s*[0-9]+%?|降低\s*[0-9]+%?|1/[0-9]+|[0-9]+倍|[0-9]+/[0-9]+\s*(passed|通过|pass)|[0-9]+\s*(out of|of|项|个)\s*[0-9]+|\+[0-9]+\.[0-9]+|\+[0-9]+%|[0-9]+\s*分|得分\s*[0-9]+|[0-9]+\s*轮|[0-9]+\s*次|[0-9]{2,}\s*条' 2>/dev/null || true)

if [ -n "$NUM_CLAIMS" ]; then
    # 来源检测：以下任一形式均视为有效来源
    # - 行业标准: ASVS, OWASP, NIST, ISO, CWE, CVE, ATLAS
    # - 内部基准文件: benchmark-report, baseline, cross-platform-gain, pass-rate-summary
    # - 引用格式: path:line, [已验证: path:line], [内部自检], http(s)://URL
    # - 证据标签: [已测试: ...], VERIFIED:
    # - 跳过文件: skip-list.txt 中的路径不检查
    HAS_SOURCE=$(echo "$INPUT" | grep -ciE '(ASVS|OWASP|NIST|ISO|CWE|CVE|ATLAS|benchmark.report|benchmark-report|baseline|cross-platform-gain|pass-rate-summary|\[已验证|\[已测试|\[内部自检|VERIFIED|https?://|[a-zA-Z0-9_./-]+\.[a-z]+:[0-9]+|source:|ref:|來源|出处|根据.*统计|harness.smoke|production.verify|audit.hooks|auto.score|flywheel\.log|\d+/\d+\s*(passed|通过)|实测|实测数据)' 2>/dev/null || true)
    HAS_SOURCE="${HAS_SOURCE:-0}"

    if [ "$HAS_SOURCE" -eq 0 ]; then
        NUM_SAMPLE=$(echo "$NUM_CLAIMS" | head -5 | tr '\n' ' ')
        # 营销文档专用检测 — 真实感是营销的生命线
        if echo "$FILE_PATH" | grep -q 'docs/marketing/'; then
            G1_VIOLATIONS="⚠️ G1_MARKETING_CLAIM: 营销文档中的数值断言(${NUM_SAMPLE})无来源引用。\n  营销文案中的任何百分比/倍数/增减数字必须附带验证来源。失去真实感，99% 的前面努力都浪费了。\n  修复: 在数字后标注来源，如 '(20 轮实测数据，benchmark-report.md:291)' 或 '[内部自检，非行业标准]'。"
        else
            G1_VIOLATIONS="⚠️ G1_PSEUDO_INTEGRITY: 数值断言(${NUM_SAMPLE})无来源。请标注 [内部自检，非行业标准] 或附加来源 URL/file:line。"
        fi
    fi
fi

# === E6 自我矛盾检测 === (DG-96 v2: content_hash diff → intent-tracker 语义字段)
# v1 错误: 按 sig+content_hash 差异判定矛盾 → 100% 假阳性（每次编辑 content_hash 都变）
# v2 正确: 检查 intent-tracker 写入的 contradiction/revert_of 字段
# 矛盾定义: contradiction=true (intent-tracker 标记) 或 revert_of 非 null (编辑被显式回退)
E6_VIOLATIONS=""
CONTRADICTION_LOG="$STATE_DIR/contradiction-log.jsonl"
if [ -f "$CONTRADICTION_LOG" ] && [ -n "$FILE_PATH" ]; then
    E6_CHECK=$(${PYTHON_BIN:-python3} - "$CONTRADICTION_LOG" "$FILE_PATH" <<'E6EOF'
import json, sys

log_path = sys.argv[1]
target_file = sys.argv[2]

try:
    matching = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            if target_file in line:
                try:
                    matching.append(json.loads(line.strip()))
                except: pass

    if len(matching) < 2:
        sys.exit(0)

    # v2: 检查 intent-tracker 的语义字段，非 content_hash 差异
    contradicted = [r for r in matching if r.get('contradiction') == True]
    reverted = [r for r in matching if r.get('revert_of') is not None]
    # 高频编辑 + 多 sig 共存 = 潜在矛盾热点（warn-only, 不阻断）
    max_edits = max((r.get('edit_count', 0) for r in matching), default=0)
    unique_sigs = len(set(r.get('sig', '') for r in matching))

    if contradicted:
        print(f"[E6] CONTRADICTION: {target_file} — {len(contradicted)} 条标记为 contradiction=true")
        for c in contradicted[:2]:
            print(f"  · sig={c.get('sig','')[:16]}...")
    elif reverted:
        print(f"[E6] REVERT_DETECTED: {target_file} — {len(reverted)} 条 revert_of 非空")
        for r in reverted[:2]:
            print(f"  · revert_of={r.get('revert_of','')[:16]}...")
    elif max_edits > 10 and unique_sigs > 3:
        # 仅 warn: 高频多 sig 编辑 = 关注信号，不是硬矛盾
        print(f"[E6] HIGH_CHURN: {target_file} — {len(matching)} 条编辑, {unique_sigs} 个签名, 最高 {max_edits} 次 (非矛盾)")
except Exception:
    pass
E6EOF
    )
    if [ -n "$E6_CHECK" ]; then
        # v2: 仅 contradiction=true 或 revert 才标记为 E6 违规
        if echo "$E6_CHECK" | grep -q 'CONTRADICTION\|REVERT_DETECTED'; then
            E6_VIOLATIONS="⚠️ E6_SELF_CONTRADICTION: ${E6_CHECK}\n"
            flywheel_event "posttool_claim_audit" "e6_contradiction_detected" "P2" || true
        else
            # HIGH_CHURN 仅 stderr 通知, 不阻断
            echo "$E6_CHECK" >&2
        fi
    fi
fi

if [ -n "$VIOLATIONS" ] || [ -n "$G1_VIOLATIONS" ] || [ -n "$E6_VIOLATIONS" ]; then
    # ── 无 read-tracker 时，所有 file:line 断言均不可信 ──
    if [ "$_READ_TRACKER_EXISTS" = false ] && [ -n "$CLAIMED_FILES" ]; then
        VIOLATIONS="⚠️ NO_READ_HISTORY: zero files read this session — all file:line claims are unverifiable. Read the referenced file before claiming its content.\n${VIOLATIONS}"
    fi
    COMBINED="${VIOLATIONS}${G1_VIOLATIONS:+\n${G1_VIOLATIONS}}${E6_VIOLATIONS:+\n${E6_VIOLATIONS}}"

    # ── issue-triage 集成: 虚假断言 → 分流（Meta-Oracle ADVISORY: claim-audit 需进 triage）──
    TRIAGE_SUFFIX=""
    if [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
        TRIAGE_MSG=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook "posttool-claim-audit" "铁律#1虚假断言: ${COMBINED}" "P0" "{}" 2>/dev/null || echo "")
        [ -n "$TRIAGE_MSG" ] && TRIAGE_SUFFIX="\n${TRIAGE_MSG}"
    fi

    if [ "$_AUTONOMOUS" = true ]; then
        # 自主模式: 降级为 warn-only，不阻断但记录违规（退出报告可审计）
        printf '⚠️ [%s] [铁律#1+#7] AI 输出真实性违规 (warn-only):\n%s\n自主模式下降级为 warn — 违规已记录，退出报告时统一审查.%s' "$_MODE" "${COMBINED}" "${TRIAGE_SUFFIX}" | hc_emit_hook_json "PostToolUse" "true"
        flywheel_event "posttool_claim_audit" "blocked" "P2"  || true
        exit 0
    fi

    printf '⛔ [铁律#1+#7] AI 输出真实性违规:\n%s\n宪法: "禁止编造" + "任何数值断言必须有可验证来源"\n请修复以上违规项后重试.%s' "${COMBINED}" "${TRIAGE_SUFFIX}" | hc_emit_hook_json "PostToolUse" "false"
    flywheel_event "posttool_claim_audit" "blocked" "P2"  || true
exit 2
fi

exit 0
