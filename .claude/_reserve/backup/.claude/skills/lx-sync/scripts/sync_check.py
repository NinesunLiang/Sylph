#!/usr/bin/env python3
"""lx-sync: Post-change consistency checker for Carror OS skills & config.

Checks:
  1. SKILL.md frontmatter ↔ feature-registry description drift
  2. Source mirror consistency (root vs source/)
  3. harness_version vs VERSION file
  4. Duplicate frontmatter keys (e.g. triggers defined twice)
  5. Referenced nodes/schemas existence
  6. skill-dependencies.yaml version alignment

Usage: python3 sync_check.py [--json] [--skill <name>]
Exit:  0 = clean, 1 = drift found, 2 = error
"""

import json, os, sys, re, yaml
from pathlib import Path
from datetime import datetime

PROJECT = Path(os.environ.get('CLAUDE_PROJECT_DIR', Path.cwd()))
SKILLS_DIR = PROJECT / '.claude' / 'skills'
SOURCE_SKILLS = PROJECT / 'source' / 'lx-skills-v5' / '.claude' / 'skills'
REGISTRY = PROJECT / '.claude' / 'feature-registry.yaml'
VERSION_FILE = PROJECT / 'VERSION.json'
DEPS_FILE = SKILLS_DIR / 'skill-dependencies.yaml'
NODES_DIR = PROJECT / '.claude' / 'nodes'
SCHEMAS_DIR = PROJECT / '.claude' / 'schemas'
TASK_SYS_DIR = PROJECT / '.claude' / 'task_sys'


