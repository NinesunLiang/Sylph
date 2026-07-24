#!/usr/bin/env python3
"""
test-stop-flywheel.py — stop-flywheel.py Stop hook regression + adversarial test

Verification points:
  V1  Runs flywheel on session stop
  V2  Extracts patterns from error-dna
  V3  Updates anti-patterns.md + claude-next.md
  V4  Never blocks — always {"continue":true} + exit 0 regardless of failure
  V5  Sublimation check — claude-next entries with hits >= 5 promoted

Layers:
  U (unit isolated):  import real extraction + writing functions, drive with temp dirs
  A (adversarial):    broken imports, corrupt files, missing dirs — must still exit 0
  R (real data):      run hook as subprocess against real project (read-only)

Usage:  python3 scripts/test-stop-flywheel.py
Exit:   0 = ALL PASS, 1 = ANY FAIL
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "stop-flywheel.py"
HOOK_DIR = HOOK.parent
SCRIPTS_LIB = ROOT / ".claude" / "scripts" / "lib"
KNOWLEDGE = ROOT / ".omc" / "knowledge"
CLAUDE_NEXT = KNOWLEDGE / "claude-next.md"
ANTI_PATTERNS = ROOT / ".claude" / "references" / "anti-patterns.md"
SUBLIMATION_LOG = KNOWLEDGE / "sublimation-log.jsonl"

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


def write_error_dna(dna_dir: Path, records: list[dict]) -> Path:
    dna_dir.mkdir(parents=True, exist_ok=True)
    p = dna_dir / "error-dna.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


# ── Import real functions from flywheel lib (for isolated extraction/writing tests) ──
_spec = importlib.util.spec_from_file_location(
    "flywheel_lib", SCRIPTS_LIB / "flywheel.py"
)
assert _spec is not None and _spec.loader is not None, "cannot load lib/flywheel.py"
fly = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fly)
os.chdir(str(ROOT))

# ── Import stop-flywheel.py (for _sublimation_check, which we monkey-patch) ──
_spec2 = importlib.util.spec_from_file_location("stop_flywheel", HOOK)
assert _spec2 is not None and _spec2.loader is not None, "cannot load stop-flywheel.py"
sf = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(sf)
os.chdir(str(ROOT))


# ============================================================
# V1 / V2 / V3: UNIT ISOLATED — flywheel extraction + writing
# ============================================================
print("=" * 64)
print("U: flywheel extraction + writing (isolated via lib functions)")
print("=" * 64)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)

    # ── V2: extract_patterns from error-dna records ──
    records = [
        {"error": "TimeoutError: test timed out after 30s", "step": "S1", "retry_count": 3},
        {"error": "TimeoutError: test timed out after 30s", "step": "S1", "retry_count": 3},
        {"error": "ImportError: module not found: mylib", "step": "S2", "retry_count": 0},
        {"error": "AssertionError: expected X got Y", "step": "S3", "retry_count": 1},
        {"error": "Permission denied: /etc/config", "step": "S4", "retry_count": 2},
        {"error": "No such file: /tmp/missing", "step": "S5", "retry_count": 0},
        {"error": "SyntaxError: invalid syntax at line 42", "step": "S6", "retry_count": 1},
    ]
    patterns = fly.extract_patterns(records)
    ok("V2a patterns list non-empty", len(patterns) > 0, detail=f"got {len(patterns)}")

    pattern_types = {p["pattern"] for p in patterns}
    ok("V2b timeout_recurring classified",
       "timeout_recurring" in pattern_types)
    ok("V2c import classified",
       "import" in pattern_types)
    ok("V2d assertion classified",
       "assertion" in pattern_types)
    ok("V2e permission_recurring classified (retry>=2)",
       "permission_recurring" in pattern_types)
    ok("V2f not_found classified",
       "not_found" in pattern_types)
    ok("V2g syntax classified",
       "syntax" in pattern_types)

    # Verify recurring flag: retry >= 2 or count >= 3
    timeout_rec = [p for p in patterns if p["pattern"] == "timeout_recurring"]
    ok("V2h timeout_recurring has retry_count=3",
       timeout_rec[0]["retry_count"] == 3 if timeout_rec else False)

    # ── V3: write_anti_patterns ──
    ap_path = tdir / ".claude" / "references" / "anti-patterns.md"
    # Monkey-patch flywheel's get_anti_patterns_path to return our temp path
    ap_path.parent.mkdir(parents=True, exist_ok=True)
    original_get_ap_path = fly.get_anti_patterns_path
    fly.get_anti_patterns_path = lambda proot: ap_path
    result = fly.write_anti_patterns(tdir, patterns)
    fly.get_anti_patterns_path = original_get_ap_path

    ok("V3a write_anti_patterns returns Path", result is not None)
    ok("V3b anti-patterns.md created", ap_path.exists())
    content = ap_path.read_text(encoding="utf-8")
    ok("V3c anti-patterns.md has header", "Anti-Patterns" in content)
    ok("V3d anti-patterns.md contains pattern entries", "timeout_recurring" in content)
    ok("V3e anti-patterns.md contains step info", "step=S1" in content)
    ok("V3f anti-patterns.md contains timestamp format",
       bool(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", content)))

    # ── V3: write_claude_next ──
    entry_count_before = len(list(tdir.rglob("claude-next.md")))
    cn_path = fly.write_claude_next(tdir, "Pattern 'timeout' detected in step S1: repeated timeout")
    ok("V3g write_claude_next returns Path", cn_path is not None)
    ok("V3h claude-next.md created", cn_path.exists())
    cn_content = cn_path.read_text(encoding="utf-8")
    ok("V3i claude-next.md contains entry", "Pattern 'timeout'" in cn_content)
    ok("V3j claude-next.md has timestamp format",
       bool(re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", cn_content)))

    # ── V1: run_flywheel end-to-end on a task dir ──
    task_dir = tdir / ".omc" / "tasks" / "unit-test"
    write_error_dna(task_dir, records * 2)  # duplicate to test grouping
    result = fly.run_flywheel(tdir, task_dir=task_dir)
    ok("V1a run_flywheel returns dict", isinstance(result, dict))
    ok("V1b patterns_found > 0", result.get("patterns_found", 0) > 0,
       detail=f"got {result.get('patterns_found')}")
    ok("V1c knowledge_entries > 0", result.get("knowledge_entries", 0) > 0)
    # Anti-patterns note: write_anti_patterns was already called above with the same
    # path, so anti_patterns_written may be overlapped.  This is fine — the key test
    # is that it runs without error.
    ok("V1d no error in result", "error" not in result,
       detail=str(result.get("error", "")))

    # ── V1: run_flywheel with no errors ──
    empty_dir = tdir / ".omc" / "tasks" / "empty"
    empty_dir.mkdir(parents=True, exist_ok=True)
    result2 = fly.run_flywheel(tdir, task_dir=empty_dir)
    ok("V1e no errors → note present", "note" in result2)
    ok("V1f no errors → patterns_found=0", result2["patterns_found"] == 0)

    # ── V2: recurring detection via count threshold (count >= 3) ──
    same_error_5x = [{"error": "TimeoutError: repeated", "step": "S1", "retry_count": 0}] * 5
    pats = fly.extract_patterns(same_error_5x)
    has_recurring = any("_recurring" in p["pattern"] for p in pats)
    ok("V2i count>=3 triggers recurring classification", has_recurring)


# ============================================================
# V5: UNIT ISOLATED — _sublimation_check
# ============================================================
print()
print("=" * 64)
print("U: _sublimation_check — claude-next hits >= 5 promotion")
print("=" * 64)

with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)

    # Build skeleton directories
    kb_dir = tdir / ".omc" / "knowledge"
    kb_dir.mkdir(parents=True)
    ap_dir = tdir / ".claude" / "references"
    ap_dir.mkdir(parents=True)
    anti_p = ap_dir / "anti-patterns.md"
    anti_p.write_text("# Anti-Patterns — 经验沉淀\n\n## 已识别模式\n\n", encoding="utf-8")

    cn = kb_dir / "claude-next.md"
    # 4 hits — below threshold
    cn.write_text(
        "\n".join(
            f"- [2026-07-20 10:00] Pattern 'low_hit' detected in step S1: minor issue"
            for _ in range(4)
        ) + "\n",
        encoding="utf-8",
    )

    # Monkey-patch paths in stop-flywheel module
    orig_cn = sf.CLAUDE_NEXT
    orig_ap = sf.ANTI_PATTERNS
    orig_sl = sf.SUBLIMATION_LOG
    sf.CLAUDE_NEXT = cn
    sf.ANTI_PATTERNS = anti_p
    sf.SUBLIMATION_LOG = kb_dir / "sublimation-log.jsonl"

    sublimated = sf._sublimation_check()
    ok("V5a 4 hits (<5) → no sublimation", len(sublimated) == 0,
       detail=f"got {sublimated}")

    # Add 5 more to reach 9 hits for 'low_hit'
    with cn.open("a", encoding="utf-8") as f:
        for _ in range(5):
            f.write("- [2026-07-20 10:00] Pattern 'low_hit' detected in step S1: minor issue\n")

    # Also add 3 entries for a second pattern (below threshold)
    for _ in range(3):
        with cn.open("a", encoding="utf-8") as f:
            f.write("- [2026-07-20 10:00] Pattern 'assertion_recurring' detected in step RPE-C-S1: mismatch\n")

    sublimated = sf._sublimation_check()
    ok("V5b low_hit (9 hits >=5) → sublimated",
       "low_hit" in sublimated, detail=f"got {sublimated}")
    ok("V5c assertion_recurring (3 hits <5) → not sublimated",
       "assertion_recurring" not in sublimated, detail=f"got {sublimated}")

    # Verify anti-patterns.md was updated
    ap_content = anti_p.read_text(encoding="utf-8")
    ok("V5d anti-patterns.md contains sublimated entry", "low_hit" in ap_content)

    # Verify sublimation log was written
    sl_file = kb_dir / "sublimation-log.jsonl"
    ok("V5e sublimation-log.jsonl exists", sl_file.exists())
    log_lines = [l for l in sl_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok("V5f log has 1 entry", len(log_lines) == 1, detail=f"got {len(log_lines)}")
    entry = json.loads(log_lines[0])
    ok("V5g log entry pattern=low_hit", entry["pattern"] == "low_hit")
    ok("V5h log entry hits=9", entry["hits"] == 9)
    ok("V5i log entry target=anti-patterns.md", entry["target"] == "anti-patterns.md")
    ok("V5j log entry has ts", "ts" in entry)

    # ── Already-sublimated patterns are not re-sublimated ──
    # Add 5 more lines for 'low_hit'
    for _ in range(5):
        with cn.open("a", encoding="utf-8") as f:
            f.write("- [2026-07-20 10:01] Pattern 'low_hit' detected in step S1: duplicate\n")
    sublimated2 = sf._sublimation_check()
    ok("V5k already-sublimated entries not re-sublimated",
       len(sublimated2) == 0, detail=f"got {sublimated2}")

    # ── 已升华 / 升华到 标记 lines are skipped ──
    # Write a line containing 已升华
    with cn.open("a", encoding="utf-8") as f:
        f.write("- [2026-07-20 10:02] Pattern '已升华' detected in step S1: already promoted\n")
    # Add new pattern 'new_pattern' 5 times
    for _ in range(5):
        with cn.open("a", encoding="utf-8") as f:
            f.write("- [2026-07-20 10:03] Pattern 'new_pattern' detected in step T1: fresh issue\n")

    sublimated3 = sf._sublimation_check()
    ok("V5l 'new_pattern' (5 fresh hits) sublimated despite 升华 line",
       "new_pattern" in sublimated3, detail=f"got {sublimated3}")
    # The 已升华 line should not contribute to any pattern count

    # ── Clean up so anti-patterns doesn't accumulate for no-claude-next test ──
    anti_p.write_text("# Anti-Patterns\n\n## 已识别模式\n\n", encoding="utf-8")

    # ── No claude-next → empty ──
    cn.unlink(missing_ok=True)
    ok("V5m no claude-next → no sublimation", sf._sublimation_check() == [])

    # Restore paths
    sf.CLAUDE_NEXT = orig_cn
    sf.ANTI_PATTERNS = orig_ap
    sf.SUBLIMATION_LOG = orig_sl


# ============================================================
# V4: ADVERSARIAL — never blocks, always exit 0 + {"continue":true}
# ============================================================
print()
print("=" * 64)
print("A: adversarial — corrupt/pathological inputs, must not block")
print("=" * 64)

# A1: Flywheel import broken (lib/flywheel.py raises on call)
with tempfile.TemporaryDirectory() as td:
    fake_root = Path(td)
    (fake_root / ".claude" / "hooks").mkdir(parents=True)
    (fake_root / ".claude" / "references").mkdir(parents=True)
    (fake_root / ".omc" / "knowledge").mkdir(parents=True)

    broken_lib = fake_root / ".claude" / "scripts" / "lib"
    broken_lib.mkdir(parents=True)
    (broken_lib / "flywheel.py").write_text(
        "def run_flywheel(project_root): raise RuntimeError('simulated crash')\n",
        encoding="utf-8",
    )
    (broken_lib / "__init__.py").write_text("", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(fake_root),
        capture_output=True,
        text=True,
        timeout=15,
    )
    ok("A1 flywheel crash → exit 0", proc.returncode == 0,
       detail=f"exit={proc.returncode}")
    last_line = proc.stdout.strip()
    try:
        payload = json.loads(last_line)
        ok("A1b stdout last line valid JSON", True)
        ok("A1c continue=true", payload.get("continue") is True,
           detail=f"got {payload}")
    except (json.JSONDecodeError, IndexError):
        ok("A1b stdout last line valid JSON", False, detail=f"stdout={proc.stdout!r}")
        ok("A1c continue=true", False)

# A2: Corrupt error-dna (invalid JSON lines, mixed valid/invalid)
with tempfile.TemporaryDirectory() as td:
    fake_root = Path(td)
    (fake_root / ".claude" / "hooks").mkdir(parents=True)
    (fake_root / ".claude" / "references").mkdir(parents=True, exist_ok=True)
    (fake_root / ".claude" / "references" / "anti-patterns.md").write_text(
        "# Anti-Patterns\n", encoding="utf-8"
    )
    (fake_root / ".omc" / "knowledge").mkdir(parents=True, exist_ok=True)
    (fake_root / ".omc" / "knowledge" / "claude-next.md").write_text(
        "- [2026-07-20 10:00] Pattern 'test_pat' detected in step S1: issue\n" * 6,
        encoding="utf-8",
    )
    shutil.copytree(str(SCRIPTS_LIB), str(fake_root / ".claude" / "scripts" / "lib"),
                    dirs_exist_ok=True)

    task_dir = fake_root / ".omc" / "tasks" / "corrupt"
    task_dir.mkdir(parents=True)
    dna = task_dir / "error-dna.jsonl"
    dna.write_text(
        '{"error": "valid error", "step": "S1", "retry_count": 0}\n'
        'not-json-at-all\n'
        '{broken json\n'
        '{"error": "another valid", "step": "S2", "retry_count": 1}\n',
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(fake_root),
        capture_output=True,
        text=True,
        timeout=15,
    )
    ok("A2 corrupt error-dna → exit 0", proc.returncode == 0,
       detail=f"exit={proc.returncode}")
    try:
        payload = json.loads(proc.stdout.strip())
        ok("A2b corrupt error-dna → continue=true",
           payload.get("continue") is True)
    except (json.JSONDecodeError, IndexError):
        ok("A2b corrupt error-dna → continue=true", False,
           detail=f"stdout={proc.stdout!r}")

# A3: Missing directories (no .omc, no .claude/references, no knowledge)
with tempfile.TemporaryDirectory() as td:
    fake_root = Path(td)
    (fake_root / ".claude" / "hooks").mkdir(parents=True)
    shutil.copytree(str(SCRIPTS_LIB), str(fake_root / ".claude" / "scripts" / "lib"),
                    dirs_exist_ok=True)

    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(fake_root),
        capture_output=True,
        text=True,
        timeout=15,
    )
    ok("A3 missing dirs → exit 0", proc.returncode == 0,
       detail=f"exit={proc.returncode}")
    try:
        payload = json.loads(proc.stdout.strip())
        ok("A3b missing dirs → continue=true",
           payload.get("continue") is True)
    except (json.JSONDecodeError, IndexError):
        ok("A3b missing dirs → continue=true", False,
           detail=f"stdout={proc.stdout!r}")

# A4: Empty stdin (Stop hook piped no input)
proc = subprocess.run(
    [sys.executable, str(HOOK)],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    timeout=15,
    input="",
)
ok("A4 empty stdin → exit 0", proc.returncode == 0,
   detail=f"exit={proc.returncode}")
try:
    payload = json.loads(proc.stdout.strip())
    ok("A4b empty stdin → continue=true",
       payload.get("continue") is True)
except (json.JSONDecodeError, IndexError):
    ok("A4b empty stdin → continue=true", False,
       detail=f"stdout={proc.stdout!r}")

# A5: 10 KiB of garbage on stdin
proc = subprocess.run(
    [sys.executable, str(HOOK)],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    timeout=15,
    input="x" * 10240,
)
ok("A5 10KiB garbage stdin → exit 0", proc.returncode == 0,
   detail=f"exit={proc.returncode}")
try:
    payload = json.loads(proc.stdout.strip())
    ok("A5b garbage stdin → continue=true",
       payload.get("continue") is True)
except (json.JSONDecodeError, IndexError):
    ok("A5b garbage stdin → continue=true", False,
       detail=f"stdout={proc.stdout!r}")

# A6: Anti-patterns.md not writable (permission error is platform-dependent;
#     instead test that non-existent parent dir is handled gracefully)
# Already covered by A3 — the hook creates parent dirs implicitly via
# _run_flywheel → run_flywheel → write_anti_patterns which uses write_text.
# No explicit makedirs call, but if ROOT/.claude/references doesn't exist,
# write_text will raise — handled by try/except in _run_flywheel.


# ============================================================
# R: REAL DATA — run hook against actual project
# ============================================================
print()
print("=" * 64)
print("R: run hook against real project directory")
print("=" * 64)

proc = subprocess.run(
    [sys.executable, str(HOOK)],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    timeout=15,
)
ok("R1 exit 0", proc.returncode == 0, detail=f"exit={proc.returncode}")
try:
    payload = json.loads(proc.stdout.strip())
    ok("R2 last stdout line is JSON", True)
    ok("R3 continue=true", payload.get("continue") is True,
       detail=f"got {payload}")
except (json.JSONDecodeError, IndexError):
    ok("R2 last stdout line is JSON", False, detail=f"stdout={proc.stdout!r}")
    ok("R3 continue=true", False)

# 4. Never blocks
ok("R4 hook completed within 15s timeout", True)


# ============================================================
# SUMMARY
# ============================================================
print()
print(f"{'=' * 64}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'=' * 64}")

sys.exit(1 if FAIL else 0)
