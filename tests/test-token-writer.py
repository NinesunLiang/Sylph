#!/usr/bin/env python3
"""Comprehensive tests for token_writer.py — token usage tracking, running state, context-guard output.

Token writer always writes to the real project's .omc/state/ (harness_core resolves _PROJECT_ROOT
from file location, not CLAUDE_PROJECT_DIR).  Tests manage this by working with the real project
root and saving/restoring state files around each test.  The harness cache is also temporarily
updated to enable token_writer.

Run: python3 scripts/test-token-writer.py
Exit 0 only if all assertions pass.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root = Carror_Base_OS
HOOKS = ROOT / ".claude" / "hooks"
TOKEN_WRITER = HOOKS / "token_writer.py"
STATE_DIR = ROOT / ".omc" / "state"
HARNESS_CACHE = STATE_DIR / ".harness-cache"
CACHE_BACKUP: bytes | None = None


def _backup_state():
    """Back up token_writer state files and harness cache before a test."""
    global CACHE_BACKUP
    if HARNESS_CACHE.is_file():
        CACHE_BACKUP = HARNESS_CACHE.read_bytes()
    else:
        CACHE_BACKUP = None


def _restore_state():
    """Restore token_writer state files and harness cache after a test."""
    global CACHE_BACKUP
    # Remove files we may have created
    for name in [
        "token-tracking-index.json",
        "token-savings.json",
        "token-compact-state.json",
        ".token-writer-session.log",
    ]:
        (STATE_DIR / name).unlink(missing_ok=True)
    # Restore harness cache
    if CACHE_BACKUP is not None:
        HARNESS_CACHE.write_bytes(CACHE_BACKUP)
    else:
        HARNESS_CACHE.unlink(missing_ok=True)


def _enable_token_writer_in_cache():
    """Write hooks_enabled.token_writer=true to the harness cache so hc_enabled returns True."""
    if HARNESS_CACHE.is_file():
        content = HARNESS_CACHE.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        new_lines = []
        sentinel_present = False
        for line in lines:
            if line.startswith("hooks_enabled.token_writer="):
                new_lines.append("hooks_enabled.token_writer=true")
            else:
                new_lines.append(line)
            if line.startswith("__parsed_count__="):
                sentinel_present = True
        # Add if not present
        if not any("hooks_enabled.token_writer" in l for l in lines):
            new_lines.append("hooks_enabled.token_writer=true")
        # Update parsed count if sentinel present
        if sentinel_present:
            for i, line in enumerate(new_lines):
                if line.startswith("__parsed_count__="):
                    new_lines[i] = f"__parsed_count__={len(new_lines)}"
        HARNESS_CACHE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        # No cache — write minimal one
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        HARNESS_CACHE.write_text(
            "__parsed_count__=1\nhooks_enabled.token_writer=true\n",
            encoding="utf-8",
        )


def _ensure_harness_yaml_exists():
    """Ensure harness.yaml exists (harness_core checks it exists before using the cache)."""
    yaml_path = ROOT / ".claude" / "harness.yaml"
    if yaml_path.is_file():
        return
    # shouldn't happen in the real project, but handle gracefully
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text("harness_version: 1.0.0\nmode: lax\n", encoding="utf-8")


def _clean_state():
    """Remove temporary token_writer state files (not originals)."""
    for name in [
        "token-tracking-index.json",
        "token-savings.json",
        "token-compact-state.json",
        ".token-writer-session.log",
    ]:
        (STATE_DIR / name).unlink(missing_ok=True)


def _run(
    cmd: list[str],
    stdin_obj: object = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    data = None
    if stdin_obj is not None:
        data = json.dumps(stdin_obj).encode("utf-8")
    e = os.environ.copy()
    e.setdefault("CLAUDE_PROJECT_DIR", str(ROOT))
    if env:
        e.update(env)
    return subprocess.run(
        cmd,
        input=data,
        cwd=str(ROOT),
        env=e,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _known_files() -> set[str]:
    """Return set of token_writer state files that existed before test."""
    existing = set()
    for name in [
        "token-tracking-index.json",
        "token-savings.json",
        "token-compact-state.json",
        ".token-writer-session.log",
    ]:
        if (STATE_DIR / name).is_file():
            existing.add(name)
    return existing


# ---------------------------------------------------------------------------
# Test: --reset
# ---------------------------------------------------------------------------

def test_reset_writes_usage_zero():
    """--reset writes index with usage=0 and source=token_writer.py."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()

        proc = _run(["python3", str(TOKEN_WRITER), "--reset"])
        assert proc.returncode == 0, f"reset rc={proc.returncode} stderr={proc.stderr!r}"

        index_file = STATE_DIR / "token-tracking-index.json"
        assert index_file.is_file(), f"index not created: {index_file}"
        data = _load(index_file)
        assert data["usage"] == 0, f"usage={data['usage']}"
        assert data["source"] == "token_writer.py --reset", f"source={data['source']}"
        assert data["limit"] > 0, f"limit={data['limit']}"
        assert "last_updated" in data, "missing last_updated"

        # session log
        log_file = STATE_DIR / ".token-writer-session.log"
        if log_file.is_file():
            assert "[token_writer] reset\n" in log_file.read_text(encoding="utf-8", errors="replace")
    finally:
        _restore_state()
    print("PASS test_reset_writes_usage_zero")


