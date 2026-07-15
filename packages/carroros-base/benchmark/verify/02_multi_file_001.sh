#!/bin/bash
# Verify: Extract sqrt
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check new file exists
python3 -c "
import importlib, sys
try:
    mod = importlib.import_module('math_utils')
    print(f'PASS: 02_multi_file_001 — module math_utils exists')
except ImportError as e:
    print(f'FAIL: 02_multi_file_001 — math_utils not found: {e}')
    sys.exit(1)
"
