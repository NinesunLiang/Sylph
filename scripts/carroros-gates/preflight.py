#!/usr/bin/env python3
"""
preflight.py — 起飞前总门禁 (v6.0, .sh → .py 迁移) = C0
lx-goal on 之前必须全绿。任何一项不过 → NO-GO（fail-closed）。
退出：0=GO 1=NO-GO 2=ERROR 3=FAILED_INVARIANT
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
GATES_DIR = SCRIPT_DIR
sys.path.insert(0, str(GATES_DIR))
from lib import common

common.parse_args()
if not common.NIGHT_DIR:
    print("ERROR: 需要 --night-dir", file=sys.stderr)
    sys.exit(2)
if not common.TARGET_REPO:
    print("ERROR: 需要 --target-repo", file=sys.stderr)
    sys.exit(2)

CARROS_BASE = str(common.CARROS_BASE)

fails = []


def note(msg):
    print(f"  ✗ {msg}")
    fails.append(msg)


def ok(msg):
    print(f"  ✓ {msg}")


print("== preflight ==")

# 1. signoff 字节哈希
signoff_path = common.MANIFEST.replace(".yaml", ".signoff.yaml") if common.MANIFEST.endswith(".yaml") else common.MANIFEST + ".signoff.yaml"
if not Path(signoff_path).is_file():
    note(f"signoff 缺失: {signoff_path}")
else:
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", signoff_path, "--get", "manifest_sha256"],
                       capture_output=True, text=True)
    recorded = r.stdout.strip() if r.returncode == 0 else ""
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", signoff_path, "--get", "decision"],
                       capture_output=True, text=True)
    decision = r.stdout.strip() if r.returncode == 0 else ""
    actual = common.sha256_file(common.MANIFEST)
    if not recorded or recorded != actual:
        note(f"signoff 哈希不匹配（manifest 签后被改动？） recorded={recorded[:12]} actual={actual[:12]}")
    elif decision not in ("GO", "CONDITIONAL_GO"):
        note(f"signoff decision={decision}（需要 GO|CONDITIONAL_GO）")
    else:
        ok(f"signoff 字节哈希匹配，decision={decision}")

# 2. control_plane_lock 自验
try:
    common.verify_control_plane_lock()
    ok("control_plane_lock 自验通过")
except SystemExit:
    note("control_plane_lock 自验失败（控制面被改动）")

# 3. first_night_selection
r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST, "--pages"],
                   capture_output=True, text=True)
pages_count = len([l for l in r.stdout.splitlines() if l.strip()])
if pages_count == 1:
    ok("pages==1")
else:
    note(f"pages={pages_count}（首夜硬规则 ==1）")

for f in ("input_completeness", "complexity", "prototype_accessible",
          "acceptance_contract_complete", "happy_path_testable"):
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                        "--get", f"first_night_selection.{f}"],
                       capture_output=True, text=True)
    v = r.stdout.strip() if r.returncode == 0 else "MISSING"
    if f == "input_completeness":
        (ok if v == "complete" else note)(f"selection.{f}={v}（需 complete）")
    elif f == "complexity":
        (ok if v == "V0_or_V1" else note)(f"selection.{f}={v}（需 V0_or_V1）")
    else:
        (ok if v == "true" else note)(f"selection.{f}={v}（需 true）")

# 4. assertion 词表封闭
CATALOG = GATES_DIR / "assertion-catalog.yaml"
r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                    "--get", "assertion_catalog_version"], capture_output=True, text=True)
cat_ver = r.stdout.strip() if r.returncode == 0 else "MISSING"
try:
    cat_data = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    file_ver = str(cat_data.get("version", "")).strip('"')
except Exception:
    file_ver = "MISSING"

if cat_ver == file_ver:
    ok(f"catalog version={cat_ver}")
else:
    note(f"catalog 版本不符 manifest={cat_ver} file={file_ver}")

# assertion ID 词表封闭
try:
    manifest_data = yaml.safe_load(Path(common.MANIFEST).read_text(encoding="utf-8"))
    known = set((cat_data.get("state_assertions") or {})) | set((cat_data.get("overlay_assertions") or {}))
    unknown = []
    for pg in manifest_data.get("pages") or []:
        for state, spec in (pg.get("required_states") or {}).items():
            if isinstance(spec, dict):
                for k in ("assert", "not", "and"):
                    aid = spec.get(k)
                    if aid and aid not in known:
                        unknown.append(f"{pg.get('id')}.{state}.{k}={aid}")
        for ov in (pg.get("overlay_contract") or {}).get("items") or []:
            for aid in ov.get("asserts") or []:
                if aid not in known:
                    unknown.append(f"{pg.get('id')}.overlay.{ov.get('selector', '?')}={aid}")
    if unknown:
        note("assertion 词表校验失败（见下）")
        for u in unknown:
            print(f"    {u}", file=sys.stderr)
    else:
        ok("assertion 词表封闭")
except Exception as e:
    note(f"assertion 词表校验异常: {e}")

# 4b. catalog helper 绑定
helpers_path = Path(common.TARGET_REPO) / "tests" / "e2e" / "helpers" / "assertions.ts"
if not helpers_path.is_file():
    note(f"断言 helper 缺失: {helpers_path}")
else:
    unbound = 0
    helpers_content = helpers_path.read_text(encoding="utf-8", errors="replace")
    for sec in ("state_assertions", "overlay_assertions"):
        for aid in (cat_data.get(sec) or {}):
            if aid not in helpers_content:
                note(f"catalog id 无 helper 绑定: {aid}")
                unbound += 1
    if unbound == 0:
        ok("catalog 全部 id 均有 helper 绑定")

# 5. 模型路由
base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
if base_url != "http://127.0.0.1:9998":
    note(f"ANTHROPIC_BASE_URL={base_url}")
else:
    r = subprocess.run(["curl", "-s", "-m", "3", base_url + "/", "-o", "/dev/null"])
    if r.returncode == 0:
        ok(f"模型代理在线（{base_url}）")
    else:
        note(f"模型代理离线（{base_url} 不可达）")

routing_proof = Path(common.NIGHT_DIR) / "model-routing-proof.yaml"
if routing_proof.is_file():
    ok("model-routing-proof 存在（Phase 0 探针证据）")
else:
    note("model-routing-proof 缺失（Phase 0 需跑 probe-model-routing）")

# 6. 预算非空
for f in ("per_page_calls", "fix_rounds", "page_wall_clock_min"):
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                        "--get", f"budgets.{f}"], capture_output=True, text=True)
    v = r.stdout.strip() if r.returncode == 0 else "MISSING"
    if v not in ("null", "MISSING", "") and v:
        ok(f"budgets.{f}={v}")
    else:
        note(f"budgets.{f} 为空（需 dry-cost 实测 P90×安全系数）")

# 7. S1 残余风险签署
r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                    "--get", "trust_boundary.residual_risk_accepted_by"], capture_output=True, text=True)
signer = r.stdout.strip() if r.returncode == 0 else ""
(ok if signer and signer != "null" else note)(f"trust_boundary 签署人: {signer}" if signer else "trust_boundary 未签署")

r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                    "--get", "trust_boundary.auto_renew"], capture_output=True, text=True)
renew = r.stdout.strip() if r.returncode == 0 else ""
(ok if renew == "false" else note)(f"auto_renew={renew}（必须 false）")

r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                    "--get", "trust_boundary.scope"], capture_output=True, text=True)
scope_v = r.stdout.strip() if r.returncode == 0 else ""
(ok if scope_v == "single_page_single_night" else note)(f"trust_boundary.scope={scope_v}")

# 8. 环境指纹
for f in ("node_version", "pnpm_version", "lockfile_sha256"):
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST,
                        "--get", f"environment_fingerprint.{f}"], capture_output=True, text=True)
    v = r.stdout.strip() if r.returncode == 0 else ""
    (ok if v and v != "null" else note)(f"fingerprint.{f} 为空")

# 9. 五类 smoke
smoke_out = Path(common.NIGHT_DIR) / "smoke-results.yaml"
r = subprocess.run([sys.executable, str(GATES_DIR / "smoke" / "run-all.py"),
                    "--manifest", common.MANIFEST, "--night-dir", common.NIGHT_DIR,
                    "--target-repo", common.TARGET_REPO, "--out", str(smoke_out)])
if r.returncode == 0:
    ok("五类 smoke 全绿")
else:
    note(f"smoke 未全绿（见 {smoke_out}）")

# 9b. 独立复跑
smoke_ind = Path(common.NIGHT_DIR) / "smoke-results-independent.yaml"
if not smoke_ind.is_file():
    note(f"smoke 独立复跑证据缺失: {smoke_ind}")
else:
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", str(smoke_ind),
                        "--get", "runner"], capture_output=True, text=True)
    ind_runner = r.stdout.strip() if r.returncode == 0 else "MISSING"
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", str(smoke_ind),
                        "--get", "all_green"], capture_output=True, text=True)
    ind_green = r.stdout.strip() if r.returncode == 0 else "MISSING"
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", str(smoke_ind),
                        "--get", "tamper_suite_passed"], capture_output=True, text=True)
    ind_tamper = r.stdout.strip() if r.returncode == 0 else "MISSING"
    r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", str(smoke_ind),
                        "--get", "control_plane_digest"], capture_output=True, text=True)
    ind_digest = r.stdout.strip() if r.returncode == 0 else "MISSING"

    try:
        cur_digest = common.verify_control_plane_lock()
    except SystemExit:
        cur_digest = ""

    if ind_runner != "independent":
        note(f"smoke 独立复跑 runner={ind_runner}（需 independent）")
    elif ind_green != "true" or ind_tamper != "true":
        note(f"smoke 独立复跑未全绿（all_green={ind_green} tamper={ind_tamper}）")
    elif not cur_digest or ind_digest != cur_digest:
        note("smoke 独立复跑 digest 过期或不符")
    else:
        ok("smoke 独立复跑 attest 在袋（runner=independent，digest 与当前一致）")

# 10. gh auth
r = subprocess.run(["gh", "auth", "status"], capture_output=True)
if r.returncode == 0:
    ok("gh 已认证（DONE 可建 Draft PR）")
else:
    print("  ! gh 未认证——DONE 页 delivery_status=NOT_ATTEMPTED（不影响 DONE 判定）")

print()
if fails:
    print(f"preflight NO-GO（{len(fails)} 项）:", file=sys.stderr)
    for f in fails:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

# GO
common.preamble()
started_at = common.now_iso()
r = subprocess.run([sys.executable, CARROS_BASE, "manifest-json", "--manifest", common.MANIFEST, "--pages"],
                   capture_output=True, text=True)
page_id = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
common.PAGE_ID = page_id
common.write_result("C0", "PASS", 0, started_at)

# 夜会话标记
state_dir = common.CARROS_ROOT / ".omc" / "state"
state_dir.mkdir(parents=True, exist_ok=True)
(state_dir / "night-session.active").write_text(
    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
print("preflight GO — 夜会话标记已创建，可以 lx-goal on")
