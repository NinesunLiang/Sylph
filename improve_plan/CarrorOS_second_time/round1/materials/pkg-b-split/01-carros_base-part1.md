# carros_base.py [1/4]

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | token CAS 助手/audit/cmd_init(第 1-588 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/scripts/carros_base.py` 第 1-588 行

```python
     1	#!/usr/bin/env python3
     2	"""
     3	carros_base.py — CarrorOS Base 核心状态系统
     4	
     5	L1 Workflow: Plan → Step → Verify → Archive
     6	
     7	Usage:
     8	    python3 .claude/scripts/carros_base.py init --task-id TASK_ID [--step S1 [S2 ...]] [--level L1|L2]
     9	    python3 .claude/scripts/carros_base.py status
    10	    python3 .claude/scripts/carros_base.py tick
    11	    python3 .claude/scripts/carros_base.py report              # 生成 final-report.md
    12	    python3 .claude/scripts/carros_base.py verify [--step S1]
    13	    python3 .claude/scripts/carros_base.py clarify --title "任务名"
    14	    python3 .claude/scripts/carros_base.py verify [--step S1]
    15	    python3 .claude/scripts/carros_base.py archive [--force]
    16	    python3 .claude/scripts/carros_base.py bench [scene]
    17	    python3 .claude/scripts/carros_base.py lint [path]
    18	    python3 .claude/scripts/carros_base.py help
    19	
    20	Exit codes: 0 = ok, 1 = warnings, 2 = errors
    21	"""
    22	
    23	import fcntl
    24	import json
    25	import os
    26	import re
    27	import sys
    28	from datetime import datetime, timezone
    29	from pathlib import Path
    30	
    31	# ─── Dependencies: sibling modules ───
    32	_hook_dir = Path(__file__).parent
    33	_omc_scripts = str(_hook_dir)
    34	if _omc_scripts not in sys.path:
    35	    sys.path.insert(0, _omc_scripts)
    36	
    37	try:
    38	    import omc_lint
    39	except ImportError:
    40	    omc_lint = None
    41	
    42	try:
    43	    import carros_utils
    44	except ImportError:
    45	    carros_utils = None
    46	
    47	try:
    48	    import task_state_tracker as tst
    49	except ImportError:
    50	    tst = None
    51	
    52	try:
    53	    import goal_state_machine as gsm
    54	    from goal_state_machine import GoalMachine, GoalError
    55	except ImportError:
    56	    gsm = None
    57	    GoalMachine = None
    58	    GoalError = Exception
    59	
    60	try:
    61	    import task_planner
    62	except ImportError:
    63	    task_planner = None
    64	
    65	try:
    66	    import sub_agent_manager as sam
    67	except ImportError:
    68	    sam = None
    69	
    70	# ─── Paths (cross-platform: pathlib) ───
    71	# .claude/        → 可复用资产（hooks, scripts, reference）
    72	# .omc/tokens/    → 任务令牌（单 json 文件）
    73	# .omc/tasks/     → 任务文档系统（research/plan/executor + sub_task/ + state/）
    74	_SCRIPT_DIR = Path(__file__).resolve().parent
    75	if (_SCRIPT_DIR / ".." / ".." / ".omc").resolve().exists():
    76	    # Script is in .claude/scripts/ -> PROJECT_ROOT is grandparent
    77	    PROJECT_ROOT = (_SCRIPT_DIR / ".." / "..").resolve()
    78	elif (_SCRIPT_DIR / ".." / ".omc").resolve().exists():
    79	    # Script is in .omc/scripts/ -> PROJECT_ROOT is parent
    80	    PROJECT_ROOT = (_SCRIPT_DIR / "..").resolve()
    81	else:
    82	    PROJECT_ROOT = Path.cwd()
    83	OMC_ROOT = PROJECT_ROOT / ".omc"
    84	OMC_TOKENS = OMC_ROOT / "tokens"
    85	OMC_TASKS = OMC_ROOT / "tasks"
    86	
    87	# 这些在 init 时根据 task_id + date 动态计算
    88	TOKEN_PATH = None  # .omc/tokens/{date}/{task_id}.json
    89	TASK_DIR = None    # .omc/tasks/{date}/{task_id}/
    90	PLAN_PATH = None
    91	EXECUTOR_PATH = None
    92	RESEARCH_PATH = None
    93	SUB_TASK_DIR = None
    94	STATE_DIR = None
    95	HANDOFF_PATH = None
    96	AUDIT_DIR = None
    97	
    98	_SCHEMA_VERSION = "v1.0"
    99	
   100	
   101	def _get_date_str():
   102	    return datetime.now(timezone.utc).strftime("%Y%m%d")
   103	
   104	
   105	def _init_task_paths(task_id=None, task_dir=None):
   106	    """根据 task_id、日期和可选的自定义 task_dir 初始化所有路径"""
   107	    date_str = _get_date_str()
   108	    tid = task_id or "unnamed"
   109	    global TOKEN_PATH, TASK_DIR, PLAN_PATH, EXECUTOR_PATH, RESEARCH_PATH
   110	    global SUB_TASK_DIR, STATE_DIR, HANDOFF_PATH, AUDIT_DIR
   111	    TOKEN_PATH = OMC_TOKENS / date_str / f"{tid}.json"
   112	    if task_dir:
   113	        TASK_DIR = Path(task_dir)
   114	    else:
   115	        TASK_DIR = OMC_TASKS / date_str / tid
   116	    PLAN_PATH = TASK_DIR / "plan.md"
   117	    EXECUTOR_PATH = TASK_DIR / "executor.md"
   118	    RESEARCH_PATH = TASK_DIR / "research.md"
   119	    SUB_TASK_DIR = TASK_DIR / "sub_task"
   120	    STATE_DIR = TASK_DIR / "state"
   121	    HANDOFF_PATH = Path(".omc/session-handoff.md")
   122	    AUDIT_DIR = STATE_DIR / "audit"
   123	
   124	
   125	def _init_paths_from_token(token, found_path):
   126	    """跨天恢复：用 _find_latest_token 找到的实际路径初始化。
   127	
   128	    修复跨天 bug：_init_task_paths 按今天日期推导路径，token 在昨天目录时
   129	    导致 "No active task"。found_path 是 token 的真实落盘路径。
   130	    """
   131	    _init_task_paths(
   132	        task_id=token.get("session", {}).get("id", "unknown"),
   133	        task_dir=token.get("task_dir") or None,
   134	    )
   135	    global TOKEN_PATH
   136	    TOKEN_PATH = Path(found_path)
   137	
   138	# ─── ANSI helpers ───
   139	def _green(s): return f"\033[32m{s}\033[0m"
   140	def _yellow(s): return f"\033[33m{s}\033[0m"
   141	def _red(s): return f"\033[31m{s}\033[0m"
   142	def _bold(s): return f"\033[1m{s}\033[0m"
   143	
   144	# ═══════════════════════════════════════════
   145	# Token helpers
   146	# ═══════════════════════════════════════════
   147	
   148	def _default_token(task_id=None, level="L1", steps=None):
   149	    now = datetime.now(timezone.utc)
   150	    suffix = now.strftime("%Y%m%d")
   151	    tid = task_id or f"sess_{suffix}_0000"
   152	    if steps is None:
   153	        steps = ["S1"]
   154	    return {
   155	        "schema_version": _SCHEMA_VERSION,
   156	        "revision": 0,
   157	        "session": {
   158	            "id": tid,
   159	            "level": level,
   160	            "created_at": now.isoformat(),
   161	            "updated_at": now.isoformat(),
   162	        },
   163	        "task_dir": str(TASK_DIR) if TASK_DIR else "",
   164	        "status": "active",
   165	        "task": {
   166	            "current_step": steps[0] if steps else "S1",
   167	            "status": "active",
   168	            "blocked": None,
   169	        },
   170	        "stats": {
   171	            "done": 0,
   172	            "total": len(steps),
   173	            "tick": 0,
   174	        },
   175	    }
   176	
   177	
   178	def _load_token(path=None):
   179	    p = Path(path) if path else TOKEN_PATH
   180	    if p and p.exists():
   181	        try:
   182	            return json.loads(p.read_text())
   183	        except (json.JSONDecodeError, OSError):
   184	            return None
   185	    return None
   186	
   187	
   188	class CASConflict(RuntimeError):
   189	    """Raised when strict token CAS detects a stale expected revision."""
   190	
   191	    def __init__(self, expected_revision, current_revision):
   192	        self.expected_revision = expected_revision
   193	        self.current_revision = current_revision
   194	        super().__init__(
   195	            f"CAS_CONFLICT expected_revision={expected_revision} current_revision={current_revision}"
   196	        )
   197	
   198	
   199	def _save_token(token, path=None, expected_revision=None):
   200	    p = Path(path) if path else TOKEN_PATH
   201	    if p is None:
   202	        raise ValueError("TOKEN_PATH is not initialized")
   203	    p.parent.mkdir(parents=True, exist_ok=True)
   204	    lock_path = p.with_suffix(p.suffix + ".lock")
   205	    tmp_path = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")
   206	
   207	    with lock_path.open("a+") as lock_file:
   208	        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
   209	        try:
   210	            token.setdefault("session", {})["updated_at"] = datetime.now(timezone.utc).isoformat()
   211	
   212	            if expected_revision is not None:
   213	                current = _load_token(p) if p.exists() else None
   214	                current_revision = current.get("revision", 0) if isinstance(current, dict) else 0
   215	                if current_revision != expected_revision:
   216	                    raise CASConflict(expected_revision, current_revision)
   217	                token["revision"] = current_revision + 1
   218	            else:
   219	                token["revision"] = token.get("revision", 0) + 1  # legacy monotonic increment
   220	
   221	            data = json.dumps(token, indent=2, ensure_ascii=False) + "\n"
   222	            with tmp_path.open("w", encoding="utf-8") as f:
   223	                f.write(data)
   224	                f.flush()
   225	                os.fsync(f.fileno())
   226	            os.replace(tmp_path, p)
   227	        finally:
   228	            if tmp_path.exists():
   229	                tmp_path.unlink(missing_ok=True)
   230	            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
   231	
   232	
   233	def now_iso():
   234	    return carros_utils.now_iso() if carros_utils else datetime.now(timezone.utc).replace(microsecond=0).isoformat()
   235	
   236	
   237	def _write_handoff(token, plan_summary=None):
   238	    """写入 Resume Capsule（NOT_SOURCE_OF_TRUTH）— 委托 handoff_writer"""
   239	    try:
   240	        import lib.handoff_writer as hw
   241	        tid = token.get("session", {}).get("id", "unknown")
   242	        hw.write_handoff(TASK_DIR, tid, token, PLAN_PATH)
   243	    except (ImportError, Exception) as e:
   244	        pass  # fallback → 旧版 inline
   245	    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
   246	    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
   247	    done = token.get("stats", {}).get("done", 0)
   248	    total = token.get("stats", {}).get("total", 0)
   249	    current = token.get("task", {}).get("current_step", "?")
   250	    steps_summary = f"  current_step: {current} ({done}/{total})"
   251	    plan = ""
   252	    if PLAN_PATH.exists():
   253	        plan = PLAN_PATH.read_text()[:300]
   254	    content = (
   255	        f"# Session Handoff: {token.get('session', {}).get('id', 'unknown')}\n"
   256	        f"\n"
   257	        f"**Updated:** {now}\n"
   258	        f"**Level:** {token.get('session', {}).get('level', '?')}\n"
   259	        f"**Progress:** {done}/{total} steps\n"
   260	        f"\n"
   261	        f"## Steps\n"
   262	        f"{steps_summary}\n"
   263	        f"\n"
   264	        f"## Plan (condensed)\n"
   265	        f"{plan}\n"
   266	        f"\n"
   267	        f"---\n"
   268	        f"_Auto-generated by carros_base.py_\n"
   269	    )
   270	    HANDOFF_PATH.write_text(content)
   271	
   272	
   273	# ═══════════════════════════════════════════
   274	# Plan / Executor helpers
   275	# ═══════════════════════════════════════════
   276	
   277	def _write_default_plan(steps=None):
   278	    """创建默认 plan.md 模板"""
   279	    if steps is None:
   280	        steps = ["S1"]
   281	    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
   282	    lines = ["# Plan\n", "", "## Goal\n\n", "## Scope\n\n"]
   283	    lines.append("## Steps\n")
   284	    for s in steps:
   285	        lines.append(f"- [ ] {s}: \n")
   286	    lines.append("\n## Verify\n")
   287	    for s in steps:
   288	        lines.append(f"- {s}: \n")
   289	    lines.append("\n---\n")
   290	    lines.append("> 冻结规则：不改 scope、不改 step 顺序、不改 verify 条件。\n")
   291	    PLAN_PATH.write_text("".join(lines))
   292	
   293	
   294	def _write_default_executor():
   295	    """创建空 executor.md 证据账簿"""
   296	    EXECUTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
   297	    content = """# Executor Evidence Ledger
   298	
   299	> schema_version: v1.0
   300	> 每步必须包含标准 evidence block。
   301	
   302	## S1
   303	
   304	**证据块：**
   305	```
   306	- action:
   307	- file:
   308	- command:
   309	- output:
   310	- status: [PASS/FAIL]
   311	```
   312	
   313	---
   314	"""
   315	    EXECUTOR_PATH.write_text(content)
   316	
   317	
   318	def _write_default_research():
   319	    """创建 research.md — 子任务也可引用 src.md"""
   320	    RESEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
   321	    content = """# Research
   322	
   323	> 事实层：技术决策、架构边界、参考来源
   324	
   325	## 背景
   326	
   327	## 约束
   328	
   329	## 已知信息
   330	"""
   331	    RESEARCH_PATH.write_text(content)
   332	
   333	
   334	def _init_task_dirs():
   335	    """初始化任务子目录：sub_task/ + state/ + state/audit + artifacts/"""
   336	    for d in [SUB_TASK_DIR, STATE_DIR, AUDIT_DIR]:
   337	        d.mkdir(parents=True, exist_ok=True)
   338	    # artifacts/ for tool store
   339	    artifacts_dir = TASK_DIR / "artifacts" if TASK_DIR else None
   340	    if artifacts_dir:
   341	        artifacts_dir.mkdir(parents=True, exist_ok=True)
   342	    # evidence.jsonl for L2+
   343	    if TASK_DIR:
   344	        evidence_path = TASK_DIR / "evidence.jsonl"
   345	        if not evidence_path.exists():
   346	            evidence_path.touch()
   347	    # working-set.yaml for L2+
   348	    if TASK_DIR:
   349	        ws_path = TASK_DIR / "working-set.yaml"
   350	        if not ws_path.exists():
   351	            ws_template = PROJECT_ROOT / ".claude/references/working-set-template.yaml"
   352	            if ws_template.exists():
   353	                ws_path.write_text(ws_template.read_text(encoding="utf-8"))
   354	
   355	
   356	def _inject_plan_step(step_id):
   357	    """为 plan.md 补充 step，当 step 不在已有列表时追加"""
   358	    if not PLAN_PATH.exists():
   359	        _write_default_plan([step_id])
   360	        return
   361	    plan = PLAN_PATH.read_text()
   362	    pattern = r"- \[ \] " + re.escape(step_id) + r":"
   363	    if re.search(pattern, plan):
   364	        return  # already exists
   365	    # append before the last line (freeze note)
   366	    lines = plan.rstrip().split("\n")
   367	    insert_idx = len(lines)
   368	    for i, line in enumerate(lines):
   369	        if line.startswith("## Verify"):
   370	            insert_idx = i
   371	            break
   372	    lines.insert(insert_idx, f"- [ ] {step_id}: ")
   373	    lines.insert(insert_idx + 1, "")
   374	    PLAN_PATH.write_text("\n".join(lines))
   375	
   376	
   377	# ═══════════════════════════════════════════
   378	# Audit helpers
   379	# ═══════════════════════════════════════════
   380	
   381	def _write_audit(event_type, data, fallback=False):
   382	    """追加审计事件到当天 JSONL — 委托 carros_utils"""
   383	    if carros_utils:
   384	        # 如果 AUDIT_DIR 是 None 但 fallback=True，直接写本地
   385	        ad = AUDIT_DIR
   386	        if ad is None and fallback:
   387	            ad = OMC_ROOT / "state" / "audit"
   388	        if ad is not None:
   389	            carros_utils.write_audit(ad, event_type, data, _SCHEMA_VERSION)
   390	            return
   391	    # fallback — inline
   392	    if AUDIT_DIR is None and fallback:
   393	        ad = OMC_ROOT / "state" / "audit"
   394	    else:
   395	        ad = AUDIT_DIR
   396	    if ad is None:
   397	        return  # 无法写 audit
   398	    ad.mkdir(parents=True, exist_ok=True)
   399	    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
   400	    audit_file = ad / f"{date_str}.jsonl"
   401	    record = {
   402	        "schema_version": _SCHEMA_VERSION,
   403	        "ts": datetime.now(timezone.utc).isoformat(),
   404	        "event": event_type,
   405	        "data": data,
   406	    }
   407	    with open(audit_file, "a") as f:
   408	        f.write(json.dumps(record, ensure_ascii=False) + "\n")
   409	
   410	
   411	# ═══════════════════════════════════════════
   412	# Commands
   413	# ═══════════════════════════════════════════
   414	
   415	def _run_plan_builder(intake_decision, user_request, task_id, feature=None):
   416	    """调用 PlanBuilder 生成 plan.md + 更新 token.json + 写 audit"""
   417	    import subprocess as sb
   418	    import tempfile
   419	
   420	    # 暂存 IntakeDecision JSON
   421	    intake_json = json.dumps(intake_decision, ensure_ascii=False)
   422	    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
   423	        f.write(intake_json)
   424	        intake_path = f.name
   425	
   426	    try:
   427	        plan_builder = _hook_dir / "plan_builder.py"
   428	        if not plan_builder.exists():
   429	            return None, "plan_builder.py not found"
   430	
   431	        # 将 token_path 作为环境变量传给 plan_builder
   432	        env = os.environ.copy()
   433	        env["CARROROS_TOKEN_PATH"] = str(TOKEN_PATH) if TOKEN_PATH else ""
   434	
   435	        cmd = [sys.executable, str(plan_builder), intake_path, user_request, task_id]
   436	        if feature:
   437	            cmd.append(feature)
   438	
   439	        result = sb.run(cmd, capture_output=True, text=True, timeout=15, env=env)
   440	        if result.returncode != 0:
   441	            return None, result.stderr or "plan_builder failed"
   442	
   443	        # PlanBuilder 已写入 plan.md + token.json + audit
   444	        return result.stdout, None
   445	    finally:
   446	        os.unlink(intake_path)
   447	
   448	
   449	def cmd_auto_init(steps=None, target=None):
   450	    """自动初始化模式 — 不要求 task_id，根据当前上下文自动推导。
   451	
   452	    用于 PretoolUse hook 自动 init 场景：检测到无 token 写操作时，
   453	    自动生成 token + task 文档，不阻断 agent 工作流。
   454	
   455	    task_id 格式：auto_{ts}_{target_file_hash_short}
   456	    scope 自动推导：从写操作的目标文件路径
   457	    """
   458	    import hashlib
   459	    now = datetime.now(timezone.utc)
   460	    ts = now.strftime("%H%M%S")
   461	    if target:
   462	        h = hashlib.md5(target.encode()).hexdigest()[:6]
   463	        tid = f"auto_{h}_{ts}"
   464	    else:
   465	        tid = f"auto_{ts}"
   466	    if steps is None:
   467	        steps = ["S1"]
   468	    _init_task_paths(task_id=tid)
   469	    token = _default_token(task_id=tid, level="L1", steps=steps)
   470	    # 如果提供了 target，写入 scope
   471	    if target:
   472	        token["scope"] = [target]
   473	    _save_token(token)
   474	    _write_default_plan(steps=steps)
   475	    _write_default_executor()
   476	    _write_default_research()
   477	    _init_task_dirs()
   478	    _write_handoff(_load_token() or token)
   479	    print(f"Auto-init complete: {tid}")
   480	    _write_audit("auto_init", {
   481	        "task_id": tid,
   482	        "target": target,
   483	        "reason": "no_active_token",
   484	    }, fallback=True)
   485	    return 0
   486	
   487	
   488	def cmd_init(task_id, level="L1", steps=None, user_request=None, task_dir=None, feature=None):
   489	    """初始化任务 — IntakeGate 分级 → PlanBuilder 生成冻结计划"""
   490	    _init_task_paths(task_id=task_id, task_dir=task_dir)
   491	
   492	    intake_decision_data = None
   493	
   494	    # IntakeGate 前置分级（如有 user_request）
   495	    if user_request:
   496	        try:
   497	            import subprocess
   498	            intake_script = _hook_dir / "intake_gate.py"
   499	            if intake_script.exists():
   500	                cmd = [sys.executable, str(intake_script), user_request]
   501	                if level in ("L2_ENHANCE", "L2"):
   502	                    cmd.append("--enhance-available")
   503	                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
   504	                if result.returncode in (0, 1):
   505	                    try:
   506	                        intake = json.loads(result.stdout)
   507	                        decision = intake["decision"]
   508	                        print(f"   IntakeGate: {decision} (risk={intake['risk_level']})")
   509	                        for r in intake.get("reasons", []):
   510	                            print(f"     reason: {r}")
   511	
   512	                        if decision == "BLOCKED":
   513	                            print(_red(f"❌ BLOCKED: {intake['next_action']}"))
   514	                            return 2
   515	                        elif decision == "ASK_USER":
   516	                            print(_yellow(f"⚠  ASK_USER: {intake['next_action']}"))
   517	                            for c in intake.get("required_confirmations", []):
   518	                                print(f"     ⚠ 确认: {c}")
   519	                            print(_yellow("等待用户补充信息后重新执行 init"))
   520	                            # 仍然生成 plan draft 供参考
   521	                            intake_decision_data = intake
   522	                        else:
   523	                            # L1 / L2 — 正常走 PlanBuilder
   524	                            intake_decision_data = intake
   525	                    except (json.JSONDecodeError, KeyError) as e:
   526	                        print(_yellow(f"   ⚠ IntakeGate parse warning: {e}"))
   527	        except subprocess.TimeoutExpired:
   528	            print(_yellow("   ⚠ IntakeGate timed out (10s), continuing with default level"))
   529	        except Exception:
   530	            pass
   531	
   532	    # 将其他 active token 标记为 archived（避免多 token 冲突）
   533	    archived_count = 0
   534	    for f in sorted(OMC_TOKENS.rglob("*.json")):
   535	        try:
   536	            t = json.loads(f.read_text())
   537	            if t.get("status") == "active":
   538	                t["status"] = "archived"
   539	                f.write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
   540	                archived_count += 1
   541	        except (json.JSONDecodeError, OSError):
   542	            continue
   543	    if archived_count > 0:
   544	        print(f"   Archived previous tokens: {archived_count} total")
   545	
   546	    # ── PlanBuilder 生成冻结计划 ──
   547	    if intake_decision_data:
   548	        plan_md_output, pb_err = _run_plan_builder(intake_decision_data, user_request, task_id, feature)
   549	        if pb_err:
   550	            print(_yellow(f"   ⚠ PlanBuilder warning: {pb_err}"))
   551	            # fallback — 使用旧方式
   552	            token = _default_token(task_id=task_id, level=level, steps=steps)
   553	            _save_token(token)
   554	            _write_default_plan(steps=steps)
   555	            _write_default_executor()
   556	            _write_default_research()
   557	        else:
   558	            print(_green(f"   PlanBuilder: plan.md + token generated"))
   559	            # plan_builder.py 已写入 plan.md + .omc/state/token.json + audit
   560	            # 但还需要创建 task dirs 和 executor.md/research.md/handoff
   561	            _write_default_executor()
   562	            _write_default_research()
   563	    else:
   564	        # 无 user_request 或 intake 失败 — 使用旧方式
   565	        token = _default_token(task_id=task_id, level=level, steps=steps)
   566	        _save_token(token)
   567	        _write_default_plan(steps=steps)
   568	        _write_default_executor()
   569	        _write_default_research()
   570	
   571	    _init_task_dirs()
   572	    _write_handoff(_load_token() or _default_token(task_id=task_id, level=level, steps=steps))
   573	    print(_green(f"✅ Initialized: {task_id}"))
   574	    # 从 token 读取最终信息
   575	    loaded = _load_token()
   576	    if loaded:
   577	        total = loaded.get("stats", {}).get("total", 0)
   578	        task_blocked = loaded.get("task", {}).get("blocked")
   579	        if task_blocked:
   580	            print(f"   Status: {loaded.get('task', {}).get('status', 'unknown')}")
   581	        print(f"   Steps: {total} total")
   582	    print(f"   Token: {TOKEN_PATH}")
   583	    print(f"   Task:  {TASK_DIR}")
   584	    print(f"   Plan:  {PLAN_PATH}")
   585	    print(f"   Exec:  {EXECUTOR_PATH}")
   586	    return 0
   587	
   588	
```
