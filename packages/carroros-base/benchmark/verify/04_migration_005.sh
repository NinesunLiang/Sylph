#!/bin/bash
# Verify: Async migration
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/api.py 2>/dev/null && \
  echo "PASS: 04_migration_005 — api compiles" || \
  (echo "FAIL: 04_migration_005" && exit 1)
