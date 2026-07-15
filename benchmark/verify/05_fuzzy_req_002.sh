#!/bin/bash
# Verify: Add help text
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/calc.py 2>/dev/null && \
  echo "PASS: 05_fuzzy_req_002 — calc compiles" || \
  (echo "FAIL: 05_fuzzy_req_002" && exit 1)
