#!/usr/bin/env python3
"""
RPE-002: Loading Benchmark
==========================
Measure token/line counts for the Carror OS progressive disclosure system.

This script evaluates Condition A (progressive disclosure / L1 only) vs
Condition B (full load / L1+L2+L3) and reports structured results.

Method: tiktoken cl100k_base encoding (Claude-compatible tokenizer).
Fallback: chars/4 estimate when tiktoken is unavailable.

Output: stdout (terminal) + .claude/state/benchmark-report.md (persistent).
Idempotent: safe to run multiple times.
"""

import os
import sys
import json
import pathlib
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CLAUDE_DIR = REPO_ROOT / ".claude"
NODES_DIR = CLAUDE_DIR / "nodes"
SKILLS_DIR = CLAUDE_DIR / "skills"
TASK_SYS_DIR = CLAUDE_DIR / "task_sys"
REPORT_PATH = CLAUDE_DIR / "state" / "benchmark-report.md"

# ---------------------------------------------------------------------------
# Layer definitions
# ---------------------------------------------------------------------------

# L1: Session startup files (always loaded)
# These are the files loaded at session start per AGENTS.md "核心执行上下文"
L1_PATHS = [
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "AGENTS.md",
    CLAUDE_DIR / "kernel.md",
    CLAUDE_DIR / "anti-patterns.md",
    CLAUDE_DIR / "claude-next.md",
]

# Files to exclude from scanning
EXCLUDE_FILES = {
    CLAUDE_DIR / "nodes" / "README.md",
}


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

_TOKENIZER = None


def _get_tokenizer():
    """Get tiktoken cl100k_base encoder, or None if unavailable."""
    global _TOKENIZER
    if _TOKENIZER is None:
        try:
            import tiktoken  # noqa
            _TOKENIZER = "tiktoken"
        except ImportError:
            _TOKENIZER = False  # sentinel for "import failed"
    return _TOKENIZER == "tiktoken"


