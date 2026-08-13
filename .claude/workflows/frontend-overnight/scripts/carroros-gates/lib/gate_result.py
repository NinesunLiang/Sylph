#!/usr/bin/env python3
"""gate-result 信封库（FINAL.md v3.1 §4.4 / GPT#4）

写入协议：临时文件 → schema 校验 → fsync → 原子 rename。
reducer：每 gate 取最新合法、非 SUPERSEDED 结果；缺权威字段 / exit 与 status 冲突 → fail-closed。
SUPERSEDED 用 sidecar 标记（append-only，不改写历史信封）。

CLI（供 shell 门禁脚本调用）：
  gate_result.py write    --out-dir DIR --gate-id C4 --status PASS \
                          --manifest-sha256 S --code-sha S --control-plane-digest S \
                          --started-at ISO --process-exit-code 0 [--evidence JSON_ARRAY]
  gate_result.py reduce   --results-dir DIR [--format json|text]
  gate_result.py supersede --results-dir DIR --gate-run-id ID --reason "..."
  gate_result.py validate --file PATH
退出码：0 成功；2 fail-closed（缺字段/冲突/损坏）；1 其他错误。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = [
    "gate_run_id", "gate_id", "status",
    "manifest_sha256", "code_sha", "control_plane_digest",
    "started_at", "finished_at", "process_exit_code", "evidence",
    "producer",
]
STATUS_ENUM = {"PASS", "FAIL", "ERROR", "SUPERSEDED"}
WRITE_STATUS_ENUM = {"PASS", "FAIL", "ERROR"}  # SUPERSEDED 只能由 sidecar 标记产生
GATE_ID_ENUM = {"C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8a", "C8b"}
# 合法生产者（Grok §17a P0-3：信封必须来自门禁脚本链；finalize 按 gate_id→producer 映射校验）
PRODUCER_ENUM = {
    "preflight.sh", "scope-check.sh", "run-gate.sh", "c7-check.sh",
    "evidence-check.sh", "finalize-page.sh", "abstraction-check.sh",
    "preflight.py", "scope_check.py", "run_gate.py", "c7_check.py",
    "evidence_check.py", "finalize_page.py", "abstraction_check.py",
}


class FailClosed(Exception):
    """权威字段缺失/冲突/文件损坏：reducer 必须失败，不得放行。"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate(env: object, source: str = "<memory>") -> dict:
    """缺任一权威字段 / 枚举越界 / exit 与 status 冲突 → FailClosed。"""
    if not isinstance(env, dict):
        raise FailClosed(f"{source}: envelope is not an object")
    missing = [f for f in REQUIRED_FIELDS if f not in env]
    if missing:
        raise FailClosed(f"{source}: missing authoritative fields: {missing}")
    if env["gate_id"] not in GATE_ID_ENUM:
        raise FailClosed(f"{source}: unknown gate_id {env['gate_id']!r}")
    if env["status"] not in STATUS_ENUM:
        raise FailClosed(f"{source}: unknown status {env['status']!r}")
    if not isinstance(env["evidence"], list):
        raise FailClosed(f"{source}: evidence must be a list")
    if not isinstance(env["process_exit_code"], int):
        raise FailClosed(f"{source}: process_exit_code must be int")
    # exit code 与 status 一致性（R4 攻击集：结果 PASS 但 exit 非 0 / exit 0 但结果 FAIL）
    if env["status"] == "PASS" and env["process_exit_code"] != 0:
        raise FailClosed(f"{source}: status PASS but process_exit_code={env['process_exit_code']}")
    if env["status"] in ("FAIL", "ERROR") and env["process_exit_code"] == 0:
        raise FailClosed(f"{source}: status {env['status']} but process_exit_code=0")
    for f in ("manifest_sha256", "code_sha", "control_plane_digest"):
        if not isinstance(env[f], str) or not env[f]:
            raise FailClosed(f"{source}: {f} must be a non-empty string")
    if env["producer"] not in PRODUCER_ENUM:
        raise FailClosed(f"{source}: producer must be one of {sorted(PRODUCER_ENUM)}, got {env['producer']!r}")
    return env


def write_result(
    out_dir: str | Path,
    gate_id: str,
    status: str,
    manifest_sha256: str,
    code_sha: str,
    control_plane_digest: str,
    started_at: str,
    process_exit_code: int,
    evidence: list | None = None,
    *,
    producer: str,
    argv_digest: str | None = None,
) -> Path:
    """临时文件 → schema 校验 → fsync → 原子 rename。"""
    if status not in WRITE_STATUS_ENUM:
        raise FailClosed(f"write: status must be one of {sorted(WRITE_STATUS_ENUM)}, got {status!r}")
    env = {
        "gate_run_id": str(uuid.uuid4()),
        "gate_id": gate_id,
        "status": status,
        "manifest_sha256": manifest_sha256,
        "code_sha": code_sha,
        "control_plane_digest": control_plane_digest,
        "started_at": started_at,
        "finished_at": _utcnow(),
        "process_exit_code": process_exit_code,
        "evidence": evidence or [],
        "producer": producer,
    }
    if argv_digest:
        env["argv_digest"] = argv_digest
    validate(env)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / f".tmp-{env['gate_run_id']}.json"
    final = out / f"{gate_id}-{env['gate_run_id']}.json"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, final)  # POSIX 原子
    return final


