#!/bin/bash
# Verify: Rate limiting
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.middleware')
# Check the expected function exists
func = getattr(mod, 'rate_limit', None)
assert func is not None, 'rate_limit not implemented'
assert callable(func), 'rate_limit not callable'
result = func('req')
assert result == True, f'unexpected result: {result}'
print(f'PASS: 09_high_risk_005 — rate_limit works correctly')
"
