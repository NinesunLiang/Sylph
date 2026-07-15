#!/bin/bash
# Verify: Fix power negative exp
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from tests.test_calc import test_add, test_divide
test_add()
test_divide()
print('PASS: 01_repo_locate_003 — calc tests pass')
" 2>&1
