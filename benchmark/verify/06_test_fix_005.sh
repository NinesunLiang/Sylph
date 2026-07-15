#!/bin/bash
# Verify: Test isolation fix
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_api.py -x -q 2>&1 && \
  echo "PASS: 06_test_fix_005 — tests/test_api.py passes" || \
  (echo "FAIL: 06_test_fix_005" && exit 1)
