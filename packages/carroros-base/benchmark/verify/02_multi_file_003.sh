#!/bin/bash
# Verify: Refactor to generator
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.data_processor')
# Check the expected function exists
func = getattr(mod, 'process_items', None)
assert func is not None, 'process_items not implemented'
assert callable(func), 'process_items not callable'
result = func([1,2,3])
assert result == [{'index':0,'original':1,'doubled':2}], f'unexpected result: {result}'
print(f'PASS: 02_multi_file_003 — process_items works correctly')
"
