#!/usr/bin/env python3
"""End-to-end contracts for native compact task handoff."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ENGINE = ROOT / ".claude" / "scripts" / "context_engine.py"
POSTCOMPACT = ROOT / ".claude" / "hooks" / "postcompact.py"
SESSION_START = ROOT / ".claude" / "hooks" / "session-start.py"
SETTINGS = ROOT / ".claude" / "settings.json"


def load_module(name: str, path: Path):
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_task(root: Path, task_id: str = "native-compact-task") -> tuple[Path, Path]:
    task_dir = root / ".omc" / "tasks" / "20990101" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "research.md").write_text("# Research\n", encoding="utf-8")
    (task_dir / "plan.md").write_text(
        "# Plan\n## Phase 1\n- [x] S1: map\n- [ ] S2: continue\n",
        encoding="utf-8",
    )
    (task_dir / "executor.md").write_text(
        "# Executor\n### EV-S1\n- step: S1\n- exit_code: 0\n",
        encoding="utf-8",
    )
    token_path = root / ".omc" / "tokens" / "20990101" / f"{task_id}.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "schema_version": "v1.0",
        "status": "active",
        "task_dir": str(task_dir),
        "task": {"id": task_id, "status": "active", "current_step": "S2:continue"},
        "stats": {"done": 1, "total": 2},
        "session": {"id": task_id, "level": "L2"},
    }), encoding="utf-8")
    return token_path, task_dir


class TestPreCompactCapsuleProducer(unittest.TestCase):
    def test_compact_write_persists_atomic_resume_capsule(self):
        context_engine = load_module("_native_recovery_context_engine", CONTEXT_ENGINE)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            token_path, task_dir = write_task(root)
            setattr(context_engine, "ROOT", root)
            (root / ".omc" / "state").mkdir(parents=True, exist_ok=True)
            out = io.StringIO()
            with patch("sys.stdout", out):
                rc = context_engine.compact_write(token_path, task_dir)
            self.assertEqual(rc, 0)
            capsule_path = root / ".omc" / "state" / "resume-capsule.json"
            self.assertTrue(capsule_path.exists())
            self.assertFalse(capsule_path.with_suffix(".json.tmp").exists())
            capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
            self.assertEqual(capsule["active_token"], str(token_path))
            self.assertEqual(capsule["plan_dir"], str(task_dir))
            self.assertIn("current_step", capsule)
            self.assertEqual(capsule["source"], "compact")
            self.assertIn("next_action", capsule)


class TestPostCompactSoleResumeInjector(unittest.TestCase):
    def run_postcompact(self, root: Path) -> dict:
        module = load_module("_native_recovery_postcompact", POSTCOMPACT)
        setattr(module, "ROOT", root)
        out = io.StringIO()
        with patch("sys.stdout", out), patch("sys.exit", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                module.main()
        return json.loads(out.getvalue())

    def test_valid_capsule_injects_exact_active_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            token_path, task_dir = write_task(root)
            state = root / ".omc" / "state"
            state.mkdir(parents=True)
            (state / "resume-capsule.json").write_text(json.dumps({
                "active_token": str(token_path),
                "plan_dir": str(task_dir),
                "current_phase": "Phase 1",
                "current_step": "S2:continue",
                "next_action": "immediately_continue",
                "source": "compact",
                "task_id": "native-compact-task",
            }), encoding="utf-8")
            result = self.run_postcompact(root)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("[AUTO-RESUME]", context)
            self.assertIn("native-compact-task", context)
            self.assertIn("S2:continue", context)
            self.assertIn("立即继续", context)
            self.assertLessEqual(len(context), 2500)

    def test_stale_capsule_never_replaces_active_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_token, _ = write_task(root, "active-task")
            stale_token, stale_dir = write_task(root, "stale-task")
            active_token.touch()
            state = root / ".omc" / "state"
            state.mkdir(parents=True)
            (state / "resume-capsule.json").write_text(json.dumps({
                "active_token": str(stale_token),
                "plan_dir": str(stale_dir),
                "current_step": "S9:stale",
                "next_action": "immediately_continue",
                "source": "compact",
            }), encoding="utf-8")
            result = self.run_postcompact(root)
            self.assertEqual(result, {"continue": True})


class TestNativeHookRegistration(unittest.TestCase):
    def test_postcompact_is_registered_for_native_success(self):
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        entries = settings["hooks"]["PostCompact"]
        self.assertTrue(any(entry.get("matcher") == "manual|auto" for entry in entries))
        commands = [hook["command"] for entry in entries for hook in entry["hooks"]]
        self.assertTrue(any("postcompact.py" in command for command in commands))

    def test_session_start_does_not_own_compact_resume(self):
        source = SESSION_START.read_text(encoding="utf-8")
        self.assertNotIn("_build_resume_context_from_capsule", source)
        self.assertNotIn("[AUTO-RESUME]", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
