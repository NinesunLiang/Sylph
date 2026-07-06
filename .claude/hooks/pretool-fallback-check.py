#!/usr/bin/env python3
"""
pretool-fallback-check.py — 自动心跳降级检测

CC hook: PretoolUseExecution
每步执行前自动运行 fallback_matrix + context_watermark 检测。
发现异常时注入警告到 AI 上下文，迫使 AI 采取降级措施。

预期输出：
  {"continue": true}        → 正常，放行
  {"continue": true, "output_additional_context": [...], "stderr": ...}  → 有警告但仍放行
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path.cwd()
OMC_ROOT = PROJECT_ROOT / ".omc"
OMC_STATE = OMC_ROOT / "state"
OMC_TOKENS = OMC_ROOT / "tokens"
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
OMC_SCRIPTS = OMC_ROOT / "scripts"

# ─── 令牌路径 ───
LEVEL_GATE_TOKEN = OMC_TOKENS / "level-gate.json"
LX_GOAL_TOKEN = OMC_STATE / "tokens" / "lx-goal.json"

# ─── 保活标记 ───
LAST_HEARTBEAT_FILE = OMC_STATE / ".fallback_last_heartbeat"
FALLBACK_LOG = OMC_STATE / "fallback-events.jsonl"


def _read_stdin():
    """读取 CC 传递的 JSON 输入"""
    try:
        raw = sys.stdin.read()
        if not raw:
            return {}
        return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return {}


def _script_path(name: str) -> Path:
    """优先 .omc/scripts/，回退 .claude/hooks/"""
    p = OMC_SCRIPTS / name
    if p.exists():
        return p
    return HOOKS_DIR / name


def _run_script(name: str, *args) -> dict:
    """运行同目录脚本并解析 JSON 输出"""
    script = _script_path(name)
    if not script.exists():
        return {"error": f"Script not found: {script}"}
    try:
        result = subprocess.run(
            [sys.executable, str(script)] + list(args),
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT) if PROJECT_ROOT.exists() else None,
        )
        out = result.stdout.strip()
        if out:
            obj = json.loads(out.split("\n")[0])
            return obj
        return {"error": f"No JSON output from {name}", "stderr": result.stderr[:200]}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error from {name}: {e}", "raw": out[:200]}
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout running {name}"}
    except Exception as e:
        return {"error": f"Error running {name}: {e}"}


def _count_no_verify():
    """统计最近 audit 中有 tick 无 verify 的连续次数"""
    try:
        audit_dir = OMC_STATE / "audit"
        if not audit_dir.exists():
            return 0
        jsonl_files = sorted(audit_dir.glob("*.jsonl"), reverse=True)
        if not jsonl_files:
            return 0
        tick_count = 0
        verify_count = 0
        for jf in jsonl_files[:3]:
            with open(jf) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("event") == "verify":
                            verify_count += 1
                        elif rec.get("event") == "tick":
                            tick_count += 1
                    except json.JSONDecodeError:
                        pass
        if tick_count >= 3 and verify_count == 0:
            return 3
        return 0
    except Exception:
        return 0


def _check_idle_time():
    """检查 session-handoff.md 的 mtime 判断是否长时间无人"""
    try:
        for handoff_path in [OMC_STATE / "session-handoff.md",
                             PROJECT_ROOT / ".claude/session-handoff.md"]:
            if handoff_path.exists():
                mtime = handoff_path.stat().st_mtime
                now = datetime.now(timezone.utc).timestamp()
                return now - mtime
    except Exception:
        pass
    return 0


def _is_autonomous():
    """判断是否无人值守模式"""
    try:
        p = OMC_STATE / "token.json"
        if p.exists():
            token = json.loads(p.read_text())
            if token.get("au") == 1 or token.get("autonomous", False):
                return True
        # 备选：检查环境
        if os.environ.get("CARROROS_AUTONOMOUS") == "1":
            return True
        return False
    except Exception:
        return False


def _log_event(event: dict):
    """记录降级事件到 fallback-events.jsonl"""
    try:
        OMC_STATE.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            **event,
        }
        with open(FALLBACK_LOG, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _update_heartbeat():
    """更新保活标记"""
    try:
        OMC_STATE.mkdir(parents=True, exist_ok=True)
        LAST_HEARTBEAT_FILE.write_text(str(time.time()))
    except Exception:
        pass


def _clear_heartbeat():
    """清除保活标记"""
    try:
        if LAST_HEARTBEAT_FILE.exists():
            LAST_HEARTBEAT_FILE.unlink()
    except Exception:
        pass


def check_conditions(input_data=None) -> dict:
    """综合检查所有降级条件，返回裁决"""
    if input_data is None:
        input_data = {}
    autonomous = _is_autonomous()
    issues = []
    should_block = False

    # --- 0. 令牌检测：level-gate.json + lx-goal.json → 模式注入 ---
    mode_context_lines = []
    if LEVEL_GATE_TOKEN.exists():
        try:
            lgt = json.loads(LEVEL_GATE_TOKEN.read_text())
            if lgt.get("level") == "L2":
                reasons = "; ".join(lgt.get("reasons", []))
                mode_context_lines.append(
                    "## 🚨 [LevelGate] 当前任务为 L2 高治理级别"
                )
                mode_context_lines.append(f"原因: {reasons}")
                mode_context_lines.append(
                    "必须使用 L2 工作流: 三段式水位 + Oracle 审核 + VerifyGate 每步 + 学习飞轮"
                )
        except (json.JSONDecodeError, OSError):
            pass
    if LX_GOAL_TOKEN.exists():
        try:
            lxg = json.loads(LX_GOAL_TOKEN.read_text())
            if lxg.get("active"):
                goal = lxg.get("goal", "?")
                mode_context_lines.append(
                    "## 🎯 [Goal] 目标驱动无人模式已激活"
                )
                mode_context_lines.append(f"目标: {goal}")
                mode_context_lines.append(
                    "规则: 不暂停 | 不提问 | 不中断 | 只记录"
                )
                mode_context_lines.append(
                    "卡点: 硬边界跳过->记录->继续 | 危险走裁决链 | 真阻断->blocked_human"
                )
        except (json.JSONDecodeError, OSError):
            pass
    if mode_context_lines:
        issues.append({
            "type": "mode_token_injection",
            "message": "\n".join(mode_context_lines),
            "severity": "info",
        })

    # 1. 水位检查（用 context_watermark.py）
    wm = _run_script("context_watermark.py", "--used", "0", "--limit", "200000")
    if wm.get("action") == "block_complex":
        issues.append({
            "type": "watermark_critical",
            "message": f"🔴 上下文水位临界 ({wm.get('pct', '?')}% >= 70%) — 停止新增操作，准备 compact",
            "severity": "block",
        })
        should_block = True
    elif wm.get("action") == "inject_warning":
        severity = "block" if autonomous else "warn"
        msg = (f"🔴 上下文水位警戒 ({wm.get('pct', '?')}% >= 40%) — "
               "autonomous 模式下停止操作，先 compact"
               if autonomous else
               f"🟡 上下文水位警戒 ({wm.get('pct', '?')}% >= 40%) — 注意控制上下文消耗")
        issues.append({
            "type": "watermark_warning",
            "message": msg,
            "severity": severity,
        })
        if autonomous:
            should_block = True

    # 2. 连续无 verify
    no_verify = _count_no_verify()
    if no_verify >= 3:
        severity = "block" if autonomous else "warn"
        suffix = " — autonomous 模式阻止操作，请立即 VerifyGate" if autonomous else " — 请立即做一次 VerifyGate 检查"
        issues.append({
            "type": "no_verify_3_ticks",
            "message": f"⚠ 连续 {no_verify} 个 tick 无 verify 事件{suffix}",
            "severity": severity,
        })
        if autonomous:
            should_block = True

    # 3. 长时间无人
    idle = _check_idle_time()
    if idle > 3600:
        severity = "block" if autonomous else "warn"
        suffix = " — autonomous 长时间无人，阻止操作等待人类确认" if autonomous else " — autonomous 模式建议限缩操作范围"
        issues.append({
            "type": "long_idle",
            "message": f"⏰ 长时间无人 ({int(idle):.0f}s > 3600s){suffix}",
            "severity": severity,
        })
        if autonomous:
            should_block = True

    # 4. fallback_matrix 综合检查
    fb = _run_script("fallback_matrix.py")
    if fb.get("should_fallback"):
        severity = "block" if autonomous else "warn"
        issues.append({
            "type": "fallback_triggered",
            "message": f"⚠ Fallback 触发: {fb.get('reason', 'unknown')} — 降级为 L1 Base 模式"
                       + (" (autonomous: 阻止操作)" if autonomous else ""),
            "severity": severity,
        })
        if autonomous:
            should_block = True

    # 5. Oracle 双法官 — autonomous 模式每次触发
    if autonomous:
        oracle = _run_script("oracle_gate.py", "--check", "autonomous_mode")
        if oracle.get("verdict") == "REJECT":
            issues.append({
                "type": "oracle_reject",
                "message": f"🛑 Oracle 门禁拒绝: {oracle.get('reason', '高风险操作')} — autonomous 模式阻止",
                "severity": "block",
            })
            should_block = True

    # 6. L1→L2 就地升级检测 — 检查当前操作是否触及 L2 条件
    if not autonomous:
        tool_name = (input_data.get("tool_name", "") or "").lower()
        command = input_data.get("tool_input", {}).get("command", "") or ""
        file_path = (input_data.get("tool_input", {}).get("path", "") or
                     input_data.get("filePath", "") or "")
        # 结合 level-gate 的关键词检测 L2 信号
        prompt_lower = (command + " " + file_path).lower()
        l2_paths = ("auth", "payment", "migration", "infra", "secret", "password", "credential")
        l2_keywords = ("删除", "部署", "迁移", "重构", "权限",
                       "delete", "deploy", "migrate", "refactor")
        l2_hit = any(p in prompt_lower for p in l2_paths)
        kw_hit = any(k.lower() in prompt_lower for k in l2_keywords)
        if l2_hit or kw_hit:
            issues.append({
                "type": "l1_to_l2_upgrade_hint",
                "message": f"🟡 L1→L2 就地升级建议: 当前操作触及 L2 条件"
                           f"({'敏感路径' if l2_hit else ''}{' + ' if l2_hit and kw_hit else ''}{'关键词' if kw_hit else ''})"
                           f" — 建议按 5 步升级通道将当前任务升级为 L2",
                "severity": "warn",
            })

    return {
        "should_block": should_block,
        "autonomous": autonomous,
        "issues": issues,
        "has_issues": len(issues) > 0,
    }


def build_stdout(check_result: dict) -> str:
    """构建 CC hook 标准输出"""
    result = {"continue": not check_result["should_block"]}

    # mode_token_injection 独立注入，不进 fallback 列表
    mode_context = []
    fallback_issues = []
    if check_result["has_issues"]:
        for issue in check_result["issues"]:
            if issue["type"] == "mode_token_injection":
                mode_context.append(issue["message"])
            else:
                fallback_issues.append(issue["message"])

    extra_context = []
    if mode_context:
        extra_context.append("\n---\n".join(mode_context))
    if fallback_issues:
        extra_context.append(
            "---\n## 🩺 Fallback 心跳检测\n"
            + "\n".join(f"- {m}" for m in fallback_issues)
            + "\n\n*自动检测 — 请按警告处理*"
        )
    if extra_context:
        result["output_additional_context"] = extra_context

    return json.dumps(result)


def build_stderr(check_result: dict) -> str:
    """构建 CC hook stderr 输出"""
    lines = ["[FallbackCheck]"]
    if check_result["has_issues"]:
        for issue in check_result["issues"]:
            if issue["type"] == "mode_token_injection":
                continue  # 模式注入不显示在 stderr
            lines.append(f"  {issue['message']}")
    if len(lines) == 1:
        lines.append("  ✅ All systems OK")
    return "\n".join(lines)


def main():
    input_data = _read_stdin()
    result = check_conditions(input_data)

    # 记录事件
    _log_event({
        "hook": "pretool-fallback-check",
        "autonomous": result["autonomous"],
        "should_block": result["should_block"],
        "issues": [i["type"] for i in result["issues"]],
    })

    prefix = "🛑" if result["should_block"] else "🩺"
    mode_tag = " [autonomous]" if result["autonomous"] else ""

    if result["should_block"]:
        # autonomous 模式下任何问题都阻止
        reasons = "; ".join(i["message"] for i in result["issues"])
        error_msg = (f"[FallbackCheck]{mode_tag} 🛑 autonomous 模式阻止工具执行: {reasons}")
        print(json.dumps({"continue": False, "error": error_msg}))
        print(error_msg, file=sys.stderr)
        _clear_heartbeat()
        sys.exit(0)

    if result["has_issues"]:
        # 有警告 — 放行但注入上下文
        print(build_stdout(result))
        print(build_stderr(result), file=sys.stderr)
    else:
        # 健康 — 静默放行
        print(json.dumps({"continue": True}))

    _update_heartbeat()


if __name__ == "__main__":
    main()
