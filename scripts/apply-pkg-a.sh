#!/usr/bin/env bash
# apply-pkg-a.sh — PKG-A 验证链修复施工脚本(整合器基于真实代码施工)
# 靶心: E3 虚假完成(基线 4 分)
# 三处修复 + 测试重写:
#   F1 carros_base.py: cmd_verify 接线 verify_gate(_run_verify_gate + 裁决循环);
#      _write_audit 自动绑定 task_id;L1 无规则降级留痕(verify_degraded,非 VERIFIED)
#   F2 verify_gate.py: write_audit task_id 从 session.id 取(原读 task.id 永远 unknown)
#   F3 pretool-gate.py: _check_verified step+task 双绑定,None 通配删除,
#      扫描 .omc/audit + .omc/state/audit + 任务自身 state/audit
#   F4 scripts/test-verify-gate.py: 重写(已先行 Write)— 本脚本只跑它验收
# 幂等: 已应用则 SKIP;备份已存在则不覆盖
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail() { echo "ERROR: $1" >&2; exit 1; }

# ---------- 1. 前置保护 ----------
BK=.omc/state/pkg-a-backup
mkdir -p "$BK"
if [ ! -f "$BK/pre-pkg-a.sha256" ]; then
  python3 - << 'PY'
from pathlib import Path
import hashlib, json
files = [
    ".claude/scripts/carros_base.py",
    ".claude/scripts/verify_gate.py",
    ".claude/hooks/pretool-gate.py",
    "scripts/test-verify-gate.py",
    # 邻边观察(不得被本包改动)
    ".claude/scripts/carros_utils.py",
    ".claude/settings.json",
    ".claude/hooks/hook-launcher.sh",
    ".claude/hooks/posttool-gate.py",
]
data = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
Path(".omc/state/pkg-a-backup/pre-pkg-a.sha256").write_text(
    json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("pre-pkg-a.sha256 written")
PY
else
  echo "backup exists, skip"
fi

# ---------- 2. 代码替换(锚点唯一校验 + 幂等) ----------
python3 - << 'PY'
from pathlib import Path
import sys

def replace(path, old, new, label, marker=None):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    # 幂等: marker 必须是"应用后才存在"的特征串(new 前 60 字符可能与 old 重叠,不可作判据)
    mark = marker if marker is not None else new.strip()[:60]
    if mark in text:
        print(f"SKIP {label} (already applied)")
        return
    old_n = text.count(old)
    if old_n == 0:
        print(f"ERROR {label}: anchor not found in {path}", file=sys.stderr)
        raise SystemExit(2)
    if old_n != 1:
        print(f"ERROR {label}: anchor not unique ({old_n}) in {path}", file=sys.stderr)
        raise SystemExit(2)
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"OK   {label}")

CB = ".claude/scripts/carros_base.py"
VG = ".claude/scripts/verify_gate.py"
PG = ".claude/hooks/pretool-gate.py"

