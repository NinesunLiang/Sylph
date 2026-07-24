#!/usr/bin/env python3
"""
test-scorecard.py — Validate CarrorOS scorecard structure.

Verifies:
  1. Expected row IDs (C1-C9, E1-E8, Governance 7, UX 7)
  2. Required column groups (baseline, self-assessment/当前, external/外评)
  3. scorer_version / created_at metadata markers
"""

import re
import sys
from pathlib import Path

SCORECARD = Path("improve_plan/CarrorOS_second_time/scorecard.md")

EXPECTED_ROWS = {
    "C": [f"C{i}" for i in range(1, 10)],         # C1–C9
    "E": [f"E{i}" for i in range(1, 9)],           # E1–E8
    "Governance": [
        "抗衰减防线",
        "AI 赋能全流程自动化",
        "学习笔记积累",
        "长期目标一致性",
        "功能标志分明",
        "内置安全与洞察",
        "Evaluation 评测框架",
    ],
    "UX": [
        "长期目标一致性",
        "用户心智负担减轻",
        "交互现代化",
        "用户掌控感",
        "ai 智能感",
        "行为可预测",
        "人机权限分明",
    ],
}

# Column groups to verify per section table.
COLUMN_PATTERNS = {
    "C": ["基线", "当前", "外评"],
    "E": ["基线", "当前", "外评"],
    "Governance": ["基线", "当前", "外评"],
    "UX": ["基线", "外评"],
}

# Markers in the scorecard are expressed in Chinese as blockquote metadata rows.
# "创建" corresponds to created_at, "基线 commit" corresponds to baseline version.
MARKER_PATTERNS = [re.compile(r">.*创建"), re.compile(r">.*基线 commit")]


def slug(row_id: str) -> str:
    """Return a short stable key for error messages."""
    return row_id.replace(" ", "_").replace("(", "").replace(")", "")


def main() -> int:
    if not SCORECARD.exists():
        print(f"FAIL: {SCORECARD} not found", file=sys.stderr)
        return 1

    text = SCORECARD.read_text(encoding="utf-8")
    lines = text.splitlines()

    errors: list[str] = []

    # ------------------------------------------------------------------
    # 1. Check that every expected row ID appears in a table row.
    # ------------------------------------------------------------------
    for group, rows in EXPECTED_ROWS.items():
        for row in rows:
            # Build a regex that matches the row ID at the start of a
            # markdown table row (after the leading pipe).
            if group in ("C", "E"):
                pattern = re.compile(r"^\|\s*" + re.escape(row) + r"\b")

            # Governance / UX: match the Chinese dimension name.
            else:
                pattern = re.compile(
                    r"^\|\s*" + re.escape(row).replace(r"\ ", r"\s*") + r"\s*\|"
                )

            if not any(pattern.match(ln) for ln in lines):
                errors.append(
                    f"MISSING_ROW  group={group}  row={row!r}  "
                    f"(expected in a table row starting with | {row})"
                )

    # ------------------------------------------------------------------
    # 2. Check column-group headers in each dimension's table.
    #    We search for a table header line (| --- | --- | …) preceded by
    #    a header row that contains the group's column names.
    # ------------------------------------------------------------------
    for section_label, cols in COLUMN_PATTERNS.items():
        found = False
        for i, ln in enumerate(lines[:-1]):
            separator = lines[i + 1] if i + 1 < len(lines) else ""
            if "|" not in ln or "|" not in separator:
                continue
            if not separator.strip().startswith("|"):
                continue
            # Check that every expected column name occurs in this header row.
            if all(c in ln for c in cols):
                found = True
                break

        if not found:
            errors.append(
                f"MISSING_COLUMNS  section={section_label}  "
                f"expected={cols}  "
                f"(no table header with all these column names found)"
            )

    # ------------------------------------------------------------------
    # 3. Check that metadata markers (created_at / baseline version) exist.
    #    The scorecard uses Chinese blockquote lines for these.
    # ------------------------------------------------------------------
    found_markers = []
    for pat in MARKER_PATTERNS:
        for ln in lines:
            if pat.match(ln):
                found_markers.append(pat.pattern)
                break
    if not found_markers:
        errors.append(
            f"MISSING_MARKERS  expected at least one of "
            + ", ".join(p.pattern for p in MARKER_PATTERNS)
            + " matching a line in the file"
        )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    if errors:
        print(f"FAIL  ({len(errors)} check(s) failed)", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"OK  scorecard={SCORECARD}  rows=24  sections=4  markers={found_markers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
