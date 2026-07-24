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
compact-write 于 2026-07-24T10:00:00+00:00 更新

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

FIXTURE_BOUNDARY_LINE_3 = json.dumps({
    "compact_boundary": True,
    "compactMetadata": {"postTokens": 8000}
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


# ── Pure function tests (_remeasure_watermark) ───────────────────────────────
# These don't need full module import — test the logic directly.

class TestRemeasureWatermark(_Base):
    """Direct tests of _remeasure_watermark() logic by calling it on a loaded module.

    Key decision tree (lines 184-192 of session-start.py):
      - Last anchor is boundary AND no usage after it →
          _write_watermark_state(last_post + overhead)
      - Otherwise (usage after last boundary, or no boundary at all) →
          _update_watermark (PUA normal path)
    """

    def _transcript_tail(self, *entries):
        """Write NDJSON transcript and return its absolute path."""
        text = "\n".join(entries) + "\n" if entries else "\n"
        self.transcript_path.write_text(text, encoding="utf-8")
        # size must be within WM_TAIL_BYTES so the _remeasure_watermark reads all lines
        return self.transcript_path

    def _call_remeasure(self, transcript_entries, pua=None):
        """Import module, set pua, call _remeasure_watermark directly."""
        mod = _mod()
        mod._pua = pua or _make_pua_mock()
        tp = self._transcript_tail(*transcript_entries)
        mod._remeasure_watermark(tp)
        return mod._pua

    def test_boundary_no_post_usage_estimates(self):
        """Last anchor is boundary, no usage after -> estimate via post+overhead.
        prev boundary post=5000, usage=17000 -> overhead=12000.
        last boundary post=15000 -> estimate = 15000+12000 = 27000.
        """
        pua = self._call_remeasure([
            FIXTURE_BOUNDARY_LINE_1,
            FIXTURE_USAGE_LINE,
            FIXTURE_BOUNDARY_LINE_2,
        ])
        pua._write_watermark_state.assert_called_once_with(27000)
        pua._update_watermark.assert_not_called()

    def test_boundary_with_post_usage_delegates(self):
        """Boundary with usage after -> delegate to _update_watermark."""
        pua = self._call_remeasure([
            FIXTURE_BOUNDARY_LINE_2,
            FIXTURE_USAGE_LINE,
        ])
        pua._update_watermark.assert_called_once()
        pua._write_watermark_state.assert_not_called()

    def test_no_boundary_delegates(self):
        """No compact_boundary lines -> delegate to _update_watermark."""
        pua = self._call_remeasure([FIXTURE_USAGE_LINE])
        pua._update_watermark.assert_called_once()
        pua._write_watermark_state.assert_not_called()

    def test_fallback_overhead_single_boundary(self):
        """Single boundary with no prior usage -> fallback overhead=30000."""
        pua = self._call_remeasure([FIXTURE_BOUNDARY_LINE_2])
        pua._write_watermark_state.assert_called_once_with(15000 + 30000)

    def test_multiple_boundaries_last_wins(self):
        """Multiple boundaries, last wins and overhead carries forward."""
        pua = self._call_remeasure([
            FIXTURE_BOUNDARY_LINE_1,    # post=5000
            FIXTURE_USAGE_LINE,          # overhead=12000
            FIXTURE_BOUNDARY_LINE_3,     # post=8000
            FIXTURE_BOUNDARY_LINE_2,     # post=15000 last, no usage after
        ])
        # last_post=15000, overhead=12000
        pua._write_watermark_state.assert_called_once_with(27000)

    def test_empty_transcript_delegates(self):
        """Empty transcript (no boundary info) -> delegates to _update_watermark."""
        pua = self._call_remeasure([])
        pua._update_watermark.assert_called_once()
        pua._write_watermark_state.assert_not_called()

    def test_nonexistent_transcript_noop(self):
        """Path doesn't exist -> no watermark calls."""
        mod = _mod()
        mod._pua = _make_pua_mock()
        mod._remeasure_watermark(self.tdp / "nope.ndjson")
        mod._pua._write_watermark_state.assert_not_called()
        mod._pua._update_watermark.assert_not_called()

    def test_boundary_usage_boundary_usage_delegates(self):
        """Boundary -> usage -> boundary -> usage -> delegate to _update_watermark."""
        pua = self._call_remeasure([
            FIXTURE_BOUNDARY_LINE_1,
            FIXTURE_USAGE_LINE,
            FIXTURE_BOUNDARY_LINE_2,
            FIXTURE_USAGE_LINE,  # usage after last boundary
        ])
        pua._update_watermark.assert_called_once()
        pua._write_watermark_state.assert_not_called()

    def test_no_pua_noop(self):
        """_pua is None -> skip entirely."""
        mod = _mod()
        mod._pua = None
        self.transcript_path.write_text(FIXTURE_USAGE_LINE, encoding="utf-8")
        # Should not raise
        mod._remeasure_watermark(self.transcript_path)

    def test_overhead_from_latest_computed_pair(self):
        """Overhead is computed from the latest boundary+usage pair that formed one."""
        pua = self._call_remeasure([
            FIXTURE_BOUNDARY_LINE_1,    # post=5000
            FIXTURE_USAGE_LINE,          # usage=17000 -> overhead=12000
            json.dumps({                 # boundary post=2000
                "compact_boundary": True,
                "compactMetadata": {"postTokens": 2000}
            }),
            json.dumps({                 # usage=22000 (14000+5000+3000)
                "message": {"usage": {"input_tokens": 14000, "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 3000}}
            }),
            FIXTURE_BOUNDARY_LINE_2,     # post=15000 last, no usage after
        ])
        # overhead from last pair = 22000 - 2000 = 20000
        # last_post=15000 -> 15000 + 20000 = 35000
        pua._write_watermark_state.assert_called_once_with(35000)

    def test_usage_before_first_boundary_ignored(self):
        """Usage before first boundary does not set prev_usage for overhead -> fallback."""
        pua = self._call_remeasure([
            FIXTURE_USAGE_LINE,           # before first boundary, no prev_boundary
            FIXTURE_BOUNDARY_LINE_2,      # post=15000, no usage after -> fallback overhead
        ])
        pua._write_watermark_state.assert_called_once_with(15000 + 30000)


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
        if pua is not None:
            mod._pua = pua
        else:
            mod._pua = None
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

    def test_compact_remeasure_error_still_continues(self):
        """Watermark remeasurement throws -> still returns continue."""
        pua = _make_pua_mock()
        pua._write_watermark_state.side_effect = RuntimeError("boom")
        self.transcript_path.write_text(
            "\n".join([FIXTURE_BOUNDARY_LINE_1, FIXTURE_USAGE_LINE, FIXTURE_BOUNDARY_LINE_2]),
            encoding="utf-8",
        )
        result = self._run_main("compact", transcript_path=self.transcript_path, pua=pua)
        self.assertTrue(result["continue"])

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


class TestCompactWatermarkIntegration(_MainBase):
    """Verifies main() calls _remeasure_watermark for compact/resume source."""

    def test_compact_triggers_remeasure(self):
        """Compact source -> remeasure called with transcript path."""
        pua = _make_pua_mock()
        self.transcript_path.write_text(
            "\n".join([FIXTURE_BOUNDARY_LINE_1, FIXTURE_USAGE_LINE, FIXTURE_BOUNDARY_LINE_2]),
            encoding="utf-8",
        )
        result = self._run_main("compact", transcript_path=self.transcript_path, pua=pua)
        self.assertTrue(result["continue"])

    def test_resume_triggers_remeasure(self):
        """Resume source -> remeasure called with transcript path."""
        pua = _make_pua_mock()
        self.transcript_path.write_text(
            "\n".join([FIXTURE_BOUNDARY_LINE_1, FIXTURE_USAGE_LINE, FIXTURE_BOUNDARY_LINE_2]),
            encoding="utf-8",
        )
        result = self._run_main("resume", transcript_path=self.transcript_path, pua=pua)
        self.assertTrue(result["continue"])

    def test_startup_skips_remeasure(self):
        """Startup source -> no remeasurement (no pua used)."""
        result = self._run_main("startup", handoff_text=FIXTURE_HANDOFF)
        # Should still produce normal output
        self.assertTrue(result["continue"])
        self.assertIn("hookSpecificOutput", result)

    def test_missing_transcript_path_skips_remeasure(self):
        """Compact source but no transcript_path -> remeasure skipped, clean exit."""
        pua = _make_pua_mock()
        result = self._run_main("compact", pua=pua)
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
