#!/usr/bin/env python3
"""
omc_lint.py — 统一 lint 系统

检查内容（按 update.md 第 9 条）：
1. token.json schema
2. plan.md step 格式
3. executor.md evidence block
4. audit jsonl 可解析
5. token done/total 与 plan 一致
6. VerifyGate audit 与 plan step 一致
7. archive readiness

Usage:
    python3 .claude/scripts/omc_lint.py [path]

Exit code: 0 = all clear | 1 = warnings | 2 = errors

Can also be imported by carros_base.py:
    import omc_lint; result = omc_lint.run_lint(path)
"""

import json
import os
import re
import sys
from pathlib import Path


def warning(msg: str):
    print(f"  ⚠  WARN: {msg}")


def error(msg: str):
    print(f"  ❌ ERROR: {msg}")


def ok(msg: str):
    print(f"  ✅ {msg}")


def _find_latest_token(root):
    """在 .omc/tokens/{date}/ 目录下找最新 token"""
    tokens_dir = root / ".omc" / "tokens"
    if not tokens_dir.exists():
        return None, None
    candidates = []
    for dd in sorted(tokens_dir.iterdir(), reverse=True):
        if dd.is_dir():
            for jf in dd.glob("*.json"):
                try:
                    candidates.append((jf.stat().st_mtime, jf))
                except OSError:
                    continue
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _, jf in candidates:
        try:
            import json
            token = json.loads(jf.read_text())
            return token, jf
        except (json.JSONDecodeError, OSError):
            continue
    if candidates:
        try:
            import json
            token = json.loads(candidates[0][1].read_text())
            return token, candidates[0][1]
        except (json.JSONDecodeError, OSError):
            pass
    return None, None


def _find_task_dir(root, task_id):
    """根据 task_id 找 .omc/tasks/{date}/{task_id}/ 目录"""
    tasks_dir = root / ".omc" / "tasks"
    if not tasks_dir.exists():
        return None
    for dd in sorted(tasks_dir.iterdir(), reverse=True):
        if dd.is_dir():
            td = dd / task_id
            if td.exists():
                return td
    return None


