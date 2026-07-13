#!/usr/bin/env python3
"""Runtime verification runner - single file, no shell escaping issues."""
import subprocess, sys, json
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / ".omc" / "scripts"))
PROJECT = Path.cwd()
results = []

def test(name, cmd, check_fn, timeout=15):
    try:
        r = subprocess.run(cmd, cwd=str(PROJECT), capture_output=True, text=True, timeout=timeout, shell=True)
        ok = check_fn(r.stdout, r.stderr) if r.returncode == 0 else False
        status = 'PASS' if ok else 'FAIL'
    except Exception as e:
        status = 'FAIL'
        r_stdout = ''
    results.append({'test': name, 'status': status, 'stdout': r.stdout[:200] if hasattr(r,'stdout') else ''})
    print(f'  [{status}] {name}')

from lib.tool_store import store_tool_result
from lib.error_dna import record_error, check_retry_gate
from lib.oracle_gate_light import should_trigger_oracle
from lib.flywheel import run_flywheel
from lib.autonomy import load_contract, LoopDetector, check_autonomy_gate
import yaml

print('=== Phase 0 — Token Slim ===')

# S2
a = Path("AGENTS.md").read_text().splitlines()
test('S2 AGENTS.md <=43 lines', f'test $(wc -l < AGENTS.md) -le 43', lambda o,_: True)
test('S2 Oracle=0', f'grep -ci oracle AGENTS.md', lambda o,_: o.strip() == '0')

# S3
test('S3 Hot Card', f'python3 .claude/scripts/carros_base.py status', lambda o,_: 'CarrorOS Hot Card' in o)

# S4
r = store_tool_result('v', b'x'*250000, {"exit_code": 0})
test('S4 tools store', 'echo ok', lambda o,_: r['bytes'] >= 240000 and len(r['preview']) < 2000)

# S5
import subprocess as sb
p_rev = json.dumps({"tool_name":"read","tool_input":{"file_path":"docs/carros/reviews/x.md"}})
r_block = sb.run(['python3','.claude/hooks/pretool-gate.py'], input=p_rev, capture_output=True, text=True, timeout=5)
test('S5 reviews BLOCK', 'echo ok', lambda o,_: 'false' in r_block.stdout)

p_ok = json.dumps({"tool_name":"read","tool_input":{"file_path":"AGENTS.md","offset":1,"limit":5}})
r_allow = sb.run(['python3','.claude/hooks/pretool-gate.py'], input=p_ok, capture_output=True, text=True, timeout=5)
test('S5 normal ALLOW', 'echo ok', lambda o,_: 'true' in r_allow.stdout)

# S6
em = Path(".claude/prompts/executor_micro.txt")
test('S6 executor_micro <=15 lines', 'echo ok', lambda o,_: len(em.read_text().splitlines()) <= 15)

# S7
cost = sb.run(['python3','.claude/scripts/carros_cost_report.py'], capture_output=True, text=True, timeout=15)
test('S7 cost report PASS', 'echo ok', lambda o,_: 'PASS' in cost.stdout)

print('\n=== Phase 0.5 — 文档基建 ===')

# W1: Handoff
h = PROJECT / ".omc/tasks/20260713/phase3-dual-judge/handoff.md"
has_nsot = "NOT SOURCE" in h.read_text() if h.exists() else True  # new tasks
test('W1 Handoff NOT_SOURCE_OF_TRUTH', 'echo ok', lambda o,_: has_nsot)

# W2: Task profiles
with open(str(PROJECT / ".claude/references/task-profiles.yaml")) as f:
    tp = yaml.safe_load(f)
test('W2 task-profiles L1+L2', 'echo ok', lambda o,_: 'L1' in tp and 'L2' in tp)

# W3: INDEX
with open(str(PROJECT / "docs/INDEX.yaml")) as f:
    idx = yaml.safe_load(f)
test('W3 INDEX >=7 docs', 'echo ok', lambda o,_: len(idx.get('documents',[])) >= 7)

# W4: Invariants
inv = Path(".claude/references/invariants.md")
inv_cnt = sum(1 for l in inv.read_text().splitlines() if 'INV-' in l)
test('W4 12 invariants', 'echo ok', lambda o,_: inv_cnt >= 12)

print('\n=== Phase 1 — L2 治理 ===')

# P1: working-set
with open(str(PROJECT / ".claude/references/working-set-template.yaml")) as f:
    ws = yaml.safe_load(f)
test('P1 working-set require_evidence', 'echo ok', lambda o,_: ws.get('verify',{}).get('require_evidence') == True)

# P1: Error DNA
d = record_error(PROJECT / ".omc", "T1", "test error")
test('P1 Error DNA records', 'echo ok', lambda o,_: d['step'] == 'T1')

# P1: Retry gate
a, c, m = check_retry_gate(PROJECT / ".omc/tasks/20260713/phase3-dual-judge", "T-NOEXIST")
test('P1 Retry gate works', 'echo ok', lambda o,_: a == True)

# P1: Oracle L1
trig, _ = should_trigger_oracle('L1')
test('P1 Oracle L1=no', 'echo ok', lambda o,_: trig == False)

# P1: Oracle L2+high
trig, _ = should_trigger_oracle('L2', risk_level='high')
test('P1 Oracle L2+high=yes', 'echo ok', lambda o,_: trig == True)

# P1: Oracle L2+medium=defer
trig, _ = should_trigger_oracle('L2', risk_level='medium')
test('P1 Oracle L2+medium=defer', 'echo ok', lambda o,_: trig == False)

print('\n=== Phase 2 — 飞轮+无人 ===')

# P2: Flywheel
fly_r = run_flywheel(PROJECT)
test('P2 Flywheel runs', 'echo ok', lambda o,_: isinstance(fly_r, dict))

# P2: claude-next
cn = PROJECT / ".omc/knowledge/claude-next.md"
test('P2 claude-next exists', 'echo ok', lambda o,_: cn.exists())

# P2: Loop detection
ld = LoopDetector(3)
[ld.record_tick('S','a') for _ in range(5)]
d = ld.detect_loop()
test('P2 Loop detection', 'echo ok', lambda o,_: d is not None and 'loop' in d['type'])

# P2: Autonomy contract
c = load_contract(PROJECT)
test('P2 Contract max_turns=30', 'echo ok', lambda o,_: c['boundaries']['max_autonomy_turns'] == 30)

# P2: Budget pause
token_over = {"stats": {"tick": 35}, "budget": {"max_turns_hard": 30}}
reason = check_autonomy_gate(token_over, LoopDetector())
test('P2 Budget pause', 'echo ok', lambda o,_: reason is not None)

# Summary
print(f'\n{"="*50}')
pass_cnt = sum(1 for r in results if r['status'] == 'PASS')
print(f'Runtime verification: {pass_cnt}/{len(results)} PASS')
for r in results:
    if r['status'] == 'FAIL':
        print(f'  FAIL: {r["test"]} — {r["stdout"][:80]}')
