#!/usr/bin/env python3
"""
intent-tracker.py — PostToolUse:Edit|Write — 跟踪文件级编辑统计 + revert 检测

Role: 跟踪编辑次数、检测内容回退（revert）、标记高频编辑（churn）

原理：
  PostToolUse 不暴露 AI 输出文本，无法直接检测语义矛盾（已知约束）。
  替代方案（均为文件级统计，非语义分析）：
  1. 跟踪每个文件在会话内的编辑次数，5+ 次编辑 = churn（标记"高频改动"）
  2. 跟踪文件内容哈希序列，检测 revert 模式（内容回到前一个哈希的版本）
  注意：churn ≠ 矛盾，revert ≠ 矛盾。本 hook 只做统计标记，不推断意图。
"""

import fcntl
import hashlib
import json
import os
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    extract_file_path, sanitize_text, output_continue,
    PROJECT_ROOT, STATE_DIR,
)


def main():
    if not hc_enabled("intent_tracker"):
        print(json.dumps({"continue": True}))
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Extract file_path
    file_path = extract_file_path(input_str)
    if not file_path:
        output_continue()
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    contradiction_log = STATE_DIR / "edit-churn-log.jsonl"
    now = int(time.time())

    # Generate content hash tracking key
    content_hash_key = hashlib.md5(file_path.encode()).hexdigest()

    # Read existing records + content history
    previous = []
    content_history = {}  # content_hash_key -> list of (ts, content_hash)

    if contradiction_log.exists():
        try:
            with open(str(contradiction_log), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        previous.append(rec)
                        if rec.get("type") == "edit" and rec.get("content_hash") and rec.get("content_hash_key"):
                            k = rec["content_hash_key"]
                            if k not in content_history:
                                content_history[k] = []
                            content_history[k].append((rec.get("ts", 0), rec["content_hash"]))
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass

    # Compute current content hash
    content_hash = ""
    try:
        with open(file_path, encoding="utf-8") as f:
            c = f.read()
        content_hash = hashlib.md5(c.encode()).hexdigest()[:16]
    except OSError:
        pass

    # Build signature
    sig = content_hash_key[:16]

    # Check for revert pattern
    revert_of_hash = None
    if content_hash and content_hash_key in content_history:
        for prev_ts, prev_hash in content_history[content_hash_key]:
            if prev_hash == content_hash and prev_ts < now:
                revert_of_hash = prev_ts
                break

    # Check for churn keyword
    churn_keyword = None
    if revert_of_hash is None and content_hash:
        for rec in reversed(previous):
            if rec.get("content_hash_key") == content_hash_key and rec.get("type") == "edit":
                kw = rec.get("diagnostic_keyword", "")
                if kw and len(kw) > 4:
                    churn_keyword = kw
                    break

    # Compute edit count
    edit_count = sum(1 for r in previous if r.get("sig") == sig) + 1

    # Determine contradiction level
    message = ""
    contradiction_level = 0
    contradiction_type = "first_edit"

    # E6 矛盾检测 — 降级阈值至 4 次编辑
    # 3次编辑 + 内容哈希变化≥2次 → content_flip（来回修改同一段逻辑）
    if edit_count >= 4:
        # Dedup: skip if same file already has churn entry within last hour
        recent_churn = False
        for r in reversed(previous):
            if r.get("sig") == sig and r.get("type") == "churn" and r.get("level") == 2:
                if now - r.get("ts", 0) < 3600:
                    recent_churn = True
                break
        if recent_churn:
            contradiction_level = 0
            contradiction_type = "dedup_churn"
        else:
            contradiction_level = 2
            contradiction_type = "churn"
            message = (f"[intent-tracker] 编辑抖动: 文件 {file_path} "
                       f"本会话已被编辑 {edit_count} 次，高频改动。")
    elif edit_count >= 3:
        # 3次编辑 — 检查内容是否有反复变化
        prev_hashes = set(r.get("content_hash", "") for r in previous
                         if r.get("sig") == sig and r.get("type") == "edit" and r.get("content_hash"))
        if len(prev_hashes) >= 2:
            contradiction_level = 2
            contradiction_type = "content_flip"
            message = (f"[intent-tracker] 内容反复: 文件 {file_path} "
                       f"本会话第 {edit_count} 次编辑，已产生 {len(prev_hashes)} 个不同版本，"
                       f"内容在多个版本间来回切换。")
    elif revert_of_hash is not None:
        contradiction_level = 2
        contradiction_type = "revert"
        message = (f"[intent-tracker] revert 检测: 文件 {file_path} "
                   f"内容回退到之前的状态（哈希 {content_hash}）。"
                   f"本会话第 {edit_count} 次编辑" +
                   (f"，注意内容方向变化。" if churn_keyword else "。"))
    elif churn_keyword:
        contradiction_level = 1
        contradiction_type = "churn_keyword"
        message = (f"[intent-tracker] 文件 {file_path} 第 {edit_count} 次编辑，"
                   f"检测到关键词 '{churn_keyword}' 前后变动。")
    elif edit_count >= 2:
        contradiction_level = 1
        contradiction_type = "revisit"
        message = (f"[intent-tracker] 文件 {file_path} 本会话第 {edit_count} 次编辑。")

    if message and contradiction_level >= 1:
        print(message, file=sys.stderr)

    record = {
        "ts": now,
        "sig": sig,
        "content_hash_key": content_hash_key,
        "content_hash": content_hash or "",
        "revert_of": revert_of_hash,
        "file": file_path,
        "edit_count": edit_count,
        "contradiction": contradiction_level >= 2 or contradiction_type == "churn_keyword",
        "level": contradiction_level,
        "type": contradiction_type,
    }

    # Append to log (atomic flock)
    try:
        with open(str(contradiction_log), "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass

    # Output additionalContext for level 2+ (real contradiction)
    if contradiction_level >= 2:
        # Build detailed context
        file_edits = [r for r in reversed(previous) if r.get("sig") == sig]
        history_summary = ""
        if len(file_edits) > 1:
            prev_types = [r.get("type", "?") for r in file_edits[:3]]
            history_summary = f"。编辑历史: {', '.join(prev_types)}"

        resolution = ("建议: (1) 若内容回退, 确认目标版本正确后重新编辑; "
                      "(2) 若频繁 churn, 先固化设计再改; "
                      "(3) 检查前几次编辑是否被意外撤销。")

        ctx = (f"[intent-tracker] {'内容回退' if revert_of_hash else '编辑抖动'}"
               f": 文件 {file_path} "
               f"本会话第 {edit_count} 次编辑{'，内容回退到历史版本' if revert_of_hash else '，高频改动'}"
               f"{history_summary}。{resolution}")

        ctx = sanitize_text(ctx)
        print(json.dumps({
            "continue": True,
            "hookSpecificOutput": {"additionalContext": ctx},
        }))

    flywheel_event("intent_tracker", "recorded", "P2")

    # M2: edit-churn-log rotation (>512KB → archive, keep 3)
    try:
        clog_size = contradiction_log.stat().st_size
        if clog_size > 524288:
            clog_ts = int(time.time())
            archive_path = Path(str(contradiction_log) + f".{clog_ts}")
            contradiction_log.rename(archive_path)
            contradiction_log.touch()

            # Keep only last 3 archives
            archives = sorted(
                Path(str(contradiction_log) + ".*").glob("*") if False else
                [p for p in contradiction_log.parent.glob(f"{contradiction_log.name}.*")],
            )
            for p in archives[:-3]:
                try:
                    p.unlink()
                except OSError:
                    pass
    except (OSError, ValueError):
        pass

    output_continue()


if __name__ == "__main__":
    main()
