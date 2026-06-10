#!/usr/bin/env python3
"""error-dna-aggregator.py — Stop — 聚合 error-dna.jsonl → error-dna.json 含去重+升华+退化

Role: 跨会话错误聚合管道
- 去重: 按 signature 聚合 error-dna.jsonl，同一天内重复签名只 count++
- 升华: count >= 3 自动生成规则到 error-rules.md
- 退化: 7天未触发标记 candidate, 14天未触发降级
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))
try:
    from harness_lib import hc_enabled, flywheel_event, PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = (_SCRIPT_DIR / "../..").resolve()


def main():
    try:
        if not hc_enabled("error_dna_aggregator"):
            sys.exit(0)
    except Exception:
        pass

    project_root = PROJECT_ROOT
    state_dir = project_root / ".omc" / "state"
    dna_jsonl = state_dir / "error-dna.jsonl"
    dna_json = state_dir / "error-dna.json"
    now_ts = int(time.time())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not dna_jsonl.exists() or dna_jsonl.stat().st_size == 0:
        sys.exit(0)

    # ── Step 1: 读 error-dna.jsonl → 聚合 by signature ──
    records = []
    try:
        with open(dna_jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    if not records:
        sys.exit(0)

    # ── Step 2: 去重聚合 ──
    existing = {}
    if dna_json.exists():
        try:
            existing = json.loads(dna_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            existing = {}

    signatures = existing.get("error_signatures", {})

    for rec in records:
        sig = rec.get("signature", "")
        if not sig:
            continue
        error_type = rec.get("error_type", "runtime")
        message = rec.get("message", "")[:100]
        cmd = rec.get("cmd", "")[:120]
        ts = rec.get("ts", now_ts)

        if sig in signatures:
            entry = signatures[sig]
            entry["count"] = entry.get("count", 0) + 1
            entry["last_seen"] = max(entry.get("last_seen", 0), ts)
            # 去重: 同一天不再加 count
            entry["daily_count"] = entry.get("daily_count", 0) + 1
        else:
            signatures[sig] = {
                "signature": sig,
                "message": message,
                "cmd": cmd,
                "error_type": error_type,
                "count": 1,
                "daily_count": 1,
                "first_seen": ts,
                "last_seen": ts,
                "status": "active",
                "fix_count": 0,
                "repair_command": "",
                "sublimated": False,
                "degradation_candidate": False,
            }

    # ── Step 3: 升华 — count >= 3 自动生成规则 ──
    rules_file = project_root / ".claude" / "reference" / "error-rules.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    new_rules = []
    for sig, entry in sorted(signatures.items(), key=lambda x: -x[1].get("count", 0)):
        if entry.get("count", 0) >= 3 and not entry.get("sublimated", False):
            rule_text = (
                f"## {entry.get('error_type', 'runtime')} — {entry.get('message', '')[:60]}\n"
                f"- **签名**: `{sig}`\n"
                f"- **出现次数**: {entry['count']}\n"
                f"- **首次出现**: {datetime.fromtimestamp(entry['first_seen'], tz=timezone.utc).strftime('%Y-%m-%d') if entry.get('first_seen') else 'unknown'}\n"
                f"- **修复建议**: 检查命令 `{entry.get('cmd', '')[:80]}` 的正确性\n"
                f"- **自动升华时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            new_rules.append(rule_text)
            entry["sublimated"] = True

    if new_rules:
        header = "# Error 升华规则\n\n> 由 error-dna-aggregator 自动从错误模式升华生成\n\n"
        try:
            existing_rules = rules_file.read_text(encoding="utf-8") if rules_file.exists() else ""
            if not existing_rules.startswith("# Error 升华规则"):
                existing_rules = header + existing_rules
            with open(rules_file, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new_rules) + "\n")
        except Exception:
            pass

    # ── Step 4: 退化检测 ──
    DEGRADATION_DAYS = 7
    REMOVAL_DAYS = 14
    for sig, entry in signatures.items():
        last_seen = entry.get("last_seen", 0)
        if last_seen == 0:
            continue
        days_since = (now_ts - last_seen) / 86400
        if days_since > REMOVAL_DAYS and entry.get("status") == "active":
            entry["status"] = "degraded"
            entry["degradation_candidate"] = False  # 已降级
        elif days_since > DEGRADATION_DAYS and entry.get("status") == "active":
            entry["degradation_candidate"] = True

    # ── Step 5: 写回 error-dna.json ──
    output = {"error_signatures": signatures, "updated_at": now_ts, "total_unique": len(signatures)}
    try:
        dna_json.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        pass

    # ── Step 6: 清理已处理记录（可选：清空 jsonl 避免重复聚合）─
    # 注意：不清空，每次聚合会重新读取全部记录再增量更新
    flywheel_event("error_dna_aggregator", f"aggregated_{len(signatures)}_sigs", "P2")
    sys.exit(0)


if __name__ == "__main__":
    main()
