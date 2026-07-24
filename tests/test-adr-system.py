#!/usr/bin/env python3
"""Test ADR index and file consistency."""

import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / ".claude" / "references" / "adr"
INDEX = ADR_DIR / "INDEX.md"

errors: list[str] = []


def check_index_exists() -> list[str]:
    """Check INDEX.md exists and has expected entries."""
    if not INDEX.exists():
        return ["FAIL: INDEX.md does not exist"]

    text = INDEX.read_text(encoding="utf-8").strip()
    if not text:
        return ["FAIL: INDEX.md is empty"]

    entries = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(\d{4})\s*\|", line)
        if m:
            entries.append(m.group(1))

    if not entries:
        return ["FAIL: INDEX.md has no ADR entries in table rows"]

    return [f"OK: INDEX.md has {len(entries)} entries: {', '.join(entries)}"]


def check_adr_files(entries: list[str]) -> list[str]:
    """Check each ADR listed in INDEX.md has a corresponding file."""
    results = []
    for entry in entries:
        # Find all .md files that start with this number
        matched = list(ADR_DIR.glob(f"{entry}-*.md"))
        if len(matched) == 0:
            results.append(f"FAIL: ADR {entry} has no corresponding file")
        elif len(matched) > 1:
            results.append(f"FAIL: ADR {entry} has multiple matching files: {matched}")
        else:
            results.append(f"OK: ADR {entry} -> {matched[0].name}")
    return results


def main() -> None:
    print("# ADR System Verification\n")

    # Step 1: INDEX.md exists and has entries
    idx_results = check_index_exists()
    for r in idx_results:
        print(r)
    print()

    # Parse entries from INDEX.md
    if not INDEX.exists():
        print("FATAL: Cannot proceed without INDEX.md", file=sys.stderr)
        sys.exit(1)

    text = INDEX.read_text("utf-8")
    entries = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(\d{4})\s*\|", line)
        if m:
            entries.append(m.group(1))

    if len(entries) < 5:
        errors.append(f"FAIL: ADR count ({len(entries)}) < 5")

    # Step 2: Each ADR has a corresponding file
    file_results = check_adr_files(entries)
    for r in file_results:
        print(r)
    print()

    # Step 3: Count all ADR .md files (exclude INDEX.md and ADR-FORMAT.md)
    adr_files = sorted(
        p for p in ADR_DIR.glob("*.md")
        if p.name not in ("INDEX.md", "ADR-FORMAT.md")
    )
    print(f"Total ADR files on disk: {len(adr_files)}")

    # Cross-check with INDEX
    indexed = set(entries)
    present = set()
    for f in adr_files:
        m = re.match(r"^(\d{4})-", f.name)
        if m:
            present.add(m.group(1))
        else:
            errors.append(f"WARN: {f.name} does not match ADR naming convention")

    missing_from_index = present - indexed
    if missing_from_index:
        errors.append(f"FAIL: ADR files not in INDEX: {sorted(missing_from_index)}")

    missing_from_disk = indexed - present
    if missing_from_disk:
        errors.append(f"FAIL: INDEX entries missing on disk: {sorted(missing_from_disk)}")

    print()
    print(f"\n=== Summary ===")
    print(f"INDEX entries: {len(indexed)}")
    print(f"Files on disk: {len(adr_files)}")
    print(f"Cross-check: {'PASS' if indexed == present else 'FAIL'}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nAll checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
