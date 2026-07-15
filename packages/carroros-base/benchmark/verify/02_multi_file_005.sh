#!/bin/bash
# Verify: Add middleware pipeline
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
from src.api import api
r, s = api.handle('/add', {'a': 1, 'b': 2})
assert s == 200 and r['data'] == 3, 'cross-module route broken'
print(f'PASS: 02_multi_file_005 — cross-module integration works')
"
