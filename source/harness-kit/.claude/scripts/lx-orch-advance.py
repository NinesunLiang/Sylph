#!/usr/bin/env python3
"""
lx-orch-advance.py — Pipeline 阶段推进
Python 移植版，完全等价 lx-orch-advance.sh v1.0

检查 Oracle gate → 推进当前 stage → 更新 pipeline.yaml
用法: python3 lx-orch-advance.py [--force]
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

STAGE_ORDER = ['hier', 'oma', 'gov', 'rpe', 'dev']
STAGE_PIPE = {
    'hier': {'from': 'pending', 'to': 'completed'},
    'oma': {'from': 'initialized', 'to': 'completed'},
    'gov': {'from': 'initialized', 'to': 'completed'},
    'rpe': {'from': 'initialized', 'to': 'completed'},
    'dev': {'from': 'initialized', 'to': 'running'},
}

STAGE_LABELS = {
    'hier': '分层拆解：主PRD→Sub PRD',
    'oma': '特性拆解：Sub PRD→Feature',
    'gov': 'PRD治理：reconcile/propagate/audit',
    'rpe': '特性开发计划：research/plan',
    'dev': '开发执行',
}


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
    force = "--force" in sys.argv

    if not PIPELINE_FILE.exists():
        print("ERROR: pipeline.yaml 未找到", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    with open(PIPELINE_FILE, "r") as f:
        data = ordered_load(f)

    stages = data.get('stages', {})
    gates = data.get('oracle_gates', [])

    # Find current incomplete stage
    current = None
    for s in STAGE_ORDER:
        st = stages.get(s, 'pending')
        if st != 'completed':
            current = s
            break

    if current is None:
        print("✅ 管线已全部完成，无可推进阶段")
        sys.exit(0)

    print(f"📍 当前阶段: {current} ({stages.get(current, 'pending')})")

    # Find gate transitioning INTO this stage
    gate_id = None
    for g in gates:
        if g.get('to_stage', '').startswith(current):
            gate_id = g['id']
            break

    if gate_id and not force:
        for g in gates:
            if g['id'] == gate_id:
                if g['status'] != 'approved':
                    print(f"⛔ Gate {gate_id} 未通过 (status: {g['status']})")
                    print(f"   请先运行: /lx-orch gate {gate_id} approve")
                    sys.exit(1)
                break

    # Advance the stage
    stages[current] = STAGE_PIPE[current]['to']
    data['updated_at'] = now

    # Atomic write: tmp → rename
    pipe_dir = os.path.dirname(str(PIPELINE_FILE))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=pipe_dir)
    with os.fdopen(tmp_fd, 'w') as f:
        ordered_dump(data, f, default_flow_style=False, allow_unicode=True)
    os.rename(tmp_path, str(PIPELINE_FILE))

    print(f"  → {current}: {STAGE_PIPE[current]['from']} → {STAGE_PIPE[current]['to']} ✅")
    print(f"  Updated: {now}")

    # ─── 方向指引 ───
    next_stages = []
    found = False
    for s in STAGE_ORDER:
        if found:
            next_stages.append(s)
        if s == current:
            found = True

    print(f"\n─── 方向指引 ───")
    print(f"  现已进入「{current}」阶段 — {STAGE_LABELS.get(current, '')}")
    print("")

    if next_stages:
        next_s = next_stages[0]
        print(f"  后续阶段: {next_s} — {STAGE_LABELS.get(next_s, '')}")
        print("")

    print(f"  建议下一步:")
    entries = []
    if current == 'hier':
        entries = [
            ("/lx-oma-hier <master-prd.md>", "开始分层拆解", "准备拆分主 PRD 为 Sub PRD"),
        ]
    elif current == 'oma':
        entries = [
            ("/lx-oma-split sub-prds/domain-{sub_prd}.md", "开始特性拆解", "将 Sub PRD 拆为可开发的 feature"),
        ]
    elif current == 'gov':
        entries = [
            ("/lx-oma-gov reconcile", "执行 reconcile 检测变更", "主 PRD 有更新，需同步到 feature"),
            ("/lx-oma-gov status", "查看治理全景", "想了解各 feature 同步和冲突状态"),
        ]
    elif current == 'rpe':
        entries = [
            ("/lx-oma-orch dev list", "查看 RPE 进度面板", "想了解各 feature 的开发进度"),
        ]
    elif current == 'dev':
        entries = [
            ("/lx-oma-orch dev list", "查看开发进度", "查看所有开发中 feature 的进度"),
        ]
    entries.append(("自定义操作", "输入你想要的命令", ""))
    for i, (cmd, desc, scene) in enumerate(entries, 1):
        if cmd == "自定义操作":
            print(f"    {i}. 自定义操作")
            print(f"       → {desc}")
        elif i == 1:
            print(f"    {i}. {cmd} — 推荐 ✓")
            print(f"       说明：{desc}")
            print(f"       适用场景：{scene}")
        else:
            print(f"    {i}. {cmd}")
            print(f"       说明：{desc}")
            print(f"       适用场景：{scene}")
    print(f"  你也可以: lx-orch status — 刷新管线全景")

    sys.exit(0)


if __name__ == "__main__":
    main()
