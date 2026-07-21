#!/usr/bin/env python3
"""
install-night-hook.py — 把 carroros-night-deny 挂入 .claude/settings.json PreToolUse 链
幂等（Rule 5）：已存在则不写；不改动任何其他字段；不打印文件内容（含密钥）。
用法: python3 scripts/carroros-gates/install-night-hook.py [--uninstall]
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CARROS_ROOT = SCRIPT_DIR.parent.parent
SETTINGS = CARROS_ROOT / ".claude" / "settings.json"
UNINSTALL = "--uninstall" in sys.argv

data = json.loads(SETTINGS.read_text(encoding="utf-8"))
hooks = data.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])

NEEDLE = "carroros-night-deny.py"
ENTRY = {
    "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Delete",
    "hooks": [{"type": "command",
               "command": "python3 \".claude/hooks/hook-launcher.py\" \"carroros-night-deny.py\""}],
}


def has_entry(lst):
    for grp in lst:
        for h in grp.get("hooks") or []:
            if NEEDLE in str(h.get("command", "")):
                return True
    return False


changed = False
if UNINSTALL:
    new_pre = []
    for grp in pre:
        grp_hooks = [h for h in (grp.get("hooks") or [])
                     if NEEDLE not in str(h.get("command", ""))]
        if grp_hooks:
            g = dict(grp)
            g["hooks"] = grp_hooks
            new_pre.append(g)
        elif grp.get("hooks"):
            pass
        else:
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
    tmp = SETTINGS.with_suffix(".json.night-hook-tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(SETTINGS)

print(f"install-night-hook: {msg}")
