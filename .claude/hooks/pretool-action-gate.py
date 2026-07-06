#!/usr/bin/env python3
"""
pretool-action-gate.py — PreActionGate 4 级裁决

CC hook: PretoolUseExecution
输出: JSON 行到 stdout

4 级裁决: ALLOW / ASK_USER / BLOCK / ESCALATE

- ALLOW: 放行
- ASK_USER: 需要人工确认
- BLOCK: 禁止执行
- ESCALATE: 升级到人类

敏感动作：
  - rm / sudo / force push / 敏感路径写 → BLOCK（无 config）或 ASK_USER（有 config）
  - 读敏感文件 → BLOCK
  - 网络调用 / 安装依赖 → ASK_USER
  - 其余 → ALLOW

Hook 协议: 打印 {"continue": true/false, "message": "..."} 到 stdout。
"""

import json
import os
import re
import sys

# ─── 敏感路径表 ───
SENSITIVE_PATTERNS = [
    r"\.env",
    r"\.ssh[/\\]",
    r"secrets[/\\]",
    r"\.aws[/\\]",
    r"config[/\\]credentials",
    r".*\.pem$",
    r".*\.key$",
    r"id_rsa",
    r"id_ed25519",
]

# ─── 危险命令前缀 ───
DANGEROUS_COMMANDS = [
    "rm -rf", "rm -r", "rm -f",
    "sudo", "chmod 777", "chown",
    "git push --force", "git push -f",
    "dd if=", "mkfs.", "fdisk",
    ":(){ :|:& };:",  # fork bomb
]

DANGEROUS_INSTALL = [
    "pip install", "npm install -g",
    "brew install", "cargo install",
    "curl.*|.*sh", "wget.*|.*sh",
]

def _is_sensitive_path(filepath: str) -> bool:
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, filepath, re.IGNORECASE):
            return True
    return False


def _is_dangerous_command(command: str) -> tuple:
    cmd_lower = command.strip().lower()
    for dc in DANGEROUS_COMMANDS:
        if cmd_lower.startswith(dc.lower()):
            return True, dc
    for di in DANGEROUS_INSTALL:
        if cmd_lower.startswith(di.lower()):
            return True, di
    return False, ""


def _has_config() -> bool:
    """检查是否有 settings.local.json 或 harness.yaml 中的用户配置"""
    config_paths = [
        Path.cwd() / ".claude" / "settings.local.json",
        Path.cwd() / ".claude" / "harness.yaml",
    ]
    for p in config_paths:
        if p.exists():
            return True
    return False


try:
    from pathlib import Path
except ImportError:
    Path = None

def main():
    """Main hook entry point"""
    # ─── 读取 stdin ───
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True, "message": "PreActionGate: no input"}))
        return 0

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True, "message": "PreActionGate: unparseable input"}))
        return 0

    # ─── 提取命令和文件路径 ───
    command = payload.get("command", "")
    file_path = payload.get("filePath", "") or payload.get("path", "")

    # ─── 判断敏感路径 ───
    if file_path and _is_sensitive_path(file_path):
        msg = f"PreActionGate: BLOCKED — sensitive path: {file_path}"
        print(json.dumps({"continue": False, "message": msg}))
        sys.stderr.write(msg + "\n")
        return 0

    # ─── 判断危险命令 ───
    if command:
        is_danger, matched = _is_dangerous_command(command)
        if is_danger:
            if _has_config():
                # ASK_USER
                msg = f"PreActionGate: ASK_USER — dangerous command: {matched}"
                print(json.dumps({"continue": True, "message": msg}))
            else:
                msg = f"PreActionGate: BLOCKED — dangerous command: {matched}"
                print(json.dumps({"continue": False, "message": msg}))
                sys.stderr.write(msg + "\n")
            return 0

        # ─── 普通命令 ALLOW ───
        print(json.dumps({"continue": True, "message": "PreActionGate: ALLOW"}))
        return 0

    # ─── 默认 ALLOW ───
    print(json.dumps({"continue": True, "message": "PreActionGate: ALLOW (no action)"}))
    return 0


if __name__ == "__main__":
    main()
