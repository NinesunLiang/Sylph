#!/usr/bin/env python3
"""分析 Claude Code 会话文件:模拟请求消息数组,定位指定 position 附近的消息。

用法:
  python3 scripts/analyze-session-positions.py FILE [POS]
  POS 默认 112。输出:主链消息总数、POS 前后各 8 条消息的结构、
  主链上所有 thinking_only 消息的 position 列表。
"""
import json
import sys
from pathlib import Path


def block_summary(content):
    """返回内容块类型摘要,如 [thinking, text(132)] 或 [tool_result]"""
    if isinstance(content, str):
        return f"str({len(content)})"
    parts = []
    for b in content if isinstance(content, list) else []:
        if not isinstance(b, dict):
            parts.append("?<non-dict>")
            continue
        t = b.get("type", "?")
        if t == "text":
            parts.append(f"text({len(b.get('text') or '')})")
        elif t == "thinking":
            parts.append(f"thinking({len(b.get('thinking') or '')})")
        elif t == "tool_use":
            parts.append(f"tool_use[{b.get('name', '?')}]")
        elif t == "tool_result":
            c = b.get("content")
            n = len(c) if isinstance(c, (str, list)) else 0
            parts.append(f"tool_result({n})")
        else:
            parts.append(t)
    return "[" + ", ".join(parts) + "]"


def main():
    path = Path(sys.argv[1])
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 112

    msgs = []  # (position_0based, lineno, obj)
    skipped_types = {}
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            if t not in ("user", "assistant"):
                skipped_types[t] = skipped_types.get(t, 0) + 1
                continue
            if obj.get("isMeta") or obj.get("isSidechain"):
                skipped_types[f"{t}:{'meta' if obj.get('isMeta') else 'sidechain'}"] = \
                    skipped_types.get(f"{t}:{'meta' if obj.get('isMeta') else 'sidechain'}", 0) + 1
                continue
            msgs.append((len(msgs), lineno, obj))

    print(f"文件: {path.name}")
    print(f"主链消息总数: {len(msgs)}  (跳过: {skipped_types})")
    if len(msgs) <= target:
        print(f"!! 主链只有 {len(msgs)} 条,不足 position {target} —— 此会话不是报错现场")
        return

    print(f"\n== position {target} 附近 (0-based) ==")
    for pos, lineno, obj in msgs:
        if not (target - 8 <= pos <= target + 8):
            continue
        m = obj.get("message") or {}
        mark = " <<<" if pos == target else ""
        print(f"pos={pos:<4} 行{lineno:<5} {obj.get('type'):<9} "
              f"{block_summary(m.get('content'))} "
              f"model={m.get('model', '-')} stop={m.get('stop_reason', '-')} "
              f"uuid={obj.get('uuid', '?')[:8]}{mark}")

    print(f"\n== 主链上所有 thinking_only(剥 thinking 后会变空)的 assistant ==")
    found = []
    for pos, lineno, obj in msgs:
        if obj.get("type") != "assistant":
            continue
        content = (obj.get("message") or {}).get("content")
        if isinstance(content, list) and content and all(
            isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking")
            for b in content
        ):
            found.append((pos, lineno))
    if not found:
        print("(无)")
    for pos, lineno in found:
        flag = "  <== 命中目标 position!" if pos == target else ""
        print(f"  pos={pos:<4} 行{lineno}{flag}")


if __name__ == "__main__":
    main()