# F1a: _run_verify_gate 助手(插在 cmd_verify 前)
replace(CB,
    'def cmd_verify(step_id=None):\n    """验证 step 完成 — 标记 plan.md [x] + 写 audit"""',
    '''def _run_verify_gate(step_id):
    """Shell out 到 verify_gate.py 裁决 step — 返回 (decision, reason, payload)。

    fail-closed: 脚本缺失/执行异常/输出不可解析 一律 BLOCKED。
    decision 取自 stdout JSON(exit code 仅辅助: VERIFIED=0, 其余=1)。
    """
    import subprocess
    # carros_base.py 是符号链接(.claude/scripts -> .omc/scripts),
    # verify_gate.py 实体在 .claude/scripts — 三候选定位,fail-closed
    _candidates = [
        Path(__file__).parent / "verify_gate.py",
        Path(__file__).resolve().parent / "verify_gate.py",
        Path(__file__).resolve().parents[2] / ".claude/scripts" / "verify_gate.py",
    ]
    script = next((c for c in _candidates if c.exists()), None)
    if script is None:
        return "BLOCKED", "verify_gate_missing", {
            "required_action": "恢复 .claude/scripts/verify_gate.py 后重跑"}
    cmd = [sys.executable, str(script), "--step", step_id,
           "--plan", str(PLAN_PATH), "--executor", str(EXECUTOR_PATH)]
    if TOKEN_PATH:
        cmd += ["--token", str(TOKEN_PATH)]
    spec = (TASK_DIR / "spec.md") if TASK_DIR else None
    if spec and spec.exists():
        cmd += ["--spec", str(spec)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return "BLOCKED", f"verify_gate_error:{type(exc).__name__}", {}
    try:
        payload = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return "BLOCKED", f"verify_gate_bad_output:{(r.stdout or r.stderr or '')[:160]}", {}
    return payload.get("decision", "BLOCKED"), payload.get("reason", ""), payload


def cmd_verify(step_id=None):
    """验证 step 完成 — VerifyGate 裁决通过才标记 plan.md [x] + 写 task-bound audit"""''',
    "F1a _run_verify_gate helper")

# F1b: cmd_verify 裁决循环(先裁决后标记;L1 无规则降级留痕)
replace(CB,
    '''    verified_any = False
    for target in targets:
        pattern = re.compile(r"^- \\[ \\] " + re.escape(target) + r":", re.MULTILINE)
        replacement = f"- [x] {target}:"
        new_plan, count = pattern.subn(replacement, plan)
        if count > 0:
            plan = new_plan
            # 更新 token — 统一新格式（递增 done 计数器）
            token["stats"]["done"] = token["stats"].get("done", 0) + 1
            if token["stats"]["done"] >= token["stats"]["total"]:
                token["task"]["status"] = "completed"
            _write_audit("verify", {"step": target, "result": "VERIFIED"})
            print(_green(f"✅ {target}: VERIFIED"))''',
    '''    level = token.get("session", {}).get("level", "L1_BASE")
    verified_any = False
    for target in targets:
        # ── VerifyGate 接线（PKG-A）：无证据不 [x]，fail-closed ──
        decision, reason, gate_payload = _run_verify_gate(target)
        degraded = False
        if decision in ("VERIFIED", "WARN"):
            pass
        elif level != "L2_ENHANCE" and reason in ("no_verify_rules", "executor_missing"):
            # L1 轻量任务无验证契约：允许标记但必须留痕（不产生 VERIFIED，Gate6 不放行）
            degraded = True
        else:
            _write_audit("verify", {"step": target, "result": decision, "reason": reason})
            print(_red(f"❌ {target}: VerifyGate {decision} — {reason}"))
            required = gate_payload.get("required_action")
            if required:
                print(_yellow(f"   需要: {required}"))
            return 2
        pattern = re.compile(r"^- \\[ \\] " + re.escape(target) + r":", re.MULTILINE)
        replacement = f"- [x] {target}:"
        new_plan, count = pattern.subn(replacement, plan)
        if count > 0:
            plan = new_plan
            # 更新 token — 统一新格式（递增 done 计数器）
            token["stats"]["done"] = token["stats"].get("done", 0) + 1
            if token["stats"]["done"] >= token["stats"]["total"]:
                token["task"]["status"] = "completed"
            if degraded:
                _write_audit("verify_degraded", {"step": target, "reason": reason})
                print(_yellow(f"⚠  {target}: {reason} — 降级标记并留痕（非 VERIFIED）"))
            else:
                _write_audit("verify", {
                    "step": target, "result": "VERIFIED", "gate": decision,
                    "warnings": gate_payload.get("warnings", []),
                })
                print(_green(f"✅ {target}: VERIFIED"))''',
    "F1b cmd_verify gate wiring",
    marker='decision, reason, gate_payload = _run_verify_gate(target)')

