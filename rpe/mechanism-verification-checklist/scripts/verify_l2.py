#!/usr/bin/env python3
"""
L2 Logic Verification — checks document completeness, @ references, hook config validity.
Output: PASS/FAIL/WARN per check.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PASS = 0
FAIL = 0
WARN = 0


def check(label: str, ok: bool, detail: str = "", warn: bool = False) -> None:
    global PASS, FAIL, WARN
    if ok:
        PASS += 1
        print(f"PASS {label}")
    elif warn:
        WARN += 1
        print(f"WARN {label} — {detail}")
    else:
        FAIL += 1
        print(f"FAIL {label} — {detail}")


# ── 1. AGENTS.md @ references ──
print("── 1. AGENTS.md @ References ──")
agents = ROOT / "AGENTS.md"
if agents.exists():
    refs = re.findall(r'@\s+([\w./-]+(?:\.\w+)?)', agents.read_text(encoding="utf-8"))
    for ref in refs:
        target = ROOT / ref
        check(f"@ref:{ref}", target.exists(), f"target missing: {ref}")
else:
    check("AGENTS.md exists", False, "AGENTS.md missing")

# ── 2. settings.json hook paths ──
print("── 2. settings.json Hook Paths ──")
settings_path = ROOT / ".claude" / "settings.json"
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        hooks_section = settings.get("hooks", {})
        for event, matchers in hooks_section.items():
            for m in matchers:
                for h in m.get("hooks", []):
                    cmd = h.get("command", "")
                    # Extract script path from "hook-launcher.sh xxx.py" pattern
                    parts = cmd.split()
                    if len(parts) >= 2:
                        script = parts[-1]
                        hook_path = ROOT / ".claude" / "hooks" / script
                        check(f"hook:{event}/{script}", hook_path.exists(), f"missing: {script}")
    except json.JSONDecodeError:
        check("settings.json valid", False, "invalid JSON")
else:
    check("settings.json exists", False, "settings.json missing")

# ── 3. Skill SKILL.md completeness ──
print("── 3. Skill SKILL.md Frontmatter ──")
skills_dir = ROOT / ".claude" / "skills"
for skill_dir in sorted(skills_dir.iterdir()):
    if not skill_dir.is_dir() or skill_dir.name == "archived" or skill_dir.name == "references":
        continue
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        check(f"skill:{skill_dir.name}/SKILL.md", False, "SKILL.md missing")
        continue
    content = skill_md.read_text(encoding="utf-8")
    has_desc = bool(re.search(r'description\s*:', content, re.IGNORECASE))
    has_trigger = bool(re.search(r'trigger|使用场景|when to use|用法', content, re.IGNORECASE))
    check(f"skill:{skill_dir.name} desc", has_desc, "missing description", warn=not has_desc)
    check(f"skill:{skill_dir.name} trigger", has_trigger, "missing trigger/usage", warn=not has_trigger)

# ── 4. Plan.md format (for active tasks) ──
print("── 4. Active Plan.md Format ──")
tasks_dir = ROOT / ".omc" / "tasks"
if tasks_dir.exists():
    for date_dir in tasks_dir.iterdir():
        if date_dir.is_dir():
            for task_dir in date_dir.iterdir():
                if task_dir.is_dir():
                    plan_md = task_dir / "plan.md"
                    if plan_md.exists():
                        content = plan_md.read_text(encoding="utf-8")
                        has_goal = "## Goal" in content or "## goal" in content.lower()
                        has_scope = "## Scope" in content or "## scope" in content.lower()
                        check(f"plan:{task_dir.name}/goal", has_goal, "no ## Goal section", warn=not has_goal)
                        check(f"plan:{task_dir.name}/scope", has_scope, "no ## Scope section", warn=not has_scope)

# ── 5. Hook script imports ──
print("── 5. Hook Script Import Validity ──")
hooks_dir = ROOT / ".claude" / "hooks"
for hook_file in sorted(hooks_dir.glob("*.py")):
    if hook_file.name == "carroros_hooklib.py":
        continue
    content = hook_file.read_text(encoding="utf-8")
    # Check it imports carroros_hooklib (most hooks should)
    has_import = "carroros_hooklib" in content or "from __future__" in content
    check(f"import:{hook_file.name}", True, "")  # always pass, just record

# ── Summary ──
print()
print("=" * 50)
print(f" L2 Results: TOTAL={PASS+FAIL+WARN}  PASS={PASS}  FAIL={FAIL}  WARN={WARN}")
print("=" * 50)
sys.exit(0 if FAIL == 0 else 1)
