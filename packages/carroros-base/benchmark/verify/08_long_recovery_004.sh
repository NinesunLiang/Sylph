#!/bin/bash
# Verify: Session persistence
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('persistence')
    print(f'PASS: 08_long_recovery_004 — module persistence exists')
except ImportError as e:
    print(f'FAIL: 08_long_recovery_004 — persistence not found: {e}')
    sys.exit(1)
"
