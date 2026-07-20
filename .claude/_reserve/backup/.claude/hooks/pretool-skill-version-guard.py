#!/usr/bin/env python3
"""
pretool-skill-version-guard.py — PreToolUse:Edit|Write — SKILL.md 版本格式 + 引用有效性门禁
拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式（指向 VERSION.json 单一真相源）
拦截 @references 指向不存在文件的写入
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event


def main():
    if not hc_enabled("pretool_skill_version_guard"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    # 解析 file_path 和 content
    file_path = ""
    content = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or parsed.get("args", {})
            file_path = ti.get("file_path", "") or ti.get("filePath", "") or ""
            content = ti.get("content", "") or ti.get("new_str", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 只检查 SKILL.md 或 TEMPLATE.md
    basename = Path(file_path).name
    if basename not in ("SKILL.md", "TEMPLATE.md"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 无内容 → 不检查（可能是删除操作）
    if not content:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    warnings = []

    # ── Check 1: harness_version 必须是 >= 格式 ──
    hv_match = re.search(r'^harness_version:\s*"([^"]*)"', content, re.MULTILINE)
    if hv_match:
        hv_value = hv_match.group(1)
        if not re.match(r'^>=', hv_value):
            print(f"❌ [version-guard] {file_path}: harness_version=\"{hv_value}\" 是硬编码版本号", file=sys.stderr)
            print("   规则: SKILL.md 必须使用 >= 格式（如 \">=6.3.0\"），不能写具体版本号", file=sys.stderr)
            print("   原因: 版本号唯一真相源是 VERSION.json，SKILL.md 只声明最低兼容版本", file=sys.stderr)
            result = json.dumps({
                "continue": True,
                "reason": f"harness_version must use >= format (e.g. \">=6.3.0\"), not hardcoded version. See VERSION.json for current version."
            })
            print(result)
            sys.exit(2)

    # ── Check 2: @references 必须指向存在的文件 ──
    skill_dir = Path(file_path).parent
    bad_refs = []

    # 提取所有 @../../ 引用
    refs = re.findall(r'@[`]?\.\./[`]?[^\s`\n]+', content)
    for ref in refs:
        # 跳过非文件引用
        if not re.search(r'\.(md|yaml|json|py|sh)$', ref):
            continue
        clean = ref.lstrip("@").replace("`", "")
        resolved = (skill_dir / clean).resolve()
        if not resolved.exists():
            bad_refs.append(f"  {ref} → {resolved}")

    if bad_refs:
        print(f"⚠️  [version-guard] {file_path}: @references 指向不存在的文件:", file=sys.stderr)
        for br in bad_refs:
            print(br, file=sys.stderr)
        print("   建议: 先创建目标文件，再引用；或使用 .claude/scripts/validate-skill.sh 校验", file=sys.stderr)
        warnings.append("- @references 指向不存在的文件")

    # 输出结果
    if warnings:
        warn_text = "\n".join(warnings)
        print(f"⚠️  [version-guard] 通过但有警告:\n{warn_text}", file=sys.stderr)
        flywheel_event("skill-version-guard", "warnings_in_use", "P2")
    else:
        print(f"✅ [version-guard] {basename} 版本格式 + 引用检查通过", file=sys.stderr)

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
