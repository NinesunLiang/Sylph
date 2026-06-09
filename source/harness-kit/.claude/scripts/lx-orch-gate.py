#!/usr/bin/env python3
"""
lx-orch-gate.py — Oracle 门禁裁决
Python 移植版，完全等价 lx-orch-gate.sh v1.0

用法: python3 lx-orch-gate.py <og-id> approve|reject [--reason "..."]
"""

import os
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
PIPELINE_FILE = PROJECT_ROOT / "state" / "pipeline.yaml"


def ordered_load(stream):
    class OrderedLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return yaml.load(stream, OrderedLoader)


def ordered_dump(data, stream=None, **kwds):
    class OrderedDumper(yaml.SafeDumper):
        pass

    def dict_representer(dumper, d):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, d.items()
        )

    OrderedDumper.add_representer(OrderedDict, dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def main():
    if len(sys.argv) < 3:
        print("用法: lx-orch-gate <og-id> approve|reject [--reason \"...\"]", file=sys.stderr)
        sys.exit(1)

    gate_id = sys.argv[1]
    verdict = sys.argv[2]

    # Parse options
    reason = ""
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--reason":
            i += 1
            if i < len(sys.argv):
                reason = sys.argv[i]
        else:
            print(f"未知选项: {sys.argv[i]}", file=sys.stderr)
            sys.exit(1)
        i += 1

    if verdict not in ("approve", "reject"):
        print("ERROR: 裁决必须为 approve 或 reject", file=sys.stderr)
        sys.exit(1)

    if not PIPELINE_FILE.exists():
        print("ERROR: pipeline.yaml 未找到", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    with open(PIPELINE_FILE, "r") as f:
        data = ordered_load(f)

    # Find the gate
    found = False
    from_stage = None
    to_stage = None
    for g in data.get('oracle_gates', []):
        if g['id'] == gate_id:
            g['status'] = verdict
            g['reviewed_at'] = now
            if reason:
                g['result'] = f"{'✅ Approved' if verdict == 'approve' else '❌ Rejected'} — {reason}"
            else:
                g['result'] = f"{'✅ Approved' if verdict == 'approve' else '❌ Rejected'}"
            from_stage = g.get('from_stage', '?')
            to_stage = g.get('to_stage', '?')
            found = True
            break

    if not found:
        print(f"ERROR: Gate {gate_id} not found in pipeline.yaml", file=sys.stderr)
        sys.exit(1)

    # Atomic write: tmp → rename
    pipe_dir = os.path.dirname(str(PIPELINE_FILE))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=pipe_dir)
    with os.fdopen(tmp_fd, 'w') as f:
        ordered_dump(data, f, default_flow_style=False, allow_unicode=True)
    os.rename(tmp_path, str(PIPELINE_FILE))

    print(f"✅ Gate {gate_id} → {verdict}")

    # ─── 方向指引 ───
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

    sys.exit(0)


if __name__ == "__main__":
    main()
