#!/bin/bash
# Verify: Connection pool
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/api.py 2>/dev/null && \
  echo "PASS: 07_perf_concur_006 — api compiles" || \
  (echo "FAIL: 07_perf_concur_006" && exit 1)
