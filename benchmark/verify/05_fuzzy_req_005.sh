#!/bin/bash
# Verify: Auto-retry decorator
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.middleware')
# Check the expected function exists
func = getattr(mod, 'retry', None)
assert func is not None, 'retry not implemented'
assert callable(func), 'retry not callable'
result = func(lambda:1, 3)
assert result == 1, f'unexpected result: {result}'
print(f'PASS: 05_fuzzy_req_005 — retry works correctly')
"
