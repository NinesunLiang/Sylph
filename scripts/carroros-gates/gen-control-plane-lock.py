#!/usr/bin/env python3
"""
gen-control-plane-lock.py — control_plane_lock 生成器 (v6.0, .sh → .py 迁移)
覆盖传递依赖：脚本 + lib + smoke + assertion-catalog.yaml + 夜跑 hook +
hook-launcher + carros_base.py + settings.json#hooks 段（规范化哈希，不含密钥）。
用法:
  python3 gen-control-plane-lock.py                        → 输出 YAML entries 到 stdout
  python3 gen-control-plane-lock.py --manifest M --write   → 写回 manifest
Phase 0 运行；写回后 manifest 需重新签署。
"""

import hashlib
import json
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CARROS_ROOT = SCRIPT_DIR.parent.parent

MANIFEST = ""
WRITE = False
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "--manifest" and i + 1 < len(args):
        MANIFEST = args[i + 1]
        i += 2
    elif args[i] == "--write":
        WRITE = True
        i += 1
    else:
        print(f"ERROR: 未知参数 {args[i]}", file=sys.stderr)
        sys.exit(2)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


files = []
# 1. 门禁脚本全套（含 lib/smoke/catalog/templates）
gates = CARROS_ROOT / "scripts" / "carroros-gates"
for p in sorted(gates.rglob("*")):
    if p.is_file() and p.suffix in (".sh", ".py", ".yaml", ".yml"):
        files.append(p)

# 2. 夜跑 hook + launcher
for rel in (".claude/hooks/carroros-night-deny.py", ".claude/hooks/hook-launcher.py"):
    p = CARROS_ROOT / rel
    if p.is_file():
        files.append(p)

# 3. carros_base.py
cb = CARROS_ROOT / ".omc" / "scripts" / "carros_base.py"
if cb.is_file():
    files.append(cb)

entries = []
seen = set()
for p in files:
    rel = p.relative_to(CARROS_ROOT).as_posix()
    if rel in seen:
        continue
    seen.add(rel)
    entries.append({"path": rel, "sha256": sha256_file(p)})

# 4. settings.json 的 hooks 段
settings = CARROS_ROOT / ".claude" / "settings.json"
if settings.is_file():
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})
        canon = json.dumps(hooks, sort_keys=True, separators=(",", ":")).encode()
        entries.append({"path": ".claude/settings.json#hooks", "sha256": sha256_bytes(canon)})
    except Exception as e:
        print(f"ERROR: settings.json hooks 段解析失败: {e}", file=sys.stderr)
        sys.exit(2)

if not WRITE:
    print(yaml.safe_dump({"algorithm": "sha256", "entries": entries},
                         sort_keys=False, allow_unicode=True))
    sys.exit(0)

if not MANIFEST:
    print("ERROR: --write 需要 --manifest", file=sys.stderr)
    sys.exit(2)

mp = Path(MANIFEST)
data = yaml.safe_load(mp.read_text(encoding="utf-8"))
data["control_plane_lock"] = {"algorithm": "sha256", "entries": entries}
mp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"control_plane_lock 已写入 {mp}（{len(entries)} 项）——manifest 已变，需重新生成 signoff")
