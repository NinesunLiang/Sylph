#!/usr/bin/env python3
"""score-archiver.py — Stop — 归档评分报告到 .claude/data/score/daily/

迁移 .omc/state/auto-score-*.json → .claude/data/score/daily/{date}.json
仅归档最新的评分报告（按天去重），不删除源文件。
"""
import json
import os
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
try:
    from harness_lib import hc_enabled, flywheel_event, PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = (_SCRIPT_DIR / "../..").resolve()


def _extract_date(filename):
    """从 auto-score-{date}.json 提取 YYYY-MM-DD"""
    m = re.search(r'auto-score-(\d{4})(\d{2})(\d{2})-', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r'score-ux-(\d{4})(\d{2})(\d{2})-', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def main():
    try:
        if not hc_enabled("score_archiver"):
            sys.exit(0)
    except Exception:
        pass

    project_root = PROJECT_ROOT
    state_dir = project_root / ".omc" / "state"
    score_dir = project_root / ".claude" / "data" / "score" / "daily"
    score_dir.mkdir(parents=True, exist_ok=True)

    if not state_dir.exists():
        sys.exit(0)

    archived = 0
    for f in state_dir.glob("auto-score-*.json"):
        date_key = _extract_date(f.name)
        if not date_key:
            continue
        target = score_dir / f"{date_key}.json"
        if target.exists():
            continue  # 已存在的不覆盖
        try:
            content = f.read_text(encoding="utf-8")
            # Validate JSON before copying
            json.loads(content)
            target.write_text(content, encoding="utf-8")
            archived += 1
        except (json.JSONDecodeError, Exception):
            pass

    for f in state_dir.glob("score-ux-*.json"):
        date_key = _extract_date(f.name)
        if not date_key:
            continue
        target = score_dir / f"ux-{date_key}.json"
        if target.exists():
            continue
        try:
            content = f.read_text(encoding="utf-8")
            json.loads(content)
            target.write_text(content, encoding="utf-8")
            archived += 1
        except (json.JSONDecodeError, Exception):
            pass

    if archived > 0:
        flywheel_event("score_archiver", f"archived_{archived}_scores", "P2")
    sys.exit(0)


if __name__ == "__main__":
    main()
