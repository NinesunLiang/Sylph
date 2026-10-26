#!/usr/bin/env python3
"""
capture_evidence.py — capture focused CarrorOS acceptance evidence into evidence.jsonl.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
EVIDENCE = PROJECT / ".omc/metrics/runtime-verify/evidence.jsonl"


def record(name, status, detail, output=""):
    rec = {
        "test": name,
        "status": status,
        "detail": detail[:500],
        "output": output[:1000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with EVIDENCE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def run(name, cmd, expect):
    try:
        r = subprocess.run(cmd, cwd=str(PROJECT), capture_output=True, text=True, timeout=60)
        output = (r.stdout or "") + (("\nSTDERR:\n" + r.stderr) if r.stderr else "")
        ok = r.returncode == 0 and expect(r.returncode, r.stdout, r.stderr)
        record(name, "PASS" if ok else "FAIL", f"exit={r.returncode}", output)
        return ok
    except Exception as exc:
        record(name, "FAIL", type(exc).__name__, str(exc))
        return False


def main() -> int:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(PROJECT), capture_output=True, text=True, timeout=5)
    failures.append(git.returncode != 0)
    record("META", "PASS" if git.returncode == 0 else "FAIL", f"git_commit={git.stdout.strip()}", "evidence capture")

    python = sys.executable
    failures.append(not run(
        "R2-PHASE3-MATRIX",
        [python, ".claude/scripts/phase3_matrix_test.py"],
        lambda rc, out, err: rc == 0 and "PASS" in out.upper(),
    ))
    failures.append(not run(
        "R3-NEGATIVE-TESTS",
        [python, ".claude/scripts/negative_tests.py"],
        lambda rc, out, _err: rc == 0 and "11/11 PASS" in out and "CAS_CONFLICT" in out,
    ))
    failures.append(not run(
        "R4-CAS-STALE-STRUCTURED-EVIDENCE",
        [python, "-m", "json.tool", ".omc/metrics/runtime-verify/h-cas-stale-evidence.json"],
        lambda rc, _out, _err: rc == 0,
    ))
    # index47：原 G4/G5 依赖 h-water-*.json，由 ga_behavioral_validation 的 water 场景产生。
    # 该场景实为自封循环——它验证的 g6-budget 门其实是依赖安装检查点，且水位防线在门禁层
    # 从无实现（grep 无命中）。故连同场景一并删除，不作为验收证据。
    failures.append(not run(
        "GA-BEHAVIORAL-VALIDATION",
        [python, ".claude/scripts/ga_behavioral_validation.py"],
        lambda rc, _out, _err: rc == 0,
    ))
    for name, path in [
        ("G1-CONCURRENT-WRITER-CONFLICT", ".omc/metrics/runtime-verify/h-concurrent-writer-conflict.json"),
        ("G2-ARTIFACT-MISSING", ".omc/metrics/runtime-verify/h-artifact-missing.json"),
        ("G3-L5-RECOVERY", ".omc/metrics/runtime-verify/h-l5-recovery.json"),
    ]:
        failures.append(not run(name, [python, "-m", "json.tool", path], lambda rc, _out, _err: rc == 0))
    print(f"Evidence captured: {EVIDENCE}")
    return 1 if any(failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
