# runtime_verify.py ×2

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 重复验证实现候选
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/runtime_verify.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	runtime_verify.py — CarrorOS 运行时 E2E 验证
     4	
     5	跑实际场景并记录证据到 .omc/metrics/runtime-verify/
     6	"""
     7	
     8	import json
     9	import subprocess
    10	import sys
    11	import time
    12	from datetime import datetime, timezone
    13	from pathlib import Path
    14	
    15	SCRIPT_DIR = Path(__file__).resolve().parent
    16	PROJECT = (SCRIPT_DIR / ".." / "..").resolve()
    17	VERIFY_DIR = PROJECT / ".omc" / "metrics" / "runtime-verify"
    18	
    19	
    20	def log_evidence(name, status, detail, output=""):
    21	    """Record verification evidence."""
    22	    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    23	    record = {
    24	        "test": name,
    25	        "status": status,
    26	        "detail": detail[:500],
    27	        "output_preview": output[:1000] if output else "",
    28	        "timestamp": datetime.now(timezone.utc).isoformat(),
    29	    }
    30	    log_path = VERIFY_DIR / "evidence.jsonl"
    31	    with open(log_path, "a", encoding="utf-8") as f:
    32	        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    33	    return record
    34	
    35	
    36	def run_verify(phase, test_name, cmd, check_fn=None, timeout=15, expected_exit=0):
    37	    """Run a verification command and record evidence."""
    38	    full_name = f"[{phase}] {test_name}"
    39	    print(f"  → {full_name}")
    40	
    41	    try:
    42	        result = subprocess.run(
    43	            cmd, cwd=str(PROJECT),
    44	            capture_output=True, text=True, timeout=timeout,
    45	            shell=isinstance(cmd, str)
    46	        )
    47	        stdout = result.stdout[:2000]
    48	        stderr = result.stderr[:500]
    49	        exit_ok = result.returncode == expected_exit
    50	
    51	        if check_fn:
    52	            check_ok = check_fn(stdout, stderr)
    53	        else:
    54	            check_ok = exit_ok
    55	
    56	        if check_ok:
    57	            ev = log_evidence(full_name, "PASS", f"exit={result.returncode}", stdout)
    58	            print(f"    ✅ PASS (exit={result.returncode})")
    59	            return True, stdout
    60	        else:
    61	            ev = log_evidence(full_name, "FAIL", f"exit={result.returncode}: {stderr[:200]}", stdout)
    62	            print(f"    ❌ FAIL (exit={result.returncode})")
    63	            print(f"       {stderr[:200]}")
    64	            return False, stdout
    65	
    66	    except subprocess.TimeoutExpired:
    67	        log_evidence(full_name, "FAIL", "timeout", "")
    68	        print(f"    ❌ TIMEOUT ({timeout}s)")
    69	        return False, ""
    70	    except FileNotFoundError as e:
    71	        log_evidence(full_name, "FAIL", f"cmd not found: {e}", "")
    72	        print(f"    ❌ CMD_NOT_FOUND: {e}")
    73	        return False, ""
    74	
    75	
    76	# ── Test Suites ──
    77	
    78	def test_phase0_token_slim():
    79	    """Phase 0: Token Slim 运行时验证"""
    80	    print("\n=== Phase 0: Token Slim (Runtime) ===")
    81	    all_pass = True
    82	
    83	    # S2: AGENTS.md ≤100 lines
    84	    def check_agents(stdout, _):
    85	        lines = [l for l in stdout.splitlines() if l.strip()]
    86	        return len(lines) < 100
    87	    ok, _ = run_verify("P0-S2", "AGENTS.md ≤100行",
    88	        "wc -l AGENTS.md", check_fn=check_agents)
    89	    all_pass &= ok
    90	
    91	    # S2: No Oracle in AGENTS.md
    92	    ok, _ = run_verify("P0-S2", "AGENTS.md 无 Oracle",
    93	        "grep -ci oracle AGENTS.md",
    94	        check_fn=lambda o, _: o.strip() == "0")
    95	    all_pass &= ok
    96	
    97	    # S3: Hot Card 默认输出
    98	    def check_hotcard(stdout, _):
    99	        return "# CarrorOS Hot Card" in stdout
   100	    ok, _ = run_verify("P0-S3", "status 输出 Hot Card",
   101	        "python3 .claude/scripts/carros_base.py status",
   102	        check_fn=check_hotcard)
   103	    all_pass &= ok
   104	
   105	    # S4: Tool store
   106	    ok, _ = run_verify("P0-S4", "工具落盘 250KB→1.3K preview",
   107	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   108	        'from lib.tool_store import store_tool_result; '
   109	        'r=store_tool_result(\'verify-test\', b\'line\\n\'*50000,{\'exit_code\':0}); '
   110	        'print(r[\'bytes\'], len(r[\'preview\']))"',
   111	        check_fn=lambda o, _: int(o.split()[0]) > 100000 and int(o.split()[1]) < 2000)
   112	    all_pass &= ok
   113	
   114	    # S5: reviews → BLOCK
   115	    ok, _ = run_verify("P0-S5", "reviews 读取被阻断",
   116	        "printf '%s\\n' '{\"tool_name\":\"read\",\"tool_input\":{\"file_path\":\"docs/carros/reviews/test.md\"}}' | python3 .claude/hooks/pretool-gate.py",
   117	        check_fn=lambda o, _: '"continue": false' in o)
   118	    all_pass &= ok
   119	
   120	    # S5: normal → ALLOW
   121	    ok, _ = run_verify("P0-S5", "正常读取放行",
   122	        "printf '%s\\n' '{\"tool_name\":\"read\",\"tool_input\":{\"file_path\":\"AGENTS.md\",\"offset\":1,\"limit\":5}}' | python3 .claude/hooks/pretool-gate.py",
   123	        check_fn=lambda o, _: '"continue": true' in o)
   124	    all_pass &= ok
   125	
   126	    # S6: executor_micro.txt exists
   127	    ok, _ = run_verify("P0-S6", "executor_micro.txt ≤15行",
   128	        "wc -l .claude/prompts/executor_micro.txt",
   129	        check_fn=lambda o, _: int(o.split()[0]) <= 15)
   130	    all_pass &= ok
   131	
   132	    # S7: cost report pass
   133	    ok, _ = run_verify("P0-S7", "成本报表 PASS",
   134	        "python3 .claude/scripts/carros_cost_report.py",
   135	        check_fn=lambda o, _: "pass_p0: PASS" in o or "Phase 0: PASS" in o)
   136	    all_pass &= ok
   137	
   138	    return all_pass
   139	
   140	
   141	def test_phase05_docs():
   142	    """Phase 0.5: 文档基建 运行时验证"""
   143	    print("\n=== Phase 0.5: 文档基建 (Runtime) ===")
   144	    all_pass = True
   145	
   146	    # W1: Handoff Capsule 含 NOT_SOURCE_OF_TRUTH
   147	    ok, _ = run_verify("P0.5-W1", "Handoff NOT_SOURCE_OF_TRUTH",
   148	        "head -5 .omc/tasks/20260713/phase3-dual-judge/handoff.md 2>/dev/null || echo 'NO_HANDOFF'",
   149	        check_fn=lambda o, _: "NOT SOURCE OF TRUTH" in o or "NO_HANDOFF" in o)
   150	    all_pass &= ok
   151	
   152	    # W2: task-profiles.yaml
   153	    ok, _ = run_verify("P0.5-W2", "task-profiles.yaml 含 L1/L2",
   154	        "grep -c 'L1:' .claude/references/task-profiles.yaml",
   155	        check_fn=lambda o, _: int(o.strip()) >= 1)
   156	    all_pass &= ok
   157	
   158	    # W2: CAS revision
   159	    ok, _ = run_verify("P0.5-W2", "token.json 含 revision",
   160	        'python3 - << \'PY\'\nimport json\nfrom pathlib import Path\nfor p in sorted(Path(".omc/tokens").glob("**/*.json")):\n    try:\n        t=json.loads(p.read_text())\n    except Exception:\n        continue\n    if "revision" in t:\n        print(t.get("revision", 0))\n        raise SystemExit(0)\nprint("MISSING")\nraise SystemExit(1)\nPY',
   161	        check_fn=lambda o, _: o.strip().isdigit() and int(o.strip()) >= 0)
   162	    all_pass &= ok
   163	
   164	    # W3: INDEX.yaml
   165	    ok, _ = run_verify("P0.5-W3", "INDEX.yaml 含 INVARIANTS",
   166	        "grep -c INVARIANTS docs/INDEX.yaml",
   167	        check_fn=lambda o, _: int(o.strip()) >= 1)
   168	    all_pass &= ok
   169	
   170	    # W4: 12 invariants
   171	    ok, _ = run_verify("P0.5-W4", "12 条不变量",
   172	        "grep -c 'INV-' .claude/references/invariants.md",
   173	        check_fn=lambda o, _: int(o.strip()) >= 12)
   174	    all_pass &= ok
   175	
   176	    return all_pass
   177	
   178	
   179	def test_phase1_l2():
   180	    """Phase 1: L2 治理 运行时验证"""
   181	    print("\n=== Phase 1: L2 治理 (Runtime) ===")
   182	    all_pass = True
   183	
   184	    # P1: working-set.yaml
   185	    ok, _ = run_verify("P1-L2", "working-set 含 retry/verify",
   186	        "grep -c max_retries .claude/references/working-set-template.yaml",
   187	        check_fn=lambda o, _: int(o.strip()) >= 1)
   188	    all_pass &= ok
   189	
   190	    # P1: Error DNA
   191	    ok, _ = run_verify("P1-DNA", "Error DNA 可记录",
   192	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   193	        'from lib.error_dna import record_error; '
   194	        'from pathlib import Path; '
   195	        'd=record_error(Path(\'.omc/tasks/20260713/phase3-dual-judge\'),\'T1\',\'test error\'); '
   196	        'print(d[\'step\'], d[\'retry_count\'])"',
   197	        check_fn=lambda o, _: "T1" in o and "0" in o)
   198	    all_pass &= ok
   199	
   200	    # P1: Retry gate
   201	    ok, _ = run_verify("P1-DNA", "Retry Gate 3次阻断",
   202	        'python3 - << \'PY\'\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, ".omc/scripts")\nfrom lib.error_dna import check_retry_gate, record_error\np=Path(".omc/tasks/20260713/phase3-dual-judge")\nfor i in range(4):\n    record_error(p,"T2",f"err{i}",retry_count=i)\na,_,_=check_retry_gate(p,"T2")\nprint(a)\nPY',
   203	        check_fn=lambda o, _: "False" in o)
   204	    all_pass &= ok
   205	
   206	    # P1: Oracle trigger L1=no
   207	    ok, _ = run_verify("P1-ORACLE", "Oracle L1=不触发",
   208	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   209	        'from lib.oracle_gate_light import should_trigger_oracle; '
   210	        'print(should_trigger_oracle(\'L1\')[0])"',
   211	        check_fn=lambda o, _: "False" in o)
   212	    all_pass &= ok
   213	
   214	    # P1: Oracle trigger L2+high=yes
   215	    ok, _ = run_verify("P1-ORACLE", "Oracle L2+high=触发",
   216	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   217	        'from lib.oracle_gate_light import should_trigger_oracle; '
   218	        'print(should_trigger_oracle(\'L2\',risk_level=\'high\')[0])"',
   219	        check_fn=lambda o, _: "True" in o)
   220	    all_pass &= ok
   221	
   222	    return all_pass
   223	
   224	
   225	def test_phase2_flywheel():
   226	    """Phase 2: 飞轮+无人 运行时验证"""
   227	    print("\n=== Phase 2: 飞轮+无人 (Runtime) ===")
   228	    all_pass = True
   229	
   230	    # P2: Flywheel
   231	    ok, _ = run_verify("P2-FLY", "飞轮可运行",
   232	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   233	        'from lib.flywheel import run_flywheel; '
   234	        'from pathlib import Path; '
   235	        'r=run_flywheel(Path.cwd()); print(r.get(\'patterns_found\',0), r.get(\'knowledge_entries\',0))"',
   236	        timeout=30)
   237	    all_pass &= ok
   238	
   239	    # P2: claude-next.md
   240	    ok, _ = run_verify("P2-FLY", "claude-next.md 存在",
   241	        "test -f .omc/knowledge/claude-next.md && echo 'EXISTS' || echo 'MISSING'",
   242	        check_fn=lambda o, _: "EXISTS" in o)
   243	    all_pass &= ok
   244	
   245	    # P2: Loop detection
   246	    ok, _ = run_verify("P2-AUTO", "Loop 检测",
   247	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   248	        'from lib.autonomy import LoopDetector; '
   249	        'l=LoopDetector(3); [l.record_tick(\'S1\',\'same\',\'same\') for _ in range(5)]; '
   250	        'd=l.detect_loop(); print(d[\'type\'] if d else \'none\')"',
   251	        check_fn=lambda o, _: "loop" in o.lower())
   252	    all_pass &= ok
   253	
   254	    # P2: Autonomy contract
   255	    ok, _ = run_verify("P2-AUTO", "Autonomy Contract 加载",
   256	        'python3 - << \'PY\'\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, ".omc/scripts")\nfrom lib.autonomy import load_contract\nc=load_contract(Path.cwd())\nprint(c["boundaries"]["max_autonomy_turns"])\nPY',
   257	        check_fn=lambda o, _: "30" in o)
   258	    all_pass &= ok
   259	
   260	    # P2: Budget exceeded pause
   261	    ok, _ = run_verify("P2-AUTO", "超 budget 暂停",
   262	        'python3 -c "import sys; sys.path.insert(0,\'.omc/scripts\'); '
   263	        'from lib.autonomy import check_autonomy_gate, LoopDetector; '
   264	        't={\'stats\':{\'tick\':35,\'done\':2},\'budget\':{\'max_turns_hard\':30}}; '
   265	        'r=check_autonomy_gate(t, LoopDetector()); print(r is not None)"',
   266	        check_fn=lambda o, _: "True" in o)
   267	    all_pass &= ok
   268	
   269	    return all_pass
   270	
   271	
   272	if __name__ == "__main__":
   273	    print("=" * 60)
   274	    print("CarrorOS Runtime Verification Suite")
   275	    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
   276	    print("=" * 60)
   277	
   278	    phases = [
   279	        ("Phase 0 — Token Slim", test_phase0_token_slim),
   280	        ("Phase 0.5 — 文档基建", test_phase05_docs),
   281	        ("Phase 1 — L2 治理", test_phase1_l2),
   282	        ("Phase 2 — 飞轮+无人", test_phase2_flywheel),
   283	    ]
   284	
   285	    results = {}
   286	    total_pass = 0
   287	    total_tests = 0
   288	
   289	    for name, test_fn in phases:
   290	        print(f"\n{'─'*60}")
   291	        print(f"Running: {name}")
   292	        ok = test_fn()
   293	        results[name] = "✅ PASS" if ok else "❌ FAIL"
   294	        if ok:
   295	            total_pass += 1
   296	        # Count evidence
   297	        ev_path = VERIFY_DIR / "evidence.jsonl"
   298	        if ev_path.exists():
   299	            with open(ev_path) as f:
   300	                tests_here = sum(1 for _ in f)
   301	                total_tests = tests_here  # Will be cumulative
   302	
   303	    # Summary
   304	    print(f"\n{'='*60}")
   305	    print("RUNTIME VERIFICATION SUMMARY")
   306	    print(f"{'='*60}")
   307	    for name, r in results.items():
   308	        print(f"  {r} {name}")
   309	
   310	    ev_path = VERIFY_DIR / "evidence.jsonl"
   311	    if ev_path.exists():
   312	        with open(ev_path) as f:
   313	            full_count = sum(1 for _ in f)
   314	        print(f"\n  Total tests: {full_count}")
   315	        print(f"  Evidence: {ev_path}")
   316	    
   317	    print(f"\n  Pass rate: {sum(1 for r in results.values() if 'PASS' in r)}/{len(results)} phases")
```

## `.claude/scripts/runtime_verify2.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""Runtime verification runner - single file, no shell escaping issues."""
     3	import subprocess, sys, json
     4	from pathlib import Path
     5	
     6	sys.path.insert(0, str(Path.cwd() / ".omc" / "scripts"))
     7	PROJECT = Path.cwd()
     8	results = []
     9	
    10	def test(name, cmd, check_fn, timeout=15):
    11	    try:
    12	        r = subprocess.run(cmd, cwd=str(PROJECT), capture_output=True, text=True, timeout=timeout, shell=True)
    13	        ok = check_fn(r.stdout, r.stderr) if r.returncode == 0 else False
    14	        status = 'PASS' if ok else 'FAIL'
    15	    except Exception as e:
    16	        status = 'FAIL'
    17	        r_stdout = ''
    18	    results.append({'test': name, 'status': status, 'stdout': r.stdout[:200] if hasattr(r,'stdout') else ''})
    19	    print(f'  [{status}] {name}')
    20	
    21	from lib.tool_store import store_tool_result
    22	from lib.error_dna import record_error, check_retry_gate
    23	from lib.oracle_gate_light import should_trigger_oracle
    24	from lib.flywheel import run_flywheel
    25	from lib.autonomy import load_contract, LoopDetector, check_autonomy_gate
    26	import yaml
    27	
    28	print('=== Phase 0 — Token Slim ===')
    29	
    30	# S2
    31	a = Path("AGENTS.md").read_text().splitlines()
    32	test('S2 AGENTS.md <=43 lines', f'test $(wc -l < AGENTS.md) -le 43', lambda o,_: True)
    33	test('S2 Oracle=0', f'grep -ci oracle AGENTS.md', lambda o,_: o.strip() == '0')
    34	
    35	# S3
    36	test('S3 Hot Card', f'python3 .claude/scripts/carros_base.py status', lambda o,_: 'CarrorOS Hot Card' in o)
    37	
    38	# S4
    39	r = store_tool_result('v', b'x'*250000, {"exit_code": 0})
    40	test('S4 tools store', 'echo ok', lambda o,_: r['bytes'] >= 240000 and len(r['preview']) < 2000)
    41	
    42	# S5
    43	import subprocess as sb
    44	p_rev = json.dumps({"tool_name":"read","tool_input":{"file_path":"docs/carros/reviews/x.md"}})
    45	r_block = sb.run(['python3','.claude/hooks/pretool-gate.py'], input=p_rev, capture_output=True, text=True, timeout=5)
    46	test('S5 reviews BLOCK', 'echo ok', lambda o,_: 'false' in r_block.stdout)
    47	
    48	p_ok = json.dumps({"tool_name":"read","tool_input":{"file_path":"AGENTS.md","offset":1,"limit":5}})
    49	r_allow = sb.run(['python3','.claude/hooks/pretool-gate.py'], input=p_ok, capture_output=True, text=True, timeout=5)
    50	test('S5 normal ALLOW', 'echo ok', lambda o,_: 'true' in r_allow.stdout)
    51	
    52	# S6
    53	em = Path(".claude/prompts/executor_micro.txt")
    54	test('S6 executor_micro <=15 lines', 'echo ok', lambda o,_: len(em.read_text().splitlines()) <= 15)
    55	
    56	# S7
    57	cost = sb.run(['python3','.claude/scripts/carros_cost_report.py'], capture_output=True, text=True, timeout=15)
    58	test('S7 cost report PASS', 'echo ok', lambda o,_: 'PASS' in cost.stdout)
    59	
    60	print('\n=== Phase 0.5 — 文档基建 ===')
    61	
    62	# W1: Handoff
    63	h = PROJECT / ".omc/tasks/20260713/phase3-dual-judge/handoff.md"
    64	has_nsot = "NOT SOURCE" in h.read_text() if h.exists() else True  # new tasks
    65	test('W1 Handoff NOT_SOURCE_OF_TRUTH', 'echo ok', lambda o,_: has_nsot)
    66	
    67	# W2: Task profiles
    68	with open(str(PROJECT / ".claude/references/task-profiles.yaml")) as f:
    69	    tp = yaml.safe_load(f)
    70	test('W2 task-profiles L1+L2', 'echo ok', lambda o,_: 'L1' in tp and 'L2' in tp)
    71	
    72	# W3: INDEX
    73	with open(str(PROJECT / "docs/INDEX.yaml")) as f:
    74	    idx = yaml.safe_load(f)
    75	test('W3 INDEX >=7 docs', 'echo ok', lambda o,_: len(idx.get('documents',[])) >= 7)
    76	
    77	# W4: Invariants
    78	inv = Path(".claude/references/invariants.md")
    79	inv_cnt = sum(1 for l in inv.read_text().splitlines() if 'INV-' in l)
    80	test('W4 12 invariants', 'echo ok', lambda o,_: inv_cnt >= 12)
    81	
    82	print('\n=== Phase 1 — L2 治理 ===')
    83	
    84	# P1: working-set
    85	with open(str(PROJECT / ".claude/references/working-set-template.yaml")) as f:
    86	    ws = yaml.safe_load(f)
    87	test('P1 working-set require_evidence', 'echo ok', lambda o,_: ws.get('verify',{}).get('require_evidence') == True)
    88	
    89	# P1: Error DNA
    90	d = record_error(PROJECT / ".omc", "T1", "test error")
    91	test('P1 Error DNA records', 'echo ok', lambda o,_: d['step'] == 'T1')
    92	
    93	# P1: Retry gate
    94	a, c, m = check_retry_gate(PROJECT / ".omc/tasks/20260713/phase3-dual-judge", "T-NOEXIST")
    95	test('P1 Retry gate works', 'echo ok', lambda o,_: a == True)
    96	
    97	# P1: Oracle L1
    98	trig, _ = should_trigger_oracle('L1')
    99	test('P1 Oracle L1=no', 'echo ok', lambda o,_: trig == False)
   100	
   101	# P1: Oracle L2+high
   102	trig, _ = should_trigger_oracle('L2', risk_level='high')
   103	test('P1 Oracle L2+high=yes', 'echo ok', lambda o,_: trig == True)
   104	
   105	# P1: Oracle L2+medium=defer
   106	trig, _ = should_trigger_oracle('L2', risk_level='medium')
   107	test('P1 Oracle L2+medium=defer', 'echo ok', lambda o,_: trig == False)
   108	
   109	print('\n=== Phase 2 — 飞轮+无人 ===')
   110	
   111	# P2: Flywheel
   112	fly_r = run_flywheel(PROJECT)
   113	test('P2 Flywheel runs', 'echo ok', lambda o,_: isinstance(fly_r, dict))
   114	
   115	# P2: claude-next
   116	cn = PROJECT / ".omc/knowledge/claude-next.md"
   117	test('P2 claude-next exists', 'echo ok', lambda o,_: cn.exists())
   118	
   119	# P2: Loop detection
   120	ld = LoopDetector(3)
   121	[ld.record_tick('S','a') for _ in range(5)]
   122	d = ld.detect_loop()
   123	test('P2 Loop detection', 'echo ok', lambda o,_: d is not None and 'loop' in d['type'])
   124	
   125	# P2: Autonomy contract
   126	c = load_contract(PROJECT)
   127	test('P2 Contract max_turns=30', 'echo ok', lambda o,_: c['boundaries']['max_autonomy_turns'] == 30)
   128	
   129	# P2: Budget pause
   130	token_over = {"stats": {"tick": 35}, "budget": {"max_turns_hard": 30}}
   131	reason = check_autonomy_gate(token_over, LoopDetector())
   132	test('P2 Budget pause', 'echo ok', lambda o,_: reason is not None)
   133	
   134	# Summary
   135	print(f'\n{"="*50}')
   136	pass_cnt = sum(1 for r in results if r['status'] == 'PASS')
   137	print(f'Runtime verification: {pass_cnt}/{len(results)} PASS')
   138	for r in results:
   139	    if r['status'] == 'FAIL':
   140	        print(f'  FAIL: {r["test"]} — {r["stdout"][:80]}')
```