def parse_frontmatter(text):
    """Extract YAML frontmatter from markdown."""
    if not text.startswith('---'):
        return {}
    end = text.find('---', 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except Exception:
        return {}



def safe_str(val):
    """Convert YAML value to string, handling None/null."""
    return str(val) if val is not None else ''

def read_file(path):
    try:
        return Path(path).read_text()
    except Exception:
        return None


def load_registry_skills():
    """Return dict of skill_name -> {description, enabled_by_default, ...} from feature-registry."""
    text = read_file(REGISTRY)
    if not text:
        return {}
    try:
        data = yaml.safe_load(text) or {}
    except Exception:
        return {}
    skills = {}
    for s in data.get('skills', []):
        if 'name' in s:
            skills[s['name']] = s
    return skills


class SyncCheck:
    def __init__(self, skill_filter=None, json_output=False):
        self.skill_filter = skill_filter
        self.json_output = json_output
        self.issues = []
        self.passes = []
        self.skill_dirs = []
        self._find_skills()

    def _find_skills(self):
        if not SKILLS_DIR.is_dir():
            return
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and d.name.startswith('lx-'):
                if self.skill_filter and d.name != self.skill_filter:
                    continue
                skill_md = d / 'SKILL.md'
                if skill_md.exists():
                    self.skill_dirs.append(d)

    def add(self, level, check, skill, detail):
        entry = {'level': level, 'check': check, 'skill': skill, 'detail': detail}
        if level == 'PASS':
            self.passes.append(entry)
        else:
            self.issues.append(entry)

    # ── Check 1: frontmatter ↔ registry description drift ──
    def check_registry_drift(self):
        registry = load_registry_skills()
        for d in self.skill_dirs:
            name = d.name
            text = read_file(d / 'SKILL.md')
            if not text:
                self.add('WARN', 'registry-drift', name, 'SKILL.md not readable')
                continue
            fm = parse_frontmatter(text)
            fm_desc = safe_str(fm.get('description', ''))
            fm_role = safe_str(fm.get('role', ''))
            if name not in registry:
                self.add('WARN', 'registry-drift', name, 'not registered in feature-registry.yaml')
                continue
            reg_desc = safe_str(registry[name].get('description', ''))

            issues = []
            # Check 1: Language-agnostic claim vs Go-specific text in frontmatter
            if '语言无关' in reg_desc or 'Language-agnostic' in reg_desc:
                go_patterns = ['Go code', 'for Go', 'Go 代码']
                for pat in go_patterns:
                    if pat in fm_desc or pat in fm_role:
                        issues.append(f'Registry says language-agnostic but SKILL.md says "{pat}"')

            # Check 2: Language-agnostic claim vs language-specific text
            lang_specific = ['Go code', 'Go 代码', 'Go 测试', 'Go project']
            if any(kw in fm_desc for kw in lang_specific) and ('语言无关' in reg_desc or 'Language-agnostic' in reg_desc):
                issues.append('Registry language-agnostic but SKILL.md language-specific')

            if issues:
                self.add('FAIL', 'registry-drift', name, '; '.join(issues))
            else:
                self.add('PASS', 'registry-drift', name, 'frontmatter ↔ registry aligned')

        # Reverse check: orphaned registry entries (no SKILL.md on disk)
        disk_skills = {d.name for d in self.skill_dirs}
        for name in registry:
            if name not in disk_skills:
                self.add('WARN', 'registry-drift', name, 'registered in registry but no SKILL.md on disk')

    # ── Check 2: Source mirror consistency ──
    def check_source_mirror(self):
        if not SOURCE_SKILLS.is_dir():
            self.add('WARN', 'source-mirror', 'all', f'source mirror dir missing: {SOURCE_SKILLS}')
            return
        for d in self.skill_dirs:
            name = d.name
            root_md = d / 'SKILL.md'
            src_md = SOURCE_SKILLS / name / 'SKILL.md'
            if not src_md.exists():
                self.add('FAIL', 'source-mirror', name, f'missing in source mirror: {src_md}')
                continue
            root_text = read_file(root_md)
            src_text = read_file(src_md)
            if root_text != src_text:
                self.add('FAIL', 'source-mirror', name, 'SKILL.md differs from source mirror')
            else:
                self.add('PASS', 'source-mirror', name, 'mirror in sync')

    # ── Check 3: harness_version vs VERSION ──
    def check_versions(self):
        current_ver = None
        if VERSION_FILE.exists():
            try:
                data = json.loads(read_file(VERSION_FILE))
                current_ver = data.get('version', '').strip()
            except Exception:
                current_ver = read_file(VERSION_FILE).strip()
        if not current_ver:
            self.add('WARN', 'version', 'all', 'VERSION.json missing or version field empty')
            current_ver = 'unknown'

        for d in self.skill_dirs:
            text = read_file(d / 'SKILL.md')
            if not text:
                continue
            fm = parse_frontmatter(text)
            hv = safe_str(fm.get('harness_version', ''))
            if not hv:
                self.add('WARN', 'version', d.name, 'missing harness_version field')
                continue
            # Skills with >=X.Y.Z are permissive — fine
            if hv.startswith('>='):
                self.add('PASS', 'version', d.name, f'permissive: {hv}')
                continue
            # Skills with exact version should match VERSION
            if not hv.startswith('>='):
                if hv != current_ver:
                    self.add('FAIL', 'version', d.name,
                             f'harness_version={hv} but VERSION={current_ver}')
                else:
                    self.add('PASS', 'version', d.name, f'aligned: {hv}')

    # ── Check 4: Duplicate frontmatter keys ──
    def check_duplicate_keys(self):
        for d in self.skill_dirs:
            text = read_file(d / 'SKILL.md')
            if not text:
                continue
            # Find frontmatter section
            if not text.startswith('---'):
                continue
            end = text.find('---', 3)
            if end == -1:
                continue
            fm_text = text[3:end]
            # Check for duplicate keys by counting occurrences
            lines = fm_text.strip().split('\n')
            keys_seen = {}
            has_duplicate = False
            for line_num, line in enumerate(lines):
                line = line.strip()
                if ':' not in line:
                    continue
                # Skip YAML list items (e.g. "- value:with:colons")
                if line.startswith('- ') or line == '-':
                    continue
                key = line.split(':')[0].strip()
                if not key or key.startswith('#'):
                    continue
                if key in keys_seen:
                    has_duplicate = True
                    self.add('FAIL', 'duplicate-key', d.name,
                             f"Duplicate frontmatter key '{key}' at lines ~{keys_seen[key]} and ~{line_num}")
                else:
                    keys_seen[key] = line_num
            if not has_duplicate:
                self.add('PASS', 'duplicate-key', d.name, 'no duplicate keys')

    # ── Check 5: Referenced nodes/schemas existence ──
    def check_references(self):
        for d in self.skill_dirs:
            text = read_file(d / 'SKILL.md')
            if not text:
                continue
            missing = []
            # Check node references (../../nodes/xxx.md)
            node_refs = re.findall(r'\.\./\.\./nodes/(\w+\.md)', text)
            for ref in set(node_refs):
                if not (NODES_DIR / ref).exists():
                    missing.append(f'nodes/{ref}')
            # Check schema references
            schema_refs = re.findall(r'\.\./\.\./schemas/([\w/]+\.yaml)', text)
            for ref in set(schema_refs):
                if not (SCHEMAS_DIR / ref).exists():
                    missing.append(f'schemas/{ref}')
            # Check task_sys references
            task_refs = re.findall(r'\.\./\.\./task_sys/(\w+\.md)', text)
            for ref in set(task_refs):
                if not (TASK_SYS_DIR / ref).exists():
                    missing.append(f'task_sys/{ref}')

            if missing:
                self.add('FAIL', 'references', d.name, f'missing: {", ".join(missing)}')
            elif node_refs or schema_refs or task_refs:
                self.add('PASS', 'references', d.name, 'all references resolve')

    # ── Check 6: skill-dependencies.yaml version alignment ──
    def check_deps_versions(self):
        deps_text = read_file(DEPS_FILE)
        if not deps_text:
            return
        try:
            deps = yaml.safe_load(deps_text) or {}
        except Exception:
            return
        dep_skills = {s['id']: s.get('version', '') for s in deps.get('skills', [])}

        for d in self.skill_dirs:
            name = d.name
            if name not in dep_skills:
                continue
            text = read_file(d / 'SKILL.md')
            if not text:
                continue
            fm = parse_frontmatter(text)
            fm_ver = safe_str(fm.get('version', ''))
            dep_ver = dep_skills[name]
            if fm_ver != dep_ver:
                self.add('WARN', 'deps-version', name,
                         f'SKILL.md version={fm_ver} but skill-dependencies.yaml={dep_ver}')
            else:
                self.add('PASS', 'deps-version', name, f'aligned: {fm_ver}')

    def run_all(self):
        self.check_registry_drift()
        self.check_source_mirror()
        self.check_versions()
        self.check_duplicate_keys()
        self.check_references()
        self.check_deps_versions()

    def report(self):
        fails = [i for i in self.issues if i['level'] == 'FAIL']
        warns = [i for i in self.issues if i['level'] == 'WARN']

        if self.json_output:
            result = {
                'timestamp': datetime.now().isoformat(),
                'summary': {'pass': len(self.passes), 'fail': len(fails), 'warn': len(warns)},
                'fails': fails,
                'warnings': warns,
                'passes': self.passes,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1 if fails else 0

        # Human-readable output
        print()
        print("=" * 60)
        print("  lx-sync — Consistency Check")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        for check_name in ['registry-drift', 'source-mirror', 'version', 'duplicate-key', 'references', 'deps-version']:
            items = [i for i in self.issues if i['check'] == check_name] + \
                    [i for i in self.passes if i['check'] == check_name]
            if not items:
                continue
            fails_here = sum(1 for i in items if i['level'] == 'FAIL')
            warns_here = sum(1 for i in items if i['level'] == 'WARN')
            icon = '✅' if fails_here == 0 and warns_here == 0 else ('⚠️' if fails_here == 0 else '❌')
            print(f"\n  {icon} {check_name} ({len(items)} skills)")
            for i in items:
                if i['level'] != 'PASS':
                    tag = 'FAIL' if i['level'] == 'FAIL' else 'WARN'
                    print(f"     [{tag}] {i['skill']}: {i['detail']}")

        print(f"\n{'=' * 60}")
        print(f"  Result: {len(fails)} FAIL, {len(warns)} WARN, {len(self.passes)} PASS")
        print(f"{'=' * 60}\n")

        return 1 if fails else 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--skill', type=str, default='')
    args = parser.parse_args()

    checker = SyncCheck(skill_filter=args.skill, json_output=args.json)
    checker.run_all()
    sys.exit(checker.report())
