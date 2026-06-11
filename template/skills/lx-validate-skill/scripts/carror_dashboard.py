#!/usr/bin/env python3
"""
carror_dashboard.py — Carror OS 健康面板 v3.0

4 面板:
  [1] Token 节省       —— token-tracking-index.json
  [2] 任务通过率        —— error-dna.jsonl
  [3] 拦截的错误        —— ~/.claude/flywheel.log
  [4] 升华的知识点      —— claude-next.md + kernel.md

用法:
  python3 carror_dashboard.py        # 标准面板
  python3 carror_dashboard.py --json # JSON 输出
  python3 carror_dashboard.py --watch# 每 5 秒刷新
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ──
STATE = Path(".omc/state")
HOME = Path.home()
FLYWHEEL_LOG = HOME / ".claude" / "flywheel.log"
FLYWHEEL_ACK = HOME / ".claude" / "flywheel-ack.log"
CLAUDE_DIR = Path(".claude")
CLAUDE_NEXT = CLAUDE_DIR / "claude-next.md"
KERNEL_MD = CLAUDE_DIR / "kernel.md"

# ── 荧光蓝色系（终端渲染） ──
FLUO_BLUE = "\033[38;5;45m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
COLOR = FLUO_BLUE

# ── Panel width —— inner (excludes side borders) ──
WI = 72

# ── Status constants ──
STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"


def colored(text, color):
    return f"{color}{text}{RESET}"


def visible_len(text):
    import unicodedata
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text)
    width = 0
    for ch in cleaned:
        if unicodedata.east_asian_width(ch) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width


def bar(value, width=20):
    """Draw a horizontal bar chart element (value: 0-100) in blue."""
    if value <= 0:
        return colored("░" * width, DIM)
    filled = min(int(round(value * width / 100)), width)
    empty = width - filled
    return colored("█" * filled, COLOR) + colored("░" * empty, DIM)


def bar_by_count(value, max_value, width=20):
    if max_value <= 0:
        return colored("░" * width, DIM)
    pct = value * 100 / max_value
    return bar(pct, width)


# ── Box rendering ──

def p(text=""):
    vlen = visible_len(text)
    pad = max(0, WI - vlen)
    sys.stdout.write(f"{colored('│', COLOR)}{text}{' ' * pad}{colored('│', COLOR)}\n")


def title(text):
    vlen = visible_len(text)
    left = max(0, (WI - vlen) // 2)
    p(" " * left + text)


def section(name):
    p(" " + colored(name, BOLD + COLOR))
    p()


def degraded_msg(source):
    p(" " + colored(f"[degraded] {source} ", DIM) + colored("数据源不可用", DIM))


def empty_msg(msg):
    p(" " + colored(msg, DIM))


def top():
    sys.stdout.write(f"{colored('┌', COLOR)}{colored('─' * WI, COLOR)}{colored('┐', COLOR)}\n")


def bottom():
    sys.stdout.write(f"{colored('└', COLOR)}{colored('─' * WI, COLOR)}{colored('┘', COLOR)}\n")


def sep():
    sys.stdout.write(f"{colored('├', COLOR)}{colored('─' * WI, COLOR)}{colored('┤', COLOR)}\n")


# ═══════════════════════════════════════════════
# Panel 1: Token 节省
# ═══════════════════════════════════════════════

# 所有 Token 数据均来自 transcript 解析 (token-tracking-real.json)
# 无硬编码估算值 — 真实的才是宝贵的


def collect_token_savings():
    """
    使用 transcript 解析的真实 token 数据。
    数据源优先级：token-tracking-real.json (平台真实) > token-savings.json (compact) > 合成计数器

    context_used = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
    """
    # === 真实数据（源：transcript 解析） ===
    real_f = STATE / "token-tracking-real.json"
    context_used = None
    peak = None
    baseline = None
    real_total_input = None
    real_total_output = None
    real_total_cache = None
    turns = None
    session_id = None
    r = None
    context_limit = None
    if real_f.exists():
        try:
            r = json.loads(real_f.read_text(encoding="utf-8"))
            context_used = r.get("current_context")
            peak = r.get("peak_context")
            baseline = r.get("session_start_cost")
            real_total_input = r.get("total_input_tokens")
            real_total_output = r.get("total_output_tokens")
            real_total_cache = r.get("total_cache_read_tokens")
            turns = r.get("total_turns")
            session_id = r.get("session_id")
            context_limit = r.get("context_limit", None)
        except json.JSONDecodeError:
            pass

    # 自动检测模型上下文限制（优先: 模型名[1m]后缀 > settings.json）
    def _detect_model_limit():
        try:
            # 优先读项目级 settings，全局 settings 兜底
            proj_settings = STATE.parent.parent / ".claude" / "settings.json"
            settings_path = proj_settings if proj_settings.exists() else Path.home().joinpath(".claude/settings.json")
            settings = json.loads(settings_path.read_text())
            model = settings.get("env", {}).get("ANTHROPIC_MODEL", "")
            m = re.search(r"\[(\d+)([km])\]", model)
            if m:
                n = int(m.group(1))
                unit = m.group(2)
                return n * 1000 if unit == "k" else n * 1000000
        except: pass
        return None

    _model_limit = _detect_model_limit()
    if context_limit is None or context_limit == 200000:
        if _model_limit and _model_limit != 200000:
            context_limit = _model_limit

    # === 合成计数器（兜底） ===
    syn_f = STATE / "token-tracking-index.json"
    synthetic_usage = None
    limit = 200000
    if syn_f.exists():
        try:
            s = json.loads(syn_f.read_text(encoding="utf-8"))
            synthetic_usage = s.get("usage", 0)
            limit = s.get("limit", 200000)
            # auto-correct hardcoded 200000
            if limit == 200000 and _model_limit and _model_limit != 200000:
                limit = _model_limit
        except (json.JSONDecodeError, KeyError):
            pass

    # === 脱水节省 — 来自转录本实测 ===
    compact_saved = 0
    compact_events = 0
    if real_f.exists() and r is not None:
        compact_events = r.get("compact_events", 0)
        compact_saved = r.get("compact_savings", 0)
    # Fallback: token-savings.json (旧格式 + DG-103 新格式)
    if compact_events == 0:
        sv_f = STATE / "token-savings.json"
        if sv_f.exists():
            try:
                sv = json.loads(sv_f.read_text(encoding="utf-8"))
                # DG-103 新格式优先 (cumulative_events / session_ratio_pct)
                compact_events = sv.get("cumulative_events", 0)
                if compact_events == 0:
                    compact_events = sv.get("compact_events", 0)
                compact_saved = sv.get("cumulative_bytes", 0)
                if compact_saved == 0:
                    compact_saved = sv.get("compact", 0)
            except json.JSONDecodeError:
                pass

    # 缓存命中率 & 回合均耗
    cache_rate = None
    per_turn_avg = None
    if real_f.exists() and r is not None:
        total_ctx = r.get("total_context_used", 0)
        if total_ctx > 0:
            cache_read = r.get("total_cache_read_tokens", 0)
            cache_rate = round(cache_read * 100 / total_ctx, 1)
            tu = r.get("total_turns", 0)
            if tu > 0:
                per_turn_avg = round(total_ctx / tu)

    # context_limit: corrected variable (auto-detected from model) > real data > synthetic > hardcoded
    if context_limit is not None and context_limit > 0 and context_limit != 200000:
        effective_limit = context_limit
    elif real_f.exists() and r is not None and r.get("context_limit"):
        effective_limit = r["context_limit"]
    else:
        effective_limit = limit

    return {
        "status": STATUS_OK,
        "context_used": context_used,
        "peak": peak,
        "baseline": baseline,
        "limit": effective_limit,
        "synthetic_usage": synthetic_usage,
        "real_total_input": real_total_input,
        "real_total_output": real_total_output,
        "real_total_cache": real_total_cache,
        "turns": turns,
        "session_id": session_id,
        "compact": compact_saved,
        "compact_events": compact_events,
        "cache_rate": cache_rate,
        "per_turn_avg": per_turn_avg,
    }


def render_token_savings(data):
    section("Token 节省")
    if data["status"] == STATUS_DEGRADED:
        degraded_msg("token-tracking-real.json 和 token-tracking-index.json 均缺失")
        return

    context_used = data["context_used"]
    peak = data["peak"]
    baseline = data["baseline"]
    limit = data["limit"]
    syn = data["synthetic_usage"]
    compact = data["compact"]
    comp_ev = data["compact_events"]
    cache_rate = data.get("cache_rate")
    per_turn_avg = data.get("per_turn_avg")

    # === 全部来自 transcript 实测 ===
    p(" " + colored("[实测] Token 消耗", BOLD + COLOR))
    if context_used is not None:
        pct = round(context_used * 100 / limit, 1)
        b = bar(pct, 20)
        p(f" Context  {b}  {pct}%  ({context_used:,}/{limit:,})")
        parts = []
        if peak is not None:
            parts.append(f"峰值: {colored(f'{peak:,}', COLOR)} tok")
        if baseline is not None:
            parts.append(f"基线: {colored(f'{baseline:,}', COLOR)} tok")
        if per_turn_avg is not None:
            parts.append(f"回合均耗: {colored(f'{per_turn_avg:,}', COLOR)} tok/轮")
        if parts:
            p("  " + "  |  ".join(parts))
        if cache_rate is not None:
            p(f" 缓存命中率: {colored(f'{cache_rate}%', COLOR)}")
    else:
        # Fallback to synthetic
        if syn is not None:
            pct = round(syn * 100 / limit, 1)
            b = bar(pct, 20)
            p(f" Context  {b}  {pct}%  ({syn:,}/{limit:,})  [合成计数器]")
        else:
            p(" " + colored("Context: 数据不可用", DIM))

    p()
    if comp_ev > 0:
        # DG-103: 读取输入压缩率
        comp_ratio = 0
        sv_f = STATE / "token-savings.json"
        if sv_f.exists():
            try:
                sv = json.loads(sv_f.read_text(encoding="utf-8"))
                comp_ratio = sv.get("session_ratio_pct", 0)
            except: pass
        ratio_str = f" ({colored(f'{comp_ratio}%', COLOR)} 输入压缩)" if comp_ratio > 0 else ""
        p(f" 因脱水节省: {colored(f'{compact:,}', COLOR)} tok  ({colored(f'{comp_ev} 次', COLOR)})")
    else:
        p(f" 因脱水节省: {colored('0 tok', DIM)}")

    # Summary line
    ti = data.get("real_total_input")
    to = data.get("real_total_output")
    tc = data.get("real_total_cache")
    tu = data.get("turns")
    if ti is not None:
        p()
        p(f" 会话累计: 输入 {colored(f'{ti:,}', COLOR)}  缓存 {colored(f'{tc:,}', COLOR)}  输出 {colored(f'{to:,}', COLOR)}  ({tu} 轮)")


# ═══════════════════════════════════════════════
# Panel 2: 任务通过率
# ═══════════════════════════════════════════════

def collect_pass_rate():
    """Error count from dna; total ops from error-dna.sh counter."""
    jsonl = STATE / "error-dna.jsonl"
    ops_f = STATE / "total-ops.txt"

    # Count errors
    err_count = 0
    type_counts = defaultdict(int)
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                et = rec.get("error_type", "unknown")
                type_counts[et] += 1
                err_count += 1
            except json.JSONDecodeError:
                pass

    # Read total ops from error-dna.sh counter
    total_ops = 0
    rate = None
    if ops_f.exists():
        try:
            total_ops = int(ops_f.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass

    if total_ops > 0 and err_count <= total_ops:
        rate = round((total_ops - err_count) * 100 / total_ops, 1)

    return {
        "status": STATUS_OK if err_count > 0 or total_ops > 0 else STATUS_DEGRADED,
        "pass_rate": rate,
        "total_ops": total_ops,
        "err_count": err_count,
        "type_counts": dict(type_counts),
    }


def render_pass_rate(data):
    section("任务通过率")
    if data["status"] == STATUS_DEGRADED or data["err_count"] == 0:
        p(" " + colored("暂无错误记录", DIM))
        return

    err_c = data["err_count"]
    rate = data["pass_rate"]
    total = data["total_ops"]

    if rate is not None:
        rate_color = COLOR if rate >= 80 else DIM
        b = bar(rate, 20)
        p(f" {b}  {colored(f'{rate}%', rate_color)}")
    else:
        p(f" {colored('▌估算 N/A', COLOR)} (需追踪总操作数)")

    p(f" 累计错误: {colored(str(err_c), COLOR)}")

    # Top error types
    types = data.get("type_counts", {})
    if types:
        top = sorted(types.items(), key=lambda x: -x[1])[:3]
        type_str = "  ".join(f"{n}×{c}" for n, c in top)
        p(f" 高频错误: {type_str}")


# ═══════════════════════════════════════════════
# Panel 3: 拦截的错误
# ═══════════════════════════════════════════════

def collect_blocked():
    """Count blocked/intercepted operations from flywheel P0 events."""
    if not FLYWHEEL_LOG.exists():
        return {"status": STATUS_DEGRADED, "source": "flywheel.log", "blocked_total": 0}

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
                    try:
                        sd = datetime.strptime(ack_date, "%Y-%m-%d") + timedelta(days=days)
                        snooze_until = sd.strftime("%Y-%m-%d")
                    except ValueError:
                        snooze_until = datetime.now().strftime("%Y-%m-%d")
                    ack_snoozed[ack_evt] = snooze_until

    today = datetime.now().strftime("%Y-%m-%d")
    type_counts = defaultdict(int)
    total_blocked = 0
    for line in FLYWHEEL_LOG.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        evt_name = parts[1].strip()
        evt_sev = parts[2].strip()
        if evt_sev != "P0":
            continue
        total_blocked += 1
        type_counts[evt_name] += 1

    active = 0
    for evt_name in type_counts:
        if evt_name in ack_resolved:
            continue
        if evt_name in ack_snoozed and today <= ack_snoozed[evt_name]:
            continue
        active += 1

    return {
        "status": STATUS_OK if total_blocked > 0 else STATUS_DEGRADED,
        "blocked_total": total_blocked,
        "active": active,
        "type_counts": dict(type_counts),
    }


def render_blocked(data):
    section("拦截的错误")
    if data["status"] == STATUS_DEGRADED or data["blocked_total"] == 0:
        degraded_msg("flywheel.log (无 P0 拦截记录)")
        return

    total = data["blocked_total"]
    active = data["active"]
    types = data.get("type_counts", {})

    # Total count with severity
    if active > 0:
        p(f" 累计拦截: {colored(str(total), COLOR + BOLD)}  待处理: {colored(str(active), COLOR)}")
    else:
        p(f" 累计拦截: {colored(str(total), COLOR + BOLD)}  (全部已确认)")

    # Top 3 types
    if types:
        sorted_types = sorted(types.items(), key=lambda x: -x[1])
        max_c = max(types.values())
        for name, count in sorted_types[:3]:
            readable = name.replace("_triggered", "").replace("_", " ")
            b = bar_by_count(count, max_c, 16)
            p(f" {readable:<14}{b} {count}")
        if len(sorted_types) > 3:
            others = sum(c for _, c in sorted_types[3:])
            p(f" 其他{len(sorted_types)-3}种{'.' * 22}{others}")


# ═══════════════════════════════════════════════
# Panel 4: 升华的知识点
# ═══════════════════════════════════════════════

def collect_knowledge():
    """Count claude-next entries vs kernel.md sections."""
    # Parse claude-next.md
    cn_entries = 0
    cn_hits_total = 0
    if CLAUDE_NEXT.exists():
        content = CLAUDE_NEXT.read_text(encoding="utf-8")
        # Count ### entries in 待验证规则 section
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("### [") or line.startswith("### "):
                cn_entries += 1
            m = re.search(r"hits:(\d+)", line)
            if m:
                cn_hits_total += int(m.group(1))

    # Count kernel.md sections with content (not placeholder)
    kernel_sections = 0
    kernel_filled = 0
    if KERNEL_MD.exists():
        content = KERNEL_MD.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                kernel_sections += 1
        # Sections that still have placeholder text
        placeholders = sum(1 for kw in ["手动填写", "请按项目", "未检测到", "(新项目"] if kw in content)
        kernel_filled = kernel_sections - placeholders

    promoted = 0
    candidates = 0
    # Check for "已升华" / "已升华到" entries in claude-next.md footer
    if CLAUDE_NEXT.exists():
        content = CLAUDE_NEXT.read_text(encoding="utf-8")
        promoted = len(re.findall(r"升华到|已升华|→\s*kernel\.md", content))

        # Detect promotion candidates: hits>=5 or age>=10 days
        sections = re.split(r'\n###\s+', content)
        today_dt = datetime.now()
        for section in sections[1:]:
            date_m = re.search(r'@(\d{4}-\d{2}-\d{2})', section)
            hits_m = re.search(r'hits:(\d+)', section)
            date_ok = date_m and (today_dt - datetime.strptime(date_m.group(1), '%Y-%m-%d')).days >= 10
            hits_ok = hits_m and int(hits_m.group(1)) >= 5
            if date_ok or hits_ok:
                candidates += 1

    return {
        "status": STATUS_OK if cn_entries > 0 else STATUS_DEGRADED,
        "cn_entries": cn_entries,
        "cn_hits": cn_hits_total,
        "candidates": candidates,
        "kernel_filled": kernel_filled,
        "kernel_total": kernel_sections,
        "promoted": promoted,
    }


def render_knowledge(data):
    section("升华的知识点")
    if data["status"] == STATUS_DEGRADED or data["cn_entries"] == 0:
        degraded_msg("claude-next.md (无记录)")
        return

    cn = data["cn_entries"]
    hits = data["cn_hits"]
    candidates = data.get("candidates", 0)
    k_filled = data["kernel_filled"]
    k_total = data["kernel_total"]
    promoted = data["promoted"]

    # Entry count
    p(f" 待升华知识: {colored(str(cn), BOLD)} 条  (累计 hits: {hits})")

    # Promotion candidates
    cand_color = COLOR
    p(f" 可升华候选: {colored(str(candidates), cand_color)} 条  (hits>=5 或 age>=10天)")

    # Kernel coverage bar
    if k_total > 0:
        k_pct = round(k_filled * 100 / k_total)
        b = bar(k_pct, 20)
        p(f" 内核填充率: {b}  {k_filled}/{k_total} ({k_pct}%)")

    # Promoted count
    if promoted > 0:
        p(f" 已升华: {colored(str(promoted), COLOR)} 条到 kernel.md")
    else:
        p(f" 已升华: {colored('0', COLOR)} 条  (hits≥5 或 age≥10天可升华)")


# ═══════════════════════════════════════════════
# Panel 5: Audit 摘要（内联，不依赖 audit_dashboard.py）
# ═══════════════════════════════════════════════

def collect_audit():
    """Check 5 audit data sources, return ok/degraded/missing counts."""
    sources = [
        ("token-tracking-index.json", STATE / "token-tracking-index.json"),
        ("error-dna.jsonl", STATE / "error-dna.jsonl"),
        ("flywheel.log", FLYWHEEL_LOG),
        ("claude-next.md", CLAUDE_NEXT),
        ("kernel.md", KERNEL_MD),
    ]
    ok_count = 0
    missing = []
    for name, path in sources:
        if path.exists():
            ok_count += 1
        else:
            missing.append(name)
    total = len(sources)
    return {"ok": ok_count, "total": total, "missing": missing}


def render_audit(data):
    ok_c = data["ok"]
    total = data["total"]
    missing = data["missing"]
    if missing:
        p(f" {colored('⚠', COLOR)} Audit: {ok_c}/{total} ok, {len(missing)} missing  ({', '.join(missing)})")
    else:
        p(f" {colored('✓', COLOR)} Audit: {ok_c}/{total} ok")


# ═══════════════════════════════════════════════
# Main Dashboard
# ═══════════════════════════════════════════════

def render_dashboard(ts, pr, bl, kn):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    top()
    title(colored("Carror OS 健康面板", BOLD + COLOR))
    p(f" {now}")
    sep()

    render_token_savings(ts)
    sep()

    render_pass_rate(pr)
    sep()

    render_blocked(bl)
    sep()

    render_knowledge(kn)
    sep()

    au = collect_audit()
    render_audit(au)
    bottom()

    # Data source legend
    source_files = [
        ("token-tracking-index.json", (STATE / "token-tracking-index.json").exists()),
        ("error-dna.jsonl", (STATE / "error-dna.jsonl").exists()),
        ("flywheel.log", FLYWHEEL_LOG.exists()),
        ("claude-next.md", CLAUDE_NEXT.exists()),
        ("kernel.md", KERNEL_MD.exists()),
    ]
    parts = []
    for name, exists in source_files:
        icon = colored("\u25cf", COLOR) if exists else colored("\u25cb", DIM)
        parts.append(f"{icon} {colored(name, COLOR if exists else DIM)}")
    sys.stdout.write("\n  " + "  ".join(parts) + "\n")


def collect_all():
    return (
        collect_token_savings(),
        collect_pass_rate(),
        collect_blocked(),
        collect_knowledge(),
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
                ts, pr, bl, kn = collect_all()
                render_dashboard(ts, pr, bl, kn)
                print(colored("  \u23f3 Ctrl+C to exit | 5s refresh", DIM))
                time.sleep(5)
        except KeyboardInterrupt:
            print()
            return

    if args.json:
        ts, pr, bl, kn = collect_all()
        print(json.dumps(
            {"token_savings": ts, "pass_rate": pr, "blocked": bl, "knowledge": kn},
            ensure_ascii=False, indent=2,
        ))
        return

    ts, pr, bl, kn = collect_all()
    render_dashboard(ts, pr, bl, kn)


if __name__ == "__main__":
    main()
