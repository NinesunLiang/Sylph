#!/usr/bin/env python3
"""CarrorOS Hook Launcher"""

import os, sys

CRITICAL_HOOKS = {"pretool-gate.py", "carroros-night-deny.py"}

def main():
    if len(sys.argv) < 2:
        print('{"continue":true,"message":"hook-launcher: missing hook name"}')
        sys.exit(0)
    hook_name = sys.argv[1]
    launcher_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(launcher_dir, "..", ".."))
    hook_path = os.path.join(launcher_dir, hook_name)

    if not os.path.isfile(hook_path):
        if hook_name in CRITICAL_HOOKS:
            cn_msg = "hook-launcher: CRITICAL hook missing: " + hook_name + " — blocked"
            out = '{"continue":true,"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"' + cn_msg + '"}}'
            print(out)
            print(cn_msg, file=sys.stderr)
            sys.exit(2)
        print('{"continue":true,"message":"hook-launcher: hook not found: ' + hook_name + '"}')
        sys.exit(0)

    os.chdir(project_root)
    os.environ.pop("NIGHT_DENY_ROOT", None)
    cmd = ["bash", hook_path] if hook_name.endswith(".sh") else [sys.executable, hook_path]
    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
