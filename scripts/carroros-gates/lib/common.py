#!/usr/bin/env python3
"""
common.py — 门禁脚本共享库 (v6.0, .sh → .py 迁移)
所有门禁脚本 import 本模块。约定:
  退出码 0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT（信任边界/权威链被碰）
  每个门禁运行必须写 gate-result 信封（lib/gate_result.py），status 与退出码一致。
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 全局状态 ──
GATES_DIR = Path(__file__).resolve().parent.parent
GATES_LIB = GATES_DIR / "lib"
CARROS_ROOT = GATES_DIR.parent.parent
CARROS_BASE = CARROS_ROOT / ".claude" / "scripts" / "carros_base.py"

MANIFEST = ""
PAGE_ID = ""
NIGHT_DIR = ""
TARGET_REPO = os.environ.get("TARGET_REPO", "")
GATES_CP_DIGEST = ""


def parse_args(argv=None):
    """解析共享参数 --manifest --page-id --night-dir --target-repo"""
    global MANIFEST, PAGE_ID, NIGHT_DIR, TARGET_REPO
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--manifest")
    parser.add_argument("--page-id")
    parser.add_argument("--night-dir")
    parser.add_argument("--target-repo")
    args, remaining = parser.parse_known_args(argv)

    MANIFEST = args.manifest or ""
    PAGE_ID = args.page_id or ""
    NIGHT_DIR = args.night_dir or ""
    TARGET_REPO = args.target_repo or TARGET_REPO

    if not MANIFEST:
        print("ERROR: 需要 --manifest", file=sys.stderr)
        sys.exit(2)
    if not Path(MANIFEST).is_file():
        print(f"ERROR: manifest 不存在: {MANIFEST}", file=sys.stderr)
        sys.exit(2)

    MANIFEST = str(Path(MANIFEST).resolve())
    return remaining


def sha256_file(path):
    """文件 sha256 → hex"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_string(s):
    """字符串 sha256 → hex"""
    return hashlib.sha256(s.encode()).hexdigest()


def manifest_sha():
    return sha256_file(MANIFEST)


def code_sha():
    """目标 repo 当前 HEAD"""
    if not TARGET_REPO:
        print("ERROR: TARGET_REPO 未设置", file=sys.stderr)
        sys.exit(2)
    r = subprocess.run(
        ["git", "-C", TARGET_REPO, "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"ERROR: git rev-parse 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


def mget(path, page=None):
    """从 manifest 读取 dotted.path 值；缺失 exit 2"""
    args = [
        sys.executable, str(CARROS_BASE), "manifest-json",
        "--manifest", MANIFEST, "--get", path,
    ]
    if page:
        args += ["--page-id", page]
    else:
        args += ["--page-id", PAGE_ID] if PAGE_ID else []
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: manifest-json --get {path} 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


def verify_control_plane_lock():
    """重算 manifest control_plane_lock.entries 每个文件的 sha256 并比对。
    任何不符/文件缺失 → exit 3 FAILED_INVARIANT。返回 digest。"""
    import yaml

    data = yaml.safe_load(Path(MANIFEST).read_text(encoding="utf-8"))
    lock = (data or {}).get("control_plane_lock") or {}
    entries = lock.get("entries") or []
    if not entries:
        print("FAIL-CLOSED: control_plane_lock.entries 为空", file=sys.stderr)
        sys.exit(3)

    canon = []
    for e in entries:
        path = e.get("path", "")
        expect = e.get("sha256", "")
        if not path or not expect:
            print(f"FAIL-CLOSED: entry 缺 path/sha256: {e}", file=sys.stderr)
            sys.exit(3)

        if path.endswith("#hooks"):
            real = CARROS_ROOT / path[:-len("#hooks")]
            if not real.is_file():
                print(f"FAILED_INVARIANT: 控制面文件缺失: {path}", file=sys.stderr)
                sys.exit(3)
            try:
                data = json.loads(real.read_text(encoding="utf-8"))
                canon_hooks = json.dumps(data.get("hooks", {}), sort_keys=True, separators=(",", ":")).encode()
                h = hashlib.sha256(canon_hooks).hexdigest()
            except Exception as ex:
                print(f"FAILED_INVARIANT: hooks 段解析失败: {ex}", file=sys.stderr)
                sys.exit(3)
        else:
            real = CARROS_ROOT / path
            if not real.is_file():
                print(f"FAILED_INVARIANT: 控制面文件缺失: {path}", file=sys.stderr)
                sys.exit(3)
            h = hashlib.sha256(real.read_bytes()).hexdigest()

        if h != expect:
            print(f"FAILED_INVARIANT: 控制面文件被改动: {path}", file=sys.stderr)
            sys.exit(3)
        canon.append(f"{path}:{h}")

    digest = hashlib.sha256("\n".join(sorted(canon)).encode()).hexdigest()
    return digest


def write_result(gate_id, status, exit_code, started_at, evidence="[]", argv_digest=""):
    """写 gate-result 信封"""
    import inspect
    results_dir_val = results_dir()
    frame = inspect.currentframe().f_back
    caller_path = frame.f_globals.get("__file__", "unknown") if frame else "unknown"
    producer = Path(caller_path).name if caller_path != "unknown" else "unknown"

    extra = ["--producer", producer]
    if argv_digest:
        extra += ["--argv-digest", argv_digest]

    args = [
        sys.executable, str(GATES_LIB / "gate_result.py"), "write",
        "--out-dir", results_dir_val,
        "--gate-id", gate_id,
        "--status", status,
        "--manifest-sha256", manifest_sha(),
        "--code-sha256", code_sha(),
        "--control-plane-digest", GATES_CP_DIGEST,
        "--started-at", started_at,
        "--process-exit-code", str(exit_code),
        "--evidence", evidence,
    ] + extra
    subprocess.run(args, check=True, capture_output=True)


def results_dir():
    if not NIGHT_DIR or not PAGE_ID:
        print("ERROR: 需要 --night-dir/--page-id", file=sys.stderr)
        sys.exit(2)
    r = subprocess.run(
        [sys.executable, str(CARROS_BASE), "gate-results-init",
         "--night-dir", NIGHT_DIR, "--page-id", PAGE_ID],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"ERROR: gate-results-init 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


def preamble():
    """门禁运行前置：自验控制面并设置 GATES_CP_DIGEST"""
    global GATES_CP_DIGEST
    GATES_CP_DIGEST = verify_control_plane_lock()
    return GATES_CP_DIGEST


def now_iso():
    return datetime.now(timezone.utc).isoformat()
