#!/usr/bin/env python3
"""
lx-oma-gov-resolve.py — L3 冲突裁决命令
Python 移植版，完全等价 lx-oma-gov-resolve.sh v1.0

来源: HUMAN-IN-THE-LOOP-GATE.md §1 + governance-spec.md §4
用法: python3 lx-oma-gov-resolve.py <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason "说明"]
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
CONSOLIDATION_LOG = PROJECT_ROOT / "CONSOLIDATION-LOG.md"
PENDING_DECISIONS = STATE_DIR / "pending-decisions.md"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if len(sys.argv) < 3:
        print("用法: lx-oma-gov-resolve <CONFLICT-ID> <accept|reject|accept-partial|defer> [--reason \"说明\"]", file=sys.stderr)
        print("", file=sys.stderr)
        print("裁决选项:", file=sys.stderr)
        print("  accept          完整接受，进入 master", file=sys.stderr)
        print("  accept-partial  部分接受（需配合 --targets）", file=sys.stderr)
        print("  reject          驳回，不进入 master", file=sys.stderr)
        print("  defer           暂缓，保留在 pending", file=sys.stderr)
        sys.exit(1)

    conflict_id = sys.argv[1]
    verdict = sys.argv[2]

    # Parse options
    reason = ""
    targets = ""
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--reason":
            i += 1
            if i < len(sys.argv):
                reason = sys.argv[i]
        elif sys.argv[i] == "--targets":
            i += 1
            if i < len(sys.argv):
                targets = sys.argv[i]
        else:
            print(f"未知选项: {sys.argv[i]}", file=sys.stderr)
            sys.exit(1)
        i += 1

    # Validate verdict
    valid_verdicts = {"accept", "reject", "defer", "accept-partial"}
    if verdict not in valid_verdicts:
        print(f"ERROR: 未知裁决 '{verdict}'。可用: accept, accept-partial, reject, defer", file=sys.stderr)
        sys.exit(1)
    if verdict == "accept-partial" and not targets:
        print("ERROR: accept-partial 需要 --targets 指定接受哪些对象", file=sys.stderr)
        sys.exit(1)

    # ─── Check prerequisites ───
    if not PENDING_DECISIONS.exists():
        print(f"ERROR: 未找到 pending-decisions.md ({PENDING_DECISIONS})", file=sys.stderr)
        print("提示: 请先运行 reconcile 产生 L3 冲突", file=sys.stderr)
        sys.exit(1)

    # ─── 1. Read conflict details from pending-decisions.md ───
    print(f"📖 查找 {conflict_id}...")
    content = PENDING_DECISIONS.read_text(encoding="utf-8")
    # Find the Open block
    lines = content.splitlines()
    conflict_start = -1
    for idx, line in enumerate(lines):
        if f"## Open" in line and conflict_id in line:
            conflict_start = idx
            break

    if conflict_start < 0:
        print(f"ERROR: {conflict_id} 未在 {PENDING_DECISIONS} 中找到", file=sys.stderr)
        print("提示: 运行 status 查看当前 open conflict 列表", file=sys.stderr)
        sys.exit(1)

    # Print conflict block
    end = conflict_start + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    conflict_block = "\n".join(lines[conflict_start:end])
    print(conflict_block)

    # ─── 2. Update CONSOLIDATION-LOG.md ───
    if CONSOLIDATION_LOG.exists():
        cl_content = CONSOLIDATION_LOG.read_text(encoding="utf-8")

        # Append adjudication record
        with open(CONSOLIDATION_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n### 裁决记录: {conflict_id}\n")
            f.write(f"- Adjudicated At: {NOW_UTC}\n")
            f.write(f"- Verdict: {verdict}\n")
            f.write(f"- Reason: {reason or '无'}\n")
            if targets:
                f.write(f"- Accepted Targets: {targets}\n")

        # Update status in the CL entry
        new_cl = re.sub(
            rf'({conflict_id}[\s\S]*?)(Status:)[^\n]*',
            rf'\1\2 {verdict}',
            cl_content
        )
        CONSOLIDATION_LOG.write_text(new_cl, encoding="utf-8")
        print("✅ CONSOLIDATION-LOG.md 已更新")

    # ─── 3. Update pending-decisions.md ───
    new_pending = content.replace(
        f"## Open {conflict_id}",
        f"## Resolved: {conflict_id} ({verdict})"
    )
    PENDING_DECISIONS.write_text(new_pending, encoding="utf-8")
    print(f"✅ {PENDING_DECISIONS} 已更新 ({conflict_id} → {verdict})")

    # ─── 4. Post-verdict actions ───
    print("")
    if verdict in ("accept", "accept-partial"):
        print(f"🔜 继续 reconcile 流程 — {conflict_id} 的变更将归并到 master")
        print("   运行 propagate --dry-run 预览传播内容")
    elif verdict == "reject":
        print(f"❌ {conflict_id} 已驳回，变更不归并到 master")
    elif verdict == "defer":
        print(f"⏸️  {conflict_id} 暂缓，保留 BLOCKED 状态")
        print("   下次 reconcile 时重新评估")

    print("")
    print("📋 裁决摘要:")
    print(f"  CONFLICT-ID: {conflict_id}")
    print(f"  Verdict: {verdict}")
    print(f"  Time: {NOW_UTC}")
    print(f"  Reason: {reason or '无'}")

    # ─── 方向指引 ───
    print("")
    print("─── 方向指引 ───")
    if verdict in ("accept", "accept-partial"):
        print("  变更已接受，可继续以下流程:")
        print("    1. lx-oma-gov propagate --dry-run — 推荐 ✓")
        print("       说明：预览传播内容")
        print("       适用场景：确认变更范围后再实际写入")
        print("    2. lx-oma-gov propagate --execute")
        print("       说明：dry-run 确认后执行实际传播")
        print("       适用场景：dry-run 已验证，准备写入")
        print("    3. lx-oma-gov status")
        print("       说明：查看治理全景")
        print("       适用场景：想了解整体治理状态")
    elif verdict == "reject":
        print("  变更已驳回。建议下一步:")
        print("    1. lx-oma-gov status — 推荐 ✓")
        print("       说明：查看更新后治理状态")
        print("       适用场景：确认驳回后各 feature 状态")
        print("    2. lx-oma-gov reconcile")
        print("       说明：如有新资料，重新 reconcile")
        print("       适用场景：有新的输入需要重新处理")
    elif verdict == "defer":
        print("  变更已暂缓。建议下一步:")
        print("    1. lx-oma-gov status — 推荐 ✓")
        print("       说明：查看待处理的 BLOCKED 项")
        print("       适用场景：了解当前所有挂起的冲突")
        print(f"    2. 收集更多信息后重新裁决")
        print(f"       说明：lx-oma-gov resolve {conflict_id} accept|reject")
        print("       适用场景：已收集到补充信息，准备重新裁决")
    print("    4. 自定义操作")
    print("       → 输入你想要的命令")

    sys.exit(0)


if __name__ == "__main__":
    main()
