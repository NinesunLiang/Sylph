#!/usr/bin/env python3
"""
flywheel.py — CarrorOS 飞轮升华管道

**燃料（index48 更换）**：门禁审计遥测 `.omc/state/audit/*.jsonl`
→ 反复出现的拦截原因即反模式原料
→ claude-next.md（供 stop-flywheel 升华检查消费，hits≥3 时写入 anti-patterns.md）
飞轮数据落 .omc/knowledge/，不进默认 Context。

历史：原燃料为 `error-dna.jsonl`。该机制于 2026-09-10（index48）整体移除——
83 条记录 100% `resolution: pending`、`.omc/knowledge/` 产出为 0、76 条
`bash_path_not_found` 中 67 条为测试自造命令。整条链历史产出为 0
（`claude-next.md` 与 `anti-pattern-redirects.jsonl` 均不存在）。
经人类裁决「接活：换真燃料」，改用真实存在的门禁审计日志。
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


KNOWLEDGE_DIR = ".omc/knowledge"

# 达到该次数即视为「反复出现」，值得沉淀
RECURRING_THRESHOLD = 3
# 单轮最多沉淀的条目数（防止把噪声灌进知识库）
MAX_ENTRIES = 5


def _knowledge_root(project_root: Path) -> Path:
    """Get .omc/knowledge/ directory, create if needed."""
    kd = project_root / KNOWLEDGE_DIR
    kd.mkdir(parents=True, exist_ok=True)
    return kd


def read_audit_events(state_dir: Path, n: int = 500) -> list:
    """读取门禁审计遥测（.omc/state/audit/*.jsonl），返回最近 n 条。

    目录缺失 / 文件损坏 → 返回空列表，绝不抛异常（飞轮永不阻断）。
    """
    audit_dir = Path(state_dir) / "audit"
    if not audit_dir.is_dir():
        return []
    records: list = []
    for path in sorted(audit_dir.glob("*.jsonl")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                records.append(rec)
    return records[-n:]


def _event_signature(ev: dict) -> str:
    """把一条审计事件归一化为「可聚类签名」：门禁 + 事件类型 + 决策/原因前缀。"""
    parts = [
        str(ev.get("gate") or ""),
        str(ev.get("event_type") or ""),
    ]
    detail = str(ev.get("reason") or ev.get("decision") or "")
    detail = re.sub(r"\s+", " ", detail).strip()
    parts.append(detail[:60])
    return " | ".join(p for p in parts if p)


def extract_patterns(events: list) -> list:
    """从门禁审计事件中提取「反复出现的拦截模式」。

    返回 [{error, step, pattern, count, retry_count}]，按出现次数降序。
    只保留非 PASS 的决策——放行记录不构成反模式。
    """
    grouped: dict[str, dict] = {}

    for ev in events:
        decision = str(ev.get("decision") or "").upper()
        if decision in ("", "PASS"):
            continue
        # 事件型记录（无 decision 字段）同样计入：privacy_*_block 等
        sig = _event_signature(ev)
        if not sig or sig == " | ":
            continue
        item = grouped.setdefault(sig, {
            "error": sig,
            "step": str(ev.get("gate") or ev.get("event_type") or "?"),
            "count": 0,
        })
        item["count"] += 1

    patterns = []
    for item in grouped.values():
        text = item["error"].lower()
        pattern_type = "governance_intervention"
        if "block" in text:
            pattern_type = "blocked_recurring"
        elif "redirect" in text:
            pattern_type = "redirect_recurring"
        elif "ask_user" in text or "ask_user" in text.lower():
            pattern_type = "escalated_recurring"
        if item["count"] < RECURRING_THRESHOLD:
            pattern_type = "one_off"

        patterns.append({
            "error": item["error"][:200],
            "step": item["step"],
            "pattern": pattern_type,
            "count": item["count"],
            "retry_count": 0,
        })

    patterns.sort(key=lambda p: -p["count"])
    return patterns


def get_anti_patterns_path(project_root: Path) -> Path:
    """Path to anti-patterns.md."""
    return project_root / ".claude" / "references" / "anti-patterns.md"


def write_anti_patterns(project_root: Path, patterns: list) -> Optional[Path]:
    """将升华后的模式写入 anti-patterns.md."""
    if not patterns:
        return None

    ap_path = get_anti_patterns_path(project_root)
    existing = []
    if ap_path.exists():
        existing = ap_path.read_text(encoding="utf-8").splitlines()

    lines = []
    lines.append("# Anti-Patterns — 经验沉淀")
    lines.append(f"")
    lines.append(f"_Updated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"")
    lines.append("## 已识别模式\n")

    for p in patterns:
        lines.append(f"- **{p['pattern']}** (step={p['step']}, count={p['count']})")
        lines.append(f"  - `{p['error'][:120]}`")
        lines.append(f"")

    # Merge with existing
    if existing:
        lines.append("\n## 历史记录\n")
        lines.extend(existing[-50:])

    ap_path.write_text("\n".join(lines), encoding="utf-8")
    return ap_path


def write_claude_next(project_root: Path, entry: str) -> Path:
    """将优化建议写入 claude-next.md (knowledge 目录)."""
    kd = _knowledge_root(project_root)
    cn_path = kd / "claude-next.md"

    lines = []
    if cn_path.exists():
        lines.append(cn_path.read_text(encoding="utf-8"))

    lines.append(f"- [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {entry}")

    cn_path.write_text("\n".join(lines[-200:]), encoding="utf-8")
    return cn_path


def run_flywheel(project_root: Path, task_dir: Optional[Path] = None) -> dict:
    """
    运行飞轮管道主流程。
    1. 读门禁审计遥测（.omc/state/audit/*.jsonl）
    2. 提取「反复出现的拦截模式」
    3. 反复模式 → knowledge/claude-next.md（供 stop-flywheel 升华检查消费）

    永不阻断：任何异常都降级为「本轮无产出」。

    Returns summary dict.
    """
    result = {"patterns_found": 0, "anti_patterns_written": False, "knowledge_entries": 0}

    try:
        state_dir = project_root / ".omc" / "state"
        events = read_audit_events(state_dir)
    except Exception:
        events = []

    if not events:
        result["note"] = "no audit telemetry found"
        return result

    patterns = extract_patterns(events)
    recurring = [p for p in patterns if p["count"] >= RECURRING_THRESHOLD]
    result["patterns_found"] = len(recurring)
    if not recurring:
        result["note"] = "no recurring intervention pattern"
        return result

    for p in recurring[:MAX_ENTRIES]:
        entry = (f"Pattern '{p['pattern']}' in {p['step']} "
                 f"(x{p['count']}): {p['error'][:80]}")
        write_claude_next(project_root, entry)
        result["knowledge_entries"] += 1

    return result
