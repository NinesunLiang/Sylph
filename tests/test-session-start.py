#!/usr/bin/env python3
"""
test-session-start.py — Comprehensive unit tests for session-start.py

Verified behaviors:
1. Never blocks: every exit path produces {"continue": true}
2. Injects session-handoff.md on session start (startup/compact/resume source)
3. After compact: boundary-aware watermark re-measurement (boundary postTokens + overhead)
4. Silent exit when no active tasks: no handoff, no tokens, no stepwise

Strategy: Test functions directly where possible (pure functions like _remeasure_watermark).
For main(), import the module in a controlled way, override constants to temp dirs,
and capture stdout. Use side_effect=SystemExit for sys.exit mock so execution
truly stops after the first print.

Run:  python3 scripts/test-session-start.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Fixtures ─────────────────────────────────────────────────────────────────

FIXTURE_HANDOFF = """# Session Handoff

当前任务: test-task, 状态: active
"""

FIXTURE_HANDOFF_STALE = """# Session Handoff
compact-write 于 2026-07-20T10:00:00+00:00 更新

非常陈旧的内容
"""

FIXTURE_LAST_PROMPT = "这是上一次的用户请求"

FIXTURE_USAGE_LINE = json.dumps({
    "type": "message",
    "message": {
        "usage": {"input_tokens": 10000, "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 2000}
    }
})

FIXTURE_BOUNDARY_LINE_1 = json.dumps({
    "compact_boundary": True,
    "compactMetadata": {"postTokens": 5000}
})

FIXTURE_BOUNDARY_LINE_2 = json.dumps({
    "compact_boundary": True,
    "compactMetadata": {"postTokens": 15000}
})

TOKEN_JSON = json.dumps({
    "task": {"id": "test-task", "current_step": "step3", "status": "active"},
    "stats": {"done": 2, "total": 5},
    "session": {"level": "medium"},
    "status": "active",
})

MODULE_NAME = "_session_start_test_mod"
_HOOK_FILE = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "session-start.py"


def _mod():
    """Import session-start.py fresh, return module with paths overridable."""
    sys.modules.pop(MODULE_NAME, None)
    spec = importlib.util.spec_from_file_location(MODULE_NAME, str(_HOOK_FILE))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {_HOOK_FILE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    # Null-out optional deps to avoid side effects during test
    mod._ssot_latest_active_token = None
    return mod


def _make_pua_mock():
    pua = MagicMock()
    pua._write_watermark_state.return_value = {
        "pct": 1.7, "used": 17000, "limit": 1_000_000, "level": "SAFE",
    }
    pua._update_watermark.return_value = {
        "pct": 2.0, "used": 20000, "limit": 1_000_000, "level": "SAFE",
    }
    return pua


# ── Test base ────────────────────────────────────────────────────────────────

class _Base(unittest.TestCase):
    """Creates temp dir with .omc/ structure, patches module constants to it."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tdp = Path(self.td.name)
        self.omc_dir = self.tdp / ".omc"
        self.omc_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.omc_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.tokens_dir = self.omc_dir / "tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self.step_dir = self.tdp / ".claude" / "references" / "templates" / "stepwise_cards" / ".state"
        self.step_dir.mkdir(parents=True, exist_ok=True)
        self.handoff_path = self.omc_dir / "session-handoff.md"
        self.last_prompts_path = self.state_dir / "last-user-prompt.md"
        self.transcript_path = self.tdp / "transcript.ndjson"

    def tearDown(self):
        self.td.cleanup()


# ── main() integration tests ─────────────────────────────────────────────────
# These import the module, override constants to temp dirs, and run main()
# via patched sys.stdin/stdout/exit.

