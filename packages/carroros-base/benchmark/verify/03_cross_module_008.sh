#!/bin/bash
# Verify: Event system
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('events')
    print(f'PASS: 03_cross_module_008 — module events exists')
except ImportError as e:
    print(f'FAIL: 03_cross_module_008 — events not found: {e}')
    sys.exit(1)
"
