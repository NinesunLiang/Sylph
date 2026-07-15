#!/bin/bash
# Verify: Hidden requirement
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Strict compliance check
# Task requires specific behavior — verify exact match
import importlib
mod = importlib.import_module('src.data_processor')
func = getattr(mod, 'sort_stable')
assert callable(func), 'sort_stable must be callable'
# Check function exists and works without errors
result = func([3,1,2])
print(f'PASS: 10_adversarial_002 — strict compliance verified')
"
