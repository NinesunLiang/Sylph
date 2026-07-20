#!/usr/bin/env python3
"""pretool-sensitive-edit.py — PreToolUse:Edit|Write|Bash — 治理文件编辑验证码门禁（哲学 #6 物化）

Role: 对 CLAUDE.md/AGENTS.md/harness.yaml/settings.json 等治理文件的 Edit/Write/Bash
      要求用户 CAPTCHA 确认
哲学 #6：先天对 AI 0 信任 — 治理文件变更须经用户显式授权
Bash 支持 (DF-04): 扫描命令字符串中的文件操作目标，检测 sed/tee/>/>>/cp/mv 操作治理文件路径
"""

import json
import os
import secrets
import sys
import time
from pathlib import Path

# 添加 hooks 目录到 sys.path，以便导入 harness_lib
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from harness_lib import (
    flywheel_event,
    hc_emit_hook_json,
    hc_enabled,
    hc_get,
    is_mode_active,
)

# ─── 路径常量 ───

PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"

# ─── 敏感文件列表 ───

SENSITIVE_FILENAMES = {
    "CLAUDE.md",
    "AGENTS.md",
    "harness.yaml",
    "settings.json",
    "kernel.md",
    "anti-patterns.md",
    "feature-registry.yaml",
    "permission-approved",
    "permission-required",
}

SENSITIVE_PATH_FRAGMENTS = [
    ".claude/harness.yaml",
    ".claude/settings.json",
    ".claude/kernel.md",
    ".claude/anti-patterns.md",
]

# Bash 命令中治理文件路径模式
BASH_GOV_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "harness.yaml",
    "settings.json",
    "kernel.md",
    "anti-patterns.md",
]


def extract_file_path(data):
    """从 JSON 数据中提取 file_path，兼容 Edit/Write/Bash 工具。"""
    tool_input = data.get("tool_input", {}) or {}
    args = data.get("args", {}) or {}
    tool_name = data.get("tool_name", data.get("tool", ""))

    # 优先尝试多种 file_path 字段名
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or args.get("filePath")
        or args.get("file_path")
        or args.get("path")
    )

    if not file_path:
        return None

    # Edit 工具：只有 new_string 存在时才是写操作
    if tool_name == "Edit":
        new_string = tool_input.get("new_string") or args.get("new_string") or ""
        if not new_string:
            return None

    # Write 工具：总是写操作，保留 file_path
    # Bash 工具：由单独逻辑处理

    return file_path


def check_bash_tool(data):
    """检查 Bash 命令是否涉及敏感文件写入操作。返回匹配的文件路径或 None。"""
    tool_name = data.get("tool_name", data.get("tool", ""))
    if tool_name != "Bash":
        return None

    command = (
        data.get("tool_input", {}).get("command")
        or data.get("args", {}).get("command")
        or ""
    )
    if not command:
        return None

    command_oneline = command.replace("\n", " ")

    # 写入操作特征检测
    write_patterns = [
        "sed -i",
        "> ",
        ">>",
        "cp ",
        "mv ",
        "tee ",
        "echo",  # 含 > 的 echo
        "open(",  # python open write
        "install ",
    ]

    has_write_op = False
    for pat in write_patterns:
        if pat in command_oneline:
            has_write_op = True
            break

    if not has_write_op:
        return None

    # 检测写入目标是否涉及治理文件
    for gov_file in BASH_GOV_FILES:
        if gov_file in command_oneline:
            return gov_file

    # 检测 .claude/hooks/ 和 .claude/scripts/ 写入
    if ".claude/hooks/" in command_oneline:
        return "hook"
    if ".claude/scripts/" in command_oneline:
        return "script"

    return None


def is_sensitive_file(file_path):
    """检查文件路径是否匹配敏感文件列表。"""
    if not file_path:
        return False

    basename = os.path.basename(file_path)

    # basename 直接匹配
    if basename in SENSITIVE_FILENAMES:
        return True

    # 路径片段匹配
    for frag in SENSITIVE_PATH_FRAGMENTS:
        if file_path.endswith(frag):
            return True

    return False


