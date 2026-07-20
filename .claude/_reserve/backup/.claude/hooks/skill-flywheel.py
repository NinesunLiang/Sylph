#!/usr/bin/env python3
"""
skill-flywheel.py — Stop — 停止时更新 skill 使用频率，驱动飞轮优化（含时间戳追踪）
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event


def main():
    if not hc_enabled("skill_flywheel"):
        sys.exit(0)

    home = Path.home()
    buffer_file = home / ".claude" / "flywheel-buffer.jsonl"
    flywheel_file = home / ".claude" / "flywheel.log"

    # buffer 不存在或为空则静默退出
    if not buffer_file.exists() or buffer_file.stat().st_size == 0:
        sys.exit(0)

    # 确保 flywheel.log 目录存在
    flywheel_file.parent.mkdir(parents=True, exist_ok=True)

    # flush: 将 buffer 内容追加到 flywheel.log，附带时间戳标记
    try:
        buffer_content = buffer_file.read_text(encoding="utf-8")
    except Exception:
        sys.exit(0)

    if not buffer_content.strip():
        buffer_file.unlink(missing_ok=True)
        sys.exit(0)

    ts = int(time.time())
    ts_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 写入时间戳标记 + buffer 内容
    try:
        with open(str(flywheel_file), "a", encoding="utf-8") as f:
            f.write(f"# ts={ts} iso={ts_iso}\n")
            f.write(buffer_content)
            if not buffer_content.endswith("\n"):
                f.write("\n")
    except Exception:
        pass

    # 消费 buffer
    buffer_file.unlink(missing_ok=True)

    lines = buffer_content.strip().splitlines()
    line_count = len(lines)

    # Analytics: compute per-skill frequency and deprecation detection
    project_root = (_HOOKS_DIR / "../..").resolve()
    analytics_script = project_root / ".claude" / "scripts" / "flywheel_analytics.py"
    if analytics_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(analytics_script),
                 str(flywheel_file),
                 str(project_root / ".omc" / "state" / "flywheel-report.json")],
                capture_output=True, timeout=30
            )
        except Exception:
            pass

    # GS-002: Deprecated skill notification
    report_file = project_root / ".omc" / "state" / "flywheel-report.json"
    if report_file.exists():
        try:
            with open(str(report_file), encoding="utf-8") as f:
                report = json.load(f)
            dep_skills = report.get("deprecated_skills", [])
            if dep_skills:
                skills = report.get("skills", {})
                lines_out = [f"[flywheel] ⚠️ {len(dep_skills)} 个技能已废弃 (>30天未使用):"]
                for name in dep_skills:
                    info = skills.get(name, {})
                    days = info.get("days_since_last_use", "?")
                    lines_out.append(f" · {name} — 上次使用: {days} 天前")
                dep_file = project_root / ".omc" / "state" / "flywheel-deprecated-skills.txt"
                dep_file.write_text("\n".join(lines_out), encoding="utf-8")
        except Exception:
            pass

    flywheel_event("skill_flywheel", "flywheel_flushed", "P2", "flushed")
    sys.exit(0)


if __name__ == "__main__":
    main()
