#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
import time
from src.cache import get, set, clear
clear()
set('k','v',ttl=1)
assert get('k')=='v'
time.sleep(1.5)
assert get('k') is None
print('PASS')
"
