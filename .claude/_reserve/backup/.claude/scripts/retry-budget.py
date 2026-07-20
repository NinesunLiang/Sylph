#!/usr/bin/env python3
"""
retry-budget.py — C9 错误修复预算追踪
Python 移植版，完全等价 retry-budget.sh v1.0

Reads error-dna.json and flags signatures exceeding retry budget.
Prevents infinite retry loops by blocking before 3rd failed attempt.

Commands:
  status   — Print retry budget status for all active errors
  check    — Exit 2 if any error exceeds budget (for hooks)
  record   — Increment retry count for a given error signature
  clear    — Clear/reset retry count for a given error signature

C2 语义去重: record/clear 支持命令归一化（去除时间戳/UUID/临时路径等），
相似命令映射到同一签名。使用 --normalize 或 -n 开关激活。

用法: python3 retry-budget.py {status|check|record <sig> [label|--normalize <label>]|clear <sig> [--normalize]|norm <raw_cmd>}
"""

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
DNA_FILE = STATE_DIR / "error-dna.json"
BUDGET_FILE = STATE_DIR / "retry-budget.json"

# Max retries from harness cache
MAX_RETRIES = 3
RETRY_CACHE = STATE_DIR / ".harness-cache"
if RETRY_CACHE.exists():
    try:
        for line in RETRY_CACHE.read_text(encoding="utf-8").splitlines():
            if line.startswith("retry_budget.max_retries="):
                val = line.split("=", 1)[1].strip()
                if val:
                    MAX_RETRIES = int(val)
                break
    except (ValueError, Exception):
        pass


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _init_budget():
    if not BUDGET_FILE.exists():
        _ensure_dir(BUDGET_FILE.parent)
        BUDGET_FILE.write_text('{"signatures":{}}', encoding="utf-8")


def _read_budget() -> dict:
    if BUDGET_FILE.exists():
        try:
            return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"signatures": {}}
    return {"signatures": {}}


def _write_budget(data: dict):
    _ensure_dir(BUDGET_FILE.parent)
    BUDGET_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── C2: 命令归一化函数 ───
def normalize_command(raw: str) -> str:
    """Remove timestamps, UUIDs, temp paths, session IDs, version numbers."""
    cmd = raw
    # 1. Timestamps: YYYYMMDD_HHMMSS / YYYY-MM-DDTHH:MM:SS / epoch seconds
    cmd = re.sub(r'\b\d{8}[-_]\d{6}\b', '<TS>', cmd)
    cmd = re.sub(r'\b\d{4}[-_]\d{2}[-_]\d{2}[T ]\d{2}[-_:]\d{2}[-_:]\d{2}\b', '<TS>', cmd)
    cmd = re.sub(r'\b1[3-9]\d{9}\b', '<TS>', cmd)
    # 2. UUID/GUID
    cmd = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '<UUID>', cmd)
    cmd = re.sub(r'\b[0-9a-fA-F]{32}\b', '<UUID>', cmd)
    # 3. Temp paths
    cmd = re.sub(r'/tmp/[^\s\"\'\\]+', '<TMP>', cmd)
    cmd = re.sub(r'/private/tmp/[^\s\"\'\\]+', '<TMP>', cmd)
    cmd = re.sub(r'/var/folders/[^\s\"\'\\]+', '<TMP>', cmd)
    # 4. Flag stripping
    cmd = re.sub(r'\s+(--verbose|-v|--debug|-d|--quiet|-q)(?:\s|$)', ' ', cmd)
    # 5. Pipe display commands
    cmd = re.sub(r'\s*\|\s*(head|tail|sort|uniq|wc|grep -v|cat -n)\s*.*$', '', cmd)
    # 6. Collapse spaces
    cmd = re.sub(r'\s+', ' ', cmd).strip()
    return cmd


def compute_signature(raw: str, do_normalize: bool = False) -> str:
    """Generate a normalized MD5 signature."""
    if do_normalize:
        normalized = normalize_command(raw)
    else:
        normalized = raw
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


