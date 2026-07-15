#!/bin/bash
# Verify: Permission guard
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.middleware')
# Check the expected function exists
func = getattr(mod, 'require_auth', None)
assert func is not None, 'require_auth not implemented'
assert callable(func), 'require_auth not callable'
result = func(lambda:True)
assert result == True, f'unexpected result: {result}'
print(f'PASS: 09_high_risk_003 — require_auth works correctly')
"
