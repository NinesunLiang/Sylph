#!/usr/bin/env python3
"""
distinct-concept-richner.py — Richner hook: distinct概念丰富化

在AI生成内容中检测概念混淆/重叠, 自动注入区分策略。
哲学归属: #7(文档) → 确保概念边界清晰, 引用准确。

工作流:
  1. 检测输出中概念混用 (同义反复/范畴错误/层级混淆)
  2. 如发现混淆 → 注入区分说明 + 引用AGENTS.md路由表
  3. 记录distinct信号到 .claude/signals/ 供后续审计

Matcher: PostToolUse | Edit | Write
"""

import json
import os
import sys
from pathlib import Path

# ── 路径探活 ──
CARROROS = Path(os.environ.get("CARROROS_DIR", str(Path.home() / "Desktop" / "Sylph" / "Carror_OS")))
SIGNALS_DIR = CARROROS / ".claude" / "signals"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)


def detect_concept_overlap(text: str) -> list:
    """检测概念混淆 —— 启发式模式匹配"""
    patterns = {
        "philosophy_vs_iron_law": ["哲学优先级", "铁律", "哲学铁律"],
        "compact_vs_full": ["compact", "压缩", "AGENTS.compact", "AGENTS.md"],
        "hook_vs_skill": ["hook", "skill", "lx-"],
    }
    hits = []
    for name, keywords in patterns.items():
        found = [kw for kw in keywords if kw in text]
        if len(found) >= 2:
            hits.append((name, found))
    return hits


def inject_distinction(hits: list, content: str) -> str:
    """注入概念区分说明"""
    injects = []
    for name, found in hits:
        if name == "philosophy_vs_iron_law":
            injects.append(
                "\n> **概念区分**: 哲学优先级(#4>#6>...)是冲突裁决链; "
                "铁律(1-8条)是行为约束。哲学决定_怎么选_, 铁律规定_不能做什么_。"
            )
        elif name == "compact_vs_full":
            injects.append(
                "\n> **概念区分**: AGENTS.compact.md 是运行时注入的压缩路由表; "
                "AGENTS.md 是完整源。compact 展开后恢复全部上下文。"
            )
        elif name == "hook_vs_skill":
            injects.append(
                "\n> **概念区分**: hook (snake_case) 是事件→动作的gate/guard; "
                "skill (lx-前缀) 是能力模块。hook 阻断/审计, skill 执行/编排。"
            )
    return content + "".join(injects)


def write_signal(name: str, detail: str):
    """写入信号文件"""
    ts = __import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")
    sig = SIGNALS_DIR / f"distinct-{name}-{ts}.signal"
    sig.write_text(f"# distinct-concept-richner signal\nname: {name}\nts: {ts}\ndetail: {detail}\n")


def main():
    # 从 stdin 或环境变量读取内容
    content = os.environ.get("ORIGINAL_CONTENT", "")
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()

    if not content:
        # 无内容可检查, 静默退出 (hook 永不阻断)
        sys.exit(0)

    hits = detect_concept_overlap(content)
    if hits:
        for name, found in hits:
            write_signal(name, f"concepts overlapped: {found}")
        enriched = inject_distinction(hits, content)
        # 输出丰富化后的内容
        print(enriched)
        sys.exit(0)

    # 无混淆, 原样输出
    if not sys.stdin.isatty():
        print(content)


if __name__ == "__main__":
    main()
