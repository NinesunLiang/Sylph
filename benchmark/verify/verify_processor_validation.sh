#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.data_processor import process_items
try: process_items('bad'); assert False
except TypeError: pass
print('PASS')
"
