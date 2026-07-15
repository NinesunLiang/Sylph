#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.data_processor import stats
s=stats([])
assert s['count']==0 and s['mean']==0
print('PASS')
"
