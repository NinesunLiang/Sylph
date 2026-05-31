#!/usr/bin/env python3
"""Fix source/harness-kit/.claude/settings.json — 完整重建"""
import json, sys, re

path = 'source/harness-kit/.claude/settings.json'
print(f"Reading: {path}")

with open(path) as f:
    raw = f.read()

# The core issue: "PreToolUse": [ is followed by "matcher" without "{"
# This means the entire hooks structure is shifted by 1 level
# Fix: add missing "{" before every "matcher" that follows "[" or "]"

# Fix 1: "[\n      \"matcher\"" -> "[\n      {\n        \"matcher\""
raw = re.sub(r'\[\s*\n(\s*)"matcher"', r'[\n\1{\n\1  "matcher"', raw)

# Fix 2: "],\n      \"matcher\"" -> "],\n      {\n        \"matcher\""
raw = re.sub(r'],\s*\n(\s*)"matcher"', r'],\n\1{\n\1  "matcher"', raw)

# Fix 3: Remove orphaned "{" after "],"
raw = re.sub(r'],\s*\n\s*\{\s*\n\s*\{', r'],\n    {', raw)

# Fix 4: Remove trailing commas before "}"
raw = re.sub(r',(\s*\n\s*)}', r'\1}', raw)

# Fix 5: Add missing comma after "}" before next key
raw = re.sub(r'}(\s*\n\s*)"(?!\s*[}\]])', r'},\1"', raw)

with open(path, 'w') as f:
    f.write(raw)

# Verify
try:
    with open(path) as f:
        s = json.load(f)
    print("JSON valid ✓")
except json.JSONDecodeError as e:
    print(f"JSON still invalid at line {e.lineno}: {e.msg}")
    lines = raw.split('\n')
    start = max(0, e.lineno - 2)
    end = min(len(lines), e.lineno + 3)
    for i in range(start, end):
        marker = " >>>" if i + 1 == e.lineno else "    "
        print(f"{marker} {i+1}: {lines[i]}")
    sys.exit(1)

# Register orphan hooks
ss = s.get('SessionStart', [])
for name, file in [('lsp-gate', 'lsp-gate.sh'), ('oracle-gate', 'oracle-gate.sh')]:
    if not any(file in str(h) for h in ss):
        ss.append({"hooks": [{"type": "command", "command": f"bash .claude/hooks/{file}", "timeout": 3000}]})
        print(f"  Registered {file}")
s['SessionStart'] = ss

pt = s.get('PostToolUse', [])
if not any('posttool-read-cite.sh' in str(h) for h in pt):
    pt.append({"hooks": [{"type": "command", "command": "bash .claude/hooks/posttool-read-cite.sh", "timeout": 3000}]})
    print("  Registered posttool-read-cite.sh")
s['PostToolUse'] = pt

with open(path, 'w') as f:
    json.dump(s, f, indent=2, ensure_ascii=False)
print(f"✅ Done")
