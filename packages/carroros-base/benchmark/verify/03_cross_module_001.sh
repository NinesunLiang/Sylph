#!/bin/bash
# Verify: Fix circular import
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from tests.test_calc import test_add, test_divide
test_add()
test_divide()
print('PASS: 03_cross_module_001 — calc tests pass')
" 2>&1
