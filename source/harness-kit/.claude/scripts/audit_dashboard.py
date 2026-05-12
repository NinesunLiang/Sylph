#!/usr/bin/env python3
"""
audit_dashboard.py — Audit 统一仪表盘 v1.0

聚合 5 个审计数据源:
  [1] read-tracker.txt          — AI 文件读取追踪
  [2] session-turns.json        — 会话轮次计数
  [3] token-tracking-index.json — Token 使用追踪
  [4] error-dna.json / jsonl    — 错误记忆库
  [5] session-snapshot.json     — 会话快照 (SHA256 防篡改)

输出:
  python3 .claude/scripts/audit_dashboard.py        # Markdown 报告
  python3 .claude/scripts/audit_dashboard.py --json # JSON 输出
  python3 .claude/scripts/audit_dashboard.py --summary # 一行摘要

状态: ok / degraded (数据损坏或校验失败) / missing (文件不存在)
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Paths ──
STATE = Path(".omc/state")

# ── Colors ──
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── Status constants ──
STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_MISSING = "missing"

# ── Box rendering ──
WI = 50


def colored(text, color):
    return f"{color}{text}{RESET}"


def visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


def p(text=""):
    """Print a single line within the box."""
    vlen = visible_len(text)
    pad = max(0, WI - vlen)
    sys.stdout.write(f"{colored('│', CYAN)}{text}{' ' * pad}{colored('│', CYAN)}\n")


def title(text):
    """Print a centered title."""
    vlen = visible_len(text)
    left = max(0, (WI - vlen) // 2)
    p(" " * left + text)


def top():
    sys.stdout.write(f"{colored('┌', CYAN)}{colored('─' * WI, CYAN)}{colored('┐', CYAN)}\n")


def bottom():
    sys.stdout.write(f"{colored('└', CYAN)}{colored('─' * WI, CYAN)}{colored('┘', CYAN)}\n")


def sep():
    sys.stdout.write(f"{colored('├', CYAN)}{colored('─' * WI, CYAN)}{colored('┤', CYAN)}\n")


# ── Status badge helpers ──

def status_badge(status):
    if status == STATUS_OK:
        return colored("ok", GREEN)
    elif status == STATUS_DEGRADED:
        return colored("degraded", RED)
    else:
        return colored("missing", YELLOW)


def source_line(name, status, detail=""):
    badge = status_badge(status)
    prefix = " " + colored("\u25b6", CYAN if status == STATUS_OK else DIM)
    text = f"{prefix} {name:<30} {badge}"
    if detail:
        text += f"  {detail}"
    p(text)


def detail_line(text):
    p("   " + colored(text, DIM))


# ═══════════════════════════════════════════════
# Data Source 1: read-tracker.txt
# ═══════════════════════════════════════════════

def collect_read_tracker():
    """读取 AI 文件读取追踪记录."""
    f = STATE / "read-tracker.txt"
    if not f.exists():
        return {"status": STATUS_MISSING, "source": "read-tracker.txt", "files": [], "count": 0}

    try:
        files = [l.strip() for l in f.read_text(encoding="utf-8").split("\n") if l.strip()]
        # Categorize files
        skill_mds = [x for x in files if "SKILL.md" in x]
        refs = [x for x in files if "/references/" in x]
        others = [x for x in files if x not in skill_mds and x not in refs]
        return {
            "status": STATUS_OK,
            "source": "read-tracker.txt",
            "files": files,
            "count": len(files),
            "skill_md_count": len(skill_mds),
            "ref_count": len(refs),
            "other_count": len(others),
        }
    except Exception as e:
        return {"status": STATUS_DEGRADED, "source": "read-tracker.txt", "error": str(e), "files": [], "count": 0}


# ═══════════════════════════════════════════════
# Data Source 2: session-turns.json
# ═══════════════════════════════════════════════

def collect_session_turns():
    """读取会话轮次计数."""
    f = STATE / "session-turns.json"
    if not f.exists():
        return {"status": STATUS_MISSING, "source": "session-turns.json"}

    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        count = data.get("count", 0)
        updated = data.get("updated", "unknown")
        return {"status": STATUS_OK, "source": "session-turns.json", "count": count, "updated": updated}
    except (json.JSONDecodeError, Exception) as e:
        return {"status": STATUS_DEGRADED, "source": "session-turns.json", "error": str(e)}


# ═══════════════════════════════════════════════
# Data Source 3: token-tracking-index.json
# ═══════════════════════════════════════════════

def collect_token_tracking():
    """读取 Token 使用追踪."""
    f = STATE / "token-tracking-index.json"
    if not f.exists():
        return {"status": STATUS_MISSING, "source": "token-tracking-index.json"}

    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        usage = data.get("usage", 0)
        limit = data.get("limit", 200000)
        pct = round(usage * 100 / limit, 1) if limit > 0 else 0
        updated = data.get("last_updated", "unknown")
        return {
            "status": STATUS_OK,
            "source": "token-tracking-index.json",
            "usage": usage,
            "limit": limit,
            "pct": pct,
            "updated": updated,
        }
    except (json.JSONDecodeError, Exception) as e:
        return {"status": STATUS_DEGRADED, "source": "token-tracking-index.json", "error": str(e)}


# ═══════════════════════════════════════════════
# Data Source 4: error-dna.json / error-dna.jsonl
# ═══════════════════════════════════════════════

def collect_error_dna():
    """读取错误记忆库."""
    jsonl = STATE / "error-dna.jsonl"
    json_f = STATE / "error-dna.json"

    if not jsonl.exists() and not json_f.exists():
        return {"status": STATUS_MISSING, "source": "error-dna.jsonl / error-dna.json"}

    type_counts = defaultdict(int)
    total_count = 0
    format_used = "none"

    if jsonl.exists():
        format_used = "jsonl"
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
        format_used = "json"
        try:
            merged = json.loads(json_f.read_text(encoding="utf-8"))
            sigs = merged.get("error_signatures", {})
            total_count = sum(s.get("count", 0) for s in sigs.values())
        except (json.JSONDecodeError, Exception):
            return {"status": STATUS_DEGRADED, "source": "error-dna.json (解析失败)"}

    status = STATUS_OK if (type_counts or total_count > 0) else STATUS_DEGRADED
    return {
        "status": status,
        "source": f"error-dna.{format_used}" if format_used != "none" else "error-dna.*",
        "type_counts": dict(type_counts),
        "total_errors": total_count,
        "format": format_used,
    }


# ═══════════════════════════════════════════════
# Data Source 5: session-snapshot.json (SHA256)
# ═══════════════════════════════════════════════

def compute_sha256(filepath):
    """Compute SHA256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def collect_session_snapshot():
    """读取会话快照并验证 SHA256."""
    f = STATE / "session-snapshot.json"
    sha_file = STATE / "session-snapshot.json.sha256"

    if not f.exists():
        return {"status": STATUS_MISSING, "source": "session-snapshot.json"}

    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        snapshot = {
            "status": STATUS_OK,
            "source": "session-snapshot.json",
            "timestamp": data.get("timestamp", "unknown"),
            "turns": data.get("turns", 0),
            "branch": data.get("branch", "unknown"),
            "modified_count": len(data.get("modified_files", [])),
            "staged_count": len(data.get("staged_files", [])),
        }

        # SHA256 完整性校验
        if sha_file.exists():
            stored_hash = sha_file.read_text(encoding="utf-8").strip()
            actual_hash = compute_sha256(f)
            if stored_hash == actual_hash:
                snapshot["sha256"] = "verified"
            else:
                snapshot["status"] = STATUS_DEGRADED
                snapshot["sha256"] = "mismatch"
                snapshot["sha256_stored"] = stored_hash[:16] + "..."
                snapshot["sha256_actual"] = actual_hash[:16] + "..."
        else:
            snapshot["sha256"] = "unverified"

        return snapshot

    except (json.JSONDecodeError, Exception) as e:
        return {"status": STATUS_DEGRADED, "source": "session-snapshot.json", "error": str(e)}


