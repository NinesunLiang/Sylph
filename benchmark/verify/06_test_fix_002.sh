#!/bin/bash
# Verify: Add test coverage
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_calc.py -x -q 2>&1 && \
  echo "PASS: 06_test_fix_002 — tests/test_calc.py passes" || \
  (echo "FAIL: 06_test_fix_002" && exit 1)
