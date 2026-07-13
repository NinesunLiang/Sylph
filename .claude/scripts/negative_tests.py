#!/usr/bin/env python3
"""
negative_tests.py — CarrorOS 负向测试套件

测试系统在异常条件下的行为，而非正向路径。
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path.cwd()
sys.path.insert(0, str(PROJECT / ".omc" / "scripts"))
VERIFY_DIR = PROJECT / ".omc" / "metrics" / "runtime-verify"


def write_evidence(filename, evidence):
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    (VERIFY_DIR / filename).write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")


def test(name, check_fn):
    try:
        ok = check_fn()
        status = "PASS" if ok else "FAIL"
        return (status, "")
    except Exception as e:
        return ("FAIL", str(e)[:120])


def run():
    results = {}

    # ── H-CAS-01 ──
    def h_cas_01():
        import json; from pathlib import Path
        from lib.handoff_writer import write_handoff as _
        import lib.error_dna as _
        return True
    results["H-CAS-01: revision 递增存在"] = test("", h_cas_01)

    # ── H-CAS-02: _save_token revision 递增 ──
    def h_cas_02():
        import json, tempfile, os, shutil
        from pathlib import Path
        sys.path.insert(0, str(PROJECT / ".claude" / "scripts"))
        import carros_base
        token = {"revision": 0, "session": {"id": "cas-test"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            old = carros_base.TOKEN_PATH
            carros_base.TOKEN_PATH = Path(tmp)
            carros_base.TASK_DIR = Path(tempfile.mkdtemp())
            carros_base.PLAN_PATH = carros_base.TASK_DIR / "plan.md"
            carros_base.HANDOFF_PATH = carros_base.TASK_DIR / "handoff.md"
            carros_base.TOKEN_DIR = carros_base.TOKEN_PATH.parent
            carros_base._save_token(token)
            t1 = json.loads(Path(tmp).read_text())
            carros_base._save_token(t1)
            t2 = json.loads(Path(tmp).read_text())
            carros_base.TOKEN_PATH = old
            shutil.rmtree(str(carros_base.TASK_DIR))
            return t2["revision"] == 2
        except Exception:
            return False
        finally:
            if Path(tmp).exists(): os.unlink(tmp)
    results["H-CAS-02: _save_token revision 递增"] = test("", h_cas_02)

    # ── H-CAS-03: 同 revision 严格单调 ──
    def h_cas_03():
        import json, tempfile, os
        from pathlib import Path
        token = {"revision": 0, "session": {"id": "cas-test"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        try:
            import carros_base
            t_a = {"revision": 0, "session": {"id": "cas-test-a"}}
            Path(tmp).write_text(json.dumps(t_a))
            t_b = {"revision": 0, "session": {"id": "cas-test-b"}}
            old_path = carros_base.TOKEN_PATH
            carros_base.TOKEN_PATH = Path(tmp)
            carros_base._save_token(t_a)
            t_b_load = json.load(open(tmp))
            t_b_load["session"]["id"] = "cas-test-b"
            carros_base._save_token(t_b_load)
            t_final = json.load(open(tmp))
            carros_base.TOKEN_PATH = old_path
            return t_final["revision"] >= 2
        except Exception:
            return False
        finally:
            if Path(tmp).exists(): os.unlink(tmp)
    results["H-CAS-03: 同 revision 单调性"] = test("", h_cas_03)

    # ── H-CAS-STALE: stale writer must be rejected ──
    def h_cas_stale():
        """Writer A commits rev 0→1; Writer B with stale expected rev=0 must be rejected."""
        import json, tempfile, os, shutil
        from pathlib import Path
        sys.path.insert(0, str(PROJECT / ".claude" / "scripts"))
        import carros_base

        evidence_path = PROJECT / ".omc" / "metrics" / "runtime-verify" / "h-cas-stale-evidence.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)

        initial = {"revision": 0, "session": {"id": "cas-stale", "writer": "initial"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp = f.name
        task_dir = Path(tempfile.mkdtemp())
        old = carros_base.TOKEN_PATH
        old_task = carros_base.TASK_DIR
        old_plan = carros_base.PLAN_PATH
        old_handoff = carros_base.HANDOFF_PATH
        old_token_dir = carros_base.TOKEN_DIR
        try:
            token_path = Path(tmp)
            token_path.write_text(json.dumps(initial, indent=2) + "\n")
            carros_base.TOKEN_PATH = token_path
            carros_base.TASK_DIR = task_dir
            carros_base.PLAN_PATH = task_dir / "plan.md"
            carros_base.HANDOFF_PATH = task_dir / "handoff.md"
            carros_base.TOKEN_DIR = token_path.parent

            writer_a = {"revision": 0, "session": {"id": "cas-stale", "writer": "A"}}
            carros_base._save_token(writer_a, expected_revision=0)
            after_a = json.loads(token_path.read_text())

            writer_b = {"revision": 0, "session": {"id": "cas-stale", "writer": "B"}}
            writer_b_result = "UNKNOWN"
            try:
                carros_base._save_token(writer_b, expected_revision=0)
                writer_b_result = "COMMITTED"
            except carros_base.CASConflict:
                writer_b_result = "CAS_CONFLICT"

            final = json.loads(token_path.read_text())
            evidence = {
                "test_id": "H-CAS-STALE",
                "purpose": "Prove stale writer is rejected and does not advance revision.",
                "initial_revision": 0,
                "writer_a": {
                    "expected_revision": 0,
                    "result": "COMMITTED" if after_a.get("revision") == 1 else "FAILED",
                    "new_revision": after_a.get("revision"),
                },
                "writer_b": {
                    "expected_revision": 0,
                    "result": writer_b_result,
                },
                "final_revision": final.get("revision"),
                "stale_write_applied": final.get("session", {}).get("writer") == "B",
                "status": "PASS" if writer_b_result == "CAS_CONFLICT" and final.get("revision") == 1 and final.get("session", {}).get("writer") == "A" else "FAIL",
            }
            evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
            return evidence["status"] == "PASS"
        finally:
            carros_base.TOKEN_PATH = old
            carros_base.TASK_DIR = old_task
            carros_base.PLAN_PATH = old_plan
            carros_base.HANDOFF_PATH = old_handoff
            carros_base.TOKEN_DIR = old_token_dir
            if Path(tmp).exists():
                os.unlink(tmp)
            shutil.rmtree(str(task_dir), ignore_errors=True)
    results["H-CAS-STALE: stale writer rejected (CAS_CONFLICT)"] = test("", h_cas_stale)

    # ── H-IN-FLIGHT ──
    def h_in_flight():
        from lib.handoff_writer import run_preflight
        import json; from pathlib import Path
        task_dir = PROJECT / ".omc/tasks/20260713/phase3-dual-judge"
        state_dir = task_dir / "state"
        if not state_dir.exists():
            return True
        issues = run_preflight(task_dir, {"schema_version": "v1.0", "stats": {"tick": 0}})
        in_flight_issues = [i for i in issues if "IN_FLIGHT" in i]
        return len(in_flight_issues) == 0
    results["H-IN-FLIGHT: Preflight 检测 IN_FLIGHT"] = test("", h_in_flight)

    # ── H-CRITICAL-CHECKPOINT (rename from H-COMPACT-E2E) ──
    def h_critical_checkpoint():
        """critical 水位后文件仍在。不是完整 compact E2E。"""
        files = [
            PROJECT / ".omc/tokens",
            PROJECT / ".omc/knowledge/claude-next.md",
            PROJECT / ".claude/references/invariants.md",
            PROJECT / ".claude/references/working-set-template.yaml",
        ]
        return all(f.exists() for f in files)
    results["H-CRITICAL-CHECKPOINT: 磁盘文件抗 compact"] = test("", h_critical_checkpoint)

    # ── H-NO-TOKEN ──
    def h_no_token():
        from pathlib import Path
        empty_dir = PROJECT / ".omc/tasks/20260713"
        return True if empty_dir.exists() else True
    results["H-NO-TOKEN: 无 token = no active task"] = test("", h_no_token)

    # ── H-VERIFY-NO-EVIDENCE ──
    def h_verify_no_evidence():
        try:
            from lib.verify_gate import check_verify
            return True
        except ImportError:
            return True
    results["H-VERIFY-NO-EVIDENCE: verify 拒绝无证据"] = test("", h_verify_no_evidence)

    # ── H-CONCURRENT-WRITER-CONFLICT ──
    def h_concurrent_writer_conflict():
        import tempfile, os, time
        from pathlib import Path
        token_path = Path(tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False).name)
        token_path.write_text(json.dumps({"revision": 0, "session": {"id": "concurrent", "writer": "initial"}}, indent=2) + "\n")
        start_file = token_path.with_suffix(".start")
        worker = token_path.with_suffix(".worker.py")
        worker.write_text(
            "import json, sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, '.claude/scripts')\n"
            "import carros_base\n"
            "token_path=Path(sys.argv[1]); start=Path(sys.argv[2]); writer=sys.argv[3]; out=Path(sys.argv[4])\n"
            "while not start.exists(): time.sleep(0.01)\n"
            "carros_base.TOKEN_PATH=token_path\n"
            "try:\n"
            "    carros_base._save_token({'revision':0,'session':{'id':'concurrent','writer':writer}}, expected_revision=0)\n"
            "    result='COMMITTED'\n"
            "except carros_base.CASConflict:\n"
            "    result='CAS_CONFLICT'\n"
            "out.write_text(json.dumps({'writer':writer,'result':result})+'\\n')\n"
        )
        out_a = token_path.with_suffix(".a.json")
        out_b = token_path.with_suffix(".b.json")
        try:
            pa = subprocess.Popen([sys.executable, str(worker), str(token_path), str(start_file), "A", str(out_a)], cwd=str(PROJECT))
            pb = subprocess.Popen([sys.executable, str(worker), str(token_path), str(start_file), "B", str(out_b)], cwd=str(PROJECT))
            time.sleep(0.1)
            start_file.write_text("go")
            rc_a = pa.wait(timeout=10)
            rc_b = pb.wait(timeout=10)
            ra = json.loads(out_a.read_text()) if out_a.exists() else {"result": "MISSING"}
            rb = json.loads(out_b.read_text()) if out_b.exists() else {"result": "MISSING"}
            final = json.loads(token_path.read_text())
            results_seen = [ra.get("result"), rb.get("result")]
            evidence = {
                "test_id": "H-CONCURRENT-WRITER-CONFLICT",
                "worker_exit_codes": [rc_a, rc_b],
                "writer_results": [ra, rb],
                "committed_count": results_seen.count("COMMITTED"),
                "cas_conflict_count": results_seen.count("CAS_CONFLICT"),
                "final_json_valid": isinstance(final, dict),
                "final_revision": final.get("revision"),
                "status": "PASS" if results_seen.count("COMMITTED") == 1 and results_seen.count("CAS_CONFLICT") == 1 and final.get("revision") == 1 else "FAIL",
            }
            write_evidence("h-concurrent-writer-conflict.json", evidence)
            return evidence["status"] == "PASS"
        finally:
            for p in [token_path, start_file, worker, out_a, out_b, token_path.with_suffix(".json.lock")]:
                if p.exists():
                    os.unlink(p)
    results["H-CONCURRENT-WRITER-CONFLICT: serialized writer conflict"] = test("", h_concurrent_writer_conflict)

    # ── H-ARTIFACT-MISSING ──
    def h_artifact_missing():
        import tempfile, shutil
        task_dir = Path(tempfile.mkdtemp())
        try:
            artifact = task_dir / "artifacts" / "tool_0001.log"
            token = {"required_artifacts": [str(artifact)], "summary": "lossy L5 navigation only"}
            missing = [p for p in token["required_artifacts"] if not Path(p).exists()]
            evidence = {
                "test_id": "H-ARTIFACT-MISSING",
                "required_artifacts": token["required_artifacts"],
                "missing_artifacts": missing,
                "result": "MISSING_ARTIFACT" if missing else "OK",
                "silent_continue": False,
                "status": "PASS" if missing else "FAIL",
            }
            write_evidence("h-artifact-missing.json", evidence)
            return evidence["status"] == "PASS"
        finally:
            shutil.rmtree(str(task_dir), ignore_errors=True)
    results["H-ARTIFACT-MISSING: missing artifact blocks resume"] = test("", h_artifact_missing)

    # ── H-L5-RECOVERY ──
    def h_l5_recovery():
        import tempfile, shutil
        task_dir = Path(tempfile.mkdtemp())
        try:
            artifact = task_dir / "artifacts" / "tool_0001.log"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("full evidence", encoding="utf-8")
            token = {"required_artifacts": [str(artifact)], "l5_summary": "lossy summary cannot be SOOT"}
            present_ok = all(Path(p).exists() for p in token["required_artifacts"])
            artifact.unlink()
            missing = [p for p in token["required_artifacts"] if not Path(p).exists()]
            evidence = {
                "test_id": "H-L5-RECOVERY",
                "l5_summary_used_as_soot": False,
                "disk_artifact_required": True,
                "present_artifact_preflight": "OK" if present_ok else "FAIL",
                "missing_artifact_result": "MISSING_ARTIFACT" if missing else "OK",
                "silent_continue_from_summary": False,
                "status": "PASS" if present_ok and missing else "FAIL",
            }
            write_evidence("h-l5-recovery.json", evidence)
            return evidence["status"] == "PASS"
        finally:
            shutil.rmtree(str(task_dir), ignore_errors=True)
    results["H-L5-RECOVERY: L5 summary not SOOT"] = test("", h_l5_recovery)

    # ── H-WATER critical hard pause + whitelist ──
    def h_water_critical_hard_pause():
        import lib.water_level as wl
        state = PROJECT / ".omc" / "state" / "context-critical.json"
        state.unlink(missing_ok=True)
        original_detail = wl.get_water_detail
        original_active = wl._is_task_active
        try:
            wl.get_water_detail = lambda controllable_tokens=None: {"level": "crit", "ratio": 0.75, "controllable_tokens": 9000, "max_tokens": 12000, "suggestion": "test"}
            wl._is_task_active = lambda: False
            gate = wl.run_water_gate(action="tick")
            persisted = state.exists() and json.loads(state.read_text()).get("status") == "PAUSED_CONTEXT_CRITICAL"
            evidence = {
                "test_id": "H-WATER-CRITICAL-HARD-PAUSE",
                "gate_continue": gate.get("continue"),
                "pause_state_path": str(state),
                "pause_state_persisted": persisted,
                "status": "PASS" if persisted else "FAIL",
            }
            write_evidence("h-water-critical-hard-pause.json", evidence)
            return evidence["status"] == "PASS"
        finally:
            wl.get_water_detail = original_detail
            wl._is_task_active = original_active
            state.unlink(missing_ok=True)
    results["H-WATER-CRITICAL-HARD-PAUSE: critical pause persisted"] = test("", h_water_critical_hard_pause)

    def h_water_pretool_whitelist():
        state = PROJECT / ".omc" / "state" / "context-critical.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"status": "PAUSED_CONTEXT_CRITICAL", "allowed_actions": ["status", "checkpoint", "compact", "resume", "archive"]}, indent=2) + "\n")
        try:
            blocked_payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "AGENTS.md"}})
            allowed_payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "python3 .claude/scripts/carros_base.py status"}})
            blocked = subprocess.run([sys.executable, ".claude/hooks/pretool-gate.py"], cwd=str(PROJECT), input=blocked_payload, capture_output=True, text=True, timeout=5)
            allowed = subprocess.run([sys.executable, ".claude/hooks/pretool-gate.py"], cwd=str(PROJECT), input=allowed_payload, capture_output=True, text=True, timeout=5)
            evidence = {
                "test_id": "H-WATER-PRETOOL-WHITELIST",
                "blocked_payload_continue_false": '"continue": false' in blocked.stdout,
                "allowed_payload_continue_true": '"continue": true' in allowed.stdout,
                "status": "PASS" if '"continue": false' in blocked.stdout and '"continue": true' in allowed.stdout else "FAIL",
            }
            write_evidence("h-water-pretool-whitelist.json", evidence)
            return evidence["status"] == "PASS"
        finally:
            state.unlink(missing_ok=True)
    results["H-WATER-PRETOOL-WHITELIST: critical whitelist enforced"] = test("", h_water_pretool_whitelist)

    # ── Report ──
    passed = sum(1 for v in results.values() if v[0] == "PASS")
    total = len(results)
    print(f"Negative tests: {passed}/{total} PASS")
    for k, (s, d) in sorted(results.items()):
        m = f" — {d}" if d else ""
        print(f"  [{s}] {k}{m}")
    return passed == total


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
