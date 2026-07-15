#!/bin/bash
# Verify: Integration test
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_integration.py -x -q 2>&1 && \
  echo "PASS: 06_test_fix_006 — tests/test_integration.py passes" || \
  (echo "FAIL: 06_test_fix_006" && exit 1)
