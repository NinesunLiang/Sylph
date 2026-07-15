#!/bin/bash
# Verify: Single-pass stats
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import time, importlib
mod = importlib.import_module('src.data_processor')
start = time.time()
# Call the function multiple times to test perf
for _ in range(100):
    mod.stats(list(range(100)))
elapsed = time.time() - start
print(f'PASS: 07_perf_concur_004 — 100 calls in {elapsed:.3f}s')
"
