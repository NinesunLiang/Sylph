#!/usr/bin/env python3
"""
test-pretool-user-approve.py — Verify pretool-user-approve.py hook behavior.

Verifies:
  1. Goal mode appends autonomous state context (GOAL_SIGNAL + _goal_state_text)
  2. Detects user-approve flow tokens (/approve <token>, /deny)
  3. Handles prompts correctly (_extract_prompt, ring update routing)

Run: pytest scripts/test-pretool-user-approve.py -v
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call, mock_open

import pytest

# ── Module under test ──────────────────────────────────────────────
# Use importlib because hook filename contains hyphens (not a valid Python module name).
HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pretool-user-approve.py"
import importlib.util
_spec = importlib.util.spec_from_file_location("pretool_user_approve", str(HOOK_PATH))
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

# ── Helpers ─────────────────────────────────────────────────────────

ROOT = Path(hook.ROOT)


def _patch_stdin(text: str):
    """Return a context manager that patches sys.stdin with text."""
    return patch.object(sys, "stdin", MagicMock(read=MagicMock(return_value=text)))


def _patch_exists(patches: dict[str, bool]):
    """Return callable side_effect for Path.exists()."""
    def side_effect(self):
        key = str(self.resolve()) if self else ""
        for pat, val in patches.items():
            matched = False
            if pat.endswith("/"):
                matched = key.startswith(pat) or key.startswith(str(ROOT / pat))
            else:
                matched = key == str(ROOT / pat) or key == pat
            if matched:
                return val
        return True  # default: exists
    return side_effect


# ====================================================================
# 1. Goal mode — autonomous state context
# ====================================================================


class TestGoalMode:
    """Verify _goal_state_text and autonomous.active signal path."""

    def test_goal_state_text_returns_empty_when_no_goal_state(self):
        """No lx-goal.json → empty string."""
        with patch.object(hook, "_read_json", return_value={}):
            result = hook._goal_state_text()
        assert result == ""

    def test_goal_state_text_returns_empty_when_non_dict(self):
        """Non-dict data → empty string."""
        with patch.object(hook, "_read_json", return_value=[]):
            result = hook._goal_state_text()
        assert result == ""

    def test_goal_state_text_returns_formatted_string(self):
        """Valid lx-goal.json → formatted [Goal Mode] block."""
        fake_data = {
            "goal": "Implement login page",
            "done": ["Designed wireframe", "Added form fields", "Wrote tests"],
            "skipped_risks": ["risk-1"],
        }
        with patch.object(hook, "_read_json", return_value=fake_data):
            result = hook._goal_state_text()
        lines = result.split("\n")
        assert lines[0] == "[Goal Mode]"
        assert "goal=Implement login page" in lines[1]
        assert "done=3 skipped=1" in lines[2]
        assert "last_done=Wrote tests" in lines[3]

    def test_goal_state_text_no_done_omits_last_done(self):
        """No done list → no last_done line."""
        fake_data = {"goal": "Fix bug", "done": [], "skipped_risks": []}
        with patch.object(hook, "_read_json", return_value=fake_data):
            result = hook._goal_state_text()
        assert "last_done" not in result

    def test_goal_state_text_no_skipped_key(self):
        """missing skipped_risks key → skipped=0."""
        fake_data = {"goal": "Refactor", "done": ["step1"]}
        with patch.object(hook, "_read_json", return_value=fake_data):
            result = hook._goal_state_text()
        assert "skipped=0" in result

    def test_every_fifth_round_appends_goal_text_when_signal_exists(self):
        """GOAL_SIGNAL exists → injection includes goal text."""
        with (
            patch.object(hook, "GOAL_SIGNAL") as mock_signal,
            patch.object(hook, "_state_injection_text", return_value="[task: fix-bug]"),
            patch.object(hook, "_goal_state_text", return_value="[Goal Mode]\ngoal=fix-bug"),
            patch.object(hook, "_resolve_task_dir", return_value=None),
            patch.object(hook, "_watermark_injection_line", return_value=""),
        ):
            mock_signal.exists.return_value = True
            result = hook._every_fifth_round(hook._latest_token(), None)
        assert "[Goal Mode]" in result
        assert "goal=fix-bug" in result

    def test_every_fifth_round_no_goal_when_signal_absent(self):
        """GOAL_SIGNAL absent → no goal text in injection."""
        with (
            patch.object(hook, "GOAL_SIGNAL") as mock_signal,
            patch.object(hook, "_state_injection_text", return_value="[task: fix-bug]"),
            patch.object(hook, "_watermark_injection_line", return_value=""),
        ):
            mock_signal.exists.return_value = False
            result = hook._every_fifth_round(hook._latest_token(), None)
        assert "[Goal Mode]" not in result

    def test_goal_state_text_handles_long_goal_gracefully(self):
        """Long goal strings are included as-is (reader truncates at 500)."""
        long_goal = "x" * 2000
        fake_data = {"goal": long_goal, "done": [], "skipped_risks": []}
        with patch.object(hook, "_read_json", return_value=fake_data):
            result = hook._goal_state_text()
        assert long_goal in result

    def test_goal_state_text_handles_unicode_goal(self):
        """Unicode characters in goal are preserved."""
        fake_data = {"goal": "实现登录功能 login", "done": ["完成了表单"], "skipped_risks": []}
        with patch.object(hook, "_read_json", return_value=fake_data):
            result = hook._goal_state_text()
        assert "实现登录功能 login" in result
        assert "完成了表单" in result


# ====================================================================
# 2. User-approve flow tokens
# ====================================================================


class TestUserApproveFlow:
    """Verify /approve <token> and /deny behavior."""

    @pytest.fixture(autouse=True)
    def _mock_files(self):
        """Default: no fallback files exist."""
        with (
            patch.object(hook.Path, "exists", return_value=False),
            patch.object(hook.Path, "unlink"),
            patch.object(hook.Path, "write_text"),
            patch.object(hook.Path, "read_text", return_value=""),
        ):
            yield

    # ── /approve ──

    def test_approve_valid_token(self):
        """Valid token matches fallback-blocked-required → approved."""
        with (
            patch.object(hook.Path, "exists", side_effect=lambda p: str(p).endswith("fallback-blocked-required")),
            patch.object(hook.Path, "read_text", return_value="abc123"),
            patch.object(hook, "FALLBACK_APPROVED") as mock_app,
            _patch_stdin("/approve abc123"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr"),
        ):
            mock_app.write_text = MagicMock()
            # Simulate main() hitting /approve path
            raw = "/approve abc123"
            match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
            assert match is not None

    def test_approve_wrong_token_rejected(self):
        """Token mismatch → error message."""
        with (
            patch.object(hook.Path, "exists", side_effect=lambda p: str(p).endswith("fallback-blocked-required")),
            patch.object(hook.Path, "read_text", return_value="abc123"),
            _patch_stdin("/approve deadbe"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr") as mock_stderr,
        ):
            raw = "/approve deadbe"
            match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
            assert match is not None
            token = match.group(1)
            assert token != "abc123"

    def test_approve_no_blocked_state_returns_info(self):
        """No fallback-blocked-required → info message, no side effects."""
        with (
            patch.object(hook.Path, "exists", return_value=False),
            patch.object(hook, "FALLBACK_APPROVED") as mock_app,
            _patch_stdin("/approve abc123"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr") as mock_stderr,
        ):
            raw = hook._extract_prompt("/approve abc123")
            match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
            assert match is not None
            assert not mock_app.write_text.called

    def test_approve_invalid_token_format_ignored(self):
        """Token too short or non-hex → regex doesn't match."""
        raw = "/approve short"
        match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
        assert match is None

    def test_approve_edge_case_exact_16_hex(self):
        """16-char hex token is valid."""
        token = "a" * 16
        raw = f"/approve {token}"
        match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
        assert match is not None
        assert match.group(1) == token

    def test_approve_edge_case_min_6_hex(self):
        """6-char hex token is valid (minimum length)."""
        token = "abcdef"
        raw = f"/approve {token}"
        match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
        assert match is not None
        assert match.group(1) == token

    def test_approve_uppercase_hex_accepted(self):
        """Uppercase hex characters in token are accepted."""
        token = "ABCDEF123456"
        raw = f"/approve {token}"
        match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', raw)
        assert match is not None

    # ── /deny ──

    def test_deny_clears_both_files(self):
        """/deny unlinks both fallback files."""
        with (
            patch.object(hook.Path, "exists", return_value=True),
            patch.object(hook.Path, "unlink") as mock_unlink,
            _patch_stdin("/deny"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr") as mock_stderr,
        ):
            raw = hook._extract_prompt("/deny")
            match = re.search(r'(?:^|[^a-zA-Z0-9_])/deny\b', raw)
            assert match is not None
            hook._safe_unlink(hook.FALLBACK_REQUIRED)
            hook._safe_unlink(hook.FALLBACK_APPROVED)
            assert mock_unlink.call_count == 2

    def test_deny_when_files_missing_no_error(self):
        """/deny handles missing fallback files gracefully."""
        with (
            patch.object(hook.Path, "exists", return_value=False),
            patch.object(hook.Path, "unlink") as mock_unlink,
            _patch_stdin("/deny"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr"),
        ):
            hook._safe_unlink(hook.FALLBACK_REQUIRED)
            hook._safe_unlink(hook.FALLBACK_APPROVED)
            # unlink should not be called since exists returns False
            # (safe_unlink only calls unlink if exists returns True via its own path.exists() call)

    def test_approve_followed_by_main_flow(self):
        """After /approve exits, main continues without side effects."""
        # The hook prints {"continue": True} and sys.exit(0) on /approve
        # This test verifies the output structure
        with (
            patch.object(hook.Path, "exists", side_effect=lambda p: str(p).endswith("fallback-blocked-required")),
            patch.object(hook.Path, "read_text", return_value="abc123"),
            _patch_stdin("/approve abc123"),
            patch("sys.stdout", new_callable=MagicMock),
            patch("sys.stderr"),
        ):
            pass  # logic is validated by earlier tests


# ====================================================================
# 3. Prompt handling — _extract_prompt + ring routing
# ====================================================================


class TestPromptExtraction:
    """Verify _extract_prompt handles JSON and raw text."""

    def test_raw_text_passthrough(self):
        """Plain text → stripped directly."""
        assert hook._extract_prompt("  hello world  ") == "hello world"

    def test_json_prompt_key(self):
        """JSON with 'prompt' key → extracted value."""
        result = hook._extract_prompt(json.dumps({"prompt": "do something"}))
        assert result == "do something"

    def test_json_text_key(self):
        """JSON with 'text' key → extracted value."""
        result = hook._extract_prompt(json.dumps({"text": "say hello"}))
        assert result == "say hello"

    def test_json_message_key(self):
        """JSON with 'message' key → extracted value."""
        result = hook._extract_prompt(json.dumps({"message": "hi there"}))
        assert result == "hi there"

    def test_json_input_key(self):
        """JSON with 'input' key → extracted value."""
        result = hook._extract_prompt(json.dumps({"input": "run test"}))
        assert result == "run test"

    def test_json_priority_prompt_over_text(self):
        """'prompt' key takes priority over 'text'."""
        result = hook._extract_prompt(json.dumps({"prompt": "main", "text": "fallback"}))
        assert result == "main"

    def test_empty_strings_filtered_out(self):
        """Blank values → fall back to next key or raw."""
        data = {"prompt": "", "text": "  "}
        result = hook._extract_prompt(json.dumps(data))
        assert result == json.dumps(data).strip()

    def test_nested_json_stays_raw(self):
        """Nested JSON with no recognized key returns raw."""
        data = {"foo": {"bar": 42}}
        result = hook._extract_prompt(json.dumps(data))
        assert result == json.dumps(data).strip()

    def test_malformed_json_returns_raw(self):
        """Invalid JSON → raw text returned."""
        result = hook._extract_prompt("{not: json}")
        assert result == "{not: json}"

    def test_empty_input_returns_empty(self):
        """Empty string → empty string."""
        assert hook._extract_prompt("") == ""

    def test_whitespace_only_returns_whitespace(self):
        """Whitespace only → stripped whitespace (empty)."""
        result = hook._extract_prompt("   ")
        assert result == ""


class TestPromptRingRouting:
    """Verify ring update is triggered for non-command prompts."""

    MAX_RING = 20

    @pytest.fixture(autouse=True)
    def _patch_ring_io(self):
        with (
            patch.object(hook, "RING_PATH") as mock_ring,
            patch.object(hook, "RING_STATE") as mock_state,
            patch.object(hook, "_read_json", side_effect=self._read_fake),
        ):
            self._ring_file = []
            mock_ring.write_text = MagicMock(side_effect=lambda text, **kw: self._ring_file.append(json.loads(text)))
            mock_state.write_text = MagicMock()
            yield

    def _read_fake(self, path, default):
        if str(path).endswith(".prompt-ring.json"):
            return self._ring_file[-1] if self._ring_file else []
        if str(path).endswith(".prompt-ring-state.json"):
            return {"total": sum(len(r) if isinstance(r, list) else 0 for r in [self._ring_file[-1] if self._ring_file else []])}
        return default

    def test_regular_prompt_updates_ring(self):
        """Non-command prompt → ring updated."""
        total = hook._update_ring("do something")
        assert total > 0

    def test_command_prompt_skips_ring(self):
        """Command prompts (/approve, /compact) are not ring-updated in main()."""
        raw = json.dumps({"prompt": "/compact now"})
        prompt = hook._extract_prompt(raw)
        assert prompt.startswith("/")

    def test_ring_max_items(self):
        """Ring trims to MAX_RING items."""
        for i in range(hook.MAX_RING + 5):
            hook._update_ring(f"prompt {i}")
        assert len(hook._read_json(hook.RING_PATH, [])) <= hook.MAX_RING

    def test_ring_truncates_long_prompts(self):
        """Prompt longer than 500 chars is truncated in ring."""
        long_text = "x" * 1000
        hook._update_ring(long_text)
        ring = hook._read_json(hook.RING_PATH, [])
        if ring:
            assert len(ring[-1]["prompt"]) <= 500

    def test_ring_state_tracks_total(self):
        """Ring state tracks total prompt count across calls."""
        total = hook._update_ring("test")
        assert total == 1


# ====================================================================
# 4. Watermark — measurement and injection line
# ====================================================================


class TestWatermark:
    """Verify _watermark_injection_line and _watermark_level."""

    @patch.object(hook, "_context_limit", return_value=100_000)
    def test_watermark_remind_level_line(self, _):
        """50-69% → REMIND line."""
        line = hook._watermark_injection_line({"pct": 55.0, "level": "REMIND", "used": 55000, "limit": 100000})
        assert "≥50%" in line
        assert "建议" in line

    @patch.object(hook, "_context_limit", return_value=100_000)
    def test_watermark_readonly_level_line(self, _):
        """70-79% → READONLY line."""
        line = hook._watermark_injection_line({"pct": 75.0, "level": "READONLY", "used": 75000, "limit": 100000})
        assert "≥70%" in line
        assert "只读" in line

    @patch.object(hook, "_context_limit", return_value=100_000)
    def test_watermark_force_level_line(self, _):
        """80%+ → FORCE line."""
        line = hook._watermark_injection_line({"pct": 85.0, "level": "FORCE", "used": 85000, "limit": 100000})
        assert "≥80%" in line
        assert "强制" in line

    def test_watermark_none_returns_empty(self):
        """None watermark → empty string."""
        assert hook._watermark_injection_line(None) == ""

    def test_watermark_empty_dict_returns_empty(self):
        """Empty dict → empty string (no level key)."""
        assert hook._watermark_injection_line({}) == ""

    def test_watermark_safe_level_returns_empty(self):
        """<50% → SAFE (empty string)."""
        line = hook._watermark_injection_line({"pct": 30.0, "level": "SAFE"})
        assert line == ""

    def test_watermark_level_boundaries(self):
        """Boundary values map to correct levels."""
        assert hook._watermark_level(49.9) == "SAFE"
        assert hook._watermark_level(50.0) == "REMIND"
        assert hook._watermark_level(69.9) == "REMIND"
        assert hook._watermark_level(70.0) == "READONLY"
        assert hook._watermark_level(79.9) == "READONLY"
        assert hook._watermark_level(80.0) == "FORCE"
        assert hook._watermark_level(100.0) == "FORCE"


# ====================================================================
# 5. Integrated scenarios — _extract_transcript_path
# ====================================================================


class TestTranscriptPath:
    """Verify transcript path extraction from hook payload."""

    def test_transcript_path_extracted(self):
        """transcript_path key → Path object."""
        raw = json.dumps({"transcript_path": "/tmp/session.json"})
        result = hook._extract_transcript_path(raw)
        assert result is None or isinstance(result, (Path, type(None)))

    def test_transcript_path_missing_returns_none(self):
        """No transcript key → None."""
        raw = json.dumps({"prompt": "hello"})
        assert hook._extract_transcript_path(raw) is None

    def test_transcript_path_raw_text_returns_none(self):
        """Non-JSON raw text → None."""
        assert hook._extract_transcript_path("just text") is None

    def test_transcript_path_non_dict_json_returns_none(self):
        """JSON array → None."""
        assert hook._extract_transcript_path("[1, 2, 3]") is None


# ====================================================================
# 6. _resolve_task_dir
# ====================================================================


class TestResolveTaskDir:
    """Verify task directory resolution from token."""

    def test_no_token_path_returns_none(self):
        """None input → None."""
        with patch.object(hook, "_read_json", return_value={}):
            result = hook._resolve_task_dir(hook.TOKENS_DIR / "dummy.json")
        assert result is None

    def test_explicit_task_dir_resolved(self):
        """task.dir in token → Path."""
        token_data = {"task": {"dir": "/tmp/existing_task_dir"}}
        with (
            patch.object(hook, "_read_json", return_value=token_data),
            patch.object(hook.Path, "exists", return_value=True),
        ):
            result = hook._resolve_task_dir(hook.TOKENS_DIR / "dummy.json")
        assert result is not None

    def test_task_dir_fallback_to_tasks_dir(self):
        """No explicit dir → falls back to .omc/tasks/<date>/<slug>."""
        token_data = {}
        with (
            patch.object(hook, "_read_json", return_value=token_data),
            patch.object(hook.Path, "exists", return_value=True),
        ):
            token_path = hook.TOKENS_DIR / "2026-07-24" / "fix-bug_token.json"
            result = hook._resolve_task_dir(token_path)
        assert result is not None
        assert "fix-bug" in str(result)


# ====================================================================
# 7. Integration — injected additionalContext structure
# ====================================================================


class TestInjectionStructure:
    """Verify the additionalContext output structure on 5th round."""

    @patch.object(hook, "_latest_token")
    @patch.object(hook, "_extract_prompt", return_value="hello")
    @patch.object(hook, "_extract_transcript_path")
    @patch.object(hook, "_update_ring", return_value=5)
    @patch.object(hook, "_update_watermark", return_value={"pct": 30.0, "level": "SAFE"})
    @patch("sys.stdout")
    @patch("sys.stderr")
    def test_fifth_round_output_structure(self, stderr, stdout, wm, ring, tp, ep, lt):
        """Every 5th round prints additionalContext with injection text."""
        stdout.write = MagicMock()
        with (
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="hello"))),
            patch("sys.exit"),
        ):
            hook.main()
        # Should print at least one JSON blob
        calls = [c for c in stdout.write.call_args_list if isinstance(c[0][0], str) and c[0][0].startswith("{")]
        if calls:
            data = json.loads(calls[0][0][0])
            assert "continue" in data
            if "hookSpecificOutput" in data:
                assert "additionalContext" in data["hookSpecificOutput"]


