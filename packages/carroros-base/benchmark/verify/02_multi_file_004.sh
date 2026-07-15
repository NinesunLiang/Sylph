#!/bin/bash
# Verify: Split batch into module
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('batch')
    print(f'PASS: 02_multi_file_004 — module batch exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_004 — batch not found: {e}')
    sys.exit(1)
"
