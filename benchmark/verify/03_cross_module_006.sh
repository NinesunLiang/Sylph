#!/bin/bash
# Verify: Consistent state
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import importlib
mod = importlib.import_module('src.state_manager')
# Check the expected function exists
func = getattr(mod, 'set_state', None)
assert func is not None, 'set_state not implemented'
assert callable(func), 'set_state not callable'
result = func('k','v')
assert result == None, f'unexpected result: {result}'
print(f'PASS: 03_cross_module_006 — set_state works correctly')
"
