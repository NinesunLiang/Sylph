#!/usr/bin/env python3
"""
pretool-skill-body-enforce.py — PreToolUse:Skill — 强制执行合约注入
在 skill 执行前自动将 body.md 内容注入 additionalContext，
确保 AI 无法"选择不看"执行合约。
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("skill_body_enforce"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    skills_dir = project_root / ".claude" / "skills"

    # 解析 skill 名称
    skill = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or parsed.get("args", {})
            skill = ti.get("skill", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not skill:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 定位 SKILL.md
    skill_md = skills_dir / skill / "SKILL.md"
    if not skill_md.exists():
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 检查 ghost/goal 模式降级
    mode = is_mode_active(str(state_dir))
    if mode != "normal":
        flywheel_event("skill_body_enforce", "mode_skip", "P3", f"skill={skill} mode={mode}")
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 读取 body_ref
    body_ref = ""
    try:
        content = skill_md.read_text(encoding="utf-8")
        m = re.search(r'^body_ref:\s*(.+)$', content, re.MULTILINE)
        if m:
            body_ref = m.group(1).strip()
    except Exception:
        pass

    if not body_ref:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 解析 body_ref 路径（相对于 SKILL.md 目录）
    skill_dir = skill_md.parent
    body_path = skill_dir / body_ref

    # 读取 body.md 内容
    if body_path.exists():
        try:
            body_content = body_path.read_text(encoding="utf-8")[:3000]
        except Exception:
            body_content = ""
    else:
        body_content = f"[body.md 缺失] 文件不存在: {body_path}"

    # 构建注入消息
    inject_msg = (
        f"[skill-body-enforce] === 强制执行合约 ===\n"
        f"Skill: {skill}\n"
        f"body_ref: {body_ref}\n"
        f"--- body.md 内容 ---\n"
        f"{body_content}\n"
        f"--- end body.md ---\n"
        f"你必须严格按 body.md 定义的步骤执行，不可跳过或自行发挥。\n"
        f"如 body.md 中定义的脚本缺失，使用 body.md 中的降级策略。"
    )

    # 通过 hc_emit_hook_json 注入 additionalContext
    print(hc_emit_hook_json(inject_msg, "PreToolUse", True))
    flywheel_event("skill_body_enforce", "injected", "P2", f"skill={skill} body_ref={body_ref}")
    sys.exit(0)


if __name__ == "__main__":
    main()
