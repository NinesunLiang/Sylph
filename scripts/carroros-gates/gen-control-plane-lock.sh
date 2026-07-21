#!/usr/bin/env bash
# gen-control-plane-lock.sh — control_plane_lock 生成器（FINAL.md v3.1 §16 / GPT#3）
# 覆盖传递依赖：七脚本 + lib + smoke + assertion-catalog.yaml + 夜跑 hook +
# hook-launcher + carros_base.py + settings.json#hooks 段（规范化哈希，不含密钥）。
# 用法:
#   gen-control-plane-lock.sh                      → 输出 YAML entries 到 stdout
#   gen-control-plane-lock.sh --manifest M --write → 写回 manifest control_plane_lock.entries
# Phase 0 运行；写回后 manifest 需重新签署（signoff 哈希会变）。

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARROS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

MANIFEST=""
WRITE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) MANIFEST="$2"; shift 2;;
    --write) WRITE=1; shift;;
    *) echo "ERROR: 未知参数 $1" >&2; exit 2;;
  esac
done

python3 - "$CARROS_ROOT" "$MANIFEST" "$WRITE" << 'PY'
import hashlib, json, sys
from pathlib import Path

import yaml

root, manifest_path, write = Path(sys.argv[1]), sys.argv[2], sys.argv[3] == "1"

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())

files = []
# 1. 门禁脚本全套（含 lib/smoke/catalog/templates）
gates = root / "scripts" / "carroros-gates"
for p in sorted(gates.rglob("*")):
    if p.is_file() and p.suffix in (".sh", ".py", ".yaml", ".yml"):
        files.append(p)
# 2. 夜跑 hook + launcher
for rel in (".claude/hooks/carroros-night-deny.py", ".claude/hooks/hook-launcher.sh"):
    p = root / rel
    if p.is_file():
        files.append(p)
# 3. carros_base.py（真实路径，非 symlink）
cb = root / ".omc" / "scripts" / "carros_base.py"
if cb.is_file():
    files.append(cb)

entries = []
seen = set()
for p in files:
    rel = p.relative_to(root).as_posix()
    if rel in seen:
        continue
    seen.add(rel)
    entries.append({"path": rel, "sha256": sha256_file(p)})

# 4. settings.json 的 hooks 段（规范化 JSON 哈希；不读/不含 env 密钥）
settings = root / ".claude" / "settings.json"
if settings.is_file():
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})
        canon = json.dumps(hooks, sort_keys=True, separators=(",", ":")).encode()
        entries.append({"path": ".claude/settings.json#hooks", "sha256": sha256_bytes(canon)})
    except Exception as e:
        print(f"ERROR: settings.json hooks 段解析失败: {e}", file=sys.stderr)
        sys.exit(2)

if not write:
    print(yaml.safe_dump({"algorithm": "sha256", "entries": entries}, sort_keys=False, allow_unicode=True))
    sys.exit(0)

if not manifest_path:
    print("ERROR: --write 需要 --manifest", file=sys.stderr)
    sys.exit(2)
mp = Path(manifest_path)
data = yaml.safe_load(mp.read_text(encoding="utf-8"))
data["control_plane_lock"] = {"algorithm": "sha256", "entries": entries}
mp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"control_plane_lock 已写入 {mp}（{len(entries)} 项）——manifest 已变，需重新生成 signoff")
PY
