#!/bin/bash

# merge-profile.sh — v5.3.0 base+diff 合并工具
# 用法：
#   bash .claude/profiles/merge-profile.sh go       # 合并 base+go
#   bash .claude/profiles/merge-profile.sh node      # 合并 base+node
#   bash .claude/profiles/merge-profile.sh python    # 合并 base+python
#   bash .claude/profiles/merge-profile.sh rust      # 合并 base+rust
#   bash .claude/profiles/merge-profile.sh go --dry-run  # 预览不写文件
#   bash .claude/profiles/merge-profile.sh --list    # 列出可用 profile
#
# 合并规则：
#   1. 从 base/harness.yaml 读取所有通用字段
#   2. 用 {lang}/harness.yaml 的字段覆盖（同名 section.key 以 diff 为准）
#   3. diff 中的 hooks_enabled 子键做"增量覆盖"（不替换整块，仅覆盖出现的键）
#   4. 输出合并后的完整 harness.yaml

set -eo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$SCRIPT_DIR/base/harness.yaml"
OUTPUT="${CLAUDE_DIR:-.claude}/harness.yaml"

# ── --list ────────────────────────────────────────────────────────
if [ "$1" = "--list" ]; then
    echo "可用 profile："
    for d in "$SCRIPT_DIR"/*/; do
        name=$(basename "$d")
        [[ "$name" == "base" ]] && continue
        [ -f "$d/harness.yaml" ] && echo "  $name"
    done
    exit 0
fi

LANG="${1:-}"
DRY_RUN=false
[ "$2" = "--dry-run" ] && DRY_RUN=true

# ── 参数校验 ──────────────────────────────────────────────────────
if [ -z "$LANG" ]; then
    echo -e "${RED}[ERROR]${NC} 请指定语言: go / node / python / rust"
    echo "  用法: bash .claude/profiles/merge-profile.sh <lang> [--dry-run]"
    exit 1
fi

DIFF="$SCRIPT_DIR/$LANG/harness.yaml"

if [ ! -f "$BASE" ]; then
    echo -e "${RED}[ERROR]${NC} base/harness.yaml 不存在: $BASE"
    exit 1
fi
if [ ! -f "$DIFF" ]; then
    echo -e "${RED}[ERROR]${NC} 未找到 profile: $DIFF"
    exit 1
fi

# ── Python3 合并核心 ──────────────────────────────────────────────
_MERGE_PY=$(mktemp /tmp/.merge_profile_py.XXXXXX) || { echo "创建临时文件失败"; exit 1; }

cat > "$_MERGE_PY" << 'PYEOF'
import sys

def parse_yaml_flat(path):
    """解析 YAML 为嵌套 dict（支持2层 + 列表）"""
    result = {}
    current_section = None
    current_list_key = None
    current_list = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n\r')
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if current_list_key and current_list:
                    if current_section not in result:
                        result[current_section] = {}
                    result[current_section][current_list_key] = current_list[:]
                    current_list_key, current_list = None, []
                continue
            indent = len(line) - len(line.lstrip())
            if stripped.startswith('- '):
                if current_list_key:
                    current_list.append(stripped[2:].strip().strip('"').strip("'"))
                continue
            if current_list_key and current_list:
                if current_section not in result:
                    result[current_section] = {}
                result[current_section][current_list_key] = current_list[:]
                current_list_key, current_list = None, []
            if ':' in stripped:
                colon = stripped.index(':')
                key = stripped[:colon].strip()
                val = stripped[colon+1:].strip()
                if val and val[0] in ('"', "'") and val[-1] == val[0]:
                    val = val[1:-1]
                if indent == 0:
                    if val:
                        result[key] = val
                    else:
                        current_section = key
                        if key not in result:
                            result[key] = {}
                elif indent > 0 and current_section:
                    if val:
                        result[current_section][key] = val
                    else:
                        current_list_key = key
                        current_list = []
        if current_list_key and current_list and current_section:
            result[current_section][current_list_key] = current_list[:]
    return result


def merge(base, diff):
    merged = {}
    for k, v in base.items():
        if isinstance(v, dict):
            merged[k] = dict(v)
        elif isinstance(v, list):
            merged[k] = list(v)
        else:
            merged[k] = v
    for k, v in diff.items():
        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = {**merged[k], **v}
        elif isinstance(v, list):
            merged[k] = list(v)
        else:
            merged[k] = v
    return merged


def val_to_yaml(v, indent=2):
    pad = ' ' * indent
    if isinstance(v, list):
        return '\n' + '\n'.join(f"{pad}- {item}" for item in v)
    if isinstance(v, bool):
        return 'true' if v else 'false'
    s = str(v)
    if any(c in s for c in ['#', ':', '{', '}', '[', ']', ',', '&', '*', '?', '|', '<', '>', '=', '!', '%', '@', '`']):
        return f'"{s}"'
    return s


base_data = parse_yaml_flat(sys.argv[1])
diff_data = parse_yaml_flat(sys.argv[2])
lang = sys.argv[3]
merged = merge(base_data, diff_data)

SECTION_ORDER = [
    'project', 'protected_files', 'architecture', 'workflow',
    'task_decomposition', 'knowledge', 'turn_counter', 'fuzzy_detection',
    'lsp_suggest', 'subagent_guard', 'completion_gate', 'bash_audit',
    'permission_gate', 'sublimation', 'correction_detector',
    'session_handoff', 'error_dna', 'coupling', 'hooks_enabled',
    'rule_anchor', 'build_validator',
]

lines = [
    f"# harness-kit harness.yaml — {lang} profile (base+diff merged)",
    f"# 由 merge-profile.sh 生成，源文件: profiles/base + profiles/{lang}",
    "# 手动编辑此文件的修改在下次 merge 时会被覆盖",
    "",
]

seen = set()
for section in SECTION_ORDER:
    if section not in merged:
        continue
    seen.add(section)
    v = merged[section]
    lines.append(f"{section}:")
    if isinstance(v, dict):
        for sk, sv in v.items():
            yv = val_to_yaml(sv)
            if yv.startswith('\n'):
                lines.append(f"  {sk}:{yv}")
            else:
                lines.append(f"  {sk}: {yv}")
    else:
        lines.append(f"  {val_to_yaml(v)}")
    lines.append("")

for section, v in merged.items():
    if section in seen:
        continue
    lines.append(f"{section}:")
    if isinstance(v, dict):
        for sk, sv in v.items():
            yv = val_to_yaml(sv)
            if yv.startswith('\n'):
                lines.append(f"  {sk}:{yv}")
            else:
                lines.append(f"  {sk}: {yv}")
    else:
        lines.append(f"  {val_to_yaml(v)}")
    lines.append("")

print('\n'.join(lines))
PYEOF

MERGED=$(python3 "$_MERGE_PY" "$BASE" "$DIFF" "$LANG")
rm -f "$_MERGE_PY"

# ── 输出 ──────────────────────────────────────────────────────────
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN]${NC} 合并结果（不写文件）："
    echo "---"
    echo "$MERGED"
    echo "---"
    LINES=$(echo "$MERGED" | wc -l | tr -d ' ')
    echo -e "${GREEN}[INFO]${NC} 合并后 $LINES 行（base 覆盖 + $LANG diff）"
else
    mkdir -p "$(dirname "$OUTPUT")"
    echo "$MERGED" > "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT" | tr -d ' ')
    echo -e "${GREEN}[OK]${NC} 已写入 $OUTPUT（$LINES 行，base + $LANG diff 合并）"
fi
