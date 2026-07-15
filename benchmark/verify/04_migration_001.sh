#!/bin/bash
# Verify: Python version check
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/calc.py 2>/dev/null && \
  echo "PASS: 04_migration_001 — calc compiles" || \
  (echo "FAIL: 04_migration_001" && exit 1)
