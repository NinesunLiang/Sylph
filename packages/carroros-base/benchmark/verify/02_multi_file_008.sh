#!/bin/bash
# Verify: Create logging module
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('logger')
    print(f'PASS: 02_multi_file_008 — module logger exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_008 — logger not found: {e}')
    sys.exit(1)
"
