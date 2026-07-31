#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW"
cd "$ROOT"

STEP=${1:-"measure"}

case "$STEP" in
  # Step 1: Measure baseline
  measure)
    pnpm exec node scripts/run-autopilot-round.mjs 2>&1 | tee /tmp/autopilot-current.json
    echo "---"
    python3 -c "
import json
d = json.load(open('/tmp/autopilot-current.json'))
s = d['score']
print(f'UIF components: global={s[\"global_similarity\"]} geom={s[\"geometry\"]} color={s[\"color\"]} typo={s[\"typography\"]} layout={s[\"layout\"]} token={s[\"token_align\"]}')
print(f'Elements: proto={d[\"proto\"][\"elements\"]} impl={d[\"impl\"][\"elements\"]}')
"
    ;;

  # Step 2: Apply consolidated fixes
  fix-all)
    echo "=== Consolidating implementation fixes ==="

    # 1. Fix sidebar icon sizing (prototype: 44x44 buttons, 24x24 icons)
    pnpm exec node -e "
import { readFileSync, writeFileSync } from 'fs';
let s = readFileSync('src/layouts/AppLayout.module.scss', 'utf8');
s = s.replace(/width: 48px;\n  height: 48px;/g, 'width: 44px;\n  height: 44px;');
s = s.replace(/gap: \$spacing-1;/g, 'gap: 8px;');
s = s.replace(/padding: \$spacing-3 0;/g, 'padding: 12px 0;');
s = s.replace(/font-size: 20px;/g, 'font-size: 22px;');
s = s.replace(/font-size: 10px;/g, 'font-size: 11px;');
writeFileSync('src/layouts/AppLayout.module.scss', s);
console.log('Updated AppLayout.module.scss');
"

    # 2. Verify typecheck
    pnpm run typecheck && echo "✅ typecheck OK"
    echo "=== All fixes applied ==="
    ;;

  # Step 3: Full iteration loop
  loop)
    echo "=== Autopilot iteration ==="

    # Measure
    pnpm exec node scripts/run-autopilot-round.mjs > /tmp/autopilot-out.json 2>&1
    SCORE=$(python3 -c "import json; print(json.load(open('/tmp/autopilot-out.json'))['score']['global_similarity'])")
    echo "Iteration score: $SCORE"

    # Apply fixes
    bash "$0" fix-all

    # Typecheck
    pnpm run typecheck 2>&1 | tail -1

    echo "=== Iteration complete ==="
    ;;

  *)
    echo "Usage: $0 {measure|fix-all|loop}"
    ;;
esac
