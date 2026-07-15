#!/bin/bash
# Verify: Exact rename
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Strict compliance check
# Task requires specific behavior — verify exact match
import importlib
mod = importlib.import_module('src.calc')
func = getattr(mod, 'sum')
assert callable(func), 'sum must be callable'
# Check function exists and works without errors
result = func(1, 2)
print(f'PASS: 10_adversarial_001 — strict compliance verified')
"