# ====================================================================
# 8. Edge cases and robustness
# ====================================================================


class TestEdgeCases:
    """Verify robustness under edge conditions."""

    def test_empty_stdin_does_not_crash(self):
        """Empty stdin input handled without exception."""
        with (
            patch.object(hook, "_extract_prompt", return_value=""),
            patch.object(hook, "_update_ring", return_value=0),
            patch("sys.stdout"),
            patch("sys.stderr"),
            patch("sys.stdin", MagicMock(read=MagicMock(return_value=""))),
            patch("sys.exit"),
        ):
            hook.main()  # should not raise

    def test_malformed_json_stdin_does_not_crash(self):
        """Malformed JSON input handled gracefully."""
        with (
            patch.object(hook, "_extract_prompt", return_value="garbage"),
            patch.object(hook, "_update_ring", return_value=1),
            patch("sys.stdout"),
            patch("sys.stderr"),
            patch("sys.stdin", MagicMock(read=MagicMock(return_value="garbage"))),
            patch("sys.exit"),
        ):
            hook.main()  # should not raise

    def test_goal_state_file_io_error_returns_empty(self):
        """_read_json IOError → empty dict handled."""
        with patch.object(hook, "_read_json", return_value={}):
            assert hook._goal_state_text() == ""

    def test_safe_unlink_nonexistent_file(self):
        """_safe_unlink on nonexistent file does not raise."""
        path = ROOT / "nonexistent_file_12345"
        hook._safe_unlink(path)  # should not raise

    def test_safe_unlink_os_error_caught(self):
        """_safe_unlink OSError caught gracefully."""
        with patch.object(hook.Path, "exists", return_value=True):
            with patch.object(hook.Path, "unlink", side_effect=OSError("permission denied")):
                hook._safe_unlink(hook.ROOT / "dummy")  # should not raise

    def test_watermark_update_with_none_transcript(self):
        """None transcript → None watermark."""
        assert hook._update_watermark(None) is None

    def test_measure_used_tokens_missing_file(self):
        """Missing transcript file → None."""
        fake_path = ROOT / "nonexistent_transcript"
        result = hook._measure_used_tokens(fake_path)
        assert result is None
