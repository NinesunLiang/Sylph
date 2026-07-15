#!/bin/bash
# Verify: Transaction log
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('transaction')
    print(f'PASS: 08_long_recovery_005 — module transaction exists')
except ImportError as e:
    print(f'FAIL: 08_long_recovery_005 — transaction not found: {e}')
    sys.exit(1)
"
