#!/usr/bin/env python3
"""opus-p1-payloads.py — Opus 4.8 §17a 三个新 P1 的当场实测（fresh，非复诵）

R1  O3+O5：manifest 含拼写错 assert id + pages=2 + input_completeness=partial
    → preflight 必须 NO-GO 且报"未知 assertion ID"/"pages=2"/"selection.input_completeness"
R2  P1-10a：缺 smoke-results-independent.yaml → 9b 报"证据缺失"
R3  P1-10b：independent 文件 runner=self → 9b 报"runner=self"
R4  P1-10c：independent 文件 digest 过期 → 9b 报"digest 过期或不符"
R5  P1-10d：independent 文件完全合法 → 9b 打 ✓（attest 在袋）

用法：python3 UI/round5/opus-p1-payloads.py > UI/round5/logs/opus-p1-payloads-$(date +%F).log 2>&1
（从仓库根跑；全程 tempfile，不碰真实夜目录与 .omc/state）
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GATES = ROOT / "scripts" / "carroros-gates"
PREFLIGHT = GATES / "preflight.sh"
CATALOG = GATES / "assertion-catalog.yaml"
TEMPLATE = GATES / "templates" / "night-manifest.template.yaml"

results = []


def check(name, expect, ok, detail=""):
    results.append(bool(ok))
    print(f"  {'✓' if ok else '✗'} {name}: expect={expect}{(' | ' + detail) if detail else ''}")


def sh(*a, **kw):
    r = subprocess.run(list(a), capture_output=True, **kw)
    r.stdout = r.stdout.decode("utf-8", errors="replace")
    r.stderr = r.stderr.decode("utf-8", errors="replace")
    return r


def real_digest(manifest_path: Path) -> str:
    r = sh("bash", "-c",
           f"source '{GATES}/lib/common.sh' && MANIFEST='{manifest_path}' gates_verify_control_plane_lock",
           cwd=ROOT)
    if r.returncode != 0:
        print(f"ERROR: digest 计算失败: {r.stderr}", file=sys.stderr)
        sys.exit(2)
    return r.stdout.strip()


def build_manifest(lock: dict) -> dict:
    m = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    m["control_plane_lock"] = lock
    m["trust_boundary"]["residual_risk_accepted_by"] = "OpusPayloadTest"
    m["inputs"]["prototype"] = {"kind": "static", "path_or_url": "/tmp/proto.png",
                                "status": "present", "login_required": False}
    m["inputs"]["prd"] = {"path": "/tmp/prd.md", "status": "present"}
    m["inputs"]["api_doc"] = {"path": "", "status": "pending"}
    pg = m["pages"][0]
    pg["id"] = "FE-t"
    pg["feature_dir"] = "prd/app/feat-FE-t/"
    pg["files_allowed"] = ["src/pages/t/**"]
    pg["paths"]["spec"] = "tests/e2e/t.spec.ts"
    pg["paths"]["artifacts"] = ".omc/task/x/FE-t/artifacts/"
    m["environment_fingerprint"].update(
        {"node_version": "v22.0.0", "pnpm_version": "10.0.0", "lockfile_sha256": "abc123"})
    m["budgets"].update({"per_page_calls": 10, "fix_rounds": 3, "page_wall_clock_min": 60})
    return m


def make_fixture_repo(d: Path) -> Path:
    """含全部 17 个 catalog id 的 helper 绑定（preflight 4b 要 grep）"""
    repo = d / "target"
    helpers = repo / "tests" / "e2e" / "helpers"
    helpers.mkdir(parents=True)
    cat = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    ids = list((cat.get("state_assertions") or {})) + list((cat.get("overlay_assertions") or {}))
    body = "// fixture: catalog id registry\nexport const registry = {\n"
    body += "".join(f"  '{i}': () => true,\n" for i in ids)
    body += "}\n"
    (helpers / "assertions.ts").write_text(body, encoding="utf-8")
    for cmd in (["git", "init", "-q"], ["git", "add", "."],
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
        r = sh(*cmd, cwd=repo)
        if r.returncode != 0:
            print(f"ERROR: fixture git {' '.join(cmd)}: {r.stderr}", file=sys.stderr)
            sys.exit(2)
    return repo


def write_manifest(nd: Path, m: dict) -> Path:
    mp = nd / "night-manifest.yaml"
    mp.write_text(yaml.safe_dump(m, allow_unicode=True), encoding="utf-8")
    sig = {"manifest_sha256": hashlib.sha256(mp.read_bytes()).hexdigest(),
           "decision": "GO", "signer": "OpusPayloadTest", "signed_at": "2026-07-18T00:00:00Z"}
    (nd / "night-manifest.signoff.yaml").write_text(yaml.safe_dump(sig), encoding="utf-8")
    return mp


def write_independent(nd: Path, runner: str, digest: str):
    (nd / "smoke-results-independent.yaml").write_text(yaml.safe_dump({
        "all_green": True, "tamper_suite_passed": True,
        "runner": runner, "control_plane_digest": digest, "cases": [],
    }), encoding="utf-8")


def run_preflight(mp: Path, nd: Path, repo: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    r = sh("bash", str(PREFLIGHT), "--manifest", str(mp),
           "--night-dir", str(nd), "--target-repo", str(repo), cwd=ROOT, env=env)
    return f"exit={r.returncode}\n{r.stdout}\n{r.stderr}"


# 真实 control_plane_lock（与 preflight 自验同源）
_lock = sh("bash", str(GATES / "gen-control-plane-lock.sh"), cwd=ROOT)
if _lock.returncode != 0:
    print(f"ERROR: gen-control-plane-lock 失败: {_lock.stderr}", file=sys.stderr)
    sys.exit(2)
LOCK = yaml.safe_load(_lock.stdout)

print("== R1: O3 未知 assert id + O5 pages=2/selection 不全 ==")
with tempfile.TemporaryDirectory() as td:
    nd = Path(td) / "night"; nd.mkdir()
    repo = make_fixture_repo(Path(td))
    m = build_manifest(LOCK)
    m["pages"][0]["required_states"]["loading"]["assert"] = "skelton_visible"  # 拼写错
    m["pages"].append({**m["pages"][0], "id": "FE-t2"})                        # pages=2
    m["first_night_selection"]["input_completeness"] = "partial"               # selection 不全
    mp = write_manifest(nd, m)
    write_independent(nd, "independent", real_digest(mp))                      # 隔离 9b 噪音
    out = run_preflight(mp, nd, repo)
    check("R1a O3: 报未知 assertion ID", "含'未知 assertion ID'", "未知 assertion ID" in out)
    check("R1b O3: 点名 skelton_visible", "含拼写错 id", "skelton_visible" in out)
    check("R1c O5: 报 pages=2", "含'pages=2'", "pages=2" in out)
    check("R1d O5: 报 selection.input_completeness=partial", "含该字段",
          "selection.input_completeness=partial" in out)
    check("R1e preflight 整体 NO-GO", "exit=1", out.startswith("exit=1"))

for tag, runner, digest_fn, expect_sub, desc in [
    ("R2 P1-10a 缺独立文件", None, None, "smoke 独立复跑证据缺失", "9b 报证据缺失"),
    ("R3 P1-10b runner=self", "self", "real", "runner=self", "9b 报 runner=self"),
    ("R4 P1-10c digest 过期", "independent", "stale", "digest 过期或不符", "9b 报 digest 不符"),
]:
    print(f"\n== {tag} ==")
    with tempfile.TemporaryDirectory() as td:
        nd = Path(td) / "night"; nd.mkdir()
        repo = make_fixture_repo(Path(td))
        mp = write_manifest(nd, build_manifest(LOCK))
        if runner is not None:
            dg = real_digest(mp) if digest_fn == "real" else "0" * 64
            write_independent(nd, runner, dg)
        out = run_preflight(mp, nd, repo)
        check(desc, f"含'{expect_sub}'", expect_sub in out)
        check(f"{tag} preflight 整体 NO-GO", "exit=1", out.startswith("exit=1"))

print("\n== R5: P1-10d 独立 attest 完全合法 ==")
with tempfile.TemporaryDirectory() as td:
    nd = Path(td) / "night"; nd.mkdir()
    repo = make_fixture_repo(Path(td))
    mp = write_manifest(nd, build_manifest(LOCK))
    write_independent(nd, "independent", real_digest(mp))
    out = run_preflight(mp, nd, repo)
    check("R5a 9b 打勾", "含'✓ smoke 独立复跑 attest 在袋'", "✓ smoke 独立复跑 attest 在袋" in out)
    check("R5b 9b 无任何红项", "不含'独立复跑证据缺失/runner=/digest 过期'",
          all(s not in out for s in ("独立复跑证据缺失", "runner=self", "digest 过期或不符")))

print(f"\nOpus P1 实测: {sum(results)}/{len(results)} 绿")
sys.exit(0 if all(results) else 1)