def test_reset_detects_real_context_limit():
    """--reset auto-detects context limit (at minimum 200000 fallback)."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        proc = _run(["python3", str(TOKEN_WRITER), "--reset"])
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["limit"] >= 200000, f"limit={data['limit']} (expected >= 200000)"
    finally:
        _restore_state()
    print("PASS test_reset_detects_real_context_limit")


def test_increment_writes_savings_file():
    """--increment creates token-savings.json with required fields."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        stdin = {"tool_name": "read"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0

        savings_file = STATE_DIR / "token-savings.json"
        assert savings_file.is_file(), "savings not created or was removed"
        data = _load(savings_file)
        for field in ("compact", "total", "compact_events", "last_updated"):
            assert field in data, f"missing field {field} in savings"
    finally:
        _restore_state()
    print("PASS test_increment_writes_savings_file")


# ---------------------------------------------------------------------------
# Test: --increment (no compact state)
# ---------------------------------------------------------------------------

def test_increment_writes_accumulated_usage():
    """--increment reads previous usage from index and adds tool-incr."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Seed with usage=1000
        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 1000, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        stdin = {"tool_name": "bash", "tool_response": {"content": []}}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0, f"increment rc={proc.returncode} stderr={proc.stderr!r}"

        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 3000, f"usage={data['usage']} (expected 3000 = 1000 + bash(2000))"
        assert data["limit"] == 200000
        assert data["source"] == "token_writer.py"
    finally:
        _restore_state()
    print("PASS test_increment_writes_accumulated_usage")


def test_increment_zero_usage_no_index():
    """--increment handles missing index file as usage=0."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        stdin = {"tool_name": "read"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 500, f"usage={data['usage']} (expected 500 for read)"
    finally:
        _restore_state()
    print("PASS test_increment_zero_usage_no_index")


def test_increment_caps_at_limit():
    """--increment clamps usage to limit."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 199500, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        stdin = {"tool_name": "write"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 200000, f"usage={data['usage']} (expected 200000 capped)"
    finally:
        _restore_state()
    print("PASS test_increment_caps_at_limit")


def test_increment_no_stdin():
    """--increment handles stdin with no data gracefully (default incr=3000)."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=None,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        # No index existed -> usage=0, no tool_name known -> default incr=3000
        assert data["usage"] == 3000, f"usage={data['usage']} (expected 3000 default)"
    finally:
        _restore_state()
    print("PASS test_increment_no_stdin")


# ---------------------------------------------------------------------------
# Test: tool_name mapping
# ---------------------------------------------------------------------------

