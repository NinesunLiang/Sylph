from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]


def _validate_and_read_capsule(capsule_path: Path) -> str | None:
    """Read resume-capsule.json, validate token/task, return AUTO-RESUME context."""
    try:
        if not capsule_path.exists():
            return None
        capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
        active_token = capsule.get("active_token")
        plan_dir = capsule.get("plan_dir")
        step = capsule.get("current_step")
        phase = capsule.get("current_phase", "unknown")
        task_id = capsule.get("task_id")
        if not all([active_token, plan_dir, step, task_id]):
            return None
        active_p = Path(active_token)
        plan_p = Path(plan_dir)
        if not active_p.exists():
            return None
        # 检查 token 尚未归档
        try:
            token_data = json.loads(active_p.read_text(encoding="utf-8"))
            if token_data.get("status") == "archived":
                return None
        except Exception:
            return None
        if not plan_p.exists():
            return None
        for required_file in ("plan.md", "research.md", "executor.md"):
            if not (plan_p / required_file).exists():
                return None
        lines = []
        lines.append("[AUTO-RESUME] 原生 compact 已完成，继续任务。")
        lines.append(f"task={task_id} phase={phase} step={step}")
        lines.append("立即继续，不要询问，不要重新开始。")
        context = "\n".join(lines)
        if len(context) > 2500:
            context = context[:2497] + "..."
        return context
    except Exception:
        return None


def _safe_write_resume_note(context: str, note_path: Path) -> bool:
    """Atomic write of resume-note.md via tmp file + os.replace.

    Prevents partial files when SessionStart hook reads concurrently.
    Returns True on success, False on any I/O error.
    """
    import os
    tmp_path = note_path.with_suffix(note_path.suffix + f".{os.getpid()}.tmp")
    try:
        note_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(context, encoding="utf-8")
        os.replace(str(tmp_path), str(note_path))
        return True
    except OSError:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return False
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _validate_capsule_or_fail_silent(capsule_path: Path) -> str | None:
    """Wrap _validate_and_read_capsule with broad exception handling.

    PostCompact hook MUST NOT raise — fail-closed with None.
    """
    try:
        return _validate_and_read_capsule(capsule_path)
    except Exception:
        return None


def main() -> None:
    capsule_path = ROOT / ".omc" / "state" / "resume-capsule.json"
    context = _validate_capsule_or_fail_silent(capsule_path)

    if context:
        note_path = ROOT / ".omc" / "state" / "resume-note.md"
        _safe_write_resume_note(context, note_path)

    # PostCompact hook schema 不支持 hookSpecificOutput.additionalContext,
    # 因此 AUTO-RESUME 上下文写入 resume-note.md,
    # 由 session-start.py 在 SessionStart 事件中读取并注入。
    json.dump({"continue": True}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()