#!/usr/bin/env python3
"""对 .claude/ 的存量机制资源做规则体检 —— 逐条规则过 Jev。

和 jev_sweep.py 的分工：
  jev_sweep  —— 判**一次改动**（commit / 任务交付）符不符合规则。
  claude_audit_jev —— 判**已经躺在仓库里的资源**该不该继续存在。

两者共用同一个 Jev 客户端与判定口径；判读不同（本工具用 jev_rules_audit.yaml）。

流程：
  1. 机械筛候选（没接线 / 只有 1 处接线的机制文件）
  2. 给每个候选补事实（谁调它、最后改动、在不在注册表里）
  3. 逐条规则问 Jev
  4. 出体检报告，标 建议删除 / 建议调整 / 保留

只读：不删任何文件，不改任何机制。删不删由人类看完报告决定。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import jev_sweep as js  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AUDIT_RULES = SCRIPTS / "jev_rules_audit.yaml"
MAIN_RULES = SCRIPTS / "jev_rules.yaml"

EXCLUDE_SEG = ("references/", "worktrees/", "archived/", "archive/")
TEXT_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".sh", ".ts", ".tsx", ".js", ".txt"}
MECH_EXT = {".py", ".sh"}

SUBJECT = "这个存量机制文件"

# 两次请求之间的间隔。背靠背连打会被丢连接（实测 19 次连打 12 次 URLError）。
REQUEST_GAP_S = 1.0


# ── 1. 机械筛候选 ──────────────────────────────────────────────────
def _tracked(prefix: str) -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z", prefix],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [p for p in out.split("\0") if p.strip()]


def _is_test(rel: str) -> bool:
    n = Path(rel).name
    return n.startswith("test_") or n.endswith("_test.py") or "/tests/" in rel


def _excluded(rel: str) -> bool:
    return any(s in rel for s in EXCLUDE_SEG)


def _patterns(rel: str) -> list[re.Pattern]:
    stem, name = re.escape(Path(rel).stem), re.escape(Path(rel).name)
    return [
        re.compile(rf"^\s*(from\s+[\w.]*\b{stem}\b\s+import|import\s+[\w.]*\b{stem}\b)", re.M),
        re.compile(rf"[\w/.\-]*{name}\b"),
        re.compile(rf"[\w/.\-]*\b{stem}\.py\b"),
    ]


def _last_commits(prefix: str) -> dict[str, str]:
    out = subprocess.run(
        ["git", "log", "--format=COMMIT %cI", "--name-only", "-z", "--", prefix],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    dates: dict[str, str] = {}
    cur = ""
    for tok in out.split("\0"):
        tok = tok.strip()
        if tok.startswith("COMMIT "):
            cur = tok[len("COMMIT "):]
        elif tok and tok not in dates:
            dates[tok] = cur
    return dates


def collect_candidates() -> tuple[list[dict], dict]:
    files = _tracked(".claude")
    idx: dict[str, str] = {}
    for rel in files:
        if _excluded(rel):
            continue
        p = ROOT / rel
        if p.suffix in TEXT_EXT and p.is_file():
            try:
                idx[rel] = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    dates = _last_commits(".claude")
    mech, tests = [], []
    for rel in files:
        p = ROOT / rel
        if _excluded(rel) or p.suffix not in MECH_EXT or not p.is_file():
            continue
        (tests if _is_test(rel) else mech).append(rel)

    out = []
    for rel in mech:
        pats = _patterns(rel)
        stem, name = Path(rel).stem, Path(rel).name
        callers = []
        for other, text in idx.items():
            if other == rel:
                continue
            # 先做一次廉价的子串预筛再来正则。
            # 实测：不做这步，118 个目标 × 400 份文本 × 3 条正则会跑 20 秒，
            # 而绝大多数文本里根本没出现过这个名字。
            if stem not in text and name not in text:
                continue
            if any(pat.search(text) for pat in pats):
                callers.append(other)
        out.append({
            "path": rel,
            "bytes": (ROOT / rel).stat().st_size,
            "callers": sorted(callers),
            "last_commit": dates.get(rel, "?"),
        })

    # 只把「可疑」的送去判：完全没接线，或只有 1 处接线（自产自销嫌疑）
    suspects = [c for c in out if len(c["callers"]) <= 1]
    stats = {
        "mech_total": len(mech),
        "test_total": len(tests),
        "suspects": len(suspects),
        "unwired": sum(1 for c in out if not c["callers"]),
    }
    return suspects, stats


# ── 2. 补事实 ──────────────────────────────────────────────────────
def _head_excerpt(rel: str, max_lines: int = 25) -> str:
    """取文件头几十行当「它在干什么」的证据。文档字符串通常在开头。"""
    try:
        lines = (ROOT / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return "（读不出来）"
    return "\n".join(lines[:max_lines])


_REPO_PATH_RE = re.compile(r"\.claude/[\w\-./]+\.[A-Za-z0-9]+")


def _dead_refs(rel: str) -> list[str]:
    """文件里点名、但仓库里已经不存在的 .claude/ 路径。

    「过时」这条判据最容易变成空话 —— 让 Jev 自己去找依赖是否存在是做不到的，
    必须由这里把实际检查结果喂给它。只认 .claude/ 开头的引用：
    这类引用没有歧义，别的写法（裸文件名、相对路径）误判率太高，宁可不报。
    """
    try:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    dead, seen = [], set()
    for m in _REPO_PATH_RE.findall(text):
        if m in seen:
            continue
        seen.add(m)
        if not (ROOT / m).exists():
            dead.append(m)
    return sorted(dead)[:15]


REGISTRIES = (
    ".claude/settings.json",
    ".claude/index.md",
    ".claude/hooks/index.md",
    ".claude/scripts/index.md",
    ".claude/skills/index.md",
    ".claude/workflows/index.md",
    ".claude/nodes/README.md",
)


def _registration(rel: str) -> str:
    """这个文件（或它所在的目录/工作流）有没有被注册表点名。

    为什么必须有这一条：实测踩过 —— ui_autopilot 下一个文件只被它兄弟文件调用，
    Jev 判「自产自销」。可它属于一个**在 index.md 里登记过的独立工作流**，
    整个子树是自洽的，根上有入口。缺了这条事实，整棵子树会被误判成僵尸。
    """
    def _text(reg: str) -> str:
        p = ROOT / reg
        if not p.is_file():
            return ""
        try:
            return p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    parts = Path(rel).parts
    lines: list[str] = []

    # ① 归属：workflows/<名字> 或 skills/<名字>。
    #    这类目录是**一个自洽单元**，根上有入口，内部文件互相调用是正常的。
    #    注册表里登记的是短名（`frontend-overnight/`），不是全路径，所以按名字查。
    if len(parts) >= 3 and parts[0] == ".claude" and parts[1] in ("workflows", "skills"):
        own = parts[2]
        idx = f".claude/{parts[1]}/index.md"
        text = _text(idx) + _text(".claude/index.md")
        if own in text:
            lines.append(
                f"  - 它属于 {parts[1][:-1]}「{own}」，该单元在 {idx} 里有登记 —— "
                f"这个单元的根上有入口，内部文件互相调用属于单元内正常分工"
            )
        else:
            lines.append(f"  - 它属于 {parts[1][:-1]}「{own}」，但注册表里查不到这个单元")

    # ② 文件自己有没有被点名
    if rel in _text(".claude/settings.json"):
        lines.append("  - settings.json 直接点名了这个文件（是注册的 hook）")
    for reg in REGISTRIES:
        if rel in _text(reg):
            lines.append(f"  - {reg} 直接点名了这个文件")
            break

    return "\n".join(lines) if lines else "（注册表没有提到它，也不属于任何已登记的工作流/技能）"


def build_facts(cand: dict) -> str:
    """把事实整理成 repo_context —— Jev 只负责判，事实由这里喂。

    教训：判据写得再好，喂进去的是空泛描述，结果就是一片「证据不足」。
    每条判据都得有对应的、检查过的事实。缺事实的判据等于没写。
    """
    callers = cand["callers"]
    if not callers:
        caller_txt = "（没有任何文件 import 它、调用它，也没有任何注册表点名它）"
    else:
        caller_txt = "\n".join(f"  - {c}" for c in callers)

    dead = _dead_refs(cand["path"])
    if dead:
        dead_txt = "\n".join(f"  - {d}（不存在）" for d in dead)
    else:
        dead_txt = "（无 —— 它点名的 .claude/ 路径都还在）"

    return (
        f"### 待体检资源\n"
        f"路径: {cand['path']}\n"
        f"大小: {cand['bytes']} 字节\n"
        f"最后改动: {cand['last_commit'][:10]}\n"
        f"调用方数量: {len(callers)}\n"
        f"调用方清单:\n{caller_txt}\n\n"
        f"### 注册表登记情况（实际检查过：这个文件或它的祖先目录有没有被点名）\n"
        f"{_registration(cand['path'])}\n\n"
        f"### 失效引用（实际检查过：这些 .claude/ 路径在仓库里已不存在）\n"
        f"{dead_txt}\n\n"
        f"### 文件开头（用于判断它是干什么的）\n"
        f"```\n{_head_excerpt(cand['path'])}\n```\n"
    )


# ── 3. 合并判读 ────────────────────────────────────────────────────
def merged_rules() -> list[dict]:
    """主表给哲学原文与阈值，体检表负责判读。

    体检表条目有两种：
      1. rule_id 与主表一致 → 只覆盖 criteria，原文/来源/阈值仍以主表为真源
      2. rule_id 主表没有   → **必须**带 derives_from 指明派生自哪条 CarrorOS 规则。
         凭空发明的规则，Jev 判得再对也没有治理意义，所以这里直接拒绝。
    """
    main = {r["rule_id"]: r for r in js.load_registry(MAIN_RULES).get("rules", [])}
    audit = js.load_registry(AUDIT_RULES)

    picked: list[dict] = []
    problems: list[str] = []
    for ar in audit.get("rules", []):
        rid = ar.get("rule_id")
        if not rid:
            problems.append("有条目缺 rule_id")
            continue

        if rid in main:
            merged = dict(main[rid])
            merged["criteria_true"] = ar["criteria_true"]
            merged["criteria_false"] = ar["criteria_false"]
            picked.append(merged)
            continue

        derives = ar.get("derives_from")
        if not derives:
            problems.append(f"{rid}: 主表没有它，又没写 derives_from —— 不许凭空发明规则")
            continue
        if derives not in main:
            problems.append(f"{rid}: derives_from={derives} 在主表里不存在")
            continue
        base = dict(main[derives])
        base.update(ar)
        base["derived_from_rule"] = derives
        picked.append(base)

    if problems:
        raise SystemExit("ERROR: 体检规则表有问题:\n  " + "\n  ".join(problems))
    if not picked:
        raise SystemExit("ERROR: 体检表没产出任何规则，检查 rule_id 是否对得上")
    return picked


# ── 4. 判定 ────────────────────────────────────────────────────────
def judge_one(cand: dict, rules: list[dict], client, model: str, samples: int) -> dict:
    facts = build_facts(cand)
    state = {
        "purpose": f"体检存量机制资源：{cand['path']}",
        "change_kind": "repo_audit",
        "change": f"（本次不是判改动，是判这个已经存在于仓库里的资源：{cand['path']}）",
        "delivery": {"available": False, "reason": "存量体检不涉及交付物"},
        "repo_context": facts,
        "repo_context_available": True,
    }
    questions = js.build_questions(rules, SUBJECT)

    # 多次采样时复用 sweep 里已经测过的聚合逻辑，不在这里手搓一份。
    raw_list, meta = [], {}
    for _ in range(max(1, samples)):
        raw = client.judge(state, questions, model)
        meta = raw
        if isinstance(raw, dict) and "answers" in raw:
            raw_list.append(raw)
    answers = js._aggregate_answers(raw_list) if raw_list else {}
    if not answers:
        meta = meta or {}
        err = (meta.get("_error") or meta.get("_http_error") or "未知")
        if meta.get("_detail"):
            err = f"{err} —— {meta['_detail']}"
        return {"path": cand["path"], "verdicts": {}, "error": str(err),
                "callers": cand["callers"], "facts": facts}

    verdicts = {}
    for rule in rules:
        rid = rule["rule_id"]
        ans = answers.get(rid)
        if not isinstance(ans, dict):
            verdicts[rid] = {"verdict": js.VERDICT_UNAVAILABLE, "reason": "answers 缺项"}
            continue
        if ans.get("type") == "noul":
            v = js.verdict_from_noul(
                ans.get("noul"),
                float(rule.get("accept_at", 0.85)),
                float(rule.get("reject_at", 0.30)),
            )
            verdicts[rid] = {"verdict": v, "noul": ans.get("noul")}
        else:
            v = js.verdict_from_choice(ans.get("choice"), ans.get("confidence"),
                                       float(rule.get("confidence_at", 0.55)))
            verdicts[rid] = {"verdict": v, "choice": ans.get("choice"),
                             "confidence": ans.get("confidence")}
    return {"path": cand["path"], "verdicts": verdicts, "error": None,
            "callers": cand["callers"], "facts": facts}


def suggest(row: dict) -> str:
    """把三条规则的结论压成一个动作建议。只给建议，不动手。"""
    vs = row.get("verdicts") or {}
    vals = [v.get("verdict") for v in vs.values()]
    if not vals or row.get("error"):
        return "待定（本次没拿到结论）"
    if js.VERDICT_BAD in vals:
        n = vals.count(js.VERDICT_BAD)
        return f"建议删除或重写（{n} 条规则判不符合）"
    if js.VERDICT_UNDECIDED in vals or js.VERDICT_INSUFFICIENT in vals:
        return "需人工复核（规则拿不准，可能是判据本身要调）"
    if vals.count(js.VERDICT_OK) == len(vals):
        return "保留"
    return "待定"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=".claude/ 存量机制资源规则体检（只读）")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--model", default=js.MODEL_FROZEN)
    ap.add_argument("--out", default=str(ROOT / ".omc" / "state" / "jev" / "claude-audit"))
    ap.add_argument("--dry-run", action="store_true", help="只列候选，不调 Jev")
    args = ap.parse_args(argv)

    cands, stats = collect_candidates()
    rules = merged_rules()

    print(f"机制文件 {stats['mech_total']} 个（测试 {stats['test_total']} 个另计）")
    print(f"可疑候选 {stats['suspects']} 个（0 接线 {stats['unwired']}）")
    print(f"体检规则 {len(rules)} 条: {[r['rule_id'] for r in rules]}")
    print()

    if args.dry_run:
        for c in cands:
            print(f"  {len(c['callers'])} 接线  {c['bytes']:>7,}B  {c['path']}")
        return 0

    client = js.JevClient()
    if not client.api_key:
        print("ERROR: 没读到 OPENROUTER_API_KEY —— 体检需要它。", file=sys.stderr)
        print("请先运行: python3 .omc/scripts/jev_set_api_key.py", file=sys.stderr)
        return 2

    rows = []
    for i, c in enumerate(cands, 1):
        print(f"[{i}/{len(cands)}] {c['path']} …", flush=True)
        rows.append(judge_one(c, rules, client, args.model, args.samples))
        # 背靠背连打会被丢连接。实测：19 次连打 12 次 URLError，
        # 每次隔 1 秒则是 19/19 成功。间隔不是可选的。
        if i < len(cands):
            time.sleep(REQUEST_GAP_S)

    report = {
        "schema_version": "carros.claude_audit.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "stats": stats,
        "rules_used": [r["rule_id"] for r in rules],
        "rows": rows,
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 体检结果 ===")
    for row in sorted(rows, key=lambda r: (suggest(r) != "保留", r["path"])):
        print(f"\n{row['path']}  （{len(row['callers'])} 处接线）")
        print(f"  建议: {suggest(row)}")
        for rid, v in (row.get("verdicts") or {}).items():
            sig = v.get("noul") or v.get("confidence")
            print(f"    {rid:22s} {v['verdict']}"
                  + (f"  (信号 {sig})" if sig is not None else ""))
        if row.get("error"):
            print(f"    ⚠️ 拿不到答案: {row['error']}")

    print(f"\n明细: {(out_dir / 'audit.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
