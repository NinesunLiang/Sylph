#!/usr/bin/env python3
"""
carror_dashboard.py — Carror OS 健康面板 v2.0

5 面板:
  [1] Token 趋势       —— token-tracking-index.json
  [2] Error DNA 状态    —— error-dna.json / error-dna.jsonl
  [3] Flywheel P0 事件  —— ~/.claude/flywheel.log
  [4] Feature Registry  —— .claude/feature-registry.yaml
  [5] 上下文             —— token-tracking-index.json

用法:
  python3 carror_dashboard.py        # 标准面板
  python3 carror_dashboard.py --json # JSON 输出
  python3 carror_dashboard.py --watch# 每 5 秒刷新

AC 覆盖:
  AC-12.1: Token 消耗趋势 ASCII 图 + 源缺失时 degraded
  AC-12.2: Error DNA 错误类型分布直方图 + RPE-001 未就绪时 degraded
  AC-12.3: Flywheel P0 事件时间线
  AC-12.4: feature-registry.yaml 注册表状态
  AC-12.5: 所有面板数据源缺失时输出 degraded
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Paths ──
STATE = Path(".omc/state")
FEATURE_REGISTRY = Path(".claude/feature-registry.yaml")
HOME = Path.home()
FLYWHEEL_LOG = HOME / ".claude" / "flywheel.log"
FLYWHEEL_ACK = HOME / ".claude" / "flywheel-ack.log"

# ── Colors ──
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Panel width —— inner (excludes side borders) ──
WI = 46

# ── Status constants ──
STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"


def colored(text, color):
    return f"{color}{text}{RESET}"


def visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


def bar(value, width=20):
    """Draw a horizontal bar chart element (value: 0-100)."""
    if value <= 0:
        return colored("░" * width, DIM)
    filled = min(int(round(value * width / 100)), width)
    empty = width - filled
    if value >= 80:
        c = GREEN
    elif value >= 50:
        c = YELLOW
    else:
        c = RED
    return colored("█" * filled, c) + colored("░" * empty, DIM)


def bar_by_count(value, max_value, width=20):
    """Draw a bar proportional to value/max_value."""
    if max_value <= 0:
        return colored("░" * width, DIM)
    pct = value * 100 / max_value
    return bar(pct, width)


# ── Box rendering ──

def p(text=""):
    """Print a single line within the box (borders auto-added)."""
    vlen = visible_len(text)
    pad = max(0, WI - vlen)
    sys.stdout.write(f"{colored('│', CYAN)}{text}{' ' * pad}{colored('│', CYAN)}\n")


def title(text):
    """Print a centered title."""
    vlen = visible_len(text)
    left = max(0, (WI - vlen) // 2)
    p(" " * left + text)


def section(name):
    """Print a section header (left-aligned with leading space)."""
    p(" " + colored(name, BOLD + YELLOW))
    p()


def degraded_msg(source):
    """Print a degraded status line."""
    p(" " + colored(f"[degraded] {source} ", RED + DIM) + colored("数据源不可用", DIM))


def empty_msg(msg):
    """Print an empty/no-data message."""
    p(" " + colored(msg, DIM))


def top():
    sys.stdout.write(f"{colored('┌', CYAN)}{colored('─' * WI, CYAN)}{colored('┐', CYAN)}\n")


def bottom():
    sys.stdout.write(f"{colored('└', CYAN)}{colored('─' * WI, CYAN)}{colored('┘', CYAN)}\n")


def sep():
    sys.stdout.write(f"{colored('├', CYAN)}{colored('─' * WI, CYAN)}{colored('┤', CYAN)}\n")


# ═══════════════════════════════════════════════
# Panel 1: Token 趋势
# ═══════════════════════════════════════════════

def collect_token_trend():
    f = STATE / "token-tracking-index.json"
    if not f.exists():
        return {"status": STATUS_DEGRADED, "source": "token-tracking-index.json"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        usage = data.get("usage", 0)
        limit = data.get("limit", 200000)
        pct = round(usage * 100 / limit, 1) if limit > 0 else 0
        updated = data.get("last_updated", "unknown")
        return {"status": STATUS_OK, "usage": usage, "limit": limit, "pct": pct, "updated": updated}
    except (json.JSONDecodeError, KeyError):
        return {"status": STATUS_DEGRADED, "source": "token-tracking-index.json (解析失败)"}


def render_token_trend(data):
    section("Token 趋势")
    if data["status"] == STATUS_DEGRADED:
        degraded_msg(data.get("source", "unknown"))
        p(" RPE-003 修复后启用数据追踪")
        return
    b = bar(data["pct"], 20)
    pct_str = f"{data['pct']}%"
    usage_str = f"({data['usage']:,}/{data['limit']:,})"
    p(f" {b}  {pct_str} {usage_str}")
    p(f" 最后更新: {data['updated']}")


# ═══════════════════════════════════════════════
# Panel 2: Error DNA 状态
# ═══════════════════════════════════════════════

def collect_error_dna():
    """Read error-dna.jsonl for error type distribution; fallback to error-dna.json."""
    jsonl = STATE / "error-dna.jsonl"
    json_f = STATE / "error-dna.json"
    if not jsonl.exists() and not json_f.exists():
        return {"status": STATUS_DEGRADED, "source": "error-dna.jsonl / error-dna.json", "type_counts": {}}

    type_counts = defaultdict(int)
    total_count = 0
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                et = rec.get("error_type", "unknown")
                type_counts[et] += 1
                total_count += 1
            except json.JSONDecodeError:
                pass

    if not type_counts and json_f.exists():
        try:
            merged = json.loads(json_f.read_text(encoding="utf-8"))
            sigs = merged.get("error_signatures", {})
            for sig_data in sigs.values():
                total_count += sig_data.get("count", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    return {
        "status": STATUS_OK if type_counts or total_count > 0 else STATUS_DEGRADED,
        "type_counts": dict(type_counts),
        "total_errors": total_count,
        "source_degraded": not jsonl.exists() and json_f.exists(),
    }


def render_error_dna(data):
    section("Error DNA 状态")
    if data["status"] == STATUS_DEGRADED:
        degraded_msg("error-dna.jsonl / error-dna.json")
        p(" RPE-001 数据未就绪，执行 lx-rpe 后自动生成")
        return

    types = data.get("type_counts", {})
    total = data.get("total_errors", 0)

    if types:
        max_count = max(types.values())
        for et in sorted(types.items(), key=lambda x: (-x[1], x[0])):
            et_name, et_count = et
            b = bar_by_count(et_count, max_count, 20)
            p(f" {et_name:<12}{b} {et_count}")
    else:
        p(f" 总错误数: {total} (无分类数据)")


# ═══════════════════════════════════════════════
# Panel 3: Flywheel P0 事件
# ═══════════════════════════════════════════════

def collect_flywheel():
    if not FLYWHEEL_LOG.exists():
        return {"status": STATUS_DEGRADED, "source": "flywheel.log", "events": []}

    ack_resolved = set()
    ack_snoozed = {}
    if FLYWHEEL_ACK.exists():
        for line in FLYWHEEL_ACK.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                ack_date, ack_evt, action = parts[0], parts[1], parts[2]
                if action == "resolved":
                    ack_resolved.add(ack_evt)
                elif action.startswith("snooze"):
                    try:
                        days = int(action[6:])
                    except (ValueError, IndexError):
                        days = 7
                    snooze_until = datetime.now().strftime("%Y-%m-%d")
                    # Simplified: use ack_date + days
                    from datetime import timedelta
                    try:
                        sd = datetime.strptime(ack_date, "%Y-%m-%d") + timedelta(days=days)
                        snooze_until = sd.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
                    ack_snoozed[ack_evt] = snooze_until

    today = datetime.now().strftime("%Y-%m-%d")
    events = []
    for line in FLYWHEEL_LOG.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        evt_date = parts[0]
        evt_name = parts[1].strip()
        evt_sev = parts[2].strip() if len(parts) > 2 else ""
        evt_proj = parts[3].strip() if len(parts) > 3 else ""

        # Only P0 events
        if evt_sev != "P0":
            continue
        if evt_name in ack_resolved:
            continue
        if evt_name in ack_snoozed and today <= ack_snoozed[evt_name]:
            continue
        events.append((evt_date, evt_name, evt_proj))

    events.sort(key=lambda x: x[0], reverse=True)
    events = events[:5]

    return {"status": STATUS_OK if events else STATUS_OK, "events": events}


def render_flywheel(data):
    section("Flywheel P0 事件")
    if data["status"] == STATUS_DEGRADED and not data.get("events"):
        degraded_msg("flywheel.log")
        return
    events = data.get("events", [])
    if not events:
        empty_msg("无 P0 事件记录")
        return
    for evt_date, evt_name, evt_proj in events:
        desc = f" {evt_date}  {colored(evt_name, BOLD)}"
        if evt_proj:
            desc += f" ({evt_proj})"
        p(desc)


# ═══════════════════════════════════════════════
# Panel 4: Feature Registry
# ═══════════════════════════════════════════════

def collect_feature_registry():
    if not FEATURE_REGISTRY.exists():
        return {"status": STATUS_DEGRADED, "source": "feature-registry.yaml"}

    try:
        import yaml
        with open(FEATURE_REGISTRY) as f:
            data = yaml.safe_load(f)
    except Exception:
        return {"status": STATUS_DEGRADED, "source": "feature-registry.yaml (解析失败)"}

    hooks = data.get("hooks", [])
    skills = data.get("skills", [])

    hook_type_counts = defaultdict(int)
    for h in hooks:
        hook_type_counts[h.get("type", "unknown")] += 1

    return {
        "status": STATUS_OK,
        "hook_count": len(hooks),
        "skill_count": len(skills),
        "online_hooks": sum(1 for h in hooks if h.get("enabled_by_default", False)),
        "enabled_skills": sum(1 for s in skills if s.get("enabled_by_default", False)),
        "hook_types": dict(sorted(hook_type_counts.items())),
    }


def render_feature_registry(data):
    section("Feature Registry")
    if data["status"] == STATUS_DEGRADED:
        degraded_msg(data.get("source", "unknown"))
        return

    hc = data["hook_count"]
    sc = data["skill_count"]
    oh = data["online_hooks"]
    es = data["enabled_skills"]

    all_enabled = es == sc
    all_online = oh == hc

    skills_status = colored(f"{es}/{sc}", GREEN) if all_enabled else colored(f"{es}/{sc}", YELLOW)
    hooks_status = colored(f"{oh}/{hc}", GREEN) if all_online else colored(f"{oh}/{hc}", YELLOW)

    p(f" {hc} hooks {chr(183)} {sc} skills {chr(183)} {skills_status} 启用")
    p(f" Hook 健康检查: {hooks_status} 在线")


# ═══════════════════════════════════════════════
# Panel 5: 上下文
# ═══════════════════════════════════════════════

def collect_context():
    f = STATE / "token-tracking-index.json"
    if not f.exists():
        return {"status": STATUS_DEGRADED, "source": "token-tracking-index.json"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        usage = data.get("usage", 0)
        limit = data.get("limit", 200000)
        pct = round(usage * 100 / limit, 1) if limit > 0 else 0
        return {"status": STATUS_OK, "usage": usage, "limit": limit, "pct": pct}
    except (json.JSONDecodeError, KeyError):
        return {"status": STATUS_DEGRADED, "source": "token-tracking-index.json (解析失败)"}


def render_context(data):
    section("上下文")
    if data["status"] == STATUS_DEGRADED:
        degraded_msg(data.get("source", "unknown"))
        return
    b = bar(data["pct"], 20)
    p(f" 当前: {b}  {data['pct']}% ({data['usage']:,}/{data['limit']:,})")


# ═══════════════════════════════════════════════
# Main Dashboard
# ═══════════════════════════════════════════════

def render_dashboard(ts, ed, fw, fr, ctx):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    top()
    title(colored("Carror OS 健康面板", BOLD + CYAN))
    p(f" {now}")
    sep()

    render_token_trend(ts)
    sep()

    render_error_dna(ed)
    sep()

    render_flywheel(fw)
    sep()

    render_feature_registry(fr)
    sep()

    render_context(ctx)
    bottom()

    # Data source legend
    source_files = [
        ("token-tracking-index.json", (STATE / "token-tracking-index.json").exists()),
        ("error-dna.jsonl", (STATE / "error-dna.jsonl").exists()),
        ("flywheel.log", FLYWHEEL_LOG.exists()),
        ("feature-registry.yaml", FEATURE_REGISTRY.exists()),
        ("error-dna.json", (STATE / "error-dna.json").exists()),
    ]
    parts = []
    for name, exists in source_files:
        icon = colored("\u25cf", GREEN) if exists else colored("\u25cb", DIM)
        parts.append(f"{icon} {colored(name, CYAN if exists else DIM)}")
    sys.stdout.write("\n  " + "  ".join(parts) + "\n")


def collect_all():
    return (
        collect_token_trend(),
        collect_error_dna(),
        collect_flywheel(),
        collect_feature_registry(),
        collect_context(),
    )


def main():
    p = argparse.ArgumentParser(description="Carror OS 健康面板")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--watch", action="store_true", help="每 5 秒刷新")
    args = p.parse_args()

    if args.watch:
        try:
            while True:
                sys.stdout.write("\033[2J\033[H")
                ts, ed, fw, fr, ctx = collect_all()
                render_dashboard(ts, ed, fw, fr, ctx)
                print(colored("  \u23f3 Ctrl+C to exit | 5s refresh", DIM))
                time.sleep(5)
        except KeyboardInterrupt:
            print()
            return

    if args.json:
        ts, ed, fw, fr, ctx = collect_all()
        print(json.dumps(
            {"token_trend": ts, "error_dna": ed, "flywheel": fw,
             "feature_registry": fr, "context": ctx},
            ensure_ascii=False, indent=2,
        ))
        return

    ts, ed, fw, fr, ctx = collect_all()
    render_dashboard(ts, ed, fw, fr, ctx)


if __name__ == "__main__":
    main()
