#!/usr/bin/env python3
"""
lx-goal.py — 目标模式（目标驱动自主执行）
Python 移植版，完全等价 lx-goal.sh v1.0

用法: python3 lx-goal.py on|off|status|set|report|poll|task-done|skip-risk|retry

目标模式: 给 AI 一个具体目标，AI 持续执行直到完成或过期，不干扰人，默认 6h 过期
与 lx-ghost 的区别: goal = 目标驱动（具体任务），ghost = 方向驱动（开源探索）

向后兼容: 旧 unattended-mode.json / .unattended-mode 文件标记仍可被 is_mode_active() 检测

哲学映射:
  #3 先守护: gate 降级为 warn-only 而非硬阻断
  #4 没验证=没做: task-done 逐项确认 + report 完整输出
  #6 0信任: 危险操作记录 skipped_risks 而不是跳过
  #7 文档优先: 完成时自动生成报告文档
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Path initialization ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
MODE_FILE = STATE_DIR / "tokens" / "lx-goal.json"

# ─── Helpers ───
def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _py_json_atomic(filepath: Path, data: dict):
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


def _now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _hc_get(key: str, default: str = "") -> str:
    hc_path = STATE_DIR / ".harness-cache"
    if hc_path.exists():
        try:
            for line in hc_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(key + "="):
                    return line.split("=", 1)[1]
        except Exception:
            pass
    return default


# ─── KNOWN_SUBCOMMANDS ───
_KNOWN_SUBCOMMANDS = {"on", "off", "status", "set", "report", "poll", "task-done", "skip-risk", "retry"}


# ─── Commands ───
def cmd_on(args: list[str]):
    goal = args[0] if args else "目标任务未指定"
    expiry_hours_str = args[1] if len(args) > 1 else _hc_get("goal_mode.default_expiry_hours", "6")
    try:
        expiry_hours = float(expiry_hours_str)
    except ValueError:
        expiry_hours = 6

    expires = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()

    data = {
        "active": True,
        "mode": "goal",
        "goal": goal,
        "expires_at": expires,
        "activated_at": _now_utc(),
        "retry_count": 0,
        "skipped_risks": [],
        "completed_tasks": [],
    }
    _ensure_dir(MODE_FILE.parent)
    _py_json_atomic(MODE_FILE, data)

    # Clean old formats
    for old in [STATE_DIR / "unattended-mode.json", STATE_DIR / ".unattended-mode"]:
        old.unlink(missing_ok=True)

    # Create autonomous.active signal
    _ensure_dir(STATE_DIR / "tokens")
    (STATE_DIR / "tokens" / "autonomous.active").touch(exist_ok=True)

    print(f"✅ 目标模式已开启 — 目标: {goal}, {expiry_hours}h 过期")
    print("   autonomous.active 信号已创建，所有 hook 降级为 warn-only")
    print("  使用 CronCreate 跨会话恢复（无 10 轮上限）")
    print('  任务逐项标记: lx-goal task-done "完成项描述"')
    print("  完成后输出报告: lx-goal report")


def cmd_off():
    if MODE_FILE.exists():
        MODE_FILE.unlink()
    # Clean old formats
    for old in [STATE_DIR / "unattended-mode.json", STATE_DIR / ".unattended-mode"]:
        old.unlink(missing_ok=True)
    (STATE_DIR / "tokens" / "autonomous.active").unlink(missing_ok=True)
    print("✅ 目标模式已关闭，所有 hook 恢复正常阻断")


def cmd_status():
    if MODE_FILE.exists():
        data = _read_json(MODE_FILE)
        goal = data.get("goal", "?")
        exp = data.get("expires_at", "无")
        done_count = len(data.get("completed_tasks", []))
        skip_count = len(data.get("skipped_risks", []))
        retry = data.get("retry_count", 0)
        print("📋 目标模式 (lx-goal): 🟢 开启中")
        print(f"   目标: {goal}")
        print(f"   过期: {exp}")
        print(f"   已完成: {done_count}  跳过风险: {skip_count}  重试: {retry}")
    else:
        print("📋 目标模式 (lx-goal): ⚪ 已关闭")


def cmd_set(args: list[str]):
    if len(args) < 2:
        print("用法: lx-goal set <key> <value>", file=sys.stderr)
        sys.exit(1)
    key = args[0]
    value = args[1]

    mode_file = MODE_FILE
    if not mode_file.exists():
        print("❌ 目标模式未开启，无法修改")
        sys.exit(1)

    data = _read_json(mode_file)
    try:
        data[key] = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        data[key] = value
    _py_json_atomic(mode_file, data)
    print(f"✅ 目标模式 {key} 已更新为 {value}")


def cmd_report():
    mode_file = MODE_FILE
    report_file = STATE_DIR / "goal-report.md"

    if not mode_file.exists():
        print("⚠️ 目标模式未开启，无报告可输出")
        sys.exit(1)

    data = _read_json(mode_file)
    goal = data.get("goal", "?")
    done_tasks = data.get("completed_tasks", [])
    skipped_risks = data.get("skipped_risks", [])
    retry = data.get("retry_count", 0)
    activated = data.get("activated_at", "?")
    expires = data.get("expires_at", "?")

    task_lines = []
    for t in done_tasks:
        desc = t.get("description", str(t)) if isinstance(t, dict) else str(t)
        ts = t.get("timestamp", "") if isinstance(t, dict) else ""
        task_lines.append(f"- [x] {desc}  ({ts})")

    skip_lines = []
    for r in skipped_risks:
        desc = r.get("description", str(r)) if isinstance(r, dict) else str(r)
        skip_lines.append(f"- {desc}")

    lines = [
        "# 目标模式执行报告",
        f"生成时间: {_now_local()}",
        "",
        "## 目标",
        goal,
        "",
        "## 基本信息",
        f"- 激活时间: {activated}",
        f"- 过期时间: {expires}",
        "",
        "## 执行摘要",
        f"- 已完成任务数: {len(done_tasks)}",
        f"- 跳过风险数: {len(skipped_risks)}",
        f"- 重试次数: {retry}",
        "",
        "## 已完成任务",
    ]
    if task_lines:
        lines.extend(task_lines)
    else:
        lines.append("无")
    lines.append("")
    lines.append("## 跳过的风险")
    if skip_lines:
        lines.extend(skip_lines)
    else:
        lines.append("无")
    lines.append("")
    lines.append("## 验证状态")
    lines.append(f"VERIFIED: 报告生成完毕（{len(done_tasks)} 项完成，{len(skipped_risks)} 项风险跳过，{retry} 次重试）")
    lines.append("")

    _ensure_dir(report_file.parent)
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 报告已生成: {report_file}")
    print(report_file.read_text(encoding="utf-8"))


def cmd_poll():
    poll_file = MODE_FILE
    if not poll_file.exists():
        print("❌ 目标模式未激活，停止轮询")
        sys.exit(1)

    data = _read_json(poll_file)
    expires = data.get("expires_at", "")
    if expires:
        try:
            exp = datetime.fromisoformat(expires)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > exp:
                print(f"⏰ 目标模式已过期（{expires}），自动关闭")
                poll_file.unlink(missing_ok=True)
                (STATE_DIR / "tokens" / "autonomous.active").unlink(missing_ok=True)
                # Generate expired report
                if MODE_FILE.exists():
                    print("   生成过期报告...")
                    cmd_report()
                sys.exit(0)
        except ValueError:
            pass

    goal = data.get("goal", "?")
    done_count = len(data.get("completed_tasks", []))
    skip_count = len(data.get("skipped_risks", []))
    retry = data.get("retry_count", 0)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"🔄 目标轮询 {now_str}")
    print(f"   目标: {goal}")
    print(f"   已完成: {done_count}  已跳过风险: {skip_count}  重试次数: {retry}")

    # Integrate retry-budget
    retry_py = SCRIPT_DIR / "retry-budget.py"
    retry_sh = SCRIPT_DIR / "retry-budget.sh"
    if retry_py.exists():
        _run_subprocess([sys.executable, str(retry_py), "check"])
    elif retry_sh.exists():
        _run_subprocess(["bash", str(retry_sh), "check"])

    print("   请继续执行目标，完成后用 lx-goal task-done 或 lx-goal report 输出报告")


def _run_subprocess(cmd: list[str]) -> tuple[str, int]:
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", -1


def cmd_task_done(args: list[str]):
    description = args[0] if args else "未知任务"
    task_file = MODE_FILE
    if not task_file.exists():
        print("❌ 目标模式未开启")
        sys.exit(1)

    ts = datetime.now().isoformat()
    task_entry = {"description": description, "timestamp": ts}

    data = _read_json(task_file)
    tasks = data.get("completed_tasks", [])
    tasks.append(task_entry)
    data["completed_tasks"] = tasks
    _py_json_atomic(task_file, data)
    print(f"✅ 已标记任务完成: {description}")


def cmd_skip_risk(args: list[str]):
    description = args[0] if args else "未知风险"
    task_file = MODE_FILE
    if not task_file.exists():
        print("❌ 目标模式未开启")
        sys.exit(1)

    data = _read_json(task_file)
    risks = data.get("skipped_risks", [])
    risks.append({"description": description, "timestamp": _now_utc()})
    data["skipped_risks"] = risks
    _py_json_atomic(task_file, data)
    print(f"📝 已记录跳过的风险: {description}")


def cmd_retry():
    task_file = MODE_FILE
    if not task_file.exists():
        print("❌ 目标模式未开启")
        sys.exit(1)

    data = _read_json(task_file)
    data["retry_count"] = data.get("retry_count", 0) + 1
    _py_json_atomic(task_file, data)
    print("📝 重试计数 +1")


def print_usage():
    print("用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry")
    print("")
    print("子命令:")
    print('  lx-goal on "目标描述" [过期小时=6]')
    print('    示例: lx-goal on "完成 feature-registry 中所有 P0 条目的同步"')
    print('    示例: lx-goal on "将 test 覆盖率从 45% 提升到 80%" 8')
    print("  lx-goal off")
    print("  lx-goal status")
    print("  lx-goal set <json_key> <json_value>")
    print("  lx-goal report                    输出执行报告")
    print("  lx-goal poll                      轮询入口（CronCreate 调用）")
    print('  lx-goal task-done "描述"          标记任务完成')
    print('  lx-goal skip-risk "描述"          记录跳过的风险')
    print("  lx-goal retry                     重试计数 +1")
    print("")
    print("驱动方式:")
    print("  使用 CronCreate 调度 lx-goal poll   (跨会话恢复，无 10 轮上限)")
    print('  /ralph-loop:ralph-loop "..."       (自愈循环)')
    print("")
    print("与 lx-ghost 的区别:")
    print("  lx-goal = 目标驱动（具体任务），lx-ghost = 方向驱动（开放探索）")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    # Smart parameter detection
    if cmd not in _KNOWN_SUBCOMMANDS:
        cmd_on(args)
        return

    if cmd == "on":
        cmd_on(args[1:])
    elif cmd == "off":
        cmd_off()
    elif cmd == "status":
        cmd_status()
    elif cmd == "set":
        cmd_set(args[1:])
    elif cmd == "report":
        cmd_report()
    elif cmd == "poll":
        cmd_poll()
    elif cmd == "task-done":
        cmd_task_done(args[1:])
    elif cmd == "skip-risk":
        cmd_skip_risk(args[1:])
    elif cmd == "retry":
        cmd_retry()
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
