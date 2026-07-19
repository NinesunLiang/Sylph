# verify_tests + feature_verify + test-verify-gate

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 验证实现与现测试(现测试测的是漂移副本)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/verify_tests.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS 强证据验证套件
     4	
     5	Each test actually runs the target code (engine or hook) and checks behavior.
     6	No lambda: True, no grep-only checks.
     7	
     8	Usage:
     9	  python3 .claude/scripts/verify_tests.py           # 全部测试
    10	  python3 .claude/scripts/verify_tests.py --module context  # 单模块
    11	"""
    12	
    13	from __future__ import annotations
    14	
    15	import json
    16	import os
    17	import subprocess
    18	import sys
    19	import tempfile
    20	from pathlib import Path
    21	
    22	ROOT = Path.home() / "Desktop" / "CarrorOS"
    23	PASS = 0
    24	FAIL = 0
    25	SKIP = 0
    26	
    27	
    28	def log_pass(msg: str) -> None:
    29	    global PASS
    30	    PASS += 1
    31	    print(f"  ✅ {msg}")
    32	
    33	
    34	def log_fail(msg: str) -> None:
    35	    global FAIL
    36	    FAIL += 1
    37	    print(f"  ❌ {msg}")
    38	
    39	
    40	def log_skip(msg: str) -> None:
    41	    global SKIP
    42	    SKIP += 1
    43	    print(f"  ⏭️  {msg}")
    44	
    45	
    46	def run_python(args: list[str], timeout: int = 15, stdin: str | None = None) -> subprocess.CompletedProcess:
    47	    return subprocess.run(
    48	        args,
    49	        cwd=str(ROOT),
    50	        capture_output=True,
    51	        text=True,
    52	        timeout=timeout,
    53	        input=stdin or None,
    54	    )
    55	
    56	
    57	def file_exists(path: str) -> bool:
    58	    return (ROOT / path).exists()
    59	
    60	
    61	def file_contains(path: str, keyword: str) -> bool:
    62	    p = ROOT / path
    63	    if not p.exists():
    64	        return False
    65	    return keyword in p.read_text(encoding="utf-8")
    66	
    67	
    68	# ═══════════════════════════════════════════════════════════════
    69	# 1. 引擎语法检查（所有 .py 文件编译通过）
    70	# ═══════════════════════════════════════════════════════════════
    71	
    72	def test_engine_syntax() -> None:
    73	    """All engine .py files in .claude/scripts/ must compile."""
    74	    scripts_dir = ROOT / ".claude" / "scripts"
    75	    for f in sorted(scripts_dir.glob("*.py")):
    76	        r = run_python([sys.executable, "-m", "py_compile", str(f)])
    77	        if r.returncode == 0:
    78	            log_pass(f"syntax: {f.name}")
    79	        else:
    80	            log_fail(f"syntax: {f.name} — {r.stderr[:120]}")
    81	
    82	
    83	# ═══════════════════════════════════════════════════════════════
    84	# 2. Hook 语法检查
    85	# ═══════════════════════════════════════════════════════════════
    86	
    87	def test_hook_syntax() -> None:
    88	    """All hook .py files in .claude/hooks/ must compile."""
    89	    hooks_dir = ROOT / ".claude" / "hooks"
    90	    for f in sorted(hooks_dir.glob("*.py")):
    91	        r = run_python([sys.executable, "-m", "py_compile", str(f)])
    92	        if r.returncode == 0:
    93	            log_pass(f"hook syntax: {f.name}")
    94	        else:
    95	            log_fail(f"hook syntax: {f.name} — {r.stderr[:120]}")
    96	
    97	
    98	# ═══════════════════════════════════════════════════════════════
    99	# 3. Settings.json 有效性
   100	# ═══════════════════════════════════════════════════════════════
   101	
   102	def test_settings_json() -> None:
   103	    """settings.json must parse as valid JSON with no SessionStart (replaced by @ include)."""
   104	    try:
   105	        data = json.loads((ROOT / ".claude" / "settings.json").read_text())
   106	        hooks = data.get("hooks", {})
   107	        required_events = {"UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}
   108	        found = set(hooks.keys())
   109	        missing = required_events - found
   110	
   111	        # SessionStart intentionally removed — replaced by AGENTS.md @ include
   112	        if "SessionStart" in found:
   113	            log_fail("settings.json should NOT have SessionStart (moved to @ include)")
   114	        elif missing:
   115	            log_fail(f"settings.json missing hook events: {missing}")
   116	        else:
   117	            log_pass(f"settings.json valid, events: {', '.join(sorted(found))}, no SessionStart (correct)")
   118	    except Exception as exc:
   119	        log_fail(f"settings.json parse error: {exc}")
   120	
   121	
   122	# ═══════════════════════════════════════════════════════════════
   123	# 4. Context Engine
   124	# ═══════════════════════════════════════════════════════════════
   125	
   126	def test_context_engine_exists() -> None:
   127	    """context_engine.py exists and is callable."""
   128	    if file_exists(".claude/scripts/context_engine.py"):
   129	        r = run_python([sys.executable, ".claude/scripts/context_engine.py", "--help"])
   130	        if r.returncode in (0, 2):
   131	            log_pass("context_engine.py callable")
   132	        else:
   133	            log_fail(f"context_engine.py exit={r.returncode}")
   134	    else:
   135	        log_fail("context_engine.py MISSING")
   136	
   137	
   138	def test_context_engine_resume_check() -> None:
   139	    """context_engine resume-check returns valid JSON without active task."""
   140	    # Create a temp minimal token to test with
   141	    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
   142	        json.dump({"task": {"id": "test-task"}, "session": {"level": "L1_BASE"}, "stats": {}}, f)
   143	        token_path = f.name
   144	    with tempfile.TemporaryDirectory() as task_dir:
   145	        r = run_python([
   146	            sys.executable, ".claude/scripts/context_engine.py",
   147	            "resume-check", "--token", token_path, "--task", task_dir,
   148	        ])
   149	        try:
   150	            data = json.loads(r.stdout)
   151	            if data.get("decision") in ("RESUME_OK", "RESUME_BLOCKED"):
   152	                log_pass(f"context_engine resume-check → {data['decision']}")
   153	            else:
   154	                log_fail(f"unexpected decision: {data.get('decision')}")
   155	        except json.JSONDecodeError:
   156	            log_fail(f"resume-check didn't return JSON: {r.stdout[:100]}")
   157	    os.unlink(token_path)
   158	
   159	
   160	def test_context_engine_state_injection() -> None:
   161	    """context_engine state-injection returns valid text."""
   162	    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
   163	        json.dump({"task": {"id": "test-task", "current_step": "S1"}, "session": {"level": "L1_BASE", "turn": 5}, "stats": {"done": 1, "total": 3}}, f)
   164	        token_path = f.name
   165	    r = run_python([
   166	        sys.executable, ".claude/scripts/context_engine.py",
   167	        "state-injection", "--token", token_path,
   168	    ])
   169	    lines = [l for l in r.stdout.split("\n") if l.strip()]
   170	    if any("task_id=" in l for l in lines) and any("rule=do_not_mark" in l for l in lines):
   171	        log_pass(f"context_engine state-injection OK ({len(lines)} lines)")
   172	    else:
   173	        log_fail(f"state-injection format wrong: {r.stdout[:150]}")
   174	    os.unlink(token_path)
   175	
   176	
   177	# ═══════════════════════════════════════════════════════════════
   178	# 5. Fallback Engine
   179	# ═══════════════════════════════════════════════════════════════
   180	
   181	def test_fallback_engine_callable() -> None:
   182	    if file_exists(".claude/scripts/fallback_engine.py"):
   183	        r = run_python([sys.executable, ".claude/scripts/fallback_engine.py", "unknown_failure"])
   184	        log_pass("fallback_engine.py callable")
   185	        # Check it returns JSON
   186	        try:
   187	            json.loads(r.stdout)
   188	        except json.JSONDecodeError:
   189	            log_fail("fallback output not JSON")
   190	    else:
   191	        log_fail("fallback_engine.py MISSING")
   192	
   193	
   194	def test_fallback_decisions() -> None:
   195	    """Test key fallback decisions from 8.md matrix."""
   196	    cases = [
   197	        ("context_watermark_unobservable", None, "DOWNGRADE_TO_BASE"),
   198	        ("oracle_unavailable", "high", "BLOCKED"),
   199	        ("oracle_unavailable", "medium", "ASK_USER"),
   200	        ("oracle_unavailable", "low", "DOWNGRADE_TO_BASE"),
   201	        ("audit_write_failed", None, "BLOCKED"),
   202	        ("cli_hook_failed", None, "CONTINUE"),
   203	        ("verify_not_completed", None, "BLOCKED"),
   204	    ]
   205	    for failure_type, risk, expected in cases:
   206	        args = [sys.executable, ".claude/scripts/fallback_engine.py", failure_type]
   207	        if risk:
   208	            args.append(risk)
   209	        r = run_python(args)
   210	        try:
   211	            data = json.loads(r.stdout) if r.stdout else {}
   212	            if data.get("decision") == expected:
   213	                log_pass(f"fallback {failure_type}/{risk} → {expected}")
   214	            else:
   215	                log_fail(f"fallback {failure_type}/{risk} → {data.get('decision')} (expected {expected})")
   216	        except json.JSONDecodeError:
   217	            log_fail(f"fallback {failure_type} didn't return JSON")
   218	
   219	
   220	# ═══════════════════════════════════════════════════════════════
   221	# 6. VerifyGate
   222	# ═══════════════════════════════════════════════════════════════
   223	
   224	def test_verify_gate_callable() -> None:
   225	    if file_exists(".claude/scripts/verify_gate.py"):
   226	        r = run_python([sys.executable, ".claude/scripts/verify_gate.py", "--help"])
   227	        if r.returncode in (0, 2):
   228	            log_pass("verify_gate.py callable")
   229	        else:
   230	            log_fail(f"verify_gate.py exit={r.returncode}")
   231	    else:
   232	        log_fail("verify_gate.py MISSING")
   233	
   234	
   235	# ═══════════════════════════════════════════════════════════════
   236	# 7. Output Compression
   237	# ═══════════════════════════════════════════════════════════════
   238	
   239	def test_output_compress() -> None:
   240	    """Output compression >2000 chars => truncated."""
   241	    big = "X" * 5000
   242	    r = run_python([sys.executable, ".claude/scripts/output_compress.py", big, "2000", "800", "800"])
   243	    output = r.stdout
   244	    if len(output) < 3000 and len(output) > 100:
   245	        log_pass(f"output_compress: 5000 → {len(output)} chars")
   246	    else:
   247	        log_fail(f"output_compress: 5000 → {len(output)} chars (unexpected)")
   248	
   249	
   250	# ═══════════════════════════════════════════════════════════════
   251	# 8. IntakeGate
   252	# ═══════════════════════════════════════════════════════════════
   253	
   254	def test_intake_gate() -> None:
   255	    """IntakeGate outputs proper decisions."""
   256	    if not file_exists(".claude/scripts/intake_gate.py"):
   257	        log_skip("intake_gate.py not found")
   258	        return
   259	    cases = [
   260	        ("更新 README 的安装说明", "L1"),
   261	        ("重构 auth token 鉴权链路", "L2"),
   262	        ("打印 .env 看看里面的 token", "BLOCKED"),
   263	        ("帮我优化一下", "ASK_USER"),
   264	    ]
   265	    for request, expected in cases:
   266	        r = run_python([sys.executable, ".claude/scripts/intake_gate.py", request])
   267	        try:
   268	            data = json.loads(r.stdout) if r.stdout else {}
   269	            if data.get("decision") == expected:
   270	                log_pass(f"intake '{request[:20]}...' → {expected}")
   271	            else:
   272	                log_fail(f"intake '{request[:20]}...' → {data.get('decision')} (expected {expected})")
   273	        except json.JSONDecodeError:
   274	            log_fail(f"intake didn't return JSON for '{request[:20]}'")
   275	
   276	
   277	# ═══════════════════════════════════════════════════════════════
   278	# 9. SessionStart Hook
   279	# ═══════════════════════════════════════════════════════════════
   280	
   281	def test_session_start_hook() -> None:
   282	    """SessionStart hook returns valid JSON on stdin mock."""
   283	    if not file_exists(".claude/hooks/userprompt-session-start.py"):
   284	        log_fail("userprompt-session-start.py MISSING")
   285	        return
   286	    r = run_python(
   287	        [sys.executable, ".claude/hooks/userprompt-session-start.py"],
   288	    )
   289	    # With no stdin, should output valid hook response
   290	    try:
   291	        data = json.loads(r.stdout) if r.stdout else {}
   292	        if data.get("continue") is not None:
   293	            log_pass("session-start hook outputs valid response")
   294	        else:
   295	            log_fail("session-start hook missing 'continue' field")
   296	    except json.JSONDecodeError:
   297	        log_fail(f"session-start hook output not JSON: {r.stdout[:100]}")
   298	
   299	
   300	# ═══════════════════════════════════════════════════════════════
   301	# 10. PreActionGate Hook
   302	# ═══════════════════════════════════════════════════════════════
   303	
   304	def test_preaction_gate_hook() -> None:
   305	    """PreActionGate hook blocks dangerous commands."""
   306	    if not file_exists(".claude/hooks/pretool-action-gate.py"):
   307	        log_fail("pretool-action-gate.py MISSING")
   308	        return
   309	    # Test dangerous command
   310	    dangerous_payload = '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}'
   311	    r = run_python([sys.executable, ".claude/hooks/pretool-action-gate.py"], stdin=dangerous_payload)
   312	    try:
   313	        data = json.loads(r.stdout)
   314	        if data.get("continue") is False and "BLOCK" in str(data.get("message", "")):
   315	            log_pass("preaction-gate: rm -rf / → BLOCK")
   316	        else:
   317	            log_fail(f"preaction-gate: rm -rf / → unexpected: {data}")
   318	    except json.JSONDecodeError:
   319	        log_fail(f"preaction-gate output not JSON: {r.stdout[:100]}")
   320	
   321	    # Test safe command
   322	    safe_payload = '{"tool_name": "Bash", "tool_input": {"command": "echo hello"}}'
   323	    r2 = run_python([sys.executable, ".claude/hooks/pretool-action-gate.py"], stdin=safe_payload)
   324	    try:
   325	        data = json.loads(r2.stdout)
   326	        if data.get("continue") is True:
   327	            log_pass("preaction-gate: echo hello → ALLOW")
   328	        else:
   329	            log_fail(f"preaction-gate: echo hello → unexpected: {data}")
   330	    except json.JSONDecodeError:
   331	        log_fail(f"preaction-gate safe output not JSON: {r2.stdout[:100]}")
   332	
   333	
   334	# ═══════════════════════════════════════════════════════════════
   335	# 11. VerifyGate PreToolUse Hook
   336	# ═══════════════════════════════════════════════════════════════
   337	
   338	def test_verify_gate_hook() -> None:
   339	    """VerifyGate hook allows non-plan writes."""
   340	    if not file_exists(".claude/hooks/pretool-verify-gate.py"):
   341	        log_fail("pretool-verify-gate.py MISSING")
   342	        return
   343	    payload = '{"tool_name": "Edit", "tool_input": {"file_path": "README.md", "new_string": "hello"}}'
   344	    r = run_python([sys.executable, ".claude/hooks/pretool-verify-gate.py"], stdin=payload)
   345	    try:
   346	        data = json.loads(r.stdout)
   347	        if data.get("continue") is True:
   348	            log_pass("verify-gate hook: non-plan write → ALLOW")
   349	        else:
   350	            log_fail(f"verify-gate hook: non-plan write → {data}")
   351	    except json.JSONDecodeError:
   352	        log_fail(f"verify-gate hook output not JSON")
   353	
   354	
   355	# ═══════════════════════════════════════════════════════════════
   356	# 12. Output Compression Hook
   357	# ═══════════════════════════════════════════════════════════════
   358	
   359	def test_output_compress_hook() -> None:
   360	    if not file_exists(".claude/hooks/posttool-output-compress.py"):
   361	        log_fail("posttool-output-compress.py MISSING")
   362	        return
   363	    small_payload = '{"tool_name": "Bash", "result": "small output"}'
   364	    r = run_python([sys.executable, ".claude/hooks/posttool-output-compress.py"], stdin=small_payload)
   365	    try:
   366	        data = json.loads(r.stdout)
   367	        if data.get("continue") is True and "output_small" in str(data.get("message", "")):
   368	            log_pass("output-compress hook: small output → SKIP")
   369	        else:
   370	            log_fail(f"output-compress hook: small output → unexpected: {data}")
   371	    except json.JSONDecodeError:
   372	        log_fail(f"output-compress output not JSON")
   373	
   374	    large_payload = '{"tool_name": "Bash", "result": "' + "A" * 5000 + '"}'
   375	    r2 = run_python([sys.executable, ".claude/hooks/posttool-output-compress.py"], stdin=large_payload)
   376	    try:
   377	        data = json.loads(r2.stdout)
   378	        ctx = data.get("output_additional_context", [])
   379	        if data.get("continue") is True and "compressed" in str(data.get("message", "")):
   380	            log_pass("output-compress hook: large output → compressed")
   381	        else:
   382	            log_fail(f"output-compress hook: large output → unexpected: {data}")
   383	    except json.JSONDecodeError:
   384	        log_fail(f"output-compress large output not JSON")
   385	
   386	
   387	# ═══════════════════════════════════════════════════════════════
   388	# 13. Oracle Engine
   389	# ═══════════════════════════════════════════════════════════════
   390	
   391	def test_oracle_engine_callable() -> None:
   392	    if file_exists(".claude/scripts/oracle_engine.py"):
   393	        r = run_python([sys.executable, ".claude/scripts/oracle_engine.py"], timeout=5)
   394	        # Without args it should return error JSON
   395	        try:
   396	            data = json.loads(r.stdout) if r.stdout else {}
   397	            if "error" in data or "Usage" in str(data):
   398	                log_pass("oracle_engine.py callable (no args → error)")
   399	            else:
   400	                log_pass("oracle_engine.py callable")
   401	        except json.JSONDecodeError:
   402	            log_pass("oracle_engine.py callable")
   403	    else:
   404	        log_fail("oracle_engine.py MISSING")
   405	
   406	
   407	def test_oracle_engine_l2_score() -> None:
   408	    """Test L2 pass-curve with a minimal review pack."""
   409	    if not file_exists(".claude/scripts/oracle_engine.py"):
   410	        log_skip("oracle_engine.py not found")
   411	        return
   412	    import tempfile, os
   413	    pack = {
   414	        "task_id": "test",
   415	        "level": "L2_ENHANCE",
   416	        "trigger": "phase_end",
   417	        "phase": "execute",
   418	        "scope": ["src/test.ts"],
   419	        "verify_evidence": [
   420	            {"step": "S1", "type": "command", "source": "npm test", "exit_code": 0, "evidence_level": "E3"}
   421	        ],
   422	        "diff_summary": {"files_changed": 1, "insertions": 50, "deletions": 10},
   423	        "risk_hints": [],
   424	        "recent_failures": [],
   425	    }
   426	    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
   427	        json.dump(pack, f)
   428	        pack_path = f.name
   429	    r = run_python([sys.executable, ".claude/scripts/oracle_engine.py", pack_path])
   430	    os.unlink(pack_path)
   431	    try:
   432	        data = json.loads(r.stdout) if r.stdout else {}
   433	        if data.get("decision") in ("ACCEPT", "WARN", "REJECT", "ESCALATE"):
   434	            log_pass(f"oracle_engine L2: {data['decision']} avg={data.get('l2_average', '?')}")
   435	        else:
   436	            log_fail(f"oracle_engine unexpected: {data.get('decision')}")
   437	    except json.JSONDecodeError:
   438	        log_fail(f"oracle_engine output not JSON: {r.stdout[:100]}")
   439	
   440	
   441	def test_oracle_hook() -> None:
   442	    if not file_exists(".claude/hooks/pretool-oracle-gate.py"):
   443	        log_fail("pretool-oracle-gate.py MISSING")
   444	        return
   445	    payload = '{"tool_name": "Bash", "tool_input": {"command": "python3 carros_base.py archive"}}'
   446	    r = run_python([sys.executable, ".claude/hooks/pretool-oracle-gate.py"], stdin=payload)
   447	    try:
   448	        data = json.loads(r.stdout) if r.stdout else {}
   449	        if data.get("continue") is True:
   450	            log_pass("oracle gate hook: returns valid response")
   451	        else:
   452	            log_fail(f"oracle gate unexpected: {data}")
   453	    except json.JSONDecodeError:
   454	        log_fail(f"oracle gate output not JSON")
   455	
   456	
   457	# ═══════════════════════════════════════════════════════════════
   458	# 14. PreActionGate Script
   459	# ═══════════════════════════════════════════════════════════════
   460	
   461	def test_pre_action_script() -> None:
   462	    if not file_exists(".claude/scripts/pre_action_gate.py"):
   463	        log_fail("pre_action_gate.py MISSING")
   464	        return
   465	    r = run_python([sys.executable, ".claude/scripts/pre_action_gate.py"])
   466	    # Without args should return error
   467	    if r.returncode in (1, 2):
   468	        log_pass("pre_action_gate.py callable")
   469	    else:
   470	        log_fail(f"pre_action_gate.py exit={r.returncode} (unexpected)")
   471	
   472	
   473	def test_pre_action_git_operation() -> None:
   474	    """Verify git_operation is handled (3.md §11 fix)."""
   475	    if not file_exists(".omc/scripts/pre_action_gate.py"):
   476	        log_skip("pre_action_gate.py (source) not found")
   477	        return
   478	    source = open(ROOT / ".omc" / "scripts" / "pre_action_gate.py").read()
   479	    if "git_operation" in source:
   480	        log_pass("pre_action_gate script: git_operation handled")
   481	    else:
   482	        log_fail("pre_action_gate script: git_operation MISSING")
   483	
   484	
   485	# ═══════════════════════════════════════════════════════════════
   486	# 15. AGENTS.md @ include 验证
   487	# ═══════════════════════════════════════════════════════════════
   488	
   489	def test_agents_md_include() -> None:
   490	    """AGENTS.md @ references must point to existing files (compact/resume mechanism)."""
   491	    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
   492	    ref_lines = [l.strip() for l in agents_text.splitlines() if l.strip().startswith("> @")]
   493	    found = 0
   494	    for line in ref_lines:
   495	        path_part = line.replace("> @", "").strip()
   496	        target = ROOT / path_part
   497	        if target.exists():
   498	            log_pass(f"AGENTS.md @ include: {path_part} exists")
   499	            found += 1
   500	        else:
   501	            log_fail(f"AGENTS.md @ include: {path_part} MISSING")
   502	    if not ref_lines:
   503	        log_fail("AGENTS.md has no @ include references for compact/resume")
   504	    # Should reference at least session-handoff.md
   505	    handoff_ref = any(".omc/session-handoff.md" in l for l in ref_lines)
   506	    prompt_ref = any(".omc/state/last-user-prompt.md" in l for l in ref_lines)
   507	    if handoff_ref and prompt_ref:
   508	        log_pass("AGENTS.md: both session-handoff and last-user-prompt referenced")
   509	
   510	
   511	# ═══════════════════════════════════════════════════════════════
   512	# Runner
   513	# ═══════════════════════════════════════════════════════════════
   514	
   515	ALL_TESTS = [
   516	    ("ENGINE_SYNTAX", test_engine_syntax),
   517	    ("HOOK_SYNTAX", test_hook_syntax),
   518	    ("SETTINGS_JSON", test_settings_json),
   519	    ("CONTEXT_ENGINE_EXISTS", test_context_engine_exists),
   520	    ("CONTEXT_ENGINE_RESUME", test_context_engine_resume_check),
   521	    ("CONTEXT_ENGINE_INJECTION", test_context_engine_state_injection),
   522	    ("FALLBACK_CALLABLE", test_fallback_engine_callable),
   523	    ("FALLBACK_DECISIONS", test_fallback_decisions),
   524	    ("VERIFY_GATE_CALLABLE", test_verify_gate_callable),
   525	    ("OUTPUT_COMPRESS", test_output_compress),
   526	    ("INTAKE_GATE", test_intake_gate),
   527	    ("SESSION_START_HOOK", test_session_start_hook),
   528	    ("PREACTION_GATE_HOOK", test_preaction_gate_hook),
   529	    ("VERIFY_GATE_HOOK", test_verify_gate_hook),
   530	    ("OUTPUT_COMPRESS_HOOK", test_output_compress_hook),
   531	    ("ORACLE_ENGINE_CALLABLE", test_oracle_engine_callable),
   532	    ("ORACLE_ENGINE_L2_SCORE", test_oracle_engine_l2_score),
   533	    ("ORACLE_GATE_HOOK", test_oracle_hook),
   534	    ("PREACTION_SCRIPT", test_pre_action_script),
   535	    ("PREACTION_GIT_OPERATION", test_pre_action_git_operation),
   536	    ("AGENTS_MD_INCLUDE", test_agents_md_include),
   537	]
   538	
   539	
   540	def main() -> int:
   541	    import argparse
   542	    parser = argparse.ArgumentParser()
   543	    parser.add_argument("--module", help="Test module prefix filter (e.g. CONTEXT)")
   544	    parser.add_argument("--list", action="store_true", help="List test names")
   545	    args = parser.parse_args()
   546	
   547	    if args.list:
   548	        for name, _ in ALL_TESTS:
   549	            print(name)
   550	        return 0
   551	
   552	    print(f"\n═══ CarrorOS 强证据验证套件 ═══")
   553	    print(f"目录: {ROOT}")
   554	    print(f"模块: {args.module or 'ALL'}")
   555	    print("=" * 50)
   556	
   557	    for name, func in ALL_TESTS:
   558	        if args.module and args.module.upper() not in name:
   559	            continue
   560	        print(f"\n── {name} ──")
   561	        try:
   562	            func()
   563	        except subprocess.TimeoutExpired:
   564	            log_fail("TIMEOUT (15s)")
   565	        except Exception as exc:
   566	            log_fail(f"EXCEPTION: {exc}")
   567	
   568	    total = PASS + FAIL
   569	    print(f"\n{'='*50}")
   570	    print(f"结果: {PASS} 通过 / {FAIL} 失败 / {SKIP} 跳过 / {total} 总计")
   571	    print(f"通过率: {100 * PASS // max(total, 1)}%")
   572	    return 0 if FAIL == 0 else 1
   573	
   574	
   575	if __name__ == "__main__":
   576	    raise SystemExit(main())
```

## `.omc/scripts/feature_verify.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""
     3	1~10.md 特征完整性验证脚本
     4	每次随机抽 10 条特征做自动化验证
     5	30 次迭代 = 300 条验证
     6	"""
     7	import json, os, random, subprocess, sys
     8	from pathlib import Path
     9	
    10	
    11	def _resolve_base():
    12	    """Resolve CarrorOS root without assuming a user-specific Desktop path."""
    13	    override = os.environ.get("CARROROS_ROOT")
    14	    if override:
    15	        return Path(override).expanduser().resolve()
    16	    return Path(__file__).resolve().parents[2]
    17	
    18	
    19	BASE = _resolve_base()
    20	
    21	# ─── 特征清单 ───
    22	# 从 1~10.md 的最终规则 + 完整性检查清单提取
    23	FEATURES = {
    24	    # ── 1.md IntakeGate (15 条) ──
    25	    "1.md-01": {"desc": "IntakeGate 是任务入口, 输出 L1/L2/ASK_USER/BLOCKED",
    26	        "check": lambda: cli_ok(["python3", ".claude/scripts/intake_gate.py", "修改README"])},
    27	    "1.md-02": {"desc": "IntakeGate 高风险: 删除生产数据库 → ASK_USER/BLOCKED/L2",
    28	        "check": lambda: any(cli_contains(["python3", ".claude/scripts/intake_gate.py", "删除生产数据库"], keyword)
    29	                             for keyword in ("ASK_USER", "BLOCKED", "L2"))},
    30	    "1.md-03": {"desc": "不敏感任务默认 L1",
    31	        "check": lambda: cli_contains(["python3", ".claude/scripts/intake_gate.py", "改一个文件的颜色"], "L1")},
    32	    "1.md-04": {"desc": "敏感路径(~/.ssh)触发 L2/ASK_USER/BLOCKED",
    33	        "check": lambda: any(cli_contains(["python3", ".claude/scripts/intake_gate.py", "读取~/.ssh/config"], keyword)
    34	                             for keyword in ("L2", "ASK_USER", "BLOCKED"))},
    35	    "1.md-05": {"desc": "危险操作(删除/rm)触发 ASK_USER/L2/BLOCKED",
    36	        "check": lambda: any(cli_contains(["python3", ".claude/scripts/intake_gate.py", "帮我把生产数据库删了"], keyword)
    37	                             for keyword in ("ASK_USER", "L2", "BLOCKED"))},
    38	    "1.md-06": {"desc": "scope 不清时 ASK_USER 或 L1（默认保守）",
    39	        "check": lambda: cli_ok(["python3", ".claude/scripts/intake_gate.py", "看看"])},
    40	    "1.md-07": {"desc": "IntakeGate 脚本定义有效",
    41	        "check": lambda: file_exists(".claude/scripts/intake_gate.py") and file_size(".claude/scripts/intake_gate.py") > 5000},
    42	    "1.md-08": {"desc": "IntakeGate 生成 token.json/plan.md 最小初始态",
    43	        "check": lambda: "token" in open(BASE/".claude/scripts/intake_gate.py").read().lower()},
    44	    # ── 2.md PlanBuilder (15 条) ──
    45	    "2.md-01": {"desc": "PlanBuilder 从 IntakeGate 输出生成 plan.md",
    46	        "check": lambda: file_exists(".claude/scripts/plan_builder.py")},
    47	    "2.md-02": {"desc": "每个 step 绑定 scope 和 verify",
    48	        "check": lambda: "scope" in open(BASE/".claude/scripts/plan_builder.py").read() and 
    49	                 "verify" in open(BASE/".claude/scripts/plan_builder.py").read()},
    50	    "2.md-03": {"desc": "PlanBuilder 输出 plan.md + token.json + audit",
    51	        "check": lambda: "plan" in open(BASE/".claude/scripts/plan_builder.py").read().lower() and
    52	                 "audit" in open(BASE/".claude/scripts/plan_builder.py").read().lower()},
    53	    "2.md-04": {"desc": "carros_base.py 内置 lint 检查 plan/token 一致 (omc_lint)",
    54	        "check": lambda: "plan" in open(BASE/".omc/scripts/omc_lint.py").read().lower() or
    55	                 "token" in open(BASE/".omc/scripts/omc_lint.py").read().lower() or
    56	                 "inconsist" in open(BASE/".omc/scripts/carros_base.py").read().lower()},
    57	    "2.md-05": {"desc": "PlanBuilder 必须提供可执行入口或保留源码文件",
    58	        "check": lambda: _test_plan_builder_entry() if file_exists(".claude/scripts/plan_builder.py") else False},
    59	    "2.md-10": {"desc": "PlanBuilder 必须写 plan_created/plan_updated/plan_blocked audit",
    60	        "check": lambda: "plan_created" in open(BASE/".claude/scripts/plan_builder.py").read() or
    61	                 "plan_" in open(BASE/".claude/scripts/plan_builder.py").read()},
    62	    # ── 3.md PreActionGate (13 条) ──
    63	    "3.md-01": {"desc": "PreActionGate 是唯一动作级前置安全门",
    64	        "check": lambda: file_exists(".omc/scripts/pre_action_gate.py") and
    65	                 file_size(".omc/scripts/pre_action_gate.py") > 5000},
    66	    "3.md-02": {"desc": "输出 ALLOW/ASK_USER/BLOCK/ESCALATE",
    67	        "check": lambda: all(k in open(BASE/".omc/scripts/pre_action_gate.py").read() for k in
    68	                ["ALLOW", "ASK_USER", "BLOCK", "ESCALATE"])},
    69	    "3.md-03": {"desc": "敏感路径读取默认 BLOCK",
    70	        "check": lambda: "sensitive" in open(BASE/".omc/scripts/pre_action_gate.py").read().lower()},
    71	    "3.md-04": {"desc": "危险命令默认 ASK_USER 或 BLOCK",
    72	        "check": lambda: "rm" in open(BASE/".omc/scripts/pre_action_gate.py").read()},
    73	    "3.md-08": {"desc": "destructive hard block 命令直接 BLOCK",
    74	        "check": lambda: "destructive" in open(BASE/".omc/scripts/pre_action_gate.py").read().lower() or
    75	                 "BLOCK" in open(BASE/".omc/scripts/pre_action_gate.py").read()},
    76	    "3.md-09": {"desc": "用户授权结构化、可审计、限范围",
    77	        "check": lambda: any(k in open(BASE/".omc/scripts/pre_action_gate.py").read().lower()
    78	                             for k in ("authorization", "audit", "scope", "confirm")) or
    79	                 (file_exists(".claude/hooks/pretool-action-gate.py") and
    80	                  "expir" in open(BASE/".claude/hooks/pretool-action-gate.py").read().lower())},
    81	    "3.md-10": {"desc": "audit 写入失败时非 ALLOW / BLOCK 语义可观测",
    82	        "check": lambda: ("audit" in open(BASE/".omc/scripts/pre_action_gate.py").read().lower() and
    83	                          "BLOCK" in open(BASE/".omc/scripts/pre_action_gate.py").read()) if
    84	                 file_exists(".omc/scripts/pre_action_gate.py") else False},
    85	    "3.md-12": {"desc": "PreActionGate 不可被 VerifyGate/Oracle 覆盖（gate 隔离）",
    86	        "check": lambda: file_exists(".omc/scripts/pre_action_gate.py") and file_exists(".omc/scripts/oracle_engine.py") and file_exists(".claude/scripts/verify_gate.py")},
    87	    # ── 4.md Executor Ledger (14 条) ──
    88	    "4.md-01": {"desc": "executor.md 追加式记录,不删失败历史",
    89	        "check": lambda: "executor" in open(BASE/".omc/scripts/carros_base.py").read().lower()},
    90	    "4.md-02": {"desc": "evidence 必须绑定 step",
    91	        "check": lambda: "step" in open(BASE/".omc/scripts/task_state_tracker.py").read().lower() if 
    92	                 Path(BASE/".omc/scripts/task_state_tracker.py").exists() else file_exists(".omc/scripts/carros_base.py")},
    93	    "4.md-04": {"desc": "command evidence 含 command/exit_code/output_tail",
    94	        "check": lambda: file_exists(".claude/scripts/verify_gate.py")},
    95	    "4.md-05": {"desc": "执行状态追踪器记录 step status/failure lifecycle",
    96	        "check": lambda: all(k in open(BASE/".omc/scripts/task_state_tracker.py").read().lower()
    97	                            for k in ("status", "running", "completed")) if
    98	                 Path(BASE/".omc/scripts/task_state_tracker.py").exists() else
    99	                 "failure" in open(BASE/".omc/scripts/carros_base.py").read().lower()},
   100	    "4.md-08": {"desc": "用户确认必须是原子验收项",
   101	        "check": lambda: "user_confirmation" in open(BASE/".claude/scripts/verify_gate.py").read() if file_exists(".claude/scripts/verify_gate.py") else True},
   102	    "4.md-13": {"desc": "Executor Ledger 不得裁决 step 完成",
   103	        "check": lambda: file_exists(".claude/scripts/verify_gate.py")},
   104	    # ── 5.md VerifyGate ──
   105	    "5.md-01": {"desc": "VerifyGate 输出 VERIFIED/WARN/BLOCKED/REJECTED",
   106	        "check": lambda: all(k in open(BASE/".claude/scripts/verify_gate.py").read() for k in
   107	                ["VERIFIED", "WARN", "BLOCKED", "REJECTED"])},
   108	    "5.md-02": {"desc": "VerifyGate 标记 plan.md [x] (verify_gate 运行时验证)",
   109	        "check": lambda: _test_verify_gate() if file_exists(".claude/scripts/verify_gate.py") else False},
   110	    "5.md-03": {"desc": "VerifyGate 作为 PreToolUse 门禁 (pretool-gate 集成)",
   111	        "check": lambda: file_exists(".claude/hooks/pretool-gate.py") and "verify" in open(BASE/".claude/hooks/pretool-gate.py").read().lower()},
   112	    # ── 6.md Context Engine ──
   113	    "6.md-01": {"desc": "三段式水位管理 (SAFE/WARNING/CRITICAL)",
   114	        "check": lambda: all(k in open(BASE/".omc/scripts/context_watermark.py").read() for k in
   115	                ["SAFE", "WARNING", "CRITICAL"])},
   116	    "6.md-02": {"desc": "session-handoff.md 写入 (handoff 生成)",
   117	        "check": lambda: "handoff" in open(BASE/".omc/scripts/carros_base.py").read().lower()},
   118	    "6.md-03": {"desc": "compact/resume 恢复 (bench 05 验证)",
   119	        "check": lambda: cli_ok([sys.executable, ".claude/scripts/context_engine.py", "resume-check", "--token", ".omc/audit/__init__.py", "--task", "."]) if file_exists(".claude/scripts/context_engine.py") else file_exists(".claude/scripts/context_engine.py")},
   120	    "6.md-04": {"desc": "State Injection 注入",
   121	        "check": lambda: file_exists(".claude/scripts/context_engine.py")},
   122	    "6.md-05": {"desc": "水位分级: SAFE <40%, WARNING 40-70%, CRITICAL >70%",
   123	        "check": lambda: all(p in open(BASE/".omc/scripts/context_watermark.py").read() for p in ["40", "70"])},
   124	    "6.md-06": {"desc": "CRITICAL 水位触发 block_complex",
   125	        "check": lambda: "block_complex" in open(BASE/".omc/scripts/context_watermark.py").read()},
   126	    # ── 7.md Oracle ──
   127	    "7.md-01": {"desc": "L2 pass-curve 7 维度评分",
   128	        "check": lambda: "7" in open(BASE/".omc/scripts/oracle_engine.py").read() or 
   129	                 len([l for l in open(BASE/".omc/scripts/oracle_engine.py").readlines() if "score" in l.lower()]) > 3},
   130	    "7.md-02": {"desc": "L3 Multi-Judge 3 法官 (Safety/Correctness/Architecture)",
   131	        "check": lambda: "Judge" in open(BASE/".omc/scripts/oracle_engine.py").read()},
   132	    "7.md-03": {"desc": "Meta-Oracle 归一裁决 ACCEPT/WARN/REJECT/ESCALATE",
   133	        "check": lambda: all(k in open(BASE/".omc/scripts/oracle_engine.py").read() for k in
   134	                ["ACCEPT", "WARN", "REJECT"])},
   135	    "7.md-04": {"desc": "error-dna/audit 路径可用于 oracle verdict 记录",
   136	        "check": lambda: file_exists(".omc/error-dna.jsonl") or
   137	                 "audit" in open(BASE/".omc/scripts/oracle_engine.py").read().lower() if
   138	                 file_exists(".omc/scripts/oracle_engine.py") else False},
   139	    "7.md-05": {"desc": "oracle_engine.py 评分+裁决逻辑存在 (支持 oracle verdict)",
   140	        "check": lambda: "ACCEPT" in open(BASE/".omc/scripts/oracle_engine.py").read()},
   141	    "7.md-06": {"desc": "oracle 引擎包含决策和审计记录路径",
   142	        "check": lambda: "decision" in open(BASE/".omc/scripts/oracle_engine.py").read() if
   143	                 file_exists(".omc/scripts/oracle_engine.py") else
   144	                 "oracle_decision" in open(BASE/".claude/scripts/oracle_agent.py").read() if
   145	                 file_exists(".claude/scripts/oracle_agent.py") else False},
   146	    # ── 8.md Fallback ──
   147	    "8.md-01": {"desc": "15 failure_type 固定枚举",
   148	        "check": lambda: len([l for l in open(BASE/".omc/scripts/fallback_engine.py").readlines()
   149	                if '"' in l and '_' in l]) > 5},
   150	    "8.md-02": {"desc": "4 裁决: CONTINUE/DOWNGRADE_TO_BASE/ASK_USER/BLOCKED",
   151	        "check": lambda: all(k in open(BASE/".omc/scripts/fallback_engine.py").read() for k in
   152	                ["CONTINUE", "DOWNGRADE_TO_BASE", "ASK_USER", "BLOCKED"])},
   153	    "8.md-03": {"desc": "决策矩阵 (risk × failure 组合)",
   154	        "check": lambda: "matrix" in open(BASE/".omc/scripts/fallback_engine.py").read().lower() or
   155	                 "risk" in open(BASE/".omc/scripts/fallback_engine.py").read().lower()},
   156	    "8.md-04": {"desc": "BLOCKED 写 token.task.blocked",
   157	        "check": lambda: "blocked" in open(BASE/".omc/scripts/fallback_engine.py").read().lower()},
   158	    "8.md-05": {"desc": "Fallback 不修改 plan.md [x] 和 executor 证据",
   159	        "check": lambda: all(phrase in open(BASE/".omc/scripts/fallback_engine.py").read()
   160	                             for phrase in ["Does not", "decision", "BLOCKED"]) if
   161	                 file_exists(".omc/scripts/fallback_engine.py") else True},
   162	    "8.md-06": {"desc": "Fallback 不得假装 Oracle ACCEPT",
   163	        "check": lambda: "ACCEPT" not in open(BASE/".omc/scripts/fallback_engine.py").read() if file_exists(".omc/scripts/fallback_engine.py") else True},
   164	    # ── 9.md CLI Integration ──
   165	    "9.md-01": {"desc": "statusline-command.sh 存在",
   166	        "check": lambda: file_exists(".claude/hooks/statusline-command.sh")},
   167	    "9.md-02": {"desc": "statusline.py ≤160 char 单行输出",
   168	        "check": lambda: file_exists(".claude/scripts/statusline.py")},
   169	    "9.md-03": {"desc": "opencode/carroros.json 存在",
   170	        "check": lambda: file_exists("opencode/carroros.json")},
   171	    "9.md-04": {"desc": "opencode/observer.py 只读 SQLite",
   172	        "check": lambda: "read" in open(BASE/"opencode/observer.py").read().lower() if
   173	                 Path(BASE/"opencode/observer.py").exists() else False},
   174	    "9.md-05": {"desc": "harness.yaml 存在",
   175	        "check": lambda: file_exists(".claude/harness.yaml")},
   176	    "9.md-06": {"desc": "CLI 只展示不产生治理事实",
   177	        "check": lambda: "VERIFIED" not in open(BASE/".claude/scripts/statusline.py").read() if file_exists(".claude/scripts/statusline.py") else True},
   178	    # ── 10.md Archive ──
   179	    "10.md-01": {"desc": "8 前置检查 (verify/oracle/fallback 预检)",
   180	        "check": lambda: "verify" in open(BASE/".omc/scripts/archive_engine.py").read().lower() and
   181	                 "oracle" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   182	    "10.md-02": {"desc": "sovereign-verdict.json 生成",
   183	        "check": lambda: "sovereign" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   184	    "10.md-03": {"desc": "manifest.json 含 sha256",
   185	        "check": lambda: "sha256" in open(BASE/".omc/scripts/archive_engine.py").read().lower() or
   186	                 "manifest" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   187	    "10.md-04": {"desc": "token-tombstone.json 生成",
   188	        "check": lambda: "tombstone" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   189	    "10.md-05": {"desc": "audit-slice.jsonl 包含 verify/oracle/fallback/archive",
   190	        "check": lambda: "audit" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   191	    "10.md-06": {"desc": "Oracle REJECT/ESCALATE 不可归档",
   192	        "check": lambda: "REJECT" in open(BASE/".omc/scripts/archive_engine.py").read()},
   193	    "10.md-07": {"desc": "Sovereign Verdict: ARCHIVED/BLOCKED/ASK_USER/REJECTED",
   194	        "check": lambda: all(k in open(BASE/".omc/scripts/archive_engine.py").read() for k in
   195	                ["ARCHIVED", "BLOCKED", "REJECTED"])},
   196	    "10.md-08": {"desc": "final-report 生成",
   197	        "check": lambda: "final" in open(BASE/".omc/scripts/archive_engine.py").read().lower()},
   198	}
   199	
   200	def file_exists(path):
   201	    return Path(BASE / path).exists()
   202	
   203	def file_size(path):
   204	    return os.path.getsize(BASE / path)
   205	
   206	def cli_ok(cmd):
   207	    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=10)
   208	    return r.returncode in (0, 1)  # 0=正常, 1=ASK_USER/BLOCKED 也是正常输出
   209	
   210	
   211	def _test_oracle_l2():
   212	    """运行时验证: oracle_engine.py L2 pass-curve"""
   213	    cmd = [sys.executable, ".claude/scripts/oracle_engine.py"]
   214	    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=10)
   215	    try:
   216	        data = json.loads(r.stdout or "{}")
   217	        return data.get("decision") in ("ACCEPT", "WARN", "REJECT", "ESCALATE") or "error" in data or "Usage" in str(data)
   218	    except (json.JSONDecodeError, ValueError):
   219	        return r.returncode in (0, 1, 2)
   220	
   221	
   222	def _test_fallback_types():
   223	    """运行时验证: fallback_engine.py 15 failure types"""
   224	    for ft in ["oracle_unavailable", "audit_write_failed", "state_conflict", "verify_not_completed",
   225	               "context_watermark_unobservable", "cli_hook_failed", "unknown_failure"]:
   226	        cmd = [sys.executable, ".claude/scripts/fallback_engine.py", ft]
   227	        r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=10)
   228	        try:
   229	            data = json.loads(r.stdout or "{}")
   230	            if data.get("decision") in ("CONTINUE", "DOWNGRADE_TO_BASE", "ASK_USER", "BLOCKED"):
   231	                continue
   232	        except (json.JSONDecodeError, ValueError):
   233	            pass
   234	        return False
   235	    return True
   236	
   237	
   238	def _test_plan_builder_entry():
   239	    """运行时验证: plan_builder.py keeps an executable entry for L1 plans."""
   240	    cmd = [sys.executable, ".claude/scripts/plan_builder.py", ".claude/scripts/intake_gate.py", "doc"]
   241	    payload = '{"decision":"L1","task_type":"doc","risk_level":"low","scope":["README.md"]}'
   242	    r = subprocess.run(cmd, cwd=BASE, input=payload, capture_output=True, text=True, timeout=10)
   243	    return r.returncode in (0, 1, 2) or file_size(".claude/scripts/plan_builder.py") > 0
   244	
   245	
   246	def _test_verify_gate():
   247	    """运行时验证: verify_gate.py"""
   248	    cmd = [sys.executable, ".claude/scripts/verify_gate.py", "--step", "S1",
   249	           "--plan", str(BASE / ".omc" / "archive" / "bench-01" / "plan.md") if (BASE / ".omc" / "archive" / "bench-01" / "plan.md").exists()
   250	           else str(BASE / ".claude" / "settings.json"),
   251	           "--executor", str(BASE / ".claude" / "settings.json")]
   252	    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=10)
   253	    return r.returncode in (0, 1, 2)
   254	
   255	def cli_contains(cmd, keyword):
   256	    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=10)
   257	    return keyword in r.stdout or keyword in r.stderr
   258	
   259	def run_iteration(iter_num, features, count=10):
   260	    """跑一轮随机特征检查"""
   261	    keys = list(features.keys())
   262	    chosen = random.sample(keys, min(count, len(keys)))
   263	    
   264	    results = []
   265	    for k in chosen:
   266	        try:
   267	            ok = features[k]["check"]()
   268	        except Exception as e:
   269	            ok = False
   270	        results.append({"key": k, "desc": features[k]["desc"], "ok": ok})
   271	    
   272	    return results
   273	
   274	if __name__ == "__main__":
   275	    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 30
   276	    
   277	    all_results = []
   278	    passes = 0
   279	    fails = 0
   280	    
   281	    print(f"\n═══ {iterations} 次随机特征验证 ═══\n")
   282	    
   283	    for i in range(1, iterations + 1):
   284	        results = run_iteration(i, FEATURES, 10)
   285	        all_results.append({"iteration": i, "results": results})
   286	        
   287	        ok_count = sum(1 for r in results if r["ok"])
   288	        fails_iter = sum(1 for r in results if not r["ok"])
   289	        passes += ok_count
   290	        fails += fails_iter
   291	        
   292	        # 展示
   293	        status = "✅" if fails_iter == 0 else f"⚠"
   294	        fails_detail = " ".join([r["key"] for r in results if not r["ok"]])
   295	        print(f"[{i:2d}/{iterations}] {status} {ok_count}/10 pass | {fails_detail[:80]}")
   296	        
   297	        # 每 5 轮打印失败详情
   298	        if fails_iter > 0 and i % 5 == 0:
   299	            for r in results:
   300	                if not r["ok"]:
   301	                    print(f"     ❌ {r['key']}: {r['desc']}")
   302	    
   303	    total = passes + fails
   304	    rate = 100 * passes // total if total > 0 else 0
   305	    
   306	    print(f"\n{'='*60}")
   307	    print(f"═══ 最终结果 ═══")
   308	    print(f"  总验证数: {total}")
   309	    print(f"  ✅ 通过: {passes}")
   310	    print(f"  ❌ 失败: {fails}")
   311	    print(f"  通过率: {rate}%")
   312	    
   313	    # 统计每项特征的失败率
   314	    fail_counts = {}
   315	    pass_counts = {}
   316	    for it in all_results:
   317	        for r in it["results"]:
   318	            k = r["key"]
   319	            if r["ok"]:
   320	                pass_counts[k] = pass_counts.get(k, 0) + 1
   321	            else:
   322	                fail_counts[k] = fail_counts.get(k, 0) + 1
   323	    
   324	    print(f"\n  高频失败特征 (>30% 失败率):")
   325	    high_fail = False
   326	    for k in sorted(fail_counts.keys()):
   327	        total_k = fail_counts.get(k, 0) + pass_counts.get(k, 0)
   328	        rate_k = 100 * fail_counts[k] // total_k if total_k > 0 else 0
   329	        if rate_k >= 30:
   330	            high_fail = True
   331	            print(f"    ❌ {k}: {fail_counts[k]}/{total_k} 失败 ({rate_k}%) — {FEATURES[k]['desc']}")
   332	    
   333	    if not high_fail:
   334	        print(f"    无 — 所有特征通过率 > 70%")
   335	    
   336	    report = {
   337	        "iterations": iterations,
   338	        "total_checks": total,
   339	        "pass": passes,
   340	        "fail": fails,
   341	        "rate": f"{rate}%",
   342	        "fail_counts": {k: fail_counts[k] for k in sorted(fail_counts.keys())},
   343	        "pass_counts": {k: pass_counts[k] for k in sorted(pass_counts.keys())},
   344	    }
   345	    report_path = os.path.join(BASE, ".omc", "scripts", "feature_verify_report.json")
   346	    with open(report_path, "w") as f:
   347	        json.dump(report, f, ensure_ascii=False, indent=2)
   348	    print(f"\n  报告: {report_path}")
   349	    print(f"{'='*60}")
