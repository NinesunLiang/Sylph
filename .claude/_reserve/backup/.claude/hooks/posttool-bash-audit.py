#!/usr/bin/env python3
"""
posttool-bash-audit.py — PostToolUse:Bash / PostToolUseFailure:Bash — Bash 执行后审计权限上下文，只提醒不阻断
Role: Bash 执行后审计权限上下文，只提醒不阻断
对应 posttool-bash-audit.sh 的 Python 移植
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, hc_get, HOME_DIR


def main():
    # hc_enabled check
    if not hc_enabled("posttool_bash_audit"):
        output_continue()
        return

    # Escape detection gate
    ed_val = hc_get("escape_detection", "true")
    if ed_val.rstrip("\\").strip() != "true":
        output_continue()
        return

    raw_input = sys.stdin.read()

    try:
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        data = {}

    # Extract command, exit_code, stderr/stdout
    tool_input = data.get("tool_input", {}) or {}
    tool_response = data.get("tool_response", {}) or {}
    args = data.get("args", {}) or {}

    if isinstance(args, dict) and args.get("command"):
        command = args["command"]
    elif isinstance(tool_input, dict) and tool_input.get("command"):
        command = tool_input["command"]
    else:
        command = ""

    exit_code = ""
    if isinstance(tool_response, dict):
        exit_code = str(tool_response.get("exit_code", ""))

    stderr_or_stdout = ""
    if isinstance(tool_response, dict):
        stderr_or_stdout = tool_response.get("stderr", "") or tool_response.get("stdout", "") or ""
    stderr_or_stdout = stderr_or_stdout[:500]

    # PostToolUseFailure fallback
    event_name = data.get("hook_event_name", "") or ""
    top_error = data.get("error", "") or ""
    if event_name == "PostToolUseFailure":
        if not exit_code:
            exit_code = "1"
        if not stderr_or_stdout:
            stderr_or_stdout = top_error[:500]

    if not command:
        output_continue()
        return

    # Build audit messages
    audit_msg = ""
    if "git commit" in command:
        audit_msg = "Git提交已执行。如未经显式CAPTCHA授权则为门禁绕过事件，请审查。"
    elif "git push" in command:
        audit_msg = "Git推送已执行。如未经显式CAPTCHA授权则为门禁绕过事件，请审查。"
    elif "git reset --hard" in command:
        audit_msg = "⚠️ 硬重置已执行。请确认操作符合用户指令"
    elif re.search(r"\brm\s+-rf\b|rm\s+-r\b", command):
        audit_msg = "⚠️ 递归删除已执行。请确认操作范围正确"
    elif re.search(r"(?:^| )pkill\b|(?:^| )kill\b", command):
        audit_msg = "进程信号已发送。确认目标进程正确"

    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # === Escape Pattern E4: Evidence fabrication detection ===
    ev_dna_jsonl = state_dir / "error-dna.jsonl"
    ev_signals_jsonl = state_dir / "error-signals.jsonl"
    escape_e4_msg = ""

    scan_files = []
    if ev_signals_jsonl.exists():
        scan_files.append(str(ev_signals_jsonl))
        #print(f"[DEBUG] E4: {ev_signals_jsonl} exists", file=sys.stderr)
    if ev_dna_jsonl.exists():
        scan_files.append(str(ev_dna_jsonl))
        #print(f"[DEBUG] E4: {ev_dna_jsonl} exists", file=sys.stderr)

    if scan_files:
        try:
            all_entries = []
            for jsonl_path in scan_files:
                try:
                    with open(jsonl_path, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                rec = json.loads(line.strip())
                                if rec:
                                    all_entries.append(rec)
                            except (json.JSONDecodeError, ValueError):
                                pass
                except OSError:
                    pass

            def _safe_ts(r):
                ts = r.get("ts", r.get("timestamp", 0))
                return ts if isinstance(ts, (int, float)) else 0

            recent = sorted(all_entries, key=_safe_ts, reverse=True)[:20]

            # Detect completion-gate blocks
            gate_blocks = [r for r in recent
                           if r.get("error_type") == "gate_operation"
                           and ("completion" in r.get("message", "").lower()
                                or "evidence" in r.get("message", "").lower())]

            # Detect evidence write in command
            is_evidence_write = bool(re.search(
                r"VERIFIED|completion-evidence|\.completion-evidence|echo.*VERIFIED|echo.*PASS",
                command))

            # Detect build/test commands
            build_cmds = [r for r in recent
                          if r.get("error_type") in ("build", "test")
                          or any(x in r.get("cmd", "") for x in ["go build", "go test", "npm test", "cargo build"])]

            if len(gate_blocks) >= 1 and is_evidence_write and len(build_cmds) == 0:
                escape_e4_msg = (f"[E4] 可能证据编造: completion-gate 最近阻断({len(gate_blocks)}次)，当前命令写入证据文件，"
                                 f"但最近{len(recent)}条记录中无编译/测试命令。\n"
                                 f"  建议: 验证 AI 实际执行了测试，而非仅 echo VERIFIED 伪造完成证据。")
        except Exception:
            pass

    # === Escape Pattern E3: Context evasion via subagent ===
    escape_e3_msg = ""
    e3_file = ""
    if ev_signals_jsonl.exists():
        e3_file = str(ev_signals_jsonl)
    elif ev_dna_jsonl.exists():
        e3_file = str(ev_dna_jsonl)

    if e3_file:
        try:
            recent_entries = []
            with open(e3_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        if rec:
                            recent_entries.append(rec)
                    except (json.JSONDecodeError, ValueError):
                        pass

            recent = recent_entries[-10:]

            ctx_blocks = [r for r in recent
                          if ("context" in r.get("message", "").lower()
                              or "context" in r.get("error_type", "").lower())
                          and ("guard" in r.get("message", "").lower()
                               or "guard" in r.get("cmd", "").lower())]

            is_subagent = bool(re.search(
                r"task.*(create|execute|run|spawn)|subagent|sub_agent|start_agent|delegate",
                command, re.IGNORECASE))

            if len(ctx_blocks) >= 1 and is_subagent:
                escape_e3_msg = (f"[E3] 可能的上下文规避: context-guard 最近阻断({len(ctx_blocks)}次)后立即创建子 agent。\n"
                                 f"  建议: 检查 AI 是否通过子 agent 绕过上下文限制。")
        except Exception:
            pass

    # === C1 反模式检测: 编译错误盲修 ===
    build_fail_file = state_dir / "build-fail-streak.json"
    anti_pattern_msg = ""

    if re.search(r"go build|go test|npm run build|npm test|cargo build", command):
        is_success = (exit_code == "0")
        if not is_success:
            # Record failure
            state_dir.mkdir(parents=True, exist_ok=True)
            streak_data = {"count": 0, "signatures": []}
            if build_fail_file.exists():
                try:
                    with open(str(build_fail_file), "r", encoding="utf-8") as f:
                        streak_data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass

            streak_data["count"] += 1
            sig = stderr_or_stdout[:200].split("\n")[0] if stderr_or_stdout else ""
            if sig and sig not in streak_data["signatures"]:
                streak_data["signatures"].append(sig)

            with open(str(build_fail_file), "w", encoding="utf-8") as f:
                json.dump(streak_data, f)

            streak = streak_data["count"]
            fail_streak_threshold = int(hc_get("posttool_bash_audit.fail_streak_threshold", "3"))
            hard_block_threshold = int(hc_get("posttool_bash_audit.hard_block_threshold", "10"))

            if streak >= fail_streak_threshold:
                distinct = len(streak_data.get("signatures", []))
                if distinct > 1:
                    anti_pattern_msg = (f"[反模式 C1: 编译错误盲修] 连续 {streak} 次构建失败，"
                                        f"且错误签名在变化({distinct}种不同错误)。建议: 停下来做根因分析(5-Why)，"
                                        f"错误可能不在你正在改的地方。")
                else:
                    anti_pattern_msg = (f"[反模式 C1: 编译错误盲修] 连续 {streak} 次构建失败，"
                                        f"错误签名相同。建议: 当前修复方向可能正确但实现有误，仔细检查最近的改动。")

                # E5 Build Fail Gate
                gate_file = state_dir / "build-fail-gate.json"
                gate = {
                    "streak": streak,
                    "threshold": fail_streak_threshold,
                    "last_fail": time.time(),
                    "requires_diagnosis": True
                }
                with open(str(gate_file), "w", encoding="utf-8") as f:
                    json.dump(gate, f, indent=2)

            # E5 Hard Block: excessive consecutive failures → hard exit(2)
            if streak >= hard_block_threshold:
                print(f"[Build Fail Gate] ⛔ 连续 {streak} 次构建失败（硬阻断阈值: {hard_block_threshold}）。"
                      f"禁止继续盲修。请执行根因分析后再试。",
                      file=sys.stderr, flush=True)
                flywheel_event("posttool_bash_audit", "build_fail_hard_block", "P0", "carror-os")
                print(json.dumps({
                    "continue": False,
                    "reason": f"连续 {streak} 次构建失败达到硬阻断阈值 {hard_block_threshold}。执行根因分析后再试。"
                }))
                sys.exit(2)
        else:
            # Build succeeded, reset streak
            try:
                if build_fail_file.exists():
                    build_fail_file.unlink()
                gate_file = state_dir / "build-fail-gate.json"
                if gate_file.exists():
                    gate_file.unlink()
            except OSError:
                pass

    # === Hook-Skill 运行时桥 ===
    skill_route_msg = ""
    if re.search(r"Git提交|Git推送", audit_msg):
        skill_route_msg = "[Hook-Skill桥] Git 操作已执行。建议: /lx-pre-commit 验证提交质量 → /lx-pre-push 推送前门禁"
    elif re.search(r"递归删除|rm -rf|destructive", audit_msg):
        skill_route_msg = "[Hook-Skill桥] 危险删除操作。建议: 确认操作范围 → /lx-sync 检查变更后一致性"
    elif escape_e4_msg:
        skill_route_msg = "[Hook-Skill桥] 证据编造检测。建议: 运行实际测试 → /lx-test-gen 生成测试 → 重新验证"
    elif escape_e3_msg:
        skill_route_msg = "[Hook-Skill桥] 上下文规避检测。建议: /compact 释放上下文 → 重新评估是否需要子 agent"
    elif anti_pattern_msg and "C1" in anti_pattern_msg:
        skill_route_msg = "[Hook-Skill桥] 编译错误盲修(C1)。建议: /lx-stepwise 逐步攻坚 → 收集全部错误 → 从根错误开始修复"
    elif anti_pattern_msg:
        skill_route_msg = "[Hook-Skill桥] 反模式检测。建议: /lx-code-review 审查代码 → 对照 anti-patterns.md 检查"

    # Merge all messages
    combined_parts = []
    if audit_msg:
        combined_parts.append(audit_msg)
    if anti_pattern_msg:
        combined_parts.append(anti_pattern_msg)
    if escape_e4_msg:
        combined_parts.append(escape_e4_msg)
    if escape_e3_msg:
        combined_parts.append(escape_e3_msg)
    if skill_route_msg:
        combined_parts.append(skill_route_msg)

    combined_msg = " | ".join(combined_parts)

    # issue-triage 集成
    triage_msg = ""
    combined_issues = ""
    if escape_e4_msg:
        combined_issues = f"E4证据编造: {escape_e4_msg}"
    if anti_pattern_msg and "C1" in anti_pattern_msg:
        sep = "; " if combined_issues else ""
        combined_issues = f"{combined_issues}{sep}C1编译错误盲修: {anti_pattern_msg}"
    if escape_e3_msg:
        sep = "; " if combined_issues else ""
        combined_issues = f"{combined_issues}{sep}E3上下文规避: {escape_e3_msg}"

    triage_priority = "P1"
    if escape_e4_msg:
        triage_priority = "P0"

    if combined_issues:
        triage_script = script_dir.parent / "scripts" / "issue-triage.sh"
        if triage_script.exists():
            try:
                result = subprocess.run(
                    ["bash", str(triage_script), "triage_for_hook", "posttool-bash-audit",
                     combined_issues, triage_priority, "{}"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    triage_msg = result.stdout.strip()
            except Exception:
                pass

    if triage_msg:
        combined_msg = f"{combined_msg} | {triage_msg}" if combined_msg else triage_msg

    if not combined_msg:
        output_continue()
        return

    flywheel_event("posttool_bash_audit", "detected", "P2")
    print(hc_emit_hook_json(combined_msg, "PostToolUse", True))
    sys.exit(0)


if __name__ == "__main__":
    main()
