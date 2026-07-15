#!/bin/bash
# Verify: pathlib migration
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/config.py 2>/dev/null && \
  echo "PASS: 04_migration_004 — config compiles" || \
  (echo "FAIL: 04_migration_004" && exit 1)