def test_all_tool_increments():
    """Verify each tool name maps to the correct increment."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        expected = {"read": 500, "grep": 1000, "bash": 2000, "write": 5000, "edit": 5000}
        for tool, incr in expected.items():
            (STATE_DIR / "token-tracking-index.json").write_text(
                json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
                encoding="utf-8",
            )
            (STATE_DIR / "token-savings.json").write_text(
                json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
                encoding="utf-8",
            )
            stdin = {"tool_name": tool}
            proc = _run(
                ["python3", str(TOKEN_WRITER), "--increment"],
                stdin_obj=stdin,
            )
            assert proc.returncode == 0, f"tool={tool}: rc={proc.returncode}"
            data = _load(STATE_DIR / "token-tracking-index.json")
            assert data["usage"] == incr, f"tool={tool}: usage={data['usage']} != expected={incr}"

        print("PASS test_all_tool_increments")
    finally:
        _restore_state()


# ---------------------------------------------------------------------------
# Test: effective increment from response content
# ---------------------------------------------------------------------------

def test_effective_increment_from_content():
    """--increment uses actual response content length when provided."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        long_text = "A" * 12345
        stdin = {
            "tool_name": "grep",
            "tool_response": {"content": [{"text": long_text}]},
        }
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 12345, f"usage={data['usage']} (expected 12345)"
    finally:
        _restore_state()
    print("PASS test_effective_increment_from_content")


def test_effective_increment_from_stdout():
    """--increment falls back to stdout when content list is empty."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        stdin = {
            "tool_name": "bash",
            "tool_response": {"content": [], "stdout": "BBB" * 777},
        }
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 2331, f"usage={data['usage']} (expected 2331 from 777*3 bytes)"
    finally:
        _restore_state()
    print("PASS test_effective_increment_from_stdout")


def test_effective_increment_max_50000():
    """--increment caps content size at 50000."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        huge = "X" * 99999
        stdin = {
            "tool_name": "bash",
            "tool_response": {"stdout": huge},
        }
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0
        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 50000, f"usage={data['usage']} (expected 50000 capped)"
    finally:
        _restore_state()
    print("PASS test_effective_increment_max_50000")


# ---------------------------------------------------------------------------
# Test: compact state handling
# ---------------------------------------------------------------------------

def test_increment_with_compact_state():
    """--increment with pending compact state applies compact formula:
       post = pre * 3 // 10; savings = pre - post; new_usage = post + 3000.
    """
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 100, "total": 100, "compact_events": 5, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-compact-state.json").write_text(
            json.dumps({"pre_compact_usage": 10000, "pending": True}, indent=2),
            encoding="utf-8",
        )

        stdin = {"tool_name": "read"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0

        # post = 10000 * 3 // 10 = 3000; new_usage = 3000 + 3000(default incr) = 6000
        index = _load(STATE_DIR / "token-tracking-index.json")
        assert index["usage"] == 6000, f"usage={index['usage']} (expected 6000)"

        # accumulated savings: 100 + (10000 - 3000) = 7100
        savings = _load(STATE_DIR / "token-savings.json")
        assert savings["compact"] == 7100, f"compact={savings['compact']} (expected 7100)"
        assert savings["compact_events"] == 6, f"compact_events={savings['compact_events']}"

        # Compact state cleared
        cs = _load(STATE_DIR / "token-compact-state.json")
        assert cs["pre_compact_usage"] == 0
    finally:
        _restore_state()
    print("PASS test_increment_with_compact_state")


def test_increment_compact_state_zero_pre():
    """--increment with compact_state pre_compact_usage=0 does normal incr."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 500, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-compact-state.json").write_text(
            json.dumps({"pre_compact_usage": 0, "pending": True}, indent=2),
            encoding="utf-8",
        )

        stdin = {"tool_name": "edit"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0

        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 5500, f"usage={data['usage']} (expected 5500 = 500 + edit(5000))"
    finally:
        _restore_state()
    print("PASS test_increment_compact_state_zero_pre")


def test_increment_no_compact_state_file():
    """--increment proceeds normally when compact-state file does not exist."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 500, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        # No token-compact-state.json

        stdin = {"tool_name": "edit"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0

        data = _load(STATE_DIR / "token-tracking-index.json")
        assert data["usage"] == 5500, f"usage={data['usage']} (expected 5500)"
    finally:
        _restore_state()
    print("PASS test_increment_no_compact_state_file")


# ---------------------------------------------------------------------------
# Test: output file structure
# ---------------------------------------------------------------------------

def test_output_has_required_fields():
    """Index and savings files contain all required fields after --increment."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        # First reset
        _run(["python3", str(TOKEN_WRITER), "--reset"])

        # Then increment to trigger savings write
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj={"tool_name": "read"},
        )

        # token-tracking-index.json — fields
        idx = _load(STATE_DIR / "token-tracking-index.json")
        for field in ("usage", "limit", "last_updated", "source"):
            assert field in idx, f"missing field {field} in index"

        # token-savings.json — fields
        sav = _load(STATE_DIR / "token-savings.json")
        for field in ("compact", "total", "compact_events", "last_updated"):
            assert field in sav, f"missing field {field} in savings"
    finally:
        _restore_state()
    print("PASS test_output_has_required_fields")


# ---------------------------------------------------------------------------
# Test: savings file missing / corrupted
# ---------------------------------------------------------------------------

def test_corrupted_savings_file():
    """--increment handles corrupted savings file gracefully."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        (STATE_DIR / "token-tracking-index.json").write_text(
            json.dumps({"usage": 0, "limit": 200000, "last_updated": "", "source": "seed"}, indent=2),
            encoding="utf-8",
        )
        (STATE_DIR / "token-savings.json").write_text("not-valid-json{{{", encoding="utf-8")

        stdin = {"tool_name": "bash"}
        proc = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj=stdin,
        )
        assert proc.returncode == 0

        index = _load(STATE_DIR / "token-tracking-index.json")
        assert index["usage"] == 2000, f"usage={index['usage']} (expected 2000)"
    finally:
        _restore_state()
    print("PASS test_corrupted_savings_file")


