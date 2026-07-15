#!/bin/bash
cd "$(dirname "$0")/.."
python3 -c "from src.calc import divide; assert divide(5,0)==float('inf'); assert divide(0,5)==0; print('PASS')"
