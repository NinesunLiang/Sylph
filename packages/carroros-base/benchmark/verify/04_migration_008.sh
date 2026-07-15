#!/bin/bash
# Verify: Enum migration
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/config.py 2>/dev/null && \
  echo "PASS: 04_migration_008 — config compiles" || \
  (echo "FAIL: 04_migration_008" && exit 1)
