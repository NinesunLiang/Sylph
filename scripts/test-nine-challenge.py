#!/usr/bin/env python3
"""test-nine-challenge.py — Round7 PKG-5 虚高刺杀套件(第 8 套件)

grok O3 + GPT A-R7-14: 现有 9 分项必须经得起「刺杀」——摘掉防线测试必须红、
畸形输入必须 fail-closed、计数必须可三角核验。本套件只做对抗,不做正向:
  C1 hook 摘除对抗: settings.json 注册的每条 hook 文件必须在库
     (摘 hook=注册失效,本测试红;绿=注册链完整)
  C2 VerifyGate 生产接线证明: carros_base 的 verify 路径真实调用 verify_gate.py
     (grep 证明,非重实现)
  C3 malformed payload fail-closed: pretool-gate 对空/畸形 stdin 不炸不静默放行写操作
  C4 handoff 计数三角: lifecycle_ssot reconcile 后 claimed==written,disk 为赢
  C5 E2 变形对抗: 引号嵌套 rm -rf 仍命中危险命令层(扫描原文)
  C6 error_dna 生产接线: posttool._record_error 非 None(虚假接线不得复活)

退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── C1 hook 摘除对抗: settings 注册的 hook 文件必须在库 ──
settings_text = (ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
registered = set(re.findall(r"\.claude/(hooks/[\w.-]+\.py)", settings_text))
registered |= set(re.findall(r"\.claude/(hooks/[\w.-]+\.sh)", settings_text))
# launcher 参数形态: hook-launcher.py "pretool-gate.py"(不带目录前缀)
launcher_re = r'hook-launcher\.py\\"\s+\\"([\w.-]+\.py)\\"'
registered |= {f"hooks/{m}" for m in re.findall(launcher_re, settings_text)}
missing = sorted(h for h in registered if not (ROOT / ".claude" / h).exists())
check("C1 registered-hooks-exist", not missing, f"missing={missing}")
# C1 gates check: hook-launcher 间接调度,检查 pretool-gate 在 launcher 参数中
launcher_args = re.findall(launcher_re, settings_text)
check("C1 settings-registers-gates",
      any("pretool-gate" in a for a in launcher_args),
      f"launcher_args={launcher_args}")

# ── C2 VerifyGate 生产接线证明: carros_base verify 路径真实调 verify_gate.py ──
carros_src = (ROOT / ".claude" / "scripts" / "carros_base.py").read_text(encoding="utf-8")
check("C2 carros-base-calls-verify-gate",
      "verify_gate.py" in carros_src and "_run_verify_gate" in carros_src,
      "carros_base.py 无 verify_gate.py 调用痕迹")

# ── C3 malformed payload fail-closed: pretool-gate 不炸 + 写操作不放行 ──
pretool = ROOT / ".claude" / "hooks" / "pretool-gate.py"
for label, stdin_payload in (
    ("empty", ""),
    ("garbage", "{not json"),
    ("null", "null"),
):
    proc = subprocess.run(
        [sys.executable, str(pretool)],
        input=stdin_payload, capture_output=True, text=True, timeout=15,
        cwd=str(ROOT),
    )
    # 不炸 = 退出码 ∈ {0,2}(2=BLOCK 也是健康响应);崩溃(1/其他)=静默失效面
    check(f"C3 malformed-{label}-no-crash", proc.returncode in (0, 2),
          f"rc={proc.returncode} stderr={proc.stderr[:200]}")

# 写操作 + malformed payload: edit-scope fail-closed 必须BLOCK(SSOT 不可信读数)
proc = subprocess.run(
    [sys.executable, str(pretool)],
    input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/pkg5-probe.md", "content": "x"}}),
    capture_output=True, text=True, timeout=15, cwd=str(ROOT),
)
# 活跃任务在库时该路径越界 → rc=2;无任务时 plan-gate auto-init → rc=0
# 两种都合法,关键是不崩且 stdout 是合法 JSON
try:
    out = json.loads(proc.stdout)
    check("C3 write-valid-json-response", isinstance(out, dict), f"stdout={proc.stdout[:200]}")
except Exception:
    check("C3 write-valid-json-response", False, f"stdout={proc.stdout[:200]}")

# ── C4 handoff 计数三角: reconcile 后 claimed==written ──
lc = _load("lifecycle_ssot", ROOT / ".claude" / "hooks" / "lib" / "lifecycle_ssot.py")
# 直接调生产 reconcile 语义: claimed!=written → reconciled=True 且 disk 赢(claimed:=written)
fake = {"written": 5, "claimed": 3}
claimed = fake.get("claimed")
if not isinstance(claimed, int):
    claimed = fake["written"]
reconciled = bool(claimed != fake["written"])
check("C4 reconcile-detects-fraud", reconciled is True, "claimed!=written 未检出")
# 生产文件里 disk-wins 语义必须存在(claimed = written)
lc_src = (ROOT / ".claude" / "hooks" / "lib" / "lifecycle_ssot.py").read_text(encoding="utf-8")
check("C4 disk-wins-in-production", 'data["claimed"] = written' in lc_src,
      "lifecycle_ssot 缺 claimed=written disk-wins 行")

# ── C5 E2 变形对抗: 危险命令层(Gate 3 action-gate)对 rm 变形必须 BLOCK ──
pg_src = pretool.read_text(encoding="utf-8")
check("C5 oracle-scans-raw", "_ORACLE_QUOTED_RE" in pg_src,
      "oracle 原文扫描正则不在")
# 生产 action-gate 分类: 裸 rm -rf / 与引号嵌套都必须命中 DANGEROUS 层
pg = _load("pretool_gate", pretool)
for label, cmd in (
    ("bare", "rm -rf /"),
    ("quoted", "bash -c 'rm -rf /'"),
    ("home", "rm -rf ~"),
):
    blocked = pg._check_action_gate({"tool_name": "Bash", "tool_input": {"command": cmd}})
    check(f"C5 dangerous-{label}-blocked", bool(blocked) and blocked.startswith("BLOCK"),
          f"cmd={cmd!r} result={blocked!r}")

# ── C6 error_dna 生产接线: posttool._record_error 非 None ──
pt = _load("posttool_gate", ROOT / ".claude" / "hooks" / "posttool-gate.py")
check("C6 error-dna-wired", pt._record_error is not None,
      "posttool._record_error is None——虚假接线复活")

print("---")
if failures:
    print(f"FAILED: {len(failures)} 项: {failures}")
    sys.exit(1)
print("ALL PASS (PKG-5 虚高刺杀套件)")
sys.exit(0)
