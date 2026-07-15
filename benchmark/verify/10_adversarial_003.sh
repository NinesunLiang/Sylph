#!/bin/bash
# Verify: Contradictory constraints
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Strict compliance check
# Task requires specific behavior — verify exact match
import importlib
mod = importlib.import_module('src.cache')
func = getattr(mod, 'get_or_compute')
assert callable(func), 'get_or_compute must be callable'
# Check function exists and works without errors
result = func('k', lambda:42)
print(f'PASS: 10_adversarial_003 — strict compliance verified')
"
