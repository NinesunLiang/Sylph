#!/usr/bin/env python3
"""扫描/修复 Claude Code 会话文件中内容为空的 assistant 消息。

背景:Anthropic API 要求每条消息至少有一个非空 content block。
若会话历史里混入空 assistant 消息(空字符串/空数组/纯空白 text),
后续所有请求都会 400: "the message at position N with role 'assistant' must not be empty"。

用法:
  python3 scripts/find-empty-assistant.py             # 只读扫描全部项目会话
  python3 scripts/find-empty-assistant.py --fix FILE  # 修复空消息(先备份 .bak,幂等)
  python3 scripts/find-empty-assistant.py --fix-thinking FILE
      # 额外把"仅含 thinking 块"的 assistant 消息也替换为占位文本
      # (用于 /compact 因剥离 thinking 导致消息变空而 400 的场景)
"""
import json
import shutil
import sys
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"

PLACEHOLDER = "(此消息原为空,已被脚本占位修复)"


def classify_assistant(obj):
    """返回 None(非 assistant 或正常) / 'empty'(完全空) / 'thinking_only'(仅思考块)。"""
    if obj.get("type") != "assistant":
        return None
    msg = obj.get("message") or {}
    content = msg.get("content")
    if content is None:
        return "empty"
    if isinstance(content, str):
        return "empty" if not content.strip() else None
    if isinstance(content, list):
        if not content:
            return "empty"
        has_text = False
        has_thinking = False
        for block in content:
            if not isinstance(block, dict):
                return None  # 结构异常,保守跳过
            btype = block.get("type")
            if btype == "text":
                if (block.get("text") or "").strip():
                    has_text = True
            elif btype == "tool_use":
                return None  # 带工具调用,正常
            elif btype in ("thinking", "redacted_thinking"):
                has_thinking = True
            else:
                return None  # 未知块类型,保守跳过
        if has_text:
            return None
        return "thinking_only" if has_thinking else "empty"
    return None


def scan_file(path):
    """返回 [(lineno, kind, uuid, timestamp), ...]"""
    hits = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                kind = classify_assistant(obj)
                if kind:
                    hits.append((lineno, kind, obj.get("uuid", "?"), obj.get("timestamp", "?")))
    except OSError as e:
        print(f"WARN: 无法读取 {path}: {e}", file=sys.stderr)
    return hits


def fix_file(path, fix_thinking=False):
    """把空 assistant 消息(及可选的 thinking_only 消息)替换为占位文本。幂等;有改动才写文件。"""
    path = Path(path)
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    print(f"已备份: {bak}")

    out_lines = []
    fixed = 0
    fixed_thinking = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                out_lines.append(line)
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                out_lines.append(line)
                continue
            kind = classify_assistant(obj)
            if kind == "empty" or (fix_thinking and kind == "thinking_only"):
                obj["message"]["content"] = [{"type": "text", "text": PLACEHOLDER}]
                out_lines.append(json.dumps(obj, ensure_ascii=False) + "\n")
                if kind == "empty":
                    fixed += 1
                else:
                    fixed_thinking += 1
            else:
                out_lines.append(line)

    if fixed == 0 and fixed_thinking == 0:
        print("没有发现需要修复的消息,文件未改动。")
        bak.unlink()
        return
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    print(f"已修复: 空消息 {fixed} 条, thinking_only {fixed_thinking} 条 → {path}")
    print("提示:关闭该会话窗口后用 claude --resume 恢复再重试 /compact。")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--fix":
        fix_file(sys.argv[2])
        return
    if len(sys.argv) == 3 and sys.argv[1] == "--fix-thinking":
        fix_file(sys.argv[2], fix_thinking=True)
        return
    if len(sys.argv) != 1:
        print(__doc__)
        sys.exit(1)

    files = sorted(PROJECTS_DIR.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"扫描 {len(files)} 个会话文件 (按最近修改排序)\n")
    total = 0
    for path in files:
        hits = scan_file(path)
        if not hits:
            continue
        total += len(hits)
        print(f"== {path}")
        for lineno, kind, uuid, ts in hits:
            tag = "空消息(必炸)" if kind == "empty" else "仅thinking(经网关可能被剥空)"
            print(f"   行{lineno:<6} [{tag}] uuid={uuid} ts={ts}")
    if total == 0:
        print("未发现空 assistant 消息。")
    else:
        print(f"\n共 {total} 处。修复方式: python3 {sys.argv[0]} --fix <文件路径>")


if __name__ == "__main__":
    main()
