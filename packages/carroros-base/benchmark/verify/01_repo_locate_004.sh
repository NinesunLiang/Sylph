#!/bin/bash
# Verify: Add input validation
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -m pytest tests/test_data_processor.py -x -q 2>&1 && \
  echo "PASS: 01_repo_locate_004 — tests/test_data_processor.py passes" || \
  (echo "FAIL: 01_repo_locate_004" && exit 1)
