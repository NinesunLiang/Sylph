#!/usr/bin/env python3
"""
pre-ask-guard.py — PreToolUse:AskUserQuestion — 两段式决策链评估

Role: 拦截 AskUserQuestion，检查决策链是否已有答案。能自主决策则阻断提问，降低人类心智负担。

决策链（两段式）：
  Phase 1 (快速扫描): AGENTS.md → kernel.md（高频匹配层，单次读取）
  Phase 2 (完整遍历): anti-patterns.md → claude-next.md → behavior-patterns.md
仅全部不确定 → 放行问人

Conversion from pre-ask-guard.sh
"""

import json
import os
import re
import sys
from pathlib import Path

# ─── Import shared library ───
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_emit_hook_json

_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"


def extract_questions(input_data: str) -> list[str]:
    """
    从 stdin JSON 中提取所有问题文本。
    Shell 对应: echo "$INPUT" | python3 -c "..."
    """
    try:
        d = json.loads(input_data)
        qs = d.get("tool_input", {}).get("questions", [])
        return [q.get("question", "") for q in qs if q.get("question")]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def extract_keywords(question: str) -> list[str]:
    """
    提取关键词（取前 5 个有意义的词，排除停用词）
    Shell 对应: 内联 python3 -c "..." 脚本
    """
    # 中文2+字，英文3+字母
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", question)
    stop_words = {
        "what", "how", "when", "where", "which", "should", "could", "would",
        "the", "and", "for", "this", "that", "with", "from", "your", "have", "been",
        "请", "是否", "需要", "应该", "可以", "什么", "如何", "怎么", "为什么",
        "还是", "或者", "这个", "那个", "已经", "可能", "还是说", "我想", "想知道", "如果",
    }
    return [w for w in words if w.lower() not in stop_words][:5]


def search_decision_chain(question: str, files: list[tuple[str, str]]) -> tuple[str, str, str]:
    """
    两段式搜索决策链文件。
    Phase 1 (快速扫描): 只用第一个文件（AGENTS.md），匹配即返回
    Phase 2 (完整遍历): 匹配到则返回，否则继续下一个文件
    返回: (matched_layer_name, matched_line_content, layer_display_name)
    """
    keywords = extract_keywords(question)
    if not keywords:
        return ("", "", "")

    layer_display_map = {
        "AGENTS.md": "哲学/铁律层",
        "kernel.md": "铁律/执行内核层",
        "anti-patterns.md": "反模式层",
        "claude-next.md": "项目惯例层",
        "behavior-patterns.md": "行为模式层",
    }

    for filepath, display_name in files:
        if not filepath.exists():
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        lines = content.splitlines()
        for kw in keywords:
            if len(kw) < 2:
                continue
            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip comments and blockquotes
                if stripped.startswith("#") or stripped.startswith("> "):
                    continue
                if kw.lower() in stripped.lower():
                    layer_name = filepath.name
                    display = layer_display_map.get(layer_name, layer_name)
                    return (layer_name, f"{layer_name}:{lineno}:{stripped[:120]}", display)
        # If no keyword match, check if the question topic is semantically answerable
        # by the document's content structure

    return ("", "", "")


def main():
    """Main entry point (replaces the shell script body)."""

    # ─── Gate: hc_enabled ───
    if not hc_enabled("pre_ask_guard"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── Read stdin ───
    input_data = sys.stdin.read()
    questions = extract_questions(input_data)

    if not questions:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── 自主模式: 一律阻断 ──────────────────────────────────────
    # 哲学 #6 (0信任): 自主模式下 AI 不得问人。无法决策的走 blocked-human。
    mode = is_mode_active(str(_STATE_DIR))
    total_count = len(questions)

    if mode != "normal":
        msg = (
            f"🛑 [pre-ask-guard] 自主模式({mode})活跃 — 所有问题禁止问人\n"
            f"   问题数: {total_count} → 请走决策链裁决: 哲学(7条) → 铁律(8条) → 现状 → Oracle → AI自判\n"
            f"   无法确定 → 记录: lx-{mode} blocked-human \"问题\" \"AI推荐\" \"依据\" → 人在退出报告中审阅"
        )
        print(msg, file=sys.stderr, flush=True)
        flywheel_event("pre_ask_guard", "blocked_autonomous_mode", "P1",
                       f"mode={mode} questions={total_count}")
        ctx = (
            f"[pre-ask-guard] 自主模式({mode})活跃，禁止问人。所有问题走决策链: "
            f"哲学(7条) → 铁律(8条) → 现状 → Oracle → AI自判。"
            f"无法确定的记录 lx-{mode} blocked-human 人在退出报告中审阅。"
        )
        print(hc_emit_hook_json(ctx, event="PreToolUse", continue_val=False))
        sys.exit(2)

    # ─── 决策链文件（Phase 1: AGENTS.md + kernel.md 快速扫描 → Phase 2: 完整遍历） ─────
    quick_files = [
        (_PROJECT_ROOT / "AGENTS.md", "AGENTS.md"),
    ]
    deep_files = [
        (_PROJECT_ROOT / ".claude" / "kernel.md", "kernel.md"),
        (_PROJECT_ROOT / ".claude" / "anti-patterns.md", "anti-patterns.md"),
        (_PROJECT_ROOT / ".claude" / "claude-next.md", "claude-next.md"),
    ]

    # ─── 逐问题检查 ──────────────────────────────────────────────
    resolvable_count = 0
    hints: list[str] = []

    for question in questions:
        if not question:
            continue

        # Phase 1: 快速扫描 AGENTS.md
        matched_layer, matched_line, display_name = search_decision_chain(question, quick_files)

        # Phase 2: 未命中则完整遍历
        if not matched_layer:
            matched_layer, matched_line, display_name = search_decision_chain(question, deep_files)

        if matched_layer:
            resolvable_count += 1
            hints.append(
                f"🟢 「{question[:60]}…」→ {display_name} 已有覆盖: {matched_line}"
            )
        else:
            hints.append(
                f"🔴 「{question[:60]}…」→ 决策链无覆盖，需人类裁决"
            )

    # ─── 判定 ──────────────────────────────────────────────────
    hints_text = "\n".join(hints)

    if resolvable_count == total_count and total_count > 0:
        # 全部可自主决策 → 阻断提问，输出决策依据
        print(
            f"🧠 [pre-ask-guard] 决策链已覆盖全部 {total_count} 个问题 — 无需问人\n{hints_text}",
            file=sys.stderr, flush=True
        )
        flywheel_event("pre_ask_guard", "blocked_all_resolvable", "P1")
        ctx = (
            f"[pre-ask-guard] 全部 {total_count} 个问题决策链已有答案。"
            f"请标注 [哲学先行: #N→action] 后直接执行，不必问人。\n{hints_text}"
        )
        print(hc_emit_hook_json(ctx, event="PreToolUse", continue_val=False))
        sys.exit(2)

    elif resolvable_count > 0:
        # 部分可自主 → 软提示，不阻断
        print(
            f"💡 [pre-ask-guard] {resolvable_count}/{total_count} 个问题决策链可覆盖\n{hints_text}",
            file=sys.stderr, flush=True
        )
        flywheel_event("pre_ask_guard", "partial_hint", "P2")
        print(json.dumps({"continue": True}))
        sys.exit(0)

    else:
        # 全部不确定 → 放行，这是真正需要人类的问题
        flywheel_event("pre_ask_guard", "passed_genuine", "P2")
        print(json.dumps({"continue": True}))
        sys.exit(0)


if __name__ == "__main__":
    main()
