#!/usr/bin/env bash
# roi-rules-inject.sh — pretool-rules-inject ROI
set -eo pipefail
FW="$HOME/.claude/flywheel.log"
[ -f "$FW" ] || { echo "flywheel.log unavailable"; exit 0; }

${PYTHON_BIN:-python3} -c "
fw = '$FW'
rules = pg = cg = ap = 0
with open(fw) as f:
    for l in f:
        if 'pretool_rules_inject' in l: rules += 1
        elif 'permission_gate_blocked' in l: pg += 1
        elif 'completion_gate' in l: cg += 1
        elif 'anti_pattern' in l: ap += 1

cost = rules * 455
pg_save = pg * 500
cg_save = cg * 300
total_save = pg_save + cg_save

print('=== pretool-rules-inject ROI ===')
print(f'注入次数: {rules}')
print(f'预计Token成本: ~{cost} tokens')
print()
print('违规拦截:')
print(f'  permission-gate: {pg} 次 (节省 ~{pg_save} tokens)')
print(f'  completion-gate: {cg} 次 (节省 ~{cg_save} tokens)')
print(f'  anti-pattern: {ap} 次')
print()
if total_save > cost:
    print(f'净收益: +{total_save - cost} tokens (ROI {total_save * 100 // cost}%)')
else:
    print(f'净成本: -{cost - total_save} tokens')
"
