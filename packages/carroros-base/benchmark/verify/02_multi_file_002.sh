#!/bin/bash
# Verify: Move factorial
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('factorial')
    print(f'PASS: 02_multi_file_002 — module factorial exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_002 — factorial not found: {e}')
    sys.exit(1)
"
