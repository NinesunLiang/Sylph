#!/bin/bash
# one-shot: register terminal-safety hook
set -e

# harness.yaml
python3 -c "
l=open('.claude/harness.yaml').readlines()
for i,x in enumerate(l):
    if 'pretool_sensitive_edit: true' in x:
        l.insert(i+1, '  pretool_terminal_safety: true\n'); break
open('.claude/harness.yaml','w').writelines(l)
"

# settings.json
python3 -c "
import json,os
R=os.getcwd()
s=json.load(open('.claude/settings.json'))
s['hooks']['PreToolUse'].append({
    'matcher': 'Bash',
    'hooks': [{
        'type': 'command',
        'command': f'bash {R}/.claude/hooks/pretool-terminal-safety.sh',
        'timeout': 3000
    }]
})
json.dump(s, open('.claude/settings.json','w'), indent=2, ensure_ascii=False)
"

echo 'terminal-safety registered'
grep pretool_terminal_safety .claude/harness.yaml
