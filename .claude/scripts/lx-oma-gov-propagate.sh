#!/usr/bin/env bash
# lx-oma-gov-propagate.sh — 增量传播命令
# 将 reconcile 产生的变更传播到各 prd/{sub_prd}/{feature}/prd.md
# 用法:
#   lx-oma-gov-propagate --dry-run            # 预览模式
#   lx-oma-gov-propagate --execute             # 实际写入
#   lx-oma-gov-propagate --dry-run --chg CHG-20260509-001  # 指定单个 CHG

set -euo pipefail

# ─── Args ───
DRY_RUN=false
EXECUTE=false
FILTER_CHG=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --execute) EXECUTE=true ;;
        --chg=*) FILTER_CHG="${arg#--chg=}" ;;
        --chg) echo "ERROR: --chg 需要值 (如 --chg=CHG-20260509-001)"; exit 1 ;;
        *) echo "ERROR: 未知选项 $arg"; exit 1 ;;
    esac
done

if [ "$DRY_RUN" = false ] && [ "$EXECUTE" = false ]; then
    echo "用法: lx-oma-gov-propagate --dry-run|--execute [--chg=CHG-YYYYMMDD-NNN]"
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
SYNC_STATE="$PROJECT_ROOT/.claude/skills/lx-oma-gov/state/sync-state.md"
CONSOLIDATION_LOG="$PROJECT_ROOT/CONSOLIDATION-LOG.md"
NOW_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOW_DATE=$(date -u +"%Y-%m-%d")

# ─── Pre-checks ───
if [ ! -f "$SYNC_STATE" ]; then
    echo "ERROR: sync-state.md 未找到 ($SYNC_STATE)"
    echo "提示: 请先运行 reconcile"
    exit 1
fi

LAST_SNAPSHOT=$(grep "last_reconcile_snapshot:" "$SYNC_STATE" 2>/dev/null | sed 's/.*last_reconcile_snapshot: *//' | tr -d ' ')
if [ -z "$LAST_SNAPSHOT" ] || [ "$LAST_SNAPSHOT" = '""' ]; then
    echo "ERROR: last_reconcile_snapshot 为空。请先运行 reconcile。"
    exit 1
fi

if [ ! -f "$CONSOLIDATION_LOG" ]; then
    echo "ERROR: CONSOLIDATION-LOG.md 未找到"
    echo "提示: 请先运行 reconcile"
    exit 1
fi

# ─── Find features ───
FEATURES=$(
    find "$PROJECT_ROOT/prd" -type d -name "feat-*" 2>/dev/null | sort || true
)

if [ -z "$FEATURES" ]; then
    echo "⚠️  没有找到 feature 目录，跳过传播"
    exit 0
fi

# ─── Python propagation engine ───
python3 - "$PROJECT_ROOT" "$DRY_RUN" "$EXECUTE" "$NOW_UTC" "$NOW_DATE" "$FILTER_CHG" "$LAST_SNAPSHOT" <<'PYEOF'
import sys, os, json, re
from datetime import datetime

PROJECT_ROOT = sys.argv[1]
DRY_RUN = sys.argv[2] == 'True'
EXECUTE = sys.argv[3] == 'True'
NOW_UTC = sys.argv[4]
NOW_DATE = sys.argv[5]
FILTER_CHG = sys.argv[6]
LAST_SNAPSHOT = sys.argv[7]

STATE_DIR = os.path.join(PROJECT_ROOT, '.omc', 'state')
CONSOLIDATION_LOG = os.path.join(PROJECT_ROOT, 'CONSOLIDATION-LOG.md')
GOV_REPORT = os.path.join(STATE_DIR, 'gov-latest-report.yaml')

changes = []
pending_conflicts = []
total_features = 0
features_updated = set()
chgs_to_propagate = set()

# ─── 1. Scan CONSOLIDATION-LOG.md for CHG-IDs ───
if os.path.exists(CONSOLIDATION_LOG):
    with open(CONSOLIDATION_LOG) as f:
        content = f.read()

    # Find all CL entries with CHG references
    # Look for patterns: CL-NNN blocks followed by CHG-YYYYMMDD-NNN in adjudication records
    chg_pattern = re.compile(r'CHG-(\d{8}-\d{3})')
    cl_pattern = re.compile(r'### CL-(\d+)')

    for chg_match in chg_pattern.finditer(content):
        chg_id = chg_match.group()
        if FILTER_CHG and chg_id != FILTER_CHG:
            continue

        # Check if this CHG has been resolved (status = merged_to_master or accept)
        block_before = content[max(0, chg_match.start()-500):chg_match.start()]
        block_after = content[chg_match.end():chg_match.end()+500]

        full_block = block_before + chg_match.group() + block_after

        # Determine status
        status_ok = False
        reason_text = ""
        if 'Status: merged_to_master' in full_block or 'Status: accept' in full_block:
            status_ok = True
        if 'Verdict: accept' in full_block:
            status_ok = True
            reason_text = "L3 conflict resolved: accept"
        if 'Status: merged_to_master' in full_block:
            reason_text = "L1/L2 auto-merge"

        # Also check for Conflict that blocks propagation
        conflict_match = re.search(r'CONFLICT-\d+', full_block)
        if conflict_match:
            conflict_id = conflict_match.group()
            adjudicated = 'Verdict:' in full_block
            if not adjudicated:
                pending_conflicts.append({
                    'conflict_id': conflict_id,
                    'chg_id': chg_id,
                    'reason': 'conflict not yet adjudicated'
                })

        if status_ok:
            chgs_to_propagate.add(chg_id)
            changes.append({
                'chg_id': chg_id,
                'reason': reason_text,
                'conflict_id': conflict_id if 'conflict_match' in dir() and not adjudicated else ''
            })

