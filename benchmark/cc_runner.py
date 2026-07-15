#!/usr/bin/env python3
"""CarrorOS Benchmark — 简化 CC 自动化执行器

把 benchmark 任务分解成多个小 CC -p 调用（每个步骤一次），避免超时。
用法: python3 benchmark/cc_runner.py [task_id] [--all]
"""

import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BENCHMARK_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BENCHMARK_DIR / "reports"
RUNS_DIR = BENCHMARK_DIR / "runs"
VERIFY_DIR = BENCHMARK_DIR / "verify"

CC_TIMEOUT = 120  # per CC call
MAX_RETRIES = 2

# ── Task selection ──

DEMO_TASKS = [
    "01_repo_locate_001",  # divide_by_zero fix
    "01_repo_locate_002",  # factorial negative
    "01_repo_locate_007",  # api error leak
    "06_test_fix_001",     # fix wrong assertion
    "10_adversarial_001",  # exact rename
]


def load_task_info(task_id: str) -> Optional[dict]:
    """Load a task YAML and extract key info."""
    import yaml  # try PyYAML
    for path in sorted((BENCHMARK_DIR / "tasks").glob("**/*.yaml")):
        if task_id in path.name:
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                return data
            except ImportError:
                # No PyYAML, simple parser
                text = path.read_text()
                data = {}
                for line in text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        data[k.strip()] = v.strip().strip('"').strip("'")
                return data
    return None


def run_cc_step(workdir: Path, prompt: str, timeout: int = CC_TIMEOUT) -> dict:
    """Run a single CC -p call and return structured result."""
    start = time.time()
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            cwd=str(workdir),
            capture_output=True, text=True,
            timeout=timeout,
        )
        elapsed = time.time() - start
        cc_output = {}

        if result.returncode == 0 and result.stdout.strip():
            try:
                cc_output = json.loads(result.stdout)
            except json.JSONDecodeError:
                cc_output = {"raw_output": result.stdout[:500]}

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "elapsed_s": round(elapsed, 1),
            "output": cc_output,
            "error": result.stderr[:300] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "elapsed_s": timeout,
            "output": {},
            "error": f"timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -2,
            "elapsed_s": round(time.time() - start, 1),
            "output": {},
            "error": str(e),
        }


def run_single_task(task_id: str, note: str = "") -> dict:
    """Run a single task through CC -p and verify."""
    print(f"\n{'='*60}")
    print(f"🏃 Task: {task_id} {note}")
    print(f"{'='*60}")

    # Look up task info
    info = load_task_info(task_id)
    if not info:
        return {"task_id": task_id, "error": "task not found", "success": False}

    repos_base = BENCHMARK_DIR / "repos" / "bench-test-app"
    if not repos_base.exists():
        return {"task_id": task_id, "error": "repo not found", "success": False}

    # Create temp workspace
    with tempfile.TemporaryDirectory(prefix=f"cc-run-{task_id}-") as tmpdir:
        workspace = Path(tmpdir) / "task"
        shutil.copytree(repos_base, workspace)

        # Step 1: Read files
        print("  📖 Step 1: Read source files...")
        r1 = run_cc_step(workspace, f"read src/calc.py and tests/test_calc.py, list their functions")
        print(f"     {r1['elapsed_s']}s, success={r1['success']}")
        r1_log = r1.get("output", {}).get("result", "")[:200] if isinstance(r1.get("output"), dict) else ""

        # Step 2: Make changes (per task)
        print(f"  ✏️  Step 2: Execute task ({info.get('title', task_id)})...")
        
        # Build task-specific prompt
        if info.get("allowed_files"):
            scope = ", ".join(info["allowed_files"])
        else:
            scope = "src/*.py, tests/*.py"

        prompt = f"""You are working in a Python project. Task: {info.get('title', task_id)}.

{info.get('description', '')}

IMPORTANT RULES:
- Only modify files in: {scope}
- Run 'python3 -m pytest tests/ -x -q' to verify
- Provide the command output as evidence
- If you hit a permission block, print the block message and continue
- DO NOT skip verification"""

        r2 = run_cc_step(workspace, prompt, timeout=CC_TIMEOUT)
        print(f"     {r2['elapsed_s']}s, success={r2['success']}")
        if not r2["success"]:
            print(f"     ⚠  {r2['error']}")

        # Step 3: Run verify script
        print("  ✅ Step 3: Run verification...")
        verify_path = VERIFY_DIR / f"{task_id}.sh"
        if verify_path.exists():
            v_result = subprocess.run(
                ["bash", str(verify_path)],
                cwd=str(workspace),
                capture_output=True, text=True,
                timeout=30,
            )
            verify_pass = v_result.returncode == 0
            print(f"     {'PASS' if verify_pass else 'FAIL'}: {v_result.stdout.strip()[:200]}")
        else:
            print(f"     ⚠  No verify script for {task_id}")
            verify_pass = None

        # Step 4: Try pytest
        print("  🧪 Step 4: Run pytest...")
        p_result = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "-x", "-q"],
            cwd=str(workspace),
            capture_output=True, text=True,
            timeout=30,
        )
        tests_pass = p_result.returncode == 0
        print(f"     {'PASS' if tests_pass else 'FAIL'}: {p_result.stdout.strip()[:200]}")

    # Return result
    result = {
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": verify_pass if verify_pass is not None else tests_pass,
        "verify_pass": verify_pass,
        "tests_pass": tests_pass,
        "read_s": r1["elapsed_s"],
        "execute_s": r2["elapsed_s"],
        "total_s": round(r1["elapsed_s"] + r2["elapsed_s"], 1),
        "execute_success": r2["success"],
        "execute_error": r2["error"],
    }

    # Save run
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = RUNS_DIR / f"{task_id}.json"
    run_path.write_text(json.dumps(result, indent=2))

    return result


def run_demo():
    """Run a small demo with 5 representative tasks."""
    print("🔬 CarrorOS Benchmark — 简化 CC 执行器 (Demo)")
    print(f"   任务数: {len(DEMO_TASKS)}")
    print(f"   每次 CC 超时: {CC_TIMEOUT}s")

    results = []
    for task_id in DEMO_TASKS:
        r = run_single_task(task_id)
        results.append(r)

    # Summary
    print(f"\n{'='*60}")
    print("📊 Demo Summary")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r.get("success"))
    total_time = sum(r.get("total_s", 0) for r in results)
    print(f"   Passed: {passed}/{len(results)}")
    print(f"   Total time: {total_time:.0f}s")
    print(f"   Average: {total_time/len(results):.0f}s per task")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        print(f"   {status} {r['task_id']}: {r.get('total_s',0):.0f}s "
              f"(read={r.get('read_s',0):.0f}s + exec={r.get('execute_s',0):.0f}s)")

    # Save summary
    summary_path = RUNS_DIR / "demo-summary.json"
    summary_path.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks": len(results),
        "passed": passed,
        "total_time_s": total_time,
        "results": results,
    }, indent=2))
    print(f"\n   Summary: {summary_path}")


if __name__ == "__main__":
    if "--all" in sys.argv:
        run_demo()
    elif len(sys.argv) > 1:
        task_id = sys.argv[1]
        run_single_task(task_id, note="(single)")
    else:
        run_demo()
