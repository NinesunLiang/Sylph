#!/usr/bin/env bash
# fix-source-mirror-settings.sh — 修复 source/harness-kit/.claude/settings.json JSON + 注册孤儿脚本
set -euo pipefail

python3 << 'PYEOF'
import json, os

path = 'source/harness-kit/.claude/settings.json'
print(f"Fixing: {path}")

# Read raw, fix JSON
with open(path) as f:
    c = f.read()

# Fix orphaned braces (remove the extra "{" between "]" and "matcher")
import re
c = re.sub(r'\]\s*\n\s*\{\s*\n\s*"matcher"', r'],\n        "matcher"', c)

with open(path, 'w') as f:
    f.write(c)

# Verify and register orphan hooks
with open(path) as f:
    s = json.load(f)
print("JSON valid")

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
print("Done!")
PYEOF