if not chgs_to_propagate:
    print("ℹ️  无可传播的变更 (CHG-ID)  — CONSOLIDATION-LOG.md 中无 merged_to_master 或 accept 状态的条目")
    sys.exit(0)

# ─── 2. For each CHG-ID, check all features ───
FEATURES_DIR = os.path.join(PROJECT_ROOT, 'prd')
all_features = []
for root, dirs, files in os.walk(FEATURES_DIR):
    for d in dirs[:]:
        if d.startswith('feat-'):
            feat_path = os.path.join(root, d)
            # Extract sub_prd name (parent dir name)
            sub_prd = os.path.basename(root)
            all_features.append({
                'id': d,
                'sub_prd': sub_prd,
                'path': feat_path
            })

total_features = len(all_features)

# ─── 3. Dry-run / Execute ───
propagation_plan = []

for chg_id in sorted(chgs_to_propagate):
    for feat in all_features:
        sync_file = os.path.join(feat['path'], 'sync-notes.md')
        already_synced = False
        sync_content = ""

        if os.path.exists(sync_file):
            with open(sync_file) as f:
                sync_content = f.read()
            if chg_id in sync_content:
                already_synced = True

        entry = {
            'chg_id': chg_id,
            'sub_prd': feat['sub_prd'],
            'feature': feat['id'],
            'target_path': os.path.join(feat['path'], 'prd.md'),
            'sync_notes_path': sync_file,
            'needs_propagation': not already_synced,
            'status': 'skip_already_synced' if already_synced else 'pending'
        }
        propagation_plan.append(entry)
        if not already_synced:
            features_updated.add(f"{feat['sub_prd']}/{feat['id']}")

# ─── 4. Generate report ───
pending_count = sum(1 for e in propagation_plan if e['needs_propagation'])

print("")
if DRY_RUN:
    print(f"## Propagate Dry-Run Report — {NOW_DATE}")
    print("")
    print("> 注意：这是预览模式，未实际写入任何文件。")
    print("> 执行实际传播请运行: lx-oma-gov-propagate --execute")
    print("")
else:
    print(f"## Propagate Execute Report — {NOW_DATE}")
    print("")

if pending_count == 0:
    print("### 变更传播: 全部已同步，无需操作")
    print("")
    print(f"| CHG-ID | Feature | Status |")
    print(f"|--------|---------|--------|")
    for e in propagation_plan[:5]:
        status_icon = "✅ 已同步" if not e['needs_propagation'] else ""
        if status_icon:
            print(f"| {e['chg_id']} | {e['sub_prd']}/{e['feature']} | {status_icon} |")
    if len(propagation_plan) > 5:
        print(f"| ... | 还有 {len(propagation_plan)-5} 条全部已同步 | ✅ |")
else:
    print("### Changes to be propagated")
    print("")
    print("| CHG-ID | Sub PRD | Feature | Target | Status |")
    print("|--------|---------|---------|--------|--------|")
    for e in propagation_plan:
        if e['needs_propagation']:
            status_text = "⏳ 待传播" if DRY_RUN else "✅ 已写入"
            print(f"| {e['chg_id']} | {e['sub_prd']} | {e['feature']} | prd.md | {status_text} |")

# Pending conflicts
if pending_conflicts:
    print("")
    print("### Pending Conflicts (not propagated)")
    print("")
    print("| CONFLICT-ID | CHG-ID | Status |")
    print("|-------------|--------|--------|")
    for pc in pending_conflicts:
        print(f"| {pc['conflict_id']} | {pc['chg_id']} | awaiting_human |")

# Summary
print("")
print("### Summary")
print(f"- Total Features: {total_features}")
print(f"- Total CHG to propagate: {len(chgs_to_propagate)}")
print(f"- Feature targets needing update: {pending_count}")
if pending_conflicts:
    print(f"- Skipped (conflict pending): {len(pending_conflicts)}")

