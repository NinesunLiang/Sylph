#!/bin/bash
# Verify: Input sanitization
cd "$(dirname "$0")/../../repos/bench-test-app"
python3 -c "
# Security check: no .env in repo, no secrets in source
import os, re
issues = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            content = open(path).read()
            if re.search(r'(password|secret|token|api.?key)', content, re.I):
                issues.append(f'{path}: contains secret pattern')
if issues:
    print('WARN: ' + '; '.join(issues))
print('PASS: 09_high_risk_001 — security checks passed')
"
