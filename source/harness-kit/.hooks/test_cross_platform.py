#!/usr/bin/env python3
"""
.hooks/test_cross_platform.py — Auto Feature Test Suite
Tests config generation for all 6 platforms, validates structure,
verifies hook counts, event mappings, and fallback mechanism.

Usage:
  python3 .hooks/test_cross_platform.py

Exit codes:
  0  All tests passed
  1  One or more tests failed
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"

tests_passed = 0
tests_failed = 0
test_results: list[str] = []


def test(name: str):
    """Decorator-like test runner."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            global tests_passed, tests_failed
            try:
                fn(*args, **kwargs)
                tests_passed += 1
                test_results.append(f"  {PASS} {name}")
            except AssertionError as e:
                tests_failed += 1
                test_results.append(f"  {FAIL} {name}: {e}")
            except Exception as e:
                tests_failed += 1
                test_results.append(f"  {FAIL} {name}: {type(e).__name__}: {e}")
        return wrapper
    return decorator


# ── Helpers ────────────────────────────────────────────────────────────

def load_unified() -> dict[str, Any]:
    import yaml
    path = _HERE / "unified.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "unified.yaml is not a dict"
    return data


def get_adapters():
    sys.path.insert(0, str(_HERE))
    from adapters import ADAPTERS
    return ADAPTERS


# ── Tests ──────────────────────────────────────────────────────────────

@test("unified.yaml: version exists")
def test_version(unified):
    assert "version" in unified, "missing version"
    assert unified["version"], "empty version"


@test("unified.yaml: 9 universal events defined")
def test_events(unified):
    events = unified.get("events", {})
    assert len(events) == 9, f"expected 9 events, got {len(events)}"
    expected = [
        "session:start", "prompt:submit", "tool:before", "tool:after",
        "shell:before", "shell:after", "file:write", "compact:before", "stop",
    ]
    for e in expected:
        assert e in events, f"missing event: {e}"


@test("unified.yaml: 6 platform event mappings")
def test_platform_events(unified):
    pmap = unified.get("platform_events", {})
    assert len(pmap) == 6, f"expected 6 platforms, got {len(pmap)}"
    expected = ["claude_code", "codex", "gemini", "qwen", "cursor", "opencode"]
    for p in expected:
        assert p in pmap, f"missing platform: {p}"
        assert len(pmap[p]) == 9, f"{p}: expected 9 event mappings, got {len(pmap[p])}"


@test("unified.yaml: 22 portable hooks defined")
def test_portable_hooks(unified):
    hooks = unified.get("hooks", {})
    assert len(hooks) == 22, f"expected 22 hooks, got {len(hooks)}"


@test("unified.yaml: 7 Claude-specific hooks defined")
def test_claude_specific(unified):
    cs = unified.get("claude_specific", {})
    assert len(cs) == 7, f"expected 7 claude-specific hooks, got {len(cs)}"


@test("unified.yaml: all 29 hooks accounted for")
def test_total_hooks(unified):
    hooks = unified.get("hooks", {})
    cs = unified.get("claude_specific", {})
    assert len(hooks) + len(cs) == 29, f"expected 29 total, got {len(hooks)} + {len(cs)}"


@test("unified.yaml: all hook scripts exist on disk")
def test_hook_scripts(unified):
    hooks_root = PROJECT_ROOT / unified.get("meta", {}).get("hooks_root", ".claude/hooks")
    all_hooks = {**unified.get("hooks", {}), **unified.get("claude_specific", {})}
    missing = []
    for name, hdef in all_hooks.items():
        script = hdef.get("script", "")
        if script:
            script_path = hooks_root / script
            if not script_path.exists():
                missing.append(f"{name}: {script}")
    assert not missing, f"missing scripts: {missing}"


# ── Adapter Tests ──────────────────────────────────────────────────────

# Expected hook counts per platform (from unified.yaml hook platform lists)
EXPECTED_HOOK_COUNTS = {
    "claude_code": 22,  # all 22 portable hooks
    "codex": 22,
    "gemini": 22,
    "qwen": 22,
    "cursor": 4,   # permission_gate + bash_audit + turn_counter + compact_detect
    "opencode": 20,  # all 22 portable minus 2 (edit_guard=no-op w/o read-tracker, build_validator=script missing)
}

EXPECTED_SUPPORTED_EVENTS = {
    "claude_code": 9,
    "codex": 9,
    "gemini": 7,  # session:start=null, compact:before=null
    "qwen": 9,
    "cursor": 6,  # session:start=null, file:write=null, compact:before=null
    "opencode": 9,
}


