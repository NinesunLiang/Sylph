#!/usr/bin/env python3
"""Fix YAML indentation for description: | block scalars in all task files."""
import os
import glob

TASKS_DIR = os.path.expanduser("~/Desktop/CarrorOS/benchmark/tasks")
fixed = 0
errors = 0

for yaml_path in sorted(glob.glob(f"{TASKS_DIR}/**/*.yaml", recursive=True)):
    with open(yaml_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    in_description_block = False
    description_indent_done = False
    saw_blank_after_block = False
    modified = False
    
    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')
        
        # Detect "description: |" line
        if stripped.rstrip() == "description: |" or stripped.rstrip() == "description: |-":
            in_description_block = True
            description_indent_done = False
            saw_blank_after_block = False
            new_lines.append(line)
            continue
        
        if in_description_block:
            if not description_indent_done:
                # Check if this line is indented properly (starts with space)
                if stripped == '':
                    # Empty line in the block or after it
                    # Check if the next non-empty line would be a key
                    # For now, indent empty lines in the block
                    new_lines.append(line)
                    continue
                
                if not stripped.startswith(' ') and not stripped.startswith('\t'):
                    # This line has no indentation - need to check if it's still part of description
                    # Description content continues until we hit a line that looks like a new YAML key
                    # Keys are things like "repo_url:", "verify_script:", etc.
                    if any(stripped.startswith(k) for k in ['repo_url:', 'verify_script:', 'allowed_files:', 'forbidden_files:', 'max_tool_calls:', 'max_wall_time_seconds:', 'seeds:', '#']):
                        # This is a new YAML key, not part of description
                        in_description_block = False
                        new_lines.append(line)
                        continue
                    
                    # Still part of description - indent it
                    new_lines.append('  ' + line)
                    modified = True
                    continue
                else:
                    # Already indented, good
                    description_indent_done = True
                    new_lines.append(line)
                    continue
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if modified:
        with open(yaml_path, 'w') as f:
            f.writelines(new_lines)
        fixed += 1
        print(f"  ✓ Fixed: {os.path.basename(yaml_path)}")
    else:
        # Double-check: read with yaml to see if it parses
        try:
            import yaml
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            desc = data.get('description', '')
            if desc and len(desc.strip()) >= 50:
                print(f"  ✓ OK:   {os.path.basename(yaml_path)} ({len(desc.strip())} chars)")
            else:
                print(f"  ! Short: {os.path.basename(yaml_path)} (desc={len(desc.strip()) if desc else 0} chars)")
        except Exception as e:
            errors += 1
            print(f"  ✗ ERR:  {os.path.basename(yaml_path)} — {e}")

print(f"\nFixed: {fixed}, Errors: {errors}")
