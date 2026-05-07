#!/usr/bin/env python3

import json, sys, os

from pathlib import Path


def get_project_root():
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd()


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

    state_file = root / ".omc" / "state" / "token-tracking-index.json"
    usage = 0
    limit = token_limit

    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            usage = data.get("usage", 0)
            limit = data.get("limit", 200000)
        except Exception:
            pass

    if limit == 0:
        limit = 200000

    # 会话过期防御：如果 state_file 的 last_updated 超过 5 分钟前，
    # 说明这是一个新会话且 token_writer --reset 尚未运行（死锁保护）。
    # 此时将 usage 视为 0，防止旧会话残留数据导致硬阻断。
    if state_file.exists():
        try:
            import time
            file_age = time.time() - state_file.stat().st_mtime
            if file_age > 300 and data.get("usage", 0) > 0:
                usage = 0
        except Exception:
            pass

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
    }
    print(json.dumps(output))


if __name__ == "__main__":
    check_context()
