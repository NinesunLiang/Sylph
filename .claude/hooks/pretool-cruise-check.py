#!/usr/bin/env python3
"""pretool-cruise-check.py — SessionStart/PreToolUse — 巡航模式基础设施自检
Role: 检测 ghost/goal mode 激活但巡航基础设施未初始化 → 提醒 AI 创建
"""
import json
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, is_mode_active


def main():
    # ── Guard ──
    if not hc_enabled("cruise_check"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Path setup ──
    hooks_dir = Path(__file__).resolve().parent
    project_root = (hooks_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # ── Mode detection ──
    mode = is_mode_active(str(state_dir))
    if mode == "normal":
        print('{"continue": true}')
        sys.exit(0)

    # ── Check cruising infrastructure ──
    cruising_file = project_root / ".cruising"
    feature_dir = project_root / "feature"

    if not cruising_file.exists():
        # Mode active but .cruising missing → remind to create
        feature_hint = "unknown"

        # Try to extract feature from mode json
        goal_mode_file = state_dir / "goal-mode.json"
        ghost_mode_file = state_dir / "ghost-mode.json"

        if goal_mode_file.exists():
            try:
                import json as jmod
                data = jmod.loads(goal_mode_file.read_text(encoding="utf-8", errors="replace"))
                feature_hint = data.get("feature", "unknown")
            except Exception:
                pass
        elif ghost_mode_file.exists():
            try:
                import json as jmod
                data = jmod.loads(ghost_mode_file.read_text(encoding="utf-8", errors="replace"))
                feature_hint = data.get("directive", "unknown")
            except Exception:
                pass

        result = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[cruise-check] {mode} mode 已激活但巡航基础设施未初始化。"
                    f"请运行: bash .claude/scripts/cruise-bootstrap.sh {feature_hint}"
                )
            }
        }
        print(json.dumps(result, ensure_ascii=True))
        sys.exit(0)

    # ── .cruising exists but feature/ missing ──
    if not feature_dir.is_dir():
        import os
        os.makedirs(str(feature_dir), exist_ok=True)

    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
