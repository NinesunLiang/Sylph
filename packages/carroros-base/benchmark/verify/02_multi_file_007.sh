#!/bin/bash
# Verify: Add cache persistence
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('cache')
    print(f'PASS: 02_multi_file_007 — module cache exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_007 — cache not found: {e}')
    sys.exit(1)
"
