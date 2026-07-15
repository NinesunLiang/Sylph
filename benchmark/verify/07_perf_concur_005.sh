#!/bin/bash
# Verify: Thread-safe cache
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_cache.py -x -q 2>&1 && \
  echo "PASS: 07_perf_concur_005 — tests/test_cache.py passes" || \
  (echo "FAIL: 07_perf_concur_005" && exit 1)