# ─── Commands ───
def cmd_status():
    data = _read_budget()
    sigs = data.get("signatures", {})
    if not sigs:
        print("(no retry data)")
        return
    for sig, entry in sorted(sigs.items()):
        count = entry.get("retry_count", 0)
        label = entry.get("label", sig)[:80]
        blocked = "BLOCKED" if count >= MAX_RETRIES else "ok"
        print(f"{sig[:40]} | {count}/{MAX_RETRIES} | {blocked} | {label}")


def cmd_check():
    data = _read_budget()
    sigs = data.get("signatures", {})
    exceeded = [(k, v.get("retry_count", 0)) for k, v in sigs.items() if v.get("retry_count", 0) >= MAX_RETRIES]
    if exceeded:
        for sig, cnt in exceeded:
            label = sigs[sig].get("label", sig)[:80]
            print(f"{sig[:40]} ({cnt} retries): {label}")
        print(f"[Retry Budget] BLOCKED — 以下错误超过 {MAX_RETRIES} 次重试上限:", file=sys.stderr)
        for sig, cnt in exceeded:
            label = sigs[sig].get("label", sig)[:80]
            print(f"  {sig[:40]} ({cnt} retries): {label}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


def cmd_record(sig: str, label: str = "unknown"):
    _init_budget()
    data = _read_budget()
    sigs = data.get("signatures", {})

    # Handle --normalize prefix in label
    sig_key = sig
    if label.startswith("--normalize"):
        raw_cmd = sig
        sig_key = compute_signature(raw_cmd, do_normalize=True)
        label = label.replace("--normalize", "", 1).strip()
        if not label:
            label = f"normalized: {raw_cmd[:60]}"

    if sig_key not in sigs:
        sigs[sig_key] = {"retry_count": 0, "label": label, "first_seen": int(time.time())}

    entry = sigs[sig_key]
    entry["retry_count"] = entry.get("retry_count", 0) + 1
    entry["last_retry"] = int(time.time())
    entry["label"] = label

    data["signatures"] = sigs
    _write_budget(data)

    cnt = entry["retry_count"]
    print(f"[Retry Budget] {sig_key[:40]}: retry {cnt}/{MAX_RETRIES}")
    if cnt >= MAX_RETRIES:
        print(f"[Retry Budget] BLOCKED — 已达 {cnt} 次上限，需人工干预")


def cmd_clear(sig: str, do_normalize: bool = False):
    sig_key = compute_signature(sig, do_normalize=do_normalize) if do_normalize else sig
    if not BUDGET_FILE.exists():
        print("[Retry Budget] 无预算数据")
        return
    data = _read_budget()
    sigs = data.get("signatures", {})
    if sig_key in sigs:
        del sigs[sig_key]
        print(f"[Retry Budget] cleared: {sig_key[:40]}")
    else:
        print(f"[Retry Budget] not found: {sig_key[:40]}")
    data["signatures"] = sigs
    _write_budget(data)


def cmd_norm(raw_cmd: str):
    print(normalize_command(raw_cmd))


def print_usage():
    print("Usage: retry-budget.py {status|check|record <sig> [label|--normalize <label>]|clear <sig> [--normalize]|norm <raw_cmd>}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        cmd_status()
    elif cmd == "check":
        cmd_check()
    elif cmd == "record":
        if len(args) < 2:
            print("record requires: <sig> [label]", file=sys.stderr)
            sys.exit(1)
        sig = args[1]
        label = " ".join(args[2:]) if len(args) > 2 else "unknown"
        cmd_record(sig, label)
    elif cmd == "clear":
        if len(args) < 2:
            print("clear requires: <sig> [--normalize]", file=sys.stderr)
            sys.exit(1)
        sig = args[1]
        do_norm = "--normalize" in args[2:]
        cmd_clear(sig, do_norm)
    elif cmd == "norm":
        if len(args) < 2:
            print("Usage: retry-budget.sh norm <raw_cmd>", file=sys.stderr)
            sys.exit(1)
        cmd_norm(args[1])
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
