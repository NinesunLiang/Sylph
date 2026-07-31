#!/bin/bash
set -e
cd "/Users/lucas.liang/Desktop/Sylph/Carror_Base_OS_UI_WORKFLOW"

ITER_FILE=".omc/ui-autopilot/home_page/measurements/loop-iter.txt"
mkdir -p ".omc/ui-autopilot/home_page/measurements"

ITER=1
[ -f "$ITER_FILE" ] && ITER=$(($(cat "$ITER_FILE") + 1))
echo $ITER > "$ITER_FILE"

echo ""
echo "=========================================="
echo "  AUTONOMOUS LOOP #$ITER"
echo "=========================================="

# 1. Take screenshot
pnpm exec node -e "
const { chromium } = require('playwright');
const b = await chromium.launch({headless:true});
const p = await b.newPage({viewport:{width:1440,height:900}});
await p.goto('http://localhost:9001/',{timeout:10000});
await p.waitForTimeout(2000);
await p.screenshot({path:'.omc/ui-autopilot/home_page/measurements/loop-$ITER.png'});
const n = await p.evaluate(() => document.querySelectorAll('*').length);
await b.close();
console.log('Screenshot saved, DOM:', n);
" 2>&1 || echo "Screenshot failed"

# 2. Typecheck
pnpm run typecheck 2>&1 | tail -1

# 3. Log
echo "Loop #$ITER done at $(date)"
echo "----------------------------------------"
