#!/usr/bin/env python3

import json, sys, os, time
from datetime import datetime
from pathlib import Path


def get_project_root():
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def _project_transcript_dir(root):
    """Resolve the Claude Code transcript directory for this project.

    Claude Code normalizes the project path: dots, underscores, and
    special chars are replaced with hyphens in the directory encoding.
    """
    home = Path.home()
    # Match Claude Code's path encoding: replace . and _ with -
    parts = [p.replace(".", "-").replace("_", "-") for p in root.resolve().parts]
    encoded = "-".join(parts).lstrip("/")
    return home / ".claude" / "projects" / encoded


def get_real_context(transcript_dir):
    """Parse transcript to get real context from API usage data.

    Reads assistant messages in the latest transcript, extracts
    usage.input_tokens from each API response. Always 1 turn behind
    (the latest API call's usage is recorded after response).

    Returns dict with current_context, context_pct, context_limit, or None.
    """
    if not transcript_dir.is_dir():
        return None

    # Find latest transcript for this session
    transcripts = sorted(transcript_dir.glob("*.jsonl"),
                         key=lambda x: x.stat().st_mtime, reverse=True)
    if not transcripts:
        return None

    path = transcripts[0]
    usage_seq = []
    context_limit = 200000  # Claude default 200K context

    try:
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
                inp = usage.get("input_tokens", -1)
                if inp < 0:
                    continue
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_create = usage.get("cache_creation_input_tokens", 0)
                # Schema detection: some API variants report input_tokens as total
                # (including cache_read), others report it as new-only.
                # If input_tokens >= cache_read_input_tokens, it likely includes cache.
                if cache_read > 0 and inp >= cache_read:
                    context_used = inp + cache_create  # cache_read already in inp
                else:
                    context_used = inp + cache_read + cache_create
                usage_seq.append(context_used)
    except (OSError, json.JSONDecodeError):
        return None

    if not usage_seq:
        return None

    current_context = usage_seq[-1]
    peak_context = max(usage_seq)
    context_pct = round(current_context * 100 / context_limit, 1)

    return {
        "current_context": current_context,
        "context_pct": context_pct,
        "context_limit": context_limit,
        "peak_context": peak_context,
        "source": "transcript",
        "last_updated": datetime.now().isoformat(),
    }


def _read_config(root):
    """从 .harness-cache 读取 context_guard 阈值"""
    cache_file = root / ".omc" / "state" / ".harness-cache"
    config = {}
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        k, v = line.split('=', 1)
                        config[k] = v
        except Exception:
            pass
    return config


def check_context():
    root = get_project_root()
    config = _read_config(root)

    # 阈值：env 覆盖 > harness.yaml > 默认
    warn_pct = float(os.environ.get(
        "CONTEXT_WARN_THRESHOLD",
        config.get("context_guard.warn_threshold", "50")
    ))
    danger_pct = float(os.environ.get(
        "CONTEXT_DANGER_THRESHOLD",
        config.get("context_guard.danger_threshold", "80")
    ))
    token_limit = int(float(os.environ.get(
        "CONTEXT_TOKEN_LIMIT",
        config.get("token_tracking.limit", "200000")
    )))

    # ─── Layer 1: 真实上下文（从 transcript API usage 解析，落后 1 轮但准确）───
    # CONTEXT_FORCE_HEURISTIC=1 跳过真实上下文，强制使用启发式文件（测试用）
    real = None
    if not os.environ.get("CONTEXT_FORCE_HEURISTIC"):
        real = get_real_context(_project_transcript_dir(root))

    usage = 0
    limit = token_limit
    source = "none"

    if real is not None:
        usage = real["current_context"]
        limit = real["context_limit"]
        source = "transcript (real)"
    else:
        # ─── Layer 2: 轮次估算（基于 turns × per_turn，与 transcript 趋势一致）───
        # 累计计数器（token_writer.sh）会无边界增长，而真实上下文是每轮快照。
        # 轮次模型：base_cost(25K 系统提示+知识注入) + turns × 1.5K(每轮平均增长)
        turns_file = root / ".omc" / "state" / "session-turns.json"
        turns = 0
        if turns_file.exists():
            try:
                with open(turns_file) as f:
                    _data = json.load(f)
                turns = _data.get("count", 0)
                # 会话过期防御：文件超过 5 分钟前修改 → 新会话未重置
                file_age = time.time() - turns_file.stat().st_mtime
                if file_age > 300 and turns > 0:
                    turns = 0
            except Exception:
                pass

        if turns > 0:
            # 模型：25K 基础 + 每轮 1.5K
            usage = min(25000 + turns * 1500, token_limit)
            source = "heuristic (turn-estimated)"
        else:
            # ─── Layer 3: 终极兜底 — 旧累计计数器（无轮次文件时）───
            state_file = root / ".omc" / "state" / "token-tracking-index.json"
            if state_file.exists():
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    usage = data.get("usage", 0)
                    limit = data.get("limit", 200000)
                    file_age = time.time() - state_file.stat().st_mtime
                    if file_age > 300 and usage > 0:
                        usage = 0
                except Exception:
                    pass
            source = "heuristic (cumulative)"

    if limit == 0:
        limit = 200000

    ratio = usage / limit
    warn_ratio = warn_pct / 100.0
    danger_ratio = danger_pct / 100.0

    # Sweet-spot / Hand-off Alert
    sweet_spot_msg = ""
    if warn_ratio <= ratio < danger_ratio:
        sweet_spot_msg = (
            f"[context_alert]: 当前上下文已达甜点区上限 "
            f"( {ratio:.1%}，阈值 {warn_pct:.0f}% )。"
            f"请运行 /compact 压缩会话或开启新分支。"
        )

    # JSON output for the bash hook to consume
    output = {
        "usage": usage,
        "limit": limit,
        "percentage": ratio * 100,
        "thresholds": {
            "warn": warn_pct,
            "danger": danger_pct
        },
        "is_danger": ratio >= danger_ratio,
        "sweet_spot_warning": sweet_spot_msg,
        "source": source,
        "source_label": "真实上下文" if "transcript" in source else (
            "轮次估算" if "turn" in source else "累计计数器兜底"
        ),
    }
    print(json.dumps(output))


if __name__ == "__main__":
    check_context()