# F1c: _write_audit 自动绑定 task_id
replace(CB,
    '''def _write_audit(event_type, data, fallback=False):
    """追加审计事件到当天 JSONL — 委托 carros_utils"""
    if carros_utils:''',
    '''def _write_audit(event_type, data, fallback=False):
    """追加审计事件到当天 JSONL — 委托 carros_utils（自动绑定 task_id）"""
    if isinstance(data, dict) and "task_id" not in data:
        _tid = None
        try:
            _token = _load_token()
            if _token:
                _tid = (_token.get("session") or {}).get("id")
        except Exception:
            _tid = None
        data = dict(data)
        data["task_id"] = _tid or "unknown"
    if carros_utils:''',
    "F1c _write_audit task_id binding",
    marker='data["task_id"] = _tid or "unknown"')

# F2: verify_gate write_audit task_id 从 session.id 取
replace(VG,
    '''    if token:
        event["task_id"] = token.get("task", {}).get("id", "unknown")''',
    '''    if token:
        event["task_id"] = (token.get("session", {}) or {}).get("id") \\
            or token.get("task", {}).get("id", "unknown")''',
    "F2 verify_gate session.id fix")

# F3a: _check_verified step+task 双绑定,通配删除,三目录扫描
replace(PG,
    '''def _check_verified(step_id: str | None) -> bool:
    if not AUDIT.exists():
        return False
    for f in sorted(AUDIT.glob("*.jsonl")):
        with f.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # carros_base.py writes: {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}}
                if e.get("event") == "verify":
                    data = e.get("data", {})
                    if isinstance(data, dict) and data.get("result") == "VERIFIED":
                        if step_id is None or data.get("step") == step_id:
                            return True
                # Legacy compat: {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"}
                if e.get("event_type") == "verify_decision" and e.get("decision") == "VERIFIED":
                    if step_id is None or e.get("step") == step_id:
                        return True
    return False''',
    '''def _check_verified(step_id: str | None, task_id: str | None = None,
                    task_dir: Path | None = None) -> bool:
    """VerifyGate 审计回读 — step + task 双绑定，无通配，fail-closed。

    仅当审计中存在 (step_id, task_id) 双匹配的 VERIFIED 事件才放行。
    历史无 task_id 事件、跨任务事件、畸形事件一律不计（PKG-A）。
    扫描: .omc/audit(verify_gate 写) + .omc/state/audit(carros_base fallback)
          + 任务自身 state/audit(carros_base 主写点)。
    """
    if not step_id or not task_id:
        return False
    dirs = [AUDIT, OMC / "state" / "audit"]
    if task_dir:
        dirs.append(Path(task_dir) / "state" / "audit")
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # carros_base.py: {"event": "verify", "data": {"step", "result", "task_id"}}
                    if e.get("event") == "verify":
                        data = e.get("data", {})
                        if (isinstance(data, dict)
                                and data.get("result") == "VERIFIED"
                                and data.get("step") == step_id
                                and data.get("task_id") == task_id):
                            return True
                    # verify_gate.py: {"event_type": "verify_decision", "decision", "step", "task_id"}
                    if (e.get("event_type") == "verify_decision"
                            and e.get("decision") == "VERIFIED"
                            and e.get("step") == step_id
                            and e.get("task_id") == task_id):
                        return True
    return False''',
    "F3a _check_verified task binding")

# F3b: Gate6 调用点传 task_id + task_dir
replace(PG,
    '''    current_step = task.get("current_step")
    if not _check_verified(current_step):''',
    '''    current_step = task.get("current_step")
    session = token.get("session", {})
    task_id = session.get("id") if isinstance(session, dict) else None
    if not _check_verified(current_step, task_id, _task_dir(token)):''',
    "F3b Gate6 call site")
PY

# ---------- 3. 机械验收 ----------
echo "== acceptance =="

