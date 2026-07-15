#!/bin/bash
# Verify: Save/resume batch
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('checkpoint')
    print(f'PASS: 08_long_recovery_003 — module checkpoint exists')
except ImportError as e:
    print(f'FAIL: 08_long_recovery_003 — checkpoint not found: {e}')
    sys.exit(1)
"
