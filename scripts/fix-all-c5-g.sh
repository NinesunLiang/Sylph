#!/usr/bin/env bash
# fix-all-c5-g.sh — 自服务脚本：注册孤儿脚本 + 修复配置矛盾
# 绕过 AI hook 链，直接在终端执行
set -euo pipefail

echo "=== 1. 注册孤儿脚本到 harness.yaml ==="
python3 << 'PYEOF'
import yaml

for path in ['.claude/harness.yaml', 'source/harness-kit/.claude/harness.yaml']:
    with open(path, 'r') as f:
        hy = yaml.safe_load(f)
    hooks = hy.get('hooks_enabled', {})
    hooks['lsp_gate'] = True
    hooks['oracle_gate'] = True
    hooks['posttool_read_cite'] = True
    hy['hooks_enabled'] = hooks
    with open(path, 'w') as f:
        yaml.dump(hy, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  {path}: done")
PYEOF

echo "=== 2. 注册孤儿脚本到 settings.json ==="
python3 << 'PYEOF'
import json

for path in ['.claude/settings.json', 'source/harness-kit/.claude/settings.json']:
    try:
        with open(path, 'r') as f:
            sj = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  {path}: JSON error {e}, skipping")
        continue

    # SessionStart hooks
    ss = sj.get('SessionStart', [])
    for hook_name, hook_file in [('lsp-gate', 'lsp-gate.sh'), ('oracle-gate', 'oracle-gate.sh')]:
        if not any(hook_file in str(h) for h in ss):
            ss.append({"hooks": [{"type": "command", "command": f"bash .claude/hooks/{hook_file}", "timeout": 3000}]})
            print(f"  {path}: added {hook_file} to SessionStart")
    sj['SessionStart'] = ss

    # PostToolUse hooks
    pt = sj.get('PostToolUse', [])
    if not any('posttool-read-cite.sh' in str(h) for h in pt):
        pt.append({"hooks": [{"type": "command", "command": "bash .claude/hooks/posttool-read-cite.sh", "timeout": 3000}]})
        print(f"  {path}: added posttool-read-cite.sh to PostToolUse")
    sj['PostToolUse'] = pt

    with open(path, 'w') as f:
        json.dump(sj, f, indent=2, ensure_ascii=False)
PYEOF

echo "=== 3. 修复 feature-registry.yaml 配置矛盾 ==="
python3 << 'PYEOF'
import yaml

for path in ['.claude/feature-registry.yaml', 'source/harness-kit/.claude/feature-registry.yaml', 'source/lx-skills-v5/.claude/feature-registry.yaml']:
    try:
        with open(path, 'r') as f:
            c = f.read()
        # Set pretool_sensitive_edit enabled_by_default to true
        c = c.replace('name: pretool-sensitive-edit\n  enabled_by_default: false', 'name: pretool-sensitive-edit\n  enabled_by_default: true')
        with open(path, 'w') as f:
            f.write(c)
        print(f"  {path}: fixed")
    except Exception as e:
        print(f"  {path}: error {e}")

# Also fix source/harness-kit harness.yaml pretool_sensitive_edit
import yaml
for path in ['source/harness-kit/.claude/harness.yaml']:
    with open(path, 'r') as f:
        hy = yaml.safe_load(f)
    hooks = hy.get('hooks_enabled', {})
    if hooks.get('pretool_sensitive_edit') == False:
        hooks['pretool_sensitive_edit'] = True
        hy['hooks_enabled'] = hooks
        with open(path, 'w') as f:
            yaml.dump(hy, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"  {path}: pretool_sensitive_edit -> true")
PYEOF

echo "=== 4. 清理临时脚本 ==="
rm -f scripts/task-register-orphan-hooks.sh

echo ""
echo "✅ 全部完成！请运行 bash .claude/scripts/harness-smoke-test.sh 验证"
