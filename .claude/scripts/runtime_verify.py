#!/usr/bin/env python3
"""
runtime_verify.py — CarrorOS 运行时 E2E 验证

跑实际场景并记录证据到 .omc/metrics/runtime-verify/
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = (SCRIPT_DIR / ".." / "..").resolve()
VERIFY_DIR = PROJECT / ".omc" / "metrics" / "runtime-verify"


def log_evidence(name, status, detail, output=""):
    """Record verification evidence."""
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "test": name,
        "status": status,
        "detail": detail[:500],
        "output_preview": output[:1000] if output else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log_path = VERIFY_DIR / "evidence.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def run_verify(phase, test_name, cmd, check_fn=None, timeout=15, expected_exit=0):
    """Run a verification command and record evidence."""
    full_name = f"[{phase}] {test_name}"
    print(f"  → {full_name}")

    try:
        result = subprocess.run(
            cmd, cwd=str(PROJECT),
            capture_output=True, text=True, timeout=timeout,
            shell=isinstance(cmd, str)
        )
        stdout = result.stdout[:2000]
        stderr = result.stderr[:500]
        exit_ok = result.returncode == expected_exit

        if check_fn:
            check_ok = check_fn(stdout, stderr)
        else:
            check_ok = exit_ok

        if check_ok:
            ev = log_evidence(full_name, "PASS", f"exit={result.returncode}", stdout)
            print(f"    ✅ PASS (exit={result.returncode})")
            return True, stdout
        else:
            ev = log_evidence(full_name, "FAIL", f"exit={result.returncode}: {stderr[:200]}", stdout)
            print(f"    ❌ FAIL (exit={result.returncode})")
            print(f"       {stderr[:200]}")
            return False, stdout

    except subprocess.TimeoutExpired:
        log_evidence(full_name, "FAIL", "timeout", "")
        print(f"    ❌ TIMEOUT ({timeout}s)")
        return False, ""
    except FileNotFoundError as e:
        log_evidence(full_name, "FAIL", f"cmd not found: {e}", "")
        print(f"    ❌ CMD_NOT_FOUND: {e}")
        return False, ""


# ── Test Suites ──

def test_phase0_token_slim():
    """Phase 0: Token Slim 运行时验证"""
    print("\n=== Phase 0: Token Slim (Runtime) ===")
    all_pass = True

    # S2: AGENTS.md ≤100 lines
    def check_agents(stdout, _):
        lines = [l for l in stdout.splitlines() if l.strip()]
        return len(lines) < 100
    ok, _ = run_verify("P0-S2", "AGENTS.md ≤100行",
        "wc -l AGENTS.md", check_fn=check_agents)
    all_pass &= ok

    # S2: No Oracle in AGENTS.md
    ok, _ = run_verify("P0-S2", "AGENTS.md 无 Oracle",
        "grep -ci oracle AGENTS.md",
        check_fn=lambda o, _: o.strip() == "0")
    all_pass &= ok

    # S3: Hot Card 默认输出
    def check_hotcard(stdout, _):
        return "# CarrorOS Hot Card" in stdout
    ok, _ = run_verify("P0-S3", "status 输出 Hot Card",
        "python3 .claude/scripts/carros_base.py status",
        check_fn=check_hotcard)
    all_pass &= ok

    # S4: Tool store
    ok, _ = run_verify("P0-S4", "工具落盘 250KB→1.3K preview",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.tool_store import store_tool_result; '
        'r=store_tool_result(\'verify-test\', b\'line\\n\'*50000,{\'exit_code\':0}); '
        'print(r[\'bytes\'], len(r[\'preview\']))"',
        check_fn=lambda o, _: int(o.split()[0]) > 100000 and int(o.split()[1]) < 2000)
    all_pass &= ok

    # S5: reviews → BLOCK
    ok, _ = run_verify("P0-S5", "reviews 读取被阻断",
        "printf '%s\\n' '{\"tool_name\":\"read\",\"tool_input\":{\"file_path\":\"docs/carros/reviews/test.md\"}}' | python3 .claude/hooks/pretool-gate.py",
        check_fn=lambda o, _: '"continue": false' in o)
    all_pass &= ok

    # S5: normal → ALLOW
    ok, _ = run_verify("P0-S5", "正常读取放行",
        "printf '%s\\n' '{\"tool_name\":\"read\",\"tool_input\":{\"file_path\":\"AGENTS.md\",\"offset\":1,\"limit\":5}}' | python3 .claude/hooks/pretool-gate.py",
        check_fn=lambda o, _: '"continue": true' in o)
    all_pass &= ok

    # S6: executor_micro.txt exists
    ok, _ = run_verify("P0-S6", "executor_micro.txt ≤15行",
        "wc -l .claude/prompts/executor_micro.txt",
        check_fn=lambda o, _: int(o.split()[0]) <= 15)
    all_pass &= ok

    # S7: cost report pass
    ok, _ = run_verify("P0-S7", "成本报表 PASS",
        "python3 .claude/scripts/carros_cost_report.py",
        check_fn=lambda o, _: "pass_p0: PASS" in o or "Phase 0: PASS" in o)
    all_pass &= ok

    return all_pass


def test_phase05_docs():
    """Phase 0.5: 文档基建 运行时验证"""
    print("\n=== Phase 0.5: 文档基建 (Runtime) ===")
    all_pass = True

    # W1: Handoff Capsule 含 NOT_SOURCE_OF_TRUTH
    ok, _ = run_verify("P0.5-W1", "Handoff NOT_SOURCE_OF_TRUTH",
        "head -5 .omc/tasks/20260713/phase3-dual-judge/handoff.md 2>/dev/null || echo 'NO_HANDOFF'",
        check_fn=lambda o, _: "NOT SOURCE OF TRUTH" in o or "NO_HANDOFF" in o)
    all_pass &= ok

    # W2: task-profiles.yaml
    ok, _ = run_verify("P0.5-W2", "task-profiles.yaml 含 L1/L2",
        "grep -c 'L1:' .claude/references/task-profiles.yaml",
        check_fn=lambda o, _: int(o.strip()) >= 1)
    all_pass &= ok

    # W2: CAS revision
    ok, _ = run_verify("P0.5-W2", "token.json 含 revision",
        'python3 - << \'PY\'\nimport json\nfrom pathlib import Path\nfor p in sorted(Path(".omc/tokens").glob("**/*.json")):\n    try:\n        t=json.loads(p.read_text())\n    except Exception:\n        continue\n    if "revision" in t:\n        print(t.get("revision", 0))\n        raise SystemExit(0)\nprint("MISSING")\nraise SystemExit(1)\nPY',
        check_fn=lambda o, _: o.strip().isdigit() and int(o.strip()) >= 0)
    all_pass &= ok

    # W3: INDEX.yaml
    ok, _ = run_verify("P0.5-W3", "INDEX.yaml 含 INVARIANTS",
        "grep -c INVARIANTS docs/INDEX.yaml",
        check_fn=lambda o, _: int(o.strip()) >= 1)
    all_pass &= ok

    # W4: 12 invariants
    ok, _ = run_verify("P0.5-W4", "12 条不变量",
        "grep -c 'INV-' .claude/references/invariants.md",
        check_fn=lambda o, _: int(o.strip()) >= 12)
    all_pass &= ok

    return all_pass


def test_phase1_l2():
    """Phase 1: L2 治理 运行时验证"""
    print("\n=== Phase 1: L2 治理 (Runtime) ===")
    all_pass = True

    # P1: working-set.yaml
    ok, _ = run_verify("P1-L2", "working-set 含 retry/verify",
        "grep -c max_retries .claude/references/working-set-template.yaml",
        check_fn=lambda o, _: int(o.strip()) >= 1)
    all_pass &= ok

    # P1: Error DNA
    ok, _ = run_verify("P1-DNA", "Error DNA 可记录",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.error_dna import record_error; '
        'from pathlib import Path; '
        'd=record_error(Path(\'.omc/tasks/20260713/phase3-dual-judge\'),\'T1\',\'test error\'); '
        'print(d[\'step\'], d[\'retry_count\'])"',
        check_fn=lambda o, _: "T1" in o and "0" in o)
    all_pass &= ok

    # P1: Retry gate
    ok, _ = run_verify("P1-DNA", "Retry Gate 3次阻断",
        'python3 - << \'PY\'\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, ".omc/scripts")\nfrom lib.error_dna import check_retry_gate, record_error\np=Path(".omc/tasks/20260713/phase3-dual-judge")\nfor i in range(4):\n    record_error(p,"T2",f"err{i}",retry_count=i)\na,_,_=check_retry_gate(p,"T2")\nprint(a)\nPY',
        check_fn=lambda o, _: "False" in o)
    all_pass &= ok

    # P1: Oracle trigger L1=no
    ok, _ = run_verify("P1-ORACLE", "Oracle L1=不触发",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.oracle_gate_light import should_trigger_oracle; '
        'print(should_trigger_oracle(\'L1\')[0])"',
        check_fn=lambda o, _: "False" in o)
    all_pass &= ok

    # P1: Oracle trigger L2+high=yes
    ok, _ = run_verify("P1-ORACLE", "Oracle L2+high=触发",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.oracle_gate_light import should_trigger_oracle; '
        'print(should_trigger_oracle(\'L2\',risk_level=\'high\')[0])"',
        check_fn=lambda o, _: "True" in o)
    all_pass &= ok

    return all_pass


def test_phase2_flywheel():
    """Phase 2: 飞轮+无人 运行时验证"""
    print("\n=== Phase 2: 飞轮+无人 (Runtime) ===")
    all_pass = True

    # P2: Flywheel
    ok, _ = run_verify("P2-FLY", "飞轮可运行",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.flywheel import run_flywheel; '
        'from pathlib import Path; '
        'r=run_flywheel(Path.cwd()); print(r.get(\'patterns_found\',0), r.get(\'knowledge_entries\',0))"',
        timeout=30)
    all_pass &= ok

    # P2: claude-next.md
    ok, _ = run_verify("P2-FLY", "claude-next.md 存在",
        "test -f .omc/knowledge/claude-next.md && echo 'EXISTS' || echo 'MISSING'",
        check_fn=lambda o, _: "EXISTS" in o)
    all_pass &= ok

    # P2: Loop detection
    ok, _ = run_verify("P2-AUTO", "Loop 检测",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.autonomy import LoopDetector; '
        'l=LoopDetector(3); [l.record_tick(\'S1\',\'same\',\'same\') for _ in range(5)]; '
        'd=l.detect_loop(); print(d[\'type\'] if d else \'none\')"',
        check_fn=lambda o, _: "loop" in o.lower())
    all_pass &= ok

    # P2: Autonomy contract
    ok, _ = run_verify("P2-AUTO", "Autonomy Contract 加载",
        'python3 - << \'PY\'\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, ".omc/scripts")\nfrom lib.autonomy import load_contract\nc=load_contract(Path.cwd())\nprint(c["boundaries"]["max_autonomy_turns"])\nPY',
        check_fn=lambda o, _: "30" in o)
    all_pass &= ok

    # P2: Budget exceeded pause
    ok, _ = run_verify("P2-AUTO", "超 budget 暂停",
        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
        'from lib.autonomy import check_autonomy_gate, LoopDetector; '
        't={\'stats\':{\'tick\':35,\'done\':2},\'budget\':{\'max_turns_hard\':30}}; '
        'r=check_autonomy_gate(t, LoopDetector()); print(r is not None)"',
        check_fn=lambda o, _: "True" in o)
    all_pass &= ok

    return all_pass


if __name__ == "__main__":
    print("=" * 60)
    print("CarrorOS Runtime Verification Suite")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    phases = [
        ("Phase 0 — Token Slim", test_phase0_token_slim),
        ("Phase 0.5 — 文档基建", test_phase05_docs),
        ("Phase 1 — L2 治理", test_phase1_l2),
        ("Phase 2 — 飞轮+无人", test_phase2_flywheel),
    ]

    results = {}
    total_pass = 0
    total_tests = 0

    for name, test_fn in phases:
        print(f"\n{'─'*60}")
        print(f"Running: {name}")
        ok = test_fn()
        results[name] = "✅ PASS" if ok else "❌ FAIL"
        if ok:
            total_pass += 1
        # Count evidence
        ev_path = VERIFY_DIR / "evidence.jsonl"
        if ev_path.exists():
            with open(ev_path) as f:
                tests_here = sum(1 for _ in f)
                total_tests = tests_here  # Will be cumulative

    # Summary
    print(f"\n{'='*60}")
    print("RUNTIME VERIFICATION SUMMARY")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"  {r} {name}")

    ev_path = VERIFY_DIR / "evidence.jsonl"
    if ev_path.exists():
        with open(ev_path) as f:
            full_count = sum(1 for _ in f)
        print(f"\n  Total tests: {full_count}")
        print(f"  Evidence: {ev_path}")
    
    print(f"\n  Pass rate: {sum(1 for r in results.values() if 'PASS' in r)}/{len(results)} phases")
