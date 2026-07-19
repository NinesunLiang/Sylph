# pretool-gate.py [1/2] ★_check_verified

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | 助手/**_check_verified 254-278**/sensitive/fallback/action/plan/edit-scope 门(第 1-542 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/hooks/pretool-gate.py` 第 1-542 行

```python
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
```
