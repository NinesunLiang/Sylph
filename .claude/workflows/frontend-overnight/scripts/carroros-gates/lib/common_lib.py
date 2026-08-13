#!/usr/bin/env python3
"""common_lib.py — 门禁脚本共享库（FINAL.md v3.1）

替代 common.sh。所有门禁脚本 import 本文件。约定：
  退出码 0=PASS 1=FAIL 2=ERROR 3=FAILED_INVARIANT
  每个门禁运行必须写 gate-result 信封（lib/gate_result.py），status 与退出码一致。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------- 全局路径 ----------
GATES_DIR = Path(__file__).resolve().parent.parent
GATES_LIB = GATES_DIR / "lib"
CARROS_ROOT = GATES_DIR.parent.parent
CARROS_BASE = CARROS_ROOT / ".claude" / "scripts" / "carros_base.py"

# ---------- 参数 ----------
MANIFEST: Path | None = None
PAGE_ID: str = ""
NIGHT_DIR: Path | None = None
TARGET_REPO: Path | None = None


def gates_parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析门禁通用参数。返回 namespace 同时更新模块级变量。"""
    global MANIFEST, PAGE_ID, NIGHT_DIR, TARGET_REPO
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--page-id", default="")
    ap.add_argument("--night-dir", default="")
    ap.add_argument("--target-repo", default="")
    args = ap.parse_args(argv)

    MANIFEST = Path(args.manifest).resolve()
    if not MANIFEST.is_file():
        print(f"ERROR: manifest 不存在: {MANIFEST}", file=sys.stderr)
        sys.exit(2)
    PAGE_ID = args.page_id
    NIGHT_DIR = Path(args.night_dir).resolve() if args.night_dir else None
    TARGET_REPO = Path(args.target_repo).resolve() if args.target_repo else None
    return args


# ---------- 哈希 ----------
def gates_sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gates_sha256_string(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def gates_manifest_sha() -> str:
    assert MANIFEST is not None, "需要先 gates_parse_args"
    return gates_sha256_file(MANIFEST)


def gates_code_sha() -> str:
    if not TARGET_REPO:
        print("ERROR: TARGET_REPO 未设置", file=sys.stderr)
        sys.exit(2)
    r = subprocess.run(
        ["git", "-C", str(TARGET_REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    return r.stdout.strip()


# ---------- manifest 读取 ----------
def gates_mget(path: str, page: str = "") -> str:
    """读取 manifest 中的值；缺失 exit 2（fail-closed）。"""
    args = ["manifest-json", "--manifest", str(MANIFEST), "--get", path]
    if page:
        args += ["--page-id", page]
    r = subprocess.run(
        ["python3", str(CARROS_BASE)] + args,
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"ERROR: gates_mget({path}) 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


# ---------- control_plane_lock 自验（S1/GPT#3） ----------
def gates_verify_control_plane_lock() -> str:
    """重算 manifest control_plane_lock.entries 每个文件的 sha256 并比对。
    任何不符/文件缺失 → exit 3 FAILED_INVARIANT。
    返回 digest（entries 规范串的 sha256）。
    """
    import yaml  # lazy import

    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
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
            real = CARROS_ROOT / path[: -len("#hooks")]
            if not real.is_file():
                print(f"FAILED_INVARIANT: 控制面文件缺失: {path}", file=sys.stderr)
                sys.exit(3)
            try:
                data_hooks = json.loads(real.read_text(encoding="utf-8"))
                canon_hooks = json.dumps(
                    data_hooks.get("hooks", {}), sort_keys=True, separators=(",", ":")
                ).encode()
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


# ---------- gate-result 信封 ----------
GATES_CP_DIGEST: str = ""


def gates_results_dir() -> Path:
    assert NIGHT_DIR is not None and PAGE_ID, "需要 --night-dir/--page-id"
    r = subprocess.run(
        ["python3", str(CARROS_BASE), "gate-results-init",
         "--night-dir", str(NIGHT_DIR), "--page-id", PAGE_ID],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"ERROR: gate-results-init 失败: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return Path(r.stdout.strip())


def gates_write_result(
    gate_id: str,
    status: str,
    exit_code: int,
    started_at: str,
    evidence: list | None = None,
    argv_digest: str | None = None,
) -> None:
    """写 gate-result 信封。producer 自动取调用方 __main__ 名。"""
    results_dir = gates_results_dir()
    producer = "unknown"
    frame = sys._getframe(1)
    mod = frame.f_globals.get("__name__", "")
    if mod and mod != "__main__":
        producer = mod + ".py"
    else:
        import __main__
        main_file = getattr(__main__, "__file__", None)
        if main_file:
            producer = Path(main_file).name

    sys.path.insert(0, str(GATES_LIB))
    from gate_result import write_result

    write_result(
        out_dir=results_dir,
        gate_id=gate_id,
        status=status,
        manifest_sha256=gates_manifest_sha(),
        code_sha=gates_code_sha(),
        control_plane_digest=GATES_CP_DIGEST,
        started_at=started_at,
        process_exit_code=exit_code,
        evidence=evidence or [],
        producer=producer,
        argv_digest=argv_digest,
    )


def gates_preamble() -> None:
    global GATES_CP_DIGEST
    digest = gates_verify_control_plane_lock()
    if not digest:
        print("FAILED_INVARIANT: control_plane_lock 自验失败", file=sys.stderr)
        sys.exit(3)
    GATES_CP_DIGEST = digest


def gates_now() -> str:
    return datetime.now(timezone.utc).isoformat()
