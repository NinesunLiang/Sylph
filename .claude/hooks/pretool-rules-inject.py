#!/usr/bin/env python3
"""
pretool-rules-inject.py — UserPromptSubmit — 3级脱水分层注入

永不阻断 (exit 0)
Turn 0: L1+L2+L3 全量上车
Turn 1+: 自适应频率 (L1每轮, L2自适应, L3每10轮)
"""

import json
import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    output_additional_context, sanitize_text,
    PROJECT_ROOT, STATE_DIR,
)


# Fallback L1 when context-cache.md is missing
L1_FALLBACK = (
    "[L1·铁律8条] ①禁编造(file:line) ②用户裁定 ③证据门禁(VERIFIED) "
    "④Git门禁 ⑤范围冻结 ⑥隐私防线 ⑦断言真实 ⑧哲学先行\n"
    "[L1·哲学] #4验>#6信>#3守>#7文>#5人>#2益>#1简\n"
    "[L1·裁判团] 哲学7条 > 铁律8条 > 现状 > Oracle > Meta-Oracle > 人\n"
    "[L1·决策链] 过程问题->#4直接执行 | 抉择->#2最小改动 | 方案验收->问人 | 不可逆->问人"
)


def parse_context_cache(cache_path: Path, turn_count: int) -> dict:
    """Parse context-cache.md, split into L1/L2/L3 layers."""
    try:
        text = cache_path.read_text(encoding="utf-8")
    except OSError:
        return {"l1": L1_FALLBACK, "l2": "", "l3": ""}

    # Remove HTML comments and CTX-COMPACT marker
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = text.replace('CTX-COMPACT:AI-ONLY', '')

    # Split into sections by --- separators
    sections = [s.strip() for s in text.split('---') if s.strip()]

    l1_parts = []
    l2_parts = []
    l3_parts = []

    for sec in sections:
        lines = [l.strip() for l in sec.split('\n') if l.strip()]
        if not lines:
            continue
        first_line = lines[0] if lines else ''

        if '铁律:' in first_line or '铁律' in first_line:
            # L1: 铁律 + 哲学 + 软完成语
            l1_lines = [l for l in lines
                        if not l.startswith('操作约束')
                        and not l.startswith('权威')
                        and not l.startswith('Hook')
                        and not l.startswith('三源')
                        and not l.startswith('Read展开')]
            l1_parts.extend(l1_lines[:20])
            # 操作约束/Hook/三源 → L2
            meta_lines = [l for l in lines
                          if l.startswith('操作约束')
                          or l.startswith('-')
                          or l.startswith('权威')
                          or l.startswith('Hook')
                          or l.startswith('三源')
                          or l.startswith('Read展开')]
            if meta_lines:
                l2_parts.append('操作约束+Hook速查+三源:')
                l2_parts.extend(meta_lines[:15])
        elif '反模式' in first_line:
            l2_parts.extend(lines[:15])
        elif '教训' in first_line:
            l3_parts.extend(lines[:13])
        elif '架构铁律' in first_line or '命名:' in first_line:
            l2_parts.extend(lines[:12])
        elif '错误处理' in first_line or '测试:' in first_line or '禁止:' in first_line:
            l3_parts.extend(lines)
        elif '原则:' in first_line:
            l3_parts.append(first_line)

    # Build L1
    l1 = '\n'.join(l1_parts[:15]) if l1_parts else ''
    if l1:
        l1 = '[L1·铁律+哲学] context-cache.md 脱水上下文\n' + l1

    # Build L2 (Turn 0 or every 5 turns)
    l2 = ''
    l2_turns = (turn_count == 0) or (turn_count % 5 == 0)
    if l2_turns and l2_parts:
        l2 = '\n'.join(l2_parts[:25])
        if l2:
            l2 = f'[L2·操作+反模式+架构] 第{turn_count}轮刷新 (每5轮)\n' + l2

    # Build L3 (Turn 0 or every 10 turns)
    l3 = ''
    l3_turns = (turn_count == 0) or (turn_count % 10 == 0)
    if l3_turns and l3_parts:
        l3 = '\n'.join(l3_parts[:20])
        if l3:
            l3 = f'[L3·教训+禁止项] 第{turn_count}轮刷新 (每10轮)\n' + l3

    if not l1:
        l1 = L1_FALLBACK

    return {"l1": l1, "l2": l2, "l3": l3}


def main():
    if not hc_enabled("pretool_rules_inject"):
        print(json.dumps({"continue": True}))
        return

    # Read current turn count
    turns_file = STATE_DIR / "session-turns.json"
    turn_count = 0
    if turns_file.exists():
        try:
            with open(str(turns_file), encoding="utf-8") as f:
                turn_data = json.load(f)
            turn_count = int(turn_data.get("count", 0))
        except (json.JSONDecodeError, ValueError, OSError):
            pass

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Parse layered context from cache
    cache_path = STATE_DIR / "context-cache.md"
    if cache_path.exists():
        layered = parse_context_cache(cache_path, turn_count)
        l1 = layered["l1"]
        l2 = layered["l2"]
        l3 = layered["l3"]
    else:
        l1 = L1_FALLBACK
        l2 = ""
        l3 = ""

    # Assemble context
    ctx = l1

    # Append TODO (Turn 0 + every 10 turns)
    if turn_count == 0 or turn_count % 10 == 0:
        todo_queue = STATE_DIR / "todo-queue.md"
        todo_ctx = "(无)"
        if todo_queue.exists():
            try:
                lines = todo_queue.read_text(encoding="utf-8").split("\n")
                items = [l for l in lines if re.match(r'^\[.\]|^###', l)][:5]
                if items:
                    todo_ctx = "; ".join(items)
            except OSError:
                pass
        ctx += f"\n\n[TODO·第{turn_count}轮] {todo_ctx}"

    # Append L2
    if l2:
        ctx += f"\n\n{l2}"

    # Append L3
    if l3:
        ctx += f"\n\n{l3}"

    # Output
    output_additional_context(ctx, "UserPromptSubmit")
    flywheel_event("pretool_rules_inject", "injected", "P2", f"turn={turn_count}")


if __name__ == "__main__":
    main()
