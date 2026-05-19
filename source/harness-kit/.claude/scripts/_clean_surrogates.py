#!/usr/bin/env python3
"""Clean literal backslash-u-Dxxx patterns from files, replacing with safe U+ notation."""
import re, os, sys

# Match literal \uD800 through \uDFFF (case insensitive)
# Using chr() to build the pattern safely without \u in source
# Double backslash in regex: \\ matches literal \, then u[Dd][89a-fA-F] covers all surrogates
udxxx_re = re.compile(chr(92) + chr(92) + 'u[Dd][89a-fA-F][0-9A-Fa-f]{2}')

def clean_file(filepath, dry_run=False):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    def replace_udxxx(m):
        hex_str = m.group(0)[2:]  # Remove \u prefix
        return 'U+' + hex_str.upper()

    cleaned = udxxx_re.sub(replace_udxxx, content)

    if cleaned == content:
        return 0

    count = len(udxxx_re.findall(content))
    if not dry_run:
        # Backup first
        bak = filepath + '.bak-dg009'
        with open(bak, 'w', encoding='utf-8') as f:
            f.write(content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
    return count


if __name__ == '__main__':
    files = [
        '__PROJECT_ROOT__/.omc/state/session-dump.json',
        '__PROJECT_ROOT__/.claude/claude-next.md',
        '__PROJECT_ROOT__/source/harness-kit/.claude/claude-next.md',
    ]

    for fp in files:
        if not os.path.exists(fp):
            print(f"SKIP: {fp}: not found")
            continue
        count = clean_file(fp)
        if count > 0:
            print(f"CLEANED: {fp}: {count} patterns replaced")
        else:
            print(f"SKIP: {fp}: no patterns found")

    print("Done!")