def count_tokens(text: str):
    """
    Count tokens using tiktoken cl100k_base.
    Returns (token_count, method_label).
    """
    if _get_tokenizer():
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), "tiktoken cl100k_base"
    # Fallback: chars / 4 (rough estimate for English text)
    return max(1, len(text) // 4), "chars/4 estimate"


def count_lines(text: str) -> int:
    """Count total lines (including blank)."""
    lines = text.splitlines()
    return len(lines)


def count_nonempty_lines(text: str) -> int:
    """Count non-empty lines (for reference)."""
    return len([l for l in text.splitlines() if l.strip()])


def read_file_or_empty(path: pathlib.Path) -> str:
    """Read file contents, returning empty string on error."""
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return ""
    except (OSError, UnicodeDecodeError):
        return ""


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def discover_skill_skills() -> list[pathlib.Path]:
    """Discover all SKILL.md files under .claude/skills/."""
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def discover_skill_references() -> list[pathlib.Path]:
    """Discover all references/**/*.md under .claude/skills/."""
    return sorted(SKILLS_DIR.glob("*/references/**/*.md"))


def discover_node_files() -> list[pathlib.Path]:
    """Discover all .md files under .claude/nodes/, excluding README.md."""
    if not NODES_DIR.exists():
        return []
    files = []
    for f in sorted(NODES_DIR.iterdir()):
        if f.suffix == ".md" and f not in EXCLUDE_FILES:
            files.append(f)
    return files


def discover_task_sys_templates() -> list[pathlib.Path]:
    """Discover all template files under .claude/task_sys/templates/."""
    tmpl_dir = TASK_SYS_DIR / "templates"
    if not tmpl_dir.exists():
        return []
    return sorted(tmpl_dir.glob("*.md"))


def discover_on_demand_task_sys() -> list[pathlib.Path]:
    """Discover on-demand task_sys files not already in L1."""
    result = []
    for fname in [
        "context_guard.md",
        "mechanism_evals.md",
        "loading_matrix.md",
        "orchestrator.md",
        "unified_delivery_schema.md",
        "task_fs.md",
    ]:
        f = TASK_SYS_DIR / fname
        if f.exists() and f.is_file():
            result.append(f)
    return result


def scan_all_layers():
    """
    Scan the filesystem and classify files into layers.

    Returns:
        l1_files, l2_files, l3_files: each as list[tuple(path, rel_path)]
    """
    l1 = []
    l2 = []
    l3 = []

    # L1: session startup files
    l1_set = set()
    for path in L1_PATHS:
        if path.exists() and path.is_file():
            rel = str(path.relative_to(REPO_ROOT))
            l1.append((path, rel))
            l1_set.add(path)

    # L2: skill SKILL.md files
    for path in discover_skill_skills():
        if path not in l1_set:
            l2.append((path, str(path.relative_to(REPO_ROOT))))

    # L2: node system files (on-demand)
    for path in discover_node_files():
        if path not in l1_set:
            l2.append((path, str(path.relative_to(REPO_ROOT))))

    # L2: on-demand task_sys files
    for path in discover_on_demand_task_sys():
        if path not in l1_set:
            l2.append((path, str(path.relative_to(REPO_ROOT))))

    # L3: skill references
    for path in discover_skill_references():
        if path not in l1_set:
            l3.append((path, str(path.relative_to(REPO_ROOT))))

    # L3: task_sys templates
    for path in discover_task_sys_templates():
        if path not in l1_set:
            l3.append((path, str(path.relative_to(REPO_ROOT))))

    return l1, l2, l3


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def measure_files(file_list):
    """
    Measure a list of (path, rel_path) files.
    Returns list of dicts: {path, lines, nonempty, tokens, method}.
    """
    results = []
    for path, rel_path in file_list:
        text = read_file_or_empty(path)
        line_count = count_lines(text)
        nonempty_count = count_nonempty_lines(text)
        tok_count, method = count_tokens(text)
        results.append({
            "path": rel_path,
            "lines": line_count,
            "nonempty": nonempty_count,
            "tokens": tok_count,
            "method": method,
        })
    return results


def summarize(results):
    """Summarize a list of file measurements."""
    total_lines = sum(r["lines"] for r in results)
    total_nonempty = sum(r["nonempty"] for r in results)
    total_tokens = sum(r["tokens"] for r in results)
    file_count = len(results)
    return {
        "file_count": file_count,
        "total_lines": total_lines,
        "total_nonempty": total_nonempty,
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_table(rows, headers):
    """Format a list of dicts as a markdown table."""
    col_widths = {}
    for h in headers:
        col_widths[h] = len(str(h))
    for row in rows:
        for h in headers:
            val = str(row.get(h, ""))
            col_widths[h] = max(col_widths[h], len(val))

    sep = "|" + "|".join(" " + "-" * w + " " for w in [col_widths[h] for h in headers]) + "|"
    head = "|" + "|".join(" " + h.ljust(col_widths[h]) + " " for h in headers) + "|"

    lines = [head, sep]
    for row in rows:
        vals = []
        for h in headers:
            v = str(row.get(h, ""))
            vals.append(" " + v.ljust(col_widths[h]) + " ")
        lines.append("|" + "|".join(vals) + "|")
    return "\n".join(lines)


def generate_report(l1_meas, l2_meas, l3_meas):
    """Generate the full markdown report."""
    l1_sum = summarize(l1_meas)
    l2_sum = summarize(l2_meas)
    l3_sum = summarize(l3_meas)

    all_meas = l1_meas + l2_meas + l3_meas
    all_sum = summarize(all_meas)

    prog_tokens = l1_sum["total_tokens"]
    full_tokens = all_sum["total_tokens"]
    prog_lines = l1_sum["total_lines"]
    full_lines = all_sum["total_lines"]
    prog_nonempty = l1_sum["total_nonempty"]
    full_nonempty = all_sum["total_nonempty"]

    token_saving_pct = round((1 - prog_tokens / full_tokens) * 100, 1) if full_tokens > 0 else 0.0
    line_saving_pct = round((1 - prog_lines / full_lines) * 100, 1) if full_lines > 0 else 0.0
    nonempty_saving_pct = round((1 - prog_nonempty / full_nonempty) * 100, 1) if full_nonempty > 0 else 0.0

    # Verification of loading_matrix.md claim: compare both total-lines and nonempty
    matrix_claim_before = 394
    matrix_claim_after = 120
    actual_pct = round((1 - prog_lines / full_lines) * 100, 1) if full_lines > 0 else 0.0

    # Check against total lines (loading_matrix likely counts all lines)
    claim_verified_total = (
        abs(full_lines - matrix_claim_before) <= 50
        and abs(prog_lines - matrix_claim_after) <= 20
    )
    # Also check against nonempty lines
    claim_verified_nonempty = (
        abs(full_nonempty - matrix_claim_before) <= 50
        and abs(prog_nonempty - matrix_claim_after) <= 20
    )

    method_label = "tiktoken cl100k_base" if any(m["method"] == "tiktoken cl100k_base" for m in l1_meas) else "chars/4 estimate"

    report_lines = [
        "# Loading Benchmark Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Method:** {method_label}",
        f"**Repository:** `{REPO_ROOT}`",
        "",
        "---",
        "",
        "## 1. Method",
        "",
        "- **Token estimation:** Uses `tiktoken` with `cl100k_base` encoding (the same tokenizer",
        "  used by Claude models). This is an **estimate** -- actual LLM context usage depends on",
        "  the model's internal tokenization and system prompt overhead.",
        "- **Fallback:** If tiktoken is not installed, falls back to `chars // 4`, which is a",
        "  coarse estimate (~4 characters per token for English text). Fallback results are",
        "  labelled `[estimate: chars/4 fallback]`.",
        "- **Sample:** Single pass measurement of all `.md` files in `.claude/` + `CLAUDE.md` +",
        "  `AGENTS.md`. No repeated sampling (file contents are static).",
        "- **Limitations:**",
        "  1. Token counts are estimates, not exact LLM context measurements.",
        "  2. Does not account for system prompt size, conversation history, or tool definitions.",
        "  3. Single measurement -- no variance calculation (static content).",
        "  4. Only counts text content; binary/frontmatter parsing not applied.",
        "  5. Line counts are reported as total lines (including blanks) for comparison with",
        "     loading_matrix.md claims (which uses total lines). Non-empty line counts also included.",
        "",
        "---",
        "",
        "## 2. Layer Definitions",
        "",
        "| Layer | Contents | Load Strategy |",
        "|-------|----------|--------------|",
        "| **L1** | `CLAUDE.md`, `AGENTS.md`, `kernel.md`, `anti-patterns.md`, `claude-next.md` | Always loaded at session start |",
        "| **L2** | All `SKILL.md` files, node system files (`.claude/nodes/`), on-demand `task_sys/` files (orchestrator, context_guard, mechanism_evals, loading_matrix, etc.) | Loaded on-demand when entering a specific phase or triggering a skill |",
        "| **L3** | Skill reference docs (`.claude/skills/*/references/`), task template files (`.claude/task_sys/templates/`) | Precision-loaded when performing a specific operation |",
        "",
        "---",
        "",
        "## 3. Condition Comparison",
        "",
        "### Condition A: Progressive Disclosure (L1 only)",
        f"- Files: {l1_sum['file_count']}",
        f"- Total lines (incl. blanks): {l1_sum['total_lines']}",
        f"- Non-empty lines: {l1_sum['total_nonempty']}",
        f"- Total tokens: {l1_sum['total_tokens']:,}",
        "",
        "### Condition B: Full Load (L1 + L2 + L3)",
        f"- Files: {all_sum['file_count']}",
        f"- Total lines (incl. blanks): {all_sum['total_lines']}",
        f"- Non-empty lines: {all_sum['total_nonempty']}",
        f"- Total tokens: {all_sum['total_tokens']:,}",
        "",
        "### Savings",
        "| Metric | Progressive (A) | Full (B) | Reduction |",
        "|--------|----------------|----------|-----------|",
        f"| Lines (incl. blanks) | {prog_lines} | {full_lines} | {line_saving_pct}% |",
        f"| Non-empty lines | {prog_nonempty} | {full_nonempty} | {nonempty_saving_pct}% |",
        f"| Tokens | {prog_tokens:,} | {full_tokens:,} | {token_saving_pct}% |",
        "",
        "---",
        "",
        "## 4. Verification of loading_matrix.md Claims",
        "",
        "The loading matrix (`task_sys/loading_matrix.md`, line 89) claims:",
        "",
        "> \"首次加载从 394 行 → ~120 行，减少 70%。\"",
        "",
        "### Measured Results (total lines, including blanks)",
        "| Metric | Claimed | Measured |",
        "|--------|---------|----------|",
        f"| Full load (before) | ~394 lines | **{full_lines} lines** |",
        f"| Progressive (after) | ~120 lines | **{prog_lines} lines** |",
        f"| Reduction | ~70% | **{actual_pct}%** |",
        "",
        f"**Verdict (total lines):** {'PASS' if claim_verified_total else 'NOTE'} - "
        f"{'claim is consistent with measurements' if claim_verified_total else 'measured values differ from claimed values'}",
        "",
        "### Alternative: Non-empty lines",
        "| Metric | Claimed | Measured |",
        "|--------|---------|----------|",
        f"| Full load (before) | ~394 lines | **{full_nonempty} lines** |",
        f"| Progressive (after) | ~120 lines | **{prog_nonempty} lines** |",
        f"| Reduction | ~70% | **{nonempty_saving_pct}%** |",
        "",
        f"**Verdict (non-empty):** {'PASS' if claim_verified_nonempty else 'NOTE'} - "
        f"{'claim is consistent with measurements' if claim_verified_nonempty else 'measured values differ from claimed values'}",
        "",
        "---",
        "",
        "## 5. Structure Report",
        "",
        "### L1 Files (always loaded)",
        format_table(l1_meas, ["path", "lines", "nonempty", "tokens", "method"]),
        "",
        "### L2 Files (on-demand)",
        format_table(l2_meas, ["path", "lines", "nonempty", "tokens", "method"]),
        "",
        "### L3 Files (precision-loaded)",
        format_table(l3_meas, ["path", "lines", "nonempty", "tokens", "method"]),
        "",
        "### Layer Summary",
        "| Layer | Files | Lines | Non-empty | Tokens |",
        "|-------|-------|-------|-----------|--------|",
        f"| L1 | {l1_sum['file_count']} | {l1_sum['total_lines']} | {l1_sum['total_nonempty']} | {l1_sum['total_tokens']:,} |",
        f"| L2 | {l2_sum['file_count']} | {l2_sum['total_lines']} | {l2_sum['total_nonempty']} | {l2_sum['total_tokens']:,} |",
        f"| L3 | {l3_sum['file_count']} | {l3_sum['total_lines']} | {l3_sum['total_nonempty']} | {l3_sum['total_tokens']:,} |",
        f"| **Total (A: progressive)** | **{l1_sum['file_count']}** | **{prog_lines}** | **{prog_nonempty}** | **{prog_tokens:,}** |",
        f"| **Total (B: full)** | **{all_sum['file_count']}** | **{full_lines}** | **{full_nonempty}** | **{full_tokens:,}** |",
        "",
        "---",
        "",
        "## 6. Limitations",
        "",
        f"1. **Token estimation method:** {method_label}",
        "2. **Single sample:** File contents are static, so repeated measurements would yield identical results.",
        "3. **LLM context overhead:** This benchmark counts only file content tokens, not the system prompt,",
        "   conversation history, or tool/function definitions that also consume context window.",
        "4. **Line counts:** Both total lines (including blanks) and non-empty lines are reported.",
        "   The loading_matrix.md claim likely uses total lines.",
        "5. **File coverage:** Only scans `.claude/` governance/skill files.",
        "   External dependencies are not included.",
        "",
        "---",
        "",
        "## 7. Raw Data",
        "",
        "```json",
        json.dumps({
            "timestamp": datetime.now().isoformat(),
            "method_hint": "tiktoken cl100k_base" if method_label == "tiktoken cl100k_base" else "chars/4 fallback",
            "condition_a": {
                "label": "Progressive (L1 only)",
                "files": l1_sum["file_count"],
                "lines": l1_sum["total_lines"],
                "nonempty": l1_sum["total_nonempty"],
                "tokens": l1_sum["total_tokens"],
            },
            "condition_b": {
                "label": "Full load (L1+L2+L3)",
                "files": all_sum["file_count"],
                "lines": all_sum["total_lines"],
                "nonempty": all_sum["total_nonempty"],
                "tokens": all_sum["total_tokens"],
            },
            "layer_summary": {
                "L1": l1_sum,
                "L2": l2_sum,
                "L3": l3_sum,
            },
            "claim_verification": {
                "claim": "首次加载从 394 行 → ~120 行，减少 70%",
                "measured_full_lines": full_lines,
                "measured_progressive_lines": prog_lines,
                "measured_full_nonempty": full_nonempty,
                "measured_progressive_nonempty": prog_nonempty,
                "measured_reduction_pct_total_lines": actual_pct,
                "measured_reduction_pct_nonempty": nonempty_saving_pct,
                "verdict_total_lines": "consistent" if claim_verified_total else "differs",
                "verdict_nonempty": "consistent" if claim_verified_nonempty else "differs",
            },
            "file_details": all_meas,
        }, indent=2, ensure_ascii=False),
        "```",
        "",
        "---",
        "*Report auto-generated by `.claude/scripts/loading_benchmark.py`. Re-run to refresh.*",
        "",
    ]

    return "\n".join(report_lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import time
    start = time.time()

    print("=" * 68, file=sys.stderr)
    print("  RPE-002: Loading Benchmark", file=sys.stderr)
    print("  Measuring progressive disclosure token savings", file=sys.stderr)
    print("=" * 68, file=sys.stderr)
    print(file=sys.stderr)

    # Check tiktoken availability
    if _get_tokenizer():
        print("  Tokenizer: tiktoken cl100k_base (available)", file=sys.stderr)
    else:
        print("  Tokenizer: tiktoken NOT available, using chars/4 fallback", file=sys.stderr)
    print(file=sys.stderr)

    # Scan and measure
    print("  Scanning files...", file=sys.stderr)
    l1_files, l2_files, l3_files = scan_all_layers()
    print(f"  L1: {len(l1_files)} files, L2: {len(l2_files)} files, L3: {len(l3_files)} files", file=sys.stderr)

    print("  Measuring tokens...", file=sys.stderr)
    l1_meas = measure_files(l1_files)
    l2_meas = measure_files(l2_files)
    l3_meas = measure_files(l3_files)

    elapsed = time.time() - start
    report = generate_report(l1_meas, l2_meas, l3_meas)

    # Print report to stdout
    print(report)

    # Write report to file
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n  Report written to: {REPORT_PATH}", file=sys.stderr)

    # Quick summary to stderr
    l1_sum = summarize(l1_meas)
    all_sum = summarize(l1_meas + l2_meas + l3_meas)
    pct = round((1 - l1_sum['total_tokens'] / all_sum['total_tokens']) * 100, 1) if all_sum['total_tokens'] > 0 else 0
    print(f"\n  Summary:", file=sys.stderr)
    print(f"    Progressive (L1):   {l1_sum['total_lines']} lines, {l1_sum['total_tokens']:,} tokens", file=sys.stderr)
    print(f"    Full (L1+L2+L3):    {all_sum['total_lines']} lines, {all_sum['total_tokens']:,} tokens", file=sys.stderr)
    print(f"    Token reduction:    {pct}%", file=sys.stderr)
    print(f"    Elapsed:           {elapsed:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