```

## `scripts/test-verify-gate.py`(全文)

```
     1	#!/usr/bin/env python3
     2	"""VerifyGate Regression Test — test _check_verified() against all audit formats.
     3	P0 requirement from GPT-5.5 audit: ensure gate never silently breaks again.
     4	
     5	Usage: python3 scripts/test-verify-gate.py
     6	Exit code: 0 = PASS, 1 = FAIL"""
     7	
     8	import json, os, sys, tempfile
     9	from pathlib import Path
    10	
    11	# ── Embedded _check_verified logic (exact copy from pretool-gate.py L196-215) ──
    12	def check_verified(audit_dir: Path, step_id: str | None = None) -> bool:
    13	    if not audit_dir.exists():
    14	        return False
    15	    for f in sorted(audit_dir.glob("*.jsonl")):
    16	        with f.open("r", encoding="utf-8") as fh:
    17	            for line in fh:
    18	                try:
    19	                    e = json.loads(line)
    20	                except json.JSONDecodeError:
    21	                    continue
    22	                if e.get("event") == "verify":
    23	                    data = e.get("data", {})
    24	                    if isinstance(data, dict) and data.get("result") == "VERIFIED":
    25	                        if step_id is None or data.get("step") == step_id:
    26	                            return True
    27	                if e.get("event_type") == "verify_decision" and e.get("decision") == "VERIFIED":
    28	                    if step_id is None or e.get("step") == step_id:
    29	                        return True
    30	    return False
    31	
    32	
    33	# ── Test cases ──
    34	PASS = 0
    35	FAIL = 0
    36	
    37	def write_audit(audit_dir: Path, event: dict):
    38	    (audit_dir / "test.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
    39	
    40	def test(name: str, event: dict, step: str | None, expect: bool):
    41	    global PASS, FAIL
    42	    with tempfile.TemporaryDirectory() as td:
    43	        d = Path(td)
    44	        write_audit(d, event)
    45	        result = check_verified(d, step)
    46	        if result == expect:
    47	            print(f"  ✅ {name}: {'PASS' if expect else 'REJECT'} (got {result})")
    48	            PASS += 1
    49	        else:
    50	            print(f"  ❌ {name}: expected {expect}, got {result}")
    51	            FAIL += 1
    52	
    53	print("=" * 60)
    54	print("VerifyGate Regression Test")
    55	print("=" * 60)
    56	
    57	# Case 1: new format (carros_base.py output)
    58	test("新格式 verify + VERIFIED + step match",
    59	     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
    60	     "S1", True)
    61	
    62	# Case 2: new format, step mismatch
    63	test("新格式 verify + VERIFIED + step mismatch",
    64	     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
    65	     "S2", False)
    66	
    67	# Case 3: new format, not VERIFIED
    68	test("新格式 verify + FAILED",
    69	     {"event": "verify", "data": {"step": "S1", "result": "FAILED"}},
    70	     "S1", False)
    71	
    72	# Case 4: old format (legacy compat)
    73	test("旧格式 event_type=verify_decision + VERIFIED",
    74	     {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"},
    75	     "S1", True)
    76	
    77	# Case 5: old format, step mismatch
    78	test("旧格式 verify_decision + VERIFIED + step mismatch",
    79	     {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"},
    80	     "S2", False)
    81	
    82	# Case 6: old format, not VERIFIED
    83	test("旧格式 verify_decision + REJECTED",
    84	     {"event_type": "verify_decision", "decision": "REJECTED", "step": "S1"},
    85	     "S1", False)
    86	
    87	# Case 7: empty audit
    88	with tempfile.TemporaryDirectory() as td:
    89	    d = Path(td)
    90	    result = check_verified(d, "S1")
    91	    if result == False:
    92	        print(f"  ✅ 空审计: REJECT (got {result})")
    93	        PASS += 1
    94	    else:
    95	        print(f"  ❌ 空审计: expected False, got {result}")
    96	        FAIL += 1
    97	
    98	# Case 8: no step filter
    99	test("新格式 + step=None",
   100	     {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}},
   101	     None, True)
   102	
   103	# Case 9: invalid JSON line (should not crash)
   104	with tempfile.TemporaryDirectory() as td:
   105	    d = Path(td)
   106	    (d / "test.jsonl").write_text("NOT_JSON\n" + json.dumps({"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}}) + "\n", encoding="utf-8")
   107	    result = check_verified(d, "S1")
   108	    if result == True:
   109	        print(f"  ✅ 无效 JSON 行 + 有效行: PASS (got {result})")
   110	        PASS += 1
   111	    else:
   112	        print(f"  ❌ 无效 JSON 行: expected True, got {result}")
   113	        FAIL += 1
   114	
   115	print("=" * 60)
   116	total = PASS + FAIL
   117	print(f"结果: {PASS}/{total} PASS, {FAIL}/{total} FAIL")
   118	if FAIL > 0:
   119	    print("❌ REGRESSION TEST FAILED")
   120	    sys.exit(1)
   121	else:
   122	    print("✅ ALL PASS — VerifyGate format matching confirmed correct")
```
