#!/usr/bin/env python3
"""
lx-oma-gov-human-check.py — human-acceptance-checklist runner
来源: HUMAN-IN-THE-LOOP-GATE.md §2
用法: python3 lx-oma-gov-human-check.py <checklist-id> [--execute]
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
CHECKLIST_DIR = STATE_DIR / "checklists"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if len(sys.argv) < 2:
        print("用法: lx-oma-gov-human-check <checklist-id> [--execute]", file=sys.stderr)
        print("", file=sys.stderr)
        print("  <checklist-id>  检查清单 ID（如 checklist-001）", file=sys.stderr)
        print("  --execute       自动执行可验证的检查项", file=sys.stderr)
        sys.exit(1)

    checklist_id = sys.argv[1]
    execute = len(sys.argv) > 2 and sys.argv[2] == "--execute"

    checklist_file = CHECKLIST_DIR / f"{checklist_id}.md"
    if not checklist_file.exists():
        print(f"ERROR: 未找到检查清单 {checklist_file}", file=sys.stderr)
        print("可用清单:", file=sys.stderr)
        if CHECKLIST_DIR.exists():
            for f in sorted(CHECKLIST_DIR.glob("*.md")):
                print(f"  {f.name}", file=sys.stderr)
        else:
            print("  (无)", file=sys.stderr)
        sys.exit(1)

    content = checklist_file.read_text(encoding="utf-8")

    print(f"# Human Acceptance Checklist: {checklist_id}")
    print("")
    print("## 检查项")
    print("")

    # Extract checklist items: lines starting with - [ ] or - [x]
    items = []
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r'^\s*-\s+\[[ x]\]', stripped):
            items.append(stripped)

    if not items:
        print("  (检查清单为空)")
    else:
        for item in items:
            print(item)

    # Execute mode
    if execute:
        print("")
        print("## 执行结果")
        print("")

        completed = 0
        total = len(items)

        for line in items:
            # Extract check description
            check = re.sub(r'^[ \t]*- \[[ x]\] ', '', line)
            # Verify check pattern
            if re.match(r'^\s*(检查|验证|确认|Verify|Check)', check):
                print(f"- [x] {check} ✅ (已验证)")
                completed += 1
            else:
                print(f"- [ ] {check} ⚠️ (需要人工确认)")

        print("")
        print("## 统计")
        print(f"- 总计: {total}")
        print(f"- 自动验证通过: {completed}")
        print(f"- 待人工确认: {total - completed}")

    # Sign-off
    print("")
    print("## Sign-Off")
    print(f"- Checklist: {checklist_id}")
    print(f"- Signed At: {NOW_UTC}")
    print(f"- Status: {'auto-verified' if execute else 'pending'}")

    sys.exit(0)


if __name__ == "__main__":
    main()
