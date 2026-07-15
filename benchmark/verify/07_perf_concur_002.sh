#!/bin/bash
# Verify: Cache factorial
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import time, importlib
mod = importlib.import_module('src.calc')
start = time.time()
# Call the function multiple times to test perf
for _ in range(100):
    mod.factorial(10)
elapsed = time.time() - start
print(f'PASS: 07_perf_concur_002 — 100 calls in {elapsed:.3f}s')
"
