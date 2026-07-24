#!/usr/bin/env python3
"""Tests for .claude/hooks/precompact-lifecycle.py.

Covers the four PO requirements:
  1. Flushes handoff + snapshot on PreCompact
  2. Fail-closed: snapshot write failure -> exit 2
  3. Compact-write failure logs stderr, doesn't block
  4. Delegates to lifecycle_ssot.write_precompact_snapshot()
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "precompact-lifecycle.py"
SSOT_PATH = REPO_ROOT / ".claude" / "hooks" / "lib" / "lifecycle_ssot.py"


# ---------------------------------------------------------------------------
# Module loader — precompact-lifecycle.py has a hyphen so importlib is needed
# ---------------------------------------------------------------------------

def load_hook_module():
    """Load precompact-lifecycle.py module, returning the module object.

    The hook does ``from lib.lifecycle_ssot import write_precompact_snapshot``
    at module level, so names like ``write_precompact_snapshot`` are bound
    directly on the hook module.  Mock *those* rather than lifecycle_ssot.
    """
    # Ensure the SSOT module is loadable from the hooks/lib directory
    hooks_lib_dir = str(HOOK_PATH.parent / "lib")
    if hooks_lib_dir not in sys.path:
        sys.path.insert(0, hooks_lib_dir)

    # Load lifecycle_ssot first so hook's import resolves
    ssot_spec = importlib.util.spec_from_file_location(
        "lifecycle_ssot_for_test", str(SSOT_PATH)
    )
    ssot_mod = importlib.util.module_from_spec(ssot_spec)
    sys.modules["lifecycle_ssot"] = ssot_mod
    ssot_spec.loader.exec_module(ssot_mod)

    # Now load the hook
    spec = importlib.util.spec_from_file_location(
        "precompact_lifecycle_test", str(HOOK_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["precompact_lifecycle_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def unload_hook_module():
    """Remove test modules from sys.modules so next load is fresh."""
    for key in list(sys.modules):
        if "precompact_lifecycle_test" in key or "lifecycle_ssot_for_test" in key:
            sys.modules.pop(key, None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hook():
    """Fresh hook module instance per test."""
    yield load_hook_module()
    unload_hook_module()


@pytest.fixture
def fake_hook_input() -> dict:
    return {
        "session_id": "ses-abc123",
        "sessionId": "ses-abc123",
        "cwd": "/tmp",
        "transcript_path": "/tmp/transcript.json",
        "transcriptPath": "/tmp/transcript.json",
        "hook_event_name": "PreCompact",
        "hookEventName": "PreCompact",
    }


@pytest.fixture
def fake_handoff() -> dict:
    return {
        "version": 1,
        "updated_at": "2026-07-24T00:00:00Z",
        "written": 3,
        "claimed": 3,
        "reconciled": False,
        "items": [
            {
                "id": "i1",
                "kind": "test",
                "source": "fixture",
                "at": "2026-07-24T00:00:00Z",
                "body": {},
            }
        ],
        "md_progress_note": None,
    }


@pytest.fixture
def temp_omc_state(monkeypatch) -> Path:
    """Redirect .omc/state to a temp directory so real lifecycle_ssot I/O
    is exercised without touching the real .omc directory."""
    tmpdir = Path(tempfile.mkdtemp(prefix="pc-test-"))
    state_dir = tmpdir / ".omc" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmpdir))
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Requirement 1: Flushes handoff + snapshot on PreCompact
# ---------------------------------------------------------------------------


class TestPreCompactHappyPath:
    """Requirement 1: PreCompact flushes handoff state, writes snapshot,
    emits well-formed JSON to stdout, and exits 0."""

    def test_stdout_structure(self, hook, fake_hook_input, fake_handoff):
        """Verify the stdout JSON contains ok, event, snapshot, sha256,
        compact_write, handoff_written, handoff_claimed, reconciled."""
        snapshot_path = Path("/tmp/snapshots/pc-20260724-deadbeef.json")
        snapshot_digest = "a" * 64

        mock_snap = MagicMock(return_value=(snapshot_path, snapshot_digest, fake_handoff))

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()) as fake_stdout,
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            # Patch the *hook module's* local name, not lifecycle_ssot's
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            # Avoid compact-write subprocess by returning no token
            patch.object(hook, "_latest_token", return_value=None),
        ):
            result = hook.main()

        assert result == 0, f"Expected exit 0, got {result}"
        output = json.loads(fake_stdout.getvalue())
        assert output["ok"] is True
        assert output["event"] == "PreCompact"
        assert output["snapshot"] == str(snapshot_path)
        assert output["sha256"] == snapshot_digest
        assert "compact_write" in output
        # Skipped because no token
        assert output["compact_write"] == "skipped:no_token"
        assert "handoff_written" in output
        assert "handoff_claimed" in output
        assert "reconciled" in output
        assert fake_stderr.getvalue() == ""

    def test_delegates_to_write_precompact_snapshot(
        self, hook, fake_hook_input, fake_handoff
    ):
        """Requirement 4: Delegates to lifecycle_ssot.write_precompact_snapshot().
        Verify the correct hook_input and event_id are forwarded."""
        snapshot_path = Path("/tmp/snapshots/pc-cafebabe.json")
        snapshot_digest = "cafe" * 16
        mock_snap = MagicMock(return_value=(snapshot_path, snapshot_digest, fake_handoff))

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()),
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch.object(hook, "_latest_token", return_value=None),
        ):
            hook.main()

        mock_snap.assert_called_once()
        call_args, call_kwargs = mock_snap.call_args
        assert call_args[0] == fake_hook_input, "hook_input not forwarded"
        event_id = call_kwargs.get("event_id") or call_args[1]
        assert isinstance(event_id, str)
        assert event_id.startswith("pc-")
        assert len(event_id) == 19  # "pc-" + 16 hex chars

    def test_without_session_id(self, hook, fake_handoff):
        """When session_id is absent, event_id derivation still works and
        output omits the field gracefully."""
        hook_input_no_sid = {"cwd": "/tmp", "transcript_path": "/tmp/t.json"}
        mock_snap = MagicMock(
            return_value=(
                Path("/tmp/s.json"),
                "d" * 64,
                fake_handoff,
            )
        )

        with (
            patch("sys.stdin", io.StringIO(json.dumps(hook_input_no_sid))),
            patch("sys.stdout", io.StringIO()) as fake_stdout,
            patch("sys.stderr", io.StringIO()),
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch.object(hook, "_latest_token", return_value=None),
        ):
            rc = hook.main()

        assert rc == 0
        output = json.loads(fake_stdout.getvalue())
        assert output["ok"] is True


# ---------------------------------------------------------------------------
# Requirement 2: Fail-closed — snapshot write failure -> exit 2
# ---------------------------------------------------------------------------


class TestFailClosedSnapshot:
    """Requirement 2: If lifecycle_ssot.write_precompact_snapshot() raises
    an exception, the hook exits 2 and the error is written to stderr."""

    def test_snapshot_ioerror_exits_2(self, hook, fake_hook_input):
        """IOError from write_precompact_snapshot propagates as exit 2."""
        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            patch.object(
                hook, "write_precompact_snapshot",
                side_effect=IOError("PRECOMPACT_FAIL:snapshot-hash-mismatch"),
            ),
            patch.object(hook, "_latest_token", return_value=None),
        ):
            result = hook.main()

        assert result == 2, f"Expected exit 2, got {result}"
        assert "PRECOMPACT_FAIL" in fake_stderr.getvalue()

    def test_valueerror_from_snapshot_exits_2(self, hook, fake_hook_input):
        """Any Exception from write_precompact_snapshot -> exit 2."""
        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            patch.object(
                hook, "write_precompact_snapshot",
                side_effect=ValueError("bad handoff data"),
            ),
            patch.object(hook, "_latest_token", return_value=None),
        ):
            result = hook.main()

        assert result == 2
        assert "PRECOMPACT_FAIL" in fake_stderr.getvalue()

    def test_keyboardinterrupt_propagates(self, hook, fake_hook_input):
        """KeyboardInterrupt is NOT caught (it's a BaseException) so it
        propagates as a real crash."""
        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()),
            patch.object(
                hook, "write_precompact_snapshot",
                side_effect=KeyboardInterrupt(),
            ),
            patch.object(hook, "_latest_token", return_value=None),
        ):
            with pytest.raises(KeyboardInterrupt):
                hook.main()


# ---------------------------------------------------------------------------
# Requirement 3: Compact-write failure logs stderr, doesn't block
# ---------------------------------------------------------------------------


class TestCompactWriteBestEffort:
    """Requirement 3: compact-write subprocess failure is logged to stderr
    but does NOT prevent exit 0 or the snapshot emission."""

    def test_subprocess_nonexistent_logs_does_not_block(
        self, hook, fake_hook_input, fake_handoff
    ):
        """If context_engine.py subprocess fails, hook still exits 0 and
        writes the snapshot; failure is recorded on stderr."""
        mock_snap = MagicMock(
            return_value=(Path("/tmp/pc-fail.json"), "deadbeef" + "0" * 56, fake_handoff)
        )

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()) as fake_stdout,
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch("subprocess.run") as mock_run,
        ):
            # _latest_token returns a real path so refresh runs
            mock_run.side_effect = FileNotFoundError("No such file")
            with patch.object(
                hook, "_latest_token",
                return_value=Path("/tmp/fake-token.json"),
            ):
                result = hook.main()

        assert result == 0, f"Expected exit 0 (best-effort), got {result}"
        assert "PRECOMPACT_COMPACT_WRITE_FAIL" in fake_stderr.getvalue()
        output = json.loads(fake_stdout.getvalue())
        assert output["compact_write"] == "failed:FileNotFoundError"
        assert output["ok"] is True

    @pytest.mark.parametrize("returncode", [1, 127, -9])
    def test_subprocess_nonzero_rc_logs_does_not_block(
        self, hook, fake_hook_input, fake_handoff, returncode
    ):
        """Non-zero returncode from compact-write logs stderr, exits 0."""
        mock_snap = MagicMock(
            return_value=(Path("/tmp/s.json"), "d" * 64, fake_handoff)
        )

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=returncode, stderr="boom", stdout=""
            )
            with patch.object(
                hook, "_latest_token",
                return_value=Path("/tmp/fake-token.json"),
            ):
                result = hook.main()

        assert result == 0, f"Expected exit 0 despite rc={returncode}"
        assert f"PRECOMPACT_COMPACT_WRITE_FAIL:rc={returncode}" in fake_stderr.getvalue()

    def test_compact_write_timeout_logs_stderr(
        self, hook, fake_hook_input, fake_handoff
    ):
        """subprocess.TimeoutError is caught, logged, does not block."""
        mock_snap = MagicMock(
            return_value=(Path("/tmp/s.json"), "d" * 64, fake_handoff)
        )

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()),
            patch("sys.stderr", io.StringIO()) as fake_stderr,
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = TimeoutError("timeout")
            with patch.object(
                hook, "_latest_token",
                return_value=Path("/tmp/fake-token.json"),
            ):
                result = hook.main()

        assert result == 0
        assert "PRECOMPACT_COMPACT_WRITE_FAIL:TimeoutError" in fake_stderr.getvalue()
        output = json.loads(fake_stdout.getvalue())
        assert output["compact_write"] == "failed:TimeoutError"


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestLatestToken:
    """Unit coverage for _latest_token and _resolve_task_dir."""

    def test_latest_token_returns_none_when_ssot_none(self, hook):
        with patch.object(hook, "_ssot_latest_active_token", None):
            assert hook._latest_token() is None

    def test_resolve_task_dir_returns_none_for_missing_path(self, hook):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"task": {"dir": "/nonexistent/path"}}, f)
            f.flush()
            token_path = Path(f.name)

        result = hook._resolve_task_dir(token_path)
        os.unlink(token_path)
        assert result is None


class TestEdgeCases:
    """Remaining edge cases."""

    def test_ssot_unavailable_skips_compact_write(
        self, hook, fake_hook_input, fake_handoff
    ):
        """When task_ssot.latest_active_token is None (SSOT unavailable),
        compact-write is skipped entirely, but snapshot still happens."""
        mock_snap = MagicMock(
            return_value=(Path("/tmp/s.json"), "d" * 64, fake_handoff)
        )

        with (
            patch("sys.stdin", io.StringIO(json.dumps(fake_hook_input))),
            patch("sys.stdout", io.StringIO()) as fake_stdout,
            patch("sys.stderr", io.StringIO()),
            patch.object(hook, "write_precompact_snapshot", mock_snap),
            patch.object(hook, "_ssot_latest_active_token", None),
        ):
            result = hook.main()

        assert result == 0
        output = json.loads(fake_stdout.getvalue())
        assert output["compact_write"] == "skipped:no_token"


# ---------------------------------------------------------------------------
# Integration-style snapshot test (real lifecycle_ssot I/O)
# ---------------------------------------------------------------------------


class TestWritePrecompactSnapshotIntegration:
    """Light integration: write_precompact_snapshot called with real temp
    dirs. Uses the real lifecycle_ssot (no patch) to confirm the
    handoff-flush / lifecycle-update disk contract works end-to-end."""

    def test_real_write_flushes_and_updates_lifecycle(
        self, fake_hook_input, temp_omc_state
    ):
        """After write_precompact_snapshot, lifecycle.json records the
        snapshot sha256 and event_id, and handoff.json has been reconciled."""
        # Import the real ssot module directly
        hooks_lib_dir = str(HOOK_PATH.parent / "lib")
        if hooks_lib_dir not in sys.path:
            sys.path.insert(0, hooks_lib_dir)

        # Fresh-import the real lifecycle_ssot in the temp state env
        import importlib

        ssot = importlib.import_module("lifecycle_ssot")

        # Write initial lifecycle + handoff to the temp state dir
        state_dir = temp_omc_state / ".omc" / "state"
        (state_dir / "lifecycle.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "mode": "idle",
                    "goal_id": None,
                    "ghost_id": None,
                    "session_id": None,
                    "updated_at": "2026-07-24T00:00:00Z",
                    "compact": {
                        "last_precompact_at": None,
                        "last_snapshot_path": None,
                        "last_sha256": None,
                        "last_event_id": None,
                    },
                    "end": {
                        "last_session_end_at": None,
                        "last_subagent_stop_at": None,
                        "sealed": False,
                    },
                    "seen_event_ids": [],
                }
            )
        )
        (state_dir / "handoff.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "updated_at": "2026-07-24T00:00:00Z",
                    "written": 0,
                    "claimed": 0,
                    "reconciled": False,
                    "items": [],
                    "md_progress_note": None,
                }
            )
        )

        event_id = "pc-test-integration"
        path, digest, hb = ssot.write_precompact_snapshot(
            fake_hook_input, event_id=event_id
        )

        # 1. Snapshot file exists on disk
        assert path.exists(), f"Snapshot not created at {path}"
        assert path.suffix == ".json"
        assert "precompact" in path.name

        # 2. Digest matches the snapshot content
        raw = path.read_text(encoding="utf-8")
        assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == digest

        # 3. Snapshot JSON is valid and contains expected keys
        snap = json.loads(raw)
        assert snap["type"] == "precompact"
        assert snap["event_id"] == event_id
        assert snap["lifecycle"]["mode"] == "idle"
        assert snap["hook_input"]["session_id"] == "ses-abc123"

        # 4. Lifecycle updated on disk
        lc = ssot.load_lifecycle()
        assert lc["compact"]["last_event_id"] == event_id
        assert lc["compact"]["last_sha256"] == digest
        assert lc["compact"]["last_precompact_at"] is not None
        assert lc["compact"]["last_snapshot_path"] is not None

        # 5. Handoff reconciled and persisted
        assert hb["written"] == hb["claimed"]

        # 6. Handoff has the precompact_flush item
        items = hb.get("items", [])
        flush_items = [i for i in items if i.get("kind") == "precompact_flush"]
        assert len(flush_items) >= 1
        assert flush_items[-1]["body"]["sha256"] == digest

        # 7. Compact section in lifecycle has the stored session_id
        assert lc.get("session_id") == "ses-abc123"
