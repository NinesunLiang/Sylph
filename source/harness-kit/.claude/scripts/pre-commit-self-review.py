#!/usr/bin/env python3
"""
pre-commit-self-review.py — E6 自我矛盾防线（P2a）
Python 移植版，完全等价 pre-commit-self-review.sh v1.0

角色：提交前的 AI 自检工具。检查 CAPTCHA 绕过(R43)、域规则误用(R42)、新 hook 注册完整性(Oracle WARN)。
用途：在 git commit 之前运行，预防 AI 引入自我矛盾的设计漏洞
不是 Hook — 是手动审查工具。不注册到 settings.json，不通过 harness.yaml 开关控制。

使用方法:
  python3 .claude/scripts/pre-commit-self-review.py "commit message"
  python3 .claude/scripts/pre-commit-self-review.py  # 仅检查 staged diff

输出格式:
  ✅ PASS (a): ...   — 未发现问题
  ⚠️ WARN (b): ...  — 非阻断性警告（exit 0 + additionalContext）
  🔴 FAIL (c): ...  — 阻断性漏洞（exit 2）

返回码:
  0 — 全部通过 或 仅警告
  2 — 发现明确安全/设计漏洞
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ─── Path initialization ───
# The script lives in .claude/scripts/, cd to .claude/ is done via parent
SCRIPT_DIR = Path(__file__).resolve().parent
CLAUDE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CLAUDE_DIR.parent

PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)


def run(cmd: list[str], cwd: str = None) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd or str(PROJECT_ROOT))


def main():
    os.chdir(str(CLAUDE_DIR))

    commit_msg = sys.argv[1] if len(sys.argv) > 1 else ""
    has_blocking = False
    has_warning = False
    results = ""

    print("=== pre-commit-self-review: E6 自我矛盾防线 ===")
    print("")

    # Get staged diff
    staged_diff = run(["git", "diff", "--cached"]).stdout
    staged_files = run(["git", "diff", "--cached", "--name-only"]).stdout
    new_files_staged = run(["git", "diff", "--cached", "--name-only", "--diff-filter=A"]).stdout
    new_files_unstaged = run(["git", "diff", "--name-only", "--diff-filter=A"]).stdout

    # Merge new files
    new_files_set = set()
    for line in (new_files_staged + "\n" + new_files_unstaged).splitlines():
        line = line.strip()
        if line:
            new_files_set.add(line)

    all_diff = staged_diff
    new_script_files = [f for f in new_files_set if f.endswith((".sh", ".py", ".js", ".ts"))]

    print(f"  提交信息: {commit_msg if commit_msg else '（未提供）'}")
    print(f"  新增文件: {' '.join(sorted(new_files_set))}")
    print("")

    # ============================================================
    # Check (a): CAPTCHA 设计绕过 — R43 安全门
    # ============================================================
    print("--- Check (a): CAPTCHA 设计绕过 ---")

    a_pass = True
    a_failures = ""
    a_warnings = ""

    # 1. Detect scripts writing to sensitive-approved / permission-approved
    sensitive_pattern = r'sensitive-approved|permission-approved'
    exclude_pattern = r'scope_write_regex|CAPTCHA_MARKERS|SCOPE_WRITE_RE|CAPTCHA_PAIRS|approve-detect'
    for line in all_diff.splitlines():
        if re.search(sensitive_pattern, line) and not re.search(exclude_pattern, line):
            if not line.startswith("+++") and not line.startswith("---") and not line.startswith("diff ") and not line.startswith("index "):
                if any(f.endswith((".sh", ".py", ".js")) for f in new_files_set):
                    a_pass = False
                    matching = [f for f in new_files_set if f.endswith((".sh", ".py", ".js"))]
                    a_failures += f"  检测到脚本文件操作 CAPTCHA 批准文件 (sensitive-approved/permission-approved)\n"
                    a_failures += f"  R43: AI 可通过 Bash 调用创建批准标记 = 设计级安全漏洞\n"
                    a_failures += f"  涉及文件: {' '.join(matching)}\n"
                    a_failures += "  请删除该机制，改用原生 permissionDecision:ask + CAPTCHA 用户输入模式\n"
                    has_blocking = True
                    break

    # 2. Check new scripts for approve/bypass semantics
    for script_path in new_script_files:
        full_path = Path(script_path)
        if not full_path.exists():
            continue
        content = full_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r'(approve|bypass|auto\.approve|skip\.gate|skip\.permission)', content, re.IGNORECASE):
            # Exclude comment references to R43
            bad_lines = []
            for line in content.splitlines():
                if re.search(r'(approve|bypass|auto\.approve|skip\.gate)', line, re.IGNORECASE):
                    if not re.match(r'^\s*#.*(R43|教训|禁止|不)', line):
                        bad_lines.append(line.strip())
            if bad_lines:
                a_pass = False
                a_failures += f"  新脚本 {script_path} 包含批准/绕过语义\n"
                a_failures += "  这可能创建 AI 可调用的 CAPTCHA 批准通道 (R43)\n"
                a_failures += f"  相关行: {'; '.join(bad_lines[:3])}\n"
                has_blocking = True

        # 3. Check for permission-required → permission-approved chain
        if 'permission-required' in content and ('permission-approved' in content or 'sensitive-approved' in content):
            a_pass = False
            a_failures += f"  新脚本 {script_path} 同时引用 permission-required 和批准文件\n"
            a_failures += "  这是自动批准通道的特征 (R43)\n"
            has_blocking = True

    # 4. Check .zshrc/.bashrc for approval bypass
    for rc_file in new_files_set:
        if rc_file.endswith((".zshrc", ".bashrc", ".bash_profile", ".zprofile")):
            rc_path = Path(rc_file)
            if rc_path.exists():
                content = rc_path.read_text(encoding="utf-8", errors="replace")
                if re.search(r'sensitive-approved|permission-approved|approve-sen', content):
                    a_pass = False
                    a_failures += f"  shell rc 文件 {rc_file} 包含 CAPTCHA 批准引用\n"
                    a_failures += "  可能将批准工具暴露为 shell 别名/函数 (R43)\n"
                    has_blocking = True

    if a_pass:
        print("  ✅ PASS (a): 未检测到 CAPTCHA 设计绕过")
    elif not a_failures:
        print("  ⚠️ WARN (a): 模糊信号，非阻断性提示")
        has_warning = True
    else:
        print("  🔴 FAIL (a): CAPTCHA 设计绕过检测")
        print(a_failures)
    print("")

    # ============================================================
    # Check (b): 域规则误用 — R42 域隔离
    # ============================================================
    print("--- Check (b): 域规则误用 ---")

    b_pass = True
    b_warnings = ""
    b_failures = ""
    b_warn_only = False

    # 1. Detect settings.json/harness.yaml references next to skill
    if re.search(r'(settings\.json|harness\.yaml).*skill', all_diff):
        b_pass = False
        b_warnings += "  检测到 settings.json/harness.yaml 与 skill 关联引用\n"
        b_warnings += "  R42: Skill 不需要 settings.json 注册。SKILL.md 在 .claude/skills/<name>/ 存在 + feature-registry.yaml 引用 = 合法\n"
        b_warnings += "  请确认这些引用不是将 hook 注册规则应用于 skill\n"
        has_warning = True

    # 2-3. Check new scripts for domain confusion
    for script_path in new_script_files:
        full_path = Path(script_path)
        if not full_path.exists():
            continue
        content = full_path.read_text(encoding="utf-8", errors="replace")
        has_settings = 'settings.json' in content
        has_skills = '.claude/skills/' in content

        if has_settings and has_skills:
            if 'Hook.*zombie' in content or 'Skill.*zombie' in content or '区分.*类型' in content:
                b_warn_only = True
            b_pass = False
            b_warnings += f"  新脚本 {script_path} 同时引用 settings.json 和 .claude/skills/\n"
            b_warnings += "  R42: 确认不是将 hook 注册规则（settings.json）错误应用到 skill 验收\n"
            b_warnings += "  如果脚本已明确区分两种类型（hook zombie vs skill zombie），可忽略此警告\n"
            has_warning = True

        if re.search(r'\.claude/skills/.*settings\.json', content):
            b_pass = False
            b_failures += f"  用 settings.json 注册验证 skill 文件 — 域规则误用\n"
            b_failures += "  R42: Skill 不需要 settings.json 注册。这是 hook 的注册规则\n"
            has_blocking = True

    # 4. Ghost mode changes with domain confusion
    if re.search(r'zombie.*(scan|detect|clean|remov)', all_diff, re.IGNORECASE) and 'settings.json' in all_diff:
        if not re.search(r'(Hook.*zombie|Skill.*zombie|区分.*类型|different.*criteria)', all_diff):
            b_pass = False
            b_failures += "  检测到僵尸清理逻辑而未区分 Hook/Skill 两种判定标准\n"
            b_failures += "  R42: 僵尸扫描必须区分 hook（R23 规则）和 skill（disk + feature-registry.yaml）\n"
            b_failures += "  建议添加类型区分逻辑，否则可能误删 skill\n"
            has_blocking = True

    if b_pass:
        print("  ✅ PASS (b): 未检测到域规则误用")
    elif b_warn_only and not b_failures:
        print("  ✅ PASS (b): 域规则误用 — 脚本已明确区分，无实际问题")
    elif b_failures or (has_blocking and b_warnings):
        print("  🔴 FAIL (b): 域规则误用检测")
        if b_warnings:
            print(b_warnings)
        if b_failures:
            print(b_failures)
    else:
        print("  ⚠️ WARN (b): 域规则交叉引用，建议人工审查")
        if b_warnings:
            print(b_warnings)
    print("")

    # ============================================================
    # Check (c): 新机制完整性 — Oracle Stage 1: WARNING 级别
    # ============================================================
    print("--- Check (c): 新机制完整性 ---")

    c_pass = True
    c_warnings = ""

    # 1. Detect new/modified hooks
    hook_all_files = set()
    for line in staged_files.splitlines():
        line = line.strip()
        if line and re.search(r'\.claude/hooks/[^/]+\.sh$', line) and 'harness_config.sh' not in line:
            hook_all_files.add(line)
    for f in new_files_set:
        if re.search(r'\.claude/hooks/[^/]+\.sh$', f) and 'harness_config.sh' not in f:
            hook_all_files.add(f)

    for hook_path in hook_all_files:
        hook_name = Path(hook_path).stem
        yaml_key = hook_name.replace("-", "_")

        full_hook_path = Path(hook_path)
        if not full_hook_path.exists():
            continue
        content = full_hook_path.read_text(encoding="utf-8", errors="replace")

        missing_hc = 'hc_enabled ' not in content
        missing_yaml = False

        # Check harness.yaml
        harness_yaml = CLAUDE_DIR / "harness.yaml"
        if harness_yaml.exists():
            yaml_content = harness_yaml.read_text(encoding="utf-8")
            # Simple check: look for hooks_enabled section with the key
            in_section = False
            found = False
            for line in yaml_content.splitlines():
                if re.match(r'hooks_enabled:', line):
                    in_section = True
                    continue
                if in_section:
                    if line.startswith(" "):
                        if re.match(rf'\s+{re.escape(yaml_key)}:', line):
                            found = True
                            break
                    else:
                        in_section = False
            if not found:
                missing_yaml = True

        if missing_hc or missing_yaml:
            c_pass = False
            c_warnings += f"  ⚠️  {hook_path}:\n"
            if missing_hc:
                c_warnings += f"     缺少 hc_enabled 调用 — 请添加 hc_enabled \"{yaml_key}\" || exit 0\n"
            if missing_yaml:
                c_warnings += f"     harness.yaml 缺少 hooks_enabled.{yaml_key} 条目\n"
            c_warnings += "     （Oracle Stage 1: 这是 WARNING，非阻断 — sync 在发布时完成）\n"
            has_warning = True

    # 2. Check harness.yaml changes (disabled switch but script still registered)
    if 'harness.yaml' in staged_files:
        harness_yaml = CLAUDE_DIR / "harness.yaml"
        if harness_yaml.exists():
            yaml_content = harness_yaml.read_text(encoding="utf-8")
            in_section = False
            for line in yaml_content.splitlines():
                if re.match(r'hooks_enabled:', line):
                    in_section = True
                    continue
                if in_section:
                    m = re.match(r'\s+(\w+):\s*false', line)
                    if m:
                        yk = m.group(1)
                        script_name = yk.replace("_", "-") + ".sh"
                        hook_path = CLAUDE_DIR / "hooks" / script_name
                        if hook_path.exists() and script_name != "harness_config.sh":
                            settings_json = CLAUDE_DIR / "settings.json"
                            if settings_json.exists():
                                settings_content = settings_json.read_text(encoding="utf-8")
                                if script_name in settings_content:
                                    c_pass = False
                                    c_warnings += f"  ⚠️  {script_name}: harness.yaml 禁用但 settings.json 仍注册\n"
                                    c_warnings += "    R36: 三方同步要求 — 禁用需同步 settings.json 移除注册\n"
                                    c_warnings += "    （Oracle Stage 1: WARNING 级别 — 可能是有意保留的占位）\n"
                                    has_warning = True
                    elif not line.startswith(" "):
                        in_section = False

    if c_pass:
        print("  ✅ PASS (c): 新机制完整性检查通过")
    else:
        print("  ⚠️ WARN (c): 新机制完整性 — 发现可改进项")
        print(c_warnings)
    print("")

    # ============================================================
    # Check (d): settings.json command 语法校验 — DF-04
    # ============================================================
    print("--- Check (d): settings.json command 语法校验 ---")

    d_pass = True
    d_failures = ""

    settings_json = CLAUDE_DIR / "settings.json"
    if 'settings.json' in staged_files or settings_json.exists():
        if settings_json.exists():
            try:
                with open(settings_json, "r") as f:
                    settings_data = json.load(f)

                bad_cmds = []
                for event, matchers in settings_data.get("hooks", {}).items():
                    if isinstance(matchers, list):
                        for m in matchers:
                            for h in m.get("hooks", []):
                                cmd = h.get("command", "")
                                if not cmd:
                                    continue
                                # Write to temp file and check with bash -n
                                with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as tf:
                                    tf.write("#!/usr/bin/env bash\n")
                                    tf.write(cmd + "\n")
                                    tf.flush()
                                    tf_path = tf.name
                                try:
                                    r = subprocess.run(
                                        ["bash", "-n", tf_path],
                                        capture_output=True, text=True, timeout=5
                                    )
                                    if r.returncode != 0:
                                        bad_cmds.append(f"{cmd[:80]}  ->  {r.stderr.strip()[:100]}")
                                except Exception as e:
                                    bad_cmds.append(f"{cmd[:80]}  ->  parse error: {e}")
                                finally:
                                    os.unlink(tf_path)

                if bad_cmds:
                    d_pass = False
                    d_failures += "  以下 settings.json command 未通过 bash -n 语法检查:\n"
                    for bc in bad_cmds[:10]:
                        d_failures += f"    {bc}\n"
                    d_failures += "\n  DF-04: 损坏的 shell 语法会导致 hook 无法执行，系统完全不能自愈\n"
                    d_failures += "  修复: 用纯文本绝对路径 'bash /path/to/script.sh' 替代含引号变量展开\n"
                    has_blocking = True
            except Exception as e:
                print(f"  ⚠️ SKIP (d): settings.json 读取失败: {e}")
        else:
            print("  ⏭️ SKIP (d): settings.json 未变更，跳过 command 语法校验")
    else:
        print("  ⏭️ SKIP (d): settings.json 未变更，跳过 command 语法校验")

    if d_pass:
        print("  ✅ PASS (d): settings.json command 语法校验通过")
    elif d_failures:
        print("  🔴 FAIL (d): settings.json command 语法错误")
        print(d_failures)
    print("")

    # ============================================================
    # Final verdict
    # ============================================================
    print("========================================")
    if has_blocking:
        print("  VERDICT: 🔴 BLOCKING — 存在安全/设计漏洞")
        print("  修复后重新运行此检查，确认无 FAIL 后再提交")
        print("========================================")
        sys.exit(2)
    elif has_warning:
        print("  VERDICT: ⚠️ PASS WITH WARNINGS — 建议审查上述警告")
        print("  非阻断：提交前确认警告不涉及设计级问题即可继续")
        print("========================================")
        sys.exit(0)
    else:
        print("  VERDICT: ✅ ALL PASS — 三项自检全部通过")
        print("========================================")
        sys.exit(0)


if __name__ == "__main__":
    main()
