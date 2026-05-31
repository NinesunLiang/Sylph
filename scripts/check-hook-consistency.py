#!/usr/bin/env python3
"""Check consistency between harness.yaml hooks_enabled and feature-registry.yaml enabled_by_default."""
import yaml, sys

with open('.claude/harness.yaml') as f:
    harness = yaml.safe_load(f)
with open('.claude/feature-registry.yaml') as f:
    registry = yaml.safe_load(f)

reg_enabled = {}
for h in registry.get('hooks', []):
    name = h['name'].replace('-', '_')
    reg_enabled[name] = h.get('enabled_by_default', True)

mismatches = []
for name, enabled in harness.get('hooks_enabled', {}).items():
    reg_val = reg_enabled.get(name)
    if reg_val is not None and enabled != reg_val:
        mismatches.append((name, enabled, reg_val))

print(f"Found {len(mismatches)} mismatches:")
for name, h_val, r_val in mismatches:
    print(f"  {name}: harness.hooks_enabled={h_val}, registry.enabled_by_default={r_val}")
