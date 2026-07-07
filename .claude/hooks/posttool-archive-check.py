#!/usr/bin/env python3
"""
CarrorOS PostToolUse Archive Check Hook

Purpose:
  After task archive command, validate archive completeness.
  Checks that Sovereign Verdict, manifest, tombstone, and audit-slice
  were generated correctly.

Constraints:
  - Routing / observation / guardrail only
  - Does not create completion facts
"""

from __future__ import annotations

import json

from carroros_hooklib import (
    active_token,
    append_audit,
    extract_tool_name,
    hook_continue,
    read_stdin_json,
    ROOT,
)


def main() -> int:
    payload = read_stdin_json()
    tool = extract_tool_name(payload).lower()

    # Only check after archive-related commands
    result = str(payload.get("result", "") or payload.get("tool_result", "") or "")

    # Detect if an archive just happened
    if '"verdict": "ARCHIVED"' in result or "archive_completed" in result.lower():
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            return hook_continue("ArchiveCheck: SKIP no_json_result")

        archive_path = data.get("archive_path")
        if archive_path:
            archive_dir = ROOT / archive_path
            checks = {
                "final_report": archive_dir / "final-report.md",
                "sovereign_verdict": archive_dir / "sovereign-verdict.json",
                "manifest": archive_dir / "manifest.json",
                "tombstone": archive_dir / "token-tombstone.json",
            }
            missing = [name for name, path in checks.items() if not path.exists()]
            if missing:
                append_audit({
                    "event_type": "archive_check_warning",
                    "actor": "hook:posttool-archive-check",
                    "decision": "WARN",
                    "reason": f"archive_missing_files: {', '.join(missing)}",
                    "archive_path": archive_path,
                })
                return hook_continue(f"ArchiveCheck: WARN missing: {', '.join(missing)}")

            append_audit({
                "event_type": "archive_check_pass",
                "actor": "hook:posttool-archive-check",
                "decision": "OK",
                "archive_path": archive_path,
            })
            return hook_continue("ArchiveCheck: OK all_archive_files_present")

    return hook_continue("ArchiveCheck: SKIP")


if __name__ == "__main__":
    raise SystemExit(main())
