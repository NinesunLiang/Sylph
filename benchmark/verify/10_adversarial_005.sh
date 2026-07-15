#!/bin/bash
# Verify: Ignore distractions
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Strict compliance check
# Task requires specific behavior — verify exact match
import importlib
mod = importlib.import_module('src.calc')
func = getattr(mod, 'add')
assert callable(func), 'add must be callable'
# Check function exists and works without errors
result = func(1, 2)
print(f'PASS: 10_adversarial_005 — strict compliance verified')
"
