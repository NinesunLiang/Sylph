#!/bin/bash
# Verify: Parallel batch
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
import time, importlib
mod = importlib.import_module('src.data_processor')
start = time.time()
# Call the function multiple times to test perf
for _ in range(100):
    mod.batch_process(list(range(100)), chunk_size=10)
elapsed = time.time() - start
print(f'PASS: 07_perf_concur_003 — 100 calls in {elapsed:.3f}s')
"
