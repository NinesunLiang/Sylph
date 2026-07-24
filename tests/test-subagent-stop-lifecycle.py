#!/usr/bin/env python3
"""Tests for .claude/hooks/subagent-stop-lifecycle.py."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Provide a clean project dir with CLAUDE_PROJECT_DIR overridden."""
    d = tmp_path / "project"
    d.mkdir()
    return d


_HOOKS_DIR = str(
    (Path(__file__).resolve().parent.parent / ".claude" / "hooks").resolve()
)


@pytest.fixture
def lifecycle_ssot(project_dir: Path) -> type:
    """Return the lifecycle_ssot module with CLAUDE_PROJECT_DIR pointed at
    the temporary project dir, and all STATE_DIR paths rooted there."""
    with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project_dir)}):
        import importlib

        # Ensure .claude/hooks is on sys.path so 'lib.lifecycle_ssot' resolves
        if _HOOKS_DIR not in sys.path:
            sys.path.insert(0, _HOOKS_DIR)

        import lib.lifecycle_ssot as mod

        importlib.reload(mod)
        mod.STATE_DIR.mkdir(parents=True, exist_ok=True)
        return mod


@pytest.fixture
def lc(lifecycle_ssot) -> type:
    """Alias for brevity."""
    return lifecycle_ssot


# ---------------------------------------------------------------------------
# Test: on_subagent_stop records a handoff item
# ---------------------------------------------------------------------------


class TestOnSubagentStopRecords:
    def test_writes_handoff_item(self, lc) -> None:
        """A subagent stop event produces one handoff item of kind
        'subagent_stop'."""
        event_id = "ss-test-1234"
        hook_input = {
            "agent_id": "agent-foo",
            "agentType": "subagent",
            "session_id": "session-xyz",
        }
        hb = lc.on_subagent_stop(event_id, hook_input)

        assert hb["written"] == 1
        items = hb["items"]
        assert len(items) == 1
        item = items[0]
        assert item["kind"] == "subagent_stop"
        assert item["id"] == event_id
        assert item["body"]["agent_id"] == "agent-foo"
        assert item["body"]["agent_type"] == "subagent"
        assert item["body"]["session_id"] == "session-xyz"
        assert "at" in item

    def test_records_last_subagent_stop_at(self, lc) -> None:
        """lifecycle.end.last_subagent_stop_at is set."""
        event_id = "ss-ts"
        hook_input = {"agent_id": "a1"}
        lc.on_subagent_stop(event_id, hook_input)
        lc_data = lc.load_lifecycle()
        assert lc_data["end"]["last_subagent_stop_at"] is not None

    def test_empty_hook_input(self, lc) -> None:
        """Fallback agent_id to 'unknown' when no agent identifier present."""
        hb = lc.on_subagent_stop("ss-empty", {})
        assert hb["written"] == 1
        assert hb["items"][-1]["body"]["agent_id"] == "unknown"

    def test_multiple_stops_record_separate_items(self, lc) -> None:
        """Different event IDs each produce their own handoff item."""
        lc.on_subagent_stop("ss-a", {"agent_id": "a"})
        lc.on_subagent_stop("ss-b", {"agent_id": "b"})
        hb = lc.load_handoff()
        assert hb["written"] == 2
        kinds = [i["body"]["agent_id"] for i in hb["items"]]
        assert kinds == ["a", "b"]


# ---------------------------------------------------------------------------
# Test: Idempotent — same event_id is deduplicated
# ---------------------------------------------------------------------------


class TestIdempotent:
    def test_same_event_id_does_not_add_second_item(self, lc) -> None:
        """Calling on_subagent_stop twice with the same event_id must not
        create a second handoff item."""
        event_id = "ss-dedup-001"
        hook_input = {"agent_id": "agent-x", "session_id": "s1"}
        hb1 = lc.on_subagent_stop(event_id, hook_input)
        assert hb1["written"] == 1

        hb2 = lc.on_subagent_stop(event_id, hook_input)
        assert hb2["written"] == 1
        assert len(hb2["items"]) == 1

    def test_seen_event_ids_contains_id_after_first_call(self, lc) -> None:
        """After the first call, the event_id is recorded in lifecycle's
        seen_event_ids list."""
        eid = "ss-seen-abc"
        lc.on_subagent_stop(eid, {"agent_id": "x"})
        lc_data = lc.load_lifecycle()
        assert eid in lc_data["seen_event_ids"]

    def test_second_call_returns_handoff_without_mutating(self, lc) -> None:
        """The second invocation returns the current handoff, and the lifecycle's
        last_subagent_stop_at timestamp is NOT updated."""
        eid = "ss-ts-dedup"
        lc.on_subagent_stop(eid, {"agent_id": "x"})
        lc_data_1 = lc.load_lifecycle()
        ts1 = lc_data_1["end"]["last_subagent_stop_at"]

        lc.on_subagent_stop(eid, {"agent_id": "x"})
        lc_data_2 = lc.load_lifecycle()
        assert lc_data_2["end"]["last_subagent_stop_at"] == ts1

    def test_event_id_none_is_not_deduplicated(self, lc) -> None:
        """Passing event_id=None should always append, not deduplicate."""
        lc.on_subagent_stop(None, {"agent_id": "a"})
        lc.on_subagent_stop(None, {"agent_id": "b"})
        hb = lc.load_handoff()
        assert hb["written"] == 2


