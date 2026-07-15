#!/bin/bash
# Verify: Race condition test
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_cache.py -x -q 2>&1 && \
  echo "PASS: 06_test_fix_008 — tests/test_cache.py passes" || \
  (echo "FAIL: 06_test_fix_008" && exit 1)
