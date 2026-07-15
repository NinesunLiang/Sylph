#!/bin/bash
# Verify: Extract routes
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('routes')
    print(f'PASS: 02_multi_file_006 — module routes exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_006 — routes not found: {e}')
    sys.exit(1)
"
