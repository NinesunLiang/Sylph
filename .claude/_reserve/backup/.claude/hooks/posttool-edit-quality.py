#!/usr/bin/env python3
"""
posttool-edit-quality.py — PostToolUse:Edit|Write — 编辑后自查代码风格、文档同步、方案复用检测
Role: 编辑后自查代码风格、文档同步、方案复用检测
对应 posttool-edit-quality.sh 的 Python 移植
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, hc_get, HOME_DIR


def _fnmatch(name, pattern):
    """Simple shell glob matching."""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def main():
    # hc_enabled check
    if not hc_enabled("posttool_edit_quality"):
        output_continue()
        return

    raw_input = sys.stdin.read()

    try:
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        data = {}

    # Extract file_path
    tool_input = data.get("tool_input", {}) or {}
    args = data.get("args", {}) or {}
    file_path = ""
    if isinstance(tool_input, dict):
        file_path = tool_input.get("file_path", "")
    if not file_path and isinstance(args, dict):
        file_path = args.get("filePath", "")

    if not file_path:
        output_continue()
        return

    # 非源代码文件直接放行
    source_ext = hc_get("project.source_extensions", "*.go")
    filename = Path(file_path).name
    source_match = False
    for ext in source_ext.split():
        if _fnmatch(filename, ext):
            source_match = True
            break

    if not source_match:
        output_continue()
        return

    quality_checklist = hc_get("architecture.quality_checklist",
                                "命名§4.2 | 导入三段式§4.3 | 错误处理§4.4 | 函数长度§4.5 | 日志纯英文§G-7")
    msg = f"代码已修改({filename})。自查: {quality_checklist}"

    # 核心业务层追加文档同步提醒
    business_layers = hc_get("architecture.business_layers", "*/logic/* */model/* */executor/* */ai/*")
    doc_sync_target = hc_get("architecture.doc_sync_target", "executor.md")
    for layer in business_layers.split():
        if _fnmatch(file_path, layer):
            msg = f"{msg} | 文档同步: 若涉及状态/接口变更，更新{doc_sync_target}"
            break

    # Handler 层追加架构约束提醒
    handler_layers = hc_get("architecture.handler_layers", "*/handler/*")
    handler_constraint = hc_get("architecture.handler_constraint", "Handler禁止直接调用Model(§4.1)")
    for layer in handler_layers.split():
        if _fnmatch(file_path, layer):
            msg = f"{msg} | 注意: {handler_constraint}"
            break

    # 方案复用检测
    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    edit_history = state_dir / "edit-history.log"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 记录本次编辑文件
    real_path = str(Path(file_path).resolve())
    now_ts = int(time.time())
    with open(str(edit_history), "a", encoding="utf-8") as f:
        f.write(f"{now_ts} {real_path}\n")

    # 清理超过 30 分钟的记录
    cutoff = now_ts - 1800
    temp_lines = []
    if edit_history.exists():
        with open(str(edit_history), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if parts and parts[0].isdigit() and int(parts[0]) >= cutoff:
                    temp_lines.append(line)
    with open(str(edit_history), "w", encoding="utf-8") as f:
        for line in temp_lines:
            f.write(line + "\n")

    # 统计本次批量编辑的文件数
    current_files = sorted(set(p.split(None, 1)[1] for p in temp_lines if len(p.split(None, 1)) > 1))
    file_count = len(current_files)

    if file_count >= 3:
        previous_edit_file = state_dir / "previous-edit-batch.log"
        if previous_edit_file.exists():
            prev_files = []
            with open(str(previous_edit_file), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        prev_files.append(line)

            prev_count = len(prev_files)
            if prev_count > 0:
                match_count = sum(1 for f in prev_files if f in current_files)
                overlap_pct = int(match_count * 100 / prev_count)
                if overlap_pct > 60:
                    msg = (f"{msg} | ⚠️ 方案复用检测: 本次编辑 {file_count} 个文件与上次({prev_count} 个)重合度 "
                           f"{overlap_pct}%。请执行复用自检(宪法第十条): [1]文件集重合≥80% [2]接口契约未变 [3]场景类型一致 "
                           f"[4]状态机未改。未通过自检禁止直接套用旧方案。")

        # 保存本次文件集
        with open(str(previous_edit_file), "w", encoding="utf-8") as f:
            for fp in current_files:
                f.write(fp + "\n")

    # === AC-3: 工具响应异常检测 → claude-next.md 追加 ===
    claude_next = project_root / ".claude" / "claude-next.md"
    anomaly_tracker = state_dir / "edit-quality-anomalies.json"

    # Anomaly detection
    ti = data.get("tool_input", {}) or {}
    old_str = ti.get("old_string", "") or ""
    new_str = ti.get("new_string", "") or ""
    content = ti.get("content", "") or ""
    max_change = max(len(old_str), len(new_str), len(content))

    anomalies = []
    if max_change > 500:
        anomalies.append(("large_edit", f"{file_path} ({max_change} chars)"))

    if edit_history.exists():
        try:
            with open(str(edit_history), "r", encoding="utf-8") as f:
                recent_edits = [l.strip().split() for l in f if l.strip()]
            same_file_count = 0
            for parts in recent_edits:
                if len(parts) >= 2 and parts[1] == file_path:
                    try:
                        ts = int(parts[0])
                        if now_ts - ts < 60:
                            same_file_count += 1
                    except (ValueError, IndexError):
                        pass
            if same_file_count >= 3:
                anomalies.append(("rapid_edit", f"{file_path} ({same_file_count} edits/60s)"))
        except (OSError, ValueError, IndexError):
            pass

    if anomalies:
        tracked = {}
        if anomaly_tracker.exists():
            try:
                with open(str(anomaly_tracker), "r", encoding="utf-8") as f:
                    tracked = json.load(f)
            except (json.JSONDecodeError, OSError):
                tracked = {}

        new_entries = [a for a in anomalies if a[0] not in tracked]
        if new_entries:
            for sig, _ in new_entries:
                tracked[sig] = {"ts": now_ts, "file": file_path}
            with open(str(anomaly_tracker), "w", encoding="utf-8") as f:
                json.dump(tracked, f, indent=2)

            entry_date = datetime.now().strftime("%Y-%m-%d")
            lines = []
            lines.append(f"\n### [auto-detect:{entry_date}] Edit anomaly pattern\n")
            lines.append(f"@{entry_date} hits:1\n")
            anomaly_names = {"large_edit": "大编辑块", "rapid_edit": "快速连续编辑"}
            for sig, desc in new_entries:
                name = anomaly_names.get(sig, sig)
                lines.append(f"**模式**: {name} — {desc}")
                lines.append(f"触发条件：编辑工具调用中出现 {name} 模式")
                lines.append(f"建议：拆分大编辑为多个小编辑，或预先规划减少快速修正\n")

            if claude_next.exists():
                existing = claude_next.read_text(encoding="utf-8", errors="replace")
                with open(str(claude_next), "a", encoding="utf-8") as f:
                    for line in lines:
                        if line not in existing:
                            f.write(line + "\n")
            else:
                with open(str(claude_next), "w", encoding="utf-8") as f:
                    for line in lines:
                        f.write(line + "\n")

            anomaly_msg = ", ".join(a[0] for a in new_entries)
            msg = f"{msg} | 编辑异常检测: {anomaly_msg}"

    print(hc_emit_hook_json(msg, "PostToolUse", True))
    flywheel_event("posttool_edit_quality", "quality_checked", "P2", "checked")
    sys.exit(0)


if __name__ == "__main__":
    main()
