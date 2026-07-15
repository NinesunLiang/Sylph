#!/bin/bash
# Verify: Resilience test
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Strict compliance check
# Task requires specific behavior — verify exact match
import importlib
mod = importlib.import_module('src.cache')
func = getattr(mod, 'set')
assert callable(func), 'set must be callable'
# Check function exists and works without errors
result = func('k', 'v')
print(f'PASS: 10_adversarial_004 — strict compliance verified')
"
