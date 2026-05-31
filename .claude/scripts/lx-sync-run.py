#!/usr/bin/env python3
"""lx-sync: 全量一致性检查 — feature registry drift, source mirror, version alignment, duplicate keys, reference integrity"""

import os, json, re, sys

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
errors = []
warnings = []

def p(msg): print(msg)

# ─── 1. Feature registry drift ───
reg_path = os.path.join(PROJECT, ".claude", "feature-registry.yaml")
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

hooks_dir = os.path.join(PROJECT, ".claude", "hooks")
disk_hooks = {f for f in os.listdir(hooks_dir) if f.endswith('.sh') or f.endswith('.py')}
disk_hooks -= {'__pycache__'}

settings_path = os.path.join(PROJECT, ".claude", "settings.json")
with open(settings_path) as f:
    settings = json.load(f)

refs = set()
for event_name, event in settings.get('hooks', {}).items():
    for group in event:
        for hook in group.get('hooks', []):
            cmd = hook.get('command', '')
            fname = cmd.split('/')[-1] if '/' in cmd else cmd
            refs.add(fname)

p("=== Feature Registry ===")
if HAS_YAML and os.path.exists(reg_path):
    with open(reg_path) as f:
        registry = yaml.safe_load(f)

    # Registry uses 'hooks' array (not 'features' dict)
    hooks_list = registry.get('hooks', [])
    p(f"  Registry entries: {len(hooks_list)}")

    # Extract script filenames from registry entries
    reg_scripts = set()
    for entry in hooks_list:
        script = entry.get('script', '')
        if script:
            reg_scripts.add(script.split('/')[-1])
        # Also match by name convention: registry name -> hook script name
        name = entry.get('name', '')
        if name:
            # Registry uses camelCase (e.g., preTool-edit-scope), convert to hyphen case
            reg_scripts.add(f"{name}.sh")
            reg_scripts.add(f"{name}.py")

    unregistered = disk_hooks - reg_scripts - {'harness_config.sh', 'agentic-ui.sh'}
    if unregistered:
        p(f"  ⚠️ {len(unregistered)} hooks not in feature registry:")
        for f in sorted(unregistered):
            p(f"    - {f}")
    else:
        p("  ✅ All hooks registered in feature registry")
else:
    p("  ⚠️ yaml not available or feature-registry.yaml not found")

# ─── 2. Source mirror sync ───
p("\n=== Source Mirror ===")
source_dir = os.path.join(PROJECT, "source")
mirror_hooks = os.path.join(source_dir, "harness-kit", ".claude", "hooks")
if os.path.exists(mirror_hooks):
    mirror_files = {f for f in os.listdir(mirror_hooks) if f.endswith('.sh') or f.endswith('.py')}
    main_files = {f for f in os.listdir(hooks_dir) if f.endswith('.sh') or f.endswith('.py')}
    main_files -= {'__pycache__'}

    missing_in_mirror = main_files - mirror_files
    extra_in_mirror = mirror_files - main_files
    if missing_in_mirror:
        p(f"  ⚠️ {len(missing_in_mirror)} hooks in main but not in mirror: {sorted(missing_in_mirror)}")
    if extra_in_mirror:
        p(f"  ⚠️ {len(extra_in_mirror)} hooks in mirror but not in main: {sorted(extra_in_mirror)}")
    if not missing_in_mirror and not extra_in_mirror:
        p("  ✅ Main ↔ Mirror in sync")
    else:
        p(f"  Main: {len(main_files)}, Mirror: {len(mirror_files)}")
else:
    p("  ⚠️ source/harness-kit/.claude/hooks not found")

# ─── 3. Version alignment ───
p("\n=== Version ===")
version_path = os.path.join(PROJECT, "VERSION.json")
if os.path.exists(version_path):
    with open(version_path) as f:
        ver = json.load(f)
    p(f"  VERSION.json: {ver.get('version', '?')}")

# ─── 4. Duplicate hook check ───
p("\n=== Duplicate Hooks ===")
hook_counts = {}
for event_name, event in settings.get('hooks', {}).items():
    for group in event:
        for hook in group.get('hooks', []):
            cmd = hook.get('command', '')
            fname = cmd.split('/')[-1] if '/' in cmd else cmd
            key = f"{event_name}:{fname}"
            hook_counts[key] = hook_counts.get(key, 0) + 1

dupes = {k: v for k, v in hook_counts.items() if v > 1}
if dupes:
    for k, v in sorted(dupes.items()):
        p(f"  ⚠️ Duplicate: {k} appears {v} times")
else:
    p("  ✅ No duplicate hook registrations")

# ─── 5. Reference integrity ───
p("\n=== Reference Integrity ===")
skills_dir = os.path.join(PROJECT, ".claude", "skills")
skill_dirs = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and d.startswith('lx-')]
missing_skill_md = [d for d in skill_dirs if not os.path.exists(os.path.join(skills_dir, d, "SKILL.md"))]
if missing_skill_md:
    p(f"  ⚠️ Skills without SKILL.md: {missing_skill_md}")
else:
    p(f"  ✅ All {len(skill_dirs)} skills have SKILL.md")

# All refs exist on disk
missing_refs = refs - disk_hooks
if missing_refs:
    p(f"  ⚠️ Referenced scripts not on disk: {missing_refs}")
else:
    p(f"  ✅ All {len(refs)} referenced scripts exist on disk")

# ─── Summary ───
p(f"\n{'='*50}")
p(f"lx-sync complete: {len(errors)} errors, {len(warnings)} warnings")
for e in errors:
    p(f"  ❌ {e}")
for w in warnings:
    p(f"  ⚠️ {w}")

sys.exit(1 if errors else 0)
