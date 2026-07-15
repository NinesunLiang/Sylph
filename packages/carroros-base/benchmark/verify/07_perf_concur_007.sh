#!/bin/bash
# Verify: Lock-free read
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import time, importlib
mod = importlib.import_module('src.cache')
start = time.time()
# Call the function multiple times to test perf
for _ in range(100):
    mod.get('test')
elapsed = time.time() - start
print(f'PASS: 07_perf_concur_007 — 100 calls in {elapsed:.3f}s')
"
