#!/usr/bin/env python3
"""
.hooks/generate.py — Cross-platform AI CLI Hook Config Generator

Generates native hook configurations for:
  Claude Code | Codex CLI | Gemini CLI | Qwen Code | Cursor | OpenCode

Usage:
  python3 .hooks/generate.py detect          # List available platforms
  python3 .hooks/generate.py generate        # Generate configs for detected platforms
  python3 .hooks/generate.py install         # Generate + write configs
  python3 .hooks/generate.py validate        # Validate generated configs
  python3 .hooks/generate.py list            # List all hooks and portability

Options:
  --platform P  Only target a specific platform (repeatable)
  --dry-run     Show what would be written without writing
  --verbose     Detailed output (show events, hooks, mappings)

Exit codes:
  0  Success
  1  Config error
  2  Generation failure
  """

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

# ── Project Root ─────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent

# ── YAML Loader ──────────────────────────────────────────────────────────

def _load_unified(path: Path | None = None) -> dict[str, Any]:
    """Load unified.yaml using PyYAML (recommended) or fallback JSON loader."""
    if path is None:
        path = _HERE / "unified.yaml"
    if not path.exists():
        print(f"❌ unified.yaml not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("unified.yaml is empty or invalid")
        return data
    except ImportError:
        print("❌ PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


# ── Event Map Resolution ─────────────────────────────────────────────────

def _resolve_event_map(unified: dict[str, Any], platform_key: str) -> dict[str, str]:
    """Resolve unified event → native event mapping, dropping null entries."""
    pmap = unified.get("platform_events", {}).get(platform_key, {})
    return {k: str(v) for k, v in pmap.items() if v is not None}


def _filter_hooks(unified: dict[str, Any], platform_key: str) -> dict[str, Any]:
    """Return only hooks tagged for this platform."""
    all_hooks = unified.get("hooks", {})
    return {
        name: hdef for name, hdef in all_hooks.items()
        if platform_key in hdef.get("platforms", [])
    }


def _filter_events(unified: dict[str, Any], hooks: dict[str, Any]) -> set[str]:
    """Return the set of universal events used by a set of hooks."""
    events: set[str] = set()
    for hdef in hooks.values():
        events.update(hdef.get("events", []))
    return events


# ── Detection ────────────────────────────────────────────────────────────

def _do_detect(root: Path, adapters: list, verbose: bool = False) -> list[Any]:
    """Run detection on all adapters, print status, return detected list."""
    print(f"\n{'='*60}")
    print(f"  AI CLI Platform Detection")
    print(f"  Project: {root}")
    print(f"{'='*60}\n")

    detected = []
    for a in adapters:
        summary = a.summary(root)
        ok = summary.get("detected", False)
        status = "✅" if ok else "⬜"
        path_info = f" → {summary['config_path']}" if summary.get("config_path") else ""
        print(f"  {status} {a.name}{path_info}")

        if verbose and ok:
            extra = summary.get("needs_config_toml", False)
            if extra and summary.get("setup_help"):
                p = summary["setup_help"]
                for line in p.strip().split("\n"):
                    print(f"       {line}")

        if ok:
            detected.append(a)

    print(f"\n  {len(detected)}/{len(adapters)} platforms detected\n")
    return detected


# ── Generation ───────────────────────────────────────────────────────────

def _do_generate(root: Path, unified: dict[str, Any], adapters: list,
                 platform_filter: set[str] | None = None,
                 dry_run: bool = False,
                 verbose: bool = False) -> dict[str, Any]:
    """Generate and optionally install configs for detected platforms."""
    results: dict[str, Any] = {}
    claude_specific_count = len(unified.get("claude_specific", {}))

    print(f"\n{'='*60}")
    print(f"  Hook Config Generation")
    print(f"{'='*60}\n")

    for a in adapters:
        if platform_filter and a.key not in platform_filter:
            continue
        if not a.detect(root):
            print(f"  ⬜ {a.name}: not detected, skipping")
            results[a.key] = {"status": "skipped", "reason": "not detected"}
            continue

        event_map = _resolve_event_map(unified, a.key)
        if not event_map:
            print(f"  ⚠️  {a.name}: no event mapping, skipping")
            results[a.key] = {"status": "skipped", "reason": "no event map"}
            continue

        hooks = _filter_hooks(unified, a.key)
        used_events = _filter_events(unified, hooks) if hooks else set()

        config = a.generate(root, unified, hooks, event_map)
        out_path = a.config_path(root)

        # Claude Code uses existing harness — no gen
        if config is None:
            print(f"  🔗 {a.name}: uses existing harness.yaml")
            results[a.key] = {"status": "existing"}
            continue

        # Print summary
        if verbose:
            print(f"  ┌─ {a.name}")
            print(f"  │  Portable hooks: {len(hooks)} (+ {claude_specific_count} platform-specific)")
            print(f"  │  Events: {', '.join(sorted(used_events)) if used_events else 'none'}")
            print(f"  │  Output: {out_path}")
            print(f"  └─")
        else:
            hook_list = ", ".join(hooks) if hooks else "(none)"
            print(f"  🔧 {a.name} ({len(hooks)} hooks): {hook_list}")
            print(f"     → {out_path}")

        # Write or dry-run
        if dry_run:
            size = len(json.dumps(config)) if isinstance(config, (dict, list)) else len(str(config))
            print(f"     [dry-run] would write {size} bytes")
        else:
            written = a.install(root, config)
            for p in written:
                if p.exists():
                    print(f"     ✅ wrote {p.stat().st_size} bytes to {p}")
                else:
                    print(f"     ⚠️  failed to write {p}", file=sys.stderr)

        # Validate
        issues = _validate_config(config)
        if issues:
            for iss in issues:
                print(f"     ⚠️  {iss}")
            results[a.key] = {"status": "issues", "path": str(out_path), "count": len(hooks), "issues": issues}
        else:
            results[a.key] = {"status": "ok", "path": str(out_path), "count": len(hooks)}
        print()

    # After all platform configs, write the unified cache for hook fallback
    if not dry_run:
        _write_cache(root, unified)

    return results


def _write_cache(root: Path, unified: dict[str, Any]) -> None:
    """Write .hooks/.cache — key=value fallback for hooks on non-Claude-Code platforms.

    Format matches harness_config.sh's own cache format (section.key=value).
    Hook scripts call hc_get/hc_enabled which reads this when harness.yaml is absent.
    """
    cache_dir = root / ".hooks"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / ".cache"

    lines: list[str] = [
        "# Auto-generated by .hooks/generate.py",
        "# Fallback config for non-Claude-Code platforms",
        f"# Generated: 2026-05-03",
        "",
    ]

    # All portable hooks are enabled
    for name, hdef in unified.get("hooks", {}).items():
        lines.append(f"hooks_enabled.{name}=true")

    # Claude-specific hooks are disabled on non-Claude platforms
    for name in unified.get("claude_specific", {}):
        lines.append(f"hooks_enabled.{name}=false")

    # Write known config values from unified.yaml hook definitions
    for name, hdef in unified.get("hooks", {}).items():
        cfg = hdef.get("config", {})
        if isinstance(cfg, dict):
            for k, v in cfg.items():
                lines.append(f"{name}.{k}={v}")

    # Key harness.yaml values that hooks depend on
    lines.append("")
    lines.append("# workflow defaults (from harness.yaml)")
    lines.append("workflow.doc_root=rpe")
    lines.append("workflow.executor_doc=executor.md")
    lines.append("workflow.plan_doc=plan.md")

    lines.append("")
    lines.append("# project defaults")
    lines.append("project.source_extensions=.go")

    lines.append("")
    lines.append("# completion gate defaults")
    lines.append("completion_gate.min_evidence_chars=20")
    lines.append("completion_gate.required_keyword=VERIFIED")

    lines.append("")
    lines.append("# knowledge defaults")
    lines.append("knowledge.inject_files=index.md:full kernel.md:full claude-next.md:summary anti-patterns.md:summary")
    lines.append("knowledge.lsp_hint=")
    lines.append("knowledge.snapshot_expiry_sec=86400")

    lines.append("")
    lines.append("# session handoff defaults")
    lines.append("session_handoff.enabled=true")
    lines.append("session_handoff.max_adr_lines=10")
    lines.append("session_handoff.max_todo_lines=10")
    lines.append("session_handoff.max_lessons=3")

    lines.append("")
    lines.append("# sublimation defaults")
    lines.append("sublimation.count_threshold=20")
    lines.append("sublimation.age_days=10")
    lines.append("sublimation.hit_threshold=5")

    lines.append("")
    lines.append("# error DNA defaults")
    lines.append("error_dna.enabled=true")

    cache_path.write_text("\n".join(lines) + "\n")
    print(f"     ✅ wrote {cache_path.stat().st_size} bytes to {cache_path} (hook fallback cache)")


# ── Validation ───────────────────────────────────────────────────────────

def _validate_config(config: Any) -> list[str]:
    """Structural validation of a generated config."""
    issues: list[str] = []

    if isinstance(config, dict):
        h = config.get("hooks", config)
        if isinstance(h, dict):
            for evt, entries in h.items():
                if not isinstance(entries, list):
                    issues.append(f"{evt}: expected list, got {type(entries).__name__}")
                    continue
                for i, group in enumerate(entries):
                    if isinstance(group, dict) and "hooks" in group:
                        inner = group["hooks"]
                        if not isinstance(inner, list):
                            issues.append(f"{evt}[{i}].hooks: expected list")
                        else:
                            for j, e in enumerate(inner):
                                if "command" not in e:
                                    issues.append(f"{evt}[{i}].hooks[{j}]: missing command")
    elif isinstance(config, str):
        if "export default" not in config:
            issues.append("TypeScript plugin: missing export default")
        if "tool.execute.before" not in config and "tool.execute.after" not in config:
            issues.append("TypeScript plugin: no before/after hooks")

    return issues


# ── List ─────────────────────────────────────────────────────────────────

def _do_list(unified: dict[str, Any]) -> None:
    """Print full portability matrix."""
    hooks = unified.get("hooks", {})
    claude_spec = unified.get("claude_specific", {})
    pmap = unified.get("platform_events", {})
    events_def = unified.get("events", {})
    platforms = list(pmap.keys())

    print(f"\n{'='*60}")
    print(f"  Hook Portability Matrix")
    print(f"{'='*60}\n")

    # Portable hooks
    print(f"  {'Hook':<30} {'Block':<8} {'Platforms':<40} {'Events'}")
    print(f"  {'-'*30} {'-'*8} {'-'*40} {'-'*30}")
    for name in sorted(hooks):
        h = hooks[name]
        block = "⛔" if h.get("blocking") else "👁"
        plats = ", ".join(h.get("platforms", []))
        evts = ", ".join(h.get("events", []))
        print(f"  {name:<30} {block:<8} {plats:<40} {evts}")

    # Claude-specific
    print(f"\n  ── Claude Code Only ({len(claude_spec)} hooks) ──")
    for name in sorted(claude_spec):
        reason = claude_spec[name].get("reason", "")
        print(f"  • {name:<30} {reason}")

    # Per-platform event coverage
    print(f"\n  ── Event Support by Platform ──\n")
    for p in platforms:
        mapping = pmap.get(p, {})
        supported = [e for e, n in mapping.items() if n is not None]
        missing = [e for e, n in mapping.items() if n is None]
        p_hooks = _filter_hooks(unified, p)
        print(f"  {p:<20} {len(p_hooks)} hooks, {len(supported)}/{len(mapping)} events")
        if missing:
            print(f"  {'':<20} missing: {', '.join(missing)}")

    # Hook × Platform matrix
    print(f"\n  ── Hook × Platform Matrix ──\n")
    header = f"  {'Hook':<22} {'Block':<6}"
    for p in platforms:
        header += f" {p:<12}"
    print(header)
    print(f"  {'-'*22} {'-'*6} {'-'*12 * len(platforms)}")
    for name in sorted(hooks):
        h = hooks[name]
        block = "⛔" if h.get("blocking") else "👁"
        row = f"  {name:<22} {block:<6}"
        for p in platforms:
            if p in h.get("platforms", []):
                row += f" {'✅':<12}"
            else:
                row += f" {'❌':<12}"
        print(row)
    # Claude-specific summary row
    row = f"  {'Claude Only (' + str(len(claude_spec)) + ')':<22} {'—':<6}"
    for p in platforms:
        if p == "claude_code":
            row += f" {'✅':<12}"
        else:
            row += f" {'❌':<12}"
    print(row)

    # Detailed event × platform matrix
    print(f"\n  ── Event × Platform Matrix ──\n")
    evt_names = list(unified.get("events", {}).keys())
    # Header
    header = f"  {'Event':<20}"
    for p in platforms:
        header += f" {p:<12}"
    print(header)
    print(f"  {'-'*20} {'-'*12 * len(platforms)}")
    for evt in evt_names:
        row = f"  {evt:<20}"
        for p in platforms:
            mapping = pmap.get(p, {})
            native = mapping.get(evt)
            if native is None:
                row += f" {'❌':<12}"
            else:
                row += f" {'✅':<12}"
        print(row)

    print(f"\n  Total: {len(hooks)} portable + {len(claude_spec)} Claude-specific = {len(hooks) + len(claude_spec)} hooks\n")


# ── Validate Existing ───────────────────────────────────────────────────

def _do_validate(root: Path, adapters: list) -> int:
    """Validate previously generated config files."""
    print(f"\n{'='*60}")
    print(f"  Validating Generated Configs")
    print(f"{'='*60}\n")
    has_issues = False

    for a in adapters:
        p = a.config_path(root)
        if not p or not p.exists():
            print(f"  ⬜ {a.name}: no config file")
            continue

        suffix = p.suffix.lower()
        content = p.read_text()

        if suffix in (".json",):
            try:
                parsed = json.loads(content)
                issues = _validate_config(parsed)
            except json.JSONDecodeError as e:
                issues = [f"invalid JSON: {e}"]
        elif suffix == ".ts":
            # TypeScript plugin — validate structure directly
            issues = _validate_config(content)
        elif suffix in (".yaml", ".yml"):
            # YAML (harness.yaml) — validate structure manually
            issues = []
            if "hooks_enabled:" not in content:
                issues.append("missing hooks_enabled section")
            if "workflow:" not in content:
                issues.append("missing workflow section")
        else:
            issues = []  # unknown format, skip

        if issues:
            has_issues = True
            print(f"  ⚠️  {a.name} ({p}):")
            for i in issues:
                print(f"       - {i}")
        else:
            print(f"  ✅ {a.name} ({p}): valid")

    if has_issues:
        print(f"\n  ❌ Issues found\n")
        return 1
    print(f"\n  ✅ All configs valid\n")
    return 0


# ── Adapter Imports ─────────────────────────────────────────────────────

def _get_adapters():
    """Lazy-import adapters to avoid circular dependency at module level."""
    sys.path.insert(0, str(_HERE))
    from adapters import ADAPTERS as ADAPTERS_LIST
    return ADAPTERS_LIST


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    command = args[0]
    platform_filter: set[str] | None = None
    dry_run = False
    verbose = False

    i = 1
    while i < len(args):
        if args[i] == "--platform" and i + 1 < len(args):
            if platform_filter is None:
                platform_filter = set()
            platform_filter.add(args[i + 1])
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        else:
            i += 1

    unified = _load_unified()
    adapters = _get_adapters()
    root = PROJECT_ROOT

    if command == "detect":
        _do_detect(root, adapters, verbose)
        return 0

    elif command in ("generate", "install"):
        results = _do_generate(root, unified, adapters, platform_filter, dry_run, verbose)
        issues = [k for k, v in results.items()
                  if isinstance(v, dict) and v.get("status") == "issues"]
        if issues:
            print(f"  ⚠️  Issues on: {', '.join(issues)}\n", file=sys.stderr)
        return 0

    elif command == "validate":
        return _do_validate(root, adapters)

    elif command == "list":
        _do_list(unified)
        return 0

    else:
        print(f"❌ Unknown command: {command}", file=sys.stderr)
        print(f"   Commands: detect, generate, install, validate, list", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
