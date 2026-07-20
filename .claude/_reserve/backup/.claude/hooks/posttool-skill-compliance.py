#!/usr/bin/env python3
"""
posttool-skill-compliance.py — PostToolUse:Skill — 执行合规审计
在 skill 执行后审计 AI 是否按 body.md 执行了，发现偏差则注入警告
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("skill_compliance_audit"):
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
        flywheel_event("skill_compliance_audit", "mode_skip", "P3", f"skill={skill} mode={mode}")
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

    # 解析 body_ref 路径
    skill_dir = skill_md.parent
    body_path = skill_dir / body_ref

    # 提取 body.md 中定义的脚本路径（原子化声明）
    expected_scripts = []
    if body_path.exists():
        try:
            body_content = body_path.read_text(encoding="utf-8")
            # 提取 scripts/ 目录下的脚本引用
            for pattern in [
                r'["\']?\.\./scripts/([^"\' )]+)["\']?',
                r'["\']?scripts/([^"\' )]+)["\']?',
                r'["\']?\.\./\.\./scripts/([^"\' )]+)["\']?',
            ]:
                matches = re.findall(pattern, body_content)
                expected_scripts.extend(matches)
        except Exception:
            pass

    # 审计: 检查 hook-evidence.jsonl 中是否有对应脚本的执行记录
    evidence_file = state_dir / "hook-evidence.jsonl"
    audit_passed = True
    audit_details = []

    if expected_scripts and evidence_file.exists():
        try:
            evidence_text = evidence_file.read_text(encoding="utf-8")
        except Exception:
            evidence_text = ""

        for script in expected_scripts:
            if not script:
                continue
            if script in evidence_text:
                audit_details.append(f"  ✅ {script}")
            else:
                audit_details.append(f"  ⚠️  {script} (无执行证据)")
                audit_passed = False

    # 如果 body.md 定义了脚本但未找到执行证据 → 注入警告
    if not audit_passed:
        warn_lines = [
            f"[skill-compliance] ⚠️ 执行合规审计: {skill}",
            f"body_ref: {body_ref}",
            "期望执行但未找到证据:",
        ]
        for detail in audit_details:
            if "⚠️" in detail:
                warn_lines.append(detail)
        warn_lines.append(
            "建议: 验证 body.md 是否被正确执行。如步骤被跳过，请重新执行 skill 或记录偏离原因。"
        )
        warn_msg = "\n".join(warn_lines)
        print(hc_emit_hook_json(warn_msg, "PostToolUse", True))
        flywheel_event("skill_compliance_audit", "non_compliant", "P2", f"skill={skill}")
    else:
        flywheel_event("skill_compliance_audit", "compliant", "P3", f"skill={skill}")

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
