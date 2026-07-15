#!/bin/bash
# Verify: Add version info
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.calc')
# Check the expected function exists
func = getattr(mod, 'get_version', None)
assert func is not None, 'get_version not implemented'
assert callable(func), 'get_version not callable'
result = func()
assert result == '1.0.0', f'unexpected result: {result}'
print(f'PASS: 05_fuzzy_req_001 — get_version works correctly')
"
