#!/usr/bin/env python3
"""
lx-ghost.py — 幽灵模式（方向驱动自主探索）
Python 移植版，完全等价 lx-ghost.sh v1.0

用法: python3 lx-ghost.py on|off|status|set|poll|report|skip-risk|hard-boundary-hit|retry

幽灵模式: 给 AI 一个"方向"，AI 自主探索并修复，不干扰人，默认 3h 过期
与 lx-goal 的区别: ghost = 方向驱动（开源探索），goal = 目标驱动（具体任务）
同时创建 autonomous.active 信号供所有 hook 降级

哲学映射:
  #3 先守护: gate 降级为 warn-only 而非硬阻断
  #4 没验证=没做: poll 报告 + completion 软评分
  #6 0信任: 危险操作记录 skipped_risks 而不是跳过
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Path initialization ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
MODE_FILE = STATE_DIR / "tokens" / "lx-ghost.json"

# Name for hc_get default lookups
PYTHON_BIN = os.environ.get("PYTHON_BIN", "python3")


# ─── Helpers ───
def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _py_json_atomic(filepath: Path, data: dict):
    """Write JSON atomically via tmp + rename."""
    tmp = filepath.with_name(filepath.name + ".tmp." + str(os.getpid()))
    _ensure_dir(filepath.parent)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.rename(tmp, filepath)


def _read_json(filepath: Path) -> dict:
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _hc_get(key: str, default: str = "") -> str:
    """Read from harness cache (simple fallback)."""
    hc_path = STATE_DIR / ".harness-cache"
    if hc_path.exists():
        try:
            for line in hc_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(key + "="):
                    return line.split("=", 1)[1]
        except Exception:
            pass
    return default


def _flywheel_event(event: str, severity: str = "P2", project: str = ""):
    """Log structured event to ~/.claude/flywheel-buffer.jsonl"""
    log_dir = Path.home() / ".claude"
    _ensure_dir(log_dir)
    line = f"{_now_date()},{event},{severity},{project or Path(PROJECT_ROOT).name or 'unknown'}"
    try:
        with open(log_dir / "flywheel-buffer.jsonl", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── KNOWN_SUBCOMMANDS ───
_KNOWN_SUBCOMMANDS = {"on", "off", "status", "set", "poll", "report",
                       "skip-risk", "hard-boundary-hit", "retry"}


# ─── Commands ───
def cmd_on(args: list[str]):
    direction = args[0] if args else "自主探索和修复系统问题"
    interval_str = args[1] if len(args) > 1 else _hc_get("ghost_mode.default_poll_interval", "600")
    expiry_hours_str = args[2] if len(args) > 2 else _hc_get("ghost_mode.default_expiry_hours", "3")
    min_iters_str = args[3] if len(args) > 3 else _hc_get("ghost_mode.default_min_iterations", "0")

    try:
        interval = int(interval_str)
    except ValueError:
        interval = 600
    try:
        expiry_hours = float(expiry_hours_str)
    except ValueError:
        expiry_hours = 3
    try:
        min_iters = int(min_iters_str)
    except ValueError:
        min_iters = 0

    expires = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()

    data = {
        "active": True,
        "mode": "ghost",
        "direction": direction,
        "cycle_interval_seconds": interval,
        "expires_at": expires,
        "activated_at": _now_utc(),
        "min_iterations": min_iters,
        "iterations_completed": 0,
        "retry_count": 0,
        "skipped_risks": [],
    }
    _ensure_dir(MODE_FILE.parent)
    _py_json_atomic(MODE_FILE, data)

    # Create autonomous.active signal
    autonomous_signal = STATE_DIR / "tokens" / "autonomous.active"
    autonomous_signal.touch()

    # B3: flywheel telemetry
    _flywheel_event("ghost_activated", "P2", Path(PROJECT_ROOT).name)

    # B5: sticky marker for crash detection
    _ensure_dir(STATE_DIR)
    (STATE_DIR / "ghost-session-active-at").write_text(_now_utc(), encoding="utf-8")

    # Clean old format files — all legacy variants
    for old in [STATE_DIR / ".unattended-mode",
                STATE_DIR / "ghost-mode.json",
                STATE_DIR / "ghost-mode.active",
                STATE_DIR / "tokens" / "ghost-mode.active",
                STATE_DIR / "unattended-mode.json"]:
        old.unlink(missing_ok=True)

    print(f"✅ 幽灵模式已开启 — 方向: {direction}, 每 {interval}s 轮询, {expiry_hours}h 过期")
    print("   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only")
    print(f"   调用 /loop {interval}s lx-ghost poll 驱动探索轮次")
    print('   或 /lx-ghost on "继续" — 在同一次会话内继续探索')
    print("")

    # Print decision chain
    decision_chain = PROJECT_ROOT / ".claude" / "reference" / "autonomous-decision-chain.md"
    if decision_chain.exists():
        print("[.claude/reference/autonomous-decision-chain.md]")
        print(decision_chain.read_text(encoding="utf-8"))
        print("")

    print("📋 退出报告模板（完成探索后使用 lx-ghost report '...' 提交）：")
    print("")
    print("## 探索摘要")
    print("（方向、轮次、关键发现）")
    print("")
    print("## 已完成操作")
    print("（逐项列出 + Before/After 对比）")
    print("")
    print("## ⚠️ 需人类介入项（硬边界）")
    print("（被硬边界跳过的操作 + 原因 + 建议人类操作）")
    print("")
    print("## 已跳过风险")
    print("（skip-risk 记录项）")
    print("")
    print("## 附带发现")
    print("（范围外问题）")
    print("")


def cmd_off(args: list[str]):
    force = args[0] if args else ""
    exit_report = STATE_DIR / "ghost-exit-report.md"

    if force != "--force":
        if not exit_report.exists():
            print("🛑 幽灵模式关闭被阻止 — 未找到退出报告", file=sys.stderr)
            print("", file=sys.stderr)
            print("   在关闭幽灵模式前，你必须先完成退出报告：", file=sys.stderr)
            print("     1. 在对话中按 SKILL.md 退出报告结构生成报告", file=sys.stderr)
            print("     2. 执行: lx-ghost report '你的完整报告内容'", file=sys.stderr)
            print("     3. 或: 使用 lx-ghost report 生成报告后再重试", file=sys.stderr)
            print("", file=sys.stderr)
            print("   紧急绕过: lx-ghost off --force（报告将在下次 SessionStart 提醒补交）", file=sys.stderr)
            sys.exit(1)

        # Verify report completeness
        report_text = exit_report.read_text(encoding="utf-8", errors="replace") if exit_report.exists() else ""
        required_sections = ["探索摘要", "已完成操作", "需人类介入", "已跳过风险", "附带发现"]
        missing = [s for s in required_sections if s not in report_text]

        if missing:
            print(f"🛑 退出报告不完整 — 缺少必填章节:{' '.join(missing)}", file=sys.stderr)
            print("   请补充缺失章节后重试 lx-ghost off", file=sys.stderr)
            sys.exit(1)
    else:
        print("⚠️  强制关闭（--force），跳过了退出报告检查", file=sys.stderr)
        (STATE_DIR / "ghost-exit-pending").touch()
        _flywheel_event("ghost_forced_close", "P1", Path(PROJECT_ROOT).name)

    if MODE_FILE.exists():
        MODE_FILE.unlink()

    # Clean old format files
    for old in [STATE_DIR / "ghost-mode.json", STATE_DIR / "tokens" / "ghost-mode.active",
                STATE_DIR / "tokens" / "autonomous.active", STATE_DIR / "ghost-session-active-at"]:
        old.unlink(missing_ok=True)

    print("✅ 幽灵模式已关闭，所有 hook 恢复正常阻断")
    if exit_report.exists():
        print(f"   退出报告: {exit_report}")
    if force != "--force":
        pending = STATE_DIR / "ghost-exit-pending"
        pending.unlink(missing_ok=True)
        _flywheel_event("ghost_completed_with_report", "P2", Path(PROJECT_ROOT).name)

    print("   提示: 如有 CronCreate 轮询作业，请执行 CronDelete <job_id> 清理。")


def cmd_status():
    if MODE_FILE.exists():
        data = _read_json(MODE_FILE)
        direction = data.get("direction", "?")
        expires = data.get("expires_at", "无")
        interval = data.get("cycle_interval_seconds", "?")
        retry = data.get("retry_count", 0)
        skip_count = len(data.get("skipped_risks", []))
        hard_count = len(data.get("hard_boundary_hits", []))
        print(f"📋 幽灵模式 (lx-ghost): 🟢 开启中")
        print(f"   方向: {direction}")
        print(f"   间隔: {interval}s")
        print(f"   过期: {expires}")
        print(f"   重试: {retry}  跳过风险: {skip_count}  硬边界: {hard_count}")
    elif (STATE_DIR / "ghost-mode.json").exists():
        print("📋 幽灵模式 (旧格式 ghost-mode.json): 🟡 兼容中")
        print('   建议执行 lx-ghost off && lx-ghost on "方向" 迁移到新格式')
    else:
        print("📋 幽灵模式 (lx-ghost): ⚪ 已关闭")

    autonomous_signal = STATE_DIR / "tokens" / "autonomous.active"
    if autonomous_signal.exists():
        print("   autonomous.active 信号: ✅ 存在")


def cmd_set(args: list[str]):
    if len(args) < 2:
        print("用法: lx-ghost set <key> <value>", file=sys.stderr)
        sys.exit(1)
    key = args[0]
    value = args[1]
    if not MODE_FILE.exists():
        print("❌ 幽灵模式未开启，无法修改")
        sys.exit(1)

    data = _read_json(MODE_FILE)
    # Try to parse value as JSON if possible
    try:
        data[key] = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        data[key] = value
    _py_json_atomic(MODE_FILE, data)
    print(f"✅ 幽灵模式 {key} 已更新为 {value}")


def cmd_poll():
    """Ghost mode poll entry — called by loop skill / ralph-loop"""
    if not MODE_FILE.exists():
        old_file = STATE_DIR / "ghost-mode.json"
        if old_file.exists():
            data = _read_json(old_file)
            direction = data.get("direction", "?")
            print(f"⚠️ 旧格式 ghost-mode.json 存在，建议迁移: lx-ghost off && lx-ghost on \"{direction}\"")
        else:
            print("❌ 幽灵模式未激活，停止轮询")
        sys.exit(1)

    # Check expiry
    data = _read_json(MODE_FILE)
    expires = data.get("expires_at", "")
    if expires:
        try:
            exp = datetime.fromisoformat(expires)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > exp:
                print(f"⏰ 幽灵模式已过期（{expires}），自动关闭")
                (STATE_DIR / "ghost-exit-pending").touch()
                _flywheel_event("ghost_expired_no_report", "P1", Path(PROJECT_ROOT).name)
                MODE_FILE.unlink(missing_ok=True)
                (STATE_DIR / "tokens" / "autonomous.active").unlink(missing_ok=True)
                sys.exit(0)
        except ValueError:
            pass

    direction = data.get("direction", "?")
    retry_count = data.get("retry_count", 0)
    skip_count = len(data.get("skipped_risks", []))
    hard_count = len(data.get("hard_boundary_hits", []))

    print(f"=== 幽灵轮询 [{_now_utc()}] ===")
    print(f"  方向: {direction}")
    print(f"  重试次数: {retry_count}  已跳过风险: {skip_count}  硬边界: {hard_count}")

    # Status panel: active features + uncommitted changes
    rpe_dir = PROJECT_ROOT / "rpe"
    if rpe_dir.is_dir():
        features = sorted(d.name for d in rpe_dir.iterdir() if d.is_dir())
        if features:
            print(f"  活跃特征: {' '.join(features[:5])}")

    try:
        result = subprocess_run(["git", "diff", "--name-only"], cwd=str(PROJECT_ROOT))
        modified = result.strip()
        if modified:
            print(f"  未提交变更: {' '.join(modified.splitlines()[:10])}")
    except Exception:
        pass

    # Integrate retry-budget status check
    retry_script = SCRIPT_DIR / "retry-budget.sh"
    retry_py = SCRIPT_DIR / "retry-budget.py"
    retry_path = retry_py if retry_py.exists() else retry_script
    if retry_path.exists():
        if retry_path.suffix == ".py":
            ctx, code = run_python_subprocess([str(retry_path), "check"])
        else:
            ctx, code = run_bash_subprocess([str(retry_path), "check"])
        if code == 2 and ctx:
            print("⚠️ [Retry Budget BLOCKED] 以下错误已达 3 次上限，需人工干预:")
            for line in ctx.splitlines()[:5]:
                print(f"  {line}")
        elif code == 0:
            print("  retry-budget: 正常")

    # Score check
    score_script = SCRIPT_DIR / "auto-score.sh"
    if score_script.exists():
        print("  评分检查: 可用 (bash auto-score.sh)")

    print(f"  命令: {direction}")
    print("  自主探索并修复，发现问题自行处理（最多 3 次），无法处理的记录等待人工")
    print("  ⚡ 注意保持方向感，不要偏离方向做无关优化")


def cmd_report(args: list[str]):
    """Generate exit report"""
    report_content = args[0] if args else ""
    exit_report = STATE_DIR / "ghost-exit-report.md"

    if not report_content:
        print("用法: lx-ghost report '<markdown报告内容>'", file=sys.stderr)
        print("", file=sys.stderr)
        print("报告必须包含 5 个必填章节：", file=sys.stderr)
        print("  ## 探索摘要  — 方向、轮次、关键发现", file=sys.stderr)
        print("  ## 已完成操作 — 逐项列出", file=sys.stderr)
        print("  ## ⚠️ 需人类介入项（硬边界）", file=sys.stderr)
        print("  ## 已跳过风险", file=sys.stderr)
        print("  ## 附带发现", file=sys.stderr)
        sys.exit(1)

    _ensure_dir(exit_report.parent)
    exit_report.write_text(report_content, encoding="utf-8")

    # Validate sections
    required_sections = ["探索摘要", "已完成操作", "需人类介入", "已跳过风险", "附带发现"]
    missing = [s for s in required_sections if s not in report_content]

    if missing:
        print(f"⚠️  报告已保存，但缺少章节:{' '.join(missing)}", file=sys.stderr)
        print("   请在 lx-ghost off 前补充完整", file=sys.stderr)
    else:
        # Content quality gate: each section >= 20 non-whitespace chars
        thin_sections = []
        for section in required_sections:
            idx = report_content.find(section)
            if idx < 0:
                continue
            rest = report_content[idx + len(section):]
            end = rest.find("\n## ")
            sect_text = rest[:end] if end > 0 else rest
            chars = len(re.sub(r'\s+', '', sect_text))
            if chars < 20:
                thin_sections.append(f"{section}({chars}chars)")

        if thin_sections:
            print(f"⚠️  报告已保存，但以下章节内容过少（<20 非空白字符）:{' '.join(thin_sections)}", file=sys.stderr)
            print("   请在 lx-ghost off 前充实内容", file=sys.stderr)
        else:
            print("✅ 退出报告已生成并通过章节完整性 + 内容质量验证（5/5），可以执行 lx-ghost off")


def cmd_skip_risk(args: list[str]):
    description = args[0] if args else "未知风险"
    if not MODE_FILE.exists():
        print("❌ 幽灵模式未开启")
        sys.exit(1)
    data = _read_json(MODE_FILE)
    risks = data.get("skipped_risks", [])
    risks.append({"description": description, "timestamp": _now_utc()})
    data["skipped_risks"] = risks
    _py_json_atomic(MODE_FILE, data)
    print(f"📝 已记录跳过的风险: {description}")


def cmd_hard_boundary_hit(args: list[str]):
    description = args[0] if args else "未知硬边界"
    reason = args[1] if len(args) > 1 else "未知原因"
    human_action = args[2] if len(args) > 2 else "请人工审阅并决定是否执行"
    if not MODE_FILE.exists():
        print("❌ 幽灵模式未开启")
        sys.exit(1)
    data = _read_json(MODE_FILE)
    hits = data.get("hard_boundary_hits", [])
    hits.append({
        "description": description,
        "reason": reason,
        "human_action": human_action,
        "timestamp": _now_utc(),
    })
    data["hard_boundary_hits"] = hits
    _py_json_atomic(MODE_FILE, data)
    print(f"🛑 硬边界拦截已记录: {description} (原因: {reason})")


def cmd_retry():
    if not MODE_FILE.exists():
        print("❌ 幽灵模式未开启")
        sys.exit(1)
    data = _read_json(MODE_FILE)
    data["retry_count"] = data.get("retry_count", 0) + 1
    _py_json_atomic(MODE_FILE, data)
    new_count = data["retry_count"]
    print(f"📝 重试计数 +1（当前: {new_count}）")


def print_usage():
    print("用法: lx-ghost on|off|status|set|poll|skip-risk|hard-boundary-hit|retry")
    print("")
    print("子命令:")
    print('  lx-ghost on "方向描述" [间隔秒数=600] [过期小时=3]')
    print('    示例: lx-ghost on "将项目四维评分提升到 90+"')
    print('    示例: lx-ghost on "检查所有 shell 脚本安全隐患" 300 2')
    print("  lx-ghost off")
    print("  lx-ghost status")
    print("  lx-ghost set <json_key> <json_value>")
    print("  lx-ghost poll                    (loop skill 轮询入口)")
    print('  lx-ghost skip-risk "描述"       (记录跳过的风险)')
    print('  lx-ghost hard-boundary-hit "操作" "原因" "需人类执行"  (记录硬边界拦截)')
    print("  lx-ghost retry                   (重试计数 +1)")
    print("")
    print("驱动方式:")
    print("  /loop 600s lx-ghost poll         (定时轮询)")
    print('  /ralph-loop:ralph-loop "..."     (自愈循环)')
    print("")
    print("与 lx-goal 的区别:")
    print("  lx-ghost = 方向驱动（开源探索），lx-goal = 目标驱动（具体任务）")


def run_bash_subprocess(cmd_args: list[str]) -> tuple[str, int]:
    """Run a shell command and return (stdout, returncode)."""
    import subprocess
    try:
        r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def run_python_subprocess(cmd_args: list[str]) -> tuple[str, int]:
    """Run a python subprocess and return (stdout, returncode)."""
    import subprocess
    try:
        r = subprocess.run([sys.executable] + cmd_args, capture_output=True, text=True, timeout=30)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def subprocess_run(cmd: list[str], cwd: str = None) -> str:
    """Simple subprocess run returning stdout."""
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)
        return r.stdout.strip()
    except Exception:
        return ""


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    # Smart parameter detection: if first arg is not a known subcommand, treat as direction
    if cmd not in _KNOWN_SUBCOMMANDS:
        cmd = "on"
        # shift: the first arg becomes the direction
        # args stays the same, but we pass all args to cmd_on
        cmd_on(args)
        return

    if cmd == "on":
        cmd_on(args[1:])
    elif cmd == "off":
        cmd_off(args[1:])
    elif cmd == "status":
        cmd_status()
    elif cmd == "set":
        cmd_set(args[1:])
    elif cmd == "poll":
        cmd_poll()
    elif cmd == "report":
        cmd_report(args[1:])
    elif cmd == "skip-risk":
        cmd_skip_risk(args[1:])
    elif cmd == "hard-boundary-hit":
        cmd_hard_boundary_hit(args[1:])
    elif cmd == "retry":
        cmd_retry()
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
