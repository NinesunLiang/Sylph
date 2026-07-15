#!/bin/bash
# Verify: Type annotations
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m py_compile src/data_processor.py 2>/dev/null && \
  echo "PASS: 04_migration_003 — data_processor compiles" || \
  (echo "FAIL: 04_migration_003" && exit 1)
