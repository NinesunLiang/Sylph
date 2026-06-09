#!/usr/bin/env python3
"""
lx-oma-gov-propagate.py — 增量传播命令
Python 移植版，完全等价 lx-oma-gov-propagate.sh v1.0

将 reconcile 产生的变更传播到各 prd/{sub_prd}/{feature}/prd.md

用法:
  python3 lx-oma-gov-propagate.py --dry-run            # 预览模式
  python3 lx-oma-gov-propagate.py --execute             # 实际写入
  python3 lx-oma-gov-propagate.py --dry-run --chg=CHG-20260509-001  # 指定单个 CHG
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
SYNC_STATE = PROJECT_ROOT / ".claude" / "skills" / "lx-oma-gov" / "state" / "sync-state.md"
CONSOLIDATION_LOG = PROJECT_ROOT / "CONSOLIDATION-LOG.md"
GOV_REPORT = STATE_DIR / "gov-latest-report.yaml"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
NOW_DATE = datetime.now().strftime("%Y-%m-%d")


def main():
    # ─── Args ───
    dry_run = False
    execute = False
    filter_chg = ""

    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--execute":
            execute = True
        elif arg.startswith("--chg="):
            filter_chg = arg[6:]
        elif arg == "--chg":
            print("ERROR: --chg 需要值 (如 --chg=CHG-20260509-001)", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"ERROR: 未知选项 {arg}", file=sys.stderr)
            sys.exit(1)

    if not dry_run and not execute:
        print("用法: lx-oma-gov-propagate --dry-run|--execute [--chg=CHG-YYYYMMDD-NNN]", file=sys.stderr)
        sys.exit(1)

    # ─── Pre-checks ───
    if not SYNC_STATE.exists():
        print(f"ERROR: sync-state.md 未找到 ({SYNC_STATE})", file=sys.stderr)
        print("提示: 请先运行 reconcile", file=sys.stderr)
        sys.exit(1)

    sync_content = SYNC_STATE.read_text(encoding="utf-8")
    last_snapshot = ""
    for line in sync_content.splitlines():
        if "last_reconcile_snapshot:" in line:
            last_snapshot = line.split("last_reconcile_snapshot:")[-1].strip().strip('"')
            break

    if not last_snapshot or last_snapshot == '""':
        print('ERROR: last_reconcile_snapshot 为空。请先运行 reconcile。', file=sys.stderr)
        sys.exit(1)

    if not CONSOLIDATION_LOG.exists():
        print("ERROR: CONSOLIDATION-LOG.md 未找到", file=sys.stderr)
        print("提示: 请先运行 reconcile", file=sys.stderr)
        sys.exit(1)

    # ─── Find features ───
    prd_dir = PROJECT_ROOT / "prd"
    all_features = []
    if prd_dir.exists():
        for root, dirs, _ in os.walk(str(prd_dir)):
            for d in sorted(dirs):
                if d.startswith("feat-"):
                    feat_path = Path(root) / d
                    sub_prd = Path(root).name
                    all_features.append({
                        "id": d,
                        "sub_prd": sub_prd,
                        "path": feat_path,
                    })

    if not all_features:
        print("⚠️  没有找到 feature 目录，跳过传播")
        sys.exit(0)

    # ─── 1. Scan CONSOLIDATION-LOG.md for CHG-IDs ───
    cl_content = CONSOLIDATION_LOG.read_text(encoding="utf-8")
    chg_pattern = re.compile(r"CHG-(\d{8}-\d{3})")
    cl_pattern = re.compile(r"### CL-(\d+)")

    changes = []
    pending_conflicts = []
    chgs_to_propagate = set()

    for chg_match in chg_pattern.finditer(cl_content):
        chg_id = chg_match.group()
        if filter_chg and chg_id != filter_chg:
            continue

        # Look around for status
        start = max(0, chg_match.start() - 500)
        end = min(len(cl_content), chg_match.end() + 500)
        full_block = cl_content[start:end]

        status_ok = False
        reason_text = ""
        if "Status: merged_to_master" in full_block or "Status: accept" in full_block:
            status_ok = True
        if "Verdict: accept" in full_block:
            status_ok = True
            reason_text = "L3 conflict resolved: accept"
        if "Status: merged_to_master" in full_block:
            reason_text = "L1/L2 auto-merge"

        # Check for unresolved conflict
        conflict_match = re.search(r"CONFLICT-(\d+)", full_block)
        conflict_id = ""
        adjudicated = False
        if conflict_match:
            conflict_id = conflict_match.group()
            adjudicated = "Verdict:" in full_block
            if not adjudicated:
                pending_conflicts.append({
                    "conflict_id": conflict_id,
                    "chg_id": chg_id,
                    "reason": "conflict not yet adjudicated",
                })

        if status_ok:
            chgs_to_propagate.add(chg_id)
            changes.append({
                "chg_id": chg_id,
                "reason": reason_text,
                "conflict_id": conflict_id if conflict_id and not adjudicated else "",
            })

    if not chgs_to_propagate:
        print("ℹ️  无可传播的变更 (CHG-ID)  — CONSOLIDATION-LOG.md 中无 merged_to_master 或 accept 状态的条目")
        sys.exit(0)

    # ─── 2. For each CHG-ID, check all features ───
    propagation_plan = []
    features_updated = set()

    for chg_id in sorted(chgs_to_propagate):
        for feat in all_features:
            sync_file = feat["path"] / "sync-notes.md"
            already_synced = False
            if sync_file.exists():
                sync_content = sync_file.read_text(encoding="utf-8")
                if chg_id in sync_content:
                    already_synced = True

            entry = {
                "chg_id": chg_id,
                "sub_prd": feat["sub_prd"],
                "feature": feat["id"],
                "target_path": str(feat["path"] / "prd.md"),
                "sync_notes_path": str(sync_file),
                "needs_propagation": not already_synced,
                "status": "skip_already_synced" if already_synced else "pending",
            }
            propagation_plan.append(entry)
            if not already_synced:
                features_updated.add(f"{feat['sub_prd']}/{feat['id']}")

    # ─── 3. Generate report ───
    pending_count = sum(1 for e in propagation_plan if e["needs_propagation"])

    print("")
    if dry_run:
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
        print("| CHG-ID | Feature | Status |")
        print("|--------|---------|--------|")
        for e in propagation_plan[:5]:
            if not e["needs_propagation"]:
                print(f"| {e['chg_id']} | {e['sub_prd']}/{e['feature']} | ✅ 已同步 |")
        if len(propagation_plan) > 5:
            print(f"| ... | 还有 {len(propagation_plan)-5} 条全部已同步 | ✅ |")
    else:
        print("### Changes to be propagated")
        print("")
        print("| CHG-ID | Sub PRD | Feature | Target | Status |")
        print("|--------|---------|---------|--------|--------|")
        for e in propagation_plan:
            if e["needs_propagation"]:
                status_text = "⏳ 待传播" if dry_run else "✅ 已写入"
                print(f"| {e['chg_id']} | {e['sub_prd']} | {e['feature']} | prd.md | {status_text} |")

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
    print(f"- Total Features: {len(all_features)}")
    print(f"- Total CHG to propagate: {len(chgs_to_propagate)}")
    print(f"- Feature targets needing update: {pending_count}")
    if pending_conflicts:
        print(f"- Skipped (conflict pending): {len(pending_conflicts)}")

    # ─── 4. Execute: write to sync-notes.md + prd.md ───
    if execute and pending_count > 0:
        # Find CL numbers for each CHG
        cl_entries = {}
        for chg in chgs_to_propagate:
            m = re.search(rf"### CL-(\d+).*?{chg}", cl_content, re.DOTALL)
            if m:
                cl_entries[chg] = f"CL-{m.group(1)}"

        written = 0
        for e in propagation_plan:
            if not e["needs_propagation"]:
                continue

            sync_path = Path(e["sync_notes_path"])
            prd_path = Path(e["target_path"])

            # Ensure sync-notes.md exists
            sync_path.parent.mkdir(parents=True, exist_ok=True)
            if not sync_path.exists():
                sync_path.write_text(f"# Sync Notes — {e['sub_prd']}/{e['feature']}\n\n", encoding="utf-8")

            # Append sync record
            src_cl = cl_entries.get(e["chg_id"], "unknown")
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
            with open(sync_path, "a", encoding="utf-8") as f:
                f.write(sync_entry)

            # Also append reference to prd.md
            if prd_path.exists():
                ref_entry = f"""