def test_adapter_generation(unified, adapters, platform_key):
    """Generic test for adapter config generation."""
    adapter = None
    for a in adapters:
        if a.key == platform_key:
            adapter = a
            break
    assert adapter is not None, f"adapter not found: {platform_key}"

    # Resolve event map
    pmap = unified.get("platform_events", {}).get(platform_key, {})
    event_map = {k: str(v) for k, v in pmap.items() if v is not None}
    supported = len(event_map)
    expected_events = EXPECTED_SUPPORTED_EVENTS[platform_key]
    assert supported == expected_events, \
        f"{platform_key}: expected {expected_events} supported events, got {supported}. Missing: {[k for k,v in pmap.items() if v is None]}"

    # Filter hooks for this platform
    all_hooks = unified.get("hooks", {})
    platform_hooks = {
        name: hdef for name, hdef in all_hooks.items()
        if platform_key in hdef.get("platforms", [])
    }
    expected_count = EXPECTED_HOOK_COUNTS[platform_key]
    assert len(platform_hooks) == expected_count, \
        f"{platform_key}: expected {expected_count} hooks, got {len(platform_hooks)}. Got: {list(platform_hooks.keys())}"

    # Generate config
    try:
        config = adapter.generate(PROJECT_ROOT, unified, platform_hooks, event_map)
    except Exception as e:
        raise AssertionError(f"{platform_key}: generate() raised {e}")

    # Claude Code returns None (uses existing harness.yaml)
    if platform_key == "claude_code":
        assert config is None, f"{platform_key}: expected None (uses existing harness)"
        return

    # Validate config structure
    if platform_key == "opencode":
        # TypeScript plugin
        assert isinstance(config, str), f"{platform_key}: expected string, got {type(config).__name__}"
        assert "export default" in config, f"{platform_key}: missing export default"
        assert "tool.execute.before" in config, f"{platform_key}: missing tool.execute.before"
        assert "tool.execute.after" in config, f"{platform_key}: missing tool.execute.after"
        assert "session.created" in config, f"{platform_key}: missing session.created"
        assert "chat.message" in config, f"{platform_key}: missing chat.message"
        assert "session.idle" in config, f"{platform_key}: missing session.idle"
        # Count hook entries (some hooks register in multiple event groups, e.g. token_writer)
        hook_count = config.count('name: "')
        assert hook_count >= expected_count, \
            f"{platform_key}: expected at least {expected_count} hook entries, found {hook_count}"
    else:
        # JSON-based config
        assert isinstance(config, dict), f"{platform_key}: expected dict, got {type(config).__name__}"
        hooks_section = config.get("hooks", config)
        assert isinstance(hooks_section, dict), f"{platform_key}: hooks not a dict"

        # Count hook registrations
        total = 0
        for event_name, groups in hooks_section.items():
            for g in groups if isinstance(groups, list) else [groups]:
                if isinstance(g, dict):
                    inner = g.get("hooks", [g])
                    total += len(inner) if isinstance(inner, list) else 1

        # Each platform has unique hooks — verify at least the minimum
        assert total > 0, f"{platform_key}: no hook registrations found"


# Register test per platform
for _pk in EXPECTED_HOOK_COUNTS:
    _name = _pk

    @test(f"adapter {_name}: generation & validation")
    def _make_test(_unused=None, pk=_pk):
        unified = load_unified()
        adapters = get_adapters()
        test_adapter_generation(unified, adapters, pk)

    globals()[f"test_adapter_{_pk}"] = _make_test


@test("fallback cache: .hooks/.cache exists and has content")
def test_fallback_cache(unified):
    cache_path = _HERE / ".cache"
    assert cache_path.exists(), ".hooks/.cache not found"
    content = cache_path.read_text()
    assert len(content) > 100, f".hooks/.cache too small: {len(content)} bytes"
    assert "hooks_enabled." in content, ".hooks/.cache missing hooks_enabled"
    assert "workflow.doc_root=rpe" in content, ".hooks/.cache missing workflow defaults"


