#!/usr/bin/env python3
"""gov_approve.py — 人类审批票签发工具（P0 治理加固）。

治理文件（.claude/hooks、.claude/scripts、AGENTS.md、kernel.md、index.md、
harness.yaml、CLAUDE.md、rules/ 等）默认拒绝 AI 写入。
人类在真实终端签发一张有期限的审批票后，AI 才能在票面范围内修改。

安全边界：
  - 必须在真实终端运行：拒绝 CLAUDECODE / AI_AGENT 环境，且要求 stdin/stdout 是 TTY。
    Claude Code 里的 `!` 命令没有 TTY，会同样被拒绝。
  - 票绑定：文件路径 + 当前内容 sha256（首次使用时校验一次）+ TTL（最长 24h）。
  - 票文件本身受冻结域保护，AI 无法自行写入。

用法：
  bash .omc/scripts/sign_p0_ticket.sh          # 项目内置签票入口
  python3 .claude/scripts/gov_approve.py --files a.py,b.py --reason "..." [--ttl-min 30]
  python3 .claude/scripts/gov_approve.py --new .claude/scripts/new_tool.py --reason "..."
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICKET = ROOT / ".omc" / "state" / "governance-approval.json"
MAX_TTL_MIN = 24 * 60


def _rel(p: str) -> str:
    path = Path(p.strip())
    if not path.is_absolute():
        path = ROOT / path
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sha(p: str) -> str:
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    except OSError:
        return ""


def _write(data: dict) -> None:
    TICKET.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".gov-ticket-", dir=str(TICKET.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, TICKET)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    in_agent = bool(os.environ.get("CLAUDECODE") or os.environ.get("AI_AGENT"))
    if in_agent or not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("ERROR: 审批票只能由人类在真实终端签发。\n"
              "       Claude Code 内的 ! 命令没有 TTY，请打开「终端」App 再运行。",
              file=sys.stderr)
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default="", help="逗号分隔的已存在文件")
    ap.add_argument("--new", default="", help="逗号分隔的待创建文件")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--ttl-min", type=int, default=30)
    args = ap.parse_args()

    ttl = max(1, min(args.ttl_min, MAX_TTL_MIN))
    files: dict[str, dict] = {}
    for raw in [x for x in args.files.split(",") if x.strip()]:
        key = _rel(raw)
        digest = _sha(key)
        if not digest:
            print(f"ERROR: 文件不存在或不可读：{key}", file=sys.stderr)
            return 2
        files[key] = {"sha256": digest, "used": False}
    for raw in [x for x in args.new.split(",") if x.strip()]:
        files[_rel(raw)] = {"sha256": "NEW", "used": True}

    if not files:
        print("ERROR: 没有指定任何文件", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    print("\n=== 治理文件变更审批 ===")
    print(f"审批人: {getpass.getuser()}")
    print(f"理由:   {args.reason}")
    print(f"有效期: {ttl} 分钟（最长 {MAX_TTL_MIN} 分钟）")
    for key, meta in files.items():
        kind = "新建" if meta["sha256"] == "NEW" else meta["sha256"][:16] + "..."
        print(f"  - {key}  [{kind}]")
    print("\n这些文件将被 AI 修改。确认无误请输入 APPROVE（其他任何输入=取消）：")
    try:
        answer = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer != "APPROVE":
        print("已取消。未写入审批票。")
        return 1

    _write({
        "version": 1,
        "approved_by": getpass.getuser(),
        "reason": args.reason,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=ttl)).isoformat(),
        "files": files,
    })
    print(f"\n✅ 审批票已写入：{TICKET}")
    print(f"   有效期至 {now + timedelta(minutes=ttl):%Y-%m-%d %H:%M:%S} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
