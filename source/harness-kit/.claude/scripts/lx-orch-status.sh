#!/usr/bin/env bash
# lx-orch-status.sh — Pipeline Orchestrator 状态面板
# 从 governance-spec.md §Pipeline 集成 规范实现

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/state/pipeline.yaml"

if [ ! -f "$PIPELINE" ]; then
    echo "ERROR: pipeline.yaml 未找到 ($PIPELINE)"
    echo "提示: 请先运行 /lx-oma-gov init 创建治理目录"
    exit 1
fi

python3 - "$PIPELINE" <<'PYEOF'
import sys, yaml, os
from datetime import datetime

path = sys.argv[1]
with open(path) as f:
    data = yaml.safe_load(f)

now = datetime.now().strftime('%Y-%m-%d %H:%M')

print("Pipeline Status")
print("═══════════════════════════════════════")
print(f"  Updated: {data.get('updated_at', 'unknown')}")
print("")

stages = data.get('stages', {})
STAGE_ORDER = ['hier', 'oma', 'gov', 'rpe', 'dev']
for s in STAGE_ORDER:
    status = stages.get(s, 'unknown')
    icon = {'completed': '✅', 'initialized': '🟡', 'running': '🔄', 'pending': '⬜', 'blocked': '🔴'}.get(status, '⬜')
    print(f"  {s}: {icon} {status}")

print("")

# Gates
gates = data.get('oracle_gates', [])
print("Oracle Gates:")
for g in gates:
    icon = {'approved': '✅', 'pending': '⬜', 'rejected': '❌', 'running': '🔄'}.get(g['status'], '⬜')
    print(f"  {g['id']} ({g.get('from_stage','?')}→{g.get('to_stage','?')}): {icon} {g['status']}")

print("")

# Sub PRDs
subs = data.get('sub_prds', [])
print(f"Sub PRDs ({len(subs)}):")
for sub in subs:
    oracle_icon = {'final': '✅', 'approved': '✅', 'revised': '⚠️', 'pending': '⬜'}.get(sub.get('oracle',''), '⬜')
    print(f"  {sub['id']:22s} │ {sub.get('status','?'):12s} │ {len(sub.get('features',[])):2d} features │ oracle: {oracle_icon} {sub.get('oracle','?')}")

# ─── 方向指引：分析当前状态 → 推荐下一步 ───
print("")
print("─── 下一步方向 ───")

# Find current incomplete stage
current = None
for s in STAGE_ORDER:
    st = stages.get(s, 'pending')
    if st != 'completed':
        current = s
        break

if current is None:
    print("  ✅ 管线已全部完成")
    sys.exit(0)

# Find pending gates
pending_gates = [g for g in gates if g['status'] == 'pending']
# Find gate transitioning INTO current stage
current_gate = None
for g in gates:
    if g.get('to_stage', '').startswith(current):
        current_gate = g
        break

print(f"  📍 当前阶段: {current}")

# Find what's blocking / available
stage_labels = {
    'hier': '分层拆解（主PRD→Sub PRD）',
    'oma': '特性拆解（Sub PRD→Feature）',
    'gov': 'PRD治理（reconcile/propagate/audit）',
    'rpe': '特性开发计划（research/plan）',
    'dev': '开发执行',
}

available_actions = []

if current_gate and current_gate['status'] == 'pending':
    available_actions.append((
        f"lx-orch gate {current_gate['id']} approve",
        f"通过「{current_gate['from_stage']}→{current_gate['to_stage']}」门禁，进入{stage_labels.get(current, current)}阶段"
    ))
    available_actions.append((
        f"lx-orch gate {current_gate['id']} reject --reason ...",
        "拒绝门禁，阻止阶段推进（需说明理由）"
    ))

# Check if current stage's upstream gate is approved → can advance
can_advance = not current_gate or current_gate['status'] == 'approved'
if can_advance and current == 'hier':
    available_actions.append((
        "/lx-oma-hier <master-prd.md>",
        "主PRD → Sub PRD 分层拆解"
    ))
elif can_advance and current == 'oma':
    incomplete_subs = [sub for sub in subs if sub.get('status') not in ('oma_done', 'rpe_done', 'hier_done')]
    hier_done_subs = [sub for sub in subs if sub.get('status') == 'hier_done']
    if hier_done_subs:
        names = ', '.join(s['id'] for s in hier_done_subs[:3])
        available_actions.append((
            f"/lx-oma-split sub-prds/domain-{hier_done_subs[0]['id']}.md",
            f"拆解 {hier_done_subs[0]['id']}（已完成分层，待特性拆解）"
        ))
    available_actions.append((
        "/lx-oma-hier <master-prd.md>",
        "如还有未分层的 PRD，继续分层拆解"
    ))
elif can_advance and current == 'gov':
    available_actions.append((
        "/lx-oma-gov reconcile",
        "执行reconcile检测master PRD变更，产生CHG-ID + 冲突裁决"
    ))
    available_actions.append((
        "/lx-oma-gov status",
        "查看治理状态：各feature同步情况 + 待处理conflict"
    ))
elif can_advance and current == 'rpe':
    # Find features needing RPE
    features_need_rpe = []
    for sub in subs:
        for feat in sub.get('features', []):
            if feat.get('stage') == 'rpe_planned':
                features_need_rpe.append(f"{sub['id']}/{feat['id']}")
    if features_need_rpe:
        sample = features_need_rpe[0]
        available_actions.append((
            f"/lx-rpe prd/{sample.split('/')[0]}/{sample.split('/')[1]}",
            f"启动 {sample} 的research/plan/开发9步闭环"
        ))
        available_actions.append((
            "/lx-rpe status",
            "查看所有RPE实例进度面板"
        ))
elif can_advance and current == 'dev':
    available_actions.append((
        "/lx-rpe status",
        "查看所有开发中feature的进度"
    ))

if current_gate and current_gate['status'] == 'approved':
    available_actions.append((
        "/lx-orch advance",
        f"推进到{stage_labels.get(current, current)}阶段"
    ))

# Always available
available_actions.append((
    "/lx-orch status",
    "刷新本面板"
))
available_actions.append((
    "自定义操作",
    "输入你想做的其他操作（如直接调 skill / 手动检查文件）"
))

print("  建议下一步:")
for i, (cmd, desc) in enumerate(available_actions, 1):
    if cmd == "自定义操作":
        print(f"    {i}. 自定义操作")
        print(f"       → 输入你想要的命令")
    elif i == 1:
        print(f"    {i}. {cmd} — 推荐 ✓")
        print(f"       说明：{desc}")
        print(f"       适用场景：当前阶段最推荐的下一步操作")
    else:
        print(f"    {i}. {cmd}")
        print(f"       说明：{desc}")
        print(f"       适用场景：{desc}时选择此操作")

# Warning if pending gates not in current path
other_pending = [g for g in pending_gates if g != current_gate]
if other_pending:
    print("")
    print("  ⚠️  其他待处理门禁（非当前阶段阻塞项）:")
    for g in other_pending:
        print(f"    {g['id']} ({g['from_stage']}→{g['to_stage']}) — 当前还不影响推进，但建议提前了解")
PYEOF

exit 0