def _superseded_ids(results_dir: Path) -> set[str]:
    ids = set()
    for p in results_dir.glob("*.superseded.json"):
        ids.add(p.name[: -len(".superseded.json")])
    return ids


def load_all(results_dir: str | Path) -> list[dict]:
    """读取全部信封；损坏文件 / 缺字段 → FailClosed（不得跳过）。"""
    rd = Path(results_dir)
    envs: list[dict] = []
    if not rd.is_dir():
        return envs
    for p in sorted(rd.glob(".tmp-*.json")):
        raise FailClosed(f"{p}: leftover temp file (crash mid-write?) — treat as suspect")
    for p in sorted(rd.glob("C*-*.json")):
        try:
            env = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise FailClosed(f"{p}: corrupt result file: {e}")
        validate(env, source=str(p))
        env["_path"] = str(p)
        envs.append(env)
    return envs


def reduce_latest(results_dir: str | Path) -> dict[str, dict]:
    """每 gate_id 取 finished_at 最新的合法、非 SUPERSEDED 信封。"""
    rd = Path(results_dir)
    superseded = _superseded_ids(rd)
    latest: dict[str, dict] = {}
    for e in load_all(rd):
        if e["gate_run_id"] in superseded:
            continue
        cur = latest.get(e["gate_id"])
        if cur is None or e["finished_at"] > cur["finished_at"]:
            latest[e["gate_id"]] = e
    return latest


def mark_superseded(results_dir: str | Path, gate_run_id: str, reason: str) -> Path:
    """append-only 标记：写 sidecar，不改写原信封。"""
    rd = Path(results_dir)
    target = None
    for e in load_all(rd):
        if e["gate_run_id"] == gate_run_id:
            target = e
            break
    if target is None:
        raise FailClosed(f"supersede: gate_run_id {gate_run_id} not found")
    sidecar = rd / f"{gate_run_id}.superseded.json"
    payload = {"gate_run_id": gate_run_id, "reason": reason, "marked_at": _utcnow()}
    tmp = rd / f".tmp-{gate_run_id}.superseded.json"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, sidecar)
    return sidecar


def main() -> int:
    ap = argparse.ArgumentParser(description="gate-result envelope lib (FINAL.md v3.1 §4.4)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write")
    w.add_argument("--out-dir", required=True)
    w.add_argument("--gate-id", required=True)
    w.add_argument("--status", required=True)
    w.add_argument("--manifest-sha256", required=True)
    w.add_argument("--code-sha256", dest="code_sha", required=True)
    w.add_argument("--control-plane-digest", required=True)
    w.add_argument("--started-at", required=True)
    w.add_argument("--process-exit-code", type=int, required=True)
    w.add_argument("--evidence", default="[]", help="JSON array of evidence pointers")
    w.add_argument("--producer", required=True, help="调用方门禁脚本名（PRODUCER_ENUM）")
    w.add_argument("--argv-digest", default=None, help="run-gate 被包装命令的 sha256")

    r = sub.add_parser("reduce")
    r.add_argument("--results-dir", required=True)
    r.add_argument("--format", choices=["json", "text"], default="json")

    s = sub.add_parser("supersede")
    s.add_argument("--results-dir", required=True)
    s.add_argument("--gate-run-id", required=True)
    s.add_argument("--reason", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--file", required=True)

    args = ap.parse_args()
    try:
        if args.cmd == "write":
            evidence = json.loads(args.evidence)
            if not isinstance(evidence, list):
                raise FailClosed("--evidence must be a JSON array")
            p = write_result(
                args.out_dir, args.gate_id, args.status,
                args.manifest_sha256, args.code_sha, args.control_plane_digest,
                args.started_at, args.process_exit_code, evidence,
                producer=args.producer, argv_digest=args.argv_digest,
            )
            print(p)
            return 0
        if args.cmd == "reduce":
            latest = reduce_latest(args.results_dir)
            if args.format == "json":
                print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "_path"} for k, v in latest.items()}, indent=2, ensure_ascii=False))
            else:
                for gid in sorted(latest):
                    e = latest[gid]
                    print(f"{gid}: {e['status']} (run {e['gate_run_id']}, exit {e['process_exit_code']})")
            return 0
        if args.cmd == "supersede":
            print(mark_superseded(args.results_dir, args.gate_run_id, args.reason))
            return 0
        if args.cmd == "validate":
            env = json.loads(Path(args.file).read_text(encoding="utf-8"))
            validate(env, source=args.file)
            print("OK")
            return 0
    except FailClosed as e:
        print(f"FAIL-CLOSED: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
