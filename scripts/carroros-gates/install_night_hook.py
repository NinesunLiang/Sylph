#!/usr/bin/env python3
"""install_night_hook.py — 把 carroros-night-deny 挂入 settings.json PreToolUse 链
幂等：已存在则不写。用法: install_night_hook.py [--uninstall]
"""
from __future__ import annotations
import json, sys
from pathlib import Path

CARROS_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS = CARROS_ROOT / ".claude" / "settings.json"

def main() -> int:
    uninstall = "--uninstall" in sys.argv
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])

    needle = "carroros-night-deny.py"
    entry = {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Delete",
        "hooks": [{"type": "command",
                    "command": "python3 \".claude/hooks/hook-launcher.py\" \"carroros-night-deny.py\""}],
    }

    def has_entry(lst):
        for grp in lst:
            for h in (grp.get("hooks") or []):
                if needle in str(h.get("command", "")):
                    return True
        return False

    changed = False
    if uninstall:
        new_pre = []
        for grp in pre:
            grp_hooks = [h for h in (grp.get("hooks") or []) if needle not in str(h.get("command", ""))]
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
            pre.append(entry)
            changed = True
            msg = "已挂载 carroros-night-deny 到 PreToolUse 链"

    if changed:
        tmp = SETTINGS.with_suffix(".json.night-hook-tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(SETTINGS)
    print(f"install-night-hook: {msg}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
