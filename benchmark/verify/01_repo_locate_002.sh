#!/bin/bash
# Verify: Fix factorial negative
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from tests.test_calc import test_add, test_divide
test_add()
test_divide()
print('PASS: 01_repo_locate_002 — calc tests pass')
" 2>&1