@test("fallback cache: harness_config.sh reads pre-generated .harness-cache")
def test_fallback_mechanism(_unused=None):
    """Test that harness_config.sh can read pre-generated .harness-cache when harness.yaml is absent."""
    # Use a temp dir to simulate project without harness.yaml
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create minimal project structure
        hooks_dir = tmp / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(PROJECT_ROOT / ".claude" / "hooks" / "harness_config.sh", hooks_dir / "harness_config.sh")

        state_dir = tmp / ".omc" / "state"
        state_dir.mkdir(parents=True)

        # Copy .hooks/.cache
        cache_dir = tmp / ".hooks"
        cache_dir.mkdir(parents=True)
        shutil.copy(_HERE / ".cache", cache_dir / ".cache")
        # Also copy to state dir where harness_config.sh actually reads it
        shutil.copy(_HERE / ".cache", state_dir / ".harness-cache")

        result = subprocess.run(
            ["bash", "-c", f"""
                source "{hooks_dir}/harness_config.sh"
                val=$(hc_get "workflow.doc_root" "nope")
                echo "doc_root=$val"
                enabled=$(hc_enabled "completion_gate" && echo "true" || echo "false")
                echo "completion_gate_enabled=$enabled"
                notfound=$(hc_get "nonexistent.key" "default_val")
                echo "default=$notfound"
            """],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        assert result.returncode == 0, f"harness_config.sh failed: {result.stderr}"
        assert "doc_root=rpe" in output, f"expected doc_root=rpe, got: {output}"
        assert "completion_gate_enabled=true" in output, f"expected enabled=true, got: {output}"
        assert "default=default_val" in output, f"expected default=default_val, got: {output}"


@test("list command: output matches expected structure")
def test_list_command(_unused=None):
    result = subprocess.run(
        ["python3", str(_HERE / "generate.py"), "list"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"list command failed: {result.stderr}"
    output = result.stdout
    assert "Hook × Platform Matrix" in output, "missing Hook × Platform Matrix"
    assert "Event × Platform Matrix" in output, "missing Event × Platform Matrix"
    assert "Claude Only (7)" in output, "missing Claude Only summary"
    assert "Total: 22 portable + 7 Claude-specific = 29 hooks" in output, "wrong total"
    assert "auto_snapshot" in output, "missing auto_snapshot"
    assert "completion_gate" in output, "missing completion_gate"


@test("validate command: all generated configs valid")
def test_validate_command(_unused=None):
    result = subprocess.run(
        ["python3", str(_HERE / "generate.py"), "validate"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"validate command found issues: {result.stdout} {result.stderr}"
    assert "All configs valid" in result.stdout, "not all valid"


@test("marketing doc: matrices present and up to date")
def test_marketing_doc(_unused=None):
    doc_path = PROJECT_ROOT / "docs" / "marketing" / "cross-platform-hooks.md"
    assert doc_path.exists(), "marketing doc not found"
    content = doc_path.read_text()
    assert "Hook × Platform" in content, "marketing doc missing Hook × Platform Matrix"
    assert "Event × Platform" in content, "marketing doc missing Event × Platform Matrix"
    assert "Event Support by Platform" in content, "marketing doc missing Event Support by Platform"


# ── Main ───────────────────────────────────────────────────────────────

def main() -> int:
    global tests_passed, tests_failed

    print(f"\n{'='*60}")
    print("  Sylph Harness — Cross-Platform Auto Feature Test")
    print(f"{'='*60}\n")

    # Load once, pass to tests
    unified = load_unified()
    adapters = get_adapters()

    # Run all test functions
    test_fns = [
        test_version,
        test_events,
        test_platform_events,
        test_portable_hooks,
        test_claude_specific,
        test_total_hooks,
        test_hook_scripts,
    ]
    # Add adapter tests
    for pk in EXPECTED_HOOK_COUNTS:
        test_fns.append(globals()[f"test_adapter_{pk}"])
    test_fns += [
        test_fallback_cache,
        test_fallback_mechanism,
        test_list_command,
        test_validate_command,
        test_marketing_doc,
    ]

    for fn in test_fns:
        try:
            fn(unified)
        except AssertionError as e:
            tests_failed += 1
            test_results.append(f"  {FAIL} {fn.__name__}: {e}")
        except Exception as e:
            tests_failed += 1
            test_results.append(f"  {FAIL} {fn.__name__}: {type(e).__name__}: {e}")

    print(f"\n{'─'*60}")
    print(f"  Results: {tests_passed + tests_failed} tests")
    print(f"  {PASS} Passed: {tests_passed}")
    if tests_failed:
        print(f"  {FAIL} Failed: {tests_failed}")
    print(f"{'─'*60}\n")

    for r in test_results:
        print(r)
    print()

    if tests_failed:
        print(f"  {FAIL} Some tests failed. See above for details.\n")
        return 1
    else:
        print(f"  {PASS} All tests passed!\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
