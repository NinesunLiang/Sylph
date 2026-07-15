#!/bin/bash
# Verify: Fix state race
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_state.py -x -q 2>&1 && \
  echo "PASS: 07_perf_concur_008 — tests/test_state.py passes" || \
  (echo "FAIL: 07_perf_concur_008" && exit 1)
