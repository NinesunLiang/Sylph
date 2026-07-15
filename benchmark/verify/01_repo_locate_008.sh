#!/bin/bash
# Verify: Add thread safety doc
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from tests.test_calc import test_add, test_divide
test_add()
test_divide()
print('PASS: 01_repo_locate_008 — calc tests pass')
" 2>&1
