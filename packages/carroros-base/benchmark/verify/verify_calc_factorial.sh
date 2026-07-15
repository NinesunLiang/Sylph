#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.calc import factorial
try:
    factorial(-1)
    assert False
except ValueError: pass
print('PASS')
"
