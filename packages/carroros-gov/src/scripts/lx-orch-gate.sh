#!/usr/bin/env bash
# lx-orch-gate.sh — Oracle 门禁裁决
# Cross-platform Python resolution (DG-105)
[ -f "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" ] && source "$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/.claude/hooks/harness_config.sh" 2>/dev/null || true

# 用法: lx-orch-gate <og-id> approve|reject [--reason "..."]

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "用法: lx-orch-gate <og-id> approve|reject [--reason \"...\"]"
    exit 1
fi

GATE_ID="$1"
VERDICT="$2"
shift 2

REASON=""
while [ $# -gt 0 ]; do
    case "$1" in
        --reason) REASON="$2"; shift 2 ;;
        *) echo "未知选项: $1"; exit 1 ;;
    esac
done

case "$VERDICT" in
    approve|reject) ;;
    *) echo "ERROR: 裁决必须为 approve 或 reject"; exit 1 ;;
esac

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/state/pipeline.yaml"

if [ ! -f "$PIPELINE" ]; then
    echo "ERROR: pipeline.yaml 未找到"
    exit 1
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%S+08:00")

${PYTHON_BIN:-python3} - "$PIPELINE" "$GATE_ID" "$VERDICT" "$NOW" "$REASON" <<'PYEOF'
import sys, yaml, os, tempfile
from collections import OrderedDict

# Ordered YAML load/dump to preserve key order
def ordered_load(stream):
    class OrderedLoader(yaml.SafeLoader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))
    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    return yaml.load(stream, OrderedLoader)

def ordered_dump(data, stream=None, **kwds):
    class OrderedDumper(yaml.SafeDumper):
        pass
    def dict_representer(dumper, d):
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, d.items())
    OrderedDumper.add_representer(OrderedDict, dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

pipe_path = sys.argv[1]
gate_id = sys.argv[2]
verdict = sys.argv[3]
now = sys.argv[4]
reason = sys.argv[5]

with open(pipe_path) as f:
    data = ordered_load(f)

# Find the gate
found = False
for g in data.get('oracle_gates', []):
    if g['id'] == gate_id:
        g['status'] = verdict
        g['reviewed_at'] = now
        if reason:
            g['result'] = f"{'✅ Approved' if verdict == 'approve' else '❌ Rejected'} — {reason}"
        else:
            g['result'] = f"{'✅ Approved' if verdict == 'approve' else '❌ Rejected'}"
        found = True
        break

if not found:
    print(f"ERROR: Gate {gate_id} not found in pipeline.yaml")
    sys.exit(1)

# Atomic write: tmp → rename
tmp = tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(pipe_path), delete=False, suffix='.tmp')
with open(tmp.name, 'w') as f:
    ordered_dump(data, f, default_flow_style=False, allow_unicode=True)
os.rename(tmp.name, pipe_path)

print(f"✅ Gate {gate_id} → {verdict}")

# ─── 方向指引 ───
from_stage = None
to_stage = None
for g in data.get('oracle_gates', []):
    if g['id'] == gate_id:
        from_stage = g.get('from_stage', '?')
        to_stage = g.get('to_stage', '?')
        break

if verdict == 'approve':
    print(f"\n─── 方向指引 ───")
    print(f"  门禁已通过，可推进到下一阶段")
    print(f"")
    print(f"  建议下一步:")
    print(f"    1. lx-orch advance — 推荐 ✓")
    print(f"       说明：推进到下一阶段")
    print(f"       适用场景：门禁已通过，准备进入下一开发阶段")
    print(f"    2. lx-orch status")
    print(f"       说明：查看更新后管线全景")
    print(f"       适用场景：想了解整体管线状态后再决定")
    print(f"    3. 自定义操作")
    print(f"       → 输入你想要的命令")
else:
    print(f"\n─── 方向指引 ───")
    print(f"  门禁已拒绝，当前阶段阻塞")
    print(f"  需补充资料或调整方案后重新提交门禁")
    print(f"")
    print(f"  建议下一步:")
    print(f"    1. lx-orch gate {gate_id} approve --reason ... — 推荐 ✓")
    print(f"       说明：问题解决后重新批准门禁")
    print(f"       适用场景：已补充资料或调整方案，可以重新提交")
    print(f"    2. lx-orch status")
    print(f"       说明：查看当前状态")
    print(f"       适用场景：想了解阻塞详情后再决定")
    print(f"    3. 自定义操作")
    print(f"       → 输入你想要的命令")
PYEOF

exit 0
