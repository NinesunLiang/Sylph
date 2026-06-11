#!/usr/bin/env python3
"""posttool-score-archiver.py — SessionStart — 将 auto-score / ux-score 报告归档到 .claude/data/score/daily/

逻辑：
1. 扫描 .omc/state/ 下 auto-score-*.json 和 ux-score-report-*.json
2. 按日期提取（从文件名或内容中的 date 字段）
3. 归档到 .claude/data/score/daily/{date}.json（追加剧合）
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from harness_lib import hc_enabled, flywheel_event, PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()


def _extract_date_from_path(path: Path):
    """从文件名提取 YYYY-MM-DD 日期"""
    m = re.search(r'(\d{4}-\d{2}-\d{2})', path.name)
    if m:
        return m.group(1)
    return None


def _extract_date_from_content(content: str):
    """从 JSON 内容中提取 date 或 generated_at 字段"""
    try:
        data = json.loads(content)
        for key in ('date', 'generated_at', 'report_date', 'timestamp'):
            val = data.get(key)
            if val:
                if isinstance(val, (int, float)):
                    return datetime.fromtimestamp(val, tz=timezone.utc).strftime('%Y-%m-%d')
                if isinstance(val, str):
                    m = re.search(r'(\d{4}-\d{2}-\d{2})', val)
                    if m:
                        return m.group(1)
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def main():
    try:
        if not hc_enabled("score_archiver"):
            sys.exit(0)
    except Exception:
        pass

    project_root = PROJECT_ROOT
    state_dir = project_root / ".omc" / "state"
    score_dir = project_root / ".claude" / "data" / "score"
    daily_dir = score_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    if not state_dir.exists():
        sys.exit(0)

    # ── 扫描评分文件 ──
    score_patterns = ("auto-score-*.json", "auto_score_*.json",
                      "ux-score-report-*.json", "ux_score_report_*.json")
    score_files = []
    for pattern in score_patterns:
        score_files.extend(sorted(state_dir.glob(pattern)))

    if not score_files:
        sys.exit(0)

    archived_count = 0
    newly_written = set()

    for sf in score_files:
        try:
            content = sf.read_text(encoding="utf-8")
        except Exception:
            continue

        if not content.strip():
            continue

        date_str = _extract_date_from_path(sf)
        if not date_str:
            date_str = _extract_date_from_content(content)
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        daily_path = daily_dir / f"{date_str}.json"

        # 追加模式：读取已有内容追加到同天文件
        daily_records = []
        if daily_path.exists():
            try:
                existing = json.loads(daily_path.read_text(encoding="utf-8"))
                if isinstance(existing, list):
                    daily_records = existing
            except (json.JSONDecodeError, Exception):
                daily_records = []

        # 解析当前文件为单个记录或列表
        try:
            record = json.loads(content)
        except json.JSONDecodeError:
            continue

        if isinstance(record, list):
            daily_records.extend(record)
        else:
            # 标记来源
            if "source_file" not in record:
                record["source_file"] = sf.name
            daily_records.append(record)

        # 去重（按 source_file + date）
        seen = set()
        deduped = []
        for r in daily_records:
            key = f"{r.get('source_file', '')}|{r.get('date', '')}"
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        daily_path.write_text(
            json.dumps(deduped, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        newly_written.add(date_str)
        archived_count += 1

    # flywheel 事件
    try:
        flywheel_event("score_archiver", f"archived {archived_count} files to {len(newly_written)} daily files", "P3")
    except Exception:
        pass

    # 输出归档摘要
    if newly_written:
        dates = sorted(newly_written)
        print(f"Score archiver: {archived_count} files → daily/{', '.join(dates[:5])}" +
              (f"... +{len(dates)-5} more" if len(dates) > 5 else ""))


if __name__ == "__main__":
    main()
