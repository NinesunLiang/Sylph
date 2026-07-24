#!/usr/bin/env python3
"""
test-sublimation.py — Sublimation pipeline integrity tests.

Verifies:
1. sublimation-log.jsonl is valid JSONL, each entry has required fields
2. anti-patterns.md is valid markdown with expected section headers
3. Knowledge directory structure matches expected layout
4. Content consistency: log entries reference existing anti-patterns sections
5. Kernel promotion field values are valid
"""

import json
import os
import re
import sys
import pathlib

# --- Paths ---
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SUBLIMATION_LOG = REPO_ROOT / ".omc" / "knowledge" / "sublimation-log.jsonl"
ANTI_PATTERNS = REPO_ROOT / ".claude" / "references" / "anti-patterns.md"
KNOWLEDGE_DIR = REPO_ROOT / ".omc" / "knowledge"
INDEX_MD = KNOWLEDGE_DIR / "index.md"
CLAUDENEXT_MD = KNOWLEDGE_DIR / "claude-next.md"

# Required fields for each JSONL log entry
REQUIRED_LOG_FIELDS = {"ts", "pattern", "hits", "target", "kernel_promotion", "note"}
VALID_PROMOTIONS = {"promoted", "archived", "none"}


def test_log_file_exists() -> None:
    """Verify sublimation-log.jsonl exists and is non-empty."""
    assert SUBLIMATION_LOG.exists(), f"Missing: {SUBLIMATION_LOG}"
    assert SUBLIMATION_LOG.stat().st_size > 0, f"Empty file: {SUBLIMATION_LOG}"


def test_log_is_valid_jsonl() -> None:
    """Parse each line of JSONL; all must be valid JSON with required fields."""
    entries = []
    with SUBLIMATION_LOG.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue  # skip blank lines
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                raise AssertionError(f"Line {i}: invalid JSON — {e}")
            assert isinstance(entry, dict), f"Line {i}: not a JSON object"
            missing = REQUIRED_LOG_FIELDS - set(entry.keys())
            assert not missing, f"Line {i}: missing fields: {missing}"
            assert isinstance(entry["hits"], int) and entry["hits"] >= 0, (
                f"Line {i}: 'hits' must be non-negative int, got {entry['hits']}"
            )
            assert entry["kernel_promotion"] in VALID_PROMOTIONS, (
                f"Line {i}: invalid kernel_promotion '{entry['kernel_promotion']}', "
                f"must be one of {VALID_PROMOTIONS}"
            )
            entries.append(entry)
    assert entries, "JSONL file has no non-empty lines"


def test_anti_patterns_exists() -> None:
    """Verify anti-patterns.md exists and is non-empty."""
    assert ANTI_PATTERNS.exists(), f"Missing: {ANTI_PATTERNS}"
    content = ANTI_PATTERNS.read_text(encoding="utf-8")
    assert content.strip(), f"Empty file: {ANTI_PATTERNS}"


def test_anti_patterns_has_expected_sections() -> None:
    """Check for major section headers in anti-patterns.md."""
    content = ANTI_PATTERNS.read_text(encoding="utf-8")
    expected_sections = [
        "## 已识别模式",         # Identified patterns
        "## 历史记录",           # History
        "## E. 闭环失败",        # Loop Failure
        "## F. 工具误用",        # Tool Misuse
        "## G. 继承失效",        # Inheritance Breakage
        "## H. 安全忽视",        # Security Neglect
        "## I. 运行稳定性",      # Runtime Instability
        "## J. 分类缺失",        # Classification Gap
    ]
    for section in expected_sections:
        assert section in content, f"Missing section header: {section}"


def test_anti_patterns_entries_have_against() -> None:
    """
    Every E/F/G/H/I/J sub-entry (E1, E2, etc.) must have a '→ against:' line.
    """
    content = ANTI_PATTERNS.read_text(encoding="utf-8")
    lines = content.splitlines()
    current_entry = None
    for line in lines:
        m = re.match(r"^### ([A-Z]\d+)\s", line)
        if m:
            current_entry = m.group(1)
            continue
        if current_entry and "→ against:" in line:
            current_entry = None
    # Any entry left without '→ against:' is a failure
    if current_entry:
        raise AssertionError(
            f"Entry {current_entry} is missing a '→ against:' line"
        )


