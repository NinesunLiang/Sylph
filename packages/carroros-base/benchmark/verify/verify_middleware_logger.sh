#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "
from src.middleware import log_request
result=log_request(lambda d:d)('test')
assert result=='test'
print('PASS')
"
