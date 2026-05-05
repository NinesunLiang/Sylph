#!/usr/bin/env python3

"""

carror_dashboard.py — Carror OS 健康面板

三大指标一屏显示：
 [A] 节省成本 ← 渐进式披露 Token 节省
 [B] 自愈力 ← 错误遭遇次数 / 成功修复数 / 自愈率
 [C] 执行效率 ← 任务完成数 / 阻断次数 / 恢复次数

用法：
 python3 carror_dashboard.py       # 完整面板
 python3 carror_dashboard.py --json  # JSON 格式输出
 python3 carror_dashboard.py --watch # 每 5 秒刷新

exit: 0=成功, 1=无数据
"""
import argparse, json, sys, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

STATE = Path(".omc/state")
SKILLS_ROOT = Path(".claude/skills")

# ── 颜色常量 ──────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"


def colored(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


# ── 数据读取 ───────────────────────────────────────────────────
def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return records


def load_read_tracker() -> list[str]:
    f = STATE / "read-tracker.txt"
    if not f.exists():
        return []
    return [l.strip() for l in f.read_text(encoding="utf-8").split("\n") if l.strip()]


# ── [A] Token 节省分析 ─────────────────────────────────────────
def count_tokens(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").split("\n")) * 4
    except Exception:
        return 0


def calc_token_savings(read_files: list[str]) -> dict:
    refs_loaded = [f for f in read_files if "/references/" in f and f.endswith(".md")]
    actual_ref_tokens = sum(count_tokens(Path(f)) for f in refs_loaded if Path(f).exists())
    all_refs = list(SKILLS_ROOT.rglob("references/*.md"))
    max_ref_tokens = sum(count_tokens(f) for f in all_refs)
    skill_tokens = sum(count_tokens(f) for f in SKILLS_ROOT.glob("*/SKILL.md"))
    saved = max(0, max_ref_tokens - actual_ref_tokens)
    pct = round(saved * 100 / max_ref_tokens, 1) if max_ref_tokens > 0 else 0

    # 累计节省：从 session-turns.json 读取轮次估算
    turns_file = STATE / "session-turns.json"
    sessions = 1
    try:
        d = json.loads(turns_file.read_text(encoding="utf-8"))
        sessions = max(1, d.get("count", 1) // 20)  # 估算：每20轮=1个session
    except Exception:
        pass
    cumulative_saved = saved * sessions

    return {
        "refs_loaded": len(refs_loaded),
        "refs_available": len(all_refs),
        "actual_ref_tokens": actual_ref_tokens,
        "max_ref_tokens": max_ref_tokens,
        "skill_tokens": skill_tokens,
        "saved_tokens": saved,
        "save_pct": pct,
        "cost_saved_usd": round(saved * 3 / 1_000_000, 5),
        "cumulative_saved_tokens": cumulative_saved,
        "cumulative_cost_usd": round(cumulative_saved * 3 / 1_000_000, 4),
    }


# ── [B] 自愈力分析 ────────────────────────────────────────────
def calc_resilience(dna: list, traces: list) -> dict:
    # 从 error-dna.json
    total_hits = sum(e.get("hits", 1) for e in dna if isinstance(e, dict))
    fixed_count = sum(1 for e in dna if isinstance(e, dict) and e.get("status") == "fixed")
    active_count = sum(1 for e in dna if isinstance(e, dict) and e.get("status") != "fixed")
    total_errors = fixed_count + active_count

    # 从 skill-trace.jsonl
    blocks = [t for t in traces if t.get("action") == "block"]
    unblocks = [t for t in traces if t.get("action") == "unblock"]

    # 每个 block 是否有对应的 unblock（按 feature+task 匹配）
    healed = 0
    stuck = 0
    for b in blocks:
        key = (b.get("feature"), b.get("task"))
        matching_unblocks = [
            u for u in unblocks
            if (u.get("feature"), u.get("task")) == key and u.get("ts", "") > b.get("ts", "")
        ]
        if matching_unblocks:
            healed += 1
        else:
            stuck += 1

    heal_rate = round(healed * 100 / len(blocks), 1) if blocks else 100.0

    # 自愈率（DNA 维度）
    dna_heal_rate = round(fixed_count * 100 / total_errors, 1) if total_errors > 0 else 100.0

    return {
        "total_error_hits": total_hits,
        "unique_errors": total_errors,
        "fixed_errors": fixed_count,
        "active_errors": active_count,
        "dna_heal_rate": dna_heal_rate,
        "trace_blocks": len(blocks),
        "trace_healed": healed,
        "trace_stuck": stuck,
        "trace_heal_rate": heal_rate,
    }


# ── [C] 执行效率分析 ──────────────────────────────────────────
def calc_efficiency(traces: list) -> dict:
    completes = [t for t in traces if t.get("action") == "complete"]
    starts = [t for t in traces if t.get("action") == "start"]
    blocks = [t for t in traces if t.get("action") == "block"]

    features = set(t.get("feature", "") for t in traces if t.get("feature"))
    tasks_done = set((t.get("feature"), t.get("task")) for t in completes)

    # 分支分布
    branches = defaultdict(int)
    for t in traces:
        b = t.get("branch", "")
        if b:
            branches[b] += 1

    # Phase 分布
    phases = defaultdict(int)
    for t in traces:
        p = t.get("phase", "")
        if p:
            phases[p] += 1

    return {
        "features": len(features),
        "tasks_completed": len(tasks_done),
        "total_starts": len(starts),
        "total_blocks": len(blocks),
        "branch_dist": dict(branches),
        "phase_dist": dict(phases),
    }


# ── 面板渲染 ──────────────────────────────────────────────────
def bar(value: float, width: int = 20, color: str = GREEN) -> str:
    filled = int(value / 100 * width)
    empty = width - filled
    return colored("█" * filled, color) + colored("░" * empty, DIM)


def render_dashboard(ts: dict, res: dict, eff: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    w = 62

    print()
    print(colored("╔" + "═" * w + "╗", CYAN))
    print(colored("║", CYAN) + colored(f" Carror OS 健康面板", BOLD + CYAN) + " " * (w - 20) + colored("║", CYAN))
    print(colored("║", CYAN) + f" {now}" + " " * (w - len(now) - 2) + colored("║", CYAN))
    print(colored("╠" + "═" * w + "╣", CYAN))

    # ── [A] Token 节省 ──────────────────────────────────────
    print(colored("║", CYAN) + colored(" [A] 渐进式披露 · Token 节省", BOLD + YELLOW) + " " * (w - 30) + colored("║", CYAN))
    print(colored("║", CYAN) + " " * w + colored("║", CYAN))

    saved_k = ts["saved_tokens"] // 1000
    pct = ts["save_pct"]
    cost = ts["cost_saved_usd"]
    cum_cost = ts["cumulative_cost_usd"]

    bar_color = GREEN if pct >= 50 else YELLOW
    print(colored("║", CYAN) + f" 本次节省 {bar(pct, 20, bar_color)} {pct}%" + " " * max(0, w - 43) + colored("║", CYAN))
    print(colored("║", CYAN) + f" tokens {colored(str(ts['saved_tokens']), GREEN)} / {ts['max_ref_tokens']:,} 可节省" + " " * max(0, w - 40) + colored("║", CYAN))
    print(colored("║", CYAN) + f" 本次成本 {colored(f'${cost}', GREEN)} 累计估算 {colored(f'${cum_cost}', GREEN)}" + " " * max(0, w - 35) + colored("║", CYAN))
    print(colored("║", CYAN) + f" references {colored(str(ts['refs_loaded']), CYAN)}/{ts['refs_available']} 个按需加载" + " " * max(0, w - 33) + colored("║", CYAN))

    print(colored("╠" + "─" * w + "╣", CYAN))

    # ── [B] 自愈力 ──────────────────────────────────────────
    print(colored("║", CYAN) + colored(" [B] 自愈力 · 错误处理能力", BOLD + MAGENTA) + " " * (w - 28) + colored("║", CYAN))
    print(colored("║", CYAN) + " " * w + colored("║", CYAN))

    dna_rate = res["dna_heal_rate"]
    trace_rate = res["trace_heal_rate"]
    heal_color = GREEN if dna_rate >= 80 else (YELLOW if dna_rate >= 50 else RED)

    print(colored("║", CYAN) + f" 错误遭遇 {colored(str(res['total_error_hits']), RED)} 次" + f" 唯一错误 {colored(str(res['unique_errors']), YELLOW)} 种" + " " * max(0, w - 38) + colored("║", CYAN))
    print(colored("║", CYAN) + f" 成功修复 {colored(str(res['fixed_errors']), GREEN)} 个" + f" 未解决 {colored(str(res['active_errors']), RED)} 个" + " " * max(0, w - 34) + colored("║", CYAN))
    print(colored("║", CYAN) + f" DNA 自愈率 {bar(dna_rate, 20, heal_color)} {dna_rate}%" + " " * max(0, w - 46) + colored("║", CYAN))

    if res["trace_blocks"] > 0:
        trate_color = GREEN if trace_rate >= 70 else (YELLOW if trace_rate >= 40 else RED)
        print(colored("║", CYAN) + f" 执行阻断 {colored(str(res['trace_blocks']), YELLOW)} 次" + f" 自愈恢复 {colored(str(res['trace_healed']), GREEN)} 次" + f" 卡住 {colored(str(res['trace_stuck']), RED)} 次" + " " * max(0, w - 44) + colored("║", CYAN))
        print(colored("║", CYAN) + f" 执行自愈率 {bar(trace_rate, 20, trate_color)} {trace_rate}%" + " " * max(0, w - 46) + colored("║", CYAN))

    print(colored("╠" + "─" * w + "╣", CYAN))

    # ── [C] 执行效率 ────────────────────────────────────────
    print(colored("║", CYAN) + colored(" [C] 执行效率 · 任务画像", BOLD + BLUE) + " " * (w - 25) + colored("║", CYAN))
    print(colored("║", CYAN) + " " * w + colored("║", CYAN))

    print(colored("║", CYAN) + f" 活跃特性 {colored(str(eff['features']), CYAN)} 个" + f" Task 完成 {colored(str(eff['tasks_completed']), GREEN)} 个" + " " * max(0, w - 37) + colored("║", CYAN))
    print(colored("║", CYAN) + f" 节点追踪 {colored(str(eff['total_starts']), CYAN)} 个" + f" 阻断事件 {colored(str(eff['total_blocks']), YELLOW)} 次" + " " * max(0, w - 37) + colored("║", CYAN))

    if eff["branch_dist"]:
        branch_str = " ".join(
            f"{colored(b, CYAN)}:{colored(str(n), RESET)}"
            for b, n in sorted(eff["branch_dist"].items(), key=lambda x: -x[1])
        )
        leftover = w - 13 - len(" ".join(f"{b}:{n}" for b, n in eff["branch_dist"].items()))
        print(colored("║", CYAN) + f" 执行分支 {branch_str}" + " " * max(0, leftover) + colored("║", CYAN))

    print(colored("╠" + "─" * w + "╣", CYAN))

    # ── 数据来源 ────────────────────────────────────────────
    print(colored("║", CYAN) + colored(" 数据来源", DIM) + " " * (w - 10) + colored("║", CYAN))
    sources = [
        ("skill-trace.jsonl", "执行路径"),
        ("error-dna.json", "错误路径"),
        ("read-tracker.txt", "读取追踪"),
    ]
    for fname, desc in sources:
        exists = (STATE / fname).exists()
        icon = colored("●", GREEN) if exists else colored("○", DIM)
        padding = w - len(fname) - len(desc) - 6
        print(colored("║", CYAN) + f" {icon} {colored(fname, CYAN if exists else DIM)} {colored(desc, DIM)}" + " " * max(0, padding) + colored("║", CYAN))

    print(colored("╚" + "═" * w + "╝", CYAN))
    print()


# ── 主程序 ────────────────────────────────────────────────────
def collect_data():
    traces = load_jsonl(STATE / "skill-trace.jsonl")
    dna = load_json(STATE / "error-dna.json", [])
    read_files = load_read_tracker()
    ts = calc_token_savings(read_files)
    res = calc_resilience(dna, traces)
    eff = calc_efficiency(traces)
    return ts, res, eff


def main():
    p = argparse.ArgumentParser(description="Carror OS 健康面板")
    p.add_argument("--json", action="store_true", help="JSON 格式输出")
    p.add_argument("--watch", action="store_true", help="每 5 秒刷新")
    args = p.parse_args()

    if args.watch:
        try:
            while True:
                print("\033[2J\033[H", end="")  # 清屏
                ts, res, eff = collect_data()
                render_dashboard(ts, res, eff)
                print(colored(" 按 Ctrl+C 退出", DIM))
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n")
            return

    ts, res, eff = collect_data()
    if not any([
        (STATE / "skill-trace.jsonl").exists(),
        (STATE / "error-dna.json").exists(),
        (STATE / "read-tracker.txt").exists(),
    ]):
        print(" (无数据，请先执行 lx-rpe 或其他 skill)")
        sys.exit(1)

    if args.json:
        print(json.dumps({"token_savings": ts, "resilience": res, "efficiency": eff}, ensure_ascii=False, indent=2))
        return

    render_dashboard(ts, res, eff)


if __name__ == "__main__":
    main()
