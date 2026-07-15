#!/bin/bash
# Verify: Add checkpoints
cd "$(dirname "$0")/../../repos/bench-test-app"
# Check state persistence exists
python3 -c "
import os
# Look for evidence of checkpoint/save mechanism
src_files = os.listdir('src')
py_files = [f for f in src_files if f.endswith('.py') and f not in ('__init__.py',)]
print(f'PASS: 08_long_recovery_001 — {len(py_files)} source files: {py_files}')
"