# ---------------------------------------------------------------------------
# Test: Hook script main() delegates to lifecycle_ssot.on_subagent_stop()
# ---------------------------------------------------------------------------


class TestHookDelegation:
    def test_main_delegates_to_on_subagent_stop(self, project_dir: Path) -> None:
        """The hook's main() calls lifecycle_ssot.on_subagent_stop and outputs
        the expected JSON schema: {ok, event, handoff_written, handoff_claimed}."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project_dir)}):
            import importlib

            import lib.lifecycle_ssot as ssot

            importlib.reload(ssot)
            ssot.STATE_DIR.mkdir(parents=True, exist_ok=True)

            stdin_payload = json.dumps(
                {
                    "agent_id": "sub-agent-99",
                    "agentType": "worker",
                    "session_id": "sess-main",
                    "hook_event_name": "SubagentStop",
                }
            )

            mock_stdout = MagicMock()
            mock_stderr = MagicMock()

            # Import the hook module
            hook_path = Path(
                __file__
            ).parent.parent / ".claude" / "hooks" / "subagent-stop-lifecycle.py"
            spec = importlib.util.spec_from_file_location(
                "subagent_stop_hook", str(hook_path)
            )
            assert spec is not None, "could not load hook module"
            hook_mod = importlib.util.module_from_spec(spec)

            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            orig_stdin = sys.stdin
            try:
                sys.stdout = mock_stdout
                sys.stderr = mock_stderr
                spec.loader.exec_module(hook_mod)

                # Now call main() explicitly with patched stdin
                sys.stdin = MagicMock()
                sys.stdin.read.return_value = stdin_payload

                rc = hook_mod.main()
                assert rc == 0
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
                sys.stdin = orig_stdin

            stdout_text = "".join(
                a[0][0] for a in mock_stdout.write.call_args_list
            ).strip()
            if not stdout_text:
                raise AssertionError(
                    f"no stdout produced; stderr writes={mock_stderr.write.call_args_list}"
                )
            out = json.loads(stdout_text)

            assert out["ok"] is True
            assert out["event"] == "SubagentStop"
            assert out["handoff_written"] >= 1
            assert out["handoff_claimed"] >= 1

            # Verify the handoff really was written
            hb = ssot.load_handoff()
            assert hb["written"] >= 1
            items_kinds = [i["kind"] for i in hb["items"]]
            assert "subagent_stop" in items_kinds

    def test_main_exit_code_zero_on_success(self, project_dir: Path) -> None:
        """Main returns 0 on normal execution."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project_dir)}):
            import importlib

            import lib.lifecycle_ssot as ssot

            importlib.reload(ssot)
            ssot.STATE_DIR.mkdir(parents=True, exist_ok=True)

            stdin_payload = json.dumps({"agent_id": "a1"})
            hook_path = Path(
                __file__
            ).parent.parent / ".claude" / "hooks" / "subagent-stop-lifecycle.py"
            spec = importlib.util.spec_from_file_location(
                "subagent_stop_hook_exit", str(hook_path)
            )
            assert spec is not None
            hook_mod = importlib.util.module_from_spec(spec)

            with patch("sys.stdin") as mock_stdin, patch(
                "sys.stdout"
            ), patch("sys.stderr"):
                mock_stdin.read.return_value = stdin_payload
                spec.loader.exec_module(hook_mod)

                rc = hook_mod.main()
                assert rc == 0

    def test_main_returns_2_on_exception(self, project_dir: Path) -> None:
        """Main returns 2 when the underlying call raises."""
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project_dir)}):
            import importlib

            import lib.lifecycle_ssot as ssot

            importlib.reload(ssot)
            ssot.STATE_DIR.mkdir(parents=True, exist_ok=True)

            hook_path = Path(
                __file__
            ).parent.parent / ".claude" / "hooks" / "subagent-stop-lifecycle.py"
            spec = importlib.util.spec_from_file_location(
                "sub_stop_fail", str(hook_path)
            )
            assert spec is not None
            hook_mod = importlib.util.module_from_spec(spec)

            with patch("sys.stdin") as mock_stdin, patch(
                "sys.stdout"
            ), patch("sys.stderr"):
                mock_stdin.read.side_effect = RuntimeError("boom")

                orig_stdout = sys.stdout
                sys.stdout = MagicMock()
                try:
                    spec.loader.exec_module(hook_mod)
                    rc = hook_mod.main()
                    assert rc == 2
                finally:
                    sys.stdout = orig_stdout


# ---------------------------------------------------------------------------
# Test: Known bug prevention — state file corruption
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_corrupted_handoff_reinitialized(self, lc) -> None:
        """An empty/corrupt handoff file is re-initialized to defaults by
        load_json, so on_subagent_stop still works."""
        lc.STATE_DIR.mkdir(parents=True, exist_ok=True)
        # load_json handles empty or missing files, NOT arbitrary corrupt JSON
        lc.HANDOFF_PATH.write_text("")
        hb = lc.on_subagent_stop("ss-recover", {"agent_id": "r"})
        assert hb["written"] == 1

    def test_empty_stdin_in_hook(self, lc) -> None:
        """read_stdin_json returns {} for empty input, and on_subagent_stop
        handles missing keys gracefully."""
        hb = lc.on_subagent_stop("ss-empty-stdin", {})
        assert hb["written"] == 1
        assert hb["items"][-1]["body"]["agent_id"] == "unknown"