# A-A1: 四文件语法
python3 -m py_compile .claude/scripts/carros_base.py || fail "A-A1: py_compile carros_base"
python3 -m py_compile .claude/scripts/verify_gate.py || fail "A-A1: py_compile verify_gate"
python3 -m py_compile .claude/hooks/pretool-gate.py || fail "A-A1: py_compile pretool-gate"
python3 -m py_compile scripts/test-verify-gate.py || fail "A-A1: py_compile test-verify-gate"
echo "A-A1 OK"

# A-A2: 接线锚点存在
grep -qF 'def _run_verify_gate(step_id):' .claude/scripts/carros_base.py || fail "A-A2: helper missing"
grep -qF 'decision, reason, gate_payload = _run_verify_gate(target)' .claude/scripts/carros_base.py || fail "A-A2: gate call missing"
grep -qF '"verify_degraded"' .claude/scripts/carros_base.py || fail "A-A2: degraded event missing"
grep -qF 'data["task_id"] = _tid or "unknown"' .claude/scripts/carros_base.py || fail "A-A2: audit binding missing"
grep -qF '(token.get("session", {}) or {}).get("id")' .claude/scripts/verify_gate.py || fail "A-A2: verify_gate session.id fix missing"
echo "A-A2 OK"

# A-A3: 通配洞已死
if grep -nF 'step_id is None or' .claude/hooks/pretool-gate.py; then
  fail "A-A3: None wildcard still present"
fi
grep -qF 'if not step_id or not task_id:' .claude/hooks/pretool-gate.py || fail "A-A3: fail-closed guard missing"
echo "A-A3 OK"

# A-A4: 完整对抗测试(U/C/E 三层)
python3 scripts/test-verify-gate.py || fail "A-A4: test-verify-gate.py FAILED"
echo "A-A4 OK"

# A-A5: 邻边未动
python3 - << 'PY'
from pathlib import Path
import hashlib, json, sys
steady = Path(".omc/state/pkg-a-backup/steady-state.sha256")
if steady.exists():
    # R5 起稳态模式: 施工期断言(下方 legacy 分支)已于 R2 完成,不可重入;
    # 此后改为纯漂移告警——8 个观察文件须与稳态快照逐一相同,
    # 任何漂移须声明确认后重冻结 steady-state.sha256(见终审包偏差声明)
    snap = json.loads(steady.read_text(encoding="utf-8"))
    drift = [p for p, h in sorted(snap.items())
             if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
    if drift:
        print(f"STEADY-STATE DRIFT: {drift}", file=sys.stderr)
        raise SystemExit(2)
    print("NEIGHBOR_BOUNDARY_OK (steady-state)")
    raise SystemExit(0)
old = json.loads(Path(".omc/state/pkg-a-backup/pre-pkg-a.sha256").read_text(encoding="utf-8"))
changed = [p for p, h in old.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
# test-verify-gate.py 属本包交付物(重写+迭代于备份前后),允许变化;只强制 3 个源文件必须变
expected = {".claude/scripts/carros_base.py", ".claude/scripts/verify_gate.py",
            ".claude/hooks/pretool-gate.py"}
allowed = expected | {"scripts/test-verify-gate.py"}
extra = set(changed) - allowed
if extra:
    print(f"NEIGHBOR CHANGED: {sorted(extra)}", file=sys.stderr)
    raise SystemExit(2)
missing = expected - set(changed)
if missing:
    print(f"EXPECTED BUT UNCHANGED: {sorted(missing)}", file=sys.stderr)
    raise SystemExit(2)
print("NEIGHBOR_BOUNDARY_OK")
PY

git diff --check -- \
  .claude/scripts/carros_base.py \
  .omc/scripts/carros_base.py \
  .claude/scripts/verify_gate.py \
  .claude/hooks/pretool-gate.py \
  scripts/test-verify-gate.py || fail "git diff --check (pkg-a files)"
echo "== ALL PKG-A ACCEPTANCE PASSED =="
