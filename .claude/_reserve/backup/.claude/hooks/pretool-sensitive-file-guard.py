#!/usr/bin/env python3
"""pretool-sensitive-file-guard.py — PreToolUse:Edit|Write — 保护门禁文件不被 AI 直接写入
Role: 拦截 AI 通过 Edit/Write 工具直接写 permission-approved / permission-required 等门禁文件
"""
import json
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


# ── Local mode detection (simplified, uses file-based markers) ──
def _is_mode_active(state_dir):
    """Detect active mode using file-based markers."""
    sd = Path(state_dir)
    if (sd / "tokens" / "goal.active").exists():
        return "goal"
    if (sd / "tokens" / "ghost.active").exists():
        return "ghost"
    if (sd / "tokens" / "rpe.active").exists():
        return "rpe"
    return "normal"


# ── Sensitive file basenames ──
_SENSITIVE_FILES = frozenset({
    "permission-approved", "permission-required", "permission-marker",
    "current-scope.txt", "sensitive-approved", "sensitive-required",
    "oracle-gate-required", "oracle-gate-approved",
})


def main():
    # ── Guard ──
    if not hc_enabled("sensitive_file_guard"):
        sys.exit(0)

    # ── Path setup ──
    hooks_dir = Path(__file__).resolve().parent
    project_root = (hooks_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # ── Mode detection: non-normal mode → record and pass ──
    mode = _is_mode_active(str(state_dir))
    if mode != "normal":
        flywheel_event("sensitive_file_guard", f"mode_skip_{mode}", "P3")
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    if not input_str:
        print('{"continue": true}')
        sys.exit(0)

    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Extract file_path ──
    tool_input = input_data.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", input_data.get("file_path", ""))

    if not file_path:
        print('{"continue": true}')
        sys.exit(0)

    # ── Check if basename matches sensitive files ──
    basename = Path(file_path).name
    if basename in _SENSITIVE_FILES:
        sys.stderr.write(f"""
🚫 [Sensitive File Guard] AI 不得直接写入门禁文件！

文件: {file_path}
原因: 这是权限门禁的标记文件，只能由 hook 或用户操作写入。
AI 自行写入此文件构成门禁绕过企图。

""")
        flywheel_event("sensitive_file_guard", f"blocked_{basename}", "P0")

        # Build block response (note: hc_emit_hook_json for PreToolUse uses block pattern)
        result = {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    f"[Sensitive File Guard] AI 试图直接写入门禁文件 {basename}，"
                    "已阻断。门禁文件只能由 hook 或用户操作修改。"
                )
            }
        }
        print(json.dumps(result, ensure_ascii=True))
        sys.exit(2)

    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
