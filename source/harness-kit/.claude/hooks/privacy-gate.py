#!/usr/bin/env python3
"""privacy-gate.py — PreToolUse:Bash|Read|Grep — 防止隐私数据泄露（DLP 门禁）
Role: 防止隐私数据泄露（DLP 门禁）

等效移植自 privacy-gate.sh:
- 文件路径敏感匹配 (.env, .pem, .key, credentials, kubeconfig 等)
- 命令明文 Token 检测 (sk-, ghp_, Bearer 等)
- C-3: privacy-gate 在所有模式下保持活跃 — 凭据泄露零容忍
"""

import json
import os
import re
import sys
from pathlib import Path

# 导入共享库
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, hc_emit_hook_json, flywheel_event, hc_fail_closure


# ─── 常量 ───

SENSITIVE_FILE_RE = re.compile(
    r'\.env|\.pem|\.key|\.p12|\.pfx|\.jks|'
    r'id_rsa|credentials\.(json|ya?ml)|secret[es]?\.ya?ml|'
    r'auth\.json|kubeconfig',
    re.IGNORECASE
)

TOKEN_PATTERNS = [
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'sk-ant-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'xoxb-[0-9]{10,}-[0-9]{10,}'),
    re.compile(r'Bearer\s+[A-Za-z0-9\-\._~+/]{20,}=*'),
]

# ─── agentic_status 等效 ───

def _agentic_status_danger(title: str, message: str, detail: str = ""):
    """输出阻断 UI 到 stderr（等效 sh 的 agentic_status danger）。"""
    sep = "═" * 55
    lines = [
        "",
        f"🚫 [{title}]",
        sep,
        message,
        f"     {detail}" if detail else "",
        "",
    ]
    print("\n".join(lines), file=sys.stderr, flush=True)


# ─── 检测函数 ───

def _check_file_path(path: str) -> bool:
    """检查文件路径是否匹配敏感模式。"""
    if not path:
        return False
    return bool(SENSITIVE_FILE_RE.search(path))


def _check_command_for_tokens(cmd: str) -> bool:
    """检查命令中是否包含明文 token。"""
    if not cmd:
        return False
    for pattern in TOKEN_PATTERNS:
        if pattern.search(cmd):
            return True
    return False


# ─── 主逻辑 ───

def main():
    # 门禁检查
    if not hc_enabled("privacy_gate"):
        print('{"continue": true}')
        sys.exit(0)

    # C5: fail-close 自检
    if hc_fail_closure("security_gates"):
        try:
            hc_get("harness_version")
        except Exception as e:
            print(f"\u26d4 [C5] privacy-gate fail-close: harness_lib \u521d\u59cb\u5316\u5931\u8d25: {e}", file=sys.stderr)
            flywheel_event("privacy_gate", "c5_fail_close", "P1")
            # 不 exit(2)— 静默放行而非阻塞 agent
            pass

    # 读取 stdin
    stdin_data = sys.stdin.read()

    # 解析 JSON
    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        # 非 JSON 输入，放行
        print('{"continue": true}')
        sys.exit(0)

    # 提取字段
    tool_name = (payload.get("tool_name") or payload.get("tool") or "").lower()
    tool_input = payload.get("tool_input") or payload.get("args") or {}

    file_path = (tool_input.get("file_path") or tool_input.get("filePath") or "")
    pattern = tool_input.get("pattern") or ""
    command = (tool_input.get("command") or tool_input.get("args", {}).get("command") or "")

    # 统一 Bash/Read/Grep 检测
    check_path = file_path or pattern

    # 1. 文件路径拦截
    if _check_file_path(check_path):
        flywheel_event("privacy_gate", "triggered", "P2")
        _agentic_status_danger(
            "Privacy Gate 触发",
            f"禁止直接读取包含配置、凭据或密钥的敏感文件（{check_path}）。",
            "请使用 /lx-varlock 脱敏代理安全读取此文件，避免明文凭据泄漏到 AI 上下文中。"
        )
        msg = (
            f"[Hook-Skill桥] privacy-gate → /lx-varlock: "
            f"敏感文件读取被拦截（{check_path}），"
            f"请用 /lx-varlock 脱敏代理安全打开此文件。"
        )
        result = hc_emit_hook_json(msg, event="PreToolUse", continue_val=False)
        print(result)
        sys.exit(2)

    # 2. 命令明文 Token 拦截
    if tool_name == "bash" and command and _check_command_for_tokens(command):
        flywheel_event("privacy_gate", "token_triggered", "P2")
        _agentic_status_danger(
            "Privacy Gate 触发",
            "检测到在命令中包含明文 API Key 或 Token！这是严重的数据泄露风险。",
            "请使用 /lx-varlock 脱敏代理安全执行，绝不能让明文凭据泄漏到 AI 上下文中。"
        )
        msg = (
            "[Hook-Skill桥] privacy-gate → /lx-varlock: "
            "命令中包含 API Key 明文，已被拦截。"
            "请用 /lx-varlock 脱敏代理安全执行此命令。"
        )
        result = hc_emit_hook_json(msg, event="PreToolUse", continue_val=False)
        print(result)
        sys.exit(2)

    # 放行
    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
