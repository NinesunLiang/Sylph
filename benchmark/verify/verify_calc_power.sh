#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.calc import power
assert power(2,-2)==0.25
assert power(5,-1)==0.2
print('PASS')
"
