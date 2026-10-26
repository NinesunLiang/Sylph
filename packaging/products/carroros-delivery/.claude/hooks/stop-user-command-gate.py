#!/usr/bin/env python3
"""stop-user-command-gate.py — 用户命令门禁（Stop hook）。

人类裁决 2026-10-24（第三个感叹号）：
  AI 永远不得把「多行命令」或「会折行的长命令」交给用户去终端执行。
  唯一允许的用户命令形态：单行 `bash .omc/scripts/<name>.sh`。

为什么不是提示，而是门禁：
  规则文件（terminal-safety Rule 6）只是提醒，已经连续失效 3 次。
  本 hook 在每轮结束前扫描最终回复，违规即打回重写。

机制（官方 Stop hook，来源 code.claude.com/docs/en/hooks）：
  - 输入 `last_assistant_message`：官方字段，不解析易变的 transcript
  - 输出 `{"decision":"block","reason":"..."}`：本轮不结束，模型必须重写
  - `stop_hook_active=true`：不再拦（官方循环保护）
  - 任何异常 fail-open（exit 0），绝不阻断会话
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(os.environ.get("CARROROS_AUDIT_DIR", str(ROOT / ".omc" / "state" / "audit")))
ENV_SWITCH = "CARROROS_STOP_CMD_GATE"

# 终端折行阈值（显示宽度，中文按 2 列计算）。
# 用户终端 prompt 约 57 列 + "! "，留给命令的空间不到 60 列。
MAX_WIDTH = 60
# 唯一合规形态自身也设上限，防止脚本名异常长。
ALLOWED_MAX_WIDTH = 80

SHELL_INFOS = {"", "bash", "sh", "zsh", "fish", "shell", "console", "shell-session", "terminal"}

# 唯一放行的命令形态：单行 bash .omc/scripts/<name>.sh|py
ALLOWED_RE = re.compile(r"^bash \.omc/scripts/[\w./-]+\.(?:sh|py)(?:\s+\S+)*$")

# 绝对路径：必然过长，且用户已在仓库根目录时毫无必要
ABS_PATH_RE = re.compile(r"(?<![\w.-])/(?:Users|home|private|var|tmp|opt|usr|etc|Volumes)/")

_FENCE_RE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_INLINE_RE = re.compile(r"`([^`\n]+)`")

_COMMANDS = {
    "bash", "sh", "zsh", "fish", "python", "python3", "pip", "pip3", "uv",
    "node", "npm", "npx", "pnpm", "yarn", "deno", "bun",
    "git", "gh", "mv", "cp", "rm", "rmdir", "mkdir", "touch", "ln", "chmod",
    "chown", "ls", "cd", "pwd", "cat", "head", "tail", "sed", "awk", "grep",
    "find", "xargs", "tar", "zip", "unzip", "curl", "wget", "ssh", "scp",
    "rsync", "docker", "make", "brew", "sudo", "launchctl", "systemctl",
    "osascript", "defaults", "open", "code", "vim", "nano", "echo", "export",
    "source", "env", "kill", "pkill", "psql", "mysql", "redis-cli", "cargo",
    "rustc", "go", "java", "mvn", "gradle", "terraform", "kubectl", "helm",
    "pytest", "ruff", "mypy", "which", "type", "alias", "chmod", "spctl",
}

_PREFIXES = ("$ ", "! ", "% ", "> ")


def display_width(text: str) -> int:
    """终端显示宽度：CJK 宽字符/全角按 2 列。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def _strip_prefix(line: str) -> str:
    s = line.strip()
    for prefix in _PREFIXES:
        if s.startswith(prefix):
            return s[len(prefix):].strip()
    return s


def looks_like_command(line: str) -> bool:
    """保守判定：只把明确像 shell 命令的行纳入检查，避免误伤说明文字。"""
    s = line.strip()
    if not s:
        return False
    if s.startswith(("! ", "$ ", "./", "../", "/")):
        return True
    first = s.split()[0].strip("'\"")
    if first in _COMMANDS:
        return True
    if first.endswith((".sh", ".py")):
        return True
    return False


def _command_violation(line: str) -> dict | None:
    """单条命令行的判定。合规返回 None。"""
    if ALLOWED_RE.match(line) and display_width(line) <= ALLOWED_MAX_WIDTH:
        return None
    if ABS_PATH_RE.search(line):
        return {"kind": "absolute_path", "line": line}
    if display_width(line) > MAX_WIDTH:
        return {"kind": "too_long", "line": line}
    return None


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for item in items:
        key = (item["kind"], item["line"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def find_violations(text: str) -> list[dict]:
    """扫描最终回复，返回违规命令列表（空列表 = 合规）。纯函数，便于测试。"""
    if not text:
        return []

    violations: list[dict] = []

    # 1) shell 代码块
    for match in _FENCE_RE.finditer(text):
        info = (match.group(1) or "").strip().lower()
        if info not in SHELL_INFOS:
            continue
        body = match.group(2)
        lines = [
            _strip_prefix(raw) for raw in body.splitlines()
            if raw.strip() and not raw.strip().startswith("#")
        ]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        # 空语言块：只有首行像命令时才当作命令块（避免误伤目录树/输出示例）
        if info == "" and not looks_like_command(lines[0]):
            continue
        if len(lines) >= 2:
            violations.append({"kind": "multi_line", "line": lines[0]})
            continue
        found = _command_violation(lines[0])
        if found:
            violations.append(found)

    # 2) 行内代码（排除代码块后）
    outside = _FENCE_RE.sub("", text)
    for match in _INLINE_RE.finditer(outside):
        span = _strip_prefix(match.group(1))
        if not looks_like_command(span):
            continue
        found = _command_violation(span)
        if found:
            violations.append(found)

    # 3) 裸的 "! 命令" 行（用户粘贴执行的形态）
    for raw in outside.splitlines():
        s = raw.strip()
        if not s.startswith("! "):
            continue
        found = _command_violation(s[2:].strip())
        if found:
            violations.append(found)

    return _dedupe(violations)


def _audit(violations: list[dict]) -> None:
    try:
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        event = {
            "event_type": "stop_user_command_blocked",
            "actor": "hook:stop-user-command-gate",
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "kinds": sorted({v["kind"] for v in violations}),
            "samples": [v["line"][:120] for v in violations[:3]],
        }
        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _reason(violations: list[dict]) -> str:
    samples = "\n".join(f"  - [{v['kind']}] {v['line'][:100]}" for v in violations[:3])
    return (
        "⛔ CarrorOS 用户命令门禁：本轮回复把「需要人类手动执行」的命令交给了用户，"
        "属于多行块 / 会折行的长命令 / 绝对路径。\n"
        f"命中：\n{samples}\n\n"
        "唯一允许的形态是单行：bash .omc/scripts/<name>.sh\n"
        "正确做法：用 Write 把操作写成 .omc/scripts/ 下的脚本（首行后立刻 set -euo pipefail），"
        "然后重写本轮回复，只保留那一行调用。不要给多行命令，不要给绝对路径。"
    )


def main() -> int:
    if os.environ.get(ENV_SWITCH, "1") == "0":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    # 官方循环保护：已经因 Stop hook 续写过一次，不再拦。
    if payload.get("stop_hook_active"):
        return 0
    text = str(payload.get("last_assistant_message") or "")
    violations = find_violations(text)
    if not violations:
        return 0
    _audit(violations)
    print(json.dumps({"decision": "block", "reason": _reason(violations)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # fail-open：门禁自身故障绝不阻断会话
        sys.exit(0)
