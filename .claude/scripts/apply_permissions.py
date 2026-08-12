#!/usr/bin/env python3
"""apply-permissions.py — merge portable headless permission contract into local settings.

Reads `.claude/settings.permissions.json` (committed contract) and merges its
`permissions.allow` rules into `.claude/settings.local.json` (machine-local,
gitignored) as a union — dedup, preserve existing rules, never clobber unknown
fields. Idempotent: no changes → no write. Backs up target before first write.

Fresh environment setup:
    python3 .claude/scripts/apply-permissions.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = PROJECT_ROOT / ".claude" / "settings.permissions.json"
DEFAULT_TARGET = PROJECT_ROOT / ".claude" / "settings.local.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def merge_allow(existing: list, contract: list) -> list:
    """Union of allow rules preserving existing order; contract rules appended."""
    seen = set()
    out: list = []
    for rule in list(existing) + list(contract):
        if rule in seen:
            continue
        seen.add(rule)
        out.append(rule)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="contract json path")
    ap.add_argument("--target", default=str(DEFAULT_TARGET), help="settings.local.json path")
    ap.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = ap.parse_args()

    contract_path = Path(args.contract)
    target_path = Path(args.target)

    contract = load_json(contract_path)
    contract_allow = contract.get("permissions", {}).get("allow", [])
    if not isinstance(contract_allow, list) or not contract_allow:
        print(f"ERROR: contract {contract_path} has empty permissions.allow", file=sys.stderr)
        return 2

    target = load_json(target_path)
    target_permissions = target.setdefault("permissions", {})
    existing = target_permissions.get("allow", [])
    merged = merge_allow(existing if isinstance(existing, list) else [], contract_allow)

    changed = merged != existing
    print(f"contract={contract_path} target={target_path}")
    print(f"  existing allow={len(existing)} -> merged allow={len(merged)} changed={changed}")
    if not changed:
        print("OK: no changes, nothing to write (idempotent)")
        return 0
    if args.dry_run:
        print("DRY-RUN: would write", len(merged) - len(existing), "new rule(s)")
        return 0

    # backup once
    bak = Path(str(target_path) + ".bak")
    if not bak.exists():
        shutil.copy2(target_path, bak)
        print(f"backup: {bak}")
    target_permissions["allow"] = merged
    target_path.write_text(
        json.dumps(target, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"WROTE: {target_path} ({len(merged)} allow rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
