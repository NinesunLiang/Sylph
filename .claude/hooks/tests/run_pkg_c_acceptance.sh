#!/usr/bin/env bash
# PKG-C mechanical acceptance harness
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
export CLAUDE_PROJECT_DIR="$ROOT"

echo "== PKG-C V0 baseline =="
test "$(git rev-parse HEAD)" = "91954a0b01f9c53edf94965238308fcb080818eb" \
  || echo "WARN: HEAD != frozen baseline (integrator may have rebased); continue if intentional"

echo "== PKG-C V1 files exist =="
test -f .claude/hooks/lib/lifecycle_ssot.py
test -f .claude/hooks/precompact-lifecycle.py
test -f .claude/hooks/subagent-stop-lifecycle.py
test -f .claude/hooks/session-end-lifecycle.py
test -f .claude/hooks/stop-lifecycle-wrapper.sh
test -f .claude/hooks/stop-flywheel.py
chmod +x .claude/hooks/stop-lifecycle-wrapper.sh

echo "== PKG-C V2 settings events =="
python3 - <<'PY'
import json
from pathlib import Path
h = json.loads(Path(".claude/settings.json").read_text())["hooks"]
for k in ("PreCompact", "SubagentStop", "SessionEnd", "Stop"):
    assert k in h, k
cmd = h["Stop"][0]["hooks"][0]["command"]
assert "stop-lifecycle-wrapper.sh" in cmd, cmd
pc = h["PreCompact"][0]["hooks"][0]["command"]
assert "precompact-lifecycle.py" in pc, pc
print("settings_ok")
PY

echo "== PKG-C V3 unit suite =="
python3 .claude/hooks/tests/test_pkg_c_lifecycle.py

echo "== PKG-C V4 live hook triggers + jq =="
mkdir -p .claude/state/snapshots

# seed distorted claimed (simulates 0/0 speech vs 3 items)
python3 - <<'PY'
import json
from pathlib import Path
p = Path(".claude/state/handoff.json")
p.parent.mkdir(parents=True, exist_ok=True)
data = {
  "version": 1,
  "updated_at": "1970-01-01T00:00:00Z",
  "written": 0,
  "claimed": 0,
  "reconciled": False,
  "items": [
    {"id":"i1","kind":"seed","source":"accept","at":"t","body":{"n":1}},
    {"id":"i2","kind":"seed","source":"accept","at":"t","body":{"n":2}},
    {"id":"i3","kind":"seed","source":"accept","at":"t","body":{"n":3}},
  ],
}
p.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
print("seeded")
PY

printf '%s' '{"session_id":"accept-1","hook_event_name":"PreCompact","transcript_path":"/tmp/a.jsonl"}' \
  | python3 .claude/hooks/precompact-lifecycle.py | tee /tmp/pkgc-pc.out
test "$(jq -r .ok /tmp/pkgc-pc.out)" = "true"

# jq: counters must match len(items)
python3 - <<'PY'
import json
from pathlib import Path
hb = json.loads(Path(".claude/state/handoff.json").read_text())
assert hb["written"] == hb["claimed"] == len(hb["items"]), hb
assert hb["written"] >= 3, hb
lc = json.loads(Path(".claude/state/lifecycle.json").read_text())
assert lc["compact"]["last_sha256"], lc
snap = Path(lc["compact"]["last_snapshot_path"])
if not snap.is_absolute():
    snap = Path(".") / snap
assert snap.is_file(), snap
print("jq_counters_ok", hb["written"])
PY

printf '%s' '{"session_id":"accept-1","agent_id":"ag-1","agent_type":"executor","hook_event_name":"SubagentStop"}' \
  | python3 .claude/hooks/subagent-stop-lifecycle.py | tee /tmp/pkgc-ss.out
test "$(jq -r .ok /tmp/pkgc-ss.out)" = "true"

printf '%s' '{"session_id":"accept-1","hook_event_name":"Stop"}' \
  | bash .claude/hooks/stop-lifecycle-wrapper.sh | tee /tmp/pkgc-stop.out

python3 - <<'PY'
import json
from pathlib import Path
lc = json.loads(Path(".claude/state/lifecycle.json").read_text())
assert lc["mode"] == "idle", lc
assert lc["end"]["sealed"] is True, lc
assert lc.get("goal_id") in (None, "") and lc.get("ghost_id") in (None, "")
hb = json.loads(Path(".claude/state/handoff.json").read_text())
assert hb["written"] == hb["claimed"] == len(hb["items"])
print("end_seal_ok")
PY

echo "== PKG-C V5 registry zombie auto-snapshot =="
grep -q 'zombie_deleted_from_runtime' .claude/references/feature-registry.yaml
grep -q 'precompact-lifecycle' .claude/references/feature-registry.yaml

echo "== PKG-C V6 no verify/oracle file touch (scope guard) =="
# ensure this commit set does not modify PKG-A/B cores if git available
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git diff --name-only | grep -E 'verify_gate|oracle_gate|cmd_verify' ; then
    echo "SCOPE_FAIL: touched PKG-A/B files" >&2
    exit 1
  fi
fi

echo "ALL_PKG_C_ACCEPTANCE_PASSED"
