#!/bin/bash
# Verify: Context manager
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/state_manager.py 2>/dev/null && \
  echo "PASS: 04_migration_007 — state_manager compiles" || \
  (echo "FAIL: 04_migration_007" && exit 1)
