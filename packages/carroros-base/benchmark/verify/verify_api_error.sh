#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.api import api
r,s=api.handle('/unknown',{})
assert 'Internal' not in r.get('error','')
assert 'leak' not in r.get('error','')
print('PASS')
"