# ═══════════════════════════════════════════════
# Collect All
# ═══════════════════════════════════════════════

def collect_all():
    return {
        "read_tracker": collect_read_tracker(),
        "session_turns": collect_session_turns(),
        "token_tracking": collect_token_tracking(),
        "error_dna": collect_error_dna(),
        "session_snapshot": collect_session_snapshot(),
    }


def compute_overall_status(results):
    """Compute overall status from all sources."""
    ok_count = sum(1 for r in results.values() if r["status"] == STATUS_OK)
    degraded_count = sum(1 for r in results.values() if r["status"] == STATUS_DEGRADED)
    missing_count = sum(1 for r in results.values() if r["status"] == STATUS_MISSING)
    total = len(results)

    if degraded_count > 0 or missing_count > 0:
        overall = STATUS_DEGRADED
    else:
        overall = STATUS_OK

    return {
        "overall": overall,
        "ok": ok_count,
        "degraded": degraded_count,
        "missing": missing_count,
        "total": total,
    }


# ═══════════════════════════════════════════════
# Render: Markdown (with box borders)
# ═══════════════════════════════════════════════

def render_markdown(results):
    overall = compute_overall_status(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    top()
    title(colored("Audit 统一仪表盘", BOLD + CYAN))
    p(f" {now}")
    p(f" 整体状态: {status_badge(overall['overall'])}  ({overall['ok']}/{overall['total']} ok, {overall['degraded']} degraded, {overall['missing']} missing)")
    sep()

    # 1. read-tracker.txt
    rt = results["read_tracker"]
    source_line("read-tracker.txt", rt["status"])
    if rt["status"] == STATUS_OK:
        detail_line(f"{rt['count']} files tracked (SKILL.md: {rt['skill_md_count']}, refs: {rt['ref_count']}, other: {rt['other_count']})")
    elif rt["status"] == STATUS_DEGRADED:
        detail_line(f"解析失败: {rt.get('error', 'unknown')}")
    else:
        detail_line("数据源缺失, 运行 read-tracker.sh 后生成")

    # 2. session-turns.json
    st = results["session_turns"]
    source_line("session-turns.json", st["status"])
    if st["status"] == STATUS_OK:
        detail_line(f"{st['count']} turns, last updated: {st['updated']}")
    elif st["status"] == STATUS_DEGRADED:
        detail_line(f"解析失败: {st.get('error', 'unknown')}")
    else:
        detail_line("数据源缺失, 运行 turn-counter.sh 后生成")

    # 3. token-tracking-index.json
    tt = results["token_tracking"]
    source_line("token-tracking-index.json", tt["status"])
    if tt["status"] == STATUS_OK:
        detail_line(f"{tt['pct']}% ({tt['usage']:,}/{tt['limit']:,}), last updated: {tt['updated']}")
    elif tt["status"] == STATUS_DEGRADED:
        detail_line(f"解析失败: {tt.get('error', 'unknown')}")
    else:
        detail_line("数据源缺失, 运行 token_writer.sh 后生成")

    # 4. error-dna.{json,jsonl}
    ed = results["error_dna"]
    source_line(f"error-dna.*", ed["status"])
    if ed["status"] == STATUS_OK:
        types_desc = ", ".join(f"{k}:{v}" for k, v in sorted(ed.get("type_counts", {}).items(), key=lambda x: -x[1])[:3])
        detail_line(f"{ed['total_errors']} errors total (format: {ed['format']}), top types: {types_desc}")
    elif ed["status"] == STATUS_DEGRADED:
        detail_line(f"解析失败或为空: {ed.get('source', 'unknown')}")
    else:
        detail_line("数据源缺失, 运行 error-dna.sh 后生成")

    # 5. session-snapshot.json (SHA256)
    ss = results["session_snapshot"]
    source_line("session-snapshot.json", ss["status"])
    if ss["status"] == STATUS_OK:
        sha_status = colored("SHA256 \u2713", GREEN) if ss.get("sha256") == "verified" else colored("SHA256 unverified", YELLOW)
        detail_line(f"branch: {ss['branch']}, turns: {ss['turns']}, modified: {ss['modified_count']}, staged: {ss['staged_count']}  {sha_status}")
    elif ss["status"] == STATUS_DEGRADED:
        sha_detail = ""
        if ss.get("sha256") == "mismatch":
            sha_detail = f" SHA256 mismatch! stored={ss.get('sha256_stored', '?')} actual={ss.get('sha256_actual', '?')}"
        detail_line(f"数据损坏: {ss.get('error', sha_detail or 'unknown')}")
    else:
        detail_line("数据源缺失, 运行 auto-snapshot.sh 后生成")

    bottom()


# ═══════════════════════════════════════════════
# Render: JSON
# ═══════════════════════════════════════════════

def render_json(results):
    overall = compute_overall_status(results)
    output = {
        "dashboard": "audit",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": overall,
        "sources": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════════════
# Render: Summary (one line)
# ═══════════════════════════════════════════════

def render_summary(results):
    """Output a single-line summary for integration (e.g., lx-status)."""
    overall = compute_overall_status(results)
    parts = [f"Audit: {overall['ok']}/{overall['total']} ok"]
    if overall["degraded"] > 0:
        parts.append(f"{overall['degraded']} degraded")
    if overall["missing"] > 0:
        parts.append(f"{overall['missing']} missing")

    badge = colored("\u2713", GREEN) if overall["overall"] == STATUS_OK else colored("\u26a0", RED)
    line = f" {badge} {', '.join(parts)}"

    # List which sources are not ok
    degraded_sources = []
    for name, r in results.items():
        if r["status"] != STATUS_OK:
            degraded_sources.append(r["source"])
    if degraded_sources:
        line += f"  ({', '.join(degraded_sources)})"

    p(line)


# ═══════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Audit 统一仪表盘")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--summary", action="store_true", help="一行摘要模式 (供 lx-status 集成)")
    args = parser.parse_args()

    results = collect_all()

    if args.json:
        render_json(results)
    elif args.summary:
        render_summary(results)
    else:
        render_markdown(results)

    # Exit code: 0 if all ok, 1 if any degraded/missing
    overall = compute_overall_status(results)
    sys.exit(0 if overall["overall"] == STATUS_OK else 1)


if __name__ == "__main__":
    main()
