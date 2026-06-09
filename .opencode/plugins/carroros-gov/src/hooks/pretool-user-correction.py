#!/usr/bin/env python3
"""
pretool-user-correction.py — UserPromptSubmit — 检测用户纠正信号，强制记录到 claude-next.md
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, flywheel_event


def main():
    if not hc_enabled("user_correction_detector"):
        try:
            print(sys.stdin.read())
        except Exception:
            pass
        sys.exit(0)

    # 从 stdin 读取完整用户输入
    try:
        prompt = sys.stdin.read()
    except Exception:
        prompt = ""

    if not prompt:
        sys.exit(0)

    # 从配置读取纠正信号词列表
    correction_signals_str = hc_get(
        "correction_detector.signals",
        "不对 错了 你搞错了 应该是 不是这样 重新来 这不对 你弄错了 纠正一下 弄错了 理解错了 你理解错了 理解有误"
    )
    correction_signals = correction_signals_str.split()

    # 检测是否命中信号词
    triggered = False
    matched_signal = ""
    for signal in correction_signals:
        if signal in prompt:
            triggered = True
            matched_signal = signal
            break

    if triggered:
        project_root = (_HOOKS_DIR / "../..").resolve()
        claude_next = project_root / ".claude" / "claude-next.md"
        today = date.today().isoformat()

        # 当天已有新写入 → 静默（不重复提醒）
        already_written = False
        if claude_next.exists():
            try:
                content = claude_next.read_text(encoding="utf-8")
                if f"### [{today}]" in content:
                    already_written = True
            except Exception:
                pass

        if not already_written:
            # Auto-write skeleton entry to claude-next.md
            title = prompt[:50].replace("\n", " ").strip()

            entry = (
                f"\n"
                f"### [{today}] 用户纠正: {matched_signal}\n"
                f"@{today} hits:1\n"
                f"**触发场景**：检测到纠正信号「{matched_signal}」（{title}）\n"
                f"**问题**：（待本对话补充具体纠正内容）\n"
                f"**纠正**：（AI 完成任务前应引用此记录并补充根因分析）\n"
                f"\n"
            )
            try:
                with open(str(claude_next), "a", encoding="utf-8") as f:
                    f.write(entry)
            except Exception:
                pass

            # Kernel draft: auto-generate draft from correction signal
            draft_dir = project_root / ".omc" / "state" / "kernel-drafts"
            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_file = draft_dir / f"draft-{today}-{matched_signal}.md"
            if not draft_file.exists():
                prompt_summary = prompt[:200].replace("\n", " ")
                draft_content = (
                    f"# Kernel Draft — {today}\n"
                    f"\n"
                    f"## 触发场景\n"
                    f"检测到纠正信号「{matched_signal}」\n"
                    f"\n"
                    f"## 用户输入摘要\n"
                    f"{prompt_summary}\n"
                    f"\n"
                    f"## 建议规则格式\n"
                    f"- ```\n"
                    f"禁止/必须 xxx — （待补充具体规则）\n"
                    f"```\n"
                    f"\n"
                    f"## 根因分析\n"
                    f"（待补充 — AI 应在当前会话中完成根因分析）\n"
                    f"\n"
                    f"## 证据模板\n"
                    f"- 触发词: {matched_signal}\n"
                    f"- 日期: {today}\n"
                    f"- 来源: pretool-user-correction.py 自动捕获\n"
                    f"- 验证: （待补充 file:line 或命令输出）\n"
                    f"\n"
                )
                try:
                    draft_file.write_text(draft_content, encoding="utf-8")
                except Exception:
                    pass
                flywheel_event("kernel_draft_created", f"correction_signal:{matched_signal}", "P3", "kernel_draft")

        # 输出视觉提醒
        print(file=sys.stderr)
        print(f"╔══ [纠正检测] 检测到纠正信号（'{matched_signal}'）══════════════════╗", file=sys.stderr)
        if already_written:
            print("║ 今日记录已存在，跳过重复写入 claude-next.md                      ║", file=sys.stderr)
        else:
            print("║ 已自动写入骨架到 .claude/claude-next.md                          ║", file=sys.stderr)
        print("║ ⛔ 停止当前执行流！用户纠正信号 = 方向错误，先确认再继续              ║", file=sys.stderr)
        print("║ AI 应在当前输出中引用并补充：问题+根因+纠正                      ║", file=sys.stderr)
        print("╚══════════════════════════════════════════════════════════════════╝", file=sys.stderr)
        print(file=sys.stderr)

    # 透传原始输入（Claude Code 协议要求：UserPromptSubmit hook 必须将用户输入回写 stdout）
    print(prompt, end="")
    if triggered:
        flywheel_event("pretool_user_correction", "correction_detected", "P2", "correction_signal")
    sys.exit(0)


if __name__ == "__main__":
    main()
