#!/usr/bin/env bash
# snapshot-helper.sh — 非 git 环境的规范化快照工具
#
# 背景：
#   Carror OS 本身非 git 工作区，铁律 #4（Git 门禁）降级为 "sha256 + 人工批准"。
#   本脚本提供标准化的 before/after 快照 + diff，让证据门禁在非 git 环境仍可闭环。
#
# D1-3: shasum/sha256sum 跨平台兼容（macOS: shasum, Linux: sha256sum）
_SHA256() {
    if command -v sha256sum &>/dev/null; then
        sha256sum "$@"
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "$@"
    else
        echo "ERROR: no sha256sum or shasum found" >&2
        exit 99
    fi
}

# 用法：
#   bash .claude/scripts/snapshot-helper.sh before <file1> [file2 ...]
#     → 生成 .omc/state/snapshot-before-<TS>.txt
#   bash .claude/scripts/snapshot-helper.sh after  <file1> [file2 ...]
#     → 生成 .omc/state/snapshot-after-<TS>.txt （复用最近一次 before 的 TS）
#   bash .claude/scripts/snapshot-helper.sh diff
#     → 对比最近一组 before/after（sha256 变化 / 行数变化）
#   bash .claude/scripts/snapshot-helper.sh clean
#     → 清理 .omc/state/snapshot-*.txt
#
# 每份快照包含：路径 · sha256 · wc -l · mtime
# 输出格式稳定可 diff：每行 "sha256  lines  mtime  path"
#
# 退出码：0=成功；1=参数错误；2=文件不存在；3=无 before 快照可对比

set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 1

STATE_DIR=".omc/state"
mkdir -p "$STATE_DIR"

MODE="${1:-}"
shift 2>/dev/null || true

case "$MODE" in
    before)
        [ $# -eq 0 ] && { echo "usage: snapshot-helper.sh before <file>..."; exit 1; }
        TS=$(date +%Y%m%d-%H%M%S)
        OUT="$STATE_DIR/snapshot-before-$TS.txt"
        for f in "$@"; do
            if [ ! -f "$f" ]; then
                echo "missing  0  -  $f"
            else
                SHA=$(_SHA256 "$f" | awk '{print $1}')
                LINES=$(wc -l < "$f" | tr -d ' ')
                MTIME=$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%S' "$f" 2>/dev/null || stat -c '%y' "$f" 2>/dev/null | cut -d'.' -f1)
                echo "$SHA  $LINES  $MTIME  $f"
            fi
        done > "$OUT"
        # 记录"最近一次 before 的 TS"，after/diff 复用
        echo "$TS" > "$STATE_DIR/.snapshot-last-ts"
        echo "before snapshot → $OUT"
        cat "$OUT"
        ;;

    after)
        [ $# -eq 0 ] && { echo "usage: snapshot-helper.sh after <file>..."; exit 1; }
        [ -f "$STATE_DIR/.snapshot-last-ts" ] || { echo "error: no before snapshot"; exit 3; }
        TS=$(cat "$STATE_DIR/.snapshot-last-ts")
        OUT="$STATE_DIR/snapshot-after-$TS.txt"
        for f in "$@"; do
            if [ ! -f "$f" ]; then
                echo "missing  0  -  $f"
            else
                SHA=$(_SHA256 "$f" | awk '{print $1}')
                LINES=$(wc -l < "$f" | tr -d ' ')
                MTIME=$(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%S' "$f" 2>/dev/null || stat -c '%y' "$f" 2>/dev/null | cut -d'.' -f1)
                echo "$SHA  $LINES  $MTIME  $f"
            fi
        done > "$OUT"
        echo "after snapshot → $OUT"
        cat "$OUT"
        ;;

    diff)
        [ -f "$STATE_DIR/.snapshot-last-ts" ] || { echo "error: no snapshot pair"; exit 3; }
        TS=$(cat "$STATE_DIR/.snapshot-last-ts")
        BEFORE="$STATE_DIR/snapshot-before-$TS.txt"
        AFTER="$STATE_DIR/snapshot-after-$TS.txt"
        [ -f "$BEFORE" ] && [ -f "$AFTER" ] || { echo "error: $BEFORE or $AFTER missing"; exit 3; }
        echo "=== snapshot diff (TS=$TS) ==="
        ${PYTHON_BIN:-python3} - "$BEFORE" "$AFTER" <<'PYEOF'
import sys
def load(p):
    m = {}
    with open(p) as f:
        for line in f:
            parts = line.strip().split(None, 3)
            if len(parts) == 4:
                sha, lines, mtime, path = parts
                m[path] = (sha, lines, mtime)
    return m
b = load(sys.argv[1])
a = load(sys.argv[2])
paths = sorted(set(b) | set(a))
changed = unchanged = 0
for p in paths:
    bs, bl, _ = b.get(p, ('-', '-', '-'))
    as_, al, _ = a.get(p, ('-', '-', '-'))
    if bs == as_:
        print(f"  =  {p}  (sha unchanged, {al} lines)")
        unchanged += 1
    else:
        print(f"  ≠  {p}  sha {bs[:12]}→{as_[:12]}  lines {bl}→{al}")
        changed += 1
print(f"\n changed: {changed}  unchanged: {unchanged}  total: {len(paths)}")
PYEOF
        ;;

    clean)
        rm -f "$STATE_DIR"/snapshot-before-*.txt "$STATE_DIR"/snapshot-after-*.txt "$STATE_DIR/.snapshot-last-ts"
        echo "cleaned all snapshot files"
        ;;

    *)
        cat <<EOF
snapshot-helper.sh — 非 git 环境的规范化快照工具

用法：
  bash .claude/scripts/snapshot-helper.sh before <file>...   # 记录修改前状态
  bash .claude/scripts/snapshot-helper.sh after  <file>...   # 记录修改后状态
  bash .claude/scripts/snapshot-helper.sh diff               # 对比最近一组
  bash .claude/scripts/snapshot-helper.sh clean              # 清理快照

每份快照含：sha256 · 行数 · mtime · 路径
EOF
        exit 1
        ;;
esac
