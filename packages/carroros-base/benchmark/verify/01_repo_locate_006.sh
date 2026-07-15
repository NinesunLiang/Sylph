#!/bin/bash
# Verify: Add configurable log
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.middleware')
# Check the expected function exists
func = getattr(mod, 'log_request', None)
assert func is not None, 'log_request not implemented'
assert callable(func), 'log_request not callable'
result = func(lambda d:d)
assert result == True, f'unexpected result: {result}'
print(f'PASS: 01_repo_locate_006 — log_request works correctly')
"
