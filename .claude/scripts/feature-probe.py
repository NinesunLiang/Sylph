#!/usr/bin/env python3
"""feature-probe.py — 工具脚本（非 Hook）— 手动诊断工具，检查 feature 的 L1-L4 证据链完整性
Role: 手动诊断工具，检查 feature 的 L1-L4 证据链完整性
"""
import sys
import json
import subprocess
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
FEATURE_REGISTRY = PROJECT_ROOT / ".claude/feature-registry.yaml"


def usage():
    print("Usage: python3 feature-probe.py <feature_name> [--json]")
    print("Probe a registered feature (hook or skill) and output L1-L4 evidence.")
    sys.exit(1)


def run(cmd, **kwargs):
    default = {"capture_output": True, "text": True, "shell": True}
    default.update(kwargs)
    result = subprocess.run(cmd, **default)
    return result.stdout.strip(), result.returncode, result.stderr


# 解析参数
FEATURE_NAME = sys.argv[1] if len(sys.argv) > 1 else ""
OUTPUT_JSON = False
if len(sys.argv) > 2 and sys.argv[2] == "--json":
    OUTPUT_JSON = True

if not FEATURE_NAME:
    usage()


def _hook_scripts(name):
    """检查 hook 脚本是否存在"""
    dashed = name.replace("_", "-")
    # 同时支持横线名和下划线名
    for candidate in [f"{dashed}.py", f"{name}.py"]:
        f = SCRIPT_DIR / candidate
        if f.is_file():
            return str(f)
    return ""


def _skill_dir(name):
    """检查 skill 目录是否存在"""
    d = PROJECT_ROOT / f".claude/skills/{name}"
    return str(d) if d.is_dir() else ""


def _skill_skillmd(name):
    """检查 SKILL.md 是否存在"""
    f = PROJECT_ROOT / f".claude/skills/{name}/SKILL.md"
    return str(f) if f.is_file() else ""


def _skill_scripts(name):
    """检查 skill 是否有 scripts/ 目录"""
    d = PROJECT_ROOT / f".claude/skills/{name}/scripts"
    if d.is_dir():
        files = []
        for ext in ["*.py", "*.sh"]:
            files.extend([str(p) for p in sorted(d.glob(ext))[:3]])
        return "\n".join(files)
    return ""


def _registry_enabled(name):
    """检查 feature 是否在 registry 中注册"""
    try:
        import yaml
        if FEATURE_REGISTRY.is_file():
            with FEATURE_REGISTRY.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for hook in data.get("hooks", []):
                if hook.get("name") == name:
                    return str(hook.get("enabled_by_default", True))
            for skill in data.get("skills", []):
                if skill.get("name") == name:
                    return str(skill.get("enabled_by_default", True))
        return "True"
    except Exception:
        return "True"


def _bash_syntax(file):
    """bash 语法检查"""
    if not file:
        return "N/A"
    if file.endswith(".py"):
        try:
            compile(Path(file).read_text(encoding="utf-8"), file, "exec")
            return ""
        except SyntaxError as e:
            return str(e)
    stdout, rc, stderr = run(f"bash -n \"{file}\" 2>&1; echo $?")
    return stdout.strip()


def probe(name):
    """主探针逻辑"""
    hook_script = _hook_scripts(name)
    sk_dir = _skill_dir(name)
    sk_md = _skill_skillmd(name)
    syntax_check = "N/A"
    file_path = ""
    file_exists = False

    if hook_script:
        file_exists = True
        file_path = hook_script
        syntax_check = _bash_syntax(hook_script)
    elif sk_md:
        file_exists = True
        file_path = sk_md
        syntax_check = "SKILL.md (text)"
    elif sk_dir:
        file_exists = True
        file_path = sk_dir
        syntax_check = f"SKILL.md not found in {sk_dir}"

    # L4: 注册存在性
    l4 = "NOT_TESTABLE"
    try:
        import yaml
        if FEATURE_REGISTRY.is_file():
            with FEATURE_REGISTRY.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            found = False
            for hook in data.get("hooks", []):
                if hook.get("name") == name:
                    found = True
                    break
            for skill in data.get("skills", []):
                if skill.get("name") == name:
                    found = True
                    break
            l4 = "PASS" if found else "NOT_REGISTERED (feature not found in registry)"
        else:
            l4 = "NOT_TESTABLE (registry missing)"
    except ImportError:
        l4 = "NOT_TESTABLE (yaml library missing)"
    except Exception:
        l4 = "NOT_TESTABLE"

    # L3: 文件存在 + 语法
    l3 = ""
    if file_exists and not syntax_check:
        l3 = f"PASS ({file_path})"
    elif file_exists and syntax_check == "SKILL.md (text)":
        l3 = f"PASS ({file_path})"
    elif file_exists:
        l3 = f"SYNTAX_ERROR ({syntax_check})"
    else:
        l3 = "NOT_FOUND"

    # L2: harness 中启用状态
    harness_val = _registry_enabled(name).lower()
    l2 = f"ENABLED in harness.yaml" if harness_val == "true" else "DISABLED in harness.yaml"

    # L1: 完整功能验证
    l1 = ""
    if hook_script and not syntax_check:
        stdout, rc, stderr = run(f"python3 \"{hook_script}\" 2>/dev/null; echo $?")
        exit_code = int(stderr.strip() or stdout.strip().split("\n")[-1] if stderr else "0")
        if exit_code == 0 or exit_code == 2:
            l1 = f"PASS (executable, exit={exit_code})"
        else:
            l1 = f"UNEXPECTED_EXIT (exit={exit_code})"
    elif sk_md:
        l1 = "MANUAL (SKILL.md requires AI context, not auto-testable)"
    else:
        l1 = "NOT_TESTABLE"

    print(f"FEATURE: {name}")
    print(f"  L1 (functional):   {l1}")
    print(f"  L2 (config):       {l2}")
    print(f"  L3 (file+compile): {l3}")
    print(f"  L4 (registered):   {l4}")


def probe_json(name):
    """JSON 格式探针"""
    hook_script = _hook_scripts(name)
    sk_dir = _skill_dir(name)
    sk_md = _skill_skillmd(name)
    harness_val = _registry_enabled(name).lower()

    l1 = "NOT_TESTABLE"
    if hook_script:
        stdout, rc, stderr = run(f"python3 \"{hook_script}\" 2>/dev/null; echo $?")
        exit_code = int(stderr.strip() or "1")
        if exit_code == 0 or exit_code == 2:
            l1 = "PASS"
        else:
            l1 = "UNEXPECTED_EXIT"
    elif sk_md:
        l1 = "MANUAL"

    l3_path = hook_script or sk_md or sk_dir or ""

    registered = False
    try:
        import yaml
        if FEATURE_REGISTRY.is_file():
            with FEATURE_REGISTRY.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for hook in data.get("hooks", []):
                if hook.get("name") == name:
                    registered = True
                    break
            for skill in data.get("skills", []):
                if skill.get("name") == name:
                    registered = True
                    break
    except Exception:
        pass

    result = {
        "feature": name,
        "evidence": {
            "L1": l1,
            "L2": harness_val,
            "L3": l3_path,
            "L4": "REGISTERED" if registered else "NOT_REGISTERED"
        }
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


# 执行探针
if OUTPUT_JSON:
    probe_json(FEATURE_NAME)
else:
    probe(FEATURE_NAME)
