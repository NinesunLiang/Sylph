#!/bin/bash
# Verify: Rate limiter
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.middleware')
# Check the expected function exists
func = getattr(mod, 'rate_limit', None)
assert func is not None, 'rate_limit not implemented'
assert callable(func), 'rate_limit not callable'
result = func('test')
assert result == True, f'unexpected result: {result}'
print(f'PASS: 05_fuzzy_req_006 — rate_limit works correctly')
"
