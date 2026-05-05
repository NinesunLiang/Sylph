#!/usr/bin/env python3
"""
Fix truncated code fence language labels.
Pattern: ```bas\nh\n → ```bash\n
Scans the entire project for .md files and fixes all instances.
"""

import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = {'node_modules', '.opencode', '.git', 'archive', '__pycache__'}

# Known language name completions
LANGUAGE_COMPLETIONS = {
    'bas': {  # ```bas
        'h': 'bash',
    },
    'pyt': {  # ```pyt
        'h': 'python',
        'hon': 'python',
    },
    'thi': {  # ```thi
        'nk': 'think',
        's': 'this',  # not a language, but avoid breaking
    },
    'markdow': {  # ```markdow
        'n': 'markdown',
    },
    'tex': {  # ```tex
        't': 'text',
    },
    'con': {  # ```con
        'tent': 'content',
        'sole': 'console',
        'fig': 'config',
    },
    'pla': {  # ```pla
        'in': 'plain',
        'ntext': 'plantext',
        'ntuml': 'plantuml',
    },
    'sta': {  # ```sta
        'tic': 'static',
    },
    'yml': {  # ```yml
        '': 'yaml',  # ```yml\ncontent → ```yaml\ncontent
    },
    'jso': {  # ```jso
        'n': 'json',
    },
    'shel': {  # ```shel
        'l': 'shell',
    },
    'powe': {  # ```powe
        'rshell': 'powershell',
    },
    'bat': {  # ```bat
        'ch': 'batch',
    },
    'grad': {  # ```grad
        'le': 'gradle',
    },
    'swif': {  # ```swif
        't': 'swift',
    },
    'kotli': {  # ```kotli
        'n': 'kotlin',
    },
    'scal': {  # ```scal
        'a': 'scala',
    },
    'rub': {  # ```rub
        'y': 'ruby',
    },
    'per': {  # ```per
        'l': 'perl',
    },
    'ph': {  # ```ph
        'p': 'php',
    },
    'haske': {  # ```haske
        'll': 'haskell',
    },
    'erlan': {  # ```erlan
        'g': 'erlang',
    },
    'cloju': {  # ```cloju
        're': 'clojure',
    },
    'elixi': {  # ```elixi
        'r': 'elixir',
    },
    'dart': {  # ```dart (already complete)
        '': 'dart',
    },
    'dockerfil': {  # ```dockerfil
        'e': 'dockerfile',
    },
    'dockercompos': {  # ```dockercompos
        'e': 'docker-compose',
    },
    'mak': {  # ```mak
        'e': 'make',
        'efile': 'makefile',
    },
    'cmake': {  # ```cmake
        '': 'cmake',
    },
    'outpu': {  # ```outpu
        't': 'output',
    },
    'verba': {  # ```verba
        'tim': 'verbatim',
    },
    'gma': {  # ```gma
        'il': 'gmail',
    },
    'diff': {  # ```diff
        '': 'diff',
    },
    'patch': {  # ```patch
        '': 'patch',
    },
    'csv': {  # ```csv
        '': 'csv',
    },
    'tab': {  # ```tab
        'le': 'table',
    },
    'log': {  # ```log
        '': 'log',
    },
    'tra': {  # ```tra (trace)
        'ce': 'trace',
    },
}

# Also handle concatenated labels like ```bashpytho → ```bash
CONCATENATED_MAP = {
    'bashpytho': 'bash',
    'bashte': 'bash',
    'bashgr': 'bash',
    'bashg': 'bash',
    'bashmkd': 'bash',
    'bashn': 'bash',
    'markdown#': 'markdown',
    'plan_gat': 'plan',
    'stepwis': 'stepwise',
    'yamltask_inpu': 'yaml',
    'yamltask_nam': 'yaml',
    'yamlcriteria': 'yaml',
    'yamltask': 'yaml',
    'bashpytho': 'bash',
    'bashte': 'bash',
}

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if line matches ```<truncated_lang> pattern
        m = re.match(r'^(```+)(\w+)\s*$', line)
        if m:
            fence = m.group(1)
            label = m.group(2)
            label_lower = label.lower()

            # Check concatenated labels first
            if label_lower in CONCATENATED_MAP:
                result.append(f'{fence}{CONCATENATED_MAP[label_lower]}\n')
                modified = True
                i += 1
                continue

            # Check if this is a truncated language label
            # by looking at the next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].rstrip('\n')

                # Get the first word of the next line
                next_first_word = next_line.split()[0] if next_line.strip() else ''

                # Try completions
                if label_lower in LANGUAGE_COMPLETIONS:
                    completions = LANGUAGE_COMPLETIONS[label_lower]
                    for suffix, full_lang in completions.items():
                        if next_first_word == suffix:
                            # Found a match: merge fence label
                            result.append(f'{fence}{full_lang}\n')
                            # Skip the continuation line (the suffix line)
                            i += 1
                            modified = True
                            break
                    else:
                        # No match found for any completion
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)
        else:
            result.append(line)

        i += 1

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(result)
        return True
    return False


def main():
    md_files = []
    for root, dirs, files in os.walk(PROJECT_DIR):
        # Skip excluded directories only (keep dot-dirs like .claude)
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))

    md_files.sort()
    fixed_count = 0
    clean_count = 0
    error_count = 0

    for filepath in md_files:
        relpath = os.path.relpath(filepath, PROJECT_DIR)
        try:
            if fix_file(filepath):
                fixed_count += 1
                print(f"  FIXED: {relpath}")
            else:
                clean_count += 1
        except Exception as e:
            error_count += 1
            print(f"  ERROR: {relpath}: {e}")

    print()
    print(f"Total: {len(md_files)} | Fixed: {fixed_count} | Clean: {clean_count} | Errors: {error_count}")


if __name__ == '__main__':
    main()
