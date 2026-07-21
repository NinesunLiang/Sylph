#!/usr/bin/env bash
# install-night-hook.sh — 把 carroros-night-deny 挂入 .claude/settings.json PreToolUse 链
# 幂等（Rule 5）：已存在则不写；不改动任何其他字段；不打印文件内容（含密钥）。
# 用法: bash scripts/carroros-gates/install-night-hook.sh [--uninstall]

set -euo pipefail
CARROS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETTINGS="$CARROS_ROOT/.claude/settings.json"
UNINSTALL=0
[[ "${1:-}" == "--uninstall" ]] && UNINSTALL=1

python3 - "$SETTINGS" "$UNINSTALL" << 'PY'
import json, sys
from pathlib import Path

settings_path, uninstall = Path(sys.argv[1]), sys.argv[2] == "1"
data = json.loads(settings_path.read_text(encoding="utf-8"))
hooks = data.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])

NEEDLE = "carroros-night-deny.py"
ENTRY = {
    "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Delete",
    "hooks": [{"type": "command",
               "command": "bash \".claude/hooks/hook-launcher.sh\" \"carroros-night-deny.py\""}],
}

def has_entry(lst):
    for grp in lst:
        for h in (grp.get("hooks") or []):
            if NEEDLE in str(h.get("command", "")):
                return True
    return False

changed = False
if uninstall:
    new_pre = []
    for grp in pre:
        grp_hooks = [h for h in (grp.get("hooks") or []) if NEEDLE not in str(h.get("command", ""))]
        if grp_hooks:
            g = dict(grp)
            g["hooks"] = grp_hooks
            new_pre.append(g)
        elif not (grp.get("hooks")):
            new_pre.append(grp)
    if len(new_pre) != len(pre) or any(a != b for a, b in zip(new_pre, pre)):
        hooks["PreToolUse"] = new_pre
        changed = True
    msg = "已卸载" if changed else "本就不存在，无需卸载"
else:
    if has_entry(pre):
        msg = "已存在，幂等跳过"
    else:
        pre.append(ENTRY)
        changed = True
        msg = "已挂载 carroros-night-deny 到 PreToolUse 链"

if changed:
    tmp = settings_path.with_suffix(".json.night-hook-tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(settings_path)
print(f"install-night-hook: {msg}")
PY
