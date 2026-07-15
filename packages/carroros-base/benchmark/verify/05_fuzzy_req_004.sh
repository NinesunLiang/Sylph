#!/bin/bash
# Verify: Sort and dedupe
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.data_processor')
# Check the expected function exists
func = getattr(mod, 'unique_sorted', None)
assert func is not None, 'unique_sorted not implemented'
assert callable(func), 'unique_sorted not callable'
result = func([3,1,2,1])
assert result == [1,2,3], f'unexpected result: {result}'
print(f'PASS: 05_fuzzy_req_004 — unique_sorted works correctly')
"
