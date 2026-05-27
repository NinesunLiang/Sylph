#!/usr/bin/env bash
set -f
echo "=== Disk Check ==="
for h in assertion-collector skeptic-role pretool-oma-path-guard skill-flywheel stop-drain harness_config feature-probe; do
  [ -f ".claude/hooks/${h}.sh" ] && echo "$h: DISK=YES" || echo "$h: DISK=NO"
done
echo ""
echo "=== Registration Check ==="
python3 -c "
import json
d=json.load(open('.claude/settings.json'))
hooks=['assertion-collector','skeptic-role','pretool-oma-path-guard','skill-flywheel','stop-drain','harness_config','feature-probe','build-validator']
for h in hooks:
    found=False
    for ev,ms in d.get('hooks',{}).items():
        for m in ms:
            for hk in m.get('hooks',[]):
                if h in hk.get('command',''):
                    found=True
                    print(f'{h}: REGISTERED (event={ev})')
    if not found:
        print(f'{h}: NOT REGISTERED')
"
