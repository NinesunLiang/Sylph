#!/bin/bash
# Verify: Cross-validation
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('validator')
    print(f'PASS: 03_cross_module_007 — module validator exists')
except ImportError as e:
    print(f'FAIL: 03_cross_module_007 — validator not found: {e}')
    sys.exit(1)
"
