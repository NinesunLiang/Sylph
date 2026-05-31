#!/usr/bin/env python3
"""Verify E1/E2 read/write detection logic."""
import re

print("=== E1 Read-only test (python3 -m json.tool settings.json) ===")
cmd = 'python3 -m json.tool /Users/lucas.liang/Desktop/Sylph/Carror_OS/.claude/settings.json'
E1_WRITE_PATTERN = re.compile(
    r'(?:^|\||;|&&)\s*(?:echo|printf)\s+.*?(?:>>?|\|tee)\s+'
    r'|(?:^|\||;|&&)\s*sed\s+(?:-i|--in-place)\s+'
    r'|(?:^|\||;|&&)\s*tee\s+'
    r'|(?:^|\||;|&&)\s*(?:cp|mv)\s+'
    r'|(?:^|\||;|&&)\s*cat\s+.*?(?:>|>>)\s+'
    r'|(?:^|\||;|&&)\s*python3?\s+.*?(?:open\(|\.write\(|\.writelines\()'
    r'|(?:^|\||;|&&)\s*install\s+'
    r'|>\s+\.claude/'
    r'|>>\s+\.claude/',
    re.IGNORECASE
)
IS_WRITE = bool(E1_WRITE_PATTERN.search(cmd)) if cmd else False
print(f"  IS_WRITE_CMD={IS_WRITE}  {'PASS' if not IS_WRITE else 'FAIL'}")
assert not IS_WRITE, "E1 false positive on read-only!"

print("=== E1 Write test (echo > .claude/settings.json) ===")
cmd = 'echo "test" > .claude/settings.json'
IS_WRITE = bool(E1_WRITE_PATTERN.search(cmd)) if cmd else False
print(f"  IS_WRITE_CMD={IS_WRITE}  {'PASS' if IS_WRITE else 'FAIL'}")
assert IS_WRITE, "E1 missed write op!"

print("=== E2 Read-only test (cat sensitive-approved) ===")
cmd = 'cat /Users/lucas.liang/Desktop/Sylph/Carror_OS/.omc/state/sensitive-approved'
CAPTCHA_MARKERS = ['sensitive-approved', 'sensitive-required', 'permission-approved', 'permission-required']
E2_WRITE_PATTERN = re.compile(
    r'(?:echo|printf)\s+.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')'
    r'|(?:cp|mv|sed|tee)\s+.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')'
    r'|cat\s+.*(?:' + '|'.join(CAPTCHA_MARKERS) + r').*?(?:>>?|>)'
    r'|(?:>>?|>)\s*.*(?:' + '|'.join(CAPTCHA_MARKERS) + r')',
    re.IGNORECASE
)
E2 = any(_cm in cmd and E2_WRITE_PATTERN.search(cmd) for _cm in CAPTCHA_MARKERS)
print(f"  E2={E2}  {'PASS' if not E2 else 'FAIL'}")
assert not E2, "E2 false positive on read-only!"

print("=== E2 Write test (echo > sensitive-approved) ===")
cmd = 'echo "abc" > .omc/state/sensitive-approved'
E2 = any(_cm in cmd and E2_WRITE_PATTERN.search(cmd) for _cm in CAPTCHA_MARKERS)
print(f"  E2={E2}  {'PASS' if E2 else 'FAIL'}")
assert E2, "E2 missed write op!"

print("=== E2 ls test (ls .omc/state/) ===")
cmd = 'ls /Users/lucas.liang/Desktop/Sylph/Carror_OS/.omc/state/'
E2 = any(_cm in cmd and E2_WRITE_PATTERN.search(cmd) for _cm in CAPTCHA_MARKERS)
print(f"  E2={E2}  {'PASS' if not E2 else 'FAIL'}")
assert not E2, "E2 false positive on ls!"

print()
print("ALL TESTS PASSED ✅")
