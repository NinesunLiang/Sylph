#!/bin/bash
# Verify: Fix flaky test
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_data_processor.py -x -q 2>&1 && \
  echo "PASS: 06_test_fix_003 — tests/test_data_processor.py passes" || \
  (echo "FAIL: 06_test_fix_003" && exit 1)