### Governance Sync — {e['chg_id']}
- Source: {src_cl}
- Propagated: {NOW_UTC}
- Note: This feature was updated to reflect master PRD changes. See sync-notes.md for details.
"""
                with open(prd_path, "a", encoding="utf-8") as f:
                    f.write(ref_entry)

            written += 1

        print(f"\n✅ 实际写入完成: {written} 条传播记录")

    # ─── 5. Write governance report ───
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(GOV_REPORT, "w", encoding="utf-8") as f:
        f.write(f"# governance-report.yaml\n")
        f.write(f"# Generated by lx-oma-gov-propagate at {NOW_UTC}\n")
        f.write(f"version: \"1.0\"\n")
        f.write(f"command: propagate\n")
        f.write(f"result: {'success' if pending_count > 0 else 'no_changes'}\n")
        f.write(f"dry_run: {'true' if dry_run else 'false'}\n")
        if chgs_to_propagate:
            f.write("changes:\n")
            for chg in sorted(chgs_to_propagate):
                f.write(f"  - type: propagate\n")
                f.write(f"    description: \"CHG {chg}\"\n")
        f.write("features_updated:\n")
        for feat in sorted(features_updated):
            f.write(f"  - id: \"{feat}\"\n")
            f.write(f"    status: \"propagated\"\n")
        f.write("oracle_gate:\n")
        f.write("  action: skip\n")

    print(f"\n📄 治理报告已写入: {GOV_REPORT}")

    # ─── 方向指引 ───
    print("")
    print("─── 方向指引 ───")
    print("  📍 propagate 完成")

    if dry_run:
        print("")
        print("  这是预览模式（dry-run），未实际写入任何文件。")
        print("")
        print("  建议下一步:")
        print("    1. lx-oma-gov propagate --execute — 推荐 ✓")
        print("       说明：确认无误后执行实际写入")
        print("       适用场景：dry-run 预览内容符合预期，准备写入")
        print("    2. lx-oma-gov reconcile")
        print("       说明：如需调整变更内容，重新 reconcile")
        print("       适用场景：预览内容需要调整，回头修改再预览")
        print("    3. lx-oma-gov status")
        print("       说明：查看治理全景")
        print("       适用场景：想了解传播前整体治理状态")
        print("    4. 自定义操作")
        print("       → 输入你想要的命令")
    else:
        print("")
        print("  实际写入已完成。")
        print("")
        print("  建议下一步:")
        print("    1. lx-oma-gov status — 推荐 ✓")
        print("       说明：查看传播完成后各 feature 同步状态")
        print("       适用场景：确认传播结果")
        print("    2. lx-oma-gov audit")
        print("       说明：执行漂移检测，确认一致性")
        print("       适用场景：需要验证传播后各 feature 与 master 一致")
        print("    3. lx-oma-gov reconcile")
        print("       说明：开始下一轮 reconcile 循环")
        print("       适用场景：有新输入资料需再次检测变更")
        print("    4. 自定义操作")
        print("       → 输入你想要的命令")

    sys.exit(0)


if __name__ == "__main__":
    main()
