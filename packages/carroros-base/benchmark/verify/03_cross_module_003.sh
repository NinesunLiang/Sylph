#!/bin/bash
# Verify: Shared exceptions
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('exceptions')
    print(f'PASS: 03_cross_module_003 — module exceptions exists')
except ImportError as e:
    print(f'FAIL: 03_cross_module_003 — exceptions not found: {e}')
    sys.exit(1)
"
