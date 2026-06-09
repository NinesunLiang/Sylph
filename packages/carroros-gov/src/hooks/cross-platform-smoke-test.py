#!/usr/bin/env python3
"""cross-platform-smoke-test.py — SessionStart — 检测 stat 和 sed 的跨平台兼容性
Role: 检测 stat 和 sed 的跨平台兼容性，永不阻断
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def _run(args, timeout=5):
    """Run a shell command, return (stdout, stderr, rc)."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except Exception:
        return "", "error", -1


def main():
    # ── Guard ──
    if not hc_enabled("cross_platform_smoke_test"):
        print('{"continue": true}')
        sys.exit(0)

    has_problem = False
    this_file = os.path.abspath(__file__)

    # ─── Check stat command ───
    if shutil.which("stat"):
        stdout, stderr, rc = _run(["stat", "--version"])
        combined = (stdout + stderr).lower()

        if any(x in combined for x in ("usage", "illegal option", "invalid option", "unrecognized")):
            # macOS stat (BSD variant)
            r = subprocess.run(["stat", "-f", "%m", this_file], capture_output=True, timeout=5)
            if r.returncode != 0:
                flywheel_event("cross_platform_smoke_test", "stat_macos_broken", "P3", "carror-os")
                has_problem = True
        else:
            # Linux stat (GNU variant)
            r = subprocess.run(["stat", "-c", "%Y", this_file], capture_output=True, timeout=5)
            if r.returncode != 0:
                flywheel_event("cross_platform_smoke_test", "stat_linux_broken", "P3", "carror-os")
                has_problem = True
    else:
        flywheel_event("cross_platform_smoke_test", "stat_missing", "P3", "carror-os")
        has_problem = True

    # ─── Check sed command ───
    if shutil.which("sed"):
        stdout, stderr, rc = _run(["sed", "--version"])
        if "gnu" in (stdout + stderr).lower():
            # GNU sed — fine
            pass
        else:
            # BSD sed — check -i.bak
            try:
                r = subprocess.run(
                    ["sed", "-i.bak", "s/test/ok/", "/dev/null"],
                    capture_output=True, timeout=5,
                    input="test\n", text=True
                )
            except Exception:
                r = subprocess.run(
                    ["sed", "-i.bak", "s/test/ok/", "/dev/null"],
                    capture_output=True, timeout=5
                )
            if r.returncode != 0:
                flywheel_event("cross_platform_smoke_test", "sed_bsd_issue", "P3", "carror-os")
                has_problem = True
    else:
        flywheel_event("cross_platform_smoke_test", "sed_missing", "P3", "carror-os")
        has_problem = True

    # ─── Summary ───
    if has_problem:
        sys.stderr.write("[cross-platform-smoke-test] WARN: 检测到跨平台兼容性问题，已记录 flywheel\n")

    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
