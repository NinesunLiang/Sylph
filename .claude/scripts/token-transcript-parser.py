#!/usr/bin/env python3
"""
token-transcript-parser.py — 从 transcript.jsonl 提取真实 token 耗用

解析 Claude Code session transcript，从每个 assistant 消息的 usage 字段
提取平台真实 token 计数（input/cache_read/cache_create/output）。

输出：
  stdout: JSON 摘要（供 shell hook 消费）
  .omc/state/token-tracking-real.json: 持久化记录（每次执行更新）

方法：
  context_used = input_tokens + cache_read_input_tokens + cache_creation_input_tokens

Compact 检测：
  连续 assistant 消息间 context_used 下降超过 30% 视为一次 compact。
  savings += 下降前 - 下降后

用法：
  python3 token-transcript-parser.py [--transcript PATH] [--write]
    --transcript PATH  指定 transcript 文件（默认自动查找最新）
    --write            写入 state 文件（默认只输出到 stdout）
"""

import argparse
import json
import os
import sys
from pathlib import Path

STATE_DIR = Path(".omc/state")
PROJECT_DIR = Path.cwd()
HOME = Path.home()


def find_project_transcripts():
    """Find transcript files for the current project, sorted by mtime DESC."""
    encoded_cwd = "-".join(PROJECT_DIR.resolve().parts).lstrip("/")
    transcript_dir = HOME / ".claude" / "projects" / encoded_cwd

    if not transcript_dir.exists():
        # Fallback: search all project dirs for most recent
        all_projects = HOME / ".claude" / "projects"
        candidates = []
        for pdir in all_projects.iterdir():
            if pdir.is_dir():
                for f in sorted(pdir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
                    candidates.append(f)
        # Return top 3 most recent across all projects
        return sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True)[:3]

    transcripts = sorted(transcript_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
    return transcripts


def parse_transcript(transcript_path):
    """
    Parse transcript.jsonl and extract usage data.

    Returns dict with all metrics or None on failure.
    """
    path = Path(transcript_path)
    if not path.exists():
        return None

    usage_seq = []
    session_id = path.stem  # filename without .jsonl

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "assistant":
                continue

            msg = entry.get("message", {})
            usage = msg.get("usage", {})

            # Must have at least input_tokens
            inp = usage.get("input_tokens", -1)
            if inp < 0:
                continue

            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            output = usage.get("output_tokens", 0)
            context_used = inp + cache_read + cache_create

            usage_seq.append({
                "input_tokens": inp,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
                "output_tokens": output,
                "context_used": context_used,
            })

    if not usage_seq:
        return None

    # Totals
    total_input = sum(u["input_tokens"] for u in usage_seq)
    total_cache_read = sum(u["cache_read_input_tokens"] for u in usage_seq)
    total_cache_create = sum(u["cache_creation_input_tokens"] for u in usage_seq)
    total_output = sum(u["output_tokens"] for u in usage_seq)

    # Peak context (max context_used across all turns)
    peak_context = max(u["context_used"] for u in usage_seq)

    # Current context (last turn)
    current_context = usage_seq[-1]["context_used"]

    # Session start baseline (first message context cost)
    session_start_cost = usage_seq[0]["context_used"]

    # Compact detection: consecutive drop > 30%
    compact_events = 0
    compact_savings = 0
    for i in range(1, len(usage_seq)):
        prev_ctx = usage_seq[i - 1]["context_used"]
        curr_ctx = usage_seq[i]["context_used"]
        if prev_ctx > 0 and curr_ctx < prev_ctx * 0.7:
            drop = prev_ctx - curr_ctx
            compact_events += 1
            compact_savings += drop

    return {
        "session_id": session_id,
        "transcript_path": str(path.resolve()),
        "total_turns": len(usage_seq),
        "current_context": current_context,
        "peak_context": peak_context,
        "session_start_cost": session_start_cost,
        "total_input_tokens": total_input,
        "total_cache_read_tokens": total_cache_read,
        "total_cache_create_tokens": total_cache_create,
        "total_output_tokens": total_output,
        "total_context_used": total_input + total_cache_read + total_cache_create,
        "compact_events": compact_events,
        "compact_savings": compact_savings,
        "last_updated": __import__("datetime").datetime.now().isoformat(),
    }


def write_state(data):
    """Write token-tracking-real.json to state dir."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / "token-tracking-real.json"
    state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return state_file


def main():
    parser = argparse.ArgumentParser(description="Parse transcript for real token usage")
    parser.add_argument("--transcript", "-t", help="Path to transcript.jsonl")
    parser.add_argument("--write", "-w", action="store_true", help="Write to token-tracking-real.json")
    args = parser.parse_args()

    # Find transcript
    if args.transcript:
        transcript_path = Path(args.transcript)
    else:
        candidates = find_project_transcripts()
        if not candidates:
            print(json.dumps({"error": "No transcript found"}, ensure_ascii=False))
            sys.exit(1)
        transcript_path = candidates[0]

    # Parse
    result = parse_transcript(transcript_path)
    if result is None:
        print(json.dumps({"error": f"No usage data in {transcript_path}"}, ensure_ascii=False))
        sys.exit(1)

    # Add context limit info
    result["context_limit"] = 200000
    result["context_pct"] = round(result["current_context"] * 100 / 200000, 1)

    # Write state file
    if args.write:
        written = write_state(result)
        result["state_file"] = str(written)

    # Output JSON
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