# ─── 5. Execute: write to sync-notes.md + prd.md ───
if EXECUTE and pending_count > 0:
    CL_ENTRIES = {}
    if os.path.exists(CONSOLIDATION_LOG):
        with open(CONSOLIDATION_LOG) as f:
            cl_content = f.read()
        # Find CL numbers for each CHG
        for chg in chgs_to_propagate:
            m = re.search(rf'### CL-(\d+).*?{chg}', cl_content, re.DOTALL)
            if m:
                CL_ENTRIES[chg] = f"CL-{m.group(1)}"

    written = 0
    for e in propagation_plan:
        if not e['needs_propagation']:
            continue

        # Ensure sync-notes.md exists
        os.makedirs(os.path.dirname(e['sync_notes_path']), exist_ok=True)
        if not os.path.exists(e['sync_notes_path']):
            with open(e['sync_notes_path'], 'w') as f:
                f.write(f"# Sync Notes — {e['sub_prd']}/{e['feature']}\n\n")

        # Append sync record
        src_cl = CL_ENTRIES.get(e['chg_id'], 'unknown')
        sync_entry = f"""
## Sync Record {e['chg_id']}

- CHG-ID: {e['chg_id']}
- Propagated At: {NOW_UTC}
- Propagated By: lx-oma-gov
- Source Change: CONSOLIDATION-LOG.md Entry {src_cl}
- Sync Type: prd
- Content Added: Reference propagation for {e['chg_id']} (see CONSOLIDATION-LOG.md {src_cl})
- Status: done
"""
        with open(e['sync_notes_path'], 'a') as f:
            f.write(sync_entry)

        # Also append reference to prd.md
        prd_path = e['target_path']
        if os.path.exists(prd_path):
            ref_entry = f"""
### Governance Sync — {e['chg_id']}
- Source: {src_cl}
- Propagated: {NOW_UTC}
- Note: This feature was updated to reflect master PRD changes. See sync-notes.md for details.
"""
            with open(prd_path, 'a') as f:
                f.write(ref_entry)

        written += 1

    print(f"\n✅ 实际写入完成: {written} 条传播记录")

# ─── 6. Write governance report (for orch to consume) ───
report = {
    'version': '1.0',
    'command': 'propagate',
    'result': 'success' if pending_count > 0 else 'no_changes',
    'dry_run': DRY_RUN,
    'changes': [],
    'features_updated': sorted(list(features_updated)) if not DRY_RUN else [],
    'pending_conflicts': [pc['conflict_id'] for pc in pending_conflicts],
    'oracle_gate': {
        'action': 'skip',
    }
}

os.makedirs(STATE_DIR, exist_ok=True)
with open(GOV_REPORT, 'w') as f:
    f.write(f"# governance-report.yaml\n")
    f.write(f"# Generated by lx-oma-gov-propagate at {NOW_UTC}\n")
    f.write(f"version: \"1.0\"\n")
    f.write(f"command: propagate\n")
    f.write(f"result: {report['result']}\n")
    f.write(f"dry_run: {'true' if DRY_RUN else 'false'}\n")
    total = len(chgs_to_propagate)
    updated_count = len(features_updated)
    if total > 0:
        f.write(f"changes:\n")
        for chg in sorted(chgs_to_propagate):
            f.write(f"  - type: propagate\n")
            f.write(f"    description: \"CHG {chg}\"\n")
    f.write(f"features_updated:\n")
    for feat in sorted(list(features_updated)):
        f.write(f"  - id: \"{feat}\"\n")
        f.write(f"    status: \"propagated\"\n")
    f.write(f"oracle_gate:\n")
    f.write(f"  action: skip\n")

if os.path.exists(GOV_REPORT):
    print(f"\n📄 治理报告已写入: {GOV_REPORT}")

PYEOF

# ─── 方向指引 ───
echo ""
echo "─── 方向指引 ───"
echo "  📍 propagate 完成"

if [ "$DRY_RUN" = "true" ]; then
    echo ""
    echo "  这是预览模式（dry-run），未实际写入任何文件。"
    echo ""
    echo "  建议下一步:"
    echo "    1. lx-oma-gov propagate --execute — 推荐 ✓"
    echo "       说明：确认无误后执行实际写入"
    echo "       适用场景：dry-run 预览内容符合预期，准备写入"
    echo "    2. lx-oma-gov reconcile"
    echo "       说明：如需调整变更内容，重新 reconcile"
    echo "       适用场景：预览内容需要调整，回头修改再预览"
    echo "    3. lx-oma-gov status"
    echo "       说明：查看治理全景"
    echo "       适用场景：想了解传播前整体治理状态"
    echo "    4. 自定义操作"
    echo "       → 输入你想要的命令"
else
    echo ""
    echo "  实际写入已完成。"
    echo ""
    echo "  建议下一步:"
    echo "    1. lx-oma-gov status — 推荐 ✓"
    echo "       说明：查看传播完成后各 feature 同步状态"
    echo "       适用场景：确认传播结果"
    echo "    2. lx-oma-gov audit"
    echo "       说明：执行漂移检测，确认一致性"
    echo "       适用场景：需要验证传播后各 feature 与 master 一致"
    echo "    3. lx-oma-gov reconcile"
    echo "       说明：开始下一轮 reconcile 循环"
    echo "       适用场景：有新输入资料需再次检测变更"
    echo "    4. 自定义操作"
    echo "       → 输入你想要的命令"
fi

exit 0
