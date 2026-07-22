#!/usr/bin/env python3

"""

skill_trace_report.py — 执行路径 + 错误路径 + Token 节省分析

合并三个数据源，生成完整执行画像：
 数据源1: .omc/state/skill-trace.jsonl ← update_progress.py 写入（路由路径）
 数据源2: .omc/state/error-dna.json ← error-dna.sh 写入（错误路径）
 数据源3: .omc/state/read-tracker.txt ← read-tracker.sh 写入（文件读取路径）

用法：
 python3 skill_trace_report.py                   # 完整报告
 python3 skill_trace_report.py --tokens-only      # 仅 token 节省分析
 python3 skill_trace_report.py --feature user-login  # 指定特性
 python3 skill_trace_report.py --last-n 10        # 最近 N 条追踪

exit: 0=成功, 1=无数据
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

STATE = Path(".omc/state")
SKILLS_ROOT = Path(".claude/skills")


# ── 数据源读取 ─────────────────────────────────────────────────

def load_trace(last_n: int = 0, feature: str = "") -> list:
    """读取 skill-trace.jsonl"""
    f = STATE / "skill-trace.jsonl"
    if not f.exists():
        return []
    records = []
    for line in f.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if feature and r.get("feature") != feature:
                continue
            records.append(r)
        except json.JSONDecodeError:
            pass
    return records[-last_n:] if last_n > 0 else records


def load_error_dna() -> list:
    """读取 error-dna.json"""
    f = STATE / "error-dna.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_read_tracker() -> list[str]:
    """读取 read-tracker.txt（被 AI 读过的文件列表）"""
    f = STATE / "read-tracker.txt"
    if not f.exists():
        return []
    return [l.strip() for l in f.read_text(encoding="utf-8").split("\n") if l.strip()]


# ── Token 节省分析 ─────────────────────────────────────────────

def count_tokens(path: Path) -> int:
    """估算文件 token 数（4 tokens/行）"""
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").split("\n")) * 4
    except Exception:
        return 0


def analyze_token_savings(read_files: list[str]) -> dict:
    """计算渐进式披露节省的 token 数"""
    # 实际读取的 references/ 文件
    actual_refs = [f for f in read_files if "/references/" in f and f.endswith(".md")]
    actual_tokens = sum(count_tokens(Path(f)) for f in actual_refs if Path(f).exists())

    # 所有 references/ 文件（如果全量加载的话）
    all_refs = list(SKILLS_ROOT.rglob("references/*.md"))
    max_tokens = sum(count_tokens(f) for f in all_refs)

    # SKILL.md 总量
    skill_tokens = sum(count_tokens(f) for f in SKILLS_ROOT.glob("*/SKILL.md"))

    return {
        "actual_refs_loaded": len(actual_refs),
        "total_refs_available": len(all_refs),
        "actual_ref_tokens": actual_tokens,
        "max_ref_tokens": max_tokens,
        "skill_md_tokens": skill_tokens,
        "saved_tokens": max(0, max_tokens - actual_tokens),
        "save_pct": round((max_tokens - actual_tokens) * 100 / max_tokens, 1) if max_tokens > 0 else 0,
        "cost_saved_usd": round((max_tokens - actual_tokens) * 3 / 1_000_000, 5),
        "actual_refs": [Path(f).name for f in actual_refs],
    }


# ── 执行路径分析 ───────────────────────────────────────────────

def build_execution_path(traces: list) -> dict:
    """从 skill-trace.jsonl 重建执行路径"""
    by_feature = defaultdict(list)
    for r in traces:
        key = f"[{r.get('skill', 'unknown')}] {r.get('feature', '?')}/{r.get('task', '?')}"
        by_feature[key].append(r)

    paths = {}
    for key, events in by_feature.items():
        path_steps = []
        errors = []
        for e in sorted(events, key=lambda x: x.get("ts", "")):
            step_label = ""
            if e.get("phase"):
                step_label += e["phase"]
            if e.get("step"):
                step_label += f"/Step{e['step']}"
            if e.get("branch"):
                step_label += f"({e['branch']})"

            entry = {
                "ts": e.get("ts", ""),
                "step": step_label or e.get("action", ""),
                "action": e.get("action", ""),
                "status": e.get("status", "success"),
            }
            path_steps.append(entry)
            if e.get("status") == "error":
                errors.append(entry)

        paths[key] = {"steps": path_steps, "errors": errors}
    return paths


def build_error_path(dna: list) -> list:
    """从 error-dna.json 提取错误路径"""
    errors = []
    for e in dna:
        if isinstance(e, dict):
            errors.append({
                "ts": e.get("last_seen", e.get("ts", "")),
                "command": e.get("command", "")[:60],
                "stderr_hint": e.get("stderr", "")[:80],
                "status": e.get("status", "active"),
                "hits": e.get("hits", 1),
            })
    return sorted(errors, key=lambda x: x.get("ts", ""), reverse=True)


# ── 报告输出 ───────────────────────────────────────────────────

def print_report(traces: list, dna: list, read_files: list, feature: str = ""):
    """打印完整画像报告"""
    print("═" * 60)
    print(f" Carror OS 执行路径分析报告")
    print(f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if feature:
        print(f" 过滤特性: {feature}")
    print("═" * 60)

    # ── 1. 执行路径 ──────────────────────────────────────────
    print("\n【1】执行路径追踪 (update_progress.py → skill-trace.jsonl)")
    if not traces:
        print(" (无数据，请先执行 lx-rpe 任务)")
    else:
        paths = build_execution_path(traces)
        for key, data in paths.items():
            steps = data["steps"]
            errs = data["errors"]
            print(f"\n ┌─ {key}")
            for s in steps:
                icon = "✅" if s["status"] == "success" else "❌"
                print(f" │ {icon} {s['ts'][11:16]} {s['step']} [{s['action']}]")
            if errs:
                print(f" │ ⚠️ 错误路径: {len(errs)} 处")
                for e in errs:
                    print(f" │ └─ {e['step']}")
            print(f" └─ 共 {len(steps)} 个节点, {len(errs)} 个错误")

    # ── 2. 错误路径 ──────────────────────────────────────────
    print("\n【2】错误路径追踪 (error-dna.sh → error-dna.json)")
    if not dna:
        print(" (无数据)")
    else:
        errors = build_error_path(dna)
        active = [e for e in errors if e["status"] != "fixed"]
        fixed = [e for e in errors if e["status"] == "fixed"]
        print(f" 活跃错误: {len(active)} | 已修复: {len(fixed)}")
        for e in active[:5]:
            print(f" ❌ [{e['ts'][:16]}] hits={e['hits']}")
            print(f" CMD: {e['command']}")
            if e["stderr_hint"]:
                print(f" ERR: {e['stderr_hint']}")

    # ── 3. 文件读取路径 ──────────────────────────────────────
    print("\n【3】文件读取路径 (read-tracker.sh → read-tracker.txt)")
    if not read_files:
        print(" (无数据)")
    else:
        skill_mds = [f for f in read_files if "SKILL.md" in f]
        refs = [f for f in read_files if "/references/" in f]
        others = [f for f in read_files if f not in skill_mds and f not in refs]
        print(f" SKILL.md 读取: {len(skill_mds)} 次")
        print(f" references 读取: {len(refs)} 个文件")
        if refs:
            for r in refs[:8]:
                print(f" · {Path(r).name}")
            if len(refs) > 8:
                print(f" · ...还有 {len(refs) - 8} 个")
        print(f" 其他文件读取: {len(others)} 次")

    # ── 4. Token 节省分析 ────────────────────────────────────
    print("\n【4】渐进式披露 Token 节省分析")
    ts = analyze_token_savings(read_files)
    print(f" 实际加载 references: {ts['actual_refs_loaded']}/{ts['total_refs_available']} 个")
    print(f" 实际消耗 tokens: {ts['actual_ref_tokens']:,}")
    print(f" 全量加载 tokens: {ts['max_ref_tokens']:,}")
    print(f" 节省 tokens: {ts['saved_tokens']:,} ({ts['save_pct']}%)")
    print(f" 折算成本节省: ${ts['cost_saved_usd']} (claude-sonnet $3/1M)")
    if ts["actual_refs"]:
        print(f" 触发的 references: {', '.join(ts['actual_refs'][:5])}")
        if len(ts["actual_refs"]) > 5:
            print(f" ...还有 {len(ts['actual_refs']) - 5} 个")

    print("\n" + "═" * 60)
    print(" 数据文件路径:")
    print(f" · 路由追踪: {STATE}/skill-trace.jsonl")
    print(f" · 错误追踪: {STATE}/error-dna.json")
    print(f" · 读取追踪: {STATE}/read-tracker.txt")
    print("═" * 60)


def main():
    p = argparse.ArgumentParser(description="执行路径 + 错误路径 + Token 节省分析")
    p.add_argument("--tokens-only", action="store_true", help="只输出 token 节省分析")
    p.add_argument("--feature", default="", help="过滤指定特性")
    p.add_argument("--last-n", type=int, default=0, help="只看最近 N 条追踪")
    args = p.parse_args()

    traces = load_trace(args.last_n, args.feature)
    dna = load_error_dna()
    read_files = load_read_tracker()

    if not traces and not dna and not read_files:
        print(" (无任何追踪数据，请先执行 lx-rpe 或其他 skill)")
        sys.exit(1)

    if args.tokens_only:
        ts = analyze_token_savings(read_files)
        print(json.dumps(ts, ensure_ascii=False, indent=2))
        return

    print_report(traces, dna, read_files, args.feature)


if __name__ == "__main__":
    main()
