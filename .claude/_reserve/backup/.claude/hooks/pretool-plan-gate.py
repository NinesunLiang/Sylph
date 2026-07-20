#!/usr/bin/env python3
# pretool-plan-gate.py — PreToolUse:Edit|Write|Bash — Plan-before-Execute 门禁
# 哲学 #3(先守护): 方案未审批→阻断执行
# 哲学 #6(0信任): 不信任 state.json (AI可写) → 从 lx-goal.json 验证 phase0_passed_at
# 触发: 跨3+文件或20+行变更时检查

import json
import os
import re
import sys
from pathlib import Path

# ─── Path resolution ───
HOOKS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"

sys.path.insert(0, str(HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, hc_get, flywheel_event, hc_emit_hook_json


def main():
    # hc_enabled gate
    if not hc_enabled("pretool_plan_gate"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Read stdin
    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    # Parse tool name
    tool_name = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            tool_name = parsed.get("tool_name", "") or ""
        except (json.JSONDecodeError, Exception):
            tool_name = ""

    if not tool_name:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Only intercept Edit/Write/Bash (tools that produce code changes)
    if tool_name not in ("Edit", "Write", "Bash"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── Quick estimate of change size ───
    estimated_files = 0
    estimated_lines = 0
    file_path = ""

    if tool_name in ("Edit", "Write"):
        try:
            parsed = json.loads(input_data)
            tool_input = parsed.get("tool_input", {})
            file_path = tool_input.get("file_path", "") or tool_input.get("args", {}).get("filePath", "") or ""
            if file_path:
                new_content = tool_input.get("new_string", "") or tool_input.get("content", "") or ""
                if new_content:
                    estimated_lines = len(new_content.splitlines())
                estimated_files = 1
        except Exception:
            pass

    elif tool_name == "Bash":
        try:
            parsed = json.loads(input_data)
            tool_input = parsed.get("tool_input", {})
            cmd = tool_input.get("command", "") or tool_input.get("args", {}).get("command", "") or ""
            # Count file extensions in the command
            file_count = len(re.findall(r'\S+\.(?:go|py|ts|js|sh|yaml|yml|json|md|toml|rs|rb|java|css|html)', cmd))
            estimated_files = file_count
        except Exception:
            pass

    # ─── RPE plan directory pass: allow writing prd.md/progress.md/checklist.md ───
    # Only allow these three file types; state.json is NOT whitelisted
    if file_path and re.search(r'\.omc/plans/.*/(?:prd|progress|checklist)\.md$', file_path):
        print(json.dumps({"continue": True}))
        sys.exit(0)
    # Ghost RPE directory also pass
    if file_path and re.search(r'\.omc/chats/.*/progress\.md$', file_path):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── Non-substantive Bash operations pass: pure rename/directory creation/info queries ───
    if tool_name == "Bash":
        cmd = ""
        try:
            parsed = json.loads(input_data)
            tool_input = parsed.get("tool_input", {})
            cmd = tool_input.get("command", "") or tool_input.get("args", {}).get("command", "") or ""
        except Exception:
            cmd = ""

        # git mv / mv (without inline edit patterns)
        if re.search(r'^\s*(git\s+mv|mv\s+)\s', cmd) and \
           not re.search(r'\bsed\s+-i\b|\bawk\s+.*-i\b|\btee\b|[^>]>>?\s*\S|cat\s+>', cmd):
            print(json.dumps({"continue": True}))
            flywheel_event("pretool_plan_gate", "non_substantive_bypass", "P2", json.dumps({"cmd": "git_mv"}))
            sys.exit(0)

        # mkdir / ls / find / cp / rmdir
        if re.search(r'^\s*(?:mkdir|ls|find|cp|rmdir)\s', cmd):
            print(json.dumps({"continue": True}))
            flywheel_event("pretool_plan_gate", "non_substantive_bypass", "P2", json.dumps({"cmd": "filesystem_ops"}))
            sys.exit(0)

    # ─── Gate judgment ───
    # DG-114: Session-level cumulative edit detection, prevent stepwise bypass
    cumulative_files = 0
    churn_log = STATE_DIR / "edit-churn-log.jsonl"
    session_start_file = STATE_DIR / "session-start.txt"

    if churn_log.exists():
        session_start = 0
        if session_start_file.exists():
            try:
                session_start = int(session_start_file.read_text(encoding="utf-8", errors="replace").strip())
            except (ValueError, Exception):
                session_start = 0

        if session_start > 0:
            count_paths = set()
            try:
                with open(str(churn_log), "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            if record.get("ts", 0) >= session_start:
                                count_paths.add(record.get("file", ""))
                        except (json.JSONDecodeError, Exception):
                            pass
                cumulative_files = len(count_paths)
            except (OSError, Exception):
                cumulative_files = 0

    total_files = estimated_files + cumulative_files

    # Bash: can't estimate lines → only check file count. Edit/Write: check file count or lines
    if tool_name == "Bash":
        if estimated_files < 2 and total_files < 3:
            print(json.dumps({"continue": True}))
            sys.exit(0)
    else:
        # Edit/Write: can estimate lines → block if any of single file / cumulative files / lines exceeds threshold
        if estimated_files < 2 and total_files < 3 and estimated_lines < 15:
            print(json.dumps({"continue": True}))
            sys.exit(0)

    # ─── Autonomous mode awareness ──────────────────────────────────────────
    mode = is_mode_active(str(STATE_DIR))

    # Ghost mode: exploration-driven, allow code changes
    if mode == "ghost":
        print(json.dumps({"continue": True}))
        flywheel_event("pretool_plan_gate", "ghost_mode_allow", "P2",
                       json.dumps({"files": estimated_files, "lines": estimated_lines}))
        sys.exit(0)

    # Goal mode: must pass phase0-done verification (check lx-goal.json, not state.json)
    # Philosophy #6 (0-trust): state.json is AI-writable, untrusted.
    # lx-goal.json's phase0_passed_at is only written by phase0-done
    if mode == "goal":
        goal_file = STATE_DIR / "tokens" / "lx-goal.json"
        if goal_file.exists():
            try:
                goal_data = json.loads(goal_file.read_text(encoding="utf-8", errors="replace"))
                phase0_passed = goal_data.get("phase0_passed_at", "") or ""
                if phase0_passed:
                    print(json.dumps({"continue": True}))
                    flywheel_event("pretool_plan_gate", "goal_phase0_verified", "P2",
                                   json.dumps({"passed_at": phase0_passed}))
                    sys.exit(0)
            except (json.JSONDecodeError, Exception):
                pass

        # Phase 0 not complete → block
        block_msg = """⛔ [Plan Gate] 目标模式活跃，但 Phase 0 未完成 (phase0_passed_at 缺失)。

    AI 必须先调用 phase0-done 完成计划阶段:
      lx-goal phase0-done

    这会验证 prd.md 已写入子任务/验收标准/风险点，
    然后将 phase0_passed_at 写入 lx-goal.json，解锁代码变更。
    注意: 直接写 state.json 无效 — plan gate 只信任 lx-goal.json。
    """
        print(block_msg, file=sys.stderr, flush=True)
        flywheel_event("pretool_plan_gate", "blocked_phase0_incomplete", "P1", json.dumps({"mode": "goal"}))
        sys.exit(2)

    # ─── Normal mode: traditional Plan-before-Execute check ──────────
    plans_dir = PROJECT_ROOT / ".omc" / "plans"
    has_approved = False
    plan_path = ""

    if plans_dir.is_dir():
        for state_file in sorted(plans_dir.rglob("state.json")):
            if not state_file.is_file():
                continue
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8", errors="replace"))
                phase = state_data.get("phase", "") or ""
                if phase in ("approved", "executing"):
                    has_approved = True
                    plan_path = str(state_file.parent)
                    break
            except (json.JSONDecodeError, Exception):
                continue

    if has_approved:
        print(json.dumps({"continue": True}))
        flywheel_event("pretool_plan_gate", "approved_plan_active", "P2",
                       json.dumps({"plan": plan_path}))
        sys.exit(0)

    # ─── Concept review gate: Oracle/Meta-Oracle recently APPROVED → must have implementation plan ───
    # Prevent "concept APPROVED → skip implementation plan review → directly change code" (DG-114)
    oracle_verdict = STATE_DIR / "oracle-verdicts.md"
    meta_verdict = STATE_DIR / "meta-oracle-verdicts.md"
    concept_recent = False
    import time

    for verdict_file in (oracle_verdict, meta_verdict):
        if verdict_file.exists():
            try:
                file_age = int(time.time() - verdict_file.stat().st_mtime)
            except Exception:
                file_age = 999
            if file_age < 600:
                try:
                    lines = verdict_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    # Check only latest entry (last non-empty line)
                    last_line = ""
                    for ln in reversed(lines):
                        if ln.strip():
                            last_line = ln.strip()
                            break
                    if last_line and re.search(r'approved|accept', last_line, re.IGNORECASE):
                        concept_recent = True
                        break
                except Exception:
                    continue

    if concept_recent:
        block_msg = """⛔ [Plan Gate] 检测到近期概念审查已通过 (Oracle/Meta-Oracle APPROVED)，但缺少实现方案。

    AI 必须先:
    1. 输出具体的实现方案 (改动文件/行数/逻辑)
    2. 等用户审批后才能执行代码变更

    概念审查通过 ≠ 可以直接改代码。方案→双审→执行，不可跳过。
    """
        print(block_msg, file=sys.stderr, flush=True)
        flywheel_event("pretool_plan_gate", "blocked_concept_without_impl_plan", "P1",
                       json.dumps({"tool": tool_name}))
        sys.exit(2)

    # ─── Block: no approved plan ───
    # List existing plan state files
    plan_list = []
    if plans_dir.is_dir():
        for sf in sorted(plans_dir.rglob("state.json")):
            if sf.is_file():
                plan_list.append(str(sf))
                if len(plan_list) >= 5:
                    break
    plan_display = "\n".join(plan_list) if plan_list else "  (无)"

    block_msg = f"""⛔ [Plan Gate] 检测到中等以上变更 (本次{estimated_files}文件/{estimated_lines}行, 本会话累计{cumulative_files}文件)，但无已审批方案。

AI 必须:
1. 先写 PRD 到 .omc/plans/{{date}}/{{feature_slug}}/prd.md
2. 输出方案摘要给用户
3. 等用户说 '同意'/'do' 后更新 state.json phase=approved
4. 才能执行代码变更

当前已有方案目录:
{plan_display}
"""
    print(block_msg, file=sys.stderr, flush=True)
    flywheel_event("pretool_plan_gate", "blocked_no_plan", "P1",
                   json.dumps({"tool": tool_name, "files": estimated_files, "lines": estimated_lines}))
    sys.exit(2)


if __name__ == "__main__":
    main()
