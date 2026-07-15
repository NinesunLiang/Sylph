#!/bin/bash
# Verify: Security audit
cd "$(dirname "$0")/../.."
python3 -m pytest tests/ -x -q 2>/dev/null && echo "PASS: tests pass" || echo "FAIL: tests failed"