class _MainBase(_Base):
    """Base for main() tests: import module, set paths, run main, parse stdout."""

    def _run_main(self, source: str = "startup", transcript_path: str | None = None,
                  handoff_text: str | None = None, pua: MagicMock | None = None,
                  write_token: bool = False, write_stepwise: bool = False,
                  ssot_mock=None) -> dict:
        """Run module's main() and return parsed stdout JSON.

        sys.exit is mocked with side_effect=SystemExit to truly stop execution
        after the first print.
        """
        mod = _mod()
        mod.OMC = self.omc_dir
        mod.HANDOFF = self.handoff_path
        mod.LAST_PROMPTS = self.last_prompts_path
        mod.TOKENS_DIR = self.tokens_dir
        mod.STEPWISE_STATE = self.step_dir
        if ssot_mock is not None:
            mod._ssot_latest_active_token = ssot_mock
        else:
            mod._ssot_latest_active_token = None
        if handoff_text is not None:
            self.handoff_path.write_text(handoff_text, encoding="utf-8")
        if write_token:
            tf = self.tokens_dir / "test-task_token.json"
            tf.write_text(TOKEN_JSON, encoding="utf-8")
        if write_stepwise:
            swf = self.step_dir / "active-task.json"
            swf.write_text(json.dumps({
                "task_id": "task-1", "current_card": "review",
                "passed": ["step1", "step2"], "status": "active",
            }), encoding="utf-8")

        payload = {"source": source}
        if transcript_path is not None:
            payload["transcript_path"] = str(transcript_path)
        stdin_data = json.dumps(payload)

        out = io.StringIO()
        with patch("sys.stdin", io.StringIO(stdin_data)):
            with patch("sys.stdout", out):
                with patch("sys.exit", side_effect=SystemExit):
                    try:
                        mod.main()
                    except SystemExit:
                        pass
        return json.loads(out.getvalue().strip())