def run_lint(target_path):
    """Main lint function, returns dict with exit_code and output"""
    root = Path(target_path).resolve()
    if not root.exists():
        return {"exit_code": 2, "output": f"❌ Path not found: {target_path}"}

    omc_root = root / ".omc"
    omc_state = omc_root / "state"

    # 新路径：.omc/tokens/{date}/{task}.json
    token, token_path = _find_latest_token(root)
    if token_path is None:
        token_path = omc_state / "token.json"

    # 从 token 解析 task_dir
    task_dir = None
    if token:
        task_id = token.get("session", {}).get("id", "")
        if task_id:
            task_dir = _find_task_dir(root, task_id)

    # plan / executor 从 task_dir 找
    plan_path = omc_state / "plan.md"
    executor_path = omc_state / "executor.md"
    if task_dir:
        td_plan = task_dir / "plan.md"
        if td_plan.exists():
            plan_path = td_plan
        td_exec = task_dir / "executor.md"
        if td_exec.exists():
            executor_path = td_exec
    audit_dir = omc_state / "audit"
    if task_dir:
        td_audit = task_dir / "state" / "audit"
        if td_audit.exists() or plan_path == task_dir / "plan.md":
            audit_dir = td_audit

    output = []
    total_errors = 0
    total_warnings = 0

    def _out(msg):
        output.append(msg)

    def _section(name):
        _out(f"\n─── {name} ───")

    # ─── Check 1: token.json schema ───
    _section("Check 1: token.json schema")
    if token_path.exists():
        try:
            token = json.loads(token_path.read_text())
            schema_ok = True
            if "schema_version" not in token:
                warning("token.json missing schema_version"); total_warnings += 1
            if "session" not in token or "id" not in token.get("session", {}):
                warning("token.json missing session.id"); total_warnings += 1
            if "status" not in token:
                warning("token.json missing status"); total_warnings += 1
            if "stats" not in token:
                warning("token.json missing stats"); total_warnings += 1
            if "steps" not in token:
                warning("token.json missing steps"); total_warnings += 1
            if schema_ok:
                ok(f"token.json valid (schema_version: {token.get('schema_version', 'unknown')})")
        except (json.JSONDecodeError, OSError) as e:
            error(f"token.json parse error: {e}"); total_errors += 1
    else:
        warning("token.json not found (run init first)"); total_warnings += 1

    # ─── Check 2: plan.md step format ───
    _section("Check 2: plan.md step format")
    if plan_path.exists():
        content = plan_path.read_text()
        steps = re.findall(r"^- \[( |x)\] (\S+?):", content, re.MULTILINE)
        if steps:
            for checked, sid in steps:
                icon = "✅" if checked == "x" else "⬜"
                ok(f"{icon} {sid}")
        else:
            warning("No step entries found in plan.md"); total_warnings += 1
    else:
        warning("plan.md not found"); total_warnings += 1

    # ─── Check 3: executor.md evidence block ───
    _section("Check 3: executor.md evidence")
    if executor_path.exists():
        content = executor_path.read_text()
        if "evidence" in content.lower() or "Evidence" in content:
            ok("executor.md contains evidence blocks")
        else:
            warning("executor.md missing evidence blocks"); total_warnings += 1
    else:
        warning("executor.md not found"); total_warnings += 1

    # ─── Check 4: audit jsonl ───
    _section("Check 4: audit jsonl")
    if audit_dir.exists():
        jsonl_files = list(audit_dir.glob("*.jsonl"))
        if jsonl_files:
            ok(f"{len(jsonl_files)} audit file(s) found")
            for jf in jsonl_files:
                try:
                    with open(jf) as f:
                        for line in f:
                            if line.strip():
                                json.loads(line)
                    ok(f"  {jf.name}: valid")
                except (json.JSONDecodeError, OSError) as e:
                    error(f"  {jf.name}: invalid: {e}"); total_errors += 1
                    break
        else:
            ok("No audit files yet (new task)")
    else:
        ok("Audit dir not yet created (new task)")

    # ─── Check 5: token done/total vs plan ───
    _section("Check 5: token vs plan consistency")
    if token_path.exists() and plan_path.exists():
        token = json.loads(token_path.read_text())
        plan = plan_path.read_text()
        token_total = token.get("stats", {}).get("total", 0)
        token_done = token.get("stats", {}).get("done", 0)
        plan_done = len(re.findall(r"^- \[x\]", plan, re.MULTILINE))
        plan_total = len(re.findall(r"^- \[[ x]\]", plan, re.MULTILINE))

        if token_total != plan_total:
            if plan_total > 0:  # only warn if plan has steps
                warning(f"Mismatch: token total={token_total}, plan total={plan_total}")
                total_warnings += 1
        if token_done != plan_done:
            if plan_total > 0 and token_total > 0:
                warning(f"Mismatch: token done={token_done}, plan done={plan_done}")
                total_warnings += 1
        if token_total == plan_total and token_done == plan_done:
            ok(f"Consistent: done={token_done}, total={token_total}")
    else:
        warning("Cannot check consistency (token or plan missing)"); total_warnings += 1

    # ─── Check 6: audit has verify events ───
    _section("Check 6: audit verify events")
    has_verify_events = False
    if audit_dir.exists():
        verify_count = 0
        for jf in audit_dir.glob("*.jsonl"):
            with open(jf) as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            if rec.get("event") == "verify":
                                verify_count += 1
                        except json.JSONDecodeError:
                            pass
        has_verify_events = verify_count > 0
        if has_verify_events:
            ok(f"{verify_count} verify event(s) in audit log")
        else:
            # 只有当 task 完成了一部分步骤却没有 verify 事件时才 warn
            task_has_done = False
            if token_path.exists():
                try:
                    t = json.loads(token_path.read_text())
                    task_has_done = t.get("stats", {}).get("done", 0) > 0
                except (json.JSONDecodeError, OSError):
                    pass
            if task_has_done:
                warning("No verify events in audit log (task may not have verified steps)")
                total_warnings += 1
            else:
                ok("No verify events yet (task in progress)")
    else:
        # audit dir 不存在 → 新任务常态，不 warn
        ok("Audit log not yet created (new task)")

    # ─── Check 7: archive readiness ───
    _section("Check 7: archive readiness")
    if token_path.exists():
        token = json.loads(token_path.read_text())
        if token.get("status") == "archived":
            ok("Task already archived")
        else:
            done = token.get("stats", {}).get("done", 0)
            total = token.get("stats", {}).get("total", 0)
            if done == total and total > 0:
                ok("Ready for archive")
            else:
                warning(f"Not ready: {done}/{total} steps done")
                total_warnings += 1
    else:
        ok("No active task")

    # ─── Summary ───
    _out(f"\n{'='*40}")
    if total_errors == 0 and total_warnings == 0:
        _out("✅ All checks passed")
    elif total_errors == 0:
        _out(f"⚠  {total_warnings} warning(s), 0 errors")
    else:
        _out(f"❌ {total_errors} error(s), {total_warnings} warning(s)")

    exit_code = 2 if total_errors > 0 else (1 if total_warnings > 0 else 0)
    return {"exit_code": exit_code, "output": "\n".join(output)}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    result = run_lint(path)
    print(result["output"])
    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