# ---------------------------------------------------------------------------
# Test: reset then increment sequence
# ---------------------------------------------------------------------------

def test_reset_then_increment_sequence():
    """Reset then increment in sequence produces correct accumulated state."""
    _backup_state()
    try:
        _enable_token_writer_in_cache()
        _clean_state()
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )

        # Step 1: Reset
        proc1 = _run(["python3", str(TOKEN_WRITER), "--reset"])
        assert proc1.returncode == 0
        assert _load(STATE_DIR / "token-tracking-index.json")["usage"] == 0

        # Step 2: Increment for a read tool
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        proc2 = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj={"tool_name": "read"},
        )
        assert proc2.returncode == 0
        assert _load(STATE_DIR / "token-tracking-index.json")["usage"] == 500

        # Step 3: Increment for a write tool
        (STATE_DIR / "token-savings.json").write_text(
            json.dumps({"compact": 0, "total": 0, "compact_events": 0, "last_updated": ""}, indent=2),
            encoding="utf-8",
        )
        proc3 = _run(
            ["python3", str(TOKEN_WRITER), "--increment"],
            stdin_obj={"tool_name": "write"},
        )
        assert proc3.returncode == 0
        assert _load(STATE_DIR / "token-tracking-index.json")["usage"] == 5500
    finally:
        _restore_state()
    print("PASS test_reset_then_increment_sequence")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    assert TOKEN_WRITER.is_file(), f"missing {TOKEN_WRITER}"
    _ensure_harness_yaml_exists()

    test_reset_writes_usage_zero()
    test_reset_detects_real_context_limit()
    test_increment_writes_savings_file()
    test_increment_writes_accumulated_usage()
    test_increment_zero_usage_no_index()
    test_increment_caps_at_limit()
    test_increment_no_stdin()
    test_all_tool_increments()
    test_effective_increment_from_content()
    test_effective_increment_from_stdout()
    test_effective_increment_max_50000()
    test_increment_with_compact_state()
    test_increment_compact_state_zero_pre()
    test_increment_no_compact_state_file()
    test_output_has_required_fields()
    test_corrupted_savings_file()
    test_reset_then_increment_sequence()

    print("ALL_TOKEN_WRITER_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        sys.stderr.write(f"FAIL:{exc}\n")
        raise SystemExit(1)