def test_knowledge_dir_structure() -> None:
    """Verify .omc/knowledge/ has the expected file layout."""
    assert KNOWLEDGE_DIR.is_dir(), f"Missing directory: {KNOWLEDGE_DIR}"
    expected_files = {"index.md", "claude-next.md", "sublimation-log.jsonl"}
    actual_files = {p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file()}
    missing = expected_files - actual_files
    assert not missing, f"Missing files in {KNOWLEDGE_DIR}: {missing}"


def test_log_content_consistency() -> None:
    """
    Every log entry whose target is anti-patterns.md should have its pattern
    name (or a reasonable fragment) referenced in the anti-patterns doc body.
    """
    anti_content = ANTI_PATTERNS.read_text(encoding="utf-8")
    with SUBLIMATION_LOG.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("target") != "anti-patterns.md":
                continue
            # The pattern identifier should appear in the document
            # (e.g., "timeout" appears in I1 header, "unknown" appears in J1)
            pattern = entry["pattern"]
            if pattern not in anti_content:
                # Relaxed: check prefix match
                found = any(
                    pattern in line for line in anti_content.splitlines()
                )
                assert found, (
                    f"Line {i}: pattern '{pattern}' not found in anti-patterns.md"
                )


def test_log_timestamps_are_iso8601() -> None:
    """Validate timestamp format in log entries (basic ISO-8601 check)."""
    ts_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"
    )
    with SUBLIMATION_LOG.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            ts = entry.get("ts", "")
            assert ts_pattern.match(ts), (
                f"Line {i}: timestamp '{ts}' does not match ISO-8601 format"
            )


def test_anti_patterns_updated_matches_logs() -> None:
    """
    The 'Updated' line in anti-patterns.md should reference patterns
    matching the most recent sublimation-log entries.
    """
    content = ANTI_PATTERNS.read_text(encoding="utf-8")
    updated_line = [
        l for l in content.splitlines() if l.startswith("_Updated:")
    ]
    assert updated_line, "Missing _Updated: line in anti-patterns.md"
    # Read the last log entry and verify its pattern appears in the update note
    with SUBLIMATION_LOG.open("r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    last_entry = json.loads(lines[-1].strip())
    pattern = last_entry["pattern"]
    note_text = updated_line[0]
    assert pattern in note_text, (
        f"Most recent log pattern '{pattern}' not mentioned in _Updated: line"
    )


def test_no_junk_files_in_knowledge() -> None:
    """Warn if unexpected files exist in .omc/knowledge/."""
    ALLOWED = {"index.md", "claude-next.md", "sublimation-log.jsonl"}
    actual = {p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file()}
    extras = actual - ALLOWED
    if extras:
        print(f"WARNING: Unexpected files in knowledge dir: {extras}", file=sys.stderr)


def main() -> None:
    """Run all tests, exit with status 1 if any fail."""
    tests = [
        ("Log file exists", test_log_file_exists),
        ("Log is valid JSONL", test_log_is_valid_jsonl),
        ("Timestamp format", test_log_timestamps_are_iso8601),
        ("Anti-patterns exists", test_anti_patterns_exists),
        ("Anti-patterns sections", test_anti_patterns_has_expected_sections),
        ("Anti-patterns 'against:' rules", test_anti_patterns_entries_have_against),
        ("Knowledge dir structure", test_knowledge_dir_structure),
        ("Log-content consistency", test_log_content_consistency),
        ("Updated line matches logs", test_anti_patterns_updated_matches_logs),
        ("No junk files", test_no_junk_files_in_knowledge),
    ]

    failures = 0
    for name, fn in tests:
        try:
            fn()
        except (AssertionError, FileNotFoundError) as e:
            print(f"FAIL  {name}: {e}", file=sys.stderr)
            failures += 1
        else:
            print(f"OK    {name}")

    if failures:
        sys.exit(1)
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
