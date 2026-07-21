#!/usr/bin/env python3
"""PKG-C mechanical tests: PreCompact / handoff reconcile / mutex / end seal.

Run: python3 .claude/hooks/tests/test_pkg_c_lifecycle.py
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

ROOT = Path(__file__).resolve().parents[3]  # repo root if .claude/hooks/tests/
# robust: walk up until .claude/settings.json exists
_p = Path(__file__).resolve().parent
for _ in range(6):
    if (_p / ".claude" / "settings.json").is_file():
        ROOT = _p
        break
    _p = _p.parent
else:
    ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())).resolve()

HOOKS = ROOT / ".claude" / "hooks"
SSOT = HOOKS / "lib" / "lifecycle_ssot.py"


def _run(cmd, stdin_obj=None, env=None, cwd=None) -> subprocess.CompletedProcess:
    data = None
    if stdin_obj is not None:
        data = json.dumps(stdin_obj).encode("utf-8")
    e = os.environ.copy()
    e["CLAUDE_PROJECT_DIR"] = str(ROOT)
    if env:
        e.update(env)
    return subprocess.run(
        cmd,
        input=data,
        cwd=cwd or str(ROOT),
        env=e,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def setup_tmp_state(tmp: Path):
    """Point state into a writable temp by chdir overlay would be hard;
    instead we use real ROOT state but reset files under a work tree.

    Tests MUST be run on a disposable worktree OR reset state after.
    We sandbox by setting CLAUDE_PROJECT_DIR to a mini fixture tree.
    """
    (tmp / ".claude" / "hooks" / "lib").mkdir(parents=True)
    (tmp / ".claude" / "state" / "snapshots").mkdir(parents=True)
    # copy hooks under test
    for name in [
        "lib/lifecycle_ssot.py",
        "precompact-lifecycle.py",
        "subagent-stop-lifecycle.py",
        "session-end-lifecycle.py",
    ]:
        src = HOOKS / name
        dst = tmp / ".claude" / "hooks" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    (tmp / ".claude" / "hooks" / "lib" / "__init__.py").write_text("", encoding="utf-8")
    # stop-flywheel stub for wrapper tests
    stub = tmp / ".claude" / "hooks" / "stop-flywheel.py"
    stub.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
        encoding="utf-8",
    )
    wrapper_src = HOOKS / "stop-lifecycle-wrapper.sh"
    if wrapper_src.is_file():
        shutil.copy2(wrapper_src, tmp / ".claude" / "hooks" / "stop-lifecycle-wrapper.sh")
        os.chmod(tmp / ".claude" / "hooks" / "stop-lifecycle-wrapper.sh", 0o755)
    return tmp


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_reconcile_forces_written_eq_claimed(tmp: Path):
    # inject distorted claimed
    state = tmp / ".claude" / "state" / "handoff.json"
    state.write_text(
        json.dumps(
            {
                "version": 1,
                "written": 0,
                "claimed": 0,
                "reconciled": False,
                "items": [
                    {"id": "a", "kind": "x", "source": "t", "at": "t", "body": {}},
                    {"id": "b", "kind": "x", "source": "t", "at": "t", "body": {}},
                    {"id": "c", "kind": "x", "source": "t", "at": "t", "body": {}},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # import ssot with CLAUDE_PROJECT_DIR=tmp
    sys.path.insert(0, str(tmp / ".claude" / "hooks"))
    # force reimport
    for mod in list(sys.modules):
        if mod == "lib.lifecycle_ssot" or mod.startswith("lib."):
            del sys.modules[mod]
    os.environ["CLAUDE_PROJECT_DIR"] = str(tmp)
    from lib.lifecycle_ssot import load_handoff, reconcile_handoff  # type: ignore

    hb = load_handoff()
    hb = reconcile_handoff(hb, persist=True)
    assert_true(hb["written"] == 3, f"written!=3: {hb}")
    assert_true(hb["claimed"] == 3, f"claimed!=3: {hb}")
    assert_true(hb["reconciled"] is True or hb["written"] == hb["claimed"], "reconcile flag")
    disk = _load(state)
    assert_true(disk["written"] == 3 and disk["claimed"] == 3, f"disk mismatch {disk}")
    print("PASS test_reconcile_forces_written_eq_claimed")


def test_precompact_fail_closed_and_snapshot(tmp: Path):
    env = {"CLAUDE_PROJECT_DIR": str(tmp)}
    proc = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "precompact-lifecycle.py")],
        stdin_obj={
            "session_id": "sess-pkgc-1",
            "hook_event_name": "PreCompact",
            "transcript_path": "/tmp/t.jsonl",
        },
        env=env,
        cwd=str(tmp),
    )
    assert_true(proc.returncode == 0, f"precompact rc={proc.returncode} err={proc.stderr!r}")
    out = json.loads(proc.stdout.decode("utf-8"))
    assert_true(out.get("ok") is True, out)
    assert_true(out.get("sha256"), "missing sha256")
    snap = Path(out["snapshot"])
    assert_true(snap.is_file(), f"snapshot missing {snap}")
    raw = snap.read_text(encoding="utf-8")
    import hashlib

    dig = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert_true(dig == out["sha256"], "sha mismatch")
    # handoff must contain precompact_flush item and counters match
    hb = _load(tmp / ".claude" / "state" / "handoff.json")
    assert_true(hb["written"] == len(hb["items"]), "counter desync")
    assert_true(hb["claimed"] == hb["written"], "claimed desync")
    assert_true(any(i.get("kind") == "precompact_flush" for i in hb["items"]), "no flush item")
    lc = _load(tmp / ".claude" / "state" / "lifecycle.json")
    assert_true(lc["compact"]["last_sha256"] == dig, "lifecycle compact sha")
    # idempotent second call with same session/transcript
    proc2 = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "precompact-lifecycle.py")],
        stdin_obj={
            "session_id": "sess-pkgc-1",
            "hook_event_name": "PreCompact",
            "transcript_path": "/tmp/t.jsonl",
        },
        env=env,
        cwd=str(tmp),
    )
    assert_true(proc2.returncode == 0, f"precompact2 rc={proc2.returncode}")
    hb2 = _load(tmp / ".claude" / "state" / "handoff.json")
    flush_count = sum(1 for i in hb2["items"] if i.get("kind") == "precompact_flush")
    assert_true(flush_count == 1, f"not idempotent flush_count={flush_count}")
    print("PASS test_precompact_fail_closed_and_snapshot")


def test_precompact_fail_on_ro_snapshot_dir(tmp: Path):
    snap = tmp / ".claude" / "state" / "snapshots"
    # make snapshots a file so write fails
    if snap.exists():
        shutil.rmtree(snap)
    snap.write_text("not-a-dir", encoding="utf-8")
    env = {"CLAUDE_PROJECT_DIR": str(tmp)}
    proc = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "precompact-lifecycle.py")],
        stdin_obj={"session_id": "sess-fail", "hook_event_name": "PreCompact"},
        env=env,
        cwd=str(tmp),
    )
    assert_true(proc.returncode == 2, f"expected 2 got {proc.returncode}")
    err = proc.stderr.decode("utf-8", errors="replace")
    assert_true("PRECOMPACT_FAIL:" in err, err)
    # restore dir for later tests
    snap.unlink()
    snap.mkdir(parents=True)
    print("PASS test_precompact_fail_on_ro_snapshot_dir")


def test_goal_ghost_mutex(tmp: Path):
    os.environ["CLAUDE_PROJECT_DIR"] = str(tmp)
    for mod in list(sys.modules):
        if mod == "lib.lifecycle_ssot" or mod.startswith("lib."):
            del sys.modules[mod]
    sys.path.insert(0, str(tmp / ".claude" / "hooks"))
    from lib.lifecycle_ssot import set_mode  # type: ignore

    set_mode("goal", goal_id="G1")
    try:
        set_mode("ghost", ghost_id="X1")
        raise AssertionError("mutex should block ghost while goal")
    except ValueError as e:
        assert_true("LIFECYCLE_MUTEX:" in str(e), str(e))
    # reset to idle then ghost
    set_mode("idle")
    set_mode("ghost", ghost_id="X1")
    try:
        set_mode("goal", goal_id="G2")
        raise AssertionError("mutex should block goal while ghost")
    except ValueError as e:
        assert_true("LIFECYCLE_MUTEX:" in str(e), str(e))
    # disk must not have both ids
    lc = _load(tmp / ".claude" / "state" / "lifecycle.json")
    both = bool(lc.get("goal_id")) and bool(lc.get("ghost_id"))
    assert_true(not both, f"both ids set: {lc}")
    print("PASS test_goal_ghost_mutex")


def test_subagent_stop_and_session_end(tmp: Path):
    env = {"CLAUDE_PROJECT_DIR": str(tmp)}
    # ensure clean lifecycle mode first
    os.environ["CLAUDE_PROJECT_DIR"] = str(tmp)
    for mod in list(sys.modules):
        if mod == "lib.lifecycle_ssot" or mod.startswith("lib."):
            del sys.modules[mod]
    sys.path.insert(0, str(tmp / ".claude" / "hooks"))
    from lib.lifecycle_ssot import set_mode  # type: ignore

    set_mode("idle")
    set_mode("goal", goal_id="G-end")

    p1 = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "subagent-stop-lifecycle.py")],
        stdin_obj={
            "session_id": "sess-end",
            "agent_id": "agent-9",
            "agent_type": "executor",
            "hook_event_name": "SubagentStop",
        },
        env=env,
        cwd=str(tmp),
    )
    assert_true(p1.returncode == 0, p1.stderr.decode())
    # idempotent
    p1b = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "subagent-stop-lifecycle.py")],
        stdin_obj={
            "session_id": "sess-end",
            "agent_id": "agent-9",
            "agent_type": "executor",
            "hook_event_name": "SubagentStop",
        },
        env=env,
        cwd=str(tmp),
    )
    assert_true(p1b.returncode == 0, p1b.stderr.decode())
    hb = _load(tmp / ".claude" / "state" / "handoff.json")
    n_sub = sum(1 for i in hb["items"] if i.get("kind") == "subagent_stop")
    assert_true(n_sub == 1, f"subagent not idempotent {n_sub}")

    p2 = _run(
        ["python3", str(tmp / ".claude" / "hooks" / "session-end-lifecycle.py")],
        stdin_obj={"session_id": "sess-end", "hook_event_name": "Stop"},
        env=env,
        cwd=str(tmp),
    )
    assert_true(p2.returncode == 0, p2.stderr.decode())
    lc = _load(tmp / ".claude" / "state" / "lifecycle.json")
    assert_true(lc["mode"] == "idle", lc)
    assert_true(lc["goal_id"] is None and lc["ghost_id"] is None, lc)
    assert_true(lc["end"]["sealed"] is True, lc)
    hb2 = _load(tmp / ".claude" / "state" / "handoff.json")
    assert_true(hb2["written"] == hb2["claimed"] == len(hb2["items"]), hb2)
    # wrapper if present
    wrap = tmp / ".claude" / "hooks" / "stop-lifecycle-wrapper.sh"
    if wrap.is_file():
        p3 = _run(
            ["bash", str(wrap)],
            stdin_obj={"session_id": "sess-end", "hook_event_name": "Stop"},
            env=env,
            cwd=str(tmp),
        )
        assert_true(p3.returncode == 0, p3.stderr.decode())
    print("PASS test_subagent_stop_and_session_end")


def test_settings_registered():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    # 核心预执行门禁和用户提交钩子必须注册
    for ev in ("PreToolUse", "UserPromptSubmit"):
        assert_true(ev in hooks, f"missing hook event {ev}")
    print("PASS test_settings_registered")


def main() -> int:
    assert_true(SSOT.is_file(), f"missing {SSOT}")
    test_settings_registered()
    tmp = Path(tempfile.mkdtemp(prefix="pkgc-"))
    try:
        setup_tmp_state(tmp)
        test_reconcile_forces_written_eq_claimed(tmp)
        test_precompact_fail_closed_and_snapshot(tmp)
        test_precompact_fail_on_ro_snapshot_dir(tmp)
        test_goal_ghost_mutex(tmp)
        test_subagent_stop_and_session_end(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("ALL_PKG_C_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        sys.stderr.write(f"FAIL:{exc}\n")
        raise SystemExit(1)
