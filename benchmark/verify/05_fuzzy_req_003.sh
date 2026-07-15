#!/bin/bash
# Verify: Natural language search
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.data_processor')
# Check the expected function exists
func = getattr(mod, 'find', None)
assert func is not None, 'find not implemented'
assert callable(func), 'find not callable'
result = func([1,2,3], lambda x: x>1)
assert result == 2, f'unexpected result: {result}'
print(f'PASS: 05_fuzzy_req_003 — find works correctly')
"
