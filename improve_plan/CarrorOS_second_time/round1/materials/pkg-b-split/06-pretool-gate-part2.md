# pretool-gate.py [2/2] ★verify-gate 门

> 基线: `91954a0b01f9c53edf94965238308fcb080818eb`(+工作区未提交改动) | PKG-B 函数级分片 | _check_verify_gate 543/oracle 门/文档质量/G2-G6/main(第 543-879 行)
> 密钥已脱敏为 <REDACTED>;行号为原文件真实行号


## `.claude/hooks/pretool-gate.py` 第 543-879 行

```python
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