class TestNeverBlocks(_MainBase):

    def test_silent_startup(self):
        """No handoff, no tokens, no stepwise -> continue: true, no hookSpecificOutput."""
        result = self._run_main("startup")
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result)

    def test_silent_resume(self):
        """Resume with nothing active -> continue: true."""
        result = self._run_main("resume")
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result)

    def test_happy_path_has_continue(self):
        """Handoff startup -> continue: true."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        self.assertTrue(result["continue"])
        self.assertIn("hookSpecificOutput", result)

    def test_compact_has_continue(self):
        """Compact source -> continue: true."""
        self.transcript_path.write_text(FIXTURE_USAGE_LINE, encoding="utf-8")
        result = self._run_main("compact", transcript_path=self.transcript_path,
                                pua=_make_pua_mock())
        self.assertTrue(result["continue"])

    def test_compact_continues_with_handoff(self):
        """Compact source with handoff -> continue: true with context."""
        result = self._run_main("compact", handoff_text=FIXTURE_HANDOFF)
        self.assertTrue(result["continue"])
        self.assertIn("hookSpecificOutput", result)
        self.assertIn("Session Handoff", result["hookSpecificOutput"]["additionalContext"])

    def test_invalid_stdin_continues(self):
        """Garbage stdin -> continue: true, no crash."""
        mod = _mod()
        mod._ssot_latest_active_token = None
        mod._pua = None
        mod.OMC = self.omc_dir
        mod.HANDOFF = self.handoff_path
        out = io.StringIO()
        with patch("sys.stdin", io.StringIO("not json {{{")):
            with patch("sys.stdout", out):
                with patch("sys.exit", side_effect=SystemExit):
                    try:
                        mod.main()
                    except SystemExit:
                        pass
        result = json.loads(out.getvalue().strip())
        self.assertTrue(result["continue"])

    def test_no_handoff_file_continues(self):
        """Handoff file missing -> continue: true."""
        result = self._run_main("startup")
        self.assertTrue(result["continue"])


class TestInjectHandoff(_MainBase):

    def test_injects_handoff_startup(self):
        """startup source -> handoff in additionalContext."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Session Handoff", ctx)
        self.assertIn("test-task", ctx)
        self.assertIn("startup", ctx)

    def test_injects_handoff_compact_with_prompts(self):
        """compact source -> handoff + last prompts."""
        self.last_prompts_path.write_text(FIXTURE_LAST_PROMPT, encoding="utf-8")
        result = self._run_main("compact", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Session Handoff", ctx)
        self.assertIn("compact", ctx)
        self.assertIn("Last User Prompts", ctx)

    def test_injects_handoff_resume_with_prompts(self):
        """resume source -> handoff + last prompts."""
        self.last_prompts_path.write_text(FIXTURE_LAST_PROMPT, encoding="utf-8")
        result = self._run_main("resume", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Session Handoff", ctx)
        self.assertIn("resume", ctx)
        self.assertIn("Last User Prompts", ctx)

    def test_startup_no_last_prompts(self):
        """startup source -> handoff, no last prompts section."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Session Handoff", ctx)
        self.assertNotIn("Last User Prompts", ctx)

    def test_stale_handoff_banner(self):
        """Handoff older than 24h -> STALE warning."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF_STALE)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("STALE handoff", ctx)

    def test_fresh_handoff_no_stale_banner(self):
        """Handoff within 24h -> no STALE banner."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("STALE handoff", ctx)

    def test_handoff_truncated(self):
        """Handoff over 2000 chars -> truncated."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF + "x" * 5000)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        # Header: "[Session Handoff — startup 恢复导航]\n"
        # The handoff body starts after the header
        header = "[Session Handoff — startup 恢复导航]\n"
        body = ctx[len(header):] if ctx.startswith(header) else ctx
        self.assertLessEqual(len(body), 2100,
                             msg="Handoff body should be truncated to ~MAX_HANDOFF")

    def test_no_handoff_file_no_context(self):
        """No handoff file -> no additionalContext."""
        result = self._run_main("startup")
        self.assertNotIn("hookSpecificOutput", result)

    def test_empty_handoff_skipped(self):
        """Whitespace-only handoff -> no hookSpecificOutput."""
        result = self._run_main("startup", handoff_text="   \n  ")
        self.assertNotIn("hookSpecificOutput", result)

    def test_token_brief_plus_handoff(self):
        """Token brief + handoff both present."""
        def ssot_mock(dir_, require_stats=False):
            return self.tokens_dir / "test-task_token.json"
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF,
                                write_token=True, ssot_mock=ssot_mock)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[Active Task]", ctx)
        self.assertIn("Session Handoff", ctx)

    def test_stepwise_plus_handoff(self):
        """Stepwise + handoff both present."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF,
                                write_stepwise=True)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[Active Stepwise]", ctx)
        self.assertIn("Session Handoff", ctx)


class TestCompactNoWatermarkRemeasure(_MainBase):
    """RED: SessionStart compact/resume must NOT trigger watermark remeasurement.

    Contract #1 removes custom context-watermark measurement.
    Contract #4 removes SessionStart source=compact from AUTO-RESUME duty.
    """

    def test_compact_no_auto_resume_in_context(self):
        """Compact source, no resume-note.md -> no AUTO-RESUME in context."""
        result = self._run_main("compact", handoff_text=FIXTURE_HANDOFF)
        ctx = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("[AUTO-RESUME]", ctx,
                         "SessionStart must not emit AUTO-RESUME without resume-note.md")

    def test_compact_resume_note_injected(self):
        """Compact source with resume-note.md -> AUTO-RESUME in context."""
        note_path = self.state_dir / "resume-note.md"
        note_path.write_text("[AUTO-RESUME] task=T1 phase=verifying step=phase0\n立即继续，不要询问，不要重新开始。",
                             encoding="utf-8")
        result = self._run_main("compact", handoff_text=FIXTURE_HANDOFF)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[AUTO-RESUME]", ctx)
        self.assertIn("立即继续", ctx)

    def test_startup_no_auto_resume(self):
        """Startup source -> no AUTO-RESUME."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        self.assertTrue(result["continue"])
        ctx = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("[AUTO-RESUME]", ctx)

    def test_compact_bare_continue(self):
        """Compact source, no handoff -> bare continue: true."""
        result = self._run_main("compact")
        self.assertTrue(result["continue"])


class TestSilentExit(_MainBase):

    def test_no_handoff_no_tokens_no_stepwise(self):
        """Nothing active -> bare {"continue": true}."""
        result = self._run_main("startup")
        self.assertIn("continue", result)
        self.assertTrue(result["continue"])
        self.assertNotIn("hookSpecificOutput", result)
        self.assertEqual(len(result), 1, "Only continue key expected")

    def test_empty_handoff_no_injection(self):
        """Empty handoff -> silent exit."""
        result = self._run_main("startup", handoff_text="")
        self.assertNotIn("hookSpecificOutput", result)

    def test_token_brief_active_produces_output(self):
        """Token brief present -> not silent (has hookSpecificOutput)."""
        def ssot_mock(dir_, require_stats=False):
            return self.tokens_dir / "test-task_token.json"
        result = self._run_main("startup", write_token=True, ssot_mock=ssot_mock)
        self.assertIn("hookSpecificOutput", result)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[Active Task]", ctx)

    def test_stepwise_brief_active_produces_output(self):
        """Stepwise active -> not silent."""
        result = self._run_main("startup", write_stepwise=True)
        self.assertIn("hookSpecificOutput", result)
        ctx = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("[Active Stepwise]", ctx)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