def check_captcha_approval():
    """检查是否有有效的 CAPTCHA 批准。
    
    返回 (approved, approval_code)，approved=True 时验证码匹配且在 TTL 内。
    """
    sensitive_marker = STATE_DIR / "sensitive-approved"
    sensitive_required = STATE_DIR / "sensitive-required"

    if not sensitive_required.exists():
        return False, None

    expected_code = sensitive_required.read_text(encoding="utf-8", errors="replace").strip()

    if sensitive_marker.exists() and expected_code:
        actual_code = sensitive_marker.read_text(encoding="utf-8", errors="replace").strip()

        if actual_code == expected_code:
            # 检查 TTL
            try:
                cache_ttl = int(hc_get("permission_gate.approved_ops_ttl", "1800"))
                age = time.time() - sensitive_marker.stat().st_mtime
                fresh = age < cache_ttl
            except (ValueError, OSError):
                fresh = True

            if fresh:
                # 批准有效，清理标记
                sensitive_marker.unlink(missing_ok=True)
                sensitive_required.unlink(missing_ok=True)
                return True, expected_code

    # 批准无效或过期，清理 required 文件
    sensitive_required.unlink(missing_ok=True)
    return False, None


def output_captcha_block(base_name, approval_code):
    """输出 CAPTCHA 阻断消息（等效 agentic_captcha 函数）。"""
    approve_file = ".omc/state/sensitive-approved"

    flywheel_event("pretool_sensitive_edit", "blocked", "P2")
    flywheel_event("agentic_ui", "captcha_shown", "P2", f"敏感文件编辑: {base_name}")

    title = f"敏感文件编辑: {base_name}"
    description = (
        "治理文件变更须经用户显式授权。"
        "AI 不得自行绕过门禁 — 必须等待人类明确书面授权（kernel.md:26 R42）。"
    )

    # stderr 输出
    print(f"🔑 [{title}] 需要批准 — 请查看 AI 的说明", file=sys.stderr)

    # 输出 hook JSON
    captcha_msg = (
        f"[CAPTCHA] {title} | 验证码: {approval_code} | "
        f"批准文件: {approve_file} | {description} | "
        f"终端执行: echo \"{approval_code}\" > {approve_file} | "
        f"批准后 AI 行动协议: 检查批准文件是否存在(cat {approve_file} 2>/dev/null)，"
        f"存在则重试被阻断的原操作，不存在则等待用户批准"
    )

    result = hc_emit_hook_json(captcha_msg, event="PreToolUse", continue_val=True)
    print(result)
    sys.exit(2)


def main():
    # 检查功能是否启用
    if not hc_enabled("pretool_sensitive_edit"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 模式检测: ghost/goal 降级为 log+skip ──
    mode = is_mode_active(str(STATE_DIR))
    if mode != "normal":
        print(f"[{mode}] 敏感文件编辑已记录（模式降级，不阻断）", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 读取 stdin JSON ──
    try:
        raw_input = sys.stdin.read()
        data = json.loads(raw_input)
    except (json.JSONDecodeError, Exception) as e:
        print(f"⛔ [pretool-sensitive-edit] JSON 解析失败: {e}", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 提取文件路径 ──
    file_path = extract_file_path(data)

    # ── Bash 工具特殊处理：从命令中扫描敏感文件 ──
    if not file_path:
        file_path = check_bash_tool(data)

    # ── 没有文件路径，放行 ──
    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 检查是否为敏感文件 ──
    if not is_sensitive_file(file_path):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 检查 CAPTCHA 是否已批准 ──
    approved, _ = check_captcha_approval()
    if approved:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 生成验证码并保存 ──
    try:
        approval_code = secrets.token_hex(4)
    except Exception:
        import random
        import string
        approval_code = "sen-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    os.makedirs(str(STATE_DIR), exist_ok=True)
    sensitive_required = STATE_DIR / "sensitive-required"
    try:
        with open(str(sensitive_required), "w", encoding="utf-8") as f:
            f.write(approval_code + "\n")
    except (IOError, OSError) as e:
        print(f"⛔ [pretool-sensitive-edit] 无法写入验证码文件: {e}", file=sys.stderr)
        print(json.dumps({"continue": False}))
        sys.exit(2)

    # ── 输出 CAPTCHA 阻断 ──
    base_name = os.path.basename(file_path)
    output_captcha_block(base_name, approval_code)


if __name__ == "__main__":
    main()
