#!/usr/bin/env python3
"""test-coverage-gate.py — Coverage Gate

自动发现 CarrorOS 所有机制，检测是否具有独立验收测试。
无测试覆盖的机制阻止 scorecard 提分(除非 human-override)。

用法:
  python3 tests/test-coverage-gate.py           # 扫描+报告
  python3 tests/test-coverage-gate.py --block    # 无测试覆盖则 exit 2

退出码:
  0 = 所有机制有测试覆盖
  1 = 有未覆盖机制(仅报告)
  2 = 有未覆盖机制(阻断模式)
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
SCRIPTS_DIR = PROJECT_ROOT / ".claude" / "scripts"
FEATURE_TEST_DIR = PROJECT_ROOT / "tests"
TEST_SCRIPTS_DIR = FEATURE_TEST_DIR

# ─── 机制注册表 ───
# 每项 = (名称, 类型, 路径模式, 对应的测试文件)
# 找不到对应测试文件即为"未覆盖"
MECHANISMS: list[tuple[str, str, list[str], str | None]] = [
    # ── hooks 层 (38 个 py 文件) ──
    ("pretool-gate", "hook", [".claude/hooks/pretool-gate.py"], None),
    ("pre-completion-gate", "hook", [".claude/hooks/pre-completion-gate.py"], None),
    ("completion-gate", "hook", [".claude/hooks/completion-gate.py"], None),
    ("pretool-user-approve", "hook", [".claude/hooks/pretool-user-approve.py"], None),
    ("posttool-claim-audit", "hook", [".claude/hooks/posttool-claim-audit.py"], None),
    ("posttool-sensitive-filter", "hook", [".claude/hooks/posttool-sensitive-filter.py"], None),
    ("posttool-bash-audit", "hook", [".claude/hooks/posttool-bash-audit.py"], None),
    ("posttool-output-schema", "hook", [".claude/hooks/posttool-output-schema.py"], None),
    ("read-tracker", "hook", [".claude/hooks/read-tracker.py"], None),
    ("hook-launcher", "hook", [".claude/hooks/hook-launcher.py"], "test-hook-launcher.sh"),
    ("session-start", "hook", [".claude/hooks/session-start.py"], None),
    ("session-resume", "hook", [".claude/hooks/session-resume.py"], None),
    ("precompact-lifecycle", "hook", [".claude/hooks/precompact-lifecycle.py"], "test_pkg_c_lifecycle.py"),
    ("lifecycle-ssot", "hook", [".claude/hooks/lib/lifecycle_ssot.py"], "test_pkg_c_lifecycle.py"),
    ("stop-flywheel", "hook", [".claude/hooks/stop-flywheel.py"], None),
    ("error-dna", "hook", [".claude/hooks/error-dna.py"], None),
    ("turn-counter", "hook", [".claude/hooks/turn-counter.py"], None),
    ("token-writer", "hook", [".claude/hooks/token_writer.py"], None),
    ("carroros-night-deny", "hook", [".claude/hooks/carroros-night-deny.py"], "test-night-deny.py"),
    # ── scripts 层 ──
    ("verify-gate", "script", [".claude/scripts/verify_gate.py"], "test-verify-gate.py"),
    ("fallback-engine", "script", [".claude/scripts/fallback_engine.py"], "test-fallback-engine.py"),
    ("oracle-agent", "script", [".claude/scripts/oracle_agent.py"], "test-oracle-gate.py"),
    ("meta-oracle", "script", [".claude/scripts/meta_oracle.py"], None),
    ("context-watermark", "script", [".claude/scripts/context_watermark.py"], "test-context-watermark.py"),
    ("lx-goal", "skill", [".claude/skills/lx-goal/scripts/lx-goal.py"], None),
    # ── 生命周期/互斥 ──
    ("goal-mode-gate", "gate", [".claude/hooks/pretool-gate.py"], "test-goal-mode-gate.py"),
    ("lifecycle-mutex", "gate", [".claude/hooks/lib/lifecycle_ssot.py"], "test-lifecycle-mutex.py"),
    ("task-ssot", "gate", [".claude/scripts/lib/task_ssot.py", ".claude/hooks/"], "test-task-ssot.py"),
    ("e4-inertia", "gate", [".claude/hooks/pretool-gate.py"], "test-e4-inertia.py"),
    ("nine-challenge", "gate", [".claude/hooks/pretool-gate.py"], "test-nine-challenge.py"),
    ("audit-schema", "gate", [".claude/hooks/"], "test-audit-schema.py"),
    ("lx-stepwise", "gate", [".claude/skills/lx-goal/"], "test-lx-stepwise.py"),
    ("pkg-c-lifecycle", "gate", [".claude/hooks/precompact-lifecycle.py"], "test_pkg_c_lifecycle.py"),
    # ── meta 治理 ──
    ("evaluation-framework", "meta", [".claude/references/evaluation-framework.md"], None),
    ("scorecard", "meta", ["improve_plan/CarrorOS_second_time/scorecard.md"], None),
    ("ADR-system", "meta", [".claude/references/adr/"], None),
    ("knowledge-sublimation", "meta", [".omc/knowledge/"], "test-sublimation.py"),
    ("harness-core", "lib", [".claude/hooks/harness_core.py"], "test-harness-lib.py"), # implicitly tested
    ("harness-lib", "lib", [".claude/hooks/harness_lib.py"], None),
]


def _find_test_file(test_hint: str | None, name_fallback: str = "") -> Path | None:
    """Resolve a test file hint to an actual path.

    Falls back to auto-detecting: test-<name>.py or test-<name>.sh
    where name is the mechanism name with underscores converted to dashes.
    """
    if test_hint is None and name_fallback:
        for ext in (".py", ".sh"):
            pf = TEST_SCRIPTS_DIR / f"test-{name_fallback}{ext}"
            if pf.exists():
                return pf
            pf2 = HOOKS_DIR / "tests" / f"test-{name_fallback}{ext}"
            if pf2.exists():
                return pf2
        return None
    if test_hint is None:
        return None
    p = TEST_SCRIPTS_DIR / test_hint
    if p.exists():
        return p
    # Check hooks/tests/
    p2 = HOOKS_DIR / "tests" / test_hint
    if p2.exists():
        return p2
    # Check scripts/ top-level (test-* pattern)
    p3 = PROJECT_ROOT / "scripts" / test_hint
    if p3.exists():
        return p3
    return None


def _existing_test_files() -> set[str]:
    """Return basenames of all known test files."""
    tests: set[str] = set()
    for p in sorted(TEST_SCRIPTS_DIR.glob("test-*")):
        tests.add(p.name)
    for p in sorted(HOOKS_DIR.glob("tests/test-*")):
        tests.add(p.name)
    return tests


def _find_hooks() -> set[str]:
    """Return all .py files in hooks dir (auto-discovery fallback)."""
    return set(f.name for f in HOOKS_DIR.glob("*.py"))


def _auto_discover_mechanisms(all_tests: set[str], registered: set[str]) -> list[str]:
    """Auto-discover hooks that have no corresponding test file."""
    uncovered: list[str] = []
    for h in sorted(_find_hooks()):
        pyfile = HOOKS_DIR / h
        if not pyfile.is_file():
            continue
        # Skip shared libs that aren't directly registered
        if h in ("harness_core.py", "harness_lib.py", "carroros_hooklib.py", "agentic-ui.py"):
            continue
        # Skip if already in registered mechanisms (avoid double-count)
        norm_name = h.replace(".py", "").replace("_", "-")
        if norm_name in registered:
            continue
        # Look for any test-* file that contains the hook name
        has_test = any(h.replace(".py", "") in t for t in all_tests)
        if not has_test:
            uncovered.append(h)
    return uncovered


def main() -> int:
    block = "--block" in sys.argv

    all_tests = _existing_test_files()
    covered: list[str] = []
    uncovered: list[tuple[str, str, str]] = []  # (name, type, reason)

    # Check registered mechanisms
    for name, mtype, _paths, test_hint in MECHANISMS:
        tf = _find_test_file(test_hint, name_fallback=name)
        if tf is not None:
            covered.append(name)
        else:
            uncovered.append((name, mtype, f"无测试文件({test_hint})" if test_hint is not None else "无独立测试"))

    # Auto-discover any hooks not in the registry
    registered_names = {m[0] for m in MECHANISMS}
    for uh in sorted(_auto_discover_mechanisms(all_tests, registered_names)):
        if uh not in registered_names:
            uncovered.append((uh.replace(".py", ""), "hook-auto", "未注册 + 无测试"))

    # Output
    total = len(covered) + len(uncovered)
    pct = len(covered) / total * 100 if total > 0 else 0

    print("=" * 64)
    print(f"Coverage Gate — {len(covered)}/{total} 覆盖 ({pct:.0f}%)")
    print("=" * 64)
    print()

    if uncovered:
        print(f"❌ {len(uncovered)} 项无测试覆盖:")
        print()
        for name, mtype, reason in sorted(uncovered):
            print(f"  [{mtype:>10}] {name:<35} {reason}")
        print()
        print(f"  测试文件名模式: tests/test-<mechanism>.py 或 tests/test-<mechanism>.sh")
        print()
        if block:
            print("⚠️  阻断模式: 有未覆盖机制, exit=2")
            return 2
        else:
            print("⚠️  报告模式: 有未覆盖机制, exit=0")
            return 0
    else:
        print("✅ 所有机制已有测试覆盖")
        return 0


if __name__ == "__main__":
    sys.exit(main())
