#!/usr/bin/env python3
"""
test-harness-lib.py — verify harness_core / harness_lib exports.

Verifies:
1. harness_core exports: hc_enabled, output_continue, read_input, flywheel_event, hc_get
2. harness_lib re-exports all core symbols (same 5 + extras)
3. Both modules import cleanly without error
"""

import importlib
import sys
import traceback

# Use absolute path so this script works regardless of cwd
_HOOKS_DIR = "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS/.claude/hooks"
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

CORE_EXPECTED = {"hc_enabled", "output_continue", "read_input", "flywheel_event", "hc_get"}

exit_code = 0

def fail(label, msg):
    global exit_code
    exit_code = 1
    print(f"FAIL [{label}] {msg}", file=sys.stderr)

def check_importable(mod_name, label):
    """Attempt a fresh import of mod_name."""
    # Remove any prior cached import
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    try:
        importlib.import_module(mod_name)
        print(f"  PASS  {label} imports cleanly")
    except Exception:
        fail(label, f"import failed:\n{traceback.format_exc()}")

def check_has_attr(mod, name, label):
    if not hasattr(mod, name):
        fail(label, f"missing symbol: {name}")
    else:
        print(f"  PASS  {label} exports {name}")

# ─── Test 1: harness_core imports cleanly ──────────────────────────────────
print("=== Test 1: harness_core import ===")
check_importable("harness_core", "harness_core")

# Re-import for attribute checks
import harness_core as core

# ─── Test 2: harness_core exports 5 required symbols ──────────────────────
print("\n=== Test 2: harness_core exports required symbols ===")
for sym in sorted(CORE_EXPECTED):
    check_has_attr(core, sym, "harness_core")

# ─── Test 3: harness_lib imports cleanly ──────────────────────────────────
print("\n=== Test 3: harness_lib import ===")
check_importable("harness_lib", "harness_lib")

import harness_lib as lib

# ─── Test 4: harness_lib re-exports all core symbols ──────────────────────
print("\n=== Test 4: harness_lib re-exports core symbols ===")
for sym in sorted(CORE_EXPECTED):
    check_has_attr(lib, sym, "harness_lib")

# ─── Test 5: harness_lib additionally exports lib-only functions ───────────
print("\n=== Test 5: harness_lib exports lib-only functions ===")
LIB_ONLY = {"hc_init", "hc_get_list", "hc_fail_closure", "hc_hook_enabled",
            "hc_skill_enabled", "hc_project_root", "hc_state_dir",
            "is_mode_active", "hc_gate_mode_warn", "hc_gate_mode_block",
            "hc_generate_token", "hc_captcha_check", "hc_sanitize_utf8",
            "hc_gate_block", "hc_gate_warn_output", "hc_gate_pass",
            "agentic_menu", "hc_read_config", "extract_event_name",
            "extract_tool_name", "extract_file_path", "extract_tool_input_status",
            "sanitize_text", "output_additional_context"}
for sym in sorted(LIB_ONLY):
    check_has_attr(lib, sym, "harness_lib")

# ─── Test 6: Core symbols from lib are the same objects as from core ───────
print("\n=== Test 6: Same-object identity (lib.foo is core.foo) ===")
for sym in sorted(CORE_EXPECTED):
    if hasattr(lib, sym) and hasattr(core, sym):
        if getattr(lib, sym) is getattr(core, sym):
            print(f"  PASS  lib.{sym} is core.{sym}")
        else:
            fail("identity", f"lib.{sym} is NOT core.{sym} (different objects)")
    else:
        fail("identity", f"cannot check identity for {sym}")

# ─── Summary ───────────────────────────────────────────────────────────────
print("\n" + "=" * 48)
if exit_code == 0:
    print("ALL CHECKS PASSED")
else:
    print(f"SOME CHECKS FAILED (exit code {exit_code})")

sys.exit(exit_code)
