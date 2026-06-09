#!/usr/bin/env python3
"""
knowledge-condenser.py — Stop — 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议

Role: 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
GS-003: 自动知识抽取 — 支持 [seed:*] 和 @YYYY-MM-DD 两种格式
"""

import json
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, hc_get, flywheel_event, output_continue,
    PROJECT_ROOT, STATE_DIR,
)


def main():
    if not hc_enabled("knowledge_condenser"):
        output_continue()
        return

    claude_next = PROJECT_ROOT / ".claude" / "claude-next.md"
    kernel_md = PROJECT_ROOT / ".claude" / "kernel.md"

    if not claude_next.exists():
        output_continue()
        return

    auto_execute = hc_get("sublimation.auto_execute", "true").lower() == "true"
    sublimation_log = STATE_DIR / "sublimation-log.jsonl"

    # Parse claude-next.md
    try:
        text = claude_next.read_text(encoding="utf-8")
    except OSError:
        output_continue()
        return

    lines = text.split("\n")
    entries = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # ### [seed:xxx] Description @YYYY-MM-DD hits:N
        m1 = re.match(r'^###\s+\[([^\]]+)\]\s+(.+?)(?:\s+@(\d{4}-\d{2}-\d{2}))?\s+hits:(\d+)', line_stripped)
        if m1:
            tag = m1.group(1)
            desc = m1.group(2).strip()
            hits = int(m1.group(4))
            d = m1.group(3)
            entry_date = datetime.strptime(d, "%Y-%m-%d").date() if d else None
            entries.append((tag, hits, entry_date, desc, i + 1))
            continue

        # ### Description @YYYY-MM-DD hits:N
        m2 = re.match(r'^###\s+(.+?)\s+@(\d{4}-\d{2}-\d{2})\s+hits:(\d+)', line_stripped)
        if m2:
            desc = m2.group(1).strip()
            hits = int(m2.group(3))
            d = m2.group(2)
            entry_date = datetime.strptime(d, "%Y-%m-%d").date()
            entries.append((desc[:50], hits, entry_date, desc, i + 1))
            continue

        # ### [rpe-NNN] Description @YYYY-MM-DD hits:N
        m3 = re.match(r'^###\s+\[([^\]]+)\]\s+@(\d{4}-\d{2}-\d{2})\s+hits:(\d+)', line_stripped)
        if m3:
            tag = m3.group(1)
            hits = int(m3.group(3))
            d = m3.group(2)
            entry_date = datetime.strptime(d, "%Y-%m-%d").date()
            entries.append((tag, hits, entry_date, "", i + 1))
            continue

    today = date.today()
    suggestions = []

    for tag, hits, entry_date, desc, ln in entries:
        if hits < 2:  # P1.3: threshold lowered from 3 to 2
            continue

        age = (today - entry_date).days if entry_date else 0

        # Check if already in kernel.md (keyword fuzzy search)
        found_in_kernel = False
        if tag and kernel_md.exists():
            try:
                kernel_content = kernel_md.read_text(encoding="utf-8")
                found_in_kernel = tag.lower() in kernel_content.lower()
            except OSError:
                pass

        if hits >= 5 and age >= 10 and found_in_kernel:
            action = "更新 kernel.md（规则已存在但需补证据）"
        elif hits >= 5 and age >= 10 and not found_in_kernel:
            action = "升华至 kernel.md"
        elif hits >= 3 and age >= 7 and found_in_kernel:
            action = "更新 kernel.md（修表述/补证据）"
        elif hits >= 3 and age >= 7 and not found_in_kernel:
            action = "升华至 kernel.md"
        elif hits >= 3 and age >= 5 and found_in_kernel:
            action = "更新 kernel.md（修表述/补证据）"
        elif hits >= 3 and age >= 5 and not found_in_kernel:
            action = "建议升华，待确认"
        elif hits >= 3 and age < 5:
            action = f"待稳定后再升华（仅 {age} 天）"
        else:
            continue

        tag_display = tag or desc[:50]
        suggestions.append((tag_display, hits, age, action, ln, found_in_kernel))

    if not suggestions:
        output_continue()
        return

    # Sort by hits desc, then age desc
    suggestions.sort(key=lambda x: (-x[1], -x[2]))
    suggestions = suggestions[:7]

    # Auto-sublimate
    auto_sublimated = []
    if auto_execute:
        for tag_display, hits, age, action, ln, found_in_kernel in suggestions:
            if action == "升华至 kernel.md" and hits >= 5 and age >= 10 and not found_in_kernel:
                # Find the entry block
                entry_lines = text.split("\n")
                entry_block = []
                capture = False
                for j, el in enumerate(entry_lines):
                    if j + 1 == ln:
                        capture = True
                    if capture:
                        entry_block.append(el)
                        if j + 1 > ln and el.strip().startswith("### "):
                            break
                if entry_block and entry_block[-1].strip().startswith("### "):
                    entry_block = entry_block[:-1]
                entry_text = "\n".join(entry_block).strip()

                # Append to kernel.md
                kernel_lines = []
                if kernel_md.exists():
                    kernel_lines = kernel_md.read_text(encoding="utf-8").split("\n")

                insertion = len(kernel_lines)
                for j in range(len(kernel_lines) - 1, -1, -1):
                    if kernel_lines[j].strip():
                        insertion = j + 1
                        break

                sublimation_block = (
                    f"\n## 自动升华: {tag_display}\n\n"
                    f"{entry_text}\n\n"
                    f"— 自动升华自 claude-next.md:{ln} (hits:{hits}, age:{age}天)\n"
                )
                kernel_lines.insert(insertion, sublimation_block)
                try:
                    kernel_md.write_text("\n".join(kernel_lines), encoding="utf-8")
                except OSError:
                    pass

                # Log the sublimation
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "claude-next.md",
                    "source_line": ln,
                    "tag": tag_display,
                    "hits": hits,
                    "age_days": age,
                    "target": str(kernel_md),
                    "action": "auto_sublimate",
                }
                try:
                    STATE_DIR.mkdir(parents=True, exist_ok=True)
                    with open(str(sublimation_log), "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except OSError:
                    pass
                auto_sublimated.append(tag_display)

    # Build output
    lines_out = [f"[knowledge-condenser] {len(suggestions)} 个高频模式可升华:"]
    for tag_display, hits, age, action, ln, found_in_kernel in suggestions:
        in_k = "found" if found_in_kernel else "missing"
        lines_out.append(f" · {tag_display} (hits:{hits}, {age}天) → {action}")
        lines_out.append(f"   证据: claude-next.md:{ln}, kernel.md: {in_k}")

    # Auto-archive: low-hit + old entries (hits=1, age>30 days)
    old_low_hit = [
        (ln, desc[:60]) for tag, hits, entry_date, desc, ln in entries
        if hits == 1 and entry_date and (today - entry_date).days > 30
    ]
    if old_low_hit:
        lines_out.append(f"[knowledge-condenser] {len(old_low_hit)} 条低命中超龄记录(hits=1, >30天):")
        for ln, d in old_low_hit[:5]:
            lines_out.append(f" · 行{ln}: {d}")
        lines_out.append("  建议: 审查后从 claude-next.md 移除或标记为已归档")

    # Total alert: >40 entries
    if len(entries) > 40:
        lines_out.append(
            f"[knowledge-condenser] 警告: claude-next.md 当前 {len(entries)} 条，"
            f"建议审查归档低价值条目至 <30 条"
        )

    if auto_sublimated:
        lines_out.append(
            f"[knowledge-condenser] 自动升华: {len(auto_sublimated)} 条已写入 kernel.md "
            f"— {', '.join(auto_sublimated)}"
        )

    output_text = "\n".join(lines_out)

    # Stop hook: write to file instead of stdout (to avoid JSON validation errors)
    report_file = STATE_DIR / "knowledge-condenser-report.txt"
    if output_text:
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            report_file.write_text(output_text, encoding="utf-8")
        except OSError:
            pass
        flywheel_event("knowledge_condenser", "sublimation_scan", "P2", "scanned_and_suggested")

    output_continue()


if __name__ == "__main__":
    main()
