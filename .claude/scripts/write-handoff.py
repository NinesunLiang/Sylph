#!/usr/bin/env python3
"""write-handoff.py — 强制写 handoff（compact 前/关键节点调用）

写入 7 段结构化 handoff 到 .omc/session-handoff.md
用于 compact 后恢复任务状态，不依赖模型记忆。

触发时机:
- water_level yellow/red
- tick 结束时
- verify 前
- archive 前
"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OMC = ROOT / ".omc"
STATE_DIR = OMC / "state"
HANDOFF = OMC / "session-handoff.md"
LAST_USER = STATE_DIR / "last-user-prompt.md"
TOKEN_PATH = OMC / "state" / "token.json"

def main():
    # 1. 读取 token
    goal = "未知"
    level = "L1"
    step = "未知"
    task_id = "unknown"
    try:
        if TOKEN_PATH.exists():
            t = json.loads(TOKEN_PATH.read_text())
            goal = t.get("description", t.get("goal", "未知"))[:200]
            level = t.get("level", "L1")
            step = t.get("current_step", t.get("step", "未知"))
            task_id = t.get("task_id", "unknown")
    except Exception:
        pass

    # 2. 读取最后用户意图
    last_intent = ""
    try:
        if LAST_USER.exists():
            last_intent = LAST_USER.read_text(encoding="utf-8", errors="replace")[:300]
    except Exception:
        pass

    # 3. 读取 error-dna
    errors = []
    edna = STATE_DIR.parent / "error-dna.jsonl"
    try:
        if edna.exists():
            with open(edna) as f:
                for line in f:
                    try:
                        e = json.loads(line.strip())
                        errors.append(e.get("type", e.get("error_type", "?")))
                    except Exception:
                        pass
            errors = errors[-5:]
    except Exception:
        pass

    # 4. 读取水位
    water_level = "? (unknown)"
    try:
        wf = STATE_DIR / "context-watermark.json"
        if wf.exists():
            wl = json.loads(wf.read_text())
            level_pct = wl.get("level_pct", wl.get("usage_pct", "?"))
            water_level = f"{level_pct}%"
    except Exception:
        pass

    # 5. 生成 handoff（schema v2）
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # 计算 checksum（token.json）
    token_checksum = ""
    scope_info = ""
    try:
        if TOKEN_PATH.exists():
            import hashlib
            token_checksum = "sha256:" + hashlib.sha256(TOKEN_PATH.read_bytes()).hexdigest()[:12]
            t = json.loads(TOKEN_PATH.read_text())
            scope = t.get("scope", [])
            if scope:
                scope_info = "\n".join(f"  - {s}" for s in scope[:8])
    except Exception:
        pass

    data = f"""# Session Handoff

> Schema: v2.0 | 由 write-handoff.py 于 {ts} 更新
> 紧凑后自动读取本文件可恢复会话

## Meta
- schema_version: 2.0
- task_id: {task_id}
- token_checksum: {token_checksum}

## Current Goal
{goal}
{("  用户最后意图: " + last_intent) if last_intent else ""}

## Current State
- task_id: {task_id}
- level: {level}
- step: {step}
- water_level: {water_level}

## Active Files / Scope
{scope_info if scope_info else "  (未设定 scope)"}

## Decisions Made
（由 kernel.md 和 AGENTS.md 的哲学铁律指导）

## Next Action
- 继续当前 step ({step})
- 如需检查进度：carros_base.py status
- 如需重新规划：carros_base.py re-plan

## Risks
- 治理文件（.claude/hooks/* / harness.yaml / settings.json）不可修改
- token scope 不可越界写入
"""

    HANDOFF.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF.write_text(data)
    print(f"✅ Handoff written: {len(data)} chars to {HANDOFF}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
