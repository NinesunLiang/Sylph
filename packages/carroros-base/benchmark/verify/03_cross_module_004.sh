#!/bin/bash
# Verify: Dependency injection
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from src.api import api
r, s = api.handle('/add', {'a': 1, 'b': 2})
assert s == 200 and r['data'] == 3, 'cross-module route broken'
print(f'PASS: 03_cross_module_004 — cross-module integration works')
"
