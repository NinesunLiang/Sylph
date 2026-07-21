#!/usr/bin/env python3
"""gen_control_plane_lock.py — control_plane_lock 生成器（FINAL.md v3.1 §16 / GPT#3）
用法: gen_control_plane_lock.py                      → 输出 YAML entries 到 stdout
      gen_control_plane_lock.py --manifest M --write → 写回 manifest control_plane_lock.entries
"""
from __future__ import annotations
import hashlib, json, sys, yaml
from pathlib import Path

CARROS_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def main() -> int:
    manifest_path = ""
    write = False
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--manifest" and i + 1 < len(sys.argv):
            manifest_path = sys.argv[i + 1]; i += 2
        elif sys.argv[i] == "--write":
            write = True; i += 1
        else:
            print(f"ERROR: 未知参数 {sys.argv[i]}", file=sys.stderr); return 2

    def sha256_bytes(b):
        return hashlib.sha256(b).hexdigest()

    def sha256_file(p):
        return sha256_bytes(Path(p).read_bytes())

    files = []
    gates = CARROS_ROOT / "scripts" / "carroros-gates"
    for p in sorted(gates.rglob("*")):
        if p.is_file() and p.suffix in (".sh", ".py", ".yaml", ".yml"):
            files.append(p)
    for rel in (".claude/hooks/carroros-night-deny.py", ".claude/hooks/hook-launcher.sh"):
        p = CARROS_ROOT / rel
        if p.is_file():
            files.append(p)
    cb = CARROS_ROOT / ".omc" / "scripts" / "carros_base.py"
    if cb.is_file():
        files.append(cb)

    entries = []
    seen = set()
    for p in files:
        rel = str(p.relative_to(CARROS_ROOT).as_posix())
        if rel in seen:
            continue
        seen.add(rel)
        entries.append({"path": rel, "sha256": sha256_file(p)})

    settings = CARROS_ROOT / ".claude" / "settings.json"
    if settings.is_file():
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
            hooks = data.get("hooks", {})
            canon = json.dumps(hooks, sort_keys=True, separators=(",", ":")).encode()
            entries.append({"path": ".claude/settings.json#hooks", "sha256": sha256_bytes(canon)})
        except Exception as e:
            print(f"ERROR: settings.json hooks 段解析失败: {e}", file=sys.stderr)
            return 2

    if not write:
        print(yaml.safe_dump({"algorithm": "sha256", "entries": entries},
                             sort_keys=False, allow_unicode=True))
        return 0

    if not manifest_path:
        print("ERROR: --write 需要 --manifest", file=sys.stderr); return 2
    mp = Path(manifest_path)
    data = yaml.safe_load(mp.read_text(encoding="utf-8"))
    data["control_plane_lock"] = {"algorithm": "sha256", "entries": entries}
    mp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"control_plane_lock 已写入 {mp}（{len(entries)} 项）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
