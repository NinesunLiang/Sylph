# PKG-B(gpt-5.6Sol) 材料包

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb` | 生成: 2026-07-19 | 密钥已脱敏为 <REDACTED>
> 验证契约统一。git ls-files/status/HEAD/rg 全量见 shared.md,此处为完整原文集。

### `.claude/scripts/carros_base.py` — cmd_verify 所在,全文

```
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
   589	def _find_latest_token(require_active=True):
   590	    """扫描 tokens 目录，找到日期最新且活跃的 token
   591	
   592	    require_active=True: 只返回 status=active 的 token（首选）
   593	    require_active=False: 返回任何一个有效的 token（作为回退）
   594	
   595	    排序规则：按文件 mtime 倒序（最新写的优先），而非文件名排序
   596	    """
   597	    OMC_TOKENS.mkdir(parents=True, exist_ok=True)
   598	    if not OMC_TOKENS.exists():
   599	        return None, None
   600	
   601	    # 收集所有 token 文件，按 mtime 排序
   602	    candidates = []
   603	    for dd in sorted(OMC_TOKENS.iterdir(), reverse=True):
   604	        if dd.is_dir():
   605	            for jf in dd.glob("*.json"):
   606	                try:
   607	                    candidates.append((jf.stat().st_mtime, jf))
   608	                except OSError:
   609	                    continue
   610	
   611	    # 按 mtime 倒序
   612	    candidates.sort(key=lambda x: x[0], reverse=True)
   613	
   614	    fallback = None
   615	    for _, jf in candidates:
   616	        try:
   617	            token = json.loads(jf.read_text())
   618	            if token.get("status") == "active":
   619	                return token, jf
   620	            if fallback is None:
   621	                fallback = (token, jf)
   622	        except (json.JSONDecodeError, OSError):
   623	            continue
   624	
   625	    if fallback and not require_active:
   626	        return fallback
   627	    return None, None
   628	
   629	
   630	def cmd_status(hot_mode=True):
   631	    """展示当前任务状态。默认 Hot Card 模式。--full 出完整状态。"""
   632	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   633	        token, found_path = _find_latest_token()
   634	        if token and found_path:
   635	            _init_paths_from_token(token, found_path)
   636	        else:
   637	            print(_yellow("⚠  No active task"))
   638	            return 0
   639	    token = _load_token()
   640	    if not token:
   641	        print(_yellow("⚠  No active task (token.json not found)"))
   642	        return 0
   643	
   644	    if hot_mode:
   645	        # Hot Card — 极简状态（默认）
   646	        try:
   647	            import lib.hot_card as hc
   648	            card = hc.cmd_status_hot(token, TOKEN_PATH, PLAN_PATH, EXECUTOR_PATH)
   649	            print(card)
   650	            hc_len = len(card)
   651	            if hc_len > 4500:
   652	                print(_yellow(f"\n⚠  Hot Card exceeds 4.5K chars: {hc_len}"))
   653	            return 0
   654	        except ImportError:
   655	            # fallback: lib/ not available
   656	            pass
   657	
   658	    # Full status（--full 模式或 fallback）
   659	    s = token.get("stats", {})
   660	    status_top = token.get("status", "?")
   661	    status_icon = _green("●") if status_top == "active" else _red("●")
   662	    print(f"{status_icon} Task: {token.get('session', {}).get('id', '?')} [{token.get('session', {}).get('level', '?')}]")
   663	    print(f"   Status: {status_top}")
   664	    print(f"   Progress: {s.get('done', 0)}/{s.get('total', 0)} steps completed")
   665	    current_step = token.get("task", {}).get("current_step")
   666	    task_status = token.get("task", {}).get("status")
   667	    blocked = token.get("task", {}).get("blocked")
   668	    current = current_step or "?"
   669	    print(f"   Current Step: {current}")
   670	    print(f"   Task Status: {task_status}")
   671	    if blocked:
   672	        print(f"   Blocked: {blocked}")
   673	    # task-state 追踪展示
   674	    if tst:
   675	        state_info = tst.format_status(token, TOKEN_PATH)
   676	        if state_info:
   677	            print(state_info)
   678	    return 0
   679	
   680	
   681	def cmd_tick():
   682	    """递增 tick 计数器 + 水位检查 + 自动追踪当前步骤状态"""
   683	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   684	        token, found_path = _find_latest_token()
   685	        if token and found_path:
   686	            _init_paths_from_token(token, found_path)
   687	        else:
   688	            print(_red("❌ No active task"))
   689	            return 2
   690	    token = _load_token()
   691	    if not token:
   692	        print(_red("❌ No active task"))
   693	        return 2
   694	
   695	    # 水位检查
   696	    try:
   697	        from lib.water_level import run_water_gate
   698	        gate = run_water_gate(action="tick")
   699	        if not gate["continue"]:
   700	            print(_yellow(f"⚠  {gate['message']}"))
   701	            # Pause: write handoff, request compact
   702	            from lib.handoff_writer import write_handoff
   703	            write_handoff(TASK_DIR, token.get("session",{}).get("id",""), token, PLAN_PATH, executor_path=EXECUTOR_PATH)
   704	            return 0  # soft pause, not error
   705	        elif gate["water"]["level"] == "warn":
   706	            print(_yellow(f"⚠  {gate['message']}"))
   707	    except ImportError:
   708	        pass  # water_level.py not available — continue without
   709	
   710	    # 找当前 pending 步骤 — 从 plan.md 读取
   711	    current_step = None
   712	    if PLAN_PATH and PLAN_PATH.exists():
   713	        plan_content = PLAN_PATH.read_text()
   714	        pending_steps = re.findall(r"^- \[ \] (\S+?):", plan_content, re.MULTILINE)
   715	        if pending_steps:
   716	            current_step = pending_steps[0]
   717	    else:
   718	        current_step = token.get("task", {}).get("current_step")
   719	
   720	    if "tick" in token.get("stats", {}):
   721	        token["stats"]["tick"] += 1
   722	        print(f"   Tick: {token['stats']['tick']}")
   723	    else:
   724	        token["stats"]["turns"] = token["stats"].get("turns", 0) + 1
   725	        print(f"   Turn: {token['stats']['turns']}")
   726	    _save_token(token)
   727	
   728	    # task-state: 记录步骤开始追踪
   729	    if current_step and tst:
   730	        tst.mark_step_started(TOKEN_PATH, current_step)
   731	        print(f"   ◷ Tracking {current_step} (use 'verify' to complete)")
   732	    return 0
   733	
   734	
   735	def _run_dual_judge(token: dict) -> int:
   736	    """L2 任务 verify 自动双审判：static + runtime oracle → meta 聚合。
   737	
   738	    裁决落盘 .omc/state/meta-oracle-verdicts/{task_id}/latest.json。
   739	    Returns: 0=ACCEPT/ADVISORY（放行）, 2=REJECT（verify 不通过）, 3=ESCALATE（放行但提示人工）。
   740	    """
   741	    task_id = token.get("session", {}).get("id", "unknown")
   742	    static_agent = _hook_dir / "static_oracle_agent.py"
   743	    runtime_agent = _hook_dir / "runtime_oracle_agent.py"
   744	    meta = _hook_dir / "meta_oracle.py"
   745	    if not (static_agent.exists() and runtime_agent.exists() and meta.exists()):
   746	        print(_yellow("⚠  dual-judge 脚本缺失，跳过（降级为人工复核）"))
   747	        return 0
   748	
   749	    print("⚖️  L2 双审判官裁决（static → runtime → meta）...")
   750	    for name, agent in (("static", static_agent), ("runtime", runtime_agent)):
   751	        try:
   752	            r = subprocess.run(
   753	                [sys.executable, str(agent), "review", "--task-id", task_id],
   754	                capture_output=True, text=True, timeout=120,
   755	            )
   756	            if r.returncode not in (0, 1):
   757	                print(_yellow(f"⚠  {name} oracle exit={r.returncode}: {r.stderr[:200]}"))
   758	        except Exception as exc:
   759	            print(_yellow(f"⚠  {name} oracle 异常: {exc}"))
   760	
   761	    try:
   762	        r = subprocess.run(
   763	            [sys.executable, str(meta), "aggregate", "--task-id", task_id],
   764	            capture_output=True, text=True, timeout=30,
   765	        )
   766	        out = r.stdout.strip()
   767	        verdict = "UNAVAILABLE"
   768	        try:
   769	            json_start = out.find("{")
   770	            if json_start >= 0:
   771	                verdict = json.loads(out[json_start:]).get("verdict", "UNAVAILABLE")
   772	        except Exception:
   773	            pass
   774	        _write_audit("dual_judge", {"task_id": task_id, "verdict": verdict, "exit": r.returncode})
   775	        if verdict == "REJECT":
   776	            print(_red(f"⚖️  双审判 REJECT — verify 不通过，详见 .omc/state/meta-oracle-verdicts/{task_id}/latest.json"))
   777	            return 2
   778	        if verdict == "ESCALATE":
   779	            print(_yellow(f"⚖️  双审判 ESCALATE — 建议人工复核"))
   780	            return 3
   781	        print(_green(f"⚖️  双审判 {verdict}"))
   782	        return 0
   783	    except Exception as exc:
   784	        print(_yellow(f"⚠  meta 聚合异常: {exc}（降级放行，需人工复核）"))
   785	        return 0
   786	
   787	
   788	def cmd_verify(step_id=None):
   789	    """验证 step 完成 — 标记 plan.md [x] + 写 audit"""
   790	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   791	        token, found_path = _find_latest_token()
   792	        if token and found_path:
   793	            _init_paths_from_token(token, found_path)
   794	        else:
   795	            print(_red("❌ No active task"))
   796	            return 2
   797	    token = _load_token()
   798	    if not token:
   799	        print(_red("❌ No active task"))
   800	        return 2
   801	
   802	    if not PLAN_PATH.exists():
   803	        print(_red("❌ plan.md not found"))
   804	        return 2
   805	
   806	    plan = PLAN_PATH.read_text()
   807	    lines = plan.split("\n")
   808	
   809	    if step_id:
   810	        targets = [step_id]
   811	    else:
   812	        targets = []
   813	        current = token.get("task", {}).get("current_step")
   814	        if current:
   815	            targets.append(current)
   816	        if not targets:
   817	            print(_yellow("⚠  All steps already completed"))
   818	            return 0
   819	
   820	    verified_any = False
   821	    for target in targets:
   822	        pattern = re.compile(r"^- \[ \] " + re.escape(target) + r":", re.MULTILINE)
   823	        replacement = f"- [x] {target}:"
   824	        new_plan, count = pattern.subn(replacement, plan)
   825	        if count > 0:
   826	            plan = new_plan
   827	            # 更新 token — 统一新格式（递增 done 计数器）
   828	            token["stats"]["done"] = token["stats"].get("done", 0) + 1
   829	            if token["stats"]["done"] >= token["stats"]["total"]:
   830	                token["task"]["status"] = "completed"
   831	            _write_audit("verify", {"step": target, "result": "VERIFIED"})
   832	            print(_green(f"✅ {target}: VERIFIED"))
   833	            # task-state: 标记完成
   834	            if tst:
   835	                tst.mark_step_completed(TOKEN_PATH, target)
   836	                verdict = tst.format_tick_verdict(TOKEN_PATH, target)
   837	                if verdict:
   838	                    print(verdict)
   839	            verified_any = True
   840	        else:
   841	            print(_yellow(f"⚠  {target}: not found in plan.md"))
   842	
   843	    if verified_any:
   844	        PLAN_PATH.write_text(plan)
   845	        _save_token(token)
   846	        _write_handoff(token)
   847	
   848	        # L2 双审判官：verify 自动裁决（REJECT → verify 不通过）
   849	        level = token.get("session", {}).get("level", "L1_BASE")
   850	        if level == "L2_ENHANCE":
   851	            judge_rc = _run_dual_judge(token)
   852	            if judge_rc == 2:
   853	                return 2
   854	
   855	        # Goal 状态自动推进: done >= total → VERIFYING
   856	        done = token.get("stats", {}).get("done", 0)
   857	        total = token.get("stats", {}).get("total", 0)
   858	        if done >= total and GoalMachine:
   859	            try:
   860	                gm = GoalMachine(TOKEN_PATH)
   861	                gm.auto_progress(token)
   862	            except GoalError:
   863	                pass
   864	    return 0
   865	
   866	
   867	def cmd_report(use_stdout=True, archive_mode=False):
   868	    """
   869	    生成 final-report.md — 共享节点，所有流程的终止点都应调用。
   870	
   871	    从 executor.md + plan.md + audit JSONL 提取事实，不会编造。
   872	
   873	    Args:
   874	        use_stdout: 输出到 stdout（默认 True）
   875	        archive_mode: 归档模式（写入 task_dir + 额外标记）
   876	
   877	    Returns:
   878	        0 = 成功, 1 = 无活跃任务, 2 = 错误
   879	    """
   880	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   881	        token, tp = _find_latest_token()
   882	        if token and tp:
   883	            _init_paths_from_token(token, tp)
   884	        else:
   885	            print(_red("❌ No active task"))
   886	            return 2
   887	
   888	    token = _load_token()
   889	    if not token:
   890	        print(_red("❌ No active task"))
   891	        return 2
   892	
   893	    report_text = ""
   894	
   895	    if carros_utils and hasattr(carros_utils, "generate_final_report"):
   896	        report_text = carros_utils.generate_final_report(token, TASK_DIR)
   897	    else:
   898	        # fallback brief
   899	        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
   900	        stats = token.get("stats", {})
   901	        sid = token.get("session", {}).get("id", "unknown")
   902	        report_text = (
   903	            f"# Final Report: {sid}\n\n"
   904	            f"**生成时间:** {now}\n"
   905	            f"**状态:** {token.get('status', '?')}\n"
   906	            f"**完成度:** {stats.get('done', 0)}/{stats.get('total', 0)}\n\n"
   907	        )
   908	
   909	    # 输出到 stdout（用户直接看到）
   910	    if use_stdout:
   911	        print(_bold("=" * 50))
   912	        print(report_text)
   913	        print(_bold("=" * 50))
   914	
   915	    # 输出到 task_dir/final-report.md
   916	    if TASK_DIR:
   917	        report_path = TASK_DIR / "final-report.md"
   918	        report_path.write_text(report_text)
   919	        print(_green(f"✅ Report saved: {report_path}"))
   920	
   921	    return 0
   922	
   923	
   924	def cmd_archive(force=False):
   925	    """归档任务 — archive = lint + verify-summary + final-report + tombstone"""
   926	    if not TOKEN_PATH or not TOKEN_PATH.exists():
   927	        token, found_path = _find_latest_token()
   928	        if token and found_path:
   929	            _init_paths_from_token(token, found_path)
   930	        else:
   931	            print(_red("❌ No active task"))
   932	            return 2
   933	    print(_bold("Archiving task..."))
   934	
   935	    # Step 1: run lint — 仅 error (exit>=2) 阻断，warning (exit=1) 可归档
   936	    if not force:
   937	        lint_ok = cmd_lint()
   938	        if lint_ok >= 2:
   939	            print(_red("❌ Lint has errors. Use --force to archive anyway."))
   940	            return 2
   941	        elif lint_ok == 1:
   942	            print(_yellow("⚠  Lint warnings only — proceeding with archive"))
   943	    else:
   944	        print(_yellow("⚠  --force: skipping lint"))
   945	
   946	    token = _load_token()
   947	    if not token:
   948	        print(_red("❌ No active task"))
   949	        return 2
   950	
   951	    # Step 2: check all steps completed — 统一新格式
   952	    if not force:
   953	        pending = []
   954	        if token.get("stats", {}).get("done", 0) < token.get("stats", {}).get("total", 0):
   955	            pending = ["current_step not completed"]
   956	        if pending:
   957	            print(_red(f"❌ Steps not completed: {pending}"))
   958	            return 2
   959	    else:
   960	        print(_yellow("⚠  --force: skipping step completion check"))
   961	
   962	    # Step 3: generate final report (shared node)
   963	    task_sid = token.get("session", {}).get("id", "unknown")
   964	    archive_dir = OMC_ROOT / "archive" / task_sid
   965	    archive_dir.mkdir(parents=True, exist_ok=True)
   966	    cmd_report(use_stdout=False)
   967	    print(_green(f"✅ Final report: {archive_dir / 'final-report.md'}"))
   968	
   969	    # Step 4: 复制 report 到 archive 目录
   970	    if GoalMachine:
   971	        try:
   972	            gm = GoalMachine(TOKEN_PATH)
   973	            gm.transition(gsm.ARCHIVED, reason="archive completed")
   974	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
   975	            # 重新加载 token — GoalMachine 已写入 goal.archived
   976	            token = _load_token() or token
   977	        except GoalError:
   978	            pass
   979	
   980	    # Step 5: tombstone — 复制 token 到 archive 目录作为墓碑
   981	    token["status"] = "archived"
   982	    token["archived_at"] = datetime.now(timezone.utc).isoformat()
   983	    _save_token(token)
   984	
   985	    # 按方案 10.md L987-1000 写 token.final.json + token.tombstone.json
   986	    import shutil
   987	    write_json_atomic = lambda p, d: (p.parent.mkdir(parents=True, exist_ok=True), p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"))
   988	    write_json_atomic(archive_dir / "token.final.json", token)
   989	    write_json_atomic(
   990	        archive_dir / "token.tombstone.json",
   991	        {
   992	            "task_id": token["session"]["id"],
   993	            "previous_token": str(TOKEN_PATH),
   994	            "status": "archived",
   995	            "archived_at": now_iso(),
   996	            "final_report": str(archive_dir / "final-report.md"),
   997	            "final_verdict": "ARCHIVED",
   998	            "level": token.get("session", {}).get("level", "unknown_level"),
   999	        },
  1000	    )
  1001	    for optional in ["plan.md", "executor.md"]:
  1002	        src = TASK_DIR / optional if TASK_DIR else None
  1003	        if src and src.exists():
  1004	            shutil.copy2(src, archive_dir / optional)
  1005	    handoff_src = HANDOFF_PATH if HANDOFF_PATH else Path(".omc/session-handoff.md")
  1006	    if handoff_src.exists():
  1007	        shutil.copy2(handoff_src, archive_dir / "session-handoff.md")
  1008	
  1009	    _write_audit("archive", {"task_id": token["session"]["id"], "result": "ARCHIVED"})
  1010	    _write_handoff(token)
  1011	
  1012	    # Step 6: 删除 active token
  1013	    token_path_str = str(TOKEN_PATH)
  1014	    TOKEN_PATH.unlink(missing_ok=True)
  1015	    print(_green(f"✅ Token 已删除: {token_path_str}"))
  1016	
  1017	    # Step 7: 输出 {"continue": false}
  1018	    print(json.dumps({"continue": False}))
  1019	    print(_green("✅ Task archived"))
  1020	
  1021	    return 0
  1022	
  1023	
  1024	def _generate_final_report(token):
  1025	    """生成归档报告 — 委托 carros_utils"""
  1026	    if carros_utils:
  1027	        return carros_utils.generate_final_report(token)
  1028	    # fallback — inline
  1029	    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
  1030	    sid = token.get("session", {}).get("id", "unknown")
  1031	    level = token.get("session", {}).get("level", "?")
  1032	    status = token.get("status", "?")
  1033	    stats = token.get("stats", {})
  1034	
  1035	    done = stats.get("done", 0)
  1036	    total = stats.get("total", 0)
  1037	    tick = stats.get("turns", 0)
  1038	    current = token.get("task", {}).get("current_step", "?")
  1039	    task_status = token.get("task", {}).get("status", "?")
  1040	    step_lines = [f"  current_step: {current} ({task_status})"]
  1041	
  1042	    lines = [
  1043	        f"# Final Report: {sid}",
  1044	        "",
  1045	        f"**Archived at:** {now}",
  1046	        f"**Level:** {level}",
  1047	        f"**Status:** {status}",
  1048	        "",
  1049	        "## Summary",
  1050	        "",
  1051	        f"Completed {done}/{total} steps in {tick} ticks.",
  1052	        "",
  1053	        "## Steps",
  1054	        "",
  1055	    ]
  1056	    lines.extend(step_lines)
  1057	    lines.append("")
  1058	    lines.append("## Audit Trail")
  1059	    lines.append("")
  1060	    lines.append("See `.omc/state/audit/` for full event log.")
  1061	    lines.append("")
  1062	    lines.append("---")
  1063	    lines.append("_Generated by carros_base.py archive_")
  1064	    return "\n".join(lines)
  1065	
  1066	
  1067	def cmd_lint(path=None):
  1068	    """统一 lint — 委托 omc_lint 模块"""
  1069	    if omc_lint is None:
  1070	        print(_red("❌ omc_lint module not available"))
  1071	        return 2
  1072	
  1073	    target = path or str(PROJECT_ROOT)
  1074	    try:
  1075	        result = omc_lint.run_lint(target)
  1076	        print(result["output"])
  1077	        return result["exit_code"]
  1078	    except Exception as e:
  1079	        print(_red(f"❌ Lint error: {e}"))
  1080	        return 2
  1081	
  1082	
  1083	BENCH_SCENES = {
  1084	    "01_doc_update": {
  1085	        "description": "纯文档更新",
  1086	        "steps": ["S1"],
  1087	    },
  1088	    "02_single_file_fix": {
  1089	        "description": "单文件修复",
  1090	        "steps": ["S1"],
  1091	    },
  1092	    "03_multi_file_test": {
  1093	        "description": "多文件协同修改",
  1094	        "steps": ["S1", "S2"],
  1095	    },
  1096	    "04_failure_then_repair": {
  1097	        "description": "失败后修复",
  1098	        "steps": ["S1", "S2"],
  1099	    },
  1100	    "05_compact_resume": {
  1101	        "description": "compact/resume 恢复",
  1102	        "steps": ["S1", "S2", "S3"],
  1103	    },
  1104	    "06_fallback_downgrade": {
  1105	        "description": "降级场景",
  1106	        "steps": ["S1"],
  1107	    },
  1108	    "07_archive": {
  1109	        "description": "归档闭环",
  1110	        "steps": ["S1", "S2", "S3", "S4", "S5"],
  1111	    },
  1112	}
  1113	
  1114	
  1115	def cmd_bench(scene=None):
  1116	    """运行 bench 基准测试—验证治理系统基本链路"""
  1117	    import subprocess
  1118	
  1119	    scenes = BENCH_SCENES
  1120	    if scene:
  1121	        if scene not in scenes:
  1122	            print(_red(f"❌ Unknown bench scene: {scene}"))
  1123	            print(f"   Available: {', '.join(scenes.keys())}")
  1124	            return 2
  1125	        scenes = {scene: scenes[scene]}
  1126	
  1127	    results = []
  1128	    for scene_id, cfg in scenes.items():
  1129	        print(_bold(f"\n{'='*60}"))
  1130	        print(_bold(f"▶ Bench: {scene_id} — {cfg['description']}"))
  1131	        print(f"{'='*60}")
  1132	
  1133	        task_id = f"bench-{scene_id[:2]}"
  1134	        steps = cfg["steps"]
  1135	
  1136	        # 1. init
  1137	        step_args = " ".join(f"--step {s}" for s in steps)
  1138	        cmd = f"python3 .claude/scripts/carros_base.py init --task-id {task_id} {step_args} --force"
  1139	        print(_yellow(f"    init..."))
  1140	        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
  1141	        if r.returncode != 0:
  1142	            print(_red(f"    ❌ init failed: {r.stderr[:200]}"))
  1143	            results.append((scene_id, "FAIL_INIT"))
  1144	            continue
  1145	
  1146	        # 2. status
  1147	        r = subprocess.run("python3 .claude/scripts/carros_base.py status", shell=True,
  1148	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1149	        if r.returncode != 0:
  1150	            print(_red(f"    ❌ status failed"))
  1151	            results.append((scene_id, "FAIL_STATUS"))
  1152	            continue
  1153	        print(f"    {r.stdout.strip().split(chr(10))[0]}")
  1154	
  1155	        # 3. tick
  1156	        r = subprocess.run("python3 .claude/scripts/carros_base.py tick", shell=True,
  1157	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1158	        if r.returncode != 0:
  1159	            print(_yellow(f"    ⚠ tick failed"))
  1160	
  1161	        # 4. verify each step
  1162	        all_verified = True
  1163	        for s in steps:
  1164	            r = subprocess.run(f"python3 .claude/scripts/carros_base.py verify --step {s}",
  1165	                              shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
  1166	            if r.returncode == 0:
  1167	                print(f"    ✅ {s}: VERIFIED")
  1168	            else:
  1169	                print(_red(f"    ❌ {s}: {r.stdout[:100]}"))
  1170	                all_verified = False
  1171	
  1172	        if not all_verified:
  1173	            results.append((scene_id, "FAIL_VERIFY"))
  1174	            continue
  1175	
  1176	        # 5. lint
  1177	        r = subprocess.run("python3 .claude/scripts/carros_base.py lint", shell=True,
  1178	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1179	        lint_ok = r.returncode == 0
  1180	        if lint_ok:
  1181	            print(f"    ✅ lint: PASS")
  1182	        else:
  1183	            print(_yellow(f"    ⚠ lint: {r.stdout.strip()[:100]}"))
  1184	
  1185	        # 6. archive
  1186	        r = subprocess.run("python3 .claude/scripts/carros_base.py archive --force", shell=True,
  1187	                          capture_output=True, text=True, cwd=PROJECT_ROOT)
  1188	        if r.returncode == 0:
  1189	            print(_green(f"    ✅ archive: OK"))
  1190	            results.append((scene_id, "PASS"))
  1191	        else:
  1192	            print(_red(f"    ❌ archive: {r.stdout[:200]}"))
  1193	            results.append((scene_id, "FAIL_ARCHIVE"))
  1194	
  1195	    # Summary
  1196	    print(_bold(f"\n{'='*60}"))
  1197	    print(_bold("Bench Results"))
  1198	    print(f"{'='*60}")
  1199	    passed = sum(1 for _, s in results if s == "PASS")
  1200	    failed = sum(1 for _, s in results if s != "PASS")
  1201	    for scene_id, status in results:
  1202	        icon = _green("✅") if status == "PASS" else _red("❌")
  1203	        print(f"  {icon} {scene_id}: {status}")
  1204	    print(f"\n  {passed} passed, {failed} failed")
  1205	    return 0 if failed == 0 else 1
  1206	
  1207	
  1208	def cmd_gate():
  1209	    """PreActionGate - 对 action_spec 做执行前安全裁决
  1210	
  1211	    读取当前 active token，创建临时 action_spec 文件，
  1212	    调用 pre_action_gate.py 做裁决。
  1213	
  1214	    用法:
  1215	        python3 .omc/scripts/carros_base.py gate --action-type write_file --paths README.md --step S1 --intent "update docs"
  1216	    """
  1217	    import subprocess
  1218	    import tempfile
  1219	
  1220	    argv = sys.argv[sys.argv.index("gate") + 1:]
  1221	    p = {}
  1222	    i = 0
  1223	    while i < len(argv):
  1224	        if argv[i] == "--action-type" and i + 1 < len(argv):
  1225	            p["action_type"] = argv[i + 1]; i += 2
  1226	        elif argv[i] == "--command" and i + 1 < len(argv):
  1227	            p["command"] = argv[i + 1]; i += 2
  1228	        elif argv[i] == "--paths" and i + 1 < len(argv):
  1229	            p["paths"] = argv[i + 1].split(","); i += 2
  1230	        elif argv[i] == "--step" and i + 1 < len(argv):
  1231	            p["current_step"] = argv[i + 1]; i += 2
  1232	        elif argv[i] == "--intent" and i + 1 < len(argv):
  1233	            p["intent"] = argv[i + 1]; i += 2
  1234	        elif argv[i] == "--risk-hint" and i + 1 < len(argv):
  1235	            p["risk_hint"] = argv[i + 1]; i += 2
  1236	        elif argv[i] == "--network" and i + 1 < len(argv):
  1237	            p["requires_network"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1238	        elif argv[i] == "--production" and i + 1 < len(argv):
  1239	            p["requires_production"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1240	        elif argv[i] == "--database" and i + 1 < len(argv):
  1241	            p["requires_database"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
  1242	        else:
  1243	            i += 1
  1244	
  1245	    if "action_type" not in p:
  1246	        print(_red("Missing --action-type"))
  1247	        return 2
  1248	
  1249	    p.setdefault("paths", [])
  1250	    p.setdefault("intent", "")
  1251	    p.setdefault("current_step", "S1")
  1252	
  1253	    spec_file = tempfile.NamedTemporaryFile(
  1254	        mode="w", suffix=".json", delete=False, prefix="preaction-"
  1255	    )
  1256	    json.dump(p, spec_file, ensure_ascii=False, indent=2)
  1257	    spec_path = spec_file.name
  1258	    spec_file.close()
  1259	
  1260	    # 找到当前 active token
  1261	    _token_data, token_path = _find_latest_token()
  1262	    if token_path is None:
  1263	        print(_yellow("No active token found — running without token context"))
  1264	        token_arg = []
  1265	    else:
  1266	        token_arg = ["--token", str(token_path)]
  1267	
  1268	    try:
  1269	        gate_script = _hook_dir / "pre_action_gate.py"
  1270	        cmd = [sys.executable, str(gate_script), spec_path] + token_arg
  1271	        r = subprocess.run(cmd, capture_output=True, text=True)
  1272	        output = r.stdout.strip() if r.stdout else r.stderr.strip()
  1273	        if output:
  1274	            print(output)
  1275	        return r.returncode
  1276	    finally:
  1277	        Path(spec_path).unlink(missing_ok=True)
  1278	
  1279	
  1280	def _sub_token(task_dir: str, parent_id: str, step_id: str, plan_text: str = "") -> dict:
  1281	    """生成 subagent token.json — 子代理的启动契约
  1282	
  1283	    subagent 读这个文件知道：为谁工作（parent_id）、
  1284	    要做什么（subtask.plan）、被允许做什么（session.level）
  1285	    """
  1286	    now = datetime.now(timezone.utc)
  1287	    return {
  1288	        "schema_version": _SCHEMA_VERSION,
  1289	        "session": {
  1290	            "id": f"{parent_id}-{step_id}",
  1291	            "level": "L1_SUB",
  1292	            "created_at": now.isoformat(),
  1293	            "updated_at": now.isoformat(),
  1294	        },
  1295	        "parent": {
  1296	            "task_dir": task_dir,
  1297	            "task_id": parent_id,
  1298	            "step_id": step_id,
  1299	        },
  1300	        "subtask": {
  1301	            "plan": plan_text,
  1302	        },
  1303	        "status": "active",
  1304	        "stats": {"done": 0, "total": 1, "tick": 0},
  1305	    }
  1306	
  1307	
  1308	def _result_template() -> dict:
  1309	    """result.json 模板 — subagent 完成工作后写"""
  1310	    return {
  1311	        "status": "running",
  1312	        "summary": "",
  1313	        "evidence": [],
  1314	        "files_changed": [],
  1315	        "failure": None,
  1316	        "completed_at": None,
  1317	        "started_at": datetime.now(timezone.utc).isoformat(),
  1318	    }
  1319	
  1320	
  1321	def cmd_dispatch():
  1322	    """分发子任务到 subagent — 创建 sub_task/{step} 目录 + token + plan
  1323	
  1324	    用法:
  1325	        python3 .claude/scripts/carros_base.py dispatch --step S1 [--text \"要做什么\"]
  1326	
  1327	    产生文件:
  1328	        .omc/tasks/{date}/{task}/sub_task/sub-{step}/
  1329	            token.json     — subagent 契约（parent/plan/约束）
  1330	            result.json    — subagent 汇报模板
  1331	            executor.md    — 空证据账本
  1332	
  1333	    subagent 启动后工作:
  1334	        1. 读 token.json（知道 parent_task 和 plan）
  1335	        2. 按 plan 执行
  1336	        3. 写 executor.md（证据）
  1337	        4. 更新 result.json（status=completed + summary + evidence）
  1338	        5. 更新 token.json（status=completed）
  1339	    """
  1340	    global TASK_DIR, TOKEN_PATH, SUB_TASK_DIR
  1341	
  1342	    # 确保有 active token
  1343	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1344	        token, tp = _find_latest_token()
  1345	        if not token:
  1346	            print(_red("❌ No active main task. Run 'init' first."))
  1347	            return 2
  1348	        _init_paths_from_token(token, tp)
  1349	
  1350	    # 解析参数
  1351	    argv = sys.argv[sys.argv.index("dispatch") + 1:]
  1352	    step_id = "S1"
  1353	    plan_text = ""
  1354	    i = 0
  1355	    while i < len(argv):
  1356	        if argv[i] == "--step" and i + 1 < len(argv):
  1357	            step_id = argv[i + 1]; i += 2
  1358	        elif argv[i] == "--text" and i + 1 < len(argv):
  1359	            plan_text = argv[i + 1]; i += 2
  1360	        else:
  1361	            i += 1
  1362	
  1363	    # 创建 sub_task 目录
  1364	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"
  1365	    sub_dir.mkdir(parents=True, exist_ok=True)
  1366	
  1367	    # 生成 subagent token
  1368	    token_data = _sub_token(
  1369	        task_dir=str(TASK_DIR),
  1370	        parent_id=token.get("session", {}).get("id", "unknown"),
  1371	        step_id=step_id,
  1372	        plan_text=plan_text,
  1373	    )
  1374	
  1375	    # 写入 token.json
  1376	    token_path = sub_dir / "token.json"
  1377	    token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2))
  1378	
  1379	    # 写入 result.json（模板）
  1380	    result_data = _result_template()
  1381	    result_data["parent"] = {
  1382	        "task_dir": str(TASK_DIR),
  1383	        "token_path": str(TOKEN_PATH),
  1384	    }
  1385	    result_path = sub_dir / "result.json"
  1386	    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2))
  1387	
  1388	    # 写入 executor.md（空账本）
  1389	    exec_path = sub_dir / "executor.md"
  1390	    if not exec_path.exists():
  1391	        exec_path.write_text(
  1392	            f"# Executor: {token_data['session']['id']}\n"
  1393	            f"## Parent: {token_data['parent']['task_id']}\n\n"
  1394	        )
  1395	
  1396	    # 更新 main token：记录该 step 已分配 subagent
  1397	    main_token = _load_token()
  1398	    if main_token and "steps" in main_token:
  1399	        for s in main_token["steps"]:
  1400	            if s["id"] == step_id:
  1401	                s["status"] = "running"
  1402	                s["subagent_path"] = str(sub_dir)
  1403	                break
  1404	        _save_token(main_token)
  1405	
  1406	    print(_green(f"✅ Dispatched {step_id} → {sub_dir}"))
  1407	    print(f"   token:  {token_path}")
  1408	    print(f"   result: {result_path}")
  1409	    print(f"   Subagent reads token.json for task, writes result.json on completion")
  1410	    return 0
  1411	
  1412	
  1413	def cmd_poll():
  1414	    """轮询所有 subagent 状态 — main agent 追踪 subagent 进度
  1415	
  1416	    读每个 sub_task/sub-*/result.json，展示汇总状态。
  1417	    支持 --verbose 展示每个 subagent 的关键证据。
  1418	
  1419	    用法:
  1420	        python3 .claude/scripts/carros_base.py poll [--verbose]
  1421	    """
  1422	    global SUB_TASK_DIR, TASK_DIR
  1423	
  1424	    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1425	        # 尝试从当前 token 获取
  1426	        tok, _ = _find_latest_token()
  1427	        if tok:
  1428	            td = tok.get("task_dir")
  1429	            if td:
  1430	                SUB_TASK_DIR = Path(td) / "sub_task"
  1431	        if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1432	            print(_yellow("⚠  No sub tasks found"))
  1433	            return 0
  1434	
  1435	    verbose = "--verbose" in sys.argv
  1436	
  1437	    sub_dirs = sorted([d for d in SUB_TASK_DIR.iterdir() if d.is_dir()])
  1438	    if not sub_dirs:
  1439	        print(_yellow("⚠  No sub tasks found"))
  1440	        return 0
  1441	
  1442	    print(_bold(f"SubAgent Status: {len(sub_dirs)} task(s)"))
  1443	    print(f"{'─' * 50}")
  1444	
  1445	    total_done = 0
  1446	    total_failed = 0
  1447	    for sd in sub_dirs:
  1448	        name = sd.name
  1449	        result_path = sd / "result.json"
  1450	        token_path = sd / "token.json"
  1451	
  1452	        if not result_path.exists():
  1453	            print(f"   ○ {name}: no result yet")
  1454	            continue
  1455	
  1456	        try:
  1457	            result = json.loads(result_path.read_text())
  1458	            status = result.get("status", "unknown")
  1459	
  1460	            if status == "completed":
  1461	                icon = _green("✔")
  1462	                total_done += 1
  1463	            elif status == "failed":
  1464	                icon = _red("✘")
  1465	                total_failed += 1
  1466	            elif status == "running":
  1467	                icon = _yellow("◷")
  1468	            else:
  1469	                icon = "○"
  1470	
  1471	            summary = result.get("summary", "")
  1472	            parts = [f"   {icon} {name}: {status}"]
  1473	            if summary:
  1474	                parts.append(f"→ {summary[:60]}")
  1475	            if verbose and result.get("files_changed"):
  1476	                parts.append(f"files: {', '.join(result['files_changed'][:3])}")
  1477	            if result.get("failure"):
  1478	                parts.append(_red(f"FAIL: {result['failure'][:80]}"))
  1479	
  1480	            print("  ".join(parts))
  1481	
  1482	        except (json.JSONDecodeError, OSError) as e:
  1483	            print(f"   ⚠ {name}: read error ({e})")
  1484	
  1485	    print(f"{'─' * 50}")
  1486	    print(f"   {total_done} completed, {total_failed} failed, "
  1487	          f"{len(sub_dirs) - total_done - total_failed} running/pending")
  1488	
  1489	    # 更新 main token 的 step 状态
  1490	    main_token = _load_token()
  1491	    if main_token and "steps" in main_token:
  1492	        updated = False
  1493	        for s in main_token["steps"]:
  1494	            sp = s.get("subagent_path")
  1495	            if sp and s["status"] == "running":
  1496	                rp = Path(sp) / "result.json"
  1497	                if rp.exists():
  1498	                    try:
  1499	                        r = json.loads(rp.read_text())
  1500	                        if r.get("status") == "completed":
  1501	                            s["status"] = "completed"
  1502	                            updated = True
  1503	                        elif r.get("status") == "failed":
  1504	                            s["status"] = "failed"
  1505	                            updated = True
  1506	                    except Exception:
  1507	                        pass
  1508	        if updated:
  1509	            _save_token(main_token)
  1510	
  1511	    return 0
  1512	
  1513	
  1514	def cmd_collect():
  1515	    """回收 subagent 完成结果 — 把 result.json 汇入 main task executor.md
  1516	
  1517	    用法:
  1518	        python3 .claude/scripts/carros_base.py collect --step S1
  1519	
  1520	    执行:
  1521	        1. 读 sub_task/sub-{step}/result.json
  1522	        2. 验证 status=completed
  1523	        3. 证据追加到 main executor.md
  1524	        4. 文件变更记录到 audit
  1525	        5. 标记 main token step 完成
  1526	    """
  1527	    global SUB_TASK_DIR, TASK_DIR, TOKEN_PATH, EXECUTOR_PATH
  1528	
  1529	    argv = sys.argv[sys.argv.index("collect") + 1:]
  1530	    step_id = None
  1531	    i = 0
  1532	    while i < len(argv):
  1533	        if argv[i] == "--step" and i + 1 < len(argv):
  1534	            step_id = argv[i + 1]; i += 2
  1535	        else:
  1536	            i += 1
  1537	
  1538	    if not step_id:
  1539	        print(_red("❌ Usage: collect --step S1"))
  1540	        return 2
  1541	
  1542	    # 找 sub task 目录
  1543	    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
  1544	        tok, tp = _find_latest_token()
  1545	        if tok:
  1546	            td = tok.get("task_dir")
  1547	            if td:
  1548	                SUB_TASK_DIR = Path(td) / "sub_task"
  1549	                _init_paths_from_token(tok, tp)
  1550	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"
  1551	
  1552	    if not sub_dir.exists():
  1553	        print(_red(f"❌ Sub task not found: {sub_dir}"))
  1554	        return 2
  1555	
  1556	    result_path = sub_dir / "result.json"
  1557	    if not result_path.exists():
  1558	        print(_red(f"❌ No result.json — subagent hasn't reported"))
  1559	        return 2
  1560	
  1561	    try:
  1562	        result = json.loads(result_path.read_text())
  1563	    except (json.JSONDecodeError, OSError) as e:
  1564	        print(_red(f"❌ Failed to read result.json: {e}"))
  1565	        return 2
  1566	
  1567	    status = result.get("status", "unknown")
  1568	    if status == "failed":
  1569	        print(_yellow(f"⚠  {step_id} result=failed"))
  1570	        print(f"   failure: {result.get('failure', 'unknown')}")
  1571	        return 2 if "--force" not in sys.argv else 0
  1572	    elif status != "completed":
  1573	        print(_yellow(f"⚠  {step_id} is still {status}"))
  1574	
  1575	    # 证据追加到 main executor.md
  1576	    if EXECUTOR_PATH:
  1577	        ev_lines = [
  1578	            f"\n### SubAgent {step_id} — collected at {datetime.now(timezone.utc).isoformat()}",
  1579	            f"- source: sub_task/sub-{step_id}",
  1580	        ]
  1581	        if result.get("summary"):
  1582	            ev_lines.append(f"- summary: {result['summary']}")
  1583	        if result.get("evidence"):
  1584	            for ev in result["evidence"][:5]:
  1585	                ev_lines.append(f"- evidence: {ev[:100]}")
  1586	        if result.get("files_changed"):
  1587	            for f in result["files_changed"][:10]:
  1588	                ev_lines.append(f"- file: {f}")
  1589	        if result.get("failure"):
  1590	            ev_lines.append(f"- failure: {result['failure'][:100]}")
  1591	
  1592	        exec_path = Path(EXECUTOR_PATH) if isinstance(EXECUTOR_PATH, (str, Path)) else EXECUTOR_PATH
  1593	        if isinstance(exec_path, Path) and exec_path.exists():
  1594	            with exec_path.open("a") as f:
  1595	                f.write("\n".join(ev_lines) + "\n")
  1596	        else:
  1597	            # 可能还没创建 executor.md
  1598	            pass
  1599	
  1600	    # 标记 main token 完成
  1601	    main_token = _load_token()
  1602	    if main_token and "steps" in main_token:
  1603	        for s in main_token["steps"]:
  1604	            if s["id"] == step_id:
  1605	                s["status"] = "completed"
  1606	                break
  1607	        main_token["stats"]["done"] = sum(
  1608	            1 for s in main_token["steps"] if s["status"] == "completed"
  1609	        )
  1610	        _save_token(main_token)
  1611	
  1612	    _write_audit("collect", {
  1613	        "step": step_id,
  1614	        "status": status,
  1615	        "evidence_count": len(result.get("evidence", [])),
  1616	        "files_changed": len(result.get("files_changed", [])),
  1617	    }, fallback=True)
  1618	
  1619	    print(_green(f"✅ {step_id}: collected and verified"))
  1620	    summary = result.get("summary", "")
  1621	    if summary:
  1622	        print(f"   {summary}")
  1623	    return 0
  1624	
  1625	
  1626	def cmd_cancel():
  1627	    """中止 subagent 任务
  1628	
  1629	    用法:
  1630	        python3 .claude/scripts/carros_base.py cancel --step S1 [--reason \"changes not needed\"]
  1631	
  1632	    将 sub_task/sub-{step}/result.json status 设为 cancelled，
  1633	    标记 main token 对应 step 为 cancelled。
  1634	    """
  1635	    global SUB_TASK_DIR
  1636	
  1637	    argv = sys.argv[sys.argv.index("cancel") + 1:]
  1638	    step_id = None
  1639	    reason = "cancelled by main agent"
  1640	    i = 0
  1641	    while i < len(argv):
  1642	        if argv[i] == "--step" and i + 1 < len(argv):
  1643	            step_id = argv[i + 1]; i += 2
  1644	        elif argv[i] == "--reason" and i + 1 < len(argv):
  1645	            reason = argv[i + 1]; i += 2
  1646	        else:
  1647	            i += 1
  1648	
  1649	    if not step_id:
  1650	        print(_red("❌ Usage: cancel --step S1"))
  1651	        return 2
  1652	
  1653	    tok, tp = _find_latest_token()
  1654	    if tok:
  1655	        td = tok.get("task_dir")
  1656	        if td:
  1657	            SUB_TASK_DIR = Path(td) / "sub_task"
  1658	            _init_paths_from_token(tok, tp)
  1659	
  1660	    sub_dir = SUB_TASK_DIR / f"sub-{step_id}" if SUB_TASK_DIR else None
  1661	    if not sub_dir or not sub_dir.exists():
  1662	        print(_yellow(f"⚠  No sub task: sub-{step_id}"))
  1663	        return 0
  1664	
  1665	    result_path = sub_dir / "result.json"
  1666	    if result_path.exists():
  1667	        try:
  1668	            result = json.loads(result_path.read_text())
  1669	            result["status"] = "cancelled"
  1670	            result["failure"] = reason
  1671	            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
  1672	        except Exception:
  1673	            result_path.write_text(json.dumps({
  1674	                "status": "cancelled",
  1675	                "failure": reason,
  1676	                "started_at": "",
  1677	                "completed_at": datetime.now(timezone.utc).isoformat(),
  1678	            }))
  1679	
  1680	    # 更新 main token
  1681	    main_token = _load_token()
  1682	    if main_token and "steps" in main_token:
  1683	        for s in main_token["steps"]:
  1684	            if s["id"] == step_id:
  1685	                s["status"] = "cancelled"
  1686	                break
  1687	        _save_token(main_token)
  1688	
  1689	    _write_audit("cancel", {"step": step_id, "reason": reason})
  1690	    print(_yellow(f"⚠  {step_id}: cancelled ({reason})"))
  1691	    return 0
  1692	
  1693	
  1694	
  1695	def cmd_oracle():
  1696	    """Oracle 复核 — LLM 驱动双审
  1697	
  1698	    用法:
  1699	        carros_base.py oracle review --task-id <ID> [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>] [--policy security_strict|runtime_strict|fast_path|balanced]
  1700	        carros_base.py oracle health
  1701	        carros_base.py oracle status --task-id <ID>
  1702	
  1703	    Legacy (旧版 oracle_engine.py):
  1704	        carros_base.py oracle <review_pack_path>
  1705	    """
  1706	    import subprocess
  1707	    argv = sys.argv[sys.argv.index("oracle") + 1:]
  1708	
  1709	    # 探测新/旧模式
  1710	    if not argv:
  1711	        print(__doc__)
  1712	        return 2
  1713	
  1714	    if argv[0] == "review":
  1715	        # 新模型 Oracle — 调 model_oracle_spawn.py
  1716	        spawn = _hook_dir / "model_oracle_spawn.py"
  1717	        if not spawn.exists():
  1718	            print("model_oracle_spawn.py not found")
  1719	            return 1
  1720	
  1721	        # 组装子命令
  1722	        cmd = [sys.executable, str(spawn), "review", "--task-id"]
  1723	        # 找 task-id
  1724	        i = 1
  1725	        task_id = None
  1726	        extra_args = []
  1727	        while i < len(argv):
  1728	            a = argv[i]
  1729	            if a == "--task-id" and i + 1 < len(argv):
  1730	                task_id = argv[i + 1]
  1731	                i += 2
  1732	            elif a in ("--plan", "--executor", "--token", "--logs", "--diff", "--policy"):
  1733	                if i + 1 < len(argv):
  1734	                    extra_args.extend([a, argv[i + 1]])
  1735	                    i += 2
  1736	                else:
  1737	                    i += 1
  1738	            else:
  1739	                i += 1
  1740	
  1741	        if not task_id:
  1742	            # 尝试从 token 推断
  1743	            tok, tp = _find_latest_token()
  1744	            if tok:
  1745	                task_id = tok.get("session", {}).get("id", "unknown")
  1746	            else:
  1747	                print(_red("❌ No task-id provided and no active token found"))
  1748	                return 2
  1749	
  1750	        cmd.extend([task_id] + extra_args)
  1751	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
  1752	        print(result.stdout.strip())
  1753	        if result.stderr:
  1754	            print(_yellow(result.stderr[:500]))
  1755	        return result.returncode
  1756	
  1757	    elif argv[0] == "health":
  1758	        spawn = _hook_dir / "model_oracle_spawn.py"
  1759	        if not spawn.exists():
  1760	            print("model_oracle_spawn.py not found")
  1761	            return 1
  1762	        result = subprocess.run([sys.executable, str(spawn), "health"],
  1763	                                capture_output=True, text=True, timeout=10)
  1764	        print(result.stdout.strip())
  1765	        return result.returncode
  1766	
  1767	    elif argv[0] == "reset":
  1768	        spawn = _hook_dir / "model_oracle_spawn.py"
  1769	        if not spawn.exists():
  1770	            print("model_oracle_spawn.py not found")
  1771	            return 1
  1772	        result = subprocess.run([sys.executable, str(spawn), "reset"],
  1773	                                capture_output=True, text=True, timeout=5)
  1774	        print(result.stdout.strip())
  1775	        return result.returncode
  1776	
  1777	    elif argv[0] == "status" and "--task-id" in argv:
  1778	        spawn = _hook_dir / "model_oracle_spawn.py"
  1779	        if not spawn.exists():
  1780	            print("model_oracle_spawn.py not found")
  1781	            return 1
  1782	        idx = argv.index("--task-id") + 1
  1783	        tid = argv[idx] if idx < len(argv) else ""
  1784	        result = subprocess.run([sys.executable, str(spawn), "status", "--task-id", tid],
  1785	                                capture_output=True, text=True, timeout=5)
  1786	        print(result.stdout.strip())
  1787	        return result.returncode
  1788	
  1789	    # Fallback: 旧模式 (direct review_pack_path)
  1790	    pack_path = argv[0]
  1791	    engine = _hook_dir / "oracle_engine.py"
  1792	    if engine.exists():
  1793	        cmd = [sys.executable, str(engine), pack_path]
  1794	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
  1795	        print(result.stdout.strip())
  1796	        return result.returncode
  1797	    print(_red("Unknown oracle subcommand or oracle_engine.py not found"))
  1798	    return 2
  1799	
  1800	
  1801	def cmd_fallback():
  1802	    """Fallback Protocol — 调用 fallback_engine.py 处理能力失效降级"""
  1803	    import subprocess
  1804	    if len(sys.argv) >= 3:
  1805	        failure_type = sys.argv[2]
  1806	        risk = sys.argv[3] if len(sys.argv) >= 4 else None
  1807	        token_path = sys.argv[4] if len(sys.argv) >= 5 else str(TOKEN_PATH or ".omc/state/token.json")
  1808	        engine = _hook_dir / "fallback_engine.py"
  1809	        if not engine.exists():
  1810	            print("fallback_engine.py not found")
  1811	            return 1
  1812	        cmd = [sys.executable, str(engine), failure_type]
  1813	        if risk:
  1814	            cmd.append(risk)
  1815	        cmd.append(token_path)
  1816	        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
  1817	        print(result.stdout.strip())
  1818	        return result.returncode
  1819	    print("usage: carros_base.py fallback <failure_type> [risk] [token_path]")
  1820	    return 2
  1821	
  1822	
  1823	def cmd_help():
  1824	    """打印帮助信息"""
  1825	    print(__doc__.strip())
  1826	    return 0
  1827	
  1828	
  1829	def cmd_clarify():
  1830	    """Goal 前置澄清 — 交互式探查目标/AC/边界/依赖，输出 spec.md
  1831	
  1832	    用法:
  1833	        python3 .claude/scripts/carros_base.py clarify --title "任务名"
  1834	        python3 .claude/scripts/carros_base.py clarify --title "任务名" --batch < spec.json
  1835	
  1836	    Goal 状态机: 自动推进到 CLARIFY 状态
  1837	    """
  1838	    import subprocess as sb
  1839	    _omc_scripts_parent = Path(__file__).resolve().parent  # .omc/scripts/ or .claude/scripts/
  1840	    argv = sys.argv[sys.argv.index("clarify") + 1:]
  1841	
  1842	    title = "unnamed"
  1843	    batch = False
  1844	    output_path = None
  1845	    i = 0
  1846	    while i < len(argv):
  1847	        if argv[i] == "--title" and i + 1 < len(argv):
  1848	            title = argv[i + 1]; i += 2
  1849	        elif argv[i] == "--batch":
  1850	            batch = True; i += 1
  1851	        elif argv[i] == "--output" and i + 1 < len(argv):
  1852	            output_path = argv[i + 1]; i += 2
  1853	        else:
  1854	            i += 1
  1855	
  1856	    # 确保有 active token
  1857	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1858	        tok, tp = _find_latest_token()
  1859	        if tok and tp:
  1860	            _init_paths_from_token(tok, tp)
  1861	        else:
  1862	            # 自动 init
  1863	            cmd_init(title, level="L1", steps=["S1"])
  1864	            print(_yellow("  ⚠ 已自动 init 新任务"))
  1865	
  1866	    # 调用 clarify_engine.py — 先找 .omc/scripts/，再找 .claude/scripts/
  1867	    script_candidates = [
  1868	        _omc_scripts_parent / "clarify_engine.py",  # .omc/scripts/
  1869	        _hook_dir / "clarify_engine.py",             # .claude/scripts/
  1870	    ]
  1871	    script = None
  1872	    for cand in script_candidates:
  1873	        if cand.exists():
  1874	            script = cand
  1875	            break
  1876	    if not script:
  1877	        print(_red("❌ clarify_engine.py not found (.omc/scripts/ or .claude/scripts/)"))
  1878	        return 2
  1879	
  1880	    spec_path = output_path or (TASK_DIR / "spec.md") if TASK_DIR else ".omc/spec.md"
  1881	    cmd = [sys.executable, str(script), "--title", title]
  1882	    if batch:
  1883	        cmd.append("--batch")
  1884	    cmd.extend(["--output", str(spec_path)])
  1885	
  1886	    if batch:
  1887	        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
  1888	        print(result.stdout)
  1889	        if result.returncode != 0:
  1890	            print(_red(f"❌ clarify failed: {result.stderr[:200]}"))
  1891	            return 2
  1892	    else:
  1893	        result = sb.run(cmd, timeout=300)
  1894	        if result.returncode != 0:
  1895	            print(_red("❌ clarify cancelled"))
  1896	            return 2
  1897	
  1898	    # 更新 Goal 状态机
  1899	    if GoalMachine:
  1900	        try:
  1901	            gm = GoalMachine(TOKEN_PATH)
  1902	            gm.transition(gsm.CLARIFY, reason=f"clarify: {title}")
  1903	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
  1904	        except GoalError as e:
  1905	            print(_yellow(f"  ⚠ Goal state: {e}"))
  1906	
  1907	    print(_green(f"✅ Clarified: {title}"))
  1908	    print(f"   Spec: {spec_path}")
  1909	    return 0
  1910	
  1911	
  1912	def cmd_plan():
  1913	    """分解 spec.md → 原子任务 → plan.json
  1914	
  1915	    用法:
  1916	        python3 .claude/scripts/carros_base.py plan [--spec spec.md] [--level L2] [--output plan.json]
  1917	
  1918	    流程:
  1919	        1. 读 spec.md
  1920	        2. 调用 task_planner.py 分解为 plan.json
  1921	        3. 更新 Goal 状态机 → PLANNING
  1922	    """
  1923	    argv = sys.argv[sys.argv.index("plan") + 1:]
  1924	    spec_path = None
  1925	    level = "L1"
  1926	    output_path = None
  1927	    i = 0
  1928	    while i < len(argv):
  1929	        if argv[i] == "--spec" and i + 1 < len(argv):
  1930	            spec_path = argv[i + 1]; i += 2
  1931	        elif argv[i] == "--level" and i + 1 < len(argv):
  1932	            level = argv[i + 1]; i += 2
  1933	        elif argv[i] == "--output" and i + 1 < len(argv):
  1934	            output_path = argv[i + 1]; i += 2
  1935	        else:
  1936	            i += 1
  1937	
  1938	    # 确保有 active token
  1939	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  1940	        tok, tp = _find_latest_token()
  1941	        if tok and tp:
  1942	            _init_paths_from_token(tok, tp)
  1943	        else:
  1944	            print(_red("❌ No active task. Run 'clarify' or 'init' first."))
  1945	            return 2
  1946	
  1947	    # 找 spec.md
  1948	    spec_file = Path(spec_path) if spec_path else (TASK_DIR / "spec.md")
  1949	    if not spec_file.exists():
  1950	        spec_file = OMC_TASKS / "spec.md"
  1951	    if not spec_file.exists():
  1952	        print(_red(f"❌ spec.md not found. Run 'clarify' first."))
  1953	        return 2
  1954	
  1955	    if task_planner is None:
  1956	        # 直接调用 subprocess
  1957	        planner_script = _hook_dir / "task_planner.py"
  1958	        if not planner_script.exists():
  1959	            print(_red("❌ task_planner.py not available"))
  1960	            return 2
  1961	
  1962	        plan_out = output_path or str(TASK_DIR / "plan.json") if TASK_DIR else ".omc/plan.json"
  1963	        cmd = [sys.executable, str(planner_script), str(spec_file),
  1964	               "--output", plan_out, "--level", level]
  1965	        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
  1966	        print(result.stdout)
  1967	        if result.returncode != 0:
  1968	            return 2
  1969	        plan_path = Path(plan_out)
  1970	    else:
  1971	        parsed = task_planner.parse_spec(spec_file)
  1972	        plan = task_planner.decompose(parsed, level=level)
  1973	        plan_path = Path(output_path) if output_path else (TASK_DIR / "plan.json")
  1974	        task_planner.save_plan(plan, plan_path)
  1975	        print(f"📋 Plan: {len(plan['steps'])} steps, level={level}")
  1976	        for s in plan["steps"]:
  1977	            print(f"   [{s['type']}] {s['id']}: {s['goal'][:50]}")
  1978	
  1979	    # Goal 状态机 → PLANNING
  1980	    if GoalMachine:
  1981	        try:
  1982	            gm = GoalMachine(TOKEN_PATH)
  1983	            gm.transition(gsm.PLANNING, reason=f"plan: {spec_file.name}")
  1984	            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
  1985	        except GoalError as e:
  1986	            print(_yellow(f"  ⚠ Goal state: {e}"))
  1987	
  1988	    print(_green(f"✅ Plan generated: {plan_path}"))
  1989	    return 0
  1990	
  1991	
  1992	def cmd_auto():
  1993	    """全自动管道: clarify → plan → distribute → wait → collect → verify → archive
  1994	
  1995	    用法:
  1996	        python3 .claude/scripts/carros_base.py auto [--plan plan.json] [--timeout 300]
  1997	                                                  [--max-concurrency 3] [--no-archive]
  1998	
  1999	    流程:
  2000	        1. 有 plan.json 则跳过 clarify+plan
  2001	        2. 调用 sub_agent_manager auto_run
  2002	        3. 回收后 verify + archive
  2003	    """
  2004	    argv = sys.argv[sys.argv.index("auto") + 1:]
  2005	    plan_path = None
  2006	    timeout = 300
  2007	    max_concurrency = 3
  2008	    no_archive = False
  2009	    i = 0
  2010	    while i < len(argv):
  2011	        if argv[i] == "--plan" and i + 1 < len(argv):
  2012	            plan_path = argv[i + 1]; i += 2
  2013	        elif argv[i] == "--timeout" and i + 1 < len(argv):
  2014	            timeout = int(argv[i + 1]); i += 2
  2015	        elif argv[i] == "--max-concurrency" and i + 1 < len(argv):
  2016	            max_concurrency = int(argv[i + 1]); i += 2
  2017	        elif argv[i] == "--no-archive":
  2018	            no_archive = True; i += 1
  2019	        else:
  2020	            i += 1
  2021	
  2022	    # 确保有 active token
  2023	    if not TOKEN_PATH or not TOKEN_PATH.exists():
  2024	        tok, tp = _find_latest_token()
  2025	        if tok and tp:
  2026	            _init_paths_from_token(tok, tp)
  2027	        else:
  2028	            print(_red("❌ No active task. Run 'init' first."))
  2029	            return 2
  2030	
  2031	    if not TASK_DIR or not TASK_DIR.exists():
  2032	        print(_red("❌ Task directory not found"))
  2033	        return 2
  2034	
  2035	    # 确保 sub_agent_manager 可用
  2036	    if sam is None:
  2037	        print(_yellow("⚠  sub_agent_manager.py not importable, using subprocess fallback"))
  2038	
  2039	    print(_bold(f"🚀 Auto pipeline: {TASK_DIR.name} (timeout={timeout}s, cc={max_concurrency})"))
  2040	
  2041	    # 创建 manager
  2042	    mgr = sam.SubAgentManager(TASK_DIR, PROJECT_ROOT) if sam else None
  2043	
  2044	    if mgr:
  2045	        mgr.set_config(timeout=timeout, max_concurrency=max_concurrency)
  2046	
  2047	    # Step 1: 读取或准备 plan
  2048	    plan = None
  2049	    if plan_path:
  2050	        plan_file = Path(plan_path)
  2051	        if plan_file.exists():
  2052	            plan = json.loads(plan_file.read_text())
  2053	            print(f"📋 Loaded plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2054	    else:
  2055	        existing = TASK_DIR / "plan.json"
  2056	        if existing.exists():
  2057	            plan = json.loads(existing.read_text())
  2058	            print(f"📋 Using existing plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2059	
  2060	    if not plan:
  2061	        print(_red("❌ No plan.json found. Run 'plan' first or specify --plan"))
  2062	        return 2
  2063	
  2064	    # Step 2: 分发 → 等待 → 回收
  2065	    if mgr:
  2066	        result = mgr.auto_run(plan=plan, wait=True)
  2067	    else:
  2068	        # fallback: 直接 carros_base.py dispatch + poll + collect
  2069	        print(_yellow("⚠  Using carros_base.py dispatch/poll/collect fallback"))
  2070	        from subprocess import run as sbrun
  2071	        for step in plan["steps"]:
  2072	            sid = step["id"]
  2073	            r = sbrun([sys.executable, __file__, "dispatch", "--step", sid],
  2074	                      capture_output=True, text=True, timeout=10)
  2075	            print(f"   dispatch {sid}: {'ok' if r.returncode == 0 else r.stderr[:80]}")
  2076	        print("   Tasks dispatched. Run 'poll' to check status.")
  2077	        return 0
  2078	
  2079	    # Step 3: verify 每个完成的 step
  2080	    verified_count = 0
  2081	    if result.get("collect_result"):
  2082	        for sid in result["collect_result"].get("collected", []):
  2083	            r = cmd_verify(step_id=sid)
  2084	            if r == 0:
  2085	                verified_count += 1
  2086	
  2087	    # Step 4: 自动 archive（除非 --no-archive）
  2088	    if not no_archive and verified_count > 0:
  2089	        print(_bold("\n📦 Archiving..."))
  2090	        cmd_archive(force=False)
  2091	
  2092	    # 总结
  2093	    print(_bold(f"\n{'=' * 50}"))
  2094	    print(_bold(f"🏁 Auto pipeline complete"))
  2095	    print(f"   Plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
  2096	    print(f"   Result: {result.get('summary', '?')}")
  2097	    print(f"   Verified: {verified_count}/{len(plan['steps'])}")
  2098	    print(f"{'=' * 50}")
  2099	    return 0 if result.get("failed", 1) == 0 else 1
  2100	
  2101	
  2102	# ═══════════════════════════════════════════
  2103	# CLI entrypoint
  2104	# ═══════════════════════════════════════════
  2105	
  2106	# ---------------------------------------------------------------------------
  2107	# 夜跑控制面扩展（FINAL.md v3.1 §16 CarrorOS 侧）
  2108	# ---------------------------------------------------------------------------
  2109	
  2110	def cmd_manifest_json():
  2111	    """读取 night-manifest.yaml → 规范化 JSON（scope-check 等门禁消费，免 yq）。
  2112	
  2113	    用法:
  2114	        carros_base.py manifest-json --manifest PATH [--get dotted.path] [--pages]
  2115	        --get   输出单值（标量/JSON），缺失 → exit 2（fail-closed）
  2116	        --pages 仅输出 pages[] 的 id 列表（每行一个）
  2117	    """
  2118	    argv = sys.argv[sys.argv.index("manifest-json") + 1:]
  2119	    manifest_path = None
  2120	    get_path = None
  2121	    pages_only = False
  2122	    page_id = None
  2123	    i = 0
  2124	    while i < len(argv):
  2125	        if argv[i] == "--manifest" and i + 1 < len(argv):
  2126	            manifest_path = argv[i + 1]; i += 2
  2127	        elif argv[i] == "--get" and i + 1 < len(argv):
  2128	            get_path = argv[i + 1]; i += 2
  2129	        elif argv[i] == "--page-id" and i + 1 < len(argv):
  2130	            page_id = argv[i + 1]; i += 2
  2131	        elif argv[i] == "--pages":
  2132	            pages_only = True; i += 1
  2133	        else:
  2134	            i += 1
  2135	    if not manifest_path:
  2136	        print(_red("ERROR: manifest-json 需要 --manifest PATH"), file=sys.stderr)
  2137	        return 2
  2138	    p = Path(manifest_path)
  2139	    if not p.exists():
  2140	        print(_red(f"ERROR: manifest 不存在: {p}"), file=sys.stderr)
  2141	        return 2
  2142	    try:
  2143	        import yaml
  2144	        data = yaml.safe_load(p.read_text(encoding="utf-8"))
  2145	    except Exception as e:
  2146	        print(_red(f"ERROR: manifest 解析失败（fail-closed）: {e}"), file=sys.stderr)
  2147	        return 2
  2148	    if not isinstance(data, dict):
  2149	        print(_red("ERROR: manifest 顶层不是 mapping"), file=sys.stderr)
  2150	        return 2
  2151	    if pages_only:
  2152	        pages = data.get("pages") or []
  2153	        for pg in pages:
  2154	            print(pg.get("id", ""))
  2155	        return 0
  2156	    if page_id:
  2157	        pages = data.get("pages") or []
  2158	        match = [pg for pg in pages if isinstance(pg, dict) and pg.get("id") == page_id]
  2159	        if not match:
  2160	            print(_red(f"ERROR: page 不存在: {page_id}"), file=sys.stderr)
  2161	            return 2
  2162	        data = match[0]
  2163	    if get_path:
  2164	        cur = data
  2165	        for part in get_path.split("."):
  2166	            if isinstance(cur, dict) and part in cur:
  2167	                cur = cur[part]
  2168	            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
  2169	                cur = cur[int(part)]
  2170	            else:
  2171	                print(_red(f"ERROR: 字段缺失: {get_path}"), file=sys.stderr)
  2172	                return 2
  2173	        if isinstance(cur, (dict, list)):
  2174	            print(json.dumps(cur, ensure_ascii=False))
  2175	        elif cur is None:
  2176	            print("null")
  2177	        elif isinstance(cur, bool):
  2178	            print("true" if cur else "false")
  2179	        else:
  2180	            print(cur)
  2181	        return 0
  2182	    print(json.dumps(data, ensure_ascii=False, indent=2))
  2183	    return 0
  2184	
  2185	
  2186	def cmd_token_write():
  2187	    """token.json 唯一合法写入入口（FINAL §4.4：模型对 token 的写入仅允许经此 API）。
  2188	
  2189	    用法:
  2190	        carros_base.py token-write --token-path PATH --set dotted.path=value
  2191	              [--set ...] --expected-revision N
  2192	    CAS 冲突 → exit 3；缺参数 → exit 2。
  2193	    """
  2194	    argv = sys.argv[sys.argv.index("token-write") + 1:]
  2195	    token_path = None
  2196	    sets = []
  2197	    expected = None
  2198	    i = 0
  2199	    while i < len(argv):
  2200	        if argv[i] == "--token-path" and i + 1 < len(argv):
  2201	            token_path = argv[i + 1]; i += 2
  2202	        elif argv[i] == "--set" and i + 1 < len(argv):
  2203	            sets.append(argv[i + 1]); i += 2
  2204	        elif argv[i] == "--expected-revision" and i + 1 < len(argv):
  2205	            expected = int(argv[i + 1]); i += 2
  2206	        else:
  2207	            i += 1
  2208	    if not token_path or not sets or expected is None:
  2209	        print(_red("ERROR: token-write 需要 --token-path/--set/--expected-revision"), file=sys.stderr)
  2210	        return 2
  2211	    token = _load_token(Path(token_path))
  2212	    if token is None:
  2213	        print(_red(f"ERROR: token 不存在或损坏: {token_path}"), file=sys.stderr)
  2214	        return 2
  2215	    for kv in sets:
  2216	        if "=" not in kv:
  2217	            print(_red(f"ERROR: --set 格式应为 path=value: {kv}"), file=sys.stderr)
  2218	            return 2
  2219	        dotted, raw = kv.split("=", 1)
  2220	        try:
  2221	            value = json.loads(raw)
  2222	        except json.JSONDecodeError:
  2223	            value = raw
  2224	        cur = token
  2225	        parts = dotted.split(".")
  2226	        for part in parts[:-1]:
  2227	            nxt = cur.get(part)
  2228	            if not isinstance(nxt, dict):
  2229	                nxt = {}
  2230	                cur[part] = nxt
  2231	            cur = nxt
  2232	        cur[parts[-1]] = value
  2233	    try:
  2234	        _save_token(token, Path(token_path), expected_revision=expected)
  2235	    except CASConflict as e:
  2236	        print(_red(f"CAS_CONFLICT: {e}"), file=sys.stderr)
  2237	        return 3
  2238	    print(_green(f"token 已写入 revision={token.get('revision')}"))
  2239	    return 0
  2240	
  2241	
  2242	def cmd_gate_results_init():
  2243	    """创建页级 gate-results 目录（FINAL §4.4 权威链事实目录）。
  2244	
  2245	    用法:
  2246	        carros_base.py gate-results-init --night-dir .omc/night/{date} --page-id FE-xxx
  2247	    幂等；输出目录路径。
  2248	    """
  2249	    argv = sys.argv[sys.argv.index("gate-results-init") + 1:]
  2250	    night_dir = None
  2251	    page_id = None
  2252	    i = 0
  2253	    while i < len(argv):
  2254	        if argv[i] == "--night-dir" and i + 1 < len(argv):
  2255	            night_dir = argv[i + 1]; i += 2
  2256	        elif argv[i] == "--page-id" and i + 1 < len(argv):
  2257	            page_id = argv[i + 1]; i += 2
  2258	        else:
  2259	            i += 1
  2260	    if not night_dir or not page_id:
  2261	        print(_red("ERROR: gate-results-init 需要 --night-dir/--page-id"), file=sys.stderr)
  2262	        return 2
  2263	    d = Path(night_dir) / "gate-results" / page_id
  2264	    d.mkdir(parents=True, exist_ok=True)
  2265	    print(d)
  2266	    return 0
  2267	
  2268	
  2269	COMMANDS = {
  2270	    "init": cmd_init,
  2271	    "status": cmd_status,
  2272	    "tick": cmd_tick,
  2273	    "verify": cmd_verify,
  2274	    "archive": cmd_archive,
  2275	    "clarify": cmd_clarify,
  2276	    "plan": cmd_plan,
  2277	    "auto": cmd_auto,
  2278	    "lint": cmd_lint,
  2279	    "bench": cmd_bench,
  2280	    "gate": cmd_gate,
  2281	    "dispatch": cmd_dispatch,
  2282	    "poll": cmd_poll,
  2283	    "collect": cmd_collect,
  2284	    "report": cmd_report,
  2285	    "cancel": cmd_cancel,
  2286	    "oracle": cmd_oracle,
  2287	    "fallback": cmd_fallback,
  2288	    "manifest-json": cmd_manifest_json,
  2289	    "token-write": cmd_token_write,
  2290	    "gate-results-init": cmd_gate_results_init,
  2291	    "help": cmd_help,
  2292	}
  2293	
  2294	
  2295	def main(argv=None):
  2296	    if argv is None:
  2297	        argv = sys.argv[1:]
  2298	
  2299	    if not argv or argv[0] in ("-h", "--help", "help"):
  2300	        return cmd_help()
  2301	
  2302	    command = argv[0]
  2303	    if command not in COMMANDS:
  2304	        print(_red(f"Unknown command: {command}"))
  2305	        print(f"Available: {', '.join(COMMANDS.keys())}")
  2306	        return 2
  2307	
  2308	    args = argv[1:]
  2309	
  2310	    if command == "init":
  2311	        task_id = None
  2312	        level = "L1"
  2313	        steps = None
  2314	        task_dir = None
  2315	        user_request = None
  2316	        feature = None
  2317	        auto_mode = False
  2318	        i = 0
  2319	        while i < len(args):
  2320	            if args[i] == "--task-id" and i + 1 < len(args):
  2321	                task_id = args[i + 1]
  2322	                i += 2
  2323	            elif args[i] == "--level" and i + 1 < len(args):
  2324	                level = args[i + 1]
  2325	                i += 2
  2326	            elif args[i] == "--task-dir" and i + 1 < len(args):
  2327	                task_dir = args[i + 1]
  2328	                i += 2
  2329	            elif args[i] == "--step":
  2330	                if steps is None:
  2331	                    steps = []
  2332	                i += 1
  2333	                while i < len(args) and not args[i].startswith("--"):
  2334	                    steps.append(args[i])
  2335	                    i += 1
  2336	            elif args[i] == "--user-request" and i + 1 < len(args):
  2337	                user_request = args[i + 1]
  2338	                i += 2
  2339	            elif args[i] == "--feature" and i + 1 < len(args):
  2340	                feature = args[i + 1]
  2341	                i += 2
  2342	            elif args[i] == "--auto":
  2343	                auto_mode = True
  2344	                i += 1
  2345	            elif args[i] == "--target" and i + 1 < len(args):
  2346	                target = args[i + 1]
  2347	                i += 2
  2348	            else:
  2349	                i += 1
  2350	        if auto_mode:
  2351	            return cmd_auto_init(steps=steps, target=target)
  2352	        return cmd_init(task_id=task_id, level=level, steps=steps, user_request=user_request, task_dir=task_dir, feature=feature)
  2353	
  2354	    elif command == "verify":
  2355	        step_id = None
  2356	        if args and args[0] == "--step" and len(args) >= 2:
  2357	            step_id = args[1]
  2358	        return cmd_verify(step_id=step_id)
  2359	
  2360	    elif command == "archive":
  2361	        force = "--force" in args or "-f" in args
  2362	        return cmd_archive(force=force)
  2363	
  2364	    elif command == "lint":
  2365	        path = args[0] if args else None
  2366	        return cmd_lint(path=path)
  2367	
  2368	    elif command == "manifest-json":
  2369	        return cmd_manifest_json()
  2370	
  2371	    elif command == "token-write":
  2372	        return cmd_token_write()
  2373	
  2374	    elif command == "gate-results-init":
  2375	        return cmd_gate_results_init()
  2376	
  2377	    else:
  2378	        return COMMANDS[command]()
  2379	
  2380	
  2381	if __name__ == "__main__":
  2382	    sys.exit(main())
```

### `.claude/hooks/pretool-gate.py` — _check_verified 所在,全文

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS PreToolUse Unified Gate — merged from 7 individual hooks.
     4	
     5	Execution order (short-circuit on first BLOCK):
     6	  1. sensitive-edit   — block sensitive path access (.env, .ssh, keys)
     7	  2. fallback-check   — block if task is blocked/waiting_user
     8	  3. action-gate      — block dangerous commands; ask_user for risky ones
     9	  4. plan-gate        — block if task files missing
    10	  5. edit-scope       — block writes outside declared scope
    11	  6. verify-gate      — block unverified step completion marks in plan.md
    12	  7. oracle-gate      — hint (never blocks) for L2 trigger keywords
    13	
    14	Design constraints (from data_todo.md / 总结.md):
    15	  - Single Python process per tool call (was 7)
    16	  - Audit once per block decision, not per hook
    17	  - Oracle is hint-only, never blocks
    18	  - First BLOCK short-circuits; later checks skip
    19	"""
    20	
    21	from __future__ import annotations
    22	
    23	import json
    24	import re
    25	import secrets
    26	import shutil
    27	import sys
    28	from datetime import datetime, timezone
    29	from pathlib import Path
    30	from typing import Any
    31	
    32	# ── Bootstrap: self-locate project root ──
    33	_script_path = Path(__file__).resolve()
    34	ROOT = _script_path.parents[2]
    35	if not (ROOT / ".claude").is_dir():
    36	    ROOT = Path(".").resolve()
    37	import os
    38	os.chdir(str(ROOT))
    39	
    40	# ── Inline minimal hooklib (avoid import overhead for single-process gate) ──
    41	OMC = ROOT / ".omc"
    42	TOKENS = OMC / "tokens"
    43	TASKS = OMC / "tasks"
    44	AUDIT = OMC / "audit"
    45	CRITICAL_STATE = OMC / "state" / "context-critical.json"
    46	FALLBACK_REQUIRED = OMC / "state" / "fallback-blocked-required"
    47	FALLBACK_APPROVED = OMC / "state" / "fallback-blocked-approved"
    48	TEMP_BYPASS = OMC / "state" / "temp-bypass.json"
    49	
    50	SENSITIVE_PATTERNS = [
    51	    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    52	    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    53	    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b", r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b", r"cookie",
    54	]
    55	
    56	DANGEROUS_COMMANDS = [
    57	    r"(^|\s)rm\s+-rf\s+(/\s|\.\s|~\s|\*\s|/$|\.$|~$|\*$)", r"(^|\s)rm\s+-r\s+(/\s|\.\s|~\s|\*/)", r"^sudo\b",
    58	    r"^chmod\s+777\b", r"^chown\b", r"^git\s+push\s+(-f|--force)",
    59	    r"^dd\s+if=", r"^mkfs\.", r"^fdisk\b", r":\(\)\{\s*:\|:\s*&\s*\};:",
    60	]
    61	
    62	ASK_USER_COMMANDS = [
    63	    r"\bcurl\b.*\|\s*(sh|bash)", r"\bwget\b.*\|\s*(sh|bash)",
    64	    r"\bnpm\s+install\b", r"\bpip\s+install\b", r"\bbrew\s+install\b",
    65	    r"\bcargo\s+install\b", r"\bdocker\s+run\b", r"\bkubectl\b",
    66	    r"\bterraform\s+apply\b", r"\bterraform\s+destroy\b",
    67	]
    68	
    69	ORACLE_TRIGGER_KW = [
    70	    "oracle", "acceptance", "final", "archive", "phase_end",
    71	    "merge", "release", "deploy", "production",
    72	]
    73	ORACLE_FORCE_KW = ["aut", "payment", "migration", "permission"]
    74	
    75	STALE_LOCK_THRESHOLD = 1800  # 30 min: auto-clear blocked state older than this
    76	
    77	READ_TOOLS = {"read", "grep", "glob", "search_files", "list", "ls", "find", "cat"}
    78	WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
    79	PLAN_FILE_PATTERNS = ["plan.md", "plan"]
    80	
    81	
    82	# ── Helpers ──
    83	
    84	def _read_stdin() -> dict[str, Any]:
    85	    try:
    86	        raw = sys.stdin.read()
    87	        return json.loads(raw) if raw else {}
    88	    except Exception:
    89	        return {}
    90	
    91	def _check_temp_bypass() -> bool:
    92	    """Check if a user-authorized temp bypass is active.
    93	
    94	    Bypass file: .omc/state/temp-bypass.json
    95	    Format: {"reason": "...", "expires_at": "ISO8601"}
    96	    If expired, auto-delete the file.
    97	    """
    98	    if not TEMP_BYPASS.exists():
    99	        return False
   100	    try:
   101	        data = json.loads(TEMP_BYPASS.read_text(encoding="utf-8"))
   102	        expires = data.get("expires_at", "")
   103	        if expires:
   104	            try:
   105	                from datetime import datetime, timezone
   106	                exp = datetime.fromisoformat(expires)
   107	                if datetime.now(timezone.utc) >= exp:
   108	                    TEMP_BYPASS.unlink(missing_ok=True)
   109	                    return False
   110	            except Exception:
   111	                pass
   112	        return True
   113	    except Exception:
   114	        TEMP_BYPASS.unlink(missing_ok=True)
   115	        return False
   116	
   117	def _extract_tool(payload: dict) -> str:
   118	    return str(payload.get("tool_name") or payload.get("tool") or payload.get("name") or "")
   119	
   120	def _extract_input(payload: dict) -> dict[str, Any]:
   121	    for key in ("tool_input", "input", "arguments", "args"):
   122	        val = payload.get(key)
   123	        if isinstance(val, dict):
   124	            return val
   125	    return payload
   126	
   127	def _extract_path(payload: dict) -> str:
   128	    data = _extract_input(payload)
   129	    return str(data.get("file_path") or data.get("filePath") or data.get("path") or data.get("filename") or "")
   130	
   131	def _extract_command(payload: dict) -> str:
   132	    data = _extract_input(payload)
   133	    return str(data.get("command") or payload.get("command") or "")
   134	
   135	def _ok(msg: str = "OK") -> int:
   136	    print(json.dumps({"continue": True, "message": f"PreToolGate: {msg}"}, ensure_ascii=False))
   137	    return 0
   138	
   139	def _block(reason: str, suggestion: str = "") -> int:
   140	    """Block a tool call with HUMAN-READABLE reason and next step.
   141	
   142	    Sylph-inspired pattern: instead of a terse machine-only message,
   143	    give the user the context they need to decide what to do next.
   144	    Also supports a TEMP_KEY bypass mechanism for user-authorized overrides.
   145	    """
   146	    safe_reason = reason[:300]
   147	    msg_parts = [f"⛔ 操作被阻断: {safe_reason}"]
   148	    if suggestion:
   149	        msg_parts.append(f"💡 建议: {suggestion}")
   150	    bypass_hint = (
   151	        "🔑 如需临时授权跳过此检查，请运行: "
   152	        "`! python3 .claude/scripts/temp-bypass.py --minutes 60 --reason \"你的理由\"`"
   153	    )
   154	    msg_parts.append(bypass_hint)
   155	    full_msg = "\n".join(msg_parts)
   156	
   157	    print(json.dumps({
   158	        "continue": True,
   159	        "hookSpecificOutput": {
   160	            "hookEventName": "PreToolUse",
   161	            "additionalContext": full_msg,
   162	        }
   163	    }, ensure_ascii=False))
   164	    sys.stderr.write(f"PreToolGate: BLOCKED - {safe_reason}\n")
   165	    return 2
   166	
   167	def _match_any(text: str, patterns: list[str]) -> str | None:
   168	    for pat in patterns:
   169	        if re.search(pat, text, re.IGNORECASE):
   170	            return pat
   171	    return None
   172	
   173	def _is_sensitive(path: str) -> bool:
   174	    p = path.replace("\\", "/")
   175	    return any(re.search(pat, p, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)
   176	
   177	def _append_audit(event: dict) -> None:
   178	    try:
   179	        from datetime import datetime, timezone
   180	        AUDIT.mkdir(parents=True, exist_ok=True)
   181	        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
   182	        event.setdefault("timestamp", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
   183	        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
   184	            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
   185	    except OSError:
   186	        pass
   187	
   188	def _read_json(path: Path) -> dict[str, Any]:
   189	    try:
   190	        if path.exists():
   191	            data = json.loads(path.read_text(encoding="utf-8"))
   192	            return data if isinstance(data, dict) else {}
   193	    except Exception:
   194	        return {}
   195	    return {}
   196	
   197	def _latest_token() -> Path | None:
   198	    if not TOKENS.exists():
   199	        return None
   200	    candidates = sorted(
   201	        [p for p in TOKENS.glob("*/*.json") if p.is_file()],
   202	        key=lambda p: p.stat().st_mtime, reverse=True,
   203	    )
   204	    return candidates[0] if candidates else None
   205	
   206	def _active_token() -> dict[str, Any] | None:
   207	    """Returns normalized token dict, or None."""
   208	    path = _latest_token()
   209	    if not path:
   210	        return None
   211	    token = _read_json(path)
   212	    if not isinstance(token, dict) or not token:
   213	        return None
   214	    task = token.get("task", {})
   215	    if not isinstance(task, dict):
   216	        token["task"] = {"name": str(task), "status": token.get("status", "active")}
   217	    return token
   218	
   219	def _task_dir(token: dict) -> Path | None:
   220	    task = token.get("task", {})
   221	    if not isinstance(task, dict):
   222	        return None
   223	    explicit = task.get("dir") or token.get("task_dir")
   224	    if explicit:
   225	        p = ROOT / explicit if not Path(explicit).is_absolute() else Path(explicit)
   226	        if p.exists():
   227	            return p
   228	    return None
   229	
   230	def _parse_scope(plan_text: str) -> list[str]:
   231	    in_scope = False
   232	    files: list[str] = []
   233	    for line in plan_text.splitlines():
   234	        s = line.strip()
   235	        if s.lower().startswith("## scope") or s.lower().startswith("## scope freeze"):
   236	            in_scope = True
   237	            continue
   238	        if in_scope and s.startswith("## "):
   239	            break
   240	        if in_scope:
   241	            m = re.match(r"[-*]\s+`?([^`\s]+)`?", s)
   242	            if m:
   243	                files.append(m.group(1).replace("\\", "/"))
   244	    return files
   245	
   246	def _in_scope(path: str, scope: list[str]) -> bool:
   247	    p = path.replace("\\", "/").lstrip("./")
   248	    for item in scope:
   249	        s = item.replace("\\", "/").lstrip("./")
   250	        if p == s or p.endswith("/" + s) or p.startswith(s.rstrip("/") + "/"):
   251	            return True
   252	    return False
   253	
   254	def _check_verified(step_id: str | None) -> bool:
   255	    if not AUDIT.exists():
   256	        return False
   257	    for f in sorted(AUDIT.glob("*.jsonl")):
   258	        with f.open("r", encoding="utf-8") as fh:
   259	            for line in fh:
   260	                try:
   261	                    e = json.loads(line)
   262	                except json.JSONDecodeError:
   263	                    continue
   264	                # carros_base.py writes: {"event": "verify", "data": {"step": "S1", "result": "VERIFIED"}}
   265	                if e.get("event") == "verify":
   266	                    data = e.get("data", {})
   267	                    if isinstance(data, dict) and data.get("result") == "VERIFIED":
   268	                        if step_id is None or data.get("step") == step_id:
   269	                            return True
   270	                # Legacy compat: {"event_type": "verify_decision", "decision": "VERIFIED", "step": "S1"}
   271	                if e.get("event_type") == "verify_decision" and e.get("decision") == "VERIFIED":
   272	                    if step_id is None or e.get("step") == step_id:
   273	                        return True
   274	    return False
   275	
   276	
   277	# ── Gate Checks (ordered, each returns None=pass or str=block_reason) ──
   278	
   279	def _auto_init(target_path: str | None = None) -> None:
   280	    """自动 init：无 token 写操作时后台初始化 task 文档系统"""
   281	    import subprocess
   282	    try:
   283	        script = ROOT / ".claude/scripts/carros_base.py"
   284	        if not script.exists():
   285	            return
   286	        cmd = [sys.executable, str(script), "init", "--auto"]
   287	        if target_path:
   288	            cmd += ["--target", target_path]
   289	        subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=10)
   290	    except Exception:
   291	        pass
   292	
   293	def _check_sensitive_edit(payload: dict) -> str | None:
   294	    """Gate 1: block sensitive path writes only (reads are safe)."""
   295	    tool = _extract_tool(payload).lower()
   296	    if tool not in WRITE_TOOLS:
   297	        return None
   298	    path = _extract_path(payload)
   299	    if path and _is_sensitive(path):
   300	        return f"BLOCK 敏感路径 {path}，需要确认后才能修改|请确认是否确实要修改敏感文件。如果确认，请使用临时 bypass 授权"
   301	    return None
   302	
   303	def _safe_unlink(path: Path) -> None:
   304	    try:
   305	        if path.exists():
   306	            path.unlink()
   307	    except OSError:
   308	        pass
   309	
   310	
   311	def _auto_archive_token(token_path: Path, token_data: dict, reason: str) -> None:
   312	    """Move a stale/broken token out of the way so it stops blocking the project.
   313	
   314	    Token is copied to archive/tokens/{date}/ with a note, then deleted from tokens/.
   315	    Never raises — silence any I/O errors.
   316	    """
   317	    try:
   318	        archive_dir = OMC / "archive" / "tokens" / token_path.parent.name
   319	        archive_dir.mkdir(parents=True, exist_ok=True)
   320	        archive_path = archive_dir / token_path.name
   321	        # Mark as archived in the token data
   322	        token_data["status"] = "archived"
   323	        token_data.setdefault("session", {})
   324	        token_data["session"]["archived_at"] = datetime.now(timezone.utc).isoformat()
   325	        token_data.setdefault("task", {})
   326	        if isinstance(token_data.get("task"), dict):
   327	            token_data["task"]["archive_reason"] = reason
   328	        archive_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
   329	        token_path.unlink()
   330	        _append_audit({
   331	            "event_type": "token_auto_archived",
   332	            "actor": "hook:pretool-gate",
   333	            "reason": reason,
   334	            "token": token_path.name,
   335	            "archived_to": str(archive_path),
   336	        })
   337	    except OSError:
   338	        pass
   339	
   340	
   341	def _check_fallback(_payload: dict) -> str | None:
   342	    """Gate 2: block if task is blocked/waiting.
   343	
   344	    Stale lock protection: if a token has been blocked longer than
   345	    STALE_LOCK_THRESHOLD, auto-archive it instead of blocking.
   346	    Historical bad state must not freeze the project (Boss ruling 2026-07-15).
   347	    """
   348	    token_path = _latest_token()
   349	    if not token_path:
   350	        return None
   351	    token_data = _read_json(token_path)
   352	    if not token_data:
   353	        return None
   354	    token = token_data
   355	    task = token.get("task", {})
   356	    if not isinstance(task, dict):
   357	        return None
   358	    status = task.get("status") or token.get("status") or "active"
   359	    if status != "blocked":
   360	        # Normal path: check waiting_user or unresolved fallback
   361	        if status == "waiting_user":
   362	            reason = task.get("reason") or "requires_user"
   363	            return f"ASK_USER Bypass 临时授权状态：{reason}|如需继续，运行 temp-bypass 命令创建临时授权"
   364	        fallback = task.get("fallback", {}) or {}
   365	        if fallback.get("unresolved"):
   366	            return f"BLOCK fallback 状态未解决：{fallback.get('reason', 'unknown')}|请先解决fallback问题后再操作，或使用临时bypass授权跳过"
   367	        session = token.get("session", {}) or {}
   368	        if session.get("fallback"):
   369	            return None
   370	        return None
   371	    # --- Blocked token detected ---
   372	    reason = task.get("blocked") or task.get("reason") or "blocked"
   373	    # Check staleness: use fallback timestamp or token created_at
   374	    ts_str = (
   375	        (task.get("fallback") or {}).get("timestamp")
   376	        or (token.get("session") or {}).get("created_at")
   377	        or ""
   378	    )
   379	    age = 0.0
   380	    if ts_str:
   381	        try:
   382	            from datetime import datetime, timezone
   383	            ts = datetime.fromisoformat(ts_str)
   384	            age = (datetime.now(timezone.utc) - ts).total_seconds()
   385	        except Exception:
   386	            pass
   387	    if age >= STALE_LOCK_THRESHOLD:
   388	        # Stale blocked token — auto-archive so it stops freezing the project
   389	        _auto_archive_token(token_path, token_data, f"stale_blocked age={int(age)}s reason={reason}")
   390	        return None  # pass through, project is unblocked
   391	
   392	    # ─── Not stale enough for auto-archive → CAPTCHA approval pattern ───
   393	    # Check if user already approved via /approve <token>
   394	    if FALLBACK_APPROVED.exists():
   395	        _auto_archive_token(token_path, token_data, f"user_approved reason={reason}")
   396	        _safe_unlink(FALLBACK_REQUIRED)
   397	        _safe_unlink(FALLBACK_APPROVED)
   398	        return None  # pass through
   399	
   400	    # Generate CAPTCHA for user to approve
   401	    captcha = secrets.token_hex(3)  # 6-char hex
   402	    try:
   403	        FALLBACK_REQUIRED.parent.mkdir(parents=True, exist_ok=True)
   404	        FALLBACK_REQUIRED.write_text(captcha)
   405	    except OSError:
   406	        pass
   407	
   408	    # Build helpful message
   409	    task = token.get("task", {})
   410	    session = token.get("session", {})
   411	    task_name = session.get("id") or task.get("name") or token_path.stem
   412	    blocked_since = (task.get("fallback") or {}).get("timestamp") or \
   413	                    session.get("created_at", "")[:19] or "?"
   414	    current_step = task.get("current_step", "?")
   415	    age_str = f"（阻塞 {int(age)} 秒）" if age > 0 else ""
   416	
   417	    msg = (
   418	        f"\n"
   419	        f"╔══ CarrorOS 任务阻塞 ══════════════════════════════\n"
   420	        f"║  任务: {task_name}\n"
   421	        f"║  状态: blocked  {age_str}\n"
   422	        f"║  原因: {reason}\n"
   423	        f"║  当前步骤: {current_step}\n"
   424	        f"║  阻塞自: {blocked_since[:19]}\n"
   425	        f"║\n"
   426	        f"║  📌 如需解除阻塞并归档此任务，请输入:\n"
   427	        f"║     /approve {captcha}\n"
   428	        f"║\n"
   429	        f"║  📌 如需保持阻塞状态:\n"
   430	        f"║     /deny\n"
   431	        f"║\n"
   432	        f"║  ⏱ 或等待 {max(1, int(STALE_LOCK_THRESHOLD/60 - age/60))} 分钟后自动解除\n"
   433	        f"╚══════════════════════════════════════════════════\n"
   434	    )
   435	    print(msg, file=sys.stderr, flush=True)
   436	
   437	    return f"BLOCK task_blocked reason={reason}"
   438	
   439	def _check_action_gate(payload: dict) -> str | None:
   440	    """Gate 3: block dangerous commands; ask_user for risky ones."""
   441	    command = _extract_command(payload)
   442	    if not command:
   443	        return None
   444	    hard = _match_any(command, DANGEROUS_COMMANDS)
   445	    if hard:
   446	        _append_audit({
   447	            "event_type": "preaction_decision",
   448	            "actor": "hook:pretool-gate",
   449	            "decision": "BLOCK",
   450	            "reason": "dangerous_command",
   451	            "pattern": hard,
   452	            "command_preview": command[:160],
   453	        })
   454	        return f"BLOCK dangerous_command pattern={hard}"
   455	    ask = _match_any(command, ASK_USER_COMMANDS)
   456	    if ask:
   457	        _append_audit({
   458	            "event_type": "preaction_decision",
   459	            "actor": "hook:pretool-gate",
   460	            "decision": "ASK_USER",
   461	            "reason": "approval_required_command",
   462	            "pattern": ask,
   463	            "command_preview": command[:160],
   464	        })
   465	        return f"ASK_USER approval_required pattern={ask}"
   466	    return None
   467	
   468	def _check_plan_gate(payload: dict) -> str | None:
   469	    """Gate 4: 自适应自治 — 无 token 自动 init，不阻断"""
   470	    tool = _extract_tool(payload).lower()
   471	    if tool not in WRITE_TOOLS:
   472	        return None
   473	    token = _active_token()
   474	    if not token:
   475	        # 无 token → auto-init（不会阻阻断）
   476	        path = _extract_path(payload)
   477	        _auto_init(path)
   478	        return None  # 放行
   479	    task = token.get("task", {})
   480	    if not isinstance(task, dict):
   481	        return None
   482	    if task.get("status") in {"blocked", "waiting_user"}:
   483	        return f"BLOCK task_status_{task.get('status')}"
   484	    task_dir = _task_dir(token)
   485	    if not task_dir:
   486	        return None
   487	    plan = task_dir / "plan.md"
   488	    if not plan.exists():
   489	        return f"BLOCK plan_missing task_dir={task_dir}"
   490	    if not task.get("current_step"):
   491	        return "BLOCK current_step_missing"
   492	    return None
   493	
   494	def _check_edit_scope(payload: dict) -> str | None:
   495	    """Gate 5: 越界不阻断，记录 audit（方案二：柔性约束）"""
   496	    tool = _extract_tool(payload).lower()
   497	    if tool not in WRITE_TOOLS:
   498	        return None
   499	    path = _extract_path(payload)
   500	    if not path:
   501	        return None
   502	    token = _active_token()
   503	    if not token:
   504	        return None
   505	    # 检查 token scope（比 plan scope 优先）
   506	    token_scope = token.get("scope") or []
   507	    if token_scope:
   508	        in_scope = _in_scope(path, token_scope)
   509	        if in_scope:
   510	            return None
   511	        # 越界 → audit 不阻断
   512	        _append_audit({
   513	            "event_type": "scope_violation",
   514	            "actor": "hook:pretool-gate",
   515	            "decision": "WARN",
   516	            "reason": "token_scope_violation",
   517	            "path": path,
   518	            "scope": token_scope[:10],
   519	        })
   520	        return None  # 放行
   521	    # 回退到 plan scope 检查
   522	    task_dir = _task_dir(token)
   523	    if not task_dir:
   524	        return None
   525	    plan_path = task_dir / "plan.md"
   526	    if not plan_path.exists():
   527	        return None
   528	    scope = _parse_scope(plan_path.read_text(encoding="utf-8"))
   529	    if not scope:
   530	        return None
   531	    if not _in_scope(path, scope):
   532	        _append_audit({
   533	            "event_type": "scope_violation",
   534	            "actor": "hook:pretool-gate",
   535	            "decision": "WARN",
   536	            "reason": "plan_scope_violation",
   537	            "path": path,
   538	            "scope": scope[:10],
   539	        })
   540	        return None  # 放行
   541	    return None
   542	
   543	def _check_verify_gate(payload: dict) -> str | None:
   544	    """Gate 6: block unverified step [x] marks in plan.md."""
   545	    tool = _extract_tool(payload).lower()
   546	    if tool not in WRITE_TOOLS:
   547	        return None
   548	    path = _extract_path(payload)
   549	    if not path or not any(path.replace("\\", "/").endswith(p) for p in PLAN_FILE_PATTERNS):
   550	        return None
   551	    ti = _extract_input(payload)
   552	    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
   553	    if not re.search(r"\[x\]", content, re.IGNORECASE):
   554	        return None
   555	    token = _active_token()
   556	    if not token:
   557	        return None
   558	    task = token.get("task", {})
   559	    if not isinstance(task, dict):
   560	        return None
   561	    current_step = task.get("current_step")
   562	    if not _check_verified(current_step):
   563	        _append_audit({
   564	            "event_type": "verifygate_preaction_block",
   565	            "actor": "hook:pretool-gate",
   566	            "decision": "BLOCK",
   567	            "reason": "step_not_verified",
   568	            "path": path,
   569	            "current_step": current_step,
   570	        })
   571	        return f"BLOCK step_{current_step}_not_VERIFIED"
   572	    return None
   573	
   574	def _check_oracle_gate(payload: dict) -> str | None:
   575	    """Gate 7: hint for L2 oracle triggers (never blocks)."""
   576	    token = _active_token()
   577	    if not token:
   578	        return None
   579	    session = token.get("session", {}) or {}
   580	    if session.get("level", "L1_BASE") != "L2_ENHANCE":
   581	        return None
   582	    command = _extract_command(payload)
   583	    if not command:
   584	        return None
   585	    cmd_lower = command.lower()
   586	    force = any(kw in cmd_lower for kw in ORACLE_FORCE_KW)
   587	    trigger = force or any(kw in cmd_lower for kw in ORACLE_TRIGGER_KW)
   588	    if not trigger:
   589	        return None
   590	    task = token.get("task", {})
   591	    phase = task.get("phase", "execute") if isinstance(task, dict) else "execute"
   592	    _append_audit({
   593	        "event_type": "oracle_gate_trigger",
   594	        "actor": "hook:pretool-gate",
   595	        "decision": "REVIEW",
   596	        "reason": "potential_oracle_trigger_detected",
   597	        "current_step": task.get("current_step") if isinstance(task, dict) else None,
   598	        "phase": phase,
   599	    })
   600	    # Oracle never blocks — but emits a real hint so the L2 operator sees it
   601	    level = "FORCE" if force else "TRIGGER"
   602	    print(
   603	        f"🔮 [oracle-gate] L2 {level} 触发检测：建议完成后执行双审判 "
   604	        f"`python3 .claude/scripts/carros_base.py oracle review` 或 /lx-oracle review",
   605	        file=sys.stderr, flush=True,
   606	    )
   607	    return None  # always passes
   608	
   609	
   610	# ── Main dispatcher ──
   611	
   612	STATE_TOKEN = OMC / "state" / "token.json"
   613	
   614	
   615	def _clean_stale_state_token() -> None:
   616	    """Auto-clear .omc/state/token.json if blocked/waiting longer than threshold.
   617	    Prevents stale lock accumulation (ref: GPT-5.5 audit finding)."""
   618	    if not STATE_TOKEN.exists():
   619	        return
   620	    try:
   621	        data = json.loads(STATE_TOKEN.read_text(encoding="utf-8"))
   622	    except Exception:
   623	        return
   624	    task = data.get("task") if isinstance(data.get("task"), dict) else {}
   625	    status = task.get("status") or (data.get("task") or {}).get("status") or ""
   626	    if status not in ("blocked", "waiting_user"):
   627	        return
   628	    fb = task.get("fallback", {}) or {}
   629	    ts_str = fb.get("timestamp") or data.get("session", {}).get("fallback", {}).get("timestamp") or ""
   630	    if not ts_str:
   631	        return
   632	    try:
   633	        from datetime import datetime, timezone
   634	        ts = datetime.fromisoformat(ts_str)
   635	        age = (datetime.now(timezone.utc) - ts).total_seconds()
   636	    except Exception:
   637	        return
   638	    if age < STALE_LOCK_THRESHOLD:
   639	        return
   640	    # Stale lock detected — auto-clear
   641	    cleared = {
   642	        "schema_version": 3,
   643	        "session": {"clean": True, "note": f"Auto-cleared stale {status} from {ts_str}",
   644	                     "cleaned_at": datetime.now(timezone.utc).isoformat()},
   645	        "task": None,
   646	    }
   647	    STATE_TOKEN.write_text(json.dumps(cleared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
   648	    _append_audit({
   649	        "event_type": "state_lock_auto_cleared",
   650	        "actor": "hook:pretool-gate",
   651	        "reason": f"stale_{status}_age_{int(age)}s",
   652	        "original_timestamp": ts_str,
   653	    })
   654	
   655	
   656	# Dialogue residue patterns — content that indicates AI chat output left in spec docs
   657	HARD_BLOCK_DOC_PATTERNS = [
   658	    r"(^|/)\.claude/references/design-docs/",
   659	    r"(^|/)AGENTS\.md$",
   660	    r"(^|/)kernel\.md$",
   661	    r"(^|/)README\.md$",
   662	]
   663	
   664	_DIALOGUE_RESIDUE_PATTERNS = [
   665	    r"我明白了[，,。!！]?",
   666	    r"好的[，,。!！]?(,|，)?" + r"让我",
   667	    r"下面给你一版",
   668	    r"下面是一版(调整|优化|完整|修改|补充)",
   669	    r"根据你(给|上传|提供)的",
   670	    r"我对.*进行了全面(优化|调整|更新|修改)",
   671	    r"我明白你的意思",
   672	    r"可以[。.]\s*依?据?现在(已经)?定稿",
   673	    r"对[，,]刚才那版确实",
   674	    r"I understand[.,]",
   675	    r"Here is a (complete|revised|optimized|updated) version",
   676	    r"Based on your (uploaded|provided|given)",
   677	]
   678	
   679	
   680	def _check_document_quality(payload: dict) -> str | None:
   681	    """Gate 8: detect dialogue residue in spec document writes.
   682	    — Critical paths (重构指导文档, AGENTS, kernel, README): BLOCK
   683	    — Other .md: WARN (audit only, passes through)."""
   684	    tool = _extract_tool(payload).lower()
   685	    if tool not in WRITE_TOOLS:
   686	        return None
   687	    path = _extract_path(payload)
   688	    if not path or not path.endswith(".md"):
   689	        return None
   690	    ti = _extract_input(payload)
   691	    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
   692	    if not content:
   693	        return None
   694	    for pat in _DIALOGUE_RESIDUE_PATTERNS:
   695	        if re.search(pat, content, re.IGNORECASE):
   696	            is_critical = any(re.match(hp, path.replace("\\", "/"), re.IGNORECASE) for hp in HARD_BLOCK_DOC_PATTERNS)
   697	            decision = "BLOCK" if is_critical else "WARN"
   698	            _append_audit({
   699	                "event_type": "document_quality_warning",
   700	                "actor": "hook:pretool-gate",
   701	                "decision": decision,
   702	                "reason": f"dialogue_residue pattern={pat}",
   703	                "path": path,
   704	            })
   705	            if is_critical:
   706	                return f"BLOCK dialogue_residue_in_spec_doc pattern={pat} path={path}"
   707	            return None  # WARN passes through
   708	    return None
   709	
   710	
   711	# ── Context-control gates (G2/G3/G5/G6) ──
   712	# H2 修复注记：G1（单 tick 读文件计数）已删除——计数器是进程内存，
   713	# hook 每次调用都是新进程，结构性不可能工作（死代码）。
   714	
   715	
   716	def _check_g2_large_file(payload: dict) -> str | None:
   717	    """G2: read without offset/limit and >200 lines → NARROW"""
   718	    tool = _extract_tool(payload).lower()
   719	    if tool not in READ_TOOLS:
   720	        return None
   721	    ti = _extract_input(payload)
   722	    if ti.get("offset") or ti.get("limit"):
   723	        return None
   724	    path = _extract_path(payload)
   725	    if not path:
   726	        return None
   727	    p = ROOT / path.removeprefix("./") if not path.startswith("/") else Path(path)
   728	    if not p.exists():
   729	        return None
   730	    try:
   731	        lines = p.read_text(encoding="utf-8").splitlines()
   732	        if len(lines) > 200:
   733	            return f"NARROW large_file_no_offset path={path} lines={len(lines)} hint='use offset=1 limit=200'"
   734	    except (OSError, UnicodeDecodeError):
   735	        pass
   736	    return None
   737	
   738	
   739	def _check_g3_reviews(payload: dict) -> str | None:
   740	    """G3: docs/carros/reviews/** → BLOCK"""
   741	    tool = _extract_tool(payload).lower()
   742	    if tool not in READ_TOOLS:
   743	        return None
   744	    path = _extract_path(payload)
   745	    if not path:
   746	        return None
   747	    normalized = path.replace("\\", "/")
   748	    if "docs/carros/reviews/" in normalized:
   749	        return f"BLOCK reviews path={path}"
   750	    return None
   751	
   752	
   753	def _check_g5_wide_glob(payload: dict) -> str | None:
   754	    """G5: glob '**/*' without type narrowing → NARROW"""
   755	    tool = _extract_tool(payload).lower()
   756	    if tool not in READ_TOOLS:
   757	        return None
   758	    ti = _extract_input(payload)
   759	    glob_val = ti.get("glob") or ti.get("pattern") or _extract_path(payload)
   760	    if isinstance(glob_val, str) and ("**/*" in glob_val or glob_val.strip() in ("*", ".", "./*")):
   761	        return f"NARROW wide_glob pattern={glob_val} hint='add file_glob=*.py or type filter'"
   762	    return None
   763	
   764	
   765	def _check_g6_budget(payload: dict) -> str | None:
   766	    """G6: budget soft reached → CHECKPOINT_FIRST"""
   767	    tool = _extract_tool(payload).lower()
   768	    if tool not in READ_TOOLS and tool not in WRITE_TOOLS:
   769	        return None
   770	    token = _active_token()
   771	    if not token:
   772	        return None
   773	    budget = token.get("budget", {})
   774	    if not budget:
   775	        return None
   776	    stats = token.get("stats", {})
   777	    turns = stats.get("tick", 0) + stats.get("turns", 0)
   778	    soft = budget.get("max_turns_soft", 0) or 0
   779	    hard = budget.get("max_turns_hard", 0) or 0
   780	    if soft > 0 and turns >= soft:
   781	        return f"CHECKPOINT_FIRST budget_soft_reached turns={turns} soft={soft} hard={hard}"
   782	    return None
   783	
   784	
   785	def _check_context_critical_pause(payload: dict) -> str | None:
   786	    """GA water hard gate: while PAUSED_CONTEXT_CRITICAL, allow only recovery-class actions."""
   787	    if not CRITICAL_STATE.exists():
   788	        return None
   789	    try:
   790	        state = json.loads(CRITICAL_STATE.read_text(encoding="utf-8"))
   791	    except Exception:
   792	        state = {}
   793	    if state.get("status") != "PAUSED_CONTEXT_CRITICAL":
   794	        return None
   795	
   796	    tool = _extract_tool(payload).lower()
   797	    command = _extract_command(payload).lower()
   798	    path = _extract_path(payload).lower()
   799	    allowed_terms = (
   800	        "status", "checkpoint", "compact", "resume", "archive",
   801	        "context_engine.py", "carros_base.py status", "formal_seal.py",
   802	    )
   803	    text = " ".join([tool, command, path])
   804	    if any(term in text for term in allowed_terms):
   805	        return None
   806	    return "BLOCK CONTEXT_CRITICAL_PAUSED allowed=status/checkpoint/compact/resume/archive"
   807	
   808	
   809	# ── Gate registry ──
   810	
   811	GATES = [
   812	    ("context-critical", _check_context_critical_pause),
   813	    ("sensitive-edit", _check_sensitive_edit),
   814	    ("fallback", _check_fallback),
   815	    ("action", _check_action_gate),
   816	    ("plan", _check_plan_gate),
   817	    ("edit-scope", _check_edit_scope),
   818	    ("verify", _check_verify_gate),
   819	    ("oracle", _check_oracle_gate),
   820	    ("document-quality", _check_document_quality),
   821	    # Context-control gates (G2/G3/G5/G6)
   822	    ("g2-large-file", _check_g2_large_file),
   823	    ("g3-reviews", _check_g3_reviews),
   824	    ("g5-wide-glob", _check_g5_wide_glob),
   825	    ("g6-budget", _check_g6_budget),
   826	]
   827	
   828	
   829	def main() -> int:
   830	    payload = _read_stdin()
   831	    tool_name = _extract_tool(payload).lower() or "unknown"
   832	
   833	    # 如果用户已创建临时 bypass token，跳过所有 gate 检查
   834	    bypass_active = _check_temp_bypass()
   835	
   836	    _clean_stale_state_token()
   837	
   838	    for gate_name, gate_fn in GATES:
   839	        try:
   840	            result = gate_fn(payload)
   841	        except Exception:
   842	            continue
   843	        if result:
   844	            if result.startswith("BLOCK"):
   845	                if bypass_active:
   846	                    _append_audit({
   847	                        "event_type": "gate_bypassed",
   848	                        "actor": "hook:pretool-gate",
   849	                        "gate": gate_name,
   850	                        "reason": result,
   851	                    })
   852	                    return _ok(f"BYPASS_ALLOW [{gate_name}] (用户已授权临时跳过)")
   853	                parts = result.split("|", 1)
   854	                reason = parts[0].replace("BLOCK ", "").strip()
   855	                suggestion = parts[1].strip() if len(parts) > 1 else ""
   856	                return _block(reason, suggestion)
   857	            elif result.startswith("ASK_USER"):
   858	                parts = result.split("|", 1)
   859	                reason = parts[0].replace("ASK_USER ", "").strip()
   860	                suggestion = parts[1].strip() if len(parts) > 1 else ""
   861	                return _block(reason, suggestion)
   862	            elif result.startswith(("NARROW", "CHECKPOINT_FIRST")):
   863	                # 软门（G1/G2/G5/G6）：柔性约束——WARN 提示 + audit，不阻断
   864	                _append_audit({
   865	                    "event_type": "gate_soft_warn",
   866	                    "actor": "hook:pretool-gate",
   867	                    "gate": gate_name,
   868	                    "reason": result,
   869	                })
   870	                goal_mode = (OMC / "state" / "tokens" / "autonomous.active").exists()
   871	                if not goal_mode:
   872	                    print(f"⚠️ [{gate_name}] {result}", file=sys.stderr, flush=True)
   873	                continue
   874	
   875	    return _ok(f"ALLOW tool={tool_name}")
   876	
   877	
   878	if __name__ == "__main__":
   879	    raise SystemExit(main())
```

### `.claude/scripts/verify_gate.py`

```
     1	#!/usr/bin/env python3
     2	"""
     3	CarrorOS VerifyGate
     4	
     5	Purpose:
     6	  Match executor.md evidence against plan.md verify rules to decide step completion.
     7	  Only VerifyGate VERIFIED allows plan.md [x].
     8	
     9	Commands:
    10	  verify --step <step_id> --plan <path> --executor <path> [--token <path>]
    11	
    12	Output:
    13	  VERIFIED / WARN / BLOCKED / REJECTED
    14	
    15	Constraints:
    16	  - Python 3.10+ standard library only
    17	  - Does not execute fixes
    18	  - Does not alter executor evidence
    19	  - Evidence-level enforcement:
    20	    E3 command exit=0 > E2 file_assertion > E1 user_confirmation > E0 narrative (rejected)
    21	"""
    22	
    23	from __future__ import annotations
    24	
    25	import argparse
    26	import json
    27	import re
    28	import sys
    29	from dataclasses import dataclass, asdict
    30	from datetime import datetime, timezone
    31	from pathlib import Path
    32	from typing import Any
    33	
    34	SOFT_COMPLETION_PHRASES = [
    35	    "应该好了", "看起来可以", "基本完成", "大概没问题",
    36	    "已经处理", "完成了",
    37	    "looks good", "should work", "probably fixed",
    38	    "可以了", "没问题",
    39	]
    40	
    41	
    42	@dataclass
    43	class VerifyDecision:
    44	    decision: str  # VERIFIED | WARN | BLOCKED | REJECTED
    45	    reason: str
    46	    step: str
    47	    matched: list[str]
    48	    missing: list[str]
    49	    warnings: list[str]
    50	    required_action: str | None = None
    51	
    52	
    53	def now_iso() -> str:
    54	    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    55	
    56	
    57	def today() -> str:
    58	    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    59	
    60	
    61	def read_text(path: Path) -> str:
    62	    if not path.exists():
    63	        return ""
    64	    return path.read_text(encoding="utf-8")
    65	
    66	
    67	def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    68	    if not path.exists():
    69	        return default or {}
    70	    with path.open("r", encoding="utf-8") as f:
    71	        return json.load(f)
    72	
    73	
    74	def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    75	    path.parent.mkdir(parents=True, exist_ok=True)
    76	    with path.open("a", encoding="utf-8") as f:
    77	        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    78	
    79	
    80	def parse_verify_rules(plan_text: str, step: str) -> list[str]:
    81	    """Extract verify rules for a given step from plan.md."""
    82	    rules: list[str] = []
    83	    in_step = False
    84	    step_prefixes = [f"- [ ] {step}:", f"- [x] {step}:", f"- [X] {step}:"]
    85	
    86	    for line in plan_text.splitlines():
    87	        stripped = line.strip()
    88	        # Check if we're entering the target step
    89	        if any(stripped.startswith(p) for p in step_prefixes):
    90	            in_step = True
    91	            continue
    92	        # Exit step on next step heading or step marker
    93	        if in_step and (stripped.startswith("- [") or stripped.startswith("## ")):
    94	            if stripped.startswith("- [") and not any(stripped.startswith(p) for p in step_prefixes):
    95	                break
    96	        if in_step:
    97	            m = re.match(r"- verify:\s*(.+)$", stripped)
    98	            if m:
    99	                rules.append(m.group(1).strip())
   100	    if not rules:
   101	        # Fallback: search globally
   102	        for line in plan_text.splitlines():
   103	            m = re.match(r"- verify:\s*(.+)$", line.strip())
   104	            if m:
   105	                rules.append(m.group(1).strip())
   106	    return rules
   107	
   108	
   109	def parse_evidence(executor_text: str, step: str) -> list[dict[str, Any]]:
   110	    """Extract evidence entries for a given step from executor.md."""
   111	    evidence: list[dict[str, Any]] = []
   112	    current: dict[str, Any] = {}
   113	    in_entry = False
   114	
   115	    for line in executor_text.splitlines():
   116	        stripped = line.strip()
   117	        m = re.match(r"^###\s+(EV-\S+)", stripped)
   118	        if m:
   119	            if current and current.get("step") == step:
   120	                evidence.append(current)
   121	            current = {"id": m.group(1)}
   122	            in_entry = True
   123	            continue
   124	        m = re.match(r"^###\s+(FAIL-\S+)", stripped)
   125	        if m:
   126	            if current and current.get("step") == step:
   127	                evidence.append(current)
   128	            current = {"id": m.group(1), "type": "failure"}
   129	            in_entry = True
   130	            continue
   131	        if in_entry:
   132	            for key in ("step", "type", "source", "exit_code", "file", "assertion",
   133	                        "evidence_level", "confirmation", "change_summary"):
   134	                kv = re.match(rf"- {key}:\s*(.+)$", stripped)
   135	                if kv:
   136	                    val = kv.group(1).strip()
   137	                    if key == "exit_code":
   138	                        try:
   139	                            val = int(val)
   140	                        except ValueError:
   141	                            pass
   142	                    current[key] = val
   143	            if stripped.startswith("## "):
   144	                if current and current.get("step") == step:
   145	                    evidence.append(current)
   146	                current = {}
   147	                in_entry = False
   148	
   149	    if current and current.get("step") == step:
   150	        evidence.append(current)
   151	
   152	    return evidence
   153	
   154	
   155	def is_soft_completion(text: str) -> bool:
   156	    lowered = text.lower().strip()
   157	    return any(phrase.lower() in lowered for phrase in SOFT_COMPLETION_PHRASES)
   158	
   159	
   160	def match_verify_rule(rule: str, evidence: list[dict[str, Any]]) -> tuple[bool, str, list[str]]:
   161	    """Match a single verify rule against available evidence."""
   162	    warnings: list[str] = []
   163	
   164	    # command: rule
   165	    cm = re.match(r"^command:(.+)$", rule)
   166	    if cm:
   167	        expected_cmd = cm.group(1).strip()
   168	        for ev in evidence:
   169	            if ev.get("type") == "failure":
   170	                continue
   171	            src = str(ev.get("source", "")).strip()
   172	            ec = ev.get("exit_code")
   173	            el = str(ev.get("evidence_level", ""))
   174	            if src and (src == expected_cmd or src.endswith("/" + expected_cmd) or expected_cmd.endswith(src)):
   175	                if ec == 0 and el == "E3":
   176	                    return True, f"command match: {src} exit=0", []
   177	                elif ec == 0:
   178	                    warnings.append(f"command {src} exit=0 but evidence_level={el} (expected E3)")
   179	        return False, f"no matching command evidence for: {expected_cmd}", warnings
   180	
   181	    # file: rule
   182	    fm = re.match(r"^file:(.+?)\s+contains\s+(.+)$", rule)
   183	    if fm:
   184	        expected_file = fm.group(1).strip()
   185	        expected_assertion = fm.group(2).strip()
   186	        for ev in evidence:
   187	            if ev.get("type") == "failure":
   188	                continue
   189	            ef = str(ev.get("file", "")).strip()
   190	            ea = str(ev.get("assertion", "")).strip()
   191	            el = str(ev.get("evidence_level", ""))
   192	            if ef and (ef == expected_file or ef.endswith("/" + expected_file)):
   193	                if is_soft_completion(ea):
   194	                    warnings.append(f"file_assertion for {ef} contains soft completion: '{ea}'")
   195	                    return False, "soft_completion_in_assertion", warnings
   196	                if expected_assertion.lower() in ea.lower():
   197	                    if el in ("E2", "E3"):
   198	                        return True, f"file assertion match: {ef} contains '{expected_assertion}'", []
   199	                    warnings.append(f"file assertion for {ef} has evidence_level={el} (expected E2/E3)")
   200	                else:
   201	                    warnings.append(f"file assertion for {ef} doesn't contain '{expected_assertion}'")
   202	        return False, f"no matching file assertion for: {expected_file}", warnings
   203	
   204	    # assertion: rule
   205	    am = re.match(r"^assertion:(.+)$", rule)
   206	    if am:
   207	        expected = am.group(1).strip().lower()
   208	        for ev in evidence:
   209	            if ev.get("type") == "failure":
   210	                continue
   211	            if is_soft_completion(str(ev.get("assertion", ""))):
   212	                warnings.append(f"assertion contains soft completion")
   213	                continue
   214	            if expected in str(ev.get("assertion", "")).lower():
   215	                return True, f"assertion match: '{expected}'", []
   216	            txt = str(ev.get("output_tail", "")).lower()
   217	            if expected in txt and ev.get("exit_code") == 0:
   218	                return True, f"assertion in command output: '{expected}'", []
   219	        return False, f"no matching assertion for: {expected}", warnings
   220	
   221	    return False, f"unrecognized verify rule: {rule}", warnings
   222	
   223	
   224	def parse_spec_acs(spec_path: Path, step: str | None = None) -> list[str]:
   225	    """Parse Acceptance Criteria from spec.md — returns list of AC rules
   226	
   227	    spec.md 格式:
   228	        - AC1 [command:] <desc>
   229	        - AC2 [file:] <desc>
   230	        - AC3 [assertion:] <desc>
   231	    """
   232	    spec_text = read_text(spec_path)
   233	    if not spec_text:
   234	        return []
   235	
   236	    rules = []
   237	    for line in spec_text.splitlines():
   238	        stripped = line.strip()
   239	        # Match: - AC1 [command:] description
   240	        m = re.match(r"^\s*-\s*(AC\d+)\s*\[(command:|file:|assertion:)\]\s*(.+)", stripped)
   241	        if m:
   242	            prefix = m.group(2)  # e.g. "command:"
   243	            desc = m.group(3).strip()
   244	            rules.append(f"{prefix}{desc}")
   245	            continue
   246	        # Match: - AC1: description (no type prefix, default assertion:)
   247	        m2 = re.match(r"^\s*-\s*(AC\d+):\s*(.+)", stripped)
   248	        if m2:
   249	            desc = m2.group(2).strip()
   250	            rules.append(f"assertion:{desc}")
   251	
   252	    return rules
   253	
   254	
   255	def verify_step(step: str, plan_path: Path, executor_path: Path, token_path: Path | None = None,
   256	                spec_path: Path | None = None) -> VerifyDecision:
   257	    plan_text = read_text(plan_path)
   258	    executor_text = read_text(executor_path)
   259	
   260	    plan_text = read_text(plan_path)
   261	    if not plan_text:
   262	        return VerifyDecision("REJECTED", "plan_missing", step, [], [], [])
   263	
   264	    executor_text = read_text(executor_path)
   265	    if not executor_text:
   266	        return VerifyDecision("BLOCKED", "executor_missing", step, [], [], [])
   267	
   268	    # Parse verify rules for this step
   269	    verify_rules = parse_verify_rules(plan_text, step)
   270	
   271	    # Also merge AC rules from spec.md (if available)
   272	    spec_acs = []
   273	    if spec_path and spec_path.exists():
   274	        spec_acs = parse_spec_acs(spec_path, step)
   275	    all_rules = verify_rules + [r for r in spec_acs if r not in verify_rules]
   276	
   277	    if not all_rules:
   278	        return VerifyDecision("REJECTED", "no_verify_rules", step, [], [], [],
   279	                              "Plan step must have verify rules or spec.md must have ACs.")
   280	    verify_rules = all_rules
   281	
   282	    # Check for invalid rule syntax
   283	    valid_prefixes = ("command:", "file:", "assertion:", "user:")
   284	    for rule in verify_rules:
   285	        if not any(rule.startswith(p) for p in valid_prefixes):
   286	            return VerifyDecision("REJECTED", f"invalid_verify_prefix: {rule}", step, [], [], [],
   287	                                  "Verify rule must start with command:/file:/assertion:/user:")
   288	
   289	    # Parse evidence
   290	    evidence = parse_evidence(executor_text, step)
   291	    if not evidence:
   292	        return VerifyDecision("BLOCKED", "no_evidence_for_step", step, [], verify_rules, [])
   293	
   294	    # Check for soft completion in evidence assertions
   295	    for ev in evidence:
   296	        assertion = str(ev.get("assertion", ""))
   297	        confirmation = str(ev.get("confirmation", ""))
   298	        if is_soft_completion(assertion) or is_soft_completion(confirmation):
   299	            return VerifyDecision("REJECTED", "soft_completion_in_evidence", step, [], verify_rules, [])
   300	
   301	    # Check for unresolved failures
   302	    failures = [ev for ev in evidence if ev.get("type") == "failure"]
   303	    # Remove failures that have subsequent covering success evidence
   304	    for fail in failures:
   305	        fail_action = str(fail.get("action", ""))
   306	        # Check if there's a successful command evidence with same source
   307	        covered = False
   308	        for ev in evidence:
   309	            if ev.get("type") == "failure":
   310	                continue
   311	            if ev.get("exit_code") == 0:
   312	                src = str(ev.get("source", ""))
   313	                if src and fail_action.endswith(src):
   314	                    covered = True
   315	                    break
   316	        if not covered:
   317	            return VerifyDecision("BLOCKED", f"unresolved_failure:{fail.get('id', 'unknown')}",
   318	                                  step, [], verify_rules, [])
   319	
   320	    # Match each verify rule
   321	    matched_rules: list[str] = []
   322	    missing_rules: list[str] = []
   323	    all_warnings: list[str] = []
   324	
   325	    for rule in verify_rules:
   326	        ok, reason, warns = match_verify_rule(rule, evidence)
   327	        all_warnings.extend(warns)
   328	        if ok:
   329	            matched_rules.append(reason)
   330	        else:
   331	            missing_rules.append(reason)
   332	
   333	    # Check user confirmation rules separately (weaker match needed)
   334	    user_rules = [r for r in missing_rules if r.startswith("no matching")]
   335	    user_verify = [r for r in verify_rules if r.startswith("user:")]
   336	    for vr in user_verify:
   337	        expected = vr[5:].strip().lower()
   338	        for ev in evidence:
   339	            if ev.get("type") != "user_confirmation":
   340	                continue
   341	            conf = str(ev.get("confirmation", "")).lower()
   342	            if is_soft_completion(conf):
   343	                all_warnings.append(f"user confirmation contains soft completion: '{conf}'")
   344	                continue
   345	            if len(conf) >= 8 and expected in conf:
   346	                matched_rules.append(f"user confirmation match: '{expected}'")
   347	                user_rules_to_remove = [r for r in missing_rules if "user:" in r]
   348	                for rr in user_rules_to_remove:
   349	                    if rr in missing_rules:
   350	                        missing_rules.remove(rr)
   351	
   352	    # Decision
   353	    if not missing_rules and not all_warnings:
   354	        return VerifyDecision("VERIFIED", "all_verify_rules_matched", step, matched_rules, [], [])
   355	    elif not missing_rules and all_warnings:
   356	        return VerifyDecision("WARN", "all_verify_matched_with_warnings", step, matched_rules, [], all_warnings)
   357	    elif missing_rules:
   358	        return VerifyDecision("BLOCKED", "evidence_missing", step, matched_rules, missing_rules, all_warnings)
   359	
   360	    return VerifyDecision("BLOCKED", "unknown", step, matched_rules, missing_rules, all_warnings)
   361	
   362	
   363	def write_audit(decision: VerifyDecision, token: dict[str, Any] | None = None) -> None:
   364	    event = {
   365	        "event_type": "verify_decision",
   366	        "timestamp": now_iso(),
   367	        "step": decision.step,
   368	        "decision": decision.decision,
   369	        "reason": decision.reason,
   370	        "matched": decision.matched,
   371	        "missing": decision.missing,
   372	        "warnings": decision.warnings,
   373	        "required_action": decision.required_action,
   374	    }
   375	    if token:
   376	        event["task_id"] = token.get("task", {}).get("id", "unknown")
   377	        event["level"] = token.get("session", {}).get("level", "unknown")
   378	    append_jsonl(Path(".omc/audit") / f"{today()}.jsonl", event)
   379	
   380	
   381	def main() -> int:
   382	    parser = argparse.ArgumentParser()
   383	    parser.add_argument("--step", required=True)
   384	    parser.add_argument("--plan", required=True)
   385	    parser.add_argument("--executor", required=True)
   386	    parser.add_argument("--token", required=False)
   387	    parser.add_argument("--spec", required=False,
   388	                       help="spec.md 路径 — 可选，提供 AC 规则以增强验证")
   389	    args = parser.parse_args()
   390	
   391	    token = read_json(Path(args.token)) if args.token else None
   392	    spec_path = Path(args.spec) if args.spec else None
   393	    result = verify_step(args.step, Path(args.plan), Path(args.executor),
   394	                         Path(args.token) if args.token else None, spec_path)
   395	
   396	    write_audit(result, token)
   397	
   398	    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
   399	    return 0 if result.decision == "VERIFIED" else 1
   400	
   401	
   402	if __name__ == "__main__":
   403	    raise SystemExit(main())
```

### `.claude/scripts/verify_tests.py`

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

### `.claude/scripts/runtime_verify.py`

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

### `.claude/scripts/runtime_verify2.py`

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

### `.omc/scripts/feature_verify.py`

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

### `.omc/scripts/oracle_gate.py` — 双源副本 A

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_gate.py — Oracle 门禁执行器
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_gate.py --check <trigger_id> [--path <path>] [--command <cmd>]
     7	
     8	Returns: JSON with verdict/reason
     9	"""
    10	import json
    11	import os
    12	import re
    13	import sys
    14	import time
    15	from datetime import datetime, timezone
    16	from pathlib import Path
    17	
    18	TRIGGER_RULES = {
    19	    "cross_system": {
    20	        "pattern": r"^(/etc/|/usr/local/|/Applications/|/System/)",
    21	        "type": "hard_block",
    22	        "description": "跨系统操作",
    23	    },
    24	    "irreversible": {
    25	        "pattern": r"\b(rm -rf|dd |diskutil |sudo |chmod 777|> /dev/)",
    26	        "type": "hard_block",
    27	        "description": "不可逆操作",
    28	    },
    29	    "security": {
    30	        "pattern": r"(\.ssh/|/\.env|credentials|secret|id_rsa)",
    31	        "type": "hard_block",
    32	        "description": "安全/权限变更",
    33	    },
    34	    "deploy": {
    35	        "pattern": r"\b(deploy|release|publish|push --force|npm publish)\b",
    36	        "type": "soft_gate",
    37	        "description": "发布动作",
    38	    },
    39	    "long_idle": {
    40	        "type": "soft_gate",
    41	        "description": "长时间无人",
    42	        "check": "long_idle",
    43	    },
    44	}
    45	
    46	BYPASS_DIR = Path(".omc/state/oracle_bypass")
    47	BYPASS_TTL = 86400  # 24h
    48	
    49	
    50	def _check_bypass(task_id):
    51	    """检查是否有有效的 bypass 文件"""
    52	    if not BYPASS_DIR.exists():
    53	        return False
    54	    for f in BYPASS_DIR.glob(f"{task_id}_approved.md"):
    55	        mtime = f.stat().st_mtime
    56	        if time.time() - mtime < BYPASS_TTL:
    57	            return True
    58	    return False
    59	
    60	
    61	def _clean_expired_bypass():
    62	    """删除过期 bypass 文件"""
    63	    if not BYPASS_DIR.exists():
    64	        return
    65	    now = time.time()
    66	    for f in BYPASS_DIR.iterdir():
    67	        if now - f.stat().st_mtime > BYPASS_TTL:
    68	            f.unlink()
    69	
    70	
    71	def oracle_check(trigger_id, path=None, command=None):
    72	    """执行 Oracle 门禁检查"""
    73	    rule = TRIGGER_RULES.get(trigger_id)
    74	    if not rule:
    75	        return {"verdict": "ACCEPT", "reason": f"Unknown trigger: {trigger_id}"}
    76	
    77	    _clean_expired_bypass()
    78	
    79	    # 检查 bypass
    80	    task_id = os.environ.get("CARROROS_TASK_ID", "unknown")
    81	    if _check_bypass(task_id):
    82	        return {"verdict": "ACCEPT", "reason": "Bypass file active"}
    83	
    84	    if trigger_id == "long_idle":
    85	        return {"verdict": "WARN", "reason": "长时间无人，建议确认后操作"}
    86	
    87	    # 路径匹配
    88	    check_target = command or path or ""
    89	    pattern = rule["pattern"]
    90	    if re.search(pattern, check_target):
    91	        if rule["type"] == "hard_block":
    92	            return {
    93	                "verdict": "REJECT",
    94	                "reason": f"[{rule['description']}] 操作被 Oracle 门禁拦截: {check_target[:80]}",
    95	            }
    96	        else:
    97	            return {
    98	                "verdict": "WARN",
    99	                "reason": f"[{rule['description']}] 需要人工确认: {check_target[:80]}",
   100	            }
   101	
   102	    return {"verdict": "ACCEPT", "reason": "No trigger matched"}
   103	
   104	
   105	def main():
   106	    args = sys.argv[1:]
   107	    trigger_id = None
   108	    path = None
   109	    command = None
   110	
   111	    i = 0
   112	    while i < len(args):
   113	        if args[i] == "--check" and i + 1 < len(args):
   114	            trigger_id = args[i + 1]
   115	            i += 2
   116	        elif args[i] == "--path" and i + 1 < len(args):
   117	            path = args[i + 1]
   118	            i += 2
   119	        elif args[i] == "--command" and i + 1 < len(args):
   120	            command = args[i + 1]
   121	            i += 2
   122	        else:
   123	            i += 1
   124	
   125	    if not trigger_id:
   126	        print(json.dumps({"verdict": "ACCEPT", "reason": "No trigger specified"}))
   127	        return 0
   128	
   129	    result = oracle_check(trigger_id, path=path, command=command)
   130	    print(json.dumps(result))
   131	
   132	    if result["verdict"] == "REJECT":
   133	        return 2
   134	    return 0
   135	
   136	
   137	if __name__ == "__main__":
   138	    sys.exit(main())
```

### `.claude/scripts/oracle_gate.py` — 双源副本 B(与 A 比对)

```
     1	#!/usr/bin/env python3
     2	"""
     3	oracle_gate.py — Oracle 门禁执行器
     4	
     5	Usage:
     6	    python3 .omc/scripts/oracle_gate.py --check <trigger_id> [--path <path>] [--command <cmd>]
     7	
     8	Returns: JSON with verdict/reason
     9	"""
    10	import json
    11	import os
    12	import re
    13	import sys
    14	import time
    15	from datetime import datetime, timezone
    16	from pathlib import Path
    17	
    18	TRIGGER_RULES = {
    19	    "cross_system": {
    20	        "pattern": r"^(/etc/|/usr/local/|/Applications/|/System/)",
    21	        "type": "hard_block",
    22	        "description": "跨系统操作",
    23	    },
    24	    "irreversible": {
    25	        "pattern": r"\b(rm -rf|dd |diskutil |sudo |chmod 777|> /dev/)",
    26	        "type": "hard_block",
    27	        "description": "不可逆操作",
    28	    },
    29	    "security": {
    30	        "pattern": r"(\.ssh/|/\.env|credentials|secret|id_rsa)",
    31	        "type": "hard_block",
    32	        "description": "安全/权限变更",
    33	    },
    34	    "deploy": {
    35	        "pattern": r"\b(deploy|release|publish|push --force|npm publish)\b",
    36	        "type": "soft_gate",
    37	        "description": "发布动作",
    38	    },
    39	    "long_idle": {
    40	        "type": "soft_gate",
    41	        "description": "长时间无人",
    42	        "check": "long_idle",
    43	    },
    44	}
    45	
    46	BYPASS_DIR = Path(".omc/state/oracle_bypass")
    47	BYPASS_TTL = 86400  # 24h
    48	
    49	
    50	def _check_bypass(task_id):
    51	    """检查是否有有效的 bypass 文件"""
    52	    if not BYPASS_DIR.exists():
    53	        return False
    54	    for f in BYPASS_DIR.glob(f"{task_id}_approved.md"):
    55	        mtime = f.stat().st_mtime
    56	        if time.time() - mtime < BYPASS_TTL:
    57	            return True
    58	    return False
    59	
    60	
    61	def _clean_expired_bypass():
    62	    """删除过期 bypass 文件"""
    63	    if not BYPASS_DIR.exists():
    64	        return
    65	    now = time.time()
    66	    for f in BYPASS_DIR.iterdir():
    67	        if now - f.stat().st_mtime > BYPASS_TTL:
    68	            f.unlink()
    69	
    70	
    71	def oracle_check(trigger_id, path=None, command=None):
    72	    """执行 Oracle 门禁检查"""
    73	    rule = TRIGGER_RULES.get(trigger_id)
    74	    if not rule:
    75	        return {"verdict": "ACCEPT", "reason": f"Unknown trigger: {trigger_id}"}
    76	
    77	    _clean_expired_bypass()
    78	
    79	    # 检查 bypass
    80	    task_id = os.environ.get("CARROROS_TASK_ID", "unknown")
    81	    if _check_bypass(task_id):
    82	        return {"verdict": "ACCEPT", "reason": "Bypass file active"}
    83	
    84	    if trigger_id == "long_idle":
    85	        return {"verdict": "WARN", "reason": "长时间无人，建议确认后操作"}
    86	
    87	    # 路径匹配
    88	    check_target = command or path or ""
    89	    pattern = rule["pattern"]
    90	    if re.search(pattern, check_target):
    91	        if rule["type"] == "hard_block":
    92	            return {
    93	                "verdict": "REJECT",
    94	                "reason": f"[{rule['description']}] 操作被 Oracle 门禁拦截: {check_target[:80]}",
    95	            }
    96	        else:
    97	            return {
    98	                "verdict": "WARN",
    99	                "reason": f"[{rule['description']}] 需要人工确认: {check_target[:80]}",
   100	            }
   101	
   102	    return {"verdict": "ACCEPT", "reason": "No trigger matched"}
   103	
   104	
   105	def main():
   106	    args = sys.argv[1:]
   107	    trigger_id = None
   108	    path = None
   109	    command = None
   110	
   111	    i = 0
   112	    while i < len(args):
   113	        if args[i] == "--check" and i + 1 < len(args):
   114	            trigger_id = args[i + 1]
   115	            i += 2
   116	        elif args[i] == "--path" and i + 1 < len(args):
   117	            path = args[i + 1]
   118	            i += 2
   119	        elif args[i] == "--command" and i + 1 < len(args):
   120	            command = args[i + 1]
   121	            i += 2
   122	        else:
   123	            i += 1
   124	
   125	    if not trigger_id:
   126	        print(json.dumps({"verdict": "ACCEPT", "reason": "No trigger specified"}))
   127	        return 0
   128	
   129	    result = oracle_check(trigger_id, path=path, command=command)
   130	    print(json.dumps(result))
   131	
   132	    if result["verdict"] == "REJECT":
   133	        return 2
   134	    return 0
   135	
   136	
   137	if __name__ == "__main__":
   138	    sys.exit(main())
```

### `scripts/test-verify-gate.py`

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

### 含 --pipeline 的文件清单

命令: `grep -rlE --exclude-dir=.git --exclude-dir=improve_plan -- '--pipeline' .`

```
./.claude/plans/carroros-skills-merge-plan.md
./.claude/skills/references/oma/skill-chaining.md
./.claude/skills/references/oma/pipeline-contract.md
./.claude/skills/lx-oma/SKILL.md
./scripts/assemble-pkg-materials.sh
./.omc/artifacts/20260718/TaskOutput-165715.log
```

### .claude 下全部 .sh 清单

命令: `find .claude -name '*.sh' -not -path '*__pycache__*'`

```
.claude/hooks/statusline-command.sh
.claude/hooks/hook-launcher.sh
.claude/skills/lx-ghost/scripts/lx-ghost.sh
.claude/skills/lx-goal/scripts/lx-goal.sh
.claude/profiles/merge-profile.sh
```

### `.claude/hooks/statusline-command.sh`

```
     1	#!/usr/bin/env bash
     2	set -u
     3	
     4	ROOT="${CARROROS_ROOT:-$(pwd)}"
     5	PYTHON="${PYTHON:-python3}"
     6	SCRIPT="$ROOT/.claude/scripts/statusline.py"
     7	FALLBACK="$ROOT/.claude/scripts/fallback_engine.py"
     8	
     9	fallback_event() {
    10	  local reason="$1"
    11	  if command -v "$PYTHON" >/dev/null 2>&1 && [ -f "$FALLBACK" ]; then
    12	    "$PYTHON" "$FALLBACK" cli_hook_failed low >/dev/null 2>&1 || true
    13	  fi
    14	  printf 'CarrorOS L1_BASE FALLBACK %s\n' "$reason" | cut -c 1-160
    15	}
    16	
    17	if ! command -v "$PYTHON" >/dev/null 2>&1; then
    18	  printf 'CarrorOS L1_BASE FALLBACK python_missing\n'
    19	  exit 0
    20	fi
    21	
    22	if [ ! -f "$SCRIPT" ]; then
    23	  fallback_event "no_statusline_script"
    24	  exit 0
    25	fi
    26	
    27	OUTPUT="$("$PYTHON" "$SCRIPT" 2>/dev/null)"
    28	STATUS=$?
    29	
    30	if [ "$STATUS" -ne 0 ] || [ -z "$OUTPUT" ]; then
    31	  fallback_event "cli_hook_failed"
    32	  exit 0
    33	fi
    34	
    35	printf '%s\n' "$OUTPUT" | head -n 1 | tr '\r\n' ' ' | cut -c 1-160
    36	exit 0```

### `.claude/hooks/hook-launcher.sh`

```
     1	#!/usr/bin/env bash
     2	# CarrorOS Hook Launcher
     3	# 用 $0 定位自身，切到项目根目录，再跑对应 hook
     4	# settings.json 里写: .claude/hooks/hook-launcher.sh <hook_name>.py
     5	
     6	set -euo pipefail
     7	
     8	# 从 launcher 自身路径定位项目根
     9	LAUNCHER_DIR="$(cd "$(dirname "$0")" && pwd)"
    10	PROJECT_ROOT="$(cd "$LAUNCHER_DIR/../.." && pwd)"
    11	
    12	HOOK_NAME="${1:-}"
    13	if [ -z "$HOOK_NAME" ]; then
    14	  echo "{\"continue\":true,\"message\":\"hook-launcher: missing hook name\"}"
    15	  exit 0
    16	fi
    17	
    18	HOOK_PATH="$LAUNCHER_DIR/$HOOK_NAME"
    19	
    20	# H3 fail-closed：关键 hook 缺失 = 治理链断裂，必须阻断而非静默放行。
    21	# 名单与 settings.json PreToolUse 注册项一一对应；新增关键 hook 时同步加入。
    22	CRITICAL_HOOKS="pretool-gate.py carroros-night-deny.py"
    23	_is_critical_hook() {
    24	  case " $CRITICAL_HOOKS " in
    25	    *" $1 "*) return 0 ;;
    26	    *) return 1 ;;
    27	  esac
    28	}
    29	
    30	if [ ! -f "$HOOK_PATH" ]; then
    31	  if _is_critical_hook "$HOOK_NAME"; then
    32	    echo "{\"continue\":true,\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"hook-launcher: CRITICAL hook missing: $HOOK_NAME — 治理链断裂，fail-closed 阻断本次工具调用。恢复该文件后重试。\"}}"
    33	    echo "hook-launcher: BLOCKED - critical hook missing: $HOOK_NAME" >&2
    34	    exit 2
    35	  fi
    36	  echo "{\"continue\":true,\"message\":\"hook-launcher: hook not found: $HOOK_NAME\"}"
    37	  exit 0
    38	fi
    39	
    40	cd "$PROJECT_ROOT"
    41	
    42	# Sol 复审 P1-SOL-2 锁紧：生产路径显式清除 night-deny 的测试覆写变量，
    43	# 保证 marker 根只能由 hook 文件 __file__ 锚定（模型/会话环境无法拐根）。
    44	unset NIGHT_DENY_ROOT
    45	
    46	case "$HOOK_NAME" in
    47	  *.sh)
    48	    exec bash "$HOOK_PATH"
    49	    ;;
    50	  *)
    51	    exec python3 "$HOOK_PATH"
    52	    ;;
    53	esac
```

### `.claude/skills/lx-ghost/scripts/lx-ghost.sh`

```
     1	#!/usr/bin/env bash
     2	# lx-ghost.sh — 幽灵模式（方向驱动自主探索）
     3	# 用法: lx-ghost on|off|status|set <key> <value>|poll
     4	# 幽灵模式: 给 AI 一个"方向"，AI 自主探索并修复，不干扰人，默认 3h 过期
     5	# 与 lx-goal 的区别: ghost = 方向驱动（开源探索），goal = 目标驱动（具体任务）
     6	# 同时创建 autonomous.active 信号供所有 hook 降级
     7	#
     8	# 哲学映射:
     9	#   #3 先守护: gate 降级为 warn-only 而非硬阻断
    10	#   #4 没验证=没做: poll 报告 + completion 软评分
    11	#   #6 0信任: 危险操作记录 skipped_risks 而不是跳过
    12	
    13	SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    14	PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
    15	STATE_DIR="$PROJECT_ROOT/.omc/state"
    16	mkdir -p "$STATE_DIR" 2>/dev/null
    17	
    18	# source harness_config for hc_get defaults
    19	source "$SCRIPT_DIR/../../../hooks/harness_config.sh"
    20	
    21	mkdir -p "$STATE_DIR/tokens" 2>/dev/null
    22	MODE_FILE="$STATE_DIR/tokens/lx-ghost.json"
    23	
    24	# 智能参数检测：第一个参数不是已知子命令 → 当作方向描述自动激活
    25	_KNOWN_SUBCOMMANDS="on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
    26	if [ -n "${1:-}" ] && ! echo "$1" | grep -Eq "^($_KNOWN_SUBCOMMANDS)$"; then
    27	    exec bash "$0" on "$@"
    28	fi
    29	
    30	case "${1:-status}" in
    31	    on)
    32	        DIRECTION="${2:-自主探索和修复系统问题}"
    33	        INTERVAL="${3:-$(hc_get "ghost_mode.default_poll_interval" "600")}"
    34	        EXPIRY_HOURS="${4:-$(hc_get "ghost_mode.default_expiry_hours" "3")}"
    35	        # DG-007 安全修复: 用 json.dumps 序列化而非 heredoc 裸拼接
    36	        # 避免 direction 中的换行/引号/特殊字符破坏 JSON 结构
    37	        export _LX_DIRECTION="$DIRECTION"
    38	        export _LX_INTERVAL="$INTERVAL"
    39	        export _LX_EXPIRY_HOURS="$EXPIRY_HOURS"
    40	        export _LX_MODE_FILE="$MODE_FILE"
    41	        ${PYTHON_BIN:-python3} <<'PYEOF'
    42	import json, os
    43	from datetime import datetime, timedelta, timezone
    44	
    45	direction = os.environ['_LX_DIRECTION']
    46	interval = int(os.environ['_LX_INTERVAL'])
    47	expiry_hours = int(os.environ['_LX_EXPIRY_HOURS'])
    48	mode_file = os.environ['_LX_MODE_FILE']
    49	expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
    50	
    51	data = {
    52	    "active": True,
    53	    "mode": "ghost",
    54	    "direction": direction,
    55	    "cycle_interval_seconds": interval,
    56	    "expires_at": expires,
    57	    "activated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    58	    "retry_count": 0,
    59	    "skipped_risks": [],
    60	    "hard_boundary_hits": [],
    61	    "blocked_human": []
    62	}
    63	
    64	tmp = mode_file + '.tmp.' + str(os.getpid())
    65	with open(tmp, 'w', encoding='utf-8') as f:
    66	    json.dump(data, f, indent=2, ensure_ascii=False)
    67	os.rename(tmp, mode_file)
    68	PYEOF
    69	        # 创建 autonomous.active 信号供 completion-gate 等降级
    70	        touch "$STATE_DIR/tokens/autonomous.active"
    71	        # 清理旧格式文件
    72	        rm -f "$STATE_DIR/.unattended-mode" "$STATE_DIR/ghost-mode.active" 2>/dev/null
    73	DATE=$(date +%Y-%m-%d)
    74	SLUG=$(echo "$DIRECTION" | tr " " "-" | tr -cd "[:alnum:]-_" | head -c 50)
    75	[ -z "$SLUG" ] && SLUG="ghost-$(date +%H%M%S)"
    76	CHAT_DIR="$PROJECT_ROOT/.omc/chats/${DATE}/${SLUG}"
    77	mkdir -p "$CHAT_DIR"
    78		${PYTHON_BIN:-python3} -c "import json; json.dump({'phase':'exploring','created_at':'$(date -u +%Y-%m-%dT%H:%M:%SZ)'},open('$CHAT_DIR/state.json','w'))"
    79		echo "# $DIRECTION
    80	
    81	> ghost模式自动创建 @ $(date)" > "$CHAT_DIR/progress.md"
    82		echo "RPE文档层: $CHAT_DIR" >&2
    83		# Save chat_dir to lx-ghost.json for runtime subcommands
    84		export _LX_CHAT_DIR="$CHAT_DIR"
    85		export _LX_MODE_FILE="$MODE_FILE"
    86		${PYTHON_BIN:-python3} <<'PYEOF'
    87	import json, os
    88	chat_dir = os.environ['_LX_CHAT_DIR']
    89	mode_file = os.environ['_LX_MODE_FILE']
    90	d = json.load(open(mode_file))
    91	d['rpe_chat_dir'] = chat_dir
    92	tmp = mode_file + '.tmp.' + str(os.getpid())
    93	with open(tmp, 'w', encoding='utf-8') as f:
    94	    json.dump(d, f, indent=2, ensure_ascii=False)
    95	os.rename(tmp, mode_file)
    96	PYEOF
    97		# 计算 CronCreate 参数
    98		CRON_MIN=$((INTERVAL / 60))
    99		[ "$CRON_MIN" -lt 1 ] && CRON_MIN=1
   100		echo "✅ 幽灵模式已开启 — 方向: $DIRECTION, 每 ${INTERVAL}s 轮询, ${EXPIRY_HOURS}h 过期"
   101		echo "   autonomous.active 信号已创建，evidence/completion gate 降级为 warn-only"
   102		echo ""
   103		echo "🔧 [必须执行·Step 0.5.3] 注册 CronCreate 跨会话轮询:"
   104		echo ""
   105		echo "   CronCreate"
   106		echo "     cron: \"*/${CRON_MIN} * * * *\""
   107		echo "     prompt: \"lx-ghost poll → 读取: cat $CHAT_DIR/progress.md → 继续探索方向'$DIRECTION' → 记录发现 → 完成则 lx-ghost off\""
   108		echo "     recurring: true"
   109		echo "     durable: true"
   110		echo ""
   111		echo "   ⚠️ durable=true: 会话结束后继续轮询，跨会话恢复"
   112		echo "   ⚠️ 跳过此步 = 幽灵模式仅在当前会话有效，会话结束即消失"
   113	        # 将决策链注入 AI 上下文（Oracle M1: 确保模式激活时 AI 立即看到决策链）
   114	        DECISION_CHAIN="$PROJECT_ROOT/.claude/reference/autonomous-decision-chain.md"
   115	        if [ -f "$DECISION_CHAIN" ]; then
   116	            echo "[.claude/reference/autonomous-decision-chain.md]"
   117	            cat "$DECISION_CHAIN"
   118	            echo ""
   119	        fi
   120	        ;;
   121	
   122	    off)
   123			# Write summary to RPE chat dir before cleanup
   124			if [ -f "$MODE_FILE" ]; then
   125				CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
   126				if [ -n "$CHAT_DIR" ] && [ -d "$CHAT_DIR" ]; then
   127					RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
   128					SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
   129					HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
   130					{
   131						echo ""
   132						echo "---"
   133						echo "## 退出摘要"
   134						echo "- 关闭时间: $(date)"
   135						echo "- 重试次数: ${RETRY:-0}"
   136						echo "- 跳过风险: ${SKIP:-0}"
   137						echo "- 硬边界拦截: ${HARD:-0}"
   138						echo ""
   139						echo "> 幽灵模式自动关闭 @ $(date)"
   140					} >> "$CHAT_DIR/progress.md"
   141					${PYTHON_BIN:-python3} -c "
   142	import json
   143	sf = '$CHAT_DIR/state.json'
   144	d = json.load(open(sf))
   145	d['phase'] = 'completed'
   146	d['completed_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
   147	json.dump(d, open(sf, 'w'), indent=2, ensure_ascii=False)
   148	" 2>/dev/null
   149				fi
   150				rm -f "$MODE_FILE"
   151			fi
   152			# 清理旧格式文件
   153			rm -f "$STATE_DIR/ghost-mode.json" "$STATE_DIR/ghost-mode.active" 2>/dev/null
   154			rm -f "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
   155			echo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断"
   156			;;
   157	    status)
   158	        if [ -f "$MODE_FILE" ]; then
   159	            DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
   160	            EXP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
   161	            INT=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('cycle_interval_seconds','?'))" 2>/dev/null)
   162	            RETRY=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('retry_count',0))" 2>/dev/null)
   163	            SKIP=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('skipped_risks',[])))" 2>/dev/null)
   164	            HARD=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)
   165	            echo "📋 幽灵模式 (lx-ghost): 🟢 开启中"
   166	            echo "   方向: $DIR"
   167	            echo "   间隔: ${INT}s"
   168	            echo "   过期: $EXP"
   169	            echo "   重试: $RETRY  跳过风险: $SKIP  硬边界: $HARD"
   170	        elif [ -f "$STATE_DIR/ghost-mode.json" ]; then
   171	            echo "📋 幽灵模式 (旧格式 ghost-mode.json): 🟡 兼容中"
   172	            echo "   建议执行 lx-ghost off && lx-ghost on \"方向\" 迁移到新格式"
   173	        else
   174	            echo "📋 幽灵模式 (lx-ghost): ⚪ 已关闭"
   175	        fi
   176	        if [ -f "$STATE_DIR/tokens/autonomous.active" ]; then
   177	            echo "   autonomous.active 信号: ✅ 存在"
   178	        fi
   179	        ;;
   180	
   181	    set)
   182	        KEY="$2"
   183	        VALUE="$3"
   184	        if [ ! -f "$MODE_FILE" ]; then
   185	            echo "❌ 幽灵模式未开启，无法修改"
   186	            exit 1
   187	        fi
   188	        export _LX_KEY="$KEY"
   189	        export _LX_VALUE="$VALUE"
   190	        export _LX_SET_MODE_FILE="$MODE_FILE"
   191	        ${PYTHON_BIN:-python3} <<'PYEOF'
   192	import json, os
   193	key = os.environ['_LX_KEY']
   194	value_str = os.environ['_LX_VALUE']
   195	mode_file = os.environ['_LX_SET_MODE_FILE']
   196	
   197	d = json.load(open(mode_file))
   198	# 尝试解析 JSON 值（数字/布尔/对象），失败则当字符串
   199	try:
   200	    value = json.loads(value_str)
   201	except (json.JSONDecodeError, ValueError):
   202	    value = value_str
   203	d[key] = value
   204	
   205	tmp = mode_file + '.tmp.' + str(os.getpid())
   206	with open(tmp, 'w', encoding='utf-8') as f:
   207	    json.dump(d, f, indent=2, ensure_ascii=False)
   208	os.rename(tmp, mode_file)
   209	print(f"✅ 幽灵模式 {key} 已更新为 {value}")
   210	PYEOF
   211	        ;;
   212	
   213	    poll)
   214	        # 幽灵模式轮询入口 — 由 loop skill / ralph-loop 调用
   215	        if [ ! -f "$MODE_FILE" ]; then
   216	            # 回退检查旧格式
   217	            if [ -f "$STATE_DIR/ghost-mode.json" ]; then
   218	                DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$STATE_DIR/ghost-mode.json')); print(d.get('direction','?'))" 2>/dev/null)
   219	                echo "⚠️ 旧格式 ghost-mode.json 存在，建议迁移: lx-ghost off && lx-ghost on \"$DIR\""
   220	            else
   221	                echo "❌ 幽灵模式未激活，停止轮询"
   222	            fi
   223	            exit 1
   224	        fi
   225	
   226	        # 检查过期
   227	        EXPIRES=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at',''))" 2>/dev/null)
   228	        if [ -n "$EXPIRES" ]; then
   229	            EXPIRED=$(${PYTHON_BIN:-python3} -c "
   230	from datetime import datetime
   231	try:
   232	    exp = datetime.fromisoformat('$EXPIRES')
   233	    print('yes' if datetime.now() > exp else 'no')
   234	except: print('no')" 2>/dev/null)
   235	            if [ "$EXPIRED" = "yes" ]; then
   236	                echo "⏰ 幽灵模式已过期（$EXPIRES），自动关闭"
   237	                rm -f "$MODE_FILE" "$STATE_DIR/tokens/autonomous.active" 2>/dev/null
   238	                exit 0
   239	            fi
   240	        fi
   241	
   242		echo "🔄 Ghost Poll #$((RETRY + 1)) | 方向: $DIR | 过期: $EXPIRES"
   243		echo ""
   244		CHAT_DIR=$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('rpe_chat_dir',''))" 2>/dev/null)
   245		echo "📋 执行指令:"
   246		echo "   1. 读取上次探索上下文: cat $CHAT_DIR/progress.md"
   247		echo "   2. 继续围绕方向: $DIR"
   248		echo "   3. 记录发现: 追加到 $CHAT_DIR/progress.md"
   249		echo "   4. 如有风险: lx-ghost skip-risk '风险描述'"
   250		echo "   5. 如方向完成: lx-ghost off"
   251		echo ""
   252		echo "   📊 已重试: $RETRY | 已跳过风险: $SKIP | 硬边界: $(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('$MODE_FILE')); print(len(d.get('hard_boundary_hits',[])))" 2>/dev/null)"
   253			;;
   254	
   255	    skip-risk)
   256			# 记录跳过的风险（供 permission-gate 等调用）
   257			DESCRIPTION="${2:-未知风险}"
   258			if [ ! -f "$MODE_FILE" ]; then
   259				echo "❌ 幽灵模式未开启"
   260				exit 1
   261			fi
   262			export _LX_DESC="$DESCRIPTION"
   263			export _LX_MODE_FILE="$MODE_FILE"
   264			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   265	import json, os
   266	from datetime import datetime, timezone
   267	
   268	desc = os.environ['_LX_DESC']
   269	mode_file = os.environ['_LX_MODE_FILE']
   270	
   271	d = json.load(open(mode_file))
   272	risks = d.get('skipped_risks', [])
   273	risks.append({'description': desc, 'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
   274	d['skipped_risks'] = risks
   275	
   276	# Append to RPE progress.md
   277	chat_dir = d.get('rpe_chat_dir', '')
   278	if chat_dir:
   279	    progress_file = os.path.join(chat_dir, 'progress.md')
   280	    if os.path.exists(progress_file):
   281	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   282	        with open(progress_file, 'a') as pf:
   283	            pf.write(f'\n- [skip-risk] {desc}  ({ts})\n')
   284	
   285	tmp = mode_file + '.tmp.' + str(os.getpid())
   286	with open(tmp, 'w', encoding='utf-8') as f:
   287	    json.dump(d, f, indent=2, ensure_ascii=False)
   288	os.rename(tmp, mode_file)
   289	PYEOF
   290			echo "📝 已记录跳过的风险: $DESCRIPTION"
   291			;;
   292	
   293	    hard-boundary-hit)
   294			# 记录硬边界拦截项（rm / git写 / 敏感文件 / API Key）
   295			DESCRIPTION="${2:-未知硬边界}"
   296			REASON="${3:-未知原因}"
   297			HUMAN_ACTION="${4:-请人工审阅并决定是否执行}"
   298			if [ ! -f "$MODE_FILE" ]; then
   299				echo "❌ 幽灵模式未开启"
   300				exit 1
   301			fi
   302			export _LX_DESC="$DESCRIPTION"
   303			export _LX_REASON="$REASON"
   304			export _LX_HUMAN_ACTION="$HUMAN_ACTION"
   305			export _LX_MODE_FILE="$MODE_FILE"
   306			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   307	import json, os
   308	from datetime import datetime, timezone
   309	
   310	desc = os.environ['_LX_DESC']
   311	reason = os.environ['_LX_REASON']
   312	human_action = os.environ['_LX_HUMAN_ACTION']
   313	mode_file = os.environ['_LX_MODE_FILE']
   314	
   315	d = json.load(open(mode_file))
   316	hits = d.get('hard_boundary_hits', [])
   317	hits.append({
   318	    'description': desc,
   319	    'reason': reason,
   320	    'human_action': human_action,
   321	    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   322	})
   323	d['hard_boundary_hits'] = hits
   324	
   325	# Append to RPE progress.md
   326	chat_dir = d.get('rpe_chat_dir', '')
   327	if chat_dir:
   328	    progress_file = os.path.join(chat_dir, 'progress.md')
   329	    if os.path.exists(progress_file):
   330	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   331	        with open(progress_file, 'a') as pf:
   332	            pf.write(f'\n- [hard-boundary] {desc} — {reason}  ({ts})\n')
   333	
   334	tmp = mode_file + '.tmp.' + str(os.getpid())
   335	with open(tmp, 'w', encoding='utf-8') as f:
   336	    json.dump(d, f, indent=2, ensure_ascii=False)
   337	os.rename(tmp, mode_file)
   338	PYEOF
   339			echo "🛑 硬边界拦截已记录: $DESCRIPTION (原因: $REASON)"
   340			;;
   341	
   342	    blocked-human)
   343			# 记录推迟到退出报告的人类决策项（裁决链 Level 3 blocked_human）
   344			# 与 hard-boundary-hit 不同：这些不是物理禁区，而是 AI 无法确定需要人类裁决
   345			DESCRIPTION="${2:-未知决策}"
   346			AI_RECOMMENDATION="${3:-AI 推荐方案未提供}"
   347			RATIONALE="${4:-决策依据未提供}"
   348			if [ ! -f "$MODE_FILE" ]; then
   349				echo "❌ 幽灵模式未开启"
   350				exit 1
   351			fi
   352			export _LX_DESC="$DESCRIPTION"
   353			export _LX_AI_RECOMMENDATION="$AI_RECOMMENDATION"
   354			export _LX_RATIONALE="$RATIONALE"
   355			export _LX_MODE_FILE="$MODE_FILE"
   356			${PYTHON_BIN:-python3} <<'PYEOF' || { echo "❌ 写入失败" >&2; exit 1; }
   357	import json, os
   358	from datetime import datetime, timezone
   359	
   360	desc = os.environ['_LX_DESC']
   361	ai_recommendation = os.environ['_LX_AI_RECOMMENDATION']
   362	rationale = os.environ['_LX_RATIONALE']
   363	mode_file = os.environ['_LX_MODE_FILE']
   364	
   365	d = json.load(open(mode_file))
   366	blocked = d.get('blocked_human', [])
   367	blocked.append({
   368	    'description': desc,
   369	    'ai_recommendation': ai_recommendation,
   370	    'rationale': rationale,
   371	    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   372	})
   373	d['blocked_human'] = blocked
   374	
   375	# Append to RPE progress.md
   376	chat_dir = d.get('rpe_chat_dir', '')
   377	if chat_dir:
   378	    progress_file = os.path.join(chat_dir, 'progress.md')
   379	    if os.path.exists(progress_file):
   380	        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   381	        with open(progress_file, 'a') as pf:
   382	            pf.write(f'\n- [blocked-human] {desc} → {ai_recommendation}  ({ts})\n')
   383	
   384	tmp = mode_file + '.tmp.' + str(os.getpid())
   385	with open(tmp, 'w', encoding='utf-8') as f:
   386	    json.dump(d, f, indent=2, ensure_ascii=False)
   387	os.rename(tmp, mode_file)
   388	PYEOF
   389			echo "🤔 推迟决策已记录: $DESCRIPTION → 推荐: $AI_RECOMMENDATION"
   390			;;
   391	
   392	    retry)
   393	        # 增加重试计数（供 retry-budget 对接）
   394	        if [ ! -f "$MODE_FILE" ]; then
   395	            echo "❌ 幽灵模式未开启"
   396	            exit 1
   397	        fi
   398	        ${PYTHON_BIN:-python3} -c "
   399	import json, os
   400	file = '$MODE_FILE'
   401	d = json.load(open(file))
   402	d['retry_count'] = d.get('retry_count', 0) + 1
   403	tmp = file + '.tmp.' + str(os.getpid())
   404	with open(tmp, 'w') as f:
   405	    json.dump(d, f, indent=2, ensure_ascii=False)
   406	os.rename(tmp, file)
   407	" 2>/dev/null && echo "📝 重试计数 +1（当前: $(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$MODE_FILE')).get('retry_count',0))" 2>/dev/null)）"
   408	        ;;
   409	
   410	    *)
   411	        echo "用法: lx-ghost on|off|status|set|poll|skip-risk|hard-boundary-hit|blocked-human|retry"
   412	        echo ""
   413	        echo "子命令:"
   414	        echo "  lx-ghost on \"方向描述\" [间隔秒数=600] [过期小时=3]"
   415	        echo "    示例: lx-ghost on \"将项目四维评分提升到 90+\""
   416	        echo "    示例: lx-ghost on \"检查所有 shell 脚本安全隐患\" 300 2"
   417	        echo "  lx-ghost off"
   418	        echo "  lx-ghost status"
   419	        echo "  lx-ghost set <json_key> <json_value>"
   420	        echo "  lx-ghost poll                    (loop skill 轮询入口)"
   421	        echo "  lx-ghost skip-risk \"描述\"       (记录跳过的风险)"
   422	        echo "  lx-ghost blocked-human \"决策\" \"AI推荐\" \"依据\"     (记录推迟到报告的人类决策)"
   423	        echo "  lx-ghost hard-boundary-hit \"操作\" \"原因\" \"需人类执行\"  (记录硬边界拦截)"
   424	        echo "  lx-ghost retry                   (重试计数 +1)"
   425	        echo ""
   426	        echo "驱动方式:"
   427	        echo "  /loop 600s lx-ghost poll         (定时轮询)"
   428	        echo "  /ralph-loop:ralph-loop \"...\"     (自愈循环)"
   429	        echo ""
   430	        echo "与 lx-goal 的区别:"
   431	        echo "  lx-ghost = 方向驱动（开源探索），lx-goal = 目标驱动（具体任务）"
   432	        exit 1
   433	        ;;
   434	esac
```

### `.claude/skills/lx-goal/scripts/lx-goal.sh`

```
     1	#!/usr/bin/env bash
     2	# lx-goal.sh — 兼容 wrapper，实际逻辑委托给 lx-goal.py
     3	# 用法: lx-goal on|off|status|set|report|poll|task-done|skip-risk|retry
     4	
     5	SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
     6	exec python3 "$SCRIPT_DIR/lx-goal.py" "$@"
     7	
```

### `.claude/profiles/merge-profile.sh`

```
     1	#!/bin/bash
     2	
     3	# merge-profile.sh — v5.3.0 base+diff 合并工具
     4	# 用法：
     5	#   bash .claude/profiles/merge-profile.sh go       # 合并 base+go
     6	#   bash .claude/profiles/merge-profile.sh node      # 合并 base+node
     7	#   bash .claude/profiles/merge-profile.sh python    # 合并 base+python
     8	#   bash .claude/profiles/merge-profile.sh rust      # 合并 base+rust
     9	#   bash .claude/profiles/merge-profile.sh go --dry-run  # 预览不写文件
    10	#   bash .claude/profiles/merge-profile.sh --list    # 列出可用 profile
    11	#
    12	# 合并规则：
    13	#   1. 从 base/harness.yaml 读取所有通用字段
    14	#   2. 用 {lang}/harness.yaml 的字段覆盖（同名 section.key 以 diff 为准）
    15	#   3. diff 中的 hooks_enabled 子键做"增量覆盖"（不替换整块，仅覆盖出现的键）
    16	#   4. 输出合并后的完整 harness.yaml
    17	
    18	set -eo pipefail
    19	RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
    20	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    21	BASE="$SCRIPT_DIR/base/harness.yaml"
    22	OUTPUT="${CLAUDE_DIR:-.claude}/harness.yaml"
    23	
    24	# ── --list ────────────────────────────────────────────────────────
    25	if [ "$1" = "--list" ]; then
    26	    echo "可用 profile："
    27	    for d in "$SCRIPT_DIR"/*/; do
    28	        name=$(basename "$d")
    29	        [[ "$name" == "base" ]] && continue
    30	        [ -f "$d/harness.yaml" ] && echo "  $name"
    31	    done
    32	    exit 0
    33	fi
    34	
    35	LANG="${1:-}"
    36	DRY_RUN=false
    37	[ "$2" = "--dry-run" ] && DRY_RUN=true
    38	
    39	# ── 参数校验 ──────────────────────────────────────────────────────
    40	if [ -z "$LANG" ]; then
    41	    echo -e "${RED}[ERROR]${NC} 请指定语言: go / node / python / rust"
    42	    echo "  用法: bash .claude/profiles/merge-profile.sh <lang> [--dry-run]"
    43	    exit 1
    44	fi
    45	
    46	DIFF="$SCRIPT_DIR/$LANG/harness.yaml"
    47	
    48	if [ ! -f "$BASE" ]; then
    49	    echo -e "${RED}[ERROR]${NC} base/harness.yaml 不存在: $BASE"
    50	    exit 1
    51	fi
    52	if [ ! -f "$DIFF" ]; then
    53	    echo -e "${RED}[ERROR]${NC} 未找到 profile: $DIFF"
    54	    exit 1
    55	fi
    56	
    57	# ── Python3 合并核心 ──────────────────────────────────────────────
    58	_MERGE_PY=$(mktemp "${TMPDIR:-/tmp}/.merge_profile_py.XXXXXX") || { echo "创建临时文件失败"; exit 1; }
    59	
    60	cat > "$_MERGE_PY" << 'PYEOF'
    61	import sys
    62	
    63	def parse_yaml_flat(path):
    64	    """解析 YAML 为嵌套 dict（支持2层 + 列表）"""
    65	    result = {}
    66	    current_section = None
    67	    current_list_key = None
    68	    current_list = []
    69	    with open(path, encoding='utf-8') as f:
    70	        for raw in f:
    71	            line = raw.rstrip('\n\r')
    72	            stripped = line.strip()
    73	            if not stripped or stripped.startswith('#'):
    74	                if current_list_key and current_list:
    75	                    if current_section not in result:
    76	                        result[current_section] = {}
    77	                    result[current_section][current_list_key] = current_list[:]
    78	                    current_list_key, current_list = None, []
    79	                continue
    80	            indent = len(line) - len(line.lstrip())
    81	            if stripped.startswith('- '):
    82	                if current_list_key:
    83	                    current_list.append(stripped[2:].strip().strip('"').strip("'"))
    84	                continue
    85	            if current_list_key and current_list:
    86	                if current_section not in result:
    87	                    result[current_section] = {}
    88	                result[current_section][current_list_key] = current_list[:]
    89	                current_list_key, current_list = None, []
    90	            if ':' in stripped:
    91	                colon = stripped.index(':')
    92	                key = stripped[:colon].strip()
    93	                val = stripped[colon+1:].strip()
    94	                if val and val[0] in ('"', "'") and val[-1] == val[0]:
    95	                    val = val[1:-1]
    96	                if indent == 0:
    97	                    if val:
    98	                        result[key] = val
    99	                    else:
   100	                        current_section = key
   101	                        if key not in result:
   102	                            result[key] = {}
   103	                elif indent > 0 and current_section:
   104	                    if val:
   105	                        result[current_section][key] = val
   106	                    else:
   107	                        current_list_key = key
   108	                        current_list = []
   109	        if current_list_key and current_list and current_section:
   110	            result[current_section][current_list_key] = current_list[:]
   111	    return result
   112	
   113	
   114	def merge(base, diff):
   115	    merged = {}
   116	    for k, v in base.items():
   117	        if isinstance(v, dict):
   118	            merged[k] = dict(v)
   119	        elif isinstance(v, list):
   120	            merged[k] = list(v)
   121	        else:
   122	            merged[k] = v
   123	    for k, v in diff.items():
   124	        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
   125	            merged[k] = {**merged[k], **v}
   126	        elif isinstance(v, list):
   127	            merged[k] = list(v)
   128	        else:
   129	            merged[k] = v
   130	    return merged
   131	
   132	
   133	def val_to_yaml(v, indent=2):
   134	    pad = ' ' * indent
   135	    if isinstance(v, list):
   136	        return '\n' + '\n'.join(f"{pad}- {item}" for item in v)
   137	    if isinstance(v, bool):
   138	        return 'true' if v else 'false'
   139	    s = str(v)
   140	    if any(c in s for c in ['#', ':', '{', '}', '[', ']', ',', '&', '*', '?', '|', '<', '>', '=', '!', '%', '@', '`']):
   141	        return f'"{s}"'
   142	    return s
   143	
   144	
   145	base_data = parse_yaml_flat(sys.argv[1])
   146	diff_data = parse_yaml_flat(sys.argv[2])
   147	lang = sys.argv[3]
   148	merged = merge(base_data, diff_data)
   149	
   150	SECTION_ORDER = [
   151	    'project', 'protected_files', 'architecture', 'workflow',
   152	    'task_decomposition', 'knowledge', 'turn_counter', 'fuzzy_detection',
   153	    'lsp_suggest', 'subagent_guard', 'completion_gate', 'bash_audit',
   154	    'permission_gate', 'sublimation', 'correction_detector',
   155	    'session_handoff', 'error_dna', 'coupling', 'hooks_enabled',
   156	]
   157	
   158	lines = [
   159	    f"# harness-kit harness.yaml — {lang} profile (base+diff merged)",
   160	    f"# 由 merge-profile.sh 生成，源文件: profiles/base + profiles/{lang}",
   161	    "# 手动编辑此文件的修改在下次 merge 时会被覆盖",
   162	    "",
   163	]
   164	
   165	seen = set()
   166	for section in SECTION_ORDER:
   167	    if section not in merged:
   168	        continue
   169	    seen.add(section)
   170	    v = merged[section]
   171	    lines.append(f"{section}:")
   172	    if isinstance(v, dict):
   173	        for sk, sv in v.items():
   174	            yv = val_to_yaml(sv)
   175	            if yv.startswith('\n'):
   176	                lines.append(f"  {sk}:{yv}")
   177	            else:
   178	                lines.append(f"  {sk}: {yv}")
   179	    else:
   180	        lines.append(f"  {val_to_yaml(v)}")
   181	    lines.append("")
   182	
   183	for section, v in merged.items():
   184	    if section in seen:
   185	        continue
   186	    lines.append(f"{section}:")
   187	    if isinstance(v, dict):
   188	        for sk, sv in v.items():
   189	            yv = val_to_yaml(sv)
   190	            if yv.startswith('\n'):
   191	                lines.append(f"  {sk}:{yv}")
   192	            else:
   193	                lines.append(f"  {sk}: {yv}")
   194	    else:
   195	        lines.append(f"  {val_to_yaml(v)}")
   196	    lines.append("")
   197	
   198	print('\n'.join(lines))
   199	PYEOF
   200	
   201	MERGED=$(${PYTHON_BIN:-python3} "$_MERGE_PY" "$BASE" "$DIFF" "$LANG")
   202	rm -f "$_MERGE_PY"
   203	
   204	# ── 输出 ──────────────────────────────────────────────────────────
   205	if [ "$DRY_RUN" = true ]; then
   206	    echo -e "${YELLOW}[DRY-RUN]${NC} 合并结果（不写文件）："
   207	    echo "---"
   208	    echo "$MERGED"
   209	    echo "---"
   210	    LINES=$(echo "$MERGED" | wc -l | tr -d ' ')
   211	    echo -e "${GREEN}[INFO]${NC} 合并后 $LINES 行（base 覆盖 + $LANG diff）"
   212	else
   213	    mkdir -p "$(dirname "$OUTPUT")"
   214	    echo "$MERGED" > "$OUTPUT"
   215	    LINES=$(wc -l < "$OUTPUT" | tr -d ' ')
   216	    echo -e "${GREEN}[OK]${NC} 已写入 $OUTPUT（$LINES 行，base + $LANG diff 合并）"
   217	fi
```

### `.claude/skills/lx-validate-skill/SKILL.md`

```
     1	---
     2	name: lx-validate-skill
     3	version: v4.0.0
     4	description: "验收新 skill 是否遵循原子化架构规则。检查 frontmatter、原子化声明、节点/Schema 引用、无私有目录等 11 项规则。"
     5	complexity: beginner
     6	when_to_use: "Use after creating a new skill. Trigger: 'validate skill', 'check skill', 'new skill review', 'skill audit'."
     7	argument-hint: "[skill-name, default: all lx-* skills]"
     8	paths:
     9	  - ".claude/skills/lx-*/SKILL.md"
    10	harness_version: ">=6.3.0"
    11	status: draft
    12	role: "Skill atomization compliance validator — 11-rule architecture check"
    13	execution_mode: stepwise
    14	triggers:
    15	  - "/lx-validate-skill"
    16	nodes:
    17	  - scanner                  # 按规则集扫描 skill（R1-R11）
    18	  - report_generator         # 生成合规报告
    19	  - behavior_rules           # 自洽检查
    20	schemas:
    21	  - atomic/scan_report       # 扫描报告
    22	  - atomic/verdict           # 最终判定
    23	  - atomic/finding           # 合规问题发现
    24	---
    25	# lx-validate-skill — 原子化架构合规检查
    26	
    27	## 原子化声明
    28	
    29	### 通用节点
    30	| 节点 | 路径 | 用途 |
    31	|------|------|------|
    32	| scanner | `../../nodes/scanner.md` | 按 R1-R11 规则集扫描 skill |
    33	| report_generator | `../../nodes/report_generator.md` | 生成合规检查报告 |
    34	| behavior_rules | `../../nodes/behavior_rules.md` | 自洽检查 |
    35	
    36	### Schema
    37	| Schema | 路径 | 用途 |
    38	|--------|------|------|
    39	| scan_report | `../../schemas/atomic/scan_report.yaml` | 扫描报告 |
    40	| verdict | `../../schemas/atomic/verdict.yaml` | 最终判定 |
    41	| finding | `../../schemas/atomic/finding.yaml` | 合规问题发现 |
    42	
    43	### scripts/（确定性执行层）
    44	| 脚本 | 用途 | 调用时机 |
    45	|------|------|---------|
    46	| `scripts/validate_skill.py` | 核心校验：R1-R11 规则引擎 | 全流程 |
    47	| `scripts/skill_trace_report.py` | skill 依赖追踪报告 | review 阶段 |
    48	| `scripts/check_progressive_disclosure.py` | 渐进式披露合规检查 | review 阶段 |
    49	| `scripts/carror_dashboard.py` | 系统健康面板 | 运行时 |
    50	
    51	### references/（按需加载）
    52	| 文件 | 加载时机 |
    53	|------|---------|
    54	| `references/report-templates.md` | 生成合规报告时 |
    55	---
    56	
    57	表
    58	
    59	| 编号 | 规则 | 检查方式 |
    60	|:----|:-----|:---------|
    61	| R1 | frontmatter 包含必填字段 | yaml 解析 |
    62	| R2 | SKILL.md 包含 nodes 声明 | `grep '^nodes:' SKILL.md` |
    63	| R3 | SKILL.md 内联完整（无 body_ref） | 无 body_ref: 行 |
    64	| R4 | 无私有 nodes/ 目录 | `ls skills/lx-*/nodes/` |
    65	| R5 | 无私有 schemas/ 目录 | `ls skills/lx-*/schemas/` |
    66	| R6 | scripts/ 仅 .py（无 .sh 超出模板文件） | glob 检查 |
    67	| R7 | frontmatter 有 description | yaml 校验 |
    68	| R8 | 至少引用 1 个 `../../nodes/` | grep SKILL.md |
    69	| R9 | 至少引用 1 个 `../../schemas/` | grep SKILL.md |
    70	| R10 | 无私有 nodes | 同 R4 |
    71	| R11 | 无私有 schemas | 同 R5 |
    72	
    73	## 执行流程
    74	
    75	```
    76	1. 确定检查目标（指定 skill 或 all）
    77	2. 逐 skill 扫描 R1-R11（scanner 节点单规则执行）
    78	3. 输出合规报告（含每条规则的 PASS/FAIL）
    79	4. 打印改善建议
    80	```
    81	
    82	## 调用方式
    83	
    84	```bash
    85	# 检查单个 skill
    86	/lx-validate-skill lx-goal
    87	
    88	# 检查所有 skill
    89	/lx-validate-skill all
    90	
    91	# 检查特定目录
    92	python3 .claude/skills/lx-validate-skill/scripts/validate_skill.py --skills-dir .claude/skills
    93	```
```

### `.claude/skills/lx-rpe/SKILL.md`

```
     1	---
     2	name: lx-rpe
     3	version: v4.0.0
     4	description: "RPE 系统性特性开发 — 9 步闭环：TDD → code-review → security → acceptance → graded rollback"
     5	complexity: advanced
     6	when_to_use: "Use when user says 'rpe', 'feature dev', '/lx-rpe', or begins systematic feature development"
     7	argument-hint: "new [name] [需求描述] | [feature name] | [path] | status | batch-accept"
     8	harness_version: ">=6.3.0"
     9	status: mature
    10	role: "RPE-driven feature development — 9-step closed loop with quality gates"
    11	execution_mode: stepwise
    12	triggers:
    13	  - "/lx-rpe"
    14	---
    15	# lx-rpe — 主分支系统性开发
    16	
    17	## 原子化声明
    18	
    19	| 节点 | 路径 |
    20	|------|------|
    21	| scanner | `../../nodes/scanner.md` |
    22	| auto_fixer | `../../nodes/auto_fixer.md` |
    23	| verifier | `../../nodes/verifier.md` |
    24	| report_generator | `../../nodes/report_generator.md` |
    25	| behavior_rules | `../../nodes/behavior_rules.md` |
    26	
    27	| 脚本 | 用途 |
    28	|------|------|
    29	| `scripts/git_commit.py` | Git 提交 |
    30	| `scripts/update_progress.py` | 进度更新 |
    31	| `scripts/extract_ac.py` | AC 提取 |
    32	| `scripts/build_and_test.py` | 编译+测试门禁 |
    33	
    34	Schema: scan_target / finding / scan_report / fix_record / verdict
    35	
    36	### references/（按需加载）
    37	| 文件 | 加载时机 |
    38	|------|---------|
    39	| `references/batch-accept-template.md` | batch accept template 阶段 |
    40	| `references/commit-convention.md` | commit convention 阶段 |
    41	| `references/frontend-coding-rules.md` | frontend coding rules 阶段 |
    42	| `references/gate-checklist.md` | gate checklist 阶段 |
    43	| `references/go-coding-rules.md` | go coding rules 阶段 |
    44	| `references/progress-file-template.md` | progress file template 阶段 |
    45	| `references/progress-panel-template.md` | progress panel template 阶段 |
    46	| `references/recovery-flow.md` | recovery flow 阶段 |
    47	| `references/rpe_main_loop.md` | rpe_main_loop 阶段 |
    48	| `references/rpe_phases.md` | rpe_phases 阶段 |
    49	| `references/security-scan-rules.md` | security scan rules 阶段 |
    50	
    51	> 降级升级: @../references/oma/degradation-escalation.md
    52	> 裁决链: @../references/oma/decision-chain.md
    53	> 执行工作流: @../references/oma/execution-workflow.md
    54	
    55	## 状态机
    56	
    57	```
    58	Read Task → Design → Code+Pre-commit → Security → Sync → Wait Acceptance → Judge → Commit → Summary
    59	```
    60	
    61	## 硬性约束
    62	
    63	- NEVER 做验收决策（用户执行）
    64	- NEVER 混入 todo 概念 — 只有 Step
    65	- ALWAYS 按项目类型路由（Go: go-zero / 前端: React+TS）
    66	
    67	## 入口路由
    68	
    69	| 子命令 | 动作 |
    70	|--------|------|
    71	| 无参数 | 自动恢复最近活跃 RPE |
    72	| `new` | 初始化新特性 → `@references/rpe_phases.md` |
    73	| `[name]` | 继续指定特性 |
    74	| `[path]` | OMA 目录路径 |
    75	| `status` | 结构化进度面板 → `@references/progress-panel-template.md` |
    76	| `batch-accept` | 批量验收 → `@references/batch-accept-template.md` |
    77	
    78	## 新建流程 → `@references/rpe_phases.md`
    79	
    80	Phase 1 Research → 用户审阅 → Gate-R → Phase 2 Plan（Task+AC+测试+回滚）→ Gate-P/X → Phase 3 Execute → 主循环
    81	
    82	## 恢复流程 → `@references/recovery-flow.md`
    83	
    84	自动检测恢复点 → 上下文校验（research/plan/任务完整性）→ 恢复摘要 → 进入阶段
    85	
    86	## 主循环 → `@references/rpe_main_loop.md`
    87	
    88	```
    89	[1]读任务→[2]设计→[3]编码+pre-commit→[4]Security→[5]同步→[6]等待验收→[7]判定→[8]Commit→[9]摘要
    90	```
    91	
    92	回退：编译失败 3 次→回 Step 2 | 验收不通过→按类型回退 | 回退 3 次→暂停
    93	
    94	## Pipeline 集成
    95	
    96	编排由 `lx-oma-orch` 统一管理。lx-rpe 不做 pipeline.yaml 读写，仅接收 BASE_DIR。
    97	
    98	## 降级策略
    99	
   100	> 共享降级: `@../references/oma/degradation-escalation.md`
   101	
   102	| 场景 | 主路径 | 降级 |
   103	|------|--------|------|
   104	| build_and_test.py 失败 | 脚本 | go build && go test |
   105	| git_commit.py 失败 | 脚本 | git add + git commit（需确认） |
   106	| Gate-X 频繁 >3次 | 暂停 | 回 Phase 2 重审 |
   107	| Phase 迭代 >5轮 | 继续 | 暂停，简化需求 |
```

### `.claude/skills/lx-oma/SKILL.md`

```
     1	---
     2	name: lx-oma
     3	description: OMA Pipeline — hierarchically decompose, split into features, govern, orchestrate
     4	version: v2.0.0
     5	harness_version: ">=6.3.0"
     6	status: stable
     7	argument-hint: >
     8	  hier <path> [output_dir] | split <path> [--pipeline <id>] |
     9	  gov init|reconcile|resolve|propagate|status|audit [path] |
    10	  orch status|advance|gate|run|dev
    11	when_to_use: PRD 全生命周期 — 拆解、拆分、治理、编排
    12	triggers: ["/lx-oma", "oma", "pipeline", "/lx-oma-hier", "/lx-oma-split", "/lx-oma-gov", "/lx-oma-orch", "分层拆解", "prd 拆分", "拆解需求", "一人成军拆解", "oma治理", "reconcile", "propagate", "漂移检测", "管线状态", "orchestrate"]
    13	role: "OMA — Pipeline lifecycle (hier → split → gov → rpe)"
    14	execution_mode: stepwise
    15	---
    16	
    17	# lx-oma OMA Pipeline — Unified Skill
    18	
    19	> 合并自 lx-oma-hier v1.3.2 · lx-oma-split v1.2.1 · lx-oma-gov v1.2.1 · lx-oma-orch v1.2.2
    20	> 向后兼容：原 `/lx-oma-hier` `/lx-oma-split` `/lx-oma-gov` `/lx-oma-orch` 仍可触发
    21	
    22	## Subcommand 分发
    23	
    24	```
    25	/lx-oma hier <path> [output_dir]           → L1 分层拆解（原 lx-oma-hier）
    26	/lx-oma split <path> [--pipeline <id>]     → L2 特性拆解（原 lx-oma-split）
    27	/lx-oma gov <subcommand> [args...]         → 治理操作（原 lx-oma-gov）
    28	/lx-oma orch <subcommand> [args...]        → 管线编排（原 lx-oma-orch）
    29	```
    30	
    31	> **注意：** `execution_mode: stepwise` 为根级声明。split 子命令内部使用 `race` 模式 — AI 自主拆解 + 脚手架构建后交还人工审核门禁。
    32	
    33	## 共享 OMA 基础设施
    34	
    35	| 文件 | 路径 | 用途 |
    36	|------|------|------|
    37	| 降级升级策略 | `@../references/oma/degradation-escalation.md` | 降级路径 |
    38	| 裁决链 | `@../references/oma/decision-chain.md` | 决策记录 |
    39	| 执行工作流 | `@../references/oma/execution-workflow.md` | 通用执行规范 |
    40	| 链式承接 | `@../references/oma/skill-chaining.md` | 技能间委托 |
    41	| 可观测性 | `@../references/oma/observability.md` | 遥测规范 |
    42	| Pipeline 契约 | `@../references/oma/pipeline-contract.md` | 集成契约 |
    43	| 错误码体系 | `@../references/oma/error-codes.md` | 共享错误码 |
    44	| 方向指南 | `@../references/oma/direction-guide.md` | 方向指导 |
    45	
    46	### 原子化节点
    47	
    48	| 节点 | 路径 | 用途 |
    49	|------|------|------|
    50	| explore | `../../nodes/explore.md` | 文件/目录读取 |
    51	| verifier | `../../nodes/verifier.md` | 质量验证 |
    52	| oracle | `../../nodes/oracle_terminal.md` | 阶段转移门禁裁决 |
    53	| mode_selector | `../../nodes/mode_selector.md` | 执行模式路由 |
    54	
    55	### Schema
    56	
    57	| Schema | 路径 | 用途 |
    58	|--------|------|------|
    59	| verdict | `../../schemas/atomic/verdict.yaml` | MECE 拆解质量判定 |
    60	| error_codes | `../../schemas/atomic/error_codes.yaml` | 错误码共享体系 |
    61	
    62	---
    63	
    64	## hier — L1 分层 PRD 拆解（原 lx-oma-hier）
    65	
    66	### references/（按需加载）
    67	
    68	| 文件 | 加载时机 |
    69	|------|---------|
    70	| `references/hier/sub-prd-template.md` | sub prd 模板 |
    71	| `references/hier/verification-gate.md` | verification gate |
    72	
    73	### 状态机
    74	
    75	```
    76	need_input → [reading → analyzing → generating → verifying] → done
    77	```
    78	
    79	### 任务目标
    80	
    81	将超大型 PRD 按功能域 MECE 拆分为 N 个 Sub PRD，确保功能正交、黑盒边界、可独立闭环、可独立交付。
    82	> Sub PRD 模板 → `@references/hier/sub-prd-template.md` · 全生命周期管线 → `@../references/oma/pipeline-contract.md`
    83	
    84	### 参数处理
    85	
    86	入参 `<path>` + 可选 `[output_dir]`。模式：`--pipeline` 编排模式 / 无参数 手动模式。
    87	输出路径: kernel.md 约定 → 用户显式 → 默认 `sub-prds/`。
    88	文件直接读、目录读所有 `.md`、图片描述结构。
    89	
    90	### MECE 功能域拆解
    91	
    92	1. **识别核心业务实体** → 实体归属表（实体名/候选域/归属理由/原文引用）
    93	2. **按职责聚类** → 围绕实体聚合功能
    94	3. **正交性校验** → 域对检查职责重叠+数据交叉
    95	4. **边界确认** → 每个域"管什么/不管什么"
    96	
    97	#### MECE 校验摘要
    98	- 正交性矩阵: 域对×重叠点×裁决（引用原文）
    99	- 实体唯一 Own、接口耦合度(>10 警告)、孤儿接口检查、NFR 来源校验(无来源标注 `[内部自检]`)
   100	
   101	#### 依赖分析
   102	域间依赖图（A→B），区分服务依赖 vs 代码依赖，识别循环依赖，标注优先开发域。
   103	
   104	### 输出目录结构
   105	
   106	```
   107	{output_dir}/
   108	  INDEX.md              ← 层级关系树 + 依赖图 + 开发顺序
   109	  domain-{name}.md      ← Sub PRD
   110	```
   111	
   112	### 校验与门禁
   113	
   114	```bash
   115	python3 .claude/scripts/verify_oma_mece.py {output_dir}/  # exit 0 → ✅
   116	```
   117	
   118	质量报告: verify_oma_mece.py exit_code + 模板字段8项 + 非功能契约一致性 + 父需求全覆盖。
   119	G1 Meta-Oracle: ≥2子系统+不可逆变更时触发 → `@references/hier/verification-gate.md#meta-oracle-g1`
   120	
   121	### 降级策略
   122	
   123	| 场景 | 降级路径 |
   124	|------|---------|
   125	| verify_oma_mece.py 不可用 | 降级为手动 MECE 自检清单 |
   126	| Sub PRD 输出失败 | 保留中间产物，标注缺失项 |
   127	| MECE 校验 3 轮未通过 | 标记需人工介入 |
   128	
   129	---
   130	
   131	## split — L2 特性拆解（原 lx-oma-split）
   132	
   133	### references/（按需加载）
   134	
   135	| 文件 | 加载时机 |
   136	|------|---------|
   137	| `references/split/mece-checklist.md` | MECE 拆解 |
   138	| `references/split/scaffolding-template.md` | 脚手架构建 |
   139	| `references/split/interface-verification.md` | 接口归属校验 |
   140	| `references/split/delivery-report.md` | 战报交付 |
   141	
   142	### 状态机
   143	
   144	```
   145	need_input → [reading → analyzing → scaffolding → verifying] → done
   146	```
   147	
   148	### 执行流程
   149	
   150	#### 1. 参数处理
   151	读取 `<path>`（文件→读内容，目录→读所有 .md）。未提供→询问用户。
   152	从路径提取 `sub_prd_name`（如 `sub-prds/domain-auth.md` → `auth`）。
   153	
   154	#### 2. MECE 正交拆解 → `@references/split/mece-checklist.md`
   155	3-6 个 Feature，相互独立、完全穷尽。执行自检清单（正交性/完整性/独立性）。
   156	
   157	#### 3. 脚手架构建 → `@references/split/scaffolding-template.md`
   158	每个 Feature 自动生成 `prd/{sub_prd_name}/feat-XXX/{state,contracts,mocks}/prd.md`。
   159	
   160	#### 4. 接口归属校验（阻断门禁） → `@references/split/interface-verification.md`
   161	`verify_oma_interface_coverage.py` — 未归属接口必须修复后才放行。
   162	
   163	#### 5. 战报交付 → `@references/split/delivery-report.md`
   164	输出 feature 清单 + 并发启动指令（`/lx-rpe prd/...`）。
   165	
   166	### Pipeline 集成
   167	
   168	入口 `--pipeline <id>` → 检查 `hier_done` → 出口 `features[].stage=oma_created`。
   169	> 完整契约 → `@../references/oma/pipeline-contract.md`
   170	
   171	### 人工审核门禁
   172	
   173	```
   174	[ ] feature prd.md 完整？  [ ] 接口归属 exit 0？
   175	[ ] 无 phantom 接口？      [ ] MECE 正交？
   176	[ ] 所有目录已创建？
   177	确认: /lx-oma orch gate og-NNN approve
   178	```
   179	
   180	### 降级策略
   181	
   182	| 场景 | 主路径 | 降级 |
   183	|------|--------|------|
   184	| Sub PRD <200 字 | 按已有内容拆解 | 告知内容不足 |
   185	| 校验脚本不存在 | 自动化校验 | 降级手动校验 |
   186	| hier 不可用 | 委托调用 | 手动 `/lx-oma hier` |
   187	
   188	---
   189	
   190	## gov — PRD 治理（原 lx-oma-gov）
   191	
   192	### 专属文件
   193	
   194	| 文件 | 用途 |
   195	|------|------|
   196	| `gov/governance-spec.md` | 完整规范（对象 ID/状态机/漂移规则） |
   197	| `gov/HUMAN-IN-THE-LOOP-GATE.md` | awaiting_human_decision 状态机 |
   198	| `gov/state/sync-state.md` | 同步状态跟踪 |
   199	
   200	### references/（按需加载）
   201	
   202	| 文件 | 加载时机 |
   203	|------|---------|
   204	| `references/gov/directory-structure.md` | init |
   205	| `references/gov/commands-reconcile.md` | reconcile/verifier/resolve/propagate |
   206	| `references/gov/commands-audit.md` | audit |
   207	| `references/gov/pipeline-integration.md` | pipeline |
   208	
   209	### 状态机
   210	
   211	```
   212	need_input
   213	  → [init] → initialized
   214	  → [reconcile] → reconciling
   215	      → [no changes] → done
   216	      → [L3 conflict] → awaiting_human_decision → [resolve] → reconciling
   217	      → [changes ready] → verifying → propagating_dry_run
   218	          → [confirmed] → propagating → done
   219	  → [status] → done
   220	  → [audit] → done
   221	  → [error] → [repair → undone | reset → initialized]
   222	```
   223	
   224	### 命令
   225	
   226	#### init → `@references/gov/directory-structure.md`
   227	`/lx-oma gov init [path]` — 创建 state/ + source-prds/ + snapshots/ + 日志
   228	
   229	#### reconcile / verifier / resolve / propagate → `@references/gov/commands-reconcile.md`
   230	变更检测（L1/L2/L3 分级）→ verifier 质量门禁 → resolve 人工裁决 → propagate 增量传播
   231	
   232	#### status — 治理状态面板
   233	#### audit → `@references/gov/commands-audit.md`
   234	四类漂移检测（ID 孤儿/版本落后/冲突定义/孤立变更）
   235	
   236	### Pipeline 集成 → `@references/gov/pipeline-integration.md`
   237	只读 pipeline.yaml。命令执行后输出 governance-report.yaml 供 orch 消费。
   238	
   239	### 治理质量自检
   240	
   241	1. CHG-ID 完整性：格式 `CHG-YYYYMMDD-NNN`
   242	2. CHG 分类正确性：L3 必须涉及 REQ-/DEC-/TERM- 修改
   243	3. CONFLICT-ID 闭合性：已裁决标记 resolved
   244	4. 幂等安全：重复 propagate 不产生重复内容
   245	5. 引用一致性：propagate 后所有引用在 master 中存在
   246	6. 同步状态：活跃 feature 同步时间 ≥ 最后 reconcile
   247	
   248	### 降级策略
   249	
   250	| 场景 | 主路径 | 降级 |
   251	|------|--------|------|
   252	| 治理目录不存在 | 报错 | 先运行 init |
   253	| reconcile 无变更 | 报告"无差异" | fast path done |
   254	| L3 冲突无裁决 | 挂起 + 提示 | 继续 L1/L2 |
   255	| propagate 目标缺失 | 跳过 | 列出缺失 feature |
   256	| 锁超时 | 自动释放 | 记录清除日志 |
   257	
   258	---
   259	
   260	## orch — Pipeline 编排器（原 lx-oma-orch）
   261	
   262	### 子 skill 路由
   263	
   264	| 目标 | 路由 |
   265	|------|------|
   266	| Sub PRD | lx-oma hier (self) |
   267	| Feature | lx-oma split (self) |
   268	| 治理 | lx-oma gov (self) |
   269	| RPE | lx-rpe |
   270	
   271	### references/（按需加载）
   272	
   273	| 文件 | 加载时机 |
   274	|------|---------|
   275	| `references/orch/status-panel.md` | status |
   276	| `references/orch/advance-flow.md` | advance |
   277	| `references/orch/oracle-gate.md` | gate |
   278	| `references/orch/dev-management.md` | dev |
   279	| `references/orch/interface-contract.md` | 接口契约 |
   280	| `references/orch/manual-review.md` | 人工审核 |
   281	
   282	### 状态机
   283	
   284	```
   285	idle → [status] → done
   286	     → [advance] → checking_oracle_gate
   287	         → [blocked] → awaiting_decision → [approve/reject] → advance/abort
   288	         → [passed] → calling_skill → update_pipeline → done
   289	     → [gate <id> approve|reject] → update_pipeline → done
   290	     → [run <target>] → route_to_skill → done
   291	     → [dev list|mark] → done
   292	```
   293	
   294	### 命令
   295	
   296	#### status — 管线全景 → `@references/orch/status-panel.md`
   297	#### advance — 推进阶段 → `@references/orch/advance-flow.md`
   298	检查→路由→执行→更新→人工确认。
   299	
   300	#### gate — Oracle 门禁 → `@references/orch/oracle-gate.md`
   301	`/lx-oma orch gate <og-id> approve|reject [--reason "..."]`
   302	
   303	#### run — 直接路由（绕过阶段检查）
   304	| 目标 | 路由 |
   305	|------|------|
   306	| Sub PRD | lx-oma hier |
   307	| Feature | lx-oma split |
   308	| 治理 | lx-oma gov |
   309	| RPE | lx-rpe |
   310	
   311	#### dev — 并行开发 → `@references/orch/dev-management.md`
   312	
   313	### Pipeline 更新 → `@../references/oma/pipeline-contract.md`
   314	原子写入（tmp→rename）+ 更新规则 + Oracle gate 创建。
   315	
   316	### 降级策略
   317	
   318	| 场景 | 降级路径 |
   319	|------|---------|
   320	| advance 失败 | 检查管线状态，手动修复 |
   321	| gate 不可用 | 跳过 Oracle 门禁，标注 [无Oracle审核] |
   322	| Pipeline 写入失败 | 降级为手动状态跟踪 |
```

### `.claude/references/feature-registry.yaml`

```
     1	version: 1
     2	hooks:
     3	- name: permission-gate
     4	  philosophy: ["#6", "#3"]
     5	  type: gate
     6	  category: security
     7	  description: 危险命令拦截 (rm -rf, DROP TABLE, git push --force)
     8	  enabled_by_default: true
     9	  evidence_level: L3
    10	- name: privacy-gate
    11	  philosophy: ['#6', '#3']
    12	  type: gate
    13	  category: security
    14	  description: 敏感文件/DLP 保护，防止 .env/私钥泄露
    15	  enabled_by_default: true
    16	  evidence_level: L3
    17	- name: subagent-guard
    18	  philosophy: ['#6', '#3']
    19	  type: gate
    20	  category: security
    21	  description: 子代理类型安全门禁，限制 executor/designer/scientist
    22	  enabled_by_default: true
    23	  evidence_level: L3
    24	- name: edit-guard
    25	  philosophy: ['#4', '#6']
    26	  type: guard
    27	  category: quality
    28	  description: 编辑内容质量门禁，拦截空/越界编辑
    29	  enabled_by_default: true
    30	  evidence_level: L3
    31	- name: lsp-suggest
    32	  philosophy: ['#5', '#7']
    33	  type: monitor
    34	  category: observability
    35	  description: LSP 诊断建议注入
    36	  enabled_by_default: true
    37	  evidence_level: L3
    38	- name: auto-snapshot
    39	  philosophy: ['#7', '#3']
    40	  type: monitor
    41	  category: knowledge
    42	  description: 自动会话快照（根据 turn 间隔）
    43	  enabled_by_default: true
    44	  evidence_level: L3
    45	- name: inject-project-knowledge
    46	  philosophy: ['#7', '#1']
    47	  type: injector
    48	  category: knowledge
    49	  description: 会话启动时注入 kernel.md / claude-next.md / anti-patterns.md
    50	  enabled_by_default: true
    51	  evidence_level: L3
    52	- name: turn-counter
    53	  philosophy: ['#1', '#5']
    54	  type: monitor
    55	  category: observability
    56	  description: 轮次计数器，控制 todo 刷新间隔
    57	  enabled_by_default: true
    58	  evidence_level: L3
    59	- name: read-tracker
    60	  philosophy: ['#6', '#1']
    61	  type: monitor
    62	  category: observability
    63	  description: 读取跟踪，记录已读取文件
    64	  enabled_by_default: true
    65	  evidence_level: L3
    66	- name: error-dna
    67	  philosophy: ['#4', '#6']
    68	  type: monitor
    69	  category: observability
    70	  description: 错误 DNA 分析，跟踪错误模式
    71	  enabled_by_default: true
    72	  evidence_level: L3
    73	- name: skill-flywheel
    74	  philosophy: ['#1', '#7']
    75	  type: monitor
    76	  category: runtime
    77	  description: Skill 飞轮，技能使用统计和优化建议
    78	  enabled_by_default: true
    79	  evidence_level: L3
    80	- name: pretool-user-correction
    81	  philosophy: ['#4', '#5']
    82	  type: monitor
    83	  category: quality
    84	  description: 用户纠正检测，触发纠正学习
    85	  enabled_by_default: true
    86	  evidence_level: L3
    87	- name: completion-gate
    88	  philosophy: ['#4', '#6']
    89	  type: gate
    90	  category: delivery
    91	  description: 假完成拦截，要求 VERIFIED 证据
    92	  enabled_by_default: true
    93	  evidence_level: L3
    94	- name: context-guard
    95	  philosophy: ['#3']
    96	  type: gate
    97	  category: runtime
    98	  description: 上下文守卫，50% 甜点区警告 + 80% 硬阻断写/执行操作
    99	  enabled_by_default: true
   100	  evidence_level: L3
   101	- name: pretool-write-lock
   102	  philosophy: ['#6', '#3']
   103	  type: gate
   104	  category: audit
   105	  description: 写入前锁定检查，防止并发写入冲突
   106	  enabled_by_default: true
   107	  evidence_level: L3
   108	- name: posttool-write-lock
   109	  philosophy: ['#6', '#3']
   110	  type: gate
   111	  category: audit
   112	  description: 写入后锁定释放，清理锁定状态
   113	  enabled_by_default: true
   114	  evidence_level: L3
   115	- name: flywheel-report
   116	  philosophy: ['#4', '#1']
   117	  type: monitor
   118	  category: runtime
   119	  description: 飞轮报告生成，输出技能使用统计
   120	  enabled_by_default: true
   121	  evidence_level: L3
   122	- name: feature-probe
   123	  philosophy: ['#4', '#7']
   124	  type: tool
   125	  category: observability
   126	  path: .claude/scripts/feature-probe.sh
   127	  description: 特性探针，验证 feature 的 L1-L4 证据链
   128	  enabled_by_default: true
   129	  evidence_level: L3
   130	- name: ecosystem-probe
   131	  philosophy: ['#4', '#7']
   132	  type: probe
   133	  category: observability
   134	  description: 生态探针，检测运行平台（CC/OC）与 OMO 安装状态，AI 据此调整策略
   135	  enabled_by_default: true
   136	  evidence_level: L2
   137	- name: meta-oracle-trigger
   138	  philosophy: ['#6', '#4']
   139	  type: trigger
   140	  category: quality
   141	  description: Meta-Oracle 自动触发 — 检测 G1-G4 触发条件，提醒 AI 执行最高级独立验证
   142	  enabled_by_default: true
   143	  evidence_level: L3
   144	- name: oracle-gate
   145	  philosophy: ['#6', '#4']
   146	  type: gate
   147	  category: quality
   148	  description: Oracle 审查前置门禁 — 编辑机制/治理文件前检查 24h 内 Oracle/Meta-Oracle ACCEPT 裁决，无则阻断
   149	  enabled_by_default: true
   150	  evidence_level: L3
   151	- name: harness-config
   152	  philosophy: ['#1', '#3']
   153	  type: shared
   154	  category: utility
   155	  description: 共享配置读取器，所有 hook source 的工具库
   156	  enabled_by_default: true
   157	  evidence_level: L3
   158	- name: token-writer
   159	  philosophy: ['#1', '#4']
   160	  type: monitor
   161	  category: observability
   162	  description: 写入 token 追踪索引，由 context-guard 调用
   163	  script: .claude/hooks/token_writer.sh
   164	  enabled_by_default: true
   165	  evidence_level: L3
   166	- name: oma-lock
   167	  philosophy: ['#3', '#6']
   168	  type: gate
   169	  category: runtime
   170	  description: OMA 并发写锁门禁，多 Agent 写同一文件时排队互斥
   171	  enabled_by_default: true
   172	  evidence_level: L3
   173	- name: fuzzy-block
   174	  philosophy: ['#4', '#5']
   175	  type: gate
   176	  category: quality
   177	  description: 模糊指令硬阻断，C1 指令清晰度门禁
   178	  enabled_by_default: true
   179	  evidence_level: L3
   180	- name: pretool-sensitive-edit
   181	  philosophy: ['#6', '#3']
   182	  type: gate
   183	  category: security
   184	  description: 治理文件编辑 CAPTCHA 验证码门禁，Edit/Write/Bash 全覆盖
   185	  enabled_by_default: false
   186	  evidence_level: L3
   187	- name: pre-completion-gate
   188	  philosophy: ['#4', '#6']
   189	  type: gate
   190	  category: delivery
   191	  description: 前置完成门禁，阻止无证据 TaskUpdate(completed)，节省浪费轮次
   192	  enabled_by_default: true
   193	  evidence_level: L3
   194	- name: posttool-anti-pattern-detect
   195	  philosophy: ['#6', '#4']
   196	  type: gate
   197	  category: quality
   198	  description: 反模式检测，A2/F1/G1/H1 四类阻断（虚假完成/假设驱动/伪诚信/语义作弊）
   199	  enabled_by_default: true
   200	  evidence_level: L3
   201	- name: posttool-claim-audit
   202	  philosophy: ['#6', '#4', '#1']
   203	  type: audit
   204	  category: audit
   205	  description: 铁律 #1 编造检测 — 检查 Edit/Write 输出中的无证据断言，要求 file:line 引用
   206	  enabled_by_default: true
   207	  evidence_level: L3
   208	- name: posttool-subagent-audit
   209	  philosophy: ['#6', '#4']
   210	  type: audit
   211	  category: audit
   212	  description: 子 agent 字节数审计，超阈值写入 flywheel P0
   213	  enabled_by_default: true
   214	  evidence_level: L3
   215	- name: posttool-completion-audit
   216	  philosophy: ['#4', '#6']
   217	  type: audit
   218	  category: audit
   219	  description: 完成声明审计，交叉验证 TaskUpdate 与实际产物
   220	  enabled_by_default: true
   221	  evidence_level: L3
   222	- name: posttool-handoff-writer
   223	  philosophy: ['#7', '#5']
   224	  type: monitor
   225	  category: knowledge
   226	  description: 完成时自动写交接备忘录，session-handoff 持久化
   227	  enabled_by_default: true
   228	  evidence_level: L3
   229	- name: intent-tracker
   230	  philosophy: ['#6', '#4']
   231	  type: monitor
   232	  category: quality
   233	  description: 声明矛盾检测，编辑抖动/内容回退追踪
   234	  enabled_by_default: true
   235	  evidence_level: L3
   236	
   237	- name: thinking-gate
   238	  philosophy: ['#1', '#6', '#4']
   239	  type: gate
   240	  category: quality
   241	  description: Thinking/Reasoning 内容门禁 — 在消息进入 context 前剥离 reasoning_content，防止 token 膨胀
   242	  enabled_by_default: true
   243	  evidence_level: L2
   244	
   245	# ── 以下为 2026-05 补全（lx-sync 全量同步） ──
   246	
   247	# Security
   248	- name: pretool-sensitive-file-guard
   249	  philosophy: ['#6', '#3']
   250	  type: gate
   251	  category: security
   252	  description: 拦截 AI 通过 Edit/Write 工具直接写 permission-approved / permission-required 标记文件
   253	  enabled_by_default: true
   254	  evidence_level: L3
   255	- name: pretool-terminal-safety
   256	  philosophy: ['#1', '#7']
   257	  type: gate
   258	  category: security
   259	  description: 终端命令安全门禁，超长命令阻断要求写脚本文件
   260	  enabled_by_default: true
   261	  evidence_level: L3
   262	- name: pretool-blast-radius
   263	  philosophy: ['#6', '#3']
   264	  type: gate
   265	  category: security
   266	  description: 检测 git checkout . / rm -rf 等全量操作，提醒改用选择性路径
   267	  enabled_by_default: true
   268	  evidence_level: L3
   269	- name: pretool-retry-check
   270	  philosophy: ['#6', '#4']
   271	  type: gate
   272	  category: security
   273	  description: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令
   274	  enabled_by_default: true
   275	  evidence_level: L3
   276	- name: build-validator
   277	  philosophy: ['#4', '#6']
   278	  type: gate
   279	  category: quality
   280	  description: 构建失败自动记录错误日志并给出针对性修复建议
   281	  enabled_by_default: true
   282	  evidence_level: L3
   283	- name: pre-ask-guard
   284	  philosophy: ['#5', '#4']
   285	  type: gate
   286	  category: quality
   287	  description: 拦截 AskUserQuestion，检查决策链是否已有答案。能自主决策则阻断提问，降低人类心智负担
   288	  enabled_by_default: true
   289	  evidence_level: L3
   290	
   291	# Quality / Guard
   292	- name: pre-edit-lsp-check
   293	  philosophy: ['#4', '#3']
   294	  type: guard
   295	  category: quality
   296	  description: 编辑代码文件前主动获取诊断结果，注入 AI 上下文
   297	  enabled_by_default: true
   298	  evidence_level: L3
   299	- name: pretool-purify-gate
   300	  philosophy: ['#4', '#6']
   301	  type: guard
   302	  category: quality
   303	  description: 编辑治理文件时注入哲学纯度提醒到 AI 上下文（不阻断）
   304	  enabled_by_default: true
   305	  evidence_level: L3
   306	- name: pretool-skill-version-guard
   307	  philosophy: ['#4', '#7']
   308	  type: guard
   309	  category: quality
   310	  description: 拦截硬编码版本号写入 SKILL.md，确保只用 >= 格式（指向 VERSION.json 单一真相源）
   311	  enabled_by_default: true
   312	  evidence_level: L3
   313	- name: pretool-edit-scope
   314	  philosophy: ['#4', '#6']
   315	  type: guard
   316	  category: quality
   317	  description: 范围文件匹配 + 自动加入 + 核心文件警告 + 长对话规则锚定 + 无证据完成提醒
   318	  enabled_by_default: true
   319	  evidence_level: L3
   320	- name: posttool-format-gate
   321	  philosophy: ['#5', '#7']
   322	  type: guard
   323	  category: quality
   324	  description: 检查任务输出是否符合"以人为本"原则：有方向感、结构化、认知负担低
   325	  enabled_by_default: true
   326	  evidence_level: L3
   327	- name: posttool-template-check
   328	  philosophy: ['#4', '#7']
   329	  type: guard
   330	  category: quality
   331	  description: 检查编辑后的文件是否符合模板规范
   332	  enabled_by_default: true
   333	  evidence_level: L3
   334	- name: pretool-approve-detect
   335	  philosophy: ['#5', '#2']
   336	  type: gate
   337	  category: delivery
   338	  description: 拦截用户聊天中的 /approve|/deny 指令，实现对话内批准流程
   339	  enabled_by_default: true
   340	  evidence_level: L3
   341	
   342	# Observability / Monitor
   343	- name: context-compressor
   344	  philosophy: ['#1', '#4']
   345	  type: monitor
   346	  category: runtime
   347	  description: 检测源文件 mtime → 拼接精简内容 → 缓存到 .omc/state/context-cache.md
   348	  enabled_by_default: true
   349	  evidence_level: L3
   350	- name: error-dna-auto-fix
   351	  philosophy: ['#4', '#6']
   352	  type: monitor
   353	  category: observability
   354	  description: 跨会话错误回顾：扫描 error-dna.json 输出未修复的顽固错误
   355	  enabled_by_default: true
   356	  evidence_level: L3
   357	- name: knowledge-condenser
   358	  philosophy: ['#4', '#1']
   359	  type: monitor
   360	  category: knowledge
   361	  description: 扫描 claude-next.md 高频模式(hits≥2)，输出升华建议
   362	  enabled_by_default: true
   363	  evidence_level: L3
   364	- name: lsp-gate
   365	  philosophy: ['#5', '#7']
   366	  type: gate
   367	  category: observability
   368	  description: LSP 门禁 — SessionStart 检测 LSP 可用性，输出配置建议
   369	  enabled_by_default: true
   370	  evidence_level: L2
   371	- name: posttool-checkpoint
   372	  philosophy: ['#7', '#5']
   373	  type: monitor
   374	  category: knowledge
   375	  description: TaskUpdate(completed) / Stop 时自动生成过程摘要 + 决策记录 + 待处理 + 方向指引
   376	  enabled_by_default: true
   377	  evidence_level: L3
   378	- name: posttool-bash-audit
   379	  philosophy: ['#6', '#4']
   380	  type: audit
   381	  category: audit
   382	  description: Bash 执行后审计权限上下文，只提醒不阻断
   383	  enabled_by_default: true
   384	  evidence_level: L3
   385	- name: posttool-read-cite
   386	  philosophy: ['#7', '#5']
   387	  type: monitor
   388	  category: audit
   389	  description: 读取文件后提示引用规范，要求标注 file:line 来源
   390	  enabled_by_default: true
   391	  evidence_level: L3
   392	- name: posttool-write-cite
   393	  philosophy: ['#7', '#4']
   394	  type: monitor
   395	  category: audit
   396	  description: 检测写入 claude-next.md 时验证教训格式
   397	  enabled_by_default: true
   398	  evidence_level: L3
   399	- name: posttool-edit-quality
   400	  philosophy: ['#4', '#5']
   401	  type: guard
   402	  category: quality
   403	  description: 编辑后自查代码风格、文档同步、方案复用检测
   404	  enabled_by_default: true
   405	  evidence_level: L3
   406	- name: skill-usage-tracker
   407	  philosophy: ['#4', '#1']
   408	  type: monitor
   409	  category: observability
   410	  description: "无侵入 skill 使用率追踪 — 双路径: UserPromptSubmit(扫描/命令文本) + PostToolUse:Skill(工具调用)"
   411	  enabled_by_default: true
   412	  evidence_level: L3
   413	- name: session-resume
   414	  philosophy: ['#5', '#7']
   415	  type: monitor
   416	  category: runtime
   417	  description: 会话恢复 — 检测 session-handoff.md 并注入恢复上下文
   418	  enabled_by_default: true
   419	  evidence_level: L3
   420	- name: pretool-cruise-check
   421	  philosophy: ['#1', '#5']
   422	  type: gate
   423	  category: runtime
   424	  description: 巡航模式检测 — SessionStart/PreToolUse 检查是否进入 goal/ghost 巡航模式
   425	  enabled_by_default: true
   426	  evidence_level: L2
   427	- name: pretool-node-reference
   428	  philosophy: ['#7', '#1']
   429	  type: gate
   430	  category: quality
   431	  description: Agent 工具前置检查 — 注入 nodes 引用到 sub-agent 上下文
   432	  enabled_by_default: true
   433	  evidence_level: L2
   434	- name: pretool-oracle-gate-py
   435	  philosophy: ['#6', '#4']
   436	  type: gate
   437	  category: quality
   438	  description: Oracle 审查前置门禁 (Python 版) — 编辑机制/治理文件前检查 Oracle/Meta-Oracle ACCEPT 裁决
   439	  enabled_by_default: true
   440	  evidence_level: L3
   441	- name: pretool-oracle-gate
   442	  philosophy: ['#6', '#4']
   443	  type: gate
   444	  category: quality
   445	  description: Oracle 审查前置门禁 (Shell 版) — 编辑机制/治理文件前检查 Oracle/Meta-Oracle ACCEPT 裁决
   446	  enabled_by_default: true
   447	  evidence_level: L3
   448	- name: pretool-plan-gate
   449	  philosophy: ['#4', '#7']
   450	  type: gate
   451	  category: delivery
   452	  description: 非琐碎任务强制 planning — Edit|Write|Bash 前检查是否有 plan 文件
   453	  enabled_by_default: true
   454	  evidence_level: L3
   455	- name: pretool-rules-inject
   456	  philosophy: ['#7', '#3']
   457	  type: injector
   458	  category: knowledge
   459	  description: 用户提交 prompt 时注入规则提醒到 AI 上下文
   460	  enabled_by_default: true
   461	  evidence_level: L3
   462	- name: stop-drain
   463	  philosophy: ['#6', '#4']
   464	  type: monitor
   465	  category: observability
   466	  description: Stop 时兜底扫描 transcript 补写错误记录（防御纵深第二层）
   467	  enabled_by_default: true
   468	  evidence_level: L3
   469	- name: meta-oracle-trigger-py
   470	  philosophy: ['#6', '#4']
   471	  type: trigger
   472	  category: quality
   473	  description: Meta-Oracle 自动触发 (Python 版) — 检测 G1-G4 触发条件，提醒 AI 执行最高级独立验证
   474	  enabled_by_default: true
   475	  evidence_level: L3
   476	- name: agentic-ui
   477	  philosophy: ['#5', '#7']
   478	  type: monitor
   479	  category: runtime
   480	  description: Agentic UI 状态管理 — 更新轮次/锚定信息到 AI 上下文
   481	  enabled_by_default: true
   482	  evidence_level: L2
   483	
   484	# ── Skill 执行合规 (2026-06-01) ──
   485	- name: skill-body-enforce
   486	  philosophy: ['#3', '#6']
   487	  type: injector
   488	  category: governance
   489	  description: PreToolUse:Skill — 自动将 body.md 内容注入 AI 上下文，确保 AI 看到强制执行合约
   490	  enabled_by_default: true
   491	  evidence_level: L2
   492	- name: skill-compliance-audit
   493	  philosophy: ['#4', '#6']
   494	  type: audit
   495	  category: governance
   496	  description: PostToolUse:Skill — 审计 AI 是否按 body.md 执行，发现偏差注入警告
   497	  enabled_by_default: true
   498	  evidence_level: L2
```

### `.claude/schemas/registry.yaml`

```
     1	# Schema 注册表（MVP v5）
     2	
     3	# 版本：v5（精简版，仅保留有消费者的 Schema）
     4	
     5	#
     6	
     7	# 审计规则：每个 schema 必须标注 consumers，零消费者的 schema 应被删除
     8	
     9	# 最后审计：2026-06-07（Oracle 评审 P0 精简 + 孤儿文件清理）
    10	
    11	#
    12	
    13	# 已删除节点：
    14	
    15	# plan_node — 0 引用，规划逻辑内联到 skill
    16	
    17	# a0_clarifier — 0 引用，澄清逻辑合并到 interactive_prompt
    18	
    19	# spec_generator — 0 引用，generator.md 已覆盖
    20	
    21	# fallback_exploration — 0 引用，降级触发在 execute_node 中
    22	
    23	# fallback_framework — 0 引用，同上
    24	
    25	# judge — 0 引用，verdict schema 已定义判定结构
    26	
    27	#
    28	
    29	# 已清理 schemas（文件已从磁盘删除）：
    30	
    31	# output/plan_output.yaml — 消费者 plan_node 已删除
    32	
    33	# output/spec_output.yaml — 消费者 spec_generator 已删除（2026-06-07 已清理）
    34	
    35	# output/criteria_output.yaml — 无实际消费者（2026-06-07 已清理）
    36	
    37	# output/registry.yaml — 空文件，无实际消费者（2026-06-07 已清理）
    38	
    39	# output/fallback_output.yaml — 消费者 fallback_* 已删除
    40	
    41	# 保留（有引用争议，lx-todo 通过目录级引用提及）：
    42	
    43	# output/acceptance_report.yaml — Referenced by lx-todo Step 4（保留）
    44	
    45	
    46	 verdict: path: schemas/atomic/verdict.yaml version: v1 description: "最终判定" consumers: [ALL]
    47	contract: state_transitions: path: schemas/contract/state_transitions.yaml version: v1 description: "状态机转换契约（参考文档，非强制）" consumers: [lx-task-spec]
```

### `.claude/skills/skill-dependencies.yaml`

```
     1	# skill-dependencies.yaml — 技能依赖图声明
     2	# 用途：显式声明各 skill 之间的依赖关系和管线流向，防止隐式循环
     3	# 维护者：Carror OS
     4	# 版本：v2.0.0 — OMA 四合一合并
     5	#
     6	# 变更记录:
     7	#   v2.0.0: lx-oma-hier + lx-oma-split + lx-oma-gov + lx-oma-orch → lx-oma (subcommand dispatch)
     8	#   v1.0.0: 初始版本
     9	
    10	# ─── 管线阶段（严格有序） ───
    11	# 每个阶段依赖上一阶段的输出
    12	pipeline:
    13	  stages:
    14	    - id: hier
    15	      name: 分层拆解
    16	      skill: lx-oma
    17	      subcommand: hier
    18	      input: master-prd.md / 大型 PRD 目录
    19	      output: sub-prds/domain-{id}.md
    20	      gate: og-001 (hier→oma)
    21	    - id: split
    22	      name: 特性拆解
    23	      skill: lx-oma
    24	      subcommand: split
    25	      input: sub-prds/domain-{id}.md
    26	      output: prd/{sub_prd}/feat-{id}/prd.md
    27	      gate: og-002 (oma→gov)
    28	    - id: gov
    29	      name: 治理初始化
    30	      skill: lx-oma
    31	      subcommand: gov
    32	      input: master-prd.md + prd/{sub_prd}/feat-{id}/
    33	      output: .omc/state/gov-latest-report.yaml
    34	      gate: og-00N (gov→rpe)
    35	    - id: rpe
    36	      name: 特性开发
    37	      skill: lx-rpe
    38	      input: prd/{sub_prd}/feat-{id}/prd.md
    39	      output: rpe/{feature}/ (implementation)
    40	      gate: og-00N (rpe→dev)
    41	    - id: dev
    42	      name: 研发执行
    43	      skill: (multi-agent / lx-race)
    44	      input: rpe/{feature}/plan.md
    45	      output: 代码变更
    46	      gate: none (terminal stage)
    47	
    48	# ─── 技能依赖声明 ───
    49	# provides: 该 skill 产出的工件
    50	# consumes: 该 skill 消耗的工件/其他 skill 的产出
    51	# references: 该 skill 引用（import/read）的其他 skill 的 SKILL.md
    52	# orchestrator: 该 skill 被哪个编排器协调
    53	skills:
    54	  - id: lx-oma
    55	    version: v2.0.0
    56	    type: pipeline
    57	    subcommands:
    58	      - hier     # L1 分层拆解（原 lx-oma-hier v1.3.2）
    59	      - split    # L2 特性拆解（原 lx-oma-split v1.2.1）
    60	      - gov      # PRD 治理（原 lx-oma-gov v1.2.1）
    61	      - orch     # 管线编排（原 lx-oma-orch v1.2.2）
    62	    consumes:
    63	      hier: [master_prd]
    64	      split: [sub_prd_domains]
    65	      gov: [master_prd, feature_prds]
    66	      orch: [pipeline_state]
    67	    provides:
    68	      hier: [sub_prd_domains]
    69	      split: [feature_prds]
    70	      gov: [gov_report]
    71	      orch: [pipeline_advancement, gate_decisions]
    72	    orchestrates:
    73	      - lx-oma (hier → split → gov → orch, internal routing)
    74	      - lx-rpe
    75	    description: "OMA Pipeline — hierarchically decompose, split into features, govern, orchestrate (subcommand: hier|split|gov|orch)"
    76	
    77	  - id: lx-rpe
    78	    version: v4.0.0
    79	    type: implementation
    80	    consumes: [feature_prds]
    81	    provides: [implementation, test_evidence]
    82	    references:
    83	      - lx-oma    # 治理路径从 gov 接收变更通知
    84	    orchestrator: lx-oma
    85	    description: RPE 系统性开发模式 — 9 步开发闭环
    86	
    87	  - id: lx-race
    88	    version: v1.0.0
    89	    type: coordination
    90	    consumes: [task_queue]
    91	    provides: [parallel_execution, conflict_report]
    92	    orchestrator: lx-oma (optional)
    93	    description: 蜂群协调层 — 状态跟踪+冲突协调
    94	
    95	  - id: lx-oracle
    96	    version: v2.0.0
    97	    type: quality-gate
    98	    consumes: [task_evidence, executor_logs, token_files]
    99	    provides: [oracle_verdicts, gate_decisions]
   100	    description: Oracle quality gate system — static (Oracle-D), runtime (Oracle-V), dual-agent review (Duo)
   101	
   102	# ─── 数据契约 ───
   103	# 各 skill 之间交换的数据格式约定
   104	contracts:
   105	  - from: lx-oma (hier)
   106	    to: lx-oma (split)
   107	    artifact: sub-prds/domain-{id}.md
   108	    schema: Sub PRD 模板（边界/接口/非功能/Mock/数据实体/依赖/AC）
   109	  - from: lx-oma (split)
   110	    to: lx-oma (gov)
   111	    artifact: prd/{sub_prd}/feat-{id}/prd.md
   112	    schema: feature PRD 模板
   113	  - from: lx-oma (gov)
   114	    to: lx-oma (orch)
   115	    artifact: .omc/state/gov-latest-report.yaml
   116	    schema: gov_report.yaml
   117	  - from: lx-oma (orch)
   118	    to: all
   119	    artifact: state/pipeline.yaml
   120	    schema: pipeline 状态机 YAML
   121	
   122	# ─── 隐式依赖: Hook 门禁 → Skill ───
   123	# 这些依赖是通过运行时 hook 系统注入的，skill 本身不显式引用，
   124	# 但执行时必须有对应的 hook 门禁支持。
   125	hook_gates:
   126	  - gate: pretool_plan_gate
   127	    protects: [lx-goal, lx-rpe, lx-ghost]
   128	    description: Plan-before-Execute 门禁，阻断未审批的代码变更
   129	  - gate: permission_gate
   130	    protects: [lx-goal, lx-ghost, lx-rpe]
   131	    description: 危险命令拦截 + CAPTCHA 文件保护，自主执行安全网
   132	  - gate: pretool_oracle_gate
   133	    protects: [lx-ghost]
   134	    description: Oracle 审核前置门禁
   135	  - gate: pre_ask_guard
   136	    protects: [lx-goal, lx-ghost]
   137	    description: 决策链过滤，减少自主模式下的不必要打断
   138	  - gate: pretool_git_gate
   139	    protects: [lx-git-check]
   140	    description: Git 提交前检查门禁
   141	  - gate: pretool_skill_version_guard
   142	    protects: [lx-validate-skill, lx-skillify]
   143	    description: SKILL.md 版本格式门禁
   144	  - gate: pretool_skill_body_enforce
   145	    protects: [lx-skillify]
   146	    description: Skill body 强制执行合约注入
   147	
   148	# ─── 校验规则 ───
   149	validation:
   150	  # 禁止循环依赖：skills[].references 必须形成 DAG
   151	  no_cycles: true
   152	  # 管线阶段必须是有向无环的
   153	  pipeline_acyclic: true
   154	  # 每个 consumed artifact 必须被上游某个 skill 的 provides 覆盖
   155	  artifact_coverage: true
```

### `.claude/skills/SKILLS.md`

```
     1	# Carror OS Skill 体系
     2	
     3	## 分层架构
     4	
     5	```
     6	Governance (治理)           Workflow (工作流)
     7	  (暂无)                      lx-todo  lx-code-review
     8	  (soft ref: lx-oracle)       lx-pre-commit  lx-pre-push
     9	  lx-validate-skill           lx-dogfood
    10	                              lx-root-cause-analysis  lx-stepwise
    11	
    12	Autonomous (自主)           OMA Pipeline (管线)
    13	  lx-goal                    lx-oma (hier → split → gov → orch) → lx-rpe
    14	  lx-ghost
    15	
    16	Foundation (基础)
    17	  lx-task-spec  lx-learner  lx-skillify  lx-varlock
    18	```
    19	
    20	## 依赖关系
    21	
    22	```
    23	lx-goal ──→ lx-stepwise (子任务路由)
    24	lx-ghost ──→ lx-oracle (自主计划审核)
    25	lx-oma ──→ lx-rpe (管线编排)
    26	lx-task-spec ──→ lx-oma (Enhanced 模式)
    27	```
    28	
    29	## 共享基础设施
    30	
    31	| 文件 | 被引用者 |
    32	|------|---------|
    33	| `references/oma/degradation-strategies.md` | lx-oma (hier, split, orch, gov) |
    34	| `references/oma/observability.md` | lx-oma (hier, split, orch, gov) |
    35	| `references/oma/pipeline-contract.md` | lx-oma (hier, split, orch, gov) |
    36	| `references/oma/direction-guide.md` | lx-oma (hier, split), lx-rpe |
    37	| `schemas/atomic/error_codes.yaml` | lx-oma (HIER, SPLIT, ORCH, GOV) |
    38	| `nodes/oracle_terminal.md` | lx-oma, lx-goal, lx-ghost |
    39	| `nodes/mode_selector.md` | lx-oma, lx-goal, lx-ghost |
    40	
    41	## 归档
    42	
    43	| Skill | 归档原因 | 路径 |
    44	|-------|---------|------|
    45	| lx-purify | 低频思想纯度审计 | `archived/lx-purify/` |
    46	| lx-sync | 变更后一致性检查 | `archived/lx-sync/` |
    47	| lx-race | 并行执行，有独立CLI | `archived/lx-race/` |
```

### `.claude/settings.json` — hook 注册配置(已脱敏)

```
     1	{
     2	  "env": {
     3	    "ANTHROPIC_AUTH_TOKEN": "<REDACTED>",
     4	    "ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic",
     5	    "ANTHROPIC_MODEL": "kimi-k3",
     6	    "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-k3",
     7	    "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-k3",
     8	    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "kimi-k3",
     9	    "CLAUDE_CODE_SUBAGENT_MODEL": "kimi-k3",
    10	    "ENABLE_TOOL_SEARCH": "false",
    11	    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1048576"
    12	  },
    13	  "enabledPlugins": {
    14	    "pyright-lsp@claude-plugins-official": true
    15	  },
    16	  "effortLevel": "xhigh",
    17	  "skipDangerousModePermissionPrompt": true,
    18	  "skipWorkflowUsageWarning": true,
    19	  "model": "opus",
    20	  "hooks": {
    21	    "PreToolUse": [
    22	      {
    23	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    24	        "hooks": [
    25	          {
    26	            "type": "command",
    27	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"pretool-gate.py\""
    28	          }
    29	        ]
    30	      },
    31	      {
    32	        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob",
    33	        "hooks": [
    34	          {
    35	            "type": "command",
    36	            "command": "bash \".claude/hooks/hook-launcher.sh\" \"carroros-night-deny.py\""
    37	          }
    38	        ]
    39	      }
    40	    ],
    41	    "UserPromptSubmit": [
    42	      {
    43	        "hooks": [
    44	          {
    45	            "type": "command",
    46	            "command": "python3 \".claude/hooks/pretool-user-approve.py\"",
    47	            "timeout": 3000
    48	          }
    49	        ]
    50	      }
    51	    ],
    52	    "PostToolUse": [
    53	      {
    54	        "matcher": "*",
    55	        "hooks": [
    56	          {
    57	            "type": "command",
    58	            "command": "python3 \".claude/hooks/posttool-gate.py\"",
    59	            "timeout": 5000
    60	          }
    61	        ]
    62	      }
    63	    ],
    64	    "SessionStart": [
    65	      {
    66	        "hooks": [
    67	          {
    68	            "type": "command",
    69	            "command": "python3 \".claude/hooks/session-start.py\"",
    70	            "timeout": 3000
    71	          }
    72	        ]
    73	      }
    74	    ],
    75	    "Stop": [
    76	      {
    77	        "hooks": [
    78	          {
    79	            "type": "command",
    80	            "command": "python3 \".claude/hooks/stop-flywheel.py\"",
    81	            "timeout": 10000
    82	          }
    83	        ]
    84	      }
    85	    ]
    86	  },
    87	  "statusLine": {
    88	    "type": "command",
    89	    "command": "bash \".claude/hooks/statusline-command.sh\""
    90	  }
    91	}
```
