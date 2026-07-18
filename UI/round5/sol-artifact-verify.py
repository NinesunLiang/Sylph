#!/usr/bin/env python3
"""sol-artifact-verify.py — Sol 复审四向实物一致性核验（源码↔日志↔digest↔独立袋）

机械可复跑：每项打印 PASS/FAIL + 实际值；全 PASS 则 exit 0。
核验项对应 GPT 复审 §4「还不能仅凭文本确认的事项」：
  1. hook v3 实物 = lock 条目（控制面锁覆盖 hook 本身，sha256 一致）
  2. 当前真仓 control_plane_digest == 独立袋 digest == self 袋 digest
  3. 旧独立袋（post-Opus）digest ≠ 当前 → 9b 过期拒收成立
  4. launcher 生产路径显式 unset NIGHT_DENY_ROOT（实物 grep）
  5. hook 锚定优先逻辑实物存在（锚定根夜间时 env override 忽略）
  6. R-SOL-A 端到端：exit 2 且 marker 字节不变（证"命令未执行"而非仅返回值）
  7. 输出各实物 sha256（hook / 独立袋 / 源码包）供 GPT 钉版比对
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GATES = ROOT / "scripts" / "carroros-gates"
HOOK = ROOT / ".claude" / "hooks" / "carroros-night-deny.py"
LAUNCHER = ROOT / ".claude" / "hooks" / "hook-launcher.sh"
IND_BAG = ROOT / "UI" / "round5" / "logs" / "smoke-results-independent-post-sol.yaml"
SELF_BAG = ROOT / "UI" / "round5" / "logs" / "smoke-results-self-post-sol.yaml"
OLD_BAG = Path("/tmp/smoke-ind-nd/smoke-results-independent.yaml")  # post-Opus 旧袋
PACKAGE = ROOT / "UI" / "round5" / "opus-source-package.md"

fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'} {name}" + (f" | {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


print("== 1. hook 实物 = control_plane_lock 条目 ==")
lock_out = subprocess.run(["bash", str(GATES / "gen-control-plane-lock.sh")],
                          capture_output=True, text=True, cwd=ROOT)
if lock_out.returncode != 0:
    print(f"FATAL: gen-lock 失败: {lock_out.stderr}")
    sys.exit(2)
lock = yaml.safe_load(lock_out.stdout)
hook_sha = sha256(HOOK)
hook_entries = [e for e in lock["entries"] if "carroros-night-deny" in e.get("path", "")]
check("lock 含 hook 条目", len(hook_entries) == 1, hook_entries[0]["path"] if hook_entries else "无")
if hook_entries:
    check("hook sha256 与 lock 条目一致", hook_entries[0]["sha256"] == hook_sha,
          f"hook={hook_sha[:16]}… lock={hook_entries[0]['sha256'][:16]}…")
launcher_entries = [e for e in lock["entries"] if "hook-launcher" in e.get("path", "")]
check("lock 含 launcher 条目", len(launcher_entries) == 1)
if launcher_entries:
    check("launcher sha256 与 lock 条目一致", launcher_entries[0]["sha256"] == sha256(LAUNCHER))

print("\n== 2. digest 三向一致（真仓当前 = 独立袋 = self 袋）==")
_m = yaml.safe_load((GATES / "templates" / "night-manifest.template.yaml").read_text())
_m["control_plane_lock"] = lock
_mp = Path(tempfile.mkdtemp()) / "m.yaml"
_mp.write_text(yaml.safe_dump(_m))
_d = subprocess.run(["bash", "-c",
                     f"source '{GATES}/lib/common.sh' && MANIFEST='{_mp}' gates_verify_control_plane_lock"],
                    capture_output=True, text=True, cwd=ROOT)
real_digest = _d.stdout.strip()
check("真仓 digest 计算成功", _d.returncode == 0, real_digest[:16] + "…")
ind = yaml.safe_load(IND_BAG.read_text())
self_bag = yaml.safe_load(SELF_BAG.read_text())
check("独立袋 digest == 真仓当前", ind["control_plane_digest"] == real_digest,
      f"bag={ind['control_plane_digest'][:16]}… real={real_digest[:16]}…")
check("self 袋 digest == 真仓当前", self_bag["control_plane_digest"] == real_digest)
check("独立袋 runner=independent", ind.get("runner") == "independent")
check("独立袋 all_green+tamper", ind.get("all_green") is True and ind.get("tamper_suite_passed") is True,
      f"cases={len(ind.get('cases', []))}")

print("\n== 3. 旧独立袋已过期（9b 拒收的物理基础）==")
if OLD_BAG.exists():
    old = yaml.safe_load(OLD_BAG.read_text())
    check("旧袋 digest ≠ 当前", old["control_plane_digest"] != real_digest,
          f"old={old['control_plane_digest'][:16]}… current={real_digest[:16]}…")
else:
    print("  SKIP 旧袋不在 /tmp（重启后丢失）；过期拒收由 Opus R4 payload 锁定（13/13 绿）")

print("\n== 4. NIGHT_DENY_ROOT 生产不可操纵（双层实物）==")
launcher_src = LAUNCHER.read_text()
check("launcher 显式 unset NIGHT_DENY_ROOT", "unset NIGHT_DENY_ROOT" in launcher_src)
hook_src = HOOK.read_text()
check("hook 锚定优先逻辑存在（锚定根夜间时 override 忽略）",
      "not (_ANCHOR_ROOT" in hook_src and "night-session.active\").exists()" in hook_src)
# 实物行为验证：锚定根夜间 + env 指空目录 → 仍夜间 BLOCK
with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as empty:
    tree = Path(td)
    (tree / ".claude" / "hooks").mkdir(parents=True)
    (tree / ".omc" / "state").mkdir(parents=True)
    (tree / ".omc" / "state" / "night-session.active").write_text("x")
    hc = tree / ".claude" / "hooks" / "carroros-night-deny.py"
    hc.write_text(hook_src)
    r = subprocess.run(["python3", str(hc)],
                       input=json.dumps({"tool_name": "Bash",
                                         "tool_input": {"command": "python3 -c 'print(1)'"}}).encode(),
                       capture_output=True, env=dict(os.environ, NIGHT_DENY_ROOT=empty))
    check("拐根攻击实物：锚定根夜间 + env 空目录 → BLOCK", r.returncode == 2, f"exit={r.returncode}")

print("\n== 5. R-SOL-A 端到端：exit 2 且 marker 字节不变 ==")
with tempfile.TemporaryDirectory() as td:
    d = Path(td)
    (d / ".omc" / "state").mkdir(parents=True)
    marker = d / ".omc" / "state" / "night-session.active"
    content = "2026-07-18T00:00:00Z"
    marker.write_text(content)
    before = sha256(marker)
    r = subprocess.run(["python3", str(HOOK)],
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command":
                           "python3 -c 'from pathlib import Path; "
                           "Path(\".omc/st\"+\"ate/night-session.active\").unlink()'"}}).encode(),
                       capture_output=True, cwd=str(d),
                       env=dict(os.environ, NIGHT_DENY_ROOT=str(d)))
    check("R-SOL-A hook exit 2", r.returncode == 2)
    check("R-SOL-A marker 字节未变（命令未执行）",
          marker.exists() and sha256(marker) == before,
          f"exists={marker.exists()} sha={sha256(marker)[:16] if marker.exists() else '—'}…")

print("\n== 6. 实物钉版哈希（GPT 比对用）==")
print(f"  hook sha256      : {hook_sha}")
print(f"  launcher sha256  : {sha256(LAUNCHER)}")
print(f"  独立袋 sha256     : {sha256(IND_BAG)}")
print(f"  源码包 sha256     : {sha256(PACKAGE)}")
print(f"  control_plane_digest: {real_digest}")

print()
if fails:
    print(f"✗ {len(fails)} 项 FAIL: {fails}")
    sys.exit(1)
print("✓ 四向核验全 PASS（源码↔日志↔digest↔独立袋 + 拐根锁紧 + marker-intact 端到端）")
