#!/usr/bin/env bash
# common.sh — 门禁脚本共享库（FINAL.md v3.1）
# 所有门禁脚本 source 本文件。约定：
#   退出码 0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT（信任边界/权威链被碰）
#   每个门禁运行必须写 gate-result 信封（lib/gate_result.py），status 与退出码一致。

set -euo pipefail

GATES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATES_LIB="$GATES_DIR/lib"
CARROS_ROOT="$(cd "$GATES_DIR/../.." && pwd)"
CARROS_BASE="$CARROS_ROOT/.claude/scripts/carros_base.py"

# ---------- 参数 ----------
MANIFEST=""
PAGE_ID=""
NIGHT_DIR=""
TARGET_REPO="${TARGET_REPO:-}"

gates_parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --manifest) MANIFEST="$2"; shift 2;;
      --page-id) PAGE_ID="$2"; shift 2;;
      --night-dir) NIGHT_DIR="$2"; shift 2;;
      --target-repo) TARGET_REPO="$2"; shift 2;;
      *) echo "ERROR: 未知参数 $1" >&2; exit 2;;
    esac
  done
  [[ -n "$MANIFEST" ]] || { echo "ERROR: 需要 --manifest" >&2; exit 2; }
  [[ -f "$MANIFEST" ]] || { echo "ERROR: manifest 不存在: $MANIFEST" >&2; exit 2; }
  MANIFEST="$(cd "$(dirname "$MANIFEST")" && pwd)/$(basename "$MANIFEST")"
}

# ---------- 哈希（macOS/Linux 兼容，Rule 8） ----------
gates_sha256_file() { # $1=path → 输出 hex
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

gates_sha256_string() { # $1=string → 输出 hex
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
  else
    printf '%s' "$1" | sha256sum | awk '{print $1}'
  fi
}

gates_manifest_sha() { gates_sha256_file "$MANIFEST"; }

gates_code_sha() { # 目标 repo 当前 HEAD
  [[ -n "$TARGET_REPO" ]] || { echo "ERROR: TARGET_REPO 未设置" >&2; exit 2; }
  git -C "$TARGET_REPO" rev-parse HEAD
}

# ---------- manifest 读取 ----------
gates_mget() { # $1=dotted.path [--page] → 单值；缺失 exit 2（fail-closed）
  local path="$1" page="${2:-}"
  local args=(manifest-json --manifest "$MANIFEST" --get "$path")
  [[ -n "$page" ]] && args+=(--page-id "$page")
  python3 "$CARROS_BASE" "${args[@]}"
}

# ---------- control_plane_lock 自验（S1/GPT#3） ----------
# 重算 manifest control_plane_lock.entries 每个文件的 sha256 并比对。
# 任何不符/文件缺失 → exit 3 FAILED_INVARIANT。输出 digest（entries 规范串的 sha256）。
gates_verify_control_plane_lock() {
  python3 - "$MANIFEST" "$CARROS_ROOT" << 'PY'
import hashlib, json, sys
import yaml

manifest_path, root = sys.argv[1], sys.argv[2]
data = yaml.safe_load(open(manifest_path, encoding="utf-8"))
lock = (data or {}).get("control_plane_lock") or {}
entries = lock.get("entries") or []
if not entries:
    print("FAIL-CLOSED: control_plane_lock.entries 为空", file=sys.stderr)
    sys.exit(3)
canon = []
for e in entries:
    path, expect = e.get("path", ""), e.get("sha256", "")
    if not path or not expect:
        print(f"FAIL-CLOSED: entry 缺 path/sha256: {e}", file=sys.stderr)
        sys.exit(3)
    import os
    if path.endswith("#hooks"):
        # 伪条目：settings.json 的 hooks 段规范化哈希（生成器同款算法）
        real = os.path.join(root, path[: -len("#hooks")])
        if not os.path.isfile(real):
            print(f"FAILED_INVARIANT: 控制面文件缺失: {path}", file=sys.stderr)
            sys.exit(3)
        try:
            data = json.loads(open(real, encoding="utf-8").read())
            canon_hooks = json.dumps(data.get("hooks", {}), sort_keys=True, separators=(",", ":")).encode()
            h = hashlib.sha256(canon_hooks).hexdigest()
        except Exception as ex:
            print(f"FAILED_INVARIANT: hooks 段解析失败: {ex}", file=sys.stderr)
            sys.exit(3)
    else:
        real = os.path.join(root, path)
        if not os.path.isfile(real):
            print(f"FAILED_INVARIANT: 控制面文件缺失: {path}", file=sys.stderr)
            sys.exit(3)
        h = hashlib.sha256(open(real, "rb").read()).hexdigest()
    if h != expect:
        print(f"FAILED_INVARIANT: 控制面文件被改动: {path}", file=sys.stderr)
        sys.exit(3)
    canon.append(f"{path}:{h}")
digest = hashlib.sha256("\n".join(sorted(canon)).encode()).hexdigest()
print(digest)
PY
}

# ---------- gate-result 信封 ----------
# gates_write_result GATE_ID STATUS EXIT_CODE STARTED_AT [EVIDENCE_JSON] [ARGV_DIGEST]
# STATUS ∈ PASS|FAIL|ERROR；与 EXIT_CODE 一致性由 gate_result.py 强制。
# producer 自动取调用方脚本名（Grok §17a P0-3：信封必须可追溯到门禁脚本链）。
gates_write_result() {
  local gate_id="$1" status="$2" exit_code="$3" started_at="$4" evidence="${5:-[]}" argv_digest="${6:-}"
  local results_dir producer
  results_dir="$(gates_results_dir)"
  producer="$(basename "${BASH_SOURCE[1]:-unknown}")"
  local extra=(--producer "$producer")
  [[ -n "$argv_digest" ]] && extra+=(--argv-digest "$argv_digest")
  python3 "$GATES_LIB/gate_result.py" write \
    --out-dir "$results_dir" \
    --gate-id "$gate_id" \
    --status "$status" \
    --manifest-sha256 "$(gates_manifest_sha)" \
    --code-sha256 "$(gates_code_sha)" \
    --control-plane-digest "$GATES_CP_DIGEST" \
    --started-at "$started_at" \
    --process-exit-code "$exit_code" \
    --evidence "$evidence" \
    "${extra[@]}"
}

gates_results_dir() {
  [[ -n "$NIGHT_DIR" && -n "$PAGE_ID" ]] || { echo "ERROR: 需要 --night-dir/--page-id" >&2; exit 2; }
  python3 "$CARROS_BASE" gate-results-init --night-dir "$NIGHT_DIR" --page-id "$PAGE_ID"
}

# 门禁运行前置：自验控制面并设置 GATES_CP_DIGEST（所有脚本开头调用）
gates_preamble() {
  GATES_CP_DIGEST="$(gates_verify_control_plane_lock)" || {
    echo "FAILED_INVARIANT: control_plane_lock 自验失败" >&2
    exit 3
  }
  export GATES_CP_DIGEST
}

gates_now() { python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())"; }
